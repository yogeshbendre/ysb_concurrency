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
from framework.common.EsxStats import NetworkData, DSData
import datetime
import plotly.graph_objs as go
from collections import defaultdict, namedtuple
import traceback

vmdb = ["YSB-New-VM"]

host_stat_spec = defaultdict()
hostdetails = namedtuple('hostdetails', ['nic'])

hs_data = {}

#hs_data["sc2-hs1-b2832.eng.vmware.com"] = hostdetails("vmnic0")
hs_data["w1-hs4-n2204.eng.vmware.com"] = hostdetails("vmnic1")

stat_enable = {}
stat_enable["nic"] = True
stat_enable["ds"] = True

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
host_stat_spec.setdefault("w1-hs4-n2204.eng.vmware.com", []).append("Local-2204-1")


Base = declarative_base()

# esxhosts = ["sc2-hs1-b2832.eng.vmware.com","sc2-hs1-b2833.eng.vmware.com"]





final_data = {}



vm_data = defaultdict(list)
host_ds = defaultdict(list)
host_nic = defaultdict(list)

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
                print("Time:%s Progress: %s "%(result[0]*1000,result[1] ))
                #vm_data.setdefault(vm,[]).append({"Time":result[0]*1000 , "Progress" :result[1] })






        except Exception as e:
            print("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

        finally:
            rowVMSession.close()

    rownum = 1
    
    """




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


            print "Unique DS %s"%finalds

            for ds in finalds:


                print("Plotting for DS %s" % ds)
                results = rowEsxSession.query(DSData.time, DSData.dsread,DSData.dswrite)


                for result in results:
                    host_ds.setdefault(ds, []).append({"Time": int(result[0]) * 1000, "Read": result[1], "Write":  result[2]})



        except Exception as e:
            traceback.print_exc("THREAD -%s- Host Level Error while reading data from ESX DB %s" % (host, e))

        finally:
            rowEsxSession.close()

    """
except Exception as e:
    traceback.print_exc("THREAD -main- Error while reading data from ESX DB %s" % (e))

"""

final_data["vm"] = dict(vm_data)
final_data["nic"] = dict(host_nic)
final_data["datastore"] = dict(host_ds)

x = json.dumps(final_data,indent=4)

with open("testdata.js","w") as f:
    f.write("var testdata = %s"%x)
"""
