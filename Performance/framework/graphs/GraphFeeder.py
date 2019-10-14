__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
"""
from framework.common import TestConstants as tc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker

from framework.common.EsxStats import NetworkData, DSData, CpuData, MemData
from html_templates import vm_mem, vm_ds, vm_only, vm_nic

import os
import webbrowser as wb

import warnings
import pysftp
warnings.filterwarnings(action='ignore',module='.*paramiko.*')
from time import strptime, strftime, mktime, gmtime
import shutil
from framework.common import TestConstants as tc
from collections import OrderedDict, namedtuple, defaultdict
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import time

import multiprocessing
import glob
import re
import json
from framework.vcenter import Datacenter, Cluster
from framework.common import customssh
from framework.common.TaskAnalyzer import VMStats

Base = declarative_base()

final_data = {}
vm_data = defaultdict(list)
host_ds = defaultdict(list)
host_nic = defaultdict(list)
cpu_data = defaultdict(list)
mem_data = defaultdict(list)
hostcpu = {}


source_host = tc.getHost()
destination_host = tc.getXHost()
statrequired = tc.stat_enable


def DrawIt(**kwargs):
    opsname = tc.testname
    logger = tc.logger
    vmdb = kwargs["vms"]  # A list of all VMS
    datastoreinfo = kwargs["datastoreinfo"]  # A Default Dict

    statrequired = tc.stat_enable

    dscollection = statrequired.get("datastore", False)
    niccollection = statrequired.get("nic", False)
    diskcollection = statrequired.get("disk", False)
    cpucollection = statrequired.get("cpu", False)
    memcollection = statrequired.get("mem", False)

    try:
        # Plotting statts
        # This plots VM Stats

        for vm in vmdb:
            rowVMSession = None
            try:
                engine = create_engine('sqlite:///framework/db/%s.db' % vm)
                Base.metadata.bind = engine
                vdbSession = sessionmaker(bind=engine)
                rowVMSession = vdbSession()
                vmname = vm
                results = rowVMSession.query(VMStats.time, VMStats.progress)

                for result in results:
                    vm_data.setdefault(vm, []).append({"Time": result[0] * 1000, "Progress": result[1]})

            except Exception, e:
                logger.debug("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

            finally:
                rowVMSession.close()

        rowEsxSession = None

        for host, dsnames in datastoreinfo.items():
            rowEsxSession = None

            try:

                engine = create_engine('sqlite:///framework/db/%s.db' % host)
                Base.metadata.bind = engine
                esxDbSession = sessionmaker(bind=engine)
                rowEsxSession = esxDbSession()
                logger.debug("THREAD - %s - Plotting Network for host " % (host))

                vnic, = rowEsxSession.query(NetworkData.network).first()
                unit, = rowEsxSession.query(NetworkData.unit).first()
                nicresults = rowEsxSession.query(NetworkData.time, NetworkData.usage, NetworkData.sent,
                                                 NetworkData.received)
                maxspeed = rowEsxSession.query(NetworkData.maxspeed).first()

                # Changes

                for nicresult in nicresults:
                    time_val = int(nicresult[0]) * 1000
                    host_nic.setdefault(host, []).append(
                        {"Time": time_val, "Bandwidth": nicresult[1] * 0.008, "vnic": vnic, "vnicmax": maxspeed,
                         "Transmitted": nicresult[2] * 0.008, "Received": nicresult[3] * 0.008})

                finalds = []

                for row in rowEsxSession.query(DSData.datastore).distinct():
                    finalds.append(row.datastore)

                logger.debug("THREAD - %s - Unique DS %s" % (host, finalds))

                if dscollection:

                    for ds in finalds:
                        results = rowEsxSession.query(DSData.time, DSData.dsread, DSData.dswrite, DSData.hostname,
                                                      DSData.totalread, DSData.totalwrite).filter_by(datastore=ds)
                        for result in results:
                            host_ds.setdefault(ds, []).append(
                                {"Time": int(result[0]) * 1000, "ReadLatency": result[1], "WriteLatency": result[2],
                                 "Host": result[3], "Read": result[4], "Write": result[5]})

                cpus = []

                if cpucollection:

                    for row in rowEsxSession.query(CpuData.coreid).distinct():
                        cpus.append(row.coreid)

                    for cpu in cpus:
                        results = rowEsxSession.query(CpuData).filter_by(coreid=cpu)
                        for result in results:
                            cpu_data.setdefault(cpu, []).append(
                                {"Time": int(result.time) * 1000, "Usage": result.coreutil / 100})

                    hostcpu[host] = dict(cpu_data)


                memresults = rowEsxSession.query(MemData.time, MemData.usage)
                for memresult in memresults:
                    #logger.debug("The memory stat is Time %s Usage %s" % (int(memresult[0]) * 1000, memresult[1] / 100))
                    mem_data.setdefault(host, []).append(
                        {"Time": int(memresult[0]) * 1000, "Usage": memresult[1] / 100})


            except Exception, e:
                logger.exception("THREAD -%s- Host Level Error while reading data from ESX DB %s" % (host, e))

            finally:
                rowEsxSession.close()

        try:
            final_data["vm"] = dict(vm_data)
            final_data["nic"] = dict(host_nic)
            final_data["datastore"] = dict(host_ds)
            final_data["cpu"] = hostcpu
            final_data["mem"] = dict(mem_data)

            x = json.dumps(final_data, indent=4)

            js_file = tc.testname + "_" + str(tc.test_start) + ".js"

            ds_file = None

            vm_file =  tc.testname + "_" + str(tc.test_start) + "_VM_Stat" +".html"
            nic_file = tc.testname + "_" + str(tc.test_start) + "_NIC_Stat" + ".html"

            mem_file = tc.testname + "_" + str(tc.test_start) + "_Mem_Stat" + ".html"

            if dscollection:
                ds_file = tc.testname + "_" + str(tc.test_start) + "_DS_Stat" + ".html"

            print("THREAD - GraphPlotter - The Data file name %s" % js_file)

            with open(js_file, "w") as f:
                f.write("var testdata = %s" % x)

            print("THREAD - GraphPlotter - Plotting Operation Graph ")

            ds_html = None

            nic_html = vm_nic % {"datafile": js_file , "srchost" : source_host , "desthost" : destination_host}
            mem_html = vm_mem % {"datafile": js_file, "srchost" : source_host , "desthost" : destination_host}
            if dscollection:
                ds_html = vm_ds % {"datafile": js_file, "srchost" : source_host , "desthost" : destination_host}
            vm_html = vm_only % {"datafile": js_file, "srchost" : source_host , "desthost" : destination_host}

            with open(vm_file, "w") as f:
                f.write(vm_html)
            with open(nic_file, "w") as f:
                f.write(nic_html)
            if dscollection:
                with open(ds_file, "w") as f:
                    f.write(ds_html)

            with open(mem_file, "w") as f:
                f.write(mem_html)

            print("THREAD - GraphPlotter - The result is plotted at \n%s\n%s\n%s\n%s" % (vm_file,nic_file,ds_file,mem_file))

            wb.open('file://' + os.path.realpath(vm_file))
            time.sleep(5)
            wb.open_new_tab('file://' + os.path.realpath(nic_file))
            time.sleep(5)
            if dscollection:
                wb.open_new_tab('file://' + os.path.realpath(ds_file))
                time.sleep(5)
            wb.open_new_tab('file://' + os.path.realpath(mem_file))


        except Exception, e:
            logger.exception("THREAD - GraphPlotter - Error while plotting data %s" % e)




    except Exception, e:
        logger.exception("THREAD -main- Error while reading data from ESX DB %s" % (e))


def CollectData(logger, host_stat_spec, hs_data, vmdb):
    for host, dsnames in host_stat_spec.items():
        hs = hs_data[host]
        vc = hs.vcenter
        vc_user = hs.vcenter_user
        vc_pass = hs.vcenter_pass
        dc = hs.datacenter
        nic = hs.nic
        cls = hs.cluster
        hba = hs.disk

        # Work on esxtop files...

        dscollection = statrequired.get("datastore", False)
        niccollection = statrequired.get("nic", False)
        diskcollection = statrequired.get("disk", False)
        cpucollection = statrequired.get("cpu", False)
        memcollection = statrequired.get("mem", False)

        threadname = multiprocessing.current_process().name
        si = Datacenter.Login(logger, vc, vc_user, vc_pass, port=443)
        logger.info("Login Successful")

        dcMor = Datacenter.GetDatacenter(name=dc, si=si)
        logger.info("Got Dataceneter MOR")

        linkspeed = None
        hsMor = Cluster.GetHostInClusters(dcMor, host, clusterNames=[cls])
        iteration = 1
        hostPnics = hsMor.config.network.pnic
        for hostPnic in hostPnics:
            if hostPnic.device == nic:
                linkspeed = hostPnic.linkSpeed.speedMb
                logger.debug("THREAD -%s- Link Speed is  %s" % (threadname, linkspeed))

        dirpath = os.path.join(host)
        logger.debug("Removing Directory %s" % host)
        if os.path.exists(host) and os.path.isdir(host):
            shutil.rmtree(host)

        print "Creating Directory Host"
        os.mkdir(host)

        srv = pysftp.Connection(host=host, username="root", password="ca$hc0w")

        files = srv.listdir(remotepath="/tmp")

        for file in files:
            if "conc" in file:
                try:
                    print "Gettig file %s" % file
                    srv.get("/tmp/%s" % file, "%s/%s" % (host, file))
                    print "Got file %s" % file
                except Exception, e:
                    print "Exception %s" % e

        srv.close()

        concfiles = (glob.glob("%s/conc*" % host))
        concfiles.sort()

        for conc_file in concfiles:
            print conc_file

            with open(conc_file, "r") as f:
                line = f.readline()

                i = 0

                tx = 0
                rx = 0
                disk_read = 0
                disk_write = 0
                driverLatency = 0
                kernelLatency = 0
                mem = 0

                tx_pattern = re.compile('vSwitch\d:\d+:%s\)\\\MBits Transmitted/sec' % nic)
                rx_pattern = re.compile('vSwitch\d:\d+:%s\)\\\MBits Received/sec' % nic)
                disk_read_pattern = re.compile('Disk\s+Adapter\(%s\)\\\MBytes\s+Read/sec' % hba)
                disk_write_pattern = re.compile('Disk\s+Adapter\(%s\)\\\MBytes Written/sec' % hba)
                driver_latency_pattern = re.compile('Disk Adapter\(%s\)\\\Average Driver MilliSec/Command' % hba)
                kernel_latency_pattern = re.compile('Disk Adapter\(%s\)\\\Average Kernel MilliSec/Command' % hba)
                memory_pattern = re.compile('\\\Memory\\\Kernel MBytes')

                for item in line.split(","):

                    if re.search(tx_pattern, item):
                        # print str(i) +  " :  "  + item
                        tx = i
                    elif re.search(rx_pattern, item):
                        # print str(i) + " :  " + item
                        rx = i
                    elif re.search(disk_read_pattern, item):
                        # print str(i) + " :  " + item
                        disk_read = i
                    elif re.search(disk_write_pattern, item):
                        # print str(i) + " :  " + item
                        disk_write = i
                    elif re.search(driver_latency_pattern, item):
                        # print str(i) + " :  " + item
                        driverLatency = i
                    elif re.search(kernel_latency_pattern, item):
                        # print str(i) + " :  " + item
                        kernelLatency = i
                    elif re.search(memory_pattern, item):
                        # print str(i) + " :  " + item
                        mem = i

                    i += 1

                line = f.readline()
                arr = line.split(",")

                dt = arr[0].strip('"')
                target_timestamp = strptime(dt, '%m/%d/%Y %H:%M:%S')
                mktime_epoch = int(mktime(target_timestamp))

                tx_bw = float(arr[tx].strip('"'))
                rx_bw = float(arr[rx].strip('"'))
                total_bw = tx_bw + rx_bw
                disk_r = float(arr[disk_read].strip('"'))
                disk_w = float(arr[disk_write].strip('"'))
                total_disk_latency = float(arr[driverLatency].strip('"')) + float(arr[kernelLatency].strip('"'))
                mem_used = float(arr[mem].strip('"'))

                """
                print "Time : %s "%mktime_epoch
                print "NIC Sent --- %s "%tx_bw
                print "NIC Got --- %s "%rx_bw

                print "Disk   Latency --- %s "%total_latency
                print "Memory used --- %s "%mem_used


                print "Data  Read --- %s " % disk_r
                print "Data  Write --- %s " % disk_w
                """

                host_nic.setdefault(host, []).append(
                    {"Time": mktime_epoch, "Bandwidth": total_bw, "vnic": nic, "vnicmax": linkspeed,
                     "Transmitted": tx_bw, "Received": rx_bw})

                host_ds.setdefault(host, []).append(
                    {"Time": mktime_epoch, "ReadLatency": total_disk_latency,
                     "Host": host, "Read": disk_r, "Write": disk_w})

                mem_data.setdefault(host, []).append(
                    {"Time": mktime_epoch, "Usage": mem_used})

    for vm in vmdb:
        rowVMSession = None
        try:
            engine = create_engine('sqlite:///framework/db/%s.db' % vm)
            Base.metadata.bind = engine
            vdbSession = sessionmaker(bind=engine)
            rowVMSession = vdbSession()
            vmname = vm
            results = rowVMSession.query(VMStats.time, VMStats.progress)

            for result in results:
                vm_data.setdefault(vm, []).append({"Time": result[0] * 1000, "Progress": result[1]})

        except Exception, e:
            logger.debug("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

        finally:
            rowVMSession.close()

    final_data["vm"] = dict(vm_data)
    final_data["nic"] = dict(host_nic)
    final_data["disk"] = dict(host_ds)
    final_data["mem"] = dict(mem_data)

    x = json.dumps(final_data, indent=4)

    js_file = tc.testname + "_" + str(tc.test_start) + ".js"

    print("THREAD - GraphPlotter - The Data file name %s" % js_file)

    with open(js_file, "w") as f:
        f.write("var testdata = %s" % x)

    print("THREAD - GraphPlotter - Plotting Operation Graph ")





