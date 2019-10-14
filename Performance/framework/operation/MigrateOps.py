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
from framework.common import TaskAnalyzer as TaskAnalyzer
from framework.common import GraphPlotter as GraphPlotter
from framework.graphs import GraphFeeder as GraphFeeder
from framework.vcenter import VCOps, Datacenter , Propertycollector
from framework.common import  Memoized as mem
from framework.common.TaskAnalyzer import VMStats
from framework.common.EsxStats import NetworkData, DSData

from pyVmomi import vim, vmodl
from collections import defaultdict,namedtuple
import multiprocessing
import datetime
import plotly
import plotly.graph_objs as go
from plotly.tools import make_subplots

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship,sessionmaker
from sqlalchemy import create_engine
import time


logger = tc.logger
pool = tc.pool
task_pool = tc.task_pool
task_results = tc.task_results
process = tc.process


def v_motion_handler_wrapper(args):
    """
    Wrapping arround vmotion_handler
    """
    return v_motion_handler(*args)


def v_motion_handler(logger,si,template_vm,host_mor,ds_mor):
    """
    Will handle the thread handling migration of virtual machine and run post processing
    """

    #time.sleep(10) # Sleep Introduced to trigger Host Collection Stats


    if ds_mor is None:
        logger.info("No Datastore specified. Doing only Compute vMotion")

    try:

        vm_name = template_vm.name



        vm_relocate_spec = vim.VirtualMachineRelocateSpec()
        vm_relocate_spec.host = host_mor

        resource_pool = host_mor.parent.resourcePool

        vm_relocate_spec.pool = resource_pool

        if ds_mor:
            template_disks = Propertycollector.collect_template_disks(template_vm)
            vm_relocate_spec.datastore = ds_mor
            vm_relocate_spec.disk = Propertycollector.construct_locator(template_disks, ds_mor)
            print ("VM %s Host %s DS %s" % (template_vm, host_mor, ds_mor))

        logger.info("Initiating Migration of %s"%vm_name)

        task = template_vm.RelocateVM_Task(vm_relocate_spec)

        #task_results.append(task_pool.apply_async(TaskAnalyzer.Analyze,(logger,si,vm_name,task)))
        TaskAnalyzer.Analyze(logger, si, vm_name, task)



    except vmodl.MethodFault, e:
        logger.error("Caught vmodl fault: %s" % e.msg)

    except Exception, e:
        logger.error("Caught exception: %s" % str(e))





