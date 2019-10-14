__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

"""

from framework.common import TestConstants as tc
from framework.common import EsxStats as EsxStats
from framework.common import Esxtop as Esxtop
from framework.common import Memoized as mem
from framework.vcenter import Datacenter, Cluster


from collections import defaultdict, namedtuple
import multiprocessing
from multiprocessing.dummy import Pool as ThreadPool

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship,sessionmaker
from sqlalchemy import create_engine,Table, Column, Integer, String, MetaData
import time
from dateutil.parser import parse
from pyVmomi import vim, vmodl

import datetime
import pytz

logger = tc.logger
pool = ThreadPool(16)
task_pool = ThreadPool(16)
task_results = tc.task_results
process = tc.process

Base = declarative_base()

class VMStats(Base):
    __tablename__ = 'vmstatus'
    id = Column(Integer, primary_key=True)
    time = Column(Integer)
    vmname = Column(String(40))
    progress = Column(Integer)
    legend = Column(String(100))

class MaintenanceStat(Base):
    __tablename__ = 'maintenancestatus'
    id = Column(Integer, primary_key=True)
    time = Column(Integer)
    hostname = Column(String(40))
    progress = Column(Integer)


def drs_handler_wrapper(args):
    """
    Wrapping arround vmotion_handler
    """
    return drs_handler(*args)


def drs_handler(logger, si, template_vm):
    """
    Will handle the thread handling migration of virtual machine and run post processing
    """

    # time.sleep(10) # Sleep Introduced to trigger Host Collection Stats

    vmsession = None
    complete_time = None



    try:

        vm_name = template_vm.name



        engine = create_engine('sqlite:///framework/db/%s.db' % vm_name)
        # remove_db(engine, db_name)

        Base.metadata.create_all(engine)
        time.sleep(1)

        Base.metadata.bind = engine
        vmDbSession = sessionmaker(bind=engine)
        vmsession = vmDbSession()

        tzinfos = {"UTC": 0}



        vm_task = None

        taskLoop = True
        vm_loop = False
        startRecorded = False

        while taskLoop:
            try:
                vm_tasks = template_vm.recentTask
                vm_task = vm_tasks[0]

                taskLoop = False
                logger.debug("THREAD - %s - Migrating Task initiated."%vm_name)
                logger.debug("THREAD - %s - %s" % (vm_name, vm_task))
                vm_loop = True
            except IndexError, ix:
                #This means VM Migration Task is yet to be triggered
                pass
                #time.sleep(1)

        logger.info("Starting VM Task Monitor Loop")

        epoch = datetime.datetime.utcfromtimestamp(0)

        utc = pytz.UTC

        begin = epoch.replace(tzinfo=utc)

        while vm_loop:



            try:


                """
                if not queueRecorded:
                    queue_time = parse(str(vm_task.info.queueTime), tzinfos=tzinfos).strftime('%s')
                    vmStatS = VMStats(time=queue_time, vmname=vm_name, legend="Queued",
                                      progress=0)
                    vmsession.add(vmStatS)
                    vmsession.commit()
                    queueRecorded = True
                """


                if not startRecorded:
                    st_time = vm_task.info.startTime
                    st_time = st_time.replace(tzinfo=utc)
                    #start_time = parse(str(st_time), tzinfos=tzinfos).strftime('%s')
                    start_time = (st_time - begin).total_seconds() * 1000.0
                    logger.info("VM %s  Migration started at %s" % (vm_name, st_time))
                    vmStatS = VMStats(time=start_time, vmname=vm_name, legend="Started",
                                      progress=vm_task.info.progress)
                    vmsession.add(vmStatS)
                    vmsession.commit()
                    startRecorded = True

                task_time = si.CurrentTime()
                task_time = task_time.replace(tzinfo=utc)
                task_state = vm_task.info.state
                #current_time = parse(str(task_time), tzinfos=tzinfos).strftime('%s')
                current_time = (task_time - begin).total_seconds() * 1000.0

                #logger.debug("THREAD - %s - The current time is %s"%(vm_name,current_time))

                if task_state == vim.TaskInfo.State.running:

                    vm_progress = vm_task.info.progress
                    logger.info("VM %s  is running with %s progress " % (vm_name, vm_progress))

                    if vm_progress :
                        vmStatS = VMStats(time=current_time, vmname=vm_name, legend="Running",
                                          progress=vm_progress)
                        vmsession.add(vmStatS)
                        vmsession.commit()
                        time.sleep(2)



                elif task_state == vim.TaskInfo.State.success:
                    cm_time = vm_task.info.completeTime
                    cm_time = cm_time.replace(tzinfo=utc)
                    #completeTime =  parse(str(vm_task.info.completeTime), tzinfos=tzinfos).strftime('%s')
                    completeTime = (cm_time - begin).total_seconds() * 1000.0
                    vmStatS = VMStats(time=completeTime, vmname=vm_name, legend="Completed",progress=100)
                    vmsession.add(vmStatS)
                    vmsession.commit()
                    logger.info("VM %s complete time %s " % (vm_name, vm_task.info.completeTime))
                    vm_loop = False
                else:
                    logger.error("THREAD - %s - VM Unrecorded State is %s"%(vm_name,task_state))

                if vm_task.info.error is not None:
                    out = '%s DRS Migration Operation did not complete successfully: %s' % (vm_name, vm_task.info.error)
                    logger.info(out)
                    vm_loop = False

            except Exception, e:
                logger.error("%s -  Error while entring data to Task DB %s" % (vm_name, e))
            finally:
                vmsession.close()

    except vmodl.MethodFault, e:
        logger.error("Caught vmodl fault: %s" % e.msg)

    except Exception, e:
        logger.error("Caught exception: %s" % str(e))

def monitor_host_manitenenace(logger,vc, vc_user, vc_pass, dc, cls, host):

    #threadname = multiprocessing.current_process().name
    engine = create_engine('sqlite:///framework/db/%s.db' % host)
    # remove_db(engine, db_name)

    Base.metadata.create_all(engine)
    time.sleep(1)

    Base.metadata.bind = engine
    hostDbSession = sessionmaker(bind=engine)
    hostsession = hostDbSession()

    tzinfos = {"UTC": 0}



    si = Datacenter.Login(logger, vc, vc_user, vc_pass, port=443)
    logger.info("THREAD - %s - Login Successful"%host)

    dcMor = Datacenter.GetDatacenter(name=dc, si=si)
    logger.info("Got - %s - Dataceneter MOR"%host)

    host_mor = Cluster.GetHostInClusters(dcMor, host, clusterNames=[cls])
    logger.info("THREAD - %s - Got Host MOR"%host)

    logger.info("THREAD - %s - Initiating Maintenance Mode"%host)
    host_maintenance_task = host_mor.EnterMaintenanceMode_Task(timeout=0)

    logger.info("THREAD - %s - Host Maintenance queue time %s " % (host,host_maintenance_task.info.queueTime))
    logger.info("THREAD - %s - Host Maintenance start time %s " % (host,host_maintenance_task.info.startTime))

    """

    start_time = parse(str(host_maintenance_task.info.startTime), tzinfos=tzinfos).strftime('%s')
    hostStat = MaintenanceStat(time=start_time, hostname=host,progress=host_maintenance_task.info.progress)
    hostsession.add(hostStat)
    hostsession.commit()

    maintenance_loop = True
    while maintenance_loop:
        current_time = parse(str(si.CurrentTime()), tzinfos=tzinfos).strftime('%s')

        if host_maintenance_task.info.state == vim.TaskInfo.State.running:
            logger.info("THREAD - %s - Host maintenance is running in progress " % (host))
            hostStat = MaintenanceStat(time=current_time, hostname=host,  progress=host_maintenance_task.info.progress)
            hostsession.add(hostStat)
            hostsession.commit()
            time.sleep(5)
        if host_maintenance_task.info.state == vim.TaskInfo.State.success:
            complete_time = host_maintenance_task.info.completeTime
            completeTime = parse(str(complete_time), tzinfos=tzinfos).strftime('%s')
            logger.info("THREAD - %s - Host maintenance is completed at %s  with %s progress " % (host,complete_time, 100))
            maintenance_loop = False
            hostStat = MaintenanceStat(time=completeTime, hostname=host, progress=100)
            hostsession.add(hostStat)
            hostsession.commit()

        if host_maintenance_task.info.error is not None:
            out = 'THREAD - %s - Operation did not complete successfully: %s' % (host, host_maintenance_task.info.error)
            print out
            maintenance_loop = False
    hostsession.close()
    """


def runTest():
    drs_specs = []
    vmotionnic = {}

    # cluster host will contain the information of cluster to which the host belongs
    clusterhost = {}

    hostdetails = namedtuple('hostdetails',
                             ['vcenter', 'vcenter_user', 'vcenter_pass', 'datacenter', 'cluster', 'nic', 'disk'])

    # hs_data = {}

    try:

        host_mor = None
        vcenter = None
        vcenter_user = None
        vcenter_pass = None
        src_datacenter = None
        container = None
        src_host = None

        for instance in range(1, process + 1):
            tc.instance = instance
            test_vm = tc.getVM()
            vcenter = tc.getLDU()
            vcenter_user = tc.getLDULocalUser()
            vcenter_pass = tc.getLDULocalPass()
            src_datacenter = tc.getDatacenter()


            dest_datacenter = tc.getXDatacenter()
            container = tc.getCluster()



            destination_cluster = tc.getXCluster()
            host = tc.getXHost()

            datastore = tc.getXDatastore()
            pnic = tc.getPnic()
            dest_disk = tc.getDestDisk()

            # Source Host Parameter

            src_host = tc.getHost()
            src_nic = tc.getSrcPnic()
            src_datastore = tc.getDatastore()
            src_disk = tc.getSrcDisk()

            """

            tc.logger.debug("THREAD - MAIN - Instance %s specs for %s operation is %s %s %s %s %s %s %s %s %s" % (
            instance, test_vm, vcenter, vcenter_user,
            vcenter_pass, dest_datacenter, container, destination_cluster, host, datastore, pnic))
            """

            # clusterhost[host] = destination_cluster

            hs = hostdetails(vcenter, vcenter_user, vcenter_pass, dest_datacenter, destination_cluster, pnic, dest_disk)

            tc.hs_data[host] = hs

            # vmotionnic[host] = pnic

            tc.host_stat_spec.setdefault(host, []).append(datastore)

            # Source Host Spec for Stat Collection

            src_hs = hostdetails(vcenter, vcenter_user, vcenter_pass, src_datacenter, container, src_nic, src_disk)
            tc.hs_data[src_host] = src_hs
            tc.host_stat_spec.setdefault(src_host, []).append(src_datastore)

            si = mem.getMemSi(vcenter, vcenter_user, vcenter_pass)
            logger.info("Login Successful")

            src_dcMor = mem.getMemDatacenter(si, src_datacenter)
            logger.info("Got Source Datacenter MOR")

            logger.info("Obtaining Container cluster for VM")
            container_cluster = mem.getMemCluster(src_dcMor, container)
            if container_cluster is None:
                logger.warning(
                    'Container Not Provided. Traversing the whole VC to locate the template. This might take time.')
            logger.info("Got container cluster")

            logger.info("Obtaining Host mor to put in maintenance Mode")
            host_mor = mem.getMemHost(src_dcMor, src_host, container)
            logger.info("Got Host mor")



            # Get the VM Mor Using Property Collector Method

            vm_mor = None

            """

            if container_cluster and test_vm:
                logger.debug('Finding VM %s via property collector.' % test_vm)
                vm_properties = ["name"]
                view = Propertycollector.get_container_view(si, obj_type=[vim.VirtualMachine],
                                                            container=container_cluster)
                vm_data = Propertycollector.collect_properties(si, view_ref=view,
                                                               obj_type=vim.VirtualMachine,
                                                               path_set=vm_properties,
                                                               include_mors=True, desired_vm=test_vm)

                if vm_data.get("name", None) == test_vm:
                    logger.info('VM %s found' % test_vm)
                    vm_mor = vm_data['obj']
                else:
                    logger.info('Finding VM %s failed via fast method.' % test_vm)

            if vm_mor is None:
                logger.debug('Finding VM %s via walking down the inventory. This '
                             'might take time. ' % test_vm)
                vm_mor = VCOps.find_obj(si, logger, test_vm, [vim.VirtualMachine], False)
            """
            vm_mors = None
            vm_mors = host_mor.vm

            if vm_mors is None:
                logger.error('Unable to find VM %s' % vm_mor)
                return 1
            else:
                for vm_mor in vm_mors:
                    drs_specs.append((logger, si, vm_mor))
                    tc.vmdb.append(vm_mor.name)


            logger.info("THREAD - MAIN - End of Migration Spec")

        logger.info("Starting Stat collection Pool")

        statrequired = tc.stat_enable

        logger.debug("Stats for Host that needs to plot %s" % statrequired)

        for host, dsnames in tc.host_stat_spec.items():

            # logger.debug("Monitor Spec %s , %s , %s , %s , %s" % (dc,cls,host,nic,dsnames))

            # esx_stat_collection = multiprocessing.Process(target=EsxStats.PerfData, args=(logger,statrequired, vc, vc_user, vc_pass, dc, cls, host, nic, dsnames,))
            esx_stat_collection = multiprocessing.Process(target=Esxtop.TopData, args=(logger, host,))
            esx_stat_collection.name = host
            esx_stat_collection.daemon = True
            esx_stat_collection.start()

        # Introducing Sleep to Collect Host Data First
        time.sleep(5)

        logger.info("Initiating Maintenance Mode Thread")

        host_maintenance_trigger = multiprocessing.Process(target=monitor_host_manitenenace, args=(logger, vcenter, vcenter_user, vcenter_pass, src_datacenter, container, src_host,))
        host_maintenance_trigger.name = src_host
        host_maintenance_trigger.daemon = True
        host_maintenance_trigger.start()




        print("Initiating VM Monitor")

        pool.map(drs_handler_wrapper, drs_specs)
        logger.debug('Closing virtual machine migration pool')


        logger.info("Plotting Result.")




    except vmodl.MethodFault as e:
        logger.exception('Caught vmodl fault' + str(e))

    except Exception as e:
        logger.exception('Caught exception: ' + str(e))


