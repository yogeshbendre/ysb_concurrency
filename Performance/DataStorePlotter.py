__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
This is my Hobby Project. There is no guarentee of delivery.

"""


import os
import glob
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship,sessionmaker
import plotly
from plotly.tools import make_subplots
from framework.common.TaskAnalyzer import VMStats
from framework.common.EsxStats import NetworkData, DSData
import datetime
import plotly.graph_objs as go
from collections import defaultdict,namedtuple
import traceback


vmdb = ["VM-1"]


host_stat_spec = defaultdict()
hostdetails = namedtuple('hostdetails',['nic'])


hs_data = {}

hs_data["sc2-hs1-b2832.eng.vmware.com"] = hostdetails("vmnic0")
hs_data["sc2-hs1-b2833.eng.vmware.com"] = hostdetails("vmnic0")


stat_enable = {}
stat_enable["nic"] = True
stat_enable["ds"] = True


host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-0")
host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-0")
host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-1")
host_stat_spec.setdefault("sc2-hs1-b2832.eng.vmware.com", []).append("Local-32-1")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-1")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-0")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-0")
host_stat_spec.setdefault("sc2-hs1-b2833.eng.vmware.com", []).append("Local-33-1")


Base = declarative_base()

#esxhosts = ["sc2-hs1-b2832.eng.vmware.com","sc2-hs1-b2833.eng.vmware.com"]



try:
    # Plotting statts

    subplots = 1
    subplotnames = ["Clone Operation : Time/ Progress(%)"]


    for host, dsnames in host_stat_spec.items():
        uniqueds = list(set(dsnames))
        hs = hs_data[host]
        nic = hs.nic

        if stat_enable["nic"]:
            subplots += 1
            subplotnames.append("%s NIC %s" %(host,nic))
        if stat_enable["ds"]:
            subplots = subplots + len(uniqueds)
            for ds in uniqueds:
                subplotnames.append("%s Datastore %s" % (host,ds))

    specarray = []
    for i in range(subplots):
        specarray.append(5)



    print("Debug : %s Subplot will be plotted with  Names %s"%(subplots,subplotnames))

    fig = make_subplots(rows=subplots, cols=1,  shared_xaxes=True,subplot_titles=tuple(subplotnames) ,

                        vertical_spacing=0.075,
                        row_width = specarray

                        )

    rownum = 1

    #This plots VM Stats

    for vm in vmdb:
        rowVMSession = None
        try:
            engine = create_engine('sqlite:///framework/db/%s.db' % vm)
            Base.metadata.bind = engine
            vdbSession = sessionmaker(bind=engine)
            rowVMSession = vdbSession()
            vmname = vm
            timerow = rowVMSession.query(VMStats.time).all()
            print timerow
            """
            progressrow = rowVMSession.query(VMStats.progress).all()
            xAxis = [datetime.datetime.utcfromtimestamp(float(t)) for t, in timerow]
            yAxis = [value for value, in progressrow]
            print xAxis
            print yAxis
            print "=" * 40

            fig.add_trace(go.Scatter(
                x=xAxis,
                y=yAxis,
                mode="markers+lines",
                name=vmname,
            ), )
            """
        except Exception, e:
            print("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

        finally:
            rowVMSession.close()






    rowEsxSession = None


    """
    

    for host, dsnames in host_stat_spec.items():
        rowEsxSession = None
        rownum += 1
        print rownum

        try:

            engine = create_engine('sqlite:///framework/db/%s.db' % host)
            Base.metadata.bind = engine
            esxDbSession = sessionmaker(bind=engine)
            rowEsxSession = esxDbSession()
            print("Plotting Network for host %s" % host)

            vnic, = rowEsxSession.query(NetworkData.network).first()
            timerow = rowEsxSession.query(NetworkData.time).all()
            usagerow = rowEsxSession.query(NetworkData.usage).all()

            # unitrow = rowEsxSession.query(NetworkData.unit).all()

            xAxis = [datetime.datetime.utcfromtimestamp(float(t)) for t, in timerow]
            yAxis = [value for value, in usagerow]

            print xAxis
            print yAxis
            print "=" * 40

            ########### Plotting Nic

            fig.append_trace(go.Scatter(
                x=xAxis,
                y=yAxis,
                mode='markers+lines',
                name=vnic

            ), row=rownum, col=1

            )



            finalds = []



            for row in rowEsxSession.query(DSData.datastore).distinct():
                finalds.append(row.datastore)


            print "Unique DS %s"%finalds

            for ds in finalds:
                rownum += 1
                print "Ds is %s"%ds

                print("Plotting for DS %s" % ds)
                timerow = rowEsxSession.query(DSData.time).filter(DSData.datastore == ds).all()
                dsreadplot = rowEsxSession.query(DSData.dsread).filter(DSData.datastore == ds).all()
                dswriteplot = rowEsxSession.query(DSData.dswrite).filter(DSData.datastore == ds).all()

                xAxis = [datetime.datetime.utcfromtimestamp(float(t)) for t, in timerow]
                y1Axis = [value for value, in dsreadplot]
                y2Axis = [value for value, in dswriteplot]

                print ("Time %s"%xAxis)
                print ("Read %s" % y1Axis)
                print ("Write %s" % y2Axis)

                fig.append_trace(go.Scatter(
                    x=xAxis,
                    y=y1Axis,
                    mode="markers+lines",
                    name="%s-read-latency"%ds,
                ), row=rownum, col=1)

                fig.add_trace(go.Scatter(
                    x=xAxis,
                    y=y2Axis,
                    mode="markers+lines",
                    name="%s-write-latency"%ds,
                ), rownum, col=1)


        except Exception, e:
            traceback.print_exc("THREAD -%s- Host Level Error while reading data from ESX DB %s" % (host, e))

        finally:
            rowEsxSession.close()


    fig.layout.update(height=1400)
    plotly.offline.plot(fig, filename='Result.html')
    """


except Exception, e:
    traceback.print_exc("THREAD -main- Error while reading data from ESX DB %s" % ( e))









