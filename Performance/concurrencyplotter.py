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
import glob
import re
import json
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker

from framework.vcenter import Datacenter, Cluster
from framework.common import customssh
from framework.common.TaskAnalyzer import VMStats
import logging
from framework.graphs.html_templates  import vm_mem, vm_ds, vm_only, vm_nic
import time

import datetime
import pytz

from multiprocessing.dummy import Pool as ThreadPool

pool = ThreadPool(8)
dscollection = False
final_data = {}
vm_data = defaultdict(list)
host_ds = defaultdict(list)
host_disk = defaultdict(list)
host_nic = defaultdict(list)
cpu_data = defaultdict(list)
mem_data = defaultdict(list)

utc = pytz.UTC

epoch = datetime.datetime.utcfromtimestamp(0)
begin = epoch.replace(tzinfo=utc)

def generate_logger(log_file=None):
    log_level = logging.DEBUG
    fh = None
    FORMAT = "%(asctime)s %(levelname)s %(message)s"
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    # Reset the logger.handlers if it already exists.
    if logger.handlers:
        logger.handlers = []
    formatter = logging.Formatter(FORMAT)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


logger = generate_logger(log_file="ESXTopData.txt")

Base = declarative_base()

#vmdb = ["VM-1" , "VM-2", "VM-3", "VM-4", "VM-5", "VM-6","VM-7" , "VM-8", "VM-9", "VM-10", "VM-11", "VM-12", "VM-13", "VM-14", "VM-15", "VM-16"]

#vmdb = ["VM-14" ,  "VM-7",  "VM-10", "VM-13", "VM-5", "VM-4", "VM-6", "VM-16"]
vmdb = ["Test-VM-Y1" ,  "Test-VM-Y2",  "Test-VM-Y3", "Test-VM-Y4", "Test-VM-Y5", "Test-VM-Y6", "Test-VM-Y7", "Test-VM-Y8"]

hs_data = {}
hostdetails = namedtuple('hostdetails',['vcenter', 'vcenter_user', 'vcenter_pass', 'datacenter', 'cluster', 'nic', 'disk'])

"""jj
hs1 = hostdetails("10.172.109.23","Administrator@skyscraper.local","Admin!23","Datacenter4","cloud_cluster_6","vmnic1","vmhba2")
hs2 = hostdetails("10.172.109.23","Administrator@skyscraper.local","Admin!23","Datacenter4","cloud_cluster_6","vmnic1","vmhba2")

#src = "w1-hs4-n2203.eng.vmware.com"
#dest = "w1-hs4-n2205.eng.vmware.com"
src = "w1-hs4-n2213.eng.vmware.com"
dest = "w1-hs4-n2216.eng.vmware.com"

"""

hs1 = hostdetails("10.199.24.1","Administrator@vsphere.local","Admin!23","Datacenter3","cls","vmnic1","vmhba64")
hs2 = hostdetails("10.199.24.1","Administrator@vsphere.local","Admin!23","Datacenter3","cls","vmnic1","vmhba64")

src = "10.199.105.5"
dest = "10.199.105.9"

hs_data[src] = hs1
hs_data[dest] = hs2

def file_handler_wrapper(args):
    return getFiles(*args)


def getFiles(host, file):
    srv = None
    try:
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        srv = pysftp.Connection(host=host, username="root", password="ca$hc0w", cnopts=cnopts)
        print "Gettig file %s" % file
        srv.get("/tmp/%s" % file, "%s/%s" % (host, file))
        print "Got file %s" % file
        time.sleep(1)
    except Exception,e:
        print str(e)
    finally:
        if srv:
            srv.close()





