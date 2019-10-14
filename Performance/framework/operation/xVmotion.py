__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

"""

from framework.common import TestConstants as tc
from framework.common import EsxStats as EsxStats
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


def v_motion_handler(logger,template_vm, destination_vcenter,destination_vcenter_user,destination_vcenter_pass,sslThumbprint, destination_vcenter_si,destination_hostMor,destination_datastore):
    """
    Will handle the thread handling migration of virtual machine and run post processing
    """


    if destination_datastore is None:
        logger.info("No Datastore specified. Doing only Compute vMotion")

    try:

        vm_name = template_vm.name

        # Service Locator

        #(logger,destination_vcenter,destination_vcenter_user,destination_vcenter_pass,destination_si,destination_hostMor,destination_datastore)

        url = "https://" + destination_vcenter +":443/sdk"



        service_locator = vim.ServiceLocator()
        service_locator.instanceUuid = destination_vcenter_si.content.about.instanceUuid
        service_locator.url = url
        service_locator.sslThumbprint = sslThumbprint

        creds = vim.ServiceLocatorNamePassword()
        creds.username = destination_vcenter_user
        creds.password = destination_vcenter_pass

        service_locator.credential = creds

        destination_resource_pool = destination_hostMor.parent.resourcePool

        relocatespec = vim.vm.RelocateSpec()

        relocatespec.pool = destination_resource_pool
        relocatespec.service = service_locator

        relocatespec.host = destination_hostMor


        if destination_datastore:
            template_disks = Propertycollector.collect_template_disks(template_vm)
            relocatespec.datastore = destination_datastore
            relocatespec.disk = Propertycollector.construct_locator(template_disks, destination_hostMor)
            #print ("VM %s Host %s DS %s" % (template_vm, destination_hostMor, destination_datastore))

        logger.info("Initiating Migration of %s"%vm_name)

        task = template_vm.RelocateVM_Task(relocatespec)

        #task_results.append(task_pool.apply_async(TaskAnalyzer.Analyze,(logger,si,vm_name,task)))
        TaskAnalyzer.Analyze(logger, destination_vcenter_si, vm_name, task)



    except vmodl.MethodFault, e:
        logger.error("Caught vmodl fault: %s" % e.msg)

    except Exception, e:
        logger.error("Caught exception: %s" % str(e))





def runTest():


    migration_specs = []
    vmotionnic = {}
    vmdb = []
    host_stat_spec = defaultdict(list)

    #cluster host will contain the information of cluster to which the host belongs
    clusterhost = {}

    hostdetails = namedtuple('hostdetails',['vcenter', 'vcenter_user', 'vcenter_pass', 'datacenter', 'cluster', 'nic'])

    hs_data = {}

    try:

        for instance in range(1, process + 1):
            tc.instance = instance

            test_vm = tc.getVM()
            vcenter = tc.getLDU()
            vcenter_user = tc.getLDULocalUser()
            vcenter_pass = tc.getLDULocalPass()
            src_datacenter = tc.getDatacenter()
            container = tc.getCluster()

            dest_vcenter = tc.getXLDU()
            dest_vcenter_user = tc.getXLDULocalUser()
            dest_vcenter_pass = tc.getXLDULocalPass()
            dest_vcenter_root = tc.getXLDURoot()
            dest_vcenter_root_pass = tc.getXLDURootPass()

            dest_datacenter = tc.getXDatacenter()
            destination_cluster = tc.getXCluster()


            dest_host = tc.getXHost()
            dest_datastore = tc.getXDatastore()

            pnic = tc.getPnic()


            tc.logger.debug("THREAD - MAIN - Instance %s specs for %s operation is %s %s %s %s %s %s %s %s %s" % (
            instance, test_vm, vcenter, vcenter_user,
            vcenter_pass, dest_datacenter, container, destination_cluster, dest_host, dest_datastore, pnic))

            logger.info("Getting Destination VC Thumbprint")
            thumb_print = mem.getMemThumb(dest_vcenter,dest_vcenter_root,dest_vcenter_root_pass)
            logger.info("Got Destination VC Thumbprint")


            #clusterhost[host] = destination_cluster

            hs = hostdetails(dest_vcenter,dest_vcenter_user,dest_vcenter_pass,dest_datacenter,destination_cluster,pnic)

            hs_data[dest_vcenter] = hs


            #vmotionnic[host] = pnic

            host_stat_spec.setdefault(dest_host, []).append(dest_datastore)

            si = mem.getMemSi(vcenter, vcenter_user, vcenter_pass)
            logger.info("Login Successful")

            src_dcMor = mem.getMemDatacenter(si,src_datacenter)
            logger.info("Got Source Datacenter MOR")

            logger.info("Obtaining Container cluster for VM")
            container_cluster = mem.getMemCluster(src_dcMor,container)
            if container_cluster is None:
                logger.warning('Container Not Provided. Traversing the whole VC to locate the template. This might take time.')
            logger.info("Got container cluster")

            # Get the VM Mor Using Property Collector Method

            vm_mor = None

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

            if vm_mor is None:
                logger.error('Unable to find VM %s' % vm_mor)
                return 1
            else:
                vmdb.append(test_vm)

            # Get Destination Related MORs

            x_si = mem.getMemSi(dest_vcenter, dest_vcenter_user, dest_vcenter_pass)
            logger.info("Login Successful to Destination VC")

            dest_dcMor = mem.getMemDatacenter(x_si, dest_datacenter)
            logger.info("Got Destination Datacenter MOR")


            logger.info("Obtaining Destination Datastore ")
            x_ds_mor = mem.getMemDatastore(dest_dcMor,dest_datastore)
            logger.info("Got Destination datastore mor")

            logger.info("Obtaining Destination Host mor")
            x_host_mor = mem.getMemHost(dest_dcMor, dest_host, destination_cluster)
            logger.info("Got Destination Host mor")



            # logger,template_vm, destination_vcenter,destination_vcenter_user,destination_vcenter_pass,sslThumbprint, destination_vcenter_si,destination_hostMor,destination_datastore

            #logger, vm_mor, dest_vcenter, dest_vcenter_user, dest_vcenter_pass, thumb_print, x_si,x_host_mor,x_ds_mor

            migration_specs.append((logger, vm_mor, dest_vcenter, dest_vcenter_user, dest_vcenter_pass, thumb_print, x_si,x_host_mor,x_ds_mor))
            logger.info("THREAD -%s- End of VM Spec"%test_vm)

        logger.info("Starting Stat collection Pool")

        statrequired = tc.stat_enable

        logger.debug("Stats for Host that needs to plot %s"%statrequired)



        for host, dsnames in host_stat_spec.items():
            hs = hs_data[host]
            vc = hs.vcenter
            vc_user = hs.vcenter_user
            vc_pass = hs.vcenter_pass
            dc = hs.datacenter
            nic = hs.nic
            cls = hs.cluster

            logger.debug("Monitor Spec %s , %s , %s , %s , %s" % (dc,cls,host,nic,dsnames))

            esx_stat_collection = multiprocessing.Process(target=EsxStats.PerfData, args=(logger,statrequired, vc, vc_user, vc_pass, dc, cls, host, nic, dsnames,))
            esx_stat_collection.name = host
            esx_stat_collection.daemon = True
            esx_stat_collection.start()

        pool.map(v_motion_handler_wrapper, migration_specs)
        logger.debug('Closing virtual machine migration pool')

        for running_task in task_results:
            running_task.wait()

        logger.debug('Monitoring virtual machine migration task pool')

        task_pool.close()
        task_pool.join()

        logger.info("Plotting Result.")

        hostplots = []
        esxhosts = []

        #hostplots.append("VM Stats (Time/ Progress %)")

        # Plotting statts

        #GraphPlotter.PlotIt(vms=vmdb, datastoreinfo=host_stat_spec, otherhostinfo=hs_data)

        GraphFeeder.DrawIt(vms=vmdb, datastoreinfo=host_stat_spec)




    except vmodl.MethodFault as e:
        logger.exception('Caught vmodl fault' + str(e))

    except Exception as e:
        logger.exception('Caught exception: ' + str(e))


