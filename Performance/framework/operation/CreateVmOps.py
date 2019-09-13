__author__ = 'Yogesh Bendre'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

"""

from framework.common import TestConstants as tc
from framework.common import EsxStats as EsxStats
from framework.common import GraphPlotter as GraphPlotter
from framework.graphs import GraphFeeder as GraphFeeder
from framework.common import TaskAnalyzer as TaskAnalyzer
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

Base = declarative_base()

def v_create_handler_wrapper(args):
    return vm_create_handler(*args)

def vm_create_handler(logger, si, dcMor,host_mor, datastore,ds_name,vm_name, task_pool, task_results):

    try:

        logger.info('THREAD %s - Using clusters root resource pool.' % vm_name)
        resource_pool = host_mor.parent.resourcePool
        logger.info('THREAD %s - resource pool %s' % (vm_name, resource_pool))

        logger.info('THREAD %s - Setting folder to datacenter root folder as a datacenter has been defined' % vm_name)
        folder = dcMor.vmFolder

        datastore_path = '[' + ds_name + '] ' + vm_name
        logger.info('THREAD %s - Setting vmx path: %s' % (vm_name, datastore_path))

        # bare minimum VM shell, no disks. Feel free to edit
        vmx_file = vim.vm.FileInfo(logDirectory=None,
                                   snapshotDirectory=None,
                                   suspendDirectory=None,
                                   vmPathName=datastore_path)

        # Creating necessary specs
        logger.debug('THREAD %s - Creating createvm spec' % vm_name)

        controller = vim.vm.device.VirtualSCSIController()
        controller.sharedBus = 'noSharing'
        controller.busNumber = 1
        controller_spec = vim.vm.device.VirtualDeviceSpec()
        controller_spec.fileOperation = "create"
        controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        controller_spec.device = controller

        scsi_ctr = vim.vm.device.VirtualDeviceSpec()
        scsi_ctr.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        scsi_ctr.device = vim.vm.device.ParaVirtualSCSIController()
        scsi_ctr.device.busNumber = 1
        scsi_ctr.device.hotAddRemove = True
        scsi_ctr.device.sharedBus = 'noSharing'
        scsi_ctr.device.scsiCtlrUnitNumber = 7

        unit_number = 0

        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = "create"
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()

        disk_spec.device.backing = \
            vim.vm.device.VirtualDisk.FlatVer2BackingInfo()  # https://github.com/vmware/pyvmomi/tree/575ab56eb56f32f53c98f40b9b496c6219c161da/docs/vim/vm/device/VirtualDisk

        disk_spec.device.backing.thinProvisioned = False

        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.capacityInKB = 20 * 1024 * 1024
        disk_spec.device.controllerKey = scsi_ctr.device.key
        deviceChanges = []
        deviceChanges.append(scsi_ctr,disk_spec)

        print(deviceChanges)





        createspec = vim.vm.ConfigSpec(name=vm_name, memoryMB=16384, numCPUs=4,
                                   files=vmx_file, guestId='dosGuest',
                                   version='vmx-13',deviceChange=deviceChanges)

        print(createspec)
        logger.debug('THREAD %s - Creating createvm task' % vm_name)
        task = folder.CreateVM_Task(config=createspec, pool=resource_pool,host=host_mor)

        #task_results.append(task_pool.apply_async(TaskAnalyzer.Analyze, (logger, si, newvm, task)))
        TaskAnalyzer.Analyze(logger, si, vm_name, task)
    except vmodl.MethodFault, e:
        logger.error("Caught vmodl fault: %s" % e.msg)

    except Exception, e:
        logger.error("Caught exception: %s" % str(e))



def runTest():

    plotter = namedtuple("Host",["nic","datastore"])

    createvm_specs = []
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
            test_vm = tc.getSrcVM()
            pnic = tc.getPnic()
            vcenter = tc.getLDU()
            vcenter_user = tc.getLDULocalUser()
            vcenter_pass = tc.getLDULocalPass()

            dest_datacenter = tc.getXDatacenter()
            dest_cluster = tc.getXCluster()
            dest_host = tc.getXHost()
            dest_datastore = tc.getXDatastore()
            #powerstate = tc.getPowerState()
            vm_name = tc.getVM()
            #if 'R'
            print(vcenter)
            print("Hi There")
            tc.logger.debug("THREAD - MAIN - Instance %s specs for %s operation is %s %s %s %s %s %s %s %s" % (
            instance, vm_name, vcenter, vcenter_user,
            vcenter_pass, dest_datacenter, dest_cluster, dest_host, dest_datastore, pnic))


            #clusterhost[host] = destination_cluster

            hs = hostdetails(vcenter,vcenter_user,vcenter_pass,dest_datacenter,dest_cluster,pnic)

            hs_data[dest_host] = hs

            host_stat_spec.setdefault(dest_host, []).append(dest_datastore)

            si = mem.getMemSi(vcenter, vcenter_user, vcenter_pass)
            logger.info("Login Successful")

            dcMor = mem.getMemDatacenter(si,dest_datacenter)
            logger.info("Got Dataceneter MOR")

            logger.info("Obtaining Destination Datastore ")
            ds_mor = mem.getMemDatastore(dcMor,dest_datastore)
            logger.info("Got Destination datastore mor")

            """

            logger.info("Obtaining Destination cluster for VM")
            dest_cluster_mor = mem.getMemCluster(dcMor,destination_cluster)
            logger.info("Got destination cluster")

            """

            logger.info("Obtaining Destination Host mor")
            host_mor = mem.getMemHost(dcMor, dest_host, dest_cluster)
            logger.info("Got Destination Host mor")

            vm_mor = None
            vmdb.append(vm_name)   #New VM That needs to be monitored



            createvm_specs.append((logger, si, dcMor,host_mor, ds_mor,dest_datastore, vm_name, task_pool, task_results))
            logger.info("THREAD - End of VM Spec")

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





        pool.map(v_create_handler_wrapper, createvm_specs)
        logger.debug('Closing virtual machine creating pool')

        for running_task in task_results:
            running_task.wait()

        logger.debug('Monitoring virtual machine creation task pool')

        task_pool.close()
        task_pool.join()

        # Plotting statts

        #GraphPlotter.PlotIt(vms=vmdb,datastoreinfo=host_stat_spec,otherhostinfo=hs_data)

        GraphFeeder.DrawIt(vms=vmdb,datastoreinfo=host_stat_spec)






    except vmodl.MethodFault as e:
        logger.exception('Caught vmodl fault' + str(e))

    except Exception as e:
        logger.exception('Caught exception: ' + str(e))
