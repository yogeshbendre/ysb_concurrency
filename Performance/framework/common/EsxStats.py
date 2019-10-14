__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

"""
from collections import OrderedDict, namedtuple, defaultdict
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


import argparse
from pyVmomi import vim
import getpass
import atexit
import sys
import ssl
from pyVim.connect import SmartConnect, Disconnect
from datetime import datetime, timedelta, tzinfo
import copy
import time
from dateutil.parser import parse
import sys, traceback
import multiprocessing

from framework.vcenter import Datacenter, Cluster

import sys

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship,sessionmaker
from sqlalchemy import create_engine,Table, Column, Integer, String, MetaData , Float
import os


Base = declarative_base()

class NetworkData(Base):
    __tablename__ = 'networktable'
    id = Column(Integer, primary_key=True)
    time = Column(String(20))
    network = Column(String(40))
    usage = Column(Integer)
    unit = Column(String(5))
    maxspeed = Column(Integer)
    sent = Column(Integer)
    received = Column(Integer)


class DSData(Base):
    __tablename__ = 'datastoretable'
    id = Column(Integer, primary_key=True)
    time = Column(String(20))
    hostname = Column(String(80))
    datastore = Column(String(80))
    dsread = Column(Integer)
    dswrite = Column(Integer)
    unit = Column(String(5))
    totalread = Column(Integer)
    totalwrite = Column(Integer)

class MemData(Base):
    __tablename__ = 'memtable'
    id = Column(Integer, primary_key=True)
    time = Column(String(20))
    usage = Column(Float)

class CpuData(Base):
    __tablename__ = 'cputable'
    id = Column(Integer, primary_key=True)
    time = Column(String(20))
    coreid = Column(Integer)
    coreutil = Column(Float)
    


def createDB(engine):
    Base.metadata.create_all(engine)



def remove_db(engine,db_name):
    Base.metadata.drop_all(engine)
    os.remove(db_name)


def add_row(iteration,type,DBSession,time,**kwargs):
    session = None
    try:
        session = DBSession()
        if type == "network":
            storestat = NetworkData(time=time,network=kwargs["name"],usage=kwargs["usage"],unit = kwargs["unit"],maxspeed = kwargs["maxspeed"],
                                    sent= kwargs["sent"] , received =  kwargs["received"])
            session.add(storestat)
        elif type == "datastore":
            storestat = DSData(time=time,hostname=kwargs["hostname"],datastore=kwargs["name"],dsread=kwargs["dsread"],dswrite=kwargs["dswrite"],
                               unit = kwargs["unit"], totalread=kwargs["totalread"], totalwrite = kwargs["totalwrite"])
            session.add(storestat)
        elif type == "cpu":
            storestat = CpuData(time=time,coreid=kwargs["coreid"],coreutil = kwargs["coreutil"])
            session.add(storestat)
        elif type == "mem":
            storestat = MemData(time=time,usage=kwargs["usage"])
            session.add(storestat)

        session.commit()
    except Exception, e:
        session.rollback()
        print("THREAD -%s- Error while writing iteration %s data to DB %s" % ("DB-ENTRY", iteration, e))
    finally:
        session.close()

def PerfData(logger,statrequired,vc,username,password,datacenter,cluster,hostName,pnic,datastores = []):
    """
    @param si:  Service Instance of the vCenter in which the Host Reside.
    @param host: Host MOR Object
    @param pnic: The physical nic that needs to be monitored
    @param datastores: An Array of Datastores
    @return: An Ordered Hash Object which contains Performance data
    """
    dscollection = statrequired.get("datastore",False)
    niccollection = statrequired.get("nic", False)
    diskcollection = statrequired.get("disk", False)
    cpucollection = statrequired.get("cpu", False)
    memcollection = statrequired.get("mem", False)

    threadname = multiprocessing.current_process().name
    si = Datacenter.Login(logger,vc, username, password, port=443)
    logger.info("Login Successful")

    dcMor = Datacenter.GetDatacenter(name=datacenter, si=si)
    logger.info("Got Dataceneter MOR")

    #Create DB

    try:
        engine = create_engine('sqlite:///framework/db/%s.db' % hostName)
        #remove_db(engine, db_name)
        createDB(engine)
        logger.info("Created DB Successfully.")
        Base.metadata.bind = engine
        DBSession = sessionmaker(bind=engine)
    except Exception,e:
        logger.exception("Error while Creating DB %s"%e)
        raise


    try:
        linkspeed= None
        host = Cluster.GetHostInClusters(dcMor, hostName, clusterNames=[cluster])
        iteration = 1
        hostPnics = host.config.network.pnic
        for hostPnic in hostPnics:
            if hostPnic.device == pnic:
                linkspeed = hostPnic.linkSpeed.speedMb
                logger.debug("THREAD -%s- Link Speed is  %s" % (threadname, linkspeed))

        SUMMARY_INTERVALID = 1 * 30
        hostName = host.name
        content = si.RetrieveContent()
        perfMgr = content.perfManager

        dataStoreIds = {}

        datastoreMors = host.datastore
        for datastoreMor in datastoreMors:
            dsName = datastoreMor.name
            if dsName in datastores:
                datastore_id = datastoreMor.info.url.split('/')[-2]
                dataStoreIds[datastore_id] = dsName

        logger.debug("THREAD -%s- Datastore IDs %s"%(threadname,dataStoreIds) )

        metricIds = []
        idToNameMap = {}
        nameToIdMap = {}

        perfCounters = perfMgr.perfCounter

        STATS_TO_QUERY = []
        for cntrInfo in perfCounters:
            statGroup = cntrInfo.groupInfo.key
            statName = statGroup + "." + cntrInfo.nameInfo.key
            enabled = True if cntrInfo.key >= 0 else cntrInfo.enabled
            idToNameMap[cntrInfo.key] = (statName, enabled, cntrInfo.unitInfo.label)
            nameToIdMap[statName] = cntrInfo.key

            if cntrInfo.key < 0:
                STATS_TO_QUERY.append(statName)

        #summarySpecs = []


        """

        hostQuerySpec = vim.PerformanceManager.QuerySpec()
        hostQuerySpec.entity = host
        hostQuerySpec.intervalId = SUMMARY_INTERVALID
        hostQuerySpec.format = vim.PerformanceManager.Format.csv
        hostQuerySpec.metricId = metricIds
        summarySpecs.append(hostQuerySpec)
        
        

        querySpecs = copy.deepcopy(summarySpecs)

        for spec in querySpecs:
            # real-time interval
            spec.intervalId = 20
            # we need only one sample - the last one
            spec.maxSample = 1
            # Request Format.normal - we don't want to convert string to int64
            spec.format = vim.PerformanceManager.Format.normal
            
        """

        loop = True
        tzinfos = {"UTC": 0}

        statCounter = 0

        while True:

            querySpecs = None

            logger.info("THREAD -%s- %s host stats collection iteration %s"%(threadname,hostName,iteration))
            iteration +=1
            ds_unit = None
            collectionTime = si.CurrentTime()
            startTime = parse(str(collectionTime), tzinfos=tzinfos).strftime('%s')


            logger.info("* " * 10)
            logger.debug("Stat collection Instance %s Begins " % iteration)
            logger.info("* " * 10)

            esx_data = defaultdict(list)
            esx_nic_data = {}
            esx_ds_data = {}

            summarySpecs = []

            hostQuerySpec = vim.PerformanceManager.QuerySpec()
            hostQuerySpec.entity = host
            hostQuerySpec.intervalId = SUMMARY_INTERVALID
            hostQuerySpec.format = vim.PerformanceManager.Format.csv
            hostQuerySpec.metricId = metricIds
            hostQuerySpec.endTime = collectionTime
            summarySpecs.append(hostQuerySpec)

            querySpecs = copy.deepcopy(summarySpecs)



            for spec in querySpecs:
                # real-time interval
                spec.intervalId = 20
                # we need only one sample - the last one
                spec.maxSample = 1
                # Request Format.normal - we don't want to convert string to int64
                spec.format = vim.PerformanceManager.Format.normal

            queryResult = perfMgr.QueryStats(querySpecs)


            for entityMetric in queryResult:
                statCounter +=1

                for series in entityMetric.value:

                    counterId = series.id.counterId
                    instanceStr = series.id.instance
                    statName = idToNameMap[counterId][0]
                    entity = entityMetric.entity
                    unit = idToNameMap[counterId][2]
                    statValue = series.value[-1]
                    if iteration in [5,6]:
                        pass
                        #logger.debug("Stat Name: %s,  Instance: %s, Value %s, Unit : %s"%(statName,instanceStr,statValue,unit))
                    if niccollection and statName == "net.usage" and instanceStr == pnic:
                        #logger.debug("statCounter=%s, name=%s, usage=%s, maxspeed=%s"%(statCounter,instanceStr,statValue,linkspeed))
                        # add_row(iteration,"network",DBSession,startTime,name=instanceStr,usage=statValue,unit=unit,maxspeed=linkspeed)
                        #logger.debug("Iteration: %s , Net Usage: %s"%(iteration,statValue))
                        #esx_nic_data.setdefault(pnic,[]).append("usage:%s"%unit)
                        #esx_nic_data.setdefault(pnic, []).append("unit:%s" % statValue)
                        esx_nic_data["unit"] = unit
                        esx_nic_data["usage"] = statValue
                    if niccollection and statName == "net.bytesTx" and instanceStr == pnic:
                        #logger.debug("Iteration: %s , Net Tx: %s" % (iteration, statValue))
                        #esx_nic_data.setdefault(pnic,[]).append("Tx:%s"%statValue)
                        esx_nic_data["Tx"] = statValue
                    if niccollection and statName == "net.bytesRx" and instanceStr == pnic:
                        #logger.debug("Iteration: %s , Net Rx: %s" % (iteration, statValue))
                        esx_nic_data["Rx"] = statValue
                        #esx_nic_data.setdefault(pnic,[]).append("Rx:%s"%statValue)



                    #Data Store Collection

                    if dscollection and statName == "datastore.totalReadLatency" and instanceStr in dataStoreIds.keys():
                        #logger.debug("statCounter=%s, instance=%s , statValue= %s" % (statCounter, instanceStr, statValue))
                        esx_data.setdefault(dataStoreIds[instanceStr], []).append("read_latency:%s"%statValue)
                        ds_unit = unit
                        #esx_data["read_latency"] = statValue
                    if dscollection and statName == "datastore.totalWriteLatency" and instanceStr in dataStoreIds.keys():
                        #logger.debug("statCounter=%s, instance=%s , statValue= %s" % (statCounter, instanceStr, statValue))
                        esx_data.setdefault(dataStoreIds[instanceStr], []).append("write_latency:%s" % statValue)
                        #ds_unit = unit
                        #esx_data["write_latency"] = statValue
                    if dscollection and statName == "datastore.write" and instanceStr in dataStoreIds.keys():
                        #logger.debug("statCounter=%s, instance=%s , statValue= %s" % (statCounter, instanceStr, statValue))
                        esx_data.setdefault(dataStoreIds[instanceStr], []).append("write_total:%s" % statValue)
                        #ds_unit = unit
                        #esx_data["write_total"] = statValue
                    if dscollection and statName == "datastore.read" and instanceStr in dataStoreIds.keys():
                        #logger.debug("statCounter=%s, instance=%s , statValue= %s" % (statCounter, instanceStr, statValue))
                        esx_data.setdefault(dataStoreIds[instanceStr], []).append("read_total:%s" % statValue)
                        #ds_unit = unit
                        #esx_data["read_total"] = statValue


                    #CPU Collection

                    if cpucollection and statName == "cpu.coreUtilization":
                        add_row(iteration, "cpu", DBSession, startTime, coreid=instanceStr, coreutil=statValue)

                    if memcollection and statName == "mem.usage" :
                        add_row(iteration, "mem", DBSession, startTime,  usage = statValue)



            # There are multiple Parameters for NIC, DS Which  are consolidated above and needs to be written once in DB.

            """
            logger.debug("The Nic Resut is %s"%(dict(esx_nic_data)))         
            

            for nic, nicvalues in esx_nic_data.iteritems():

                nic = pnic
                usage = None
                usageunit = None
                total_tx = None
                total_rx = None
                for nicitem in nicvalues:
                    if "unit" in nicitem:
                        usageunit = nicitem.split(":")[1]
                    if "usage" in nicitem:
                        usage = int(nicitem.split(":")[1])
                    if "Tx" in nicitem:
                        total_tx = int(nicitem.split(":")[1])
                    if "Rx" in nicitem:
                        total_rx = int(nicitem.split(":")[1])
                    add_row(iteration, "network", DBSession, startTime, name=nic,usage=usage,unit=usageunit,
                            maxspeed=linkspeed, sent = total_tx , received = total_rx)
            """


            add_row(iteration, "network", DBSession, startTime, name=pnic, usage=esx_nic_data["usage"], unit=esx_nic_data["unit"] , maxspeed=linkspeed,
                    sent=esx_nic_data["Tx"], received=esx_nic_data["Rx"])

            #logger.debug("Iteration %s The DS Result is %s" % (iteration, dict(esx_data)))

            for ds, values in esx_data.iteritems():
                name = ds
                ds_read_latency = None
                ds_write_latency = None
                ds_write_total = None
                ds_read_total = None

                for item in values:
                    if "read_latency" in item:
                        ds_read_latency = int(item.split(":")[1])
                    elif "write_latency" in item:
                        ds_write_latency = int(item.split(":")[1])
                    elif "read_total" in item:
                        ds_read_total = int(item.split(":")[1])
                    elif "write_total" in item:
                        ds_write_total = int(item.split(":")[1])


                add_row(iteration, "datastore", DBSession, startTime, name=name, hostname=hostName,dswrite=ds_write_latency , dsread =ds_read_latency ,
                        unit = ds_unit,totalread=ds_read_total, totalwrite = ds_write_total)



            #logger.info("THREAD -%s- The local result after Iteration %s is \n\n%s" % (threadname,iteration, localResult))

            #operation[startTime] = localResult
            logger.info("# " * 10)
            logger.debug("Stat collection Instance %s Ends " % iteration)
            logger.info("# " * 10)
            time.sleep(5)

        #logger.info("The Operation result after last Iteration %s is \n\n%s"%(iteration,operation))

    except Exception, e:
        print '!! ' * 60
        traceback.print_exc(file=sys.stdout)
        print '!! ' * 60