def runTest():


    migration_specs = []
    vmotionnic = {}


    #cluster host will contain the information of cluster to which the host belongs
    clusterhost = {}

    hostdetails = namedtuple('hostdetails',['vcenter', 'vcenter_user', 'vcenter_pass', 'datacenter', 'cluster', 'nic', 'disk'])

    #hs_data = {}

    try:

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

            #Source Host Parameter

            src_host = tc.getHost()
            src_nic = tc.getSrcPnic()
            src_datastore = tc.getDatastore()
            src_disk = tc.getSrcDisk()


            """

            tc.logger.debug("THREAD - MAIN - Instance %s specs for %s operation is %s %s %s %s %s %s %s %s %s" % (
            instance, test_vm, vcenter, vcenter_user,
            vcenter_pass, dest_datacenter, container, destination_cluster, host, datastore, pnic))
            """


            #clusterhost[host] = destination_cluster

            hs = hostdetails(vcenter,vcenter_user,vcenter_pass,dest_datacenter,destination_cluster,pnic,dest_disk)

            tc.hs_data[host] = hs

            #vmotionnic[host] = pnic

            tc.host_stat_spec.setdefault(host, []).append(datastore)

            # Source Host Spec for Stat Collection

            src_hs = hostdetails(vcenter, vcenter_user, vcenter_pass, src_datacenter, container, src_nic,src_disk)
            tc.hs_data[src_host] = src_hs
            tc.host_stat_spec.setdefault(src_host, []).append(src_datastore)



            si = mem.getMemSi(vcenter, vcenter_user, vcenter_pass)
            logger.info("Login Successful")

            src_dcMor = mem.getMemDatacenter(si,src_datacenter)
            logger.info("Got Source Datacenter MOR")

            logger.info("Obtaining Container cluster for VM")
            container_cluster = mem.getMemCluster(src_dcMor,container)
            if container_cluster is None:
                logger.warning('Container Not Provided. Traversing the whole VC to locate the template. This might take time.')
            logger.info("Got container cluster")

            dcMor = mem.getMemDatacenter(si, dest_datacenter)
            logger.info("Got Destination Datacenter MOR")

            logger.info("Obtaining Destination Datastore ")
            ds_mor = mem.getMemDatastore(dcMor,datastore)
            logger.info("Got Destination datastore mor")

            logger.info("Obtaining Destination Host mor")
            host_mor = mem.getMemHost(dcMor, host, destination_cluster)
            logger.info("Got Destination Host mor")

            #Get the VM Mor Using Property Collector Method

            vm_mor = None

            if container_cluster and test_vm:
                logger.debug('Finding VM %s via property collector.' % test_vm)
                vm_properties = ["name"]
                view = Propertycollector.get_container_view(si, obj_type=[vim.VirtualMachine], container=container_cluster)
                vm_data = Propertycollector.collect_properties(si, view_ref=view,
                                             obj_type=vim.VirtualMachine,
                                             path_set=vm_properties,
                                             include_mors=True, desired_vm=test_vm)

                if vm_data.get("name" , None) == test_vm:
                    logger.info('VM %s found' % test_vm)
                    vm_mor = vm_data['obj']
                else:
                    logger.info('Finding VM %s failed via fast method.' % test_vm)

            if vm_mor is None:
                logger.debug('Finding VM %s via walking down the inventory. This '
                             'might take time. ' % test_vm)
                vm_mor = VCOps.find_obj(si, logger, test_vm, [vim.VirtualMachine], False)

            if vm_mor is None:
                logger.error('Unable to find VM %s' % vm_mor)
                return 1
            else:
                tc.vmdb.append(test_vm)

            migration_specs.append((logger, si, vm_mor, host_mor, ds_mor))
            logger.info("THREAD -%s- End of VM Spec"%test_vm)

        logger.info("Starting Stat collection Pool")

        statrequired = tc.stat_enable

        logger.debug("Stats for Host that needs to plot %s"%statrequired)



        for host, dsnames in tc.host_stat_spec.items():


                        
            hs = tc.hs_data[host]


            vc = hs.vcenter
            vc_user = hs.vcenter_user
            vc_pass = hs.vcenter_pass
            dc = hs.datacenter
            nic = hs.nic
            cls = hs.cluster
            disk = hs.disk


            #logger.debug("Monitor Spec %s , %s , %s , %s , %s" % (dc,cls,host,nic,dsnames))

            #esx_stat_collection = multiprocessing.Process(target=EsxStats.PerfData, args=(logger,statrequired, vc, vc_user, vc_pass, dc, cls, host, nic, dsnames,))
            esx_stat_collection = multiprocessing.Process(target=Esxtop.TopData, args=(logger,host,))
            esx_stat_collection.name = host
            esx_stat_collection.daemon = True
            esx_stat_collection.start()

        # Introducing Sleep to Collect Host Data First
        time.sleep(10)

        pool.map(v_motion_handler_wrapper, migration_specs)
        logger.debug('Closing virtual machine migration pool')

        """
        for running_task in task_results:
            running_task.wait()
        """

        logger.debug('Monitoring virtual machine migration task pool')



        tc.HOST_METRICS_COLLECT = False



        hostplots = []
        esxhosts = []

        #hostplots.append("VM Stats (Time/ Progress %)")

        # Plotting statts

        #GraphPlotter.PlotIt(vms=vmdb, datastoreinfo=host_stat_spec, otherhostinfo=hs_data)

        #GraphFeeder.DrawIt(vms=vmdb, datastoreinfo=host_stat_spec)



        #GraphFeeder.CollectData(logger, tc.host_stat_spec, tc.hs_data, tc.vmdb)

        logger.info("Plotting Result.")




    except vmodl.MethodFault as e:
        logger.exception('Caught vmodl fault' + str(e))

    except Exception as e:
        logger.exception('Caught exception: ' + str(e))


