__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
This is my Hobby Project. There is no guarentee of delivery.

"""

import json

import os
import glob
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker
import plotly
from plotly.tools import make_subplots
from framework.common.TaskAnalyzer import VMStats
from framework.common.EsxStats import NetworkData, DSData, CpuData, MemData
import datetime
import plotly.graph_objs as go
from collections import defaultdict, namedtuple
import traceback

vmdb = ["Test-VM-25"]

host_stat_spec = defaultdict()
hostdetails = namedtuple('hostdetails', ['nic'])

hs_data = {}

#hs_data["sc2-hs1-b2832.eng.vmware.com"] = hostdetails("vmnic0")
hs_data["w1-hs4-n2215.eng.vmware.com"] = hostdetails("vmnic0")
hs_data["w1-hs4-n2201.eng.vmware.com"] = hostdetails("vmnic0")


stat_enable = {}
stat_enable["nic"] = True
stat_enable["ds"] = True
stat_enable["mem"] = True
stat_enable["cpu"] = True

"""
host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-0")
host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-0")
host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-1")
host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-1")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-1")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-0")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-0")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-1")
"""
host_stat_spec.setdefault("w1-hs4-n2215.eng.vmware.com", []).append("Local-2215-1")
host_stat_spec.setdefault("w1-hs4-n2201.eng.vmware.com", []).append("Local-2201-1")

Base = declarative_base()

# esxhosts = ["sc2-hs1-b2832.eng.vmware.com","sc2-hs1-b2833.eng.vmware.com"]





final_data = {}



final_data = {}
vm_data = defaultdict(list)
host_ds = defaultdict(list)
host_nic = defaultdict(list)
cpu_data = defaultdict(list)
mem_data = defaultdict(list)
hostcpu = {}

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


            #vmstat = []

            results = rowVMSession.query(VMStats.time,VMStats.progress)

            for result in results:
                vm_data.setdefault(vm,[]).append({"Time":result[0]*1000 , "Progress" :result[1] })






        except Exception, e:
            print("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

        finally:
            rowVMSession.close()

    rownum = 1
    





    for host, dsnames in host_stat_spec.items():
        rowEsxSession = None

        try:

            engine = create_engine('sqlite:///framework/db/%s.db' % host)
            Base.metadata.bind = engine
            esxDbSession = sessionmaker(bind=engine)
            rowEsxSession = esxDbSession()
            print("Plotting Network for host %s" % host)

            vnic, = rowEsxSession.query(NetworkData.network).first()


            # unitrow = rowEsxSession.query(NetworkData.unit).all()

            nicresults = rowEsxSession.query(NetworkData.time, NetworkData.usage)

            for nicresult in nicresults:
                time_val = int(nicresult[0]) * 1000

                host_nic.setdefault(host, []).append({"Time": time_val, "Bandwidth": nicresult[1] , "vnic" : vnic})

            finalds = []

            for row in rowEsxSession.query(DSData.datastore).distinct():
                finalds.append(row.datastore)

            print("THREAD - %s - Unique DS %s" % (host, finalds))

            for ds in finalds:
                results = rowEsxSession.query(DSData.time, DSData.dsread, DSData.dswrite, DSData.hostname,
                                              DSData.totalread, DSData.totalwrite).filter_by(datastore=ds)
                for result in results:
                    host_ds.setdefault(ds, []).append(
                        {"Time": int(result[0]) * 1000, "ReadLatency": result[1], "WriteLatency": result[2],
                         "Host": result[3], "Read": result[4], "Write": result[5]})

            cpus = []

            for row in rowEsxSession.query(CpuData.coreid).distinct():
                cpus.append(row.coreid)

            for cpu in cpus:
                results = rowEsxSession.query(CpuData).filter_by(coreid=cpu)
                for result in results:
                    cpu_data.setdefault(cpu, []).append({"Time": int(result.time) * 1000, "Usage": result.coreutil})

            hostcpu[host] = dict(cpu_data)

            memresults = rowEsxSession.query(MemData.time, MemData.usage)
            for memresult in memresults:
                mem_data.setdefault(host, []).append({"Time": int(memresult[0]) * 1000, "Usage": memresult[1]})


        except Exception, e:
            traceback.print_exc("THREAD -%s- Host Level Error while reading data from ESX DB %s" % (host, e))

        finally:
            rowEsxSession.close()




except Exception, e:
    traceback.print_exc("THREAD -main- Error while reading data from ESX DB %s" % (e))


final_data["vm"] = dict(vm_data)
final_data["nic"] = dict(host_nic)
final_data["datastore"] = dict(host_ds)
final_data["cpu"] = hostcpu
final_data["mem"] = dict(mem_data)

x = json.dumps(final_data,indent=4)

with open("testdata.js","w") as f:
    f.write("var testdata = %s"%x)
