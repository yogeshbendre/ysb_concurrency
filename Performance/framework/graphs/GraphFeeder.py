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
import plotly
from plotly.tools import make_subplots
from framework.common.TaskAnalyzer import VMStats
from framework.common.EsxStats import NetworkData, DSData, CpuData, MemData
from html_templates import vm_mem, vm_ds, vm_only, vm_nic
import datetime
import plotly.graph_objs as go
from collections import defaultdict, namedtuple
import traceback
import json
import os
import webbrowser as wb
import time

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


def DrawIt(**kwargs):
    opsname = tc.testname
    logger = tc.logger
    vmdb = kwargs["vms"]  # A list of all VMS
    datastoreinfo = kwargs["datastoreinfo"]  # A Default Dict

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


            vm_file =  tc.testname + "_" + str(tc.test_start) + "_VM_Stat" +".html"
            nic_file = tc.testname + "_" + str(tc.test_start) + "_NIC_Stat" + ".html"
            ds_file = tc.testname + "_" + str(tc.test_start) + "_DS_Stat" + ".html"
            mem_file = tc.testname + "_" + str(tc.test_start) + "_Mem_Stat" + ".html"

            print("THREAD - GraphPlotter - The Data file name %s" % js_file)

            with open(js_file, "w") as f:
                f.write("var testdata = %s" % x)

            print("THREAD - GraphPlotter - Plotting Operation Graph ")

            nic_html = vm_nic % {"datafile": js_file , "srchost" : source_host , "desthost" : destination_host}
            mem_html = vm_mem % {"datafile": js_file, "srchost" : source_host , "desthost" : destination_host}
            ds_html = vm_ds % {"datafile": js_file, "srchost" : source_host , "desthost" : destination_host}
            vm_html = vm_only % {"datafile": js_file, "srchost" : source_host , "desthost" : destination_host}

            with open(vm_file, "w") as f:
                f.write(vm_html)
            with open(nic_file, "w") as f:
                f.write(nic_html)
            with open(ds_file, "w") as f:
                f.write(ds_html)
            with open(mem_file, "w") as f:
                f.write(mem_html)

            print("THREAD - GraphPlotter - The result is plotted at \n%s\n%s\n%s\n%s" % (vm_file,nic_file,ds_file,mem_file))

            wb.open('file://' + os.path.realpath(vm_file))
            time.sleep(5)
            wb.open_new_tab('file://' + os.path.realpath(nic_file))
            time.sleep(5)
            wb.open_new_tab('file://' + os.path.realpath(ds_file))
            time.sleep(5)
            wb.open_new_tab('file://' + os.path.realpath(mem_file))


        except Exception, e:
            logger.exception("THREAD - GraphPlotter - Error while plotting data %s" % e)




    except Exception, e:
        logger.exception("THREAD -main- Error while reading data from ESX DB %s" % (e))
