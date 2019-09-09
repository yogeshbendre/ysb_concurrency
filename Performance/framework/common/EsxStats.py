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
from sqlalchemy import create_engine,Table, Column, Integer, String, MetaData
import os


Base = declarative_base()

class NetworkData(Base):
    __tablename__ = 'networktable'
    id = Column(Integer, primary_key=True)
    time = Column(String(40))
    network = Column(String(40))
    usage = Column(Integer)
    unit = Column(String(5))
    maxspeed = Column(Integer)


class DSData(Base):
    __tablename__ = 'datastoretable'
    id = Column(Integer, primary_key=True)
    time = Column(String(80))
    datastore = Column(String(80))
    dsread = Column(Integer)
    dswrite = Column(Integer)
    unit = Column(String(5))

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
            storestat = NetworkData(time=time,network=kwargs["name"],usage=kwargs["usage"],unit = kwargs["unit"],maxspeed = kwargs["maxspeed"])
            session.add(storestat)
        else:
            storestat = DSData(time=time,datastore=kwargs["name"],dsread=kwargs["dsread"],dswrite=kwargs["dswrite"],unit = kwargs["unit"])
            session.add(storestat)

        session.commit()
    except Exception as e:
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
    except Exception as e:
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

        SUMMARY_INTERVALID = 5 * 60
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

        summarySpecs = []




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

        loop = True
        tzinfos = {"UTC": 0}

        statCounter = 0

        while True:



            logger.info("THREAD -%s- %s host stats collection iteration %s"%(threadname,hostName,iteration))
            iteration +=1
            ds_unit = None
            print("Debug The Current Time %s"%str(si.CurrentTime()))
            #startTime = parse(str(si.CurrentTime()), tzinfos=tzinfos).strftime('%s')
            startTime = parse(str(si.CurrentTime()))
            queryResult = perfMgr.QueryStats(querySpecs)

            esx_data = defaultdict(list)
            for entityMetric in queryResult:
                statCounter +=1
                logger.info("= "*80 )



                for series in entityMetric.value:

                    counterId = series.id.counterId
                    instanceStr = series.id.instance
                    statName = idToNameMap[counterId][0]
                    entity = entityMetric.entity
                    unit = idToNameMap[counterId][2]
                    statValue = series.value[-1]
                    #logger.debug("Stat Name ******** @@@@@@@@@@@@ %s Value %s"%(statName,statValue))
                    if niccollection and statName == "net.usage" and instanceStr == pnic:
                        add_row(iteration,"network",DBSession,startTime,name=instanceStr,usage=statValue,unit=unit,maxspeed=linkspeed)
                    if dscollection and statName == "datastore.totalReadLatency" and instanceStr in dataStoreIds.keys():
                        esx_data.setdefault(dataStoreIds[instanceStr], []).append("read:%s"%statValue)
                        ds_unit = unit
                    if dscollection and statName == "datastore.totalWriteLatency" and instanceStr in dataStoreIds.keys():
                        esx_data.setdefault(dataStoreIds[instanceStr], []).append("write:%s" % statValue)
                        ds_unit = unit


                for ds, values in esx_data.iteritems():
                    name = ds
                    r = None
                    w = None

                    arr1 = values[0].split(":")
                    arr2 = values[1].split(":")
                    if "read" in arr1:
                        r = arr1[1]
                    else:
                        r = arr2[1]
                    if "read" in arr1:
                        w = arr1[1]
                    else:
                        w = arr2[1]
                    add_row(iteration, "datastore", DBSession, startTime, name=name, dswrite=w , dsread =r ,unit = ds_unit)


            #logger.info("THREAD -%s- The local result after Iteration %s is \n\n%s" % (threadname,iteration, localResult))

            #operation[startTime] = localResult
            time.sleep(10)

        #logger.info("The Operation result after last Iteration %s is \n\n%s"%(iteration,operation))

    except Exception as e:
        print('-' * 60)
        traceback.print_exc(file=sys.stdout)
        print('-' * 60)