for host,details in hs_data.iteritems():



    hs = hs_data[host]
    vc = hs.vcenter
    vc_user = hs.vcenter_user
    vc_pass = hs.vcenter_pass
    dc = hs.datacenter
    nic = hs.nic
    cls = hs.cluster
    hba = hs.disk

    # Work on esxtop files...
    linkspeed = 10000

    """

    si = Datacenter.Login(logger, vc, vc_user, vc_pass, port=443)
    print("Login Successful")

    dcMor = Datacenter.GetDatacenter(name=dc, si=si)
    print("Got Dataceneter MOR")

    linkspeed = None
    hsMor = Cluster.GetHostInClusters(dcMor, host, clusterNames=[cls])
    iteration = 1
    hostPnics = hsMor.config.network.pnic
    for hostPnic in hostPnics:
        if hostPnic.device == nic:
            linkspeed = hostPnic.linkSpeed.speedMb
            print("THREAD -%s- Link Speed is  %s" % (host, linkspeed))

    """


    
    dirpath = os.path.join(host)
    
    print("Removing Directory %s" % host)
    if os.path.exists(host) and os.path.isdir(host):
        shutil.rmtree(host)
        

    print "Creating Directory Host"
    os.mkdir(host)

    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    srv = pysftp.Connection(host=host, username="root", password="ca$hc0w", cnopts=cnopts)

    files = srv.listdir(remotepath="/tmp")


    for file in files:
        if "conc" in file:
            try:
                print "Gettig file %s" % file
                srv.get("/tmp/%s" % file, "%s/%s" % (host, file))
                print "Got file %s" % file
                time.sleep(1)
            except Exception, e:
                print "Exception %s" % e


    srv.close()



    """
    
    file_spec = []
    for file in files:
        if "conc" in file:
            file_spec.append((host,file))

    print("Initiating File get for host %s "%host)

    pool.map(file_handler_wrapper, file_spec)
    logger.debug('Closing file get  pool for host %s'%host)

    """
    
    time.sleep(5)



    concfiles = (glob.glob("%s/conc*" % host))
    concfiles.sort(key=lambda f: int(filter(str.isdigit, f)))

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
            #print dt
            #target_timestamp = strptime(dt, '%m/%d/%Y %H:%M:%S')
            target_timestamp = datetime.datetime.strptime(dt, '%m/%d/%Y %H:%M:%S')
            ts = target_timestamp.replace(tzinfo=utc)
            #mktime_epoch = int(mktime(target_timestamp)))
            mktime_epoch = (ts - begin).total_seconds()


            tx_bw = float(arr[tx].strip('"'))
            rx_bw = float(arr[rx].strip('"'))
            total_bw = tx_bw + rx_bw
            disk_r = float(arr[disk_read].strip('"'))
            disk_w = float(arr[disk_write].strip('"'))
            total_disk_latency = float(arr[driverLatency].strip('"')) + float(arr[kernelLatency].strip('"'))
            mem_used = float(arr[mem].strip('"'))


            host_nic.setdefault(host, []).append(
                {"Time": mktime_epoch * 1000.0, "Bandwidth": total_bw, "vnic": nic, "vnicmax": linkspeed,
                 "Transmitted": tx_bw, "Received": rx_bw})

            host_disk.setdefault(host, []).append(
                {"Time": mktime_epoch * 1000.0, "TotalLatency": total_disk_latency,
                 "Host": host, "Read": disk_r, "Write": disk_w})

            mem_data.setdefault(host , []).append(
                {"Time": mktime_epoch* 1000.0, "Usage": mem_used})




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
            vm_data.setdefault(vm, []).append({"Time": result[0] , "Progress": result[1]})

    except Exception, e:
        print("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

    finally:
        rowVMSession.close()

final_data["vm"] = dict(vm_data)
final_data["nic"] = dict(host_nic)
final_data["disk"] = dict(host_disk)
final_data["datastore"] = dict(host_ds)
final_data["mem"] = dict(mem_data)

x = json.dumps(final_data, indent=4)

#print str(x)



js_file = "z_Datafile.js"

print("THREAD - GraphPlotter - The Data file name %s" % js_file)

with open(js_file, "w") as f:
    f.write("var testdata = %s" % x)


print("THREAD - GraphPlotter - Plotting Operation Graph ")

ds_html = None

nic_html = vm_nic % {"datafile": js_file , "srchost" : src , "desthost" : dest}
mem_html = vm_mem % {"datafile": js_file, "srchost" : src , "desthost" : dest}
if dscollection:
    ds_html = vm_ds % {"datafile": js_file, "srchost" : src , "desthost" : dest}
vm_html = vm_only % {"datafile": js_file, "srchost" : src , "desthost" : dest}

vm_file = "z_vm.html"
nic_file = "z_nic.html"
ds_file = "z_ds.html"
mem_file = "z_mem.html"

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




