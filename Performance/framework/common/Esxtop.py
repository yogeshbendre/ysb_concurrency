__author__ = 'Smruti P Mohanty'
import customssh
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
import traceback
import multiprocessing
import glob
import re
import json
from framework.vcenter import Datacenter, Cluster
from framework.common import customssh
from framework.common.TaskAnalyzer import VMStats


import sys

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship,sessionmaker
from sqlalchemy import create_engine,Table, Column, Integer, String, MetaData , Float
import os

statrequired = tc.stat_enable

Base = declarative_base()

final_data = {}
vm_data = defaultdict(list)
host_ds = defaultdict(list)
host_nic = defaultdict(list)
cpu_data = defaultdict(list)
mem_data = defaultdict(list)


def remove_db(engine, db_name):
    Base.metadata.drop_all(engine)
    os.remove(db_name)


def TopData(logger, host,):
    """
        @param si:  Service Instance of the vCenter in which the Host Reside.
        @param host: Host MOR Object
        @param pnic: The physical nic that needs to be monitored
        @param datastores: An Array of Datastores
        @return: An Ordered Hash Object which contains Performance data
    """


    threadname = multiprocessing.current_process().name

    try:

        iteration = 0
        # Remove old Test files.
        removefile = "rm -rf /tmp/conc*"
        exit_status, stdout0, stderr0 = customssh.CustomRunSsh(removefile,host,"root","ca$hc0w")


        while True:

            #logger.info("Host Metrics collection ++++++++++++  %s"% tc.HOST_METRICS_COLLECT)

            iteration += 1

            logger.info("* " * 10)
            logger.debug("Thread - %s - Stat collection Instance %s Begins " % (threadname,iteration))
            logger.info("* " * 10)

            generatedata = "esxtop -b -d 3 -n 1 > /tmp/conc%s"%iteration
            exit_status, stdout0, stderr0 = customssh.CustomRunSsh(generatedata, host, "root", "ca$hc0w")

            logger.info("# " * 10)
            logger.debug("Thread - %s - Stat collection Instance %s Ends " % (threadname,iteration))
            logger.info("# " * 10)
            #time.sleep(1)

    except Exception, e:
        print '!! ' * 60
        traceback.print_exc(file=sys.stdout)
        print '!! ' * 60






