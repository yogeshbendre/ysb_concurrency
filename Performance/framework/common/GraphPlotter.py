__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
"""
import TestConstants as tc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship,sessionmaker
import plotly
from plotly.tools import make_subplots
from TaskAnalyzer import VMStats
from EsxStats import NetworkData, DSData
import datetime
import plotly.graph_objs as go
from collections import defaultdict,namedtuple
import traceback

Base = declarative_base()

def PlotIt(**kwargs):

    opsname = tc.testname
    logger = tc.logger
    vmdb = kwargs["vms"]   # A list of all VMS
    datastoreinfo = kwargs["datastoreinfo"] #A Default Dict
    otherhostinfo = kwargs["otherhostinfo"] # A Named Tuple

    try:
        # Plotting statts

        subplots = 1
        subplotnames = ["%s : Time/ Progress(%s)"%(opsname,"%")]

        for host, dsnames in datastoreinfo.items():
            uniqueds = list(set(dsnames))
            hs = otherhostinfo[host]
            nic = hs.nic

            if tc.stat_enable["nic"]:
                subplots += 1
                subplotnames.append("%s NIC %s" % (host, nic))
            if tc.stat_enable["datastore"]:
                subplots = subplots + len(uniqueds)
                for ds in uniqueds:
                    subplotnames.append("%s Datastore %s" % (host, ds))

        logger.debug("THREAD - PlotIt -  %s Subplot will be plotted with  Names %s" % (subplots, subplotnames))

        fig = make_subplots(rows=subplots, cols=1, shared_xaxes=True, subplot_titles=tuple(subplotnames))

        rownum = 1

        # This plots VM Stats

        for vm in vmdb:
            rowVMSession = None
            try:
                engine = create_engine('sqlite:///framework/db/%s.db' % vm)
                Base.metadata.bind = engine
                vdbSession = sessionmaker(bind=engine)
                rowVMSession = vdbSession()
                vmname = vm
                timerow = rowVMSession.query(VMStats.time).all()
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
            except Exception as e:
                logger.debug("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

            finally:
                rowVMSession.close()

        rowEsxSession = None

        for host, dsnames in datastoreinfo.items():
            rowEsxSession = None
            rownum += 1
            print rownum

            try:

                engine = create_engine('sqlite:///framework/db/%s.db' % host)
                Base.metadata.bind = engine
                esxDbSession = sessionmaker(bind=engine)
                rowEsxSession = esxDbSession()
                logger.debug("THREAD - %s - Plotting Network for host " %(host))

                vnic, = rowEsxSession.query(NetworkData.network).first()
                unit, = rowEsxSession.query(NetworkData.unit).first()
                timerow = rowEsxSession.query(NetworkData.time).all()
                usagerow = rowEsxSession.query(NetworkData.usage).all()
                linkspeed = rowEsxSession.query(NetworkData.maxspeed).all()

                # unitrow = rowEsxSession.query(NetworkData.unit).all()

                xAxis = [datetime.datetime.utcfromtimestamp(float(t)) for t, in timerow]
                yAxis = [value for value, in usagerow]
                #y2Axis = [value*1000 for value, in linkspeed]

                print xAxis
                print yAxis
                print "=" * 40

                ########### Plotting Nic

                fig.append_trace(go.Scatter(
                    x=xAxis,
                    y=yAxis,
                    mode='markers+lines',
                    name="%s@%s"%(vnic,unit)

                ), row=rownum, col=1

                )
                """

                fig.add_trace(go.Scatter(
                    x=xAxis,
                    y=y2Axis,
                    mode="markers+lines",
                    name="%s linkspeed@mb" % (vnic),
                ), rownum, col=1)
                
                """

                """
                fig.layout.update(
                    yaxis=go.layout.YAxis(
                                title=go.layout.yaxis.Title(
                                text="y Axis",
                                font=dict(family="Courier New, monospace", size=18, color="#7f7f7f")
                                )
                                )
                    )
                """

                finalds = []

                for row in rowEsxSession.query(DSData.datastore).distinct():
                    finalds.append(row.datastore)

                logger.debug("THREAD - %s - Unique DS %s"%(host,finalds))

                for ds in finalds:
                    rownum += 1

                    """
                    dsrows = rowEsxSession.query(DSData).filter(DSData.datastore==ds).all()
                    for dsrow in dsrows:
                        print ("%10s  %25s  %15s  %25s  %25s"%(dsrow.time,dsrow.datastore,dsrow.dsread,dsrow.dswrite,dsrow.unit))
                    """
                    logger.debug("THREAD - %s - Plotting for DS %s" % (host,ds))
                    unit, = rowEsxSession.query(DSData.unit).first()
                    timerow = rowEsxSession.query(DSData.time).filter(DSData.datastore == ds).all()
                    dsreadplot = rowEsxSession.query(DSData.dsread).filter(DSData.datastore == ds).all()
                    dswriteplot = rowEsxSession.query(DSData.dswrite).filter(DSData.datastore == ds).all()

                    xAxis = [datetime.datetime.utcfromtimestamp(float(t)) for t, in timerow]
                    y1Axis = [value for value, in dsreadplot]
                    y2Axis = [value for value, in dswriteplot]

                    logger.debug("THREAD - %s - Plotting for DS Time %s" %(host,xAxis))
                    logger.debug("THREAD - %s - Plotting for DS Read %s" % (host,y1Axis))
                    logger.debug("THREAD - %s - Plotting for DS Write %s" % (host,y2Axis))

                    fig.append_trace(go.Scatter(
                        x=xAxis,
                        y=y1Axis,
                        mode="markers+lines",
                        name="%s-read-latency @ %s" % (ds,unit),
                    ), row=rownum, col=1)

                    fig.add_trace(go.Scatter(
                        x=xAxis,
                        y=y2Axis,
                        mode="markers+lines",
                        name="%s-write-latency @ %s" % (ds,unit),
                    ), rownum, col=1)


            except Exception as e:
                logger.exception("THREAD -%s- Host Level Error while reading data from ESX DB %s" % (host, e))

            finally:
                rowEsxSession.close()

        plotly.offline.plot(fig, filename='%s_%s.html'%(tc.testname,tc.test_start))


    except Exception as e:
        logger.exception("THREAD -main- Error while reading data from ESX DB %s" % (e))









