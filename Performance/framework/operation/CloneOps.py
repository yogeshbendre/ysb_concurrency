__author__ = 'Smruti P Mohanty'
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

import time

logger = tc.logger
pool = tc.pool
task_pool = tc.task_pool
task_results = tc.task_results
process = tc.process

Base = declarative_base()

def v_clone_handler_wrapper(args):
    return vm_clone_handler(*args)

def vm_clone_handler(logger, si, vm_mor,dcMor,host_mor, datastore,newvm, task_pool, task_results):

    try:

        logger.info('THREAD %s - Using clusters root resource pool.' % newvm)
        resource_pool = host_mor.parent.resourcePool
        logger.info('THREAD %s - resource pool %s' % (newvm, resource_pool))

        logger.info('THREAD %s - Setting folder to datacenter root folder as a datacenter has been defined' % newvm)
        folder = dcMor.vmFolder

        # Creating necessary specs
        logger.debug('THREAD %s - Creating relocate spec' % newvm)
        relocate_spec = vim.vm.RelocateSpec()

        if resource_pool:
            logger.debug('THREAD %s - Resource pool found, using' % newvm)
            relocate_spec.pool = resource_pool
        if datastore:
            logger.info('THREAD %s - DS on which clone will be created %s' % (newvm,datastore.name))
            relocate_spec.datastore = datastore

        if host_mor:
            logger.info('THREAD %s - Host on which clone will be created %s' %(newvm,host_mor.name))
            relocate_spec.host = host_mor

        logger.debug('THREAD %s - Creating clone spec' % newvm)
        clone_spec = vim.vm.CloneSpec(powerOn=False, template=False, location=relocate_spec)

        logger.debug('THREAD %s - Creating clone task' % newvm)
        task = vm_mor.Clone(name=newvm, folder=folder, spec=clone_spec)

        #task_results.append(task_pool.apply_async(TaskAnalyzer.Analyze, (logger, si, newvm, task)))
        TaskAnalyzer.Analyze(logger, si, newvm, task)
    except vmodl.MethodFault, e:
        logger.error("Caught vmodl fault: %s" % e.msg)

    except Exception, e:
        logger.error("Caught exception: %s" % str(e))



def runTest():

    plotter = namedtuple("Host",["nic","datastore"])

    clone_specs = []
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
            datacenter = tc.getDatacenter()
            container = tc.getCluster()
            destination_cluster = tc.getXCluster()
            host = tc.getXHost()
            datastore = tc.getXDatastore()
            powerstate = tc.getPowerState()
            newvm = tc.getVM()

            src_host = tc.getHost()
            src_nic = tc.getSrcPnic()
            src_datastore = tc.getDatastore()




            tc.logger.debug("THREAD - MAIN - Instance %s specs for %s operation is %s %s %s %s %s %s %s %s %s" % (
            instance, test_vm, vcenter, vcenter_user,
            vcenter_pass, datacenter, container, destination_cluster, host, datastore, pnic))


            #clusterhost[host] = destination_cluster

            hs = hostdetails(vcenter,vcenter_user,vcenter_pass,datacenter,destination_cluster,pnic)
            hs_data[host] = hs

            src_hs = hostdetails(vcenter, vcenter_user, vcenter_pass, datacenter, container, src_nic)
            hs_data[src_host] = src_hs


            #vmotionnic[host] = pnic

            host_stat_spec.setdefault(host, []).append(datastore)

            host_stat_spec.setdefault(src_host, []).append(src_datastore)

            si = mem.getMemSi(vcenter, vcenter_user, vcenter_pass)
            logger.info("Login Successful")

            dcMor = mem.getMemDatacenter(si,datacenter)
            logger.info("Got Dataceneter MOR")

            logger.info("Obtaining Container cluster for VM")
            container_cluster = mem.getMemCluster(dcMor,container)
            if container_cluster is None:
                logger.warning('Container Not Provided. Traversing the whole VC to locate the template. This might take time.')
            logger.info("Got container cluster")

            logger.info("Obtaining Destination Datastore ")
            ds_mor = mem.getMemDatastore(dcMor,datastore)
            logger.info("Got Destination datastore mor")

            """

            logger.info("Obtaining Destination cluster for VM")
            dest_cluster_mor = mem.getMemCluster(dcMor,destination_cluster)
            logger.info("Got destination cluster")

            """

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
                vmdb.append(newvm)   #New VM That needs to be monitored



            clone_specs.append((logger, si, vm_mor, dcMor,host_mor, ds_mor, newvm, task_pool, task_results))
            logger.info("THREAD -%s- End of VM Spec"%test_vm)

        logger.info("Starting Stat collection Pool")

        statrequired = tc.stat_enable

        logger.debug("Stats for Host that needs to plot %s"%statrequired)

        """

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
        """


        #time.sleep(5)  # Introducing Sleep to Collect Host Data First

        pool.map(v_clone_handler_wrapper, clone_specs)
        logger.debug('Closing virtual machine cloning pool')

        for running_task in task_results:
            running_task.wait()

        logger.debug('Monitoring virtual machine migration task pool')

        task_pool.close()
        task_pool.join()

        # Plotting statts

        #GraphPlotter.PlotIt(vms=vmdb,datastoreinfo=host_stat_spec,otherhostinfo=hs_data)

        #GraphFeeder.DrawIt(vms=vmdb,datastoreinfo=host_stat_spec)






    except vmodl.MethodFault as e:
        logger.exception('Caught vmodl fault' + str(e))

    except Exception as e:
        logger.exception('Caught exception: ' + str(e))
