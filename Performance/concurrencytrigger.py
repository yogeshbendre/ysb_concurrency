__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
"""

import argparse
import atexit
import getpass
import logging
import re
import ssl
import datetime
import traceback
from time import sleep
from pyVim.connect import SmartConnect, Disconnect,SmartStubAdapter,VimSessionOrientedStub
import pyVmomi
from pyVmomi import vim, vmodl
from multiprocessing.dummy import Pool as ThreadPool
import time
import multiprocessing
import json
from dateutil.parser import parse
from dateutil import tz
from collections import defaultdict
from pydoc import locate

from framework.common import TestConstants as tc



from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine,Table, Column, Integer, String, MetaData
import os


from framework.common import DataParser
from framework.common import TestConstants

import glob

Base = declarative_base()


def remove_db(engine, db_name):
    Base.metadata.drop_all(engine)
    os.remove(db_name)
    print("Removed DB %s" % db_name)

def get_args():
    parser = argparse.ArgumentParser(description="Concurrency Framework. ")

    parser.add_argument('-d', '--debug', required=False, help='Enable debug output', dest='debug', action='store_true')

    parser.add_argument('-l', '--log-file', nargs=1, required=False, help='File to log to (default = stdout)',
                        dest='logfile', type=str)
    parser.add_argument('-o', '--ops', required=True, help='Type of Operation/Test to run. Vmotion/Cloning etc.', dest='ops',
                        type=str)
    parser.add_argument('-f', '--file', required=True, help='File Name containing Migration Information.', dest='file',
                        type=str)
    parser.add_argument('-t', '--threads', nargs=1, required=False,
                        help='Amount of threads to use. Choose the amount of threads with the speed of your datastore in mind, each thread starts a process for '
                             'the migration of a virtual machine. (default = 1)',
                        dest='threads', type=int, default=[1])
    parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose',
                        action='store_true')
    parser.add_argument('-w', '--wait-max', nargs=1, required=False,
                        help='Maximum amount of seconds to wait when gathering information (default = 120)',
                        dest='maxwait', type=int, default=[120])
    args = parser.parse_args()

    return args

def remove_db(engine,db_name):
    Base.metadata.drop_all(engine)
    os.remove(db_name)


def main():

    args = get_args()

    debug = args.debug
    verbose = args.verbose

    threads = args.threads[0]

    stressparam = None
    if args.file:
        stressparam = args.file

    log_file = None
    if args.logfile:
        log_file = args.logfile[0]

    ops_name = None
    if args.ops:
        ops_name = args.ops


    # Logging settings

    def generate_logger(log_level=None, log_file=None):
        import logging
        #    PROJECT_DIR="/home/vmlib/spm/nsx"
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

    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    if log_file == 'nolog':
        TestConstants.logger = generate_logger(log_level, log_file=None)
    else:
        log_file = log_file
        if not log_file:
            TestConstants.test_start = datetime.datetime.now().strftime("%d%m%Y%H%M%S")
            log_file = ops_name + "-" + TestConstants.test_start + ".log"
            TestConstants.logger = generate_logger(log_level, log_file=log_file)

    ssl_context = None
    context = ssl._create_unverified_context()



    print("Removing Past DBs")

    myDBs = [f for f in glob.glob("framework/db/*.db")]

    for myDb in myDBs:
        try:
            engine = create_engine('sqlite:///%s' % myDb)
            remove_db(engine, myDb)
        except Exception, e:
            print("Could Not Remove DB %s due to error %s." % (myDb, e))

    TestConstants.logger.debug('Setting up pools and process for %s operation'%ops_name)
    TestConstants.pool = ThreadPool(threads)
    TestConstants.task_pool = ThreadPool(threads)

    try:

        #print ("%s , %s "%(tc.test_data, instances))
        test_specs = []
        TestConstants.logger.info("Start Test %s"%ops_name)
        logger = TestConstants.logger
        TestConstants.testname = ops_name
        TestConstants.stressparam = stressparam
        TestConstants.test_data,TestConstants.process = DataParser.DataGenerator(TestConstants.stressparam, TestConstants.testname)
        statlist = TestConstants.getStatsList()
        for stat in statlist:
            if stat in "pnic":
                TestConstants.stat_enable["nic"] = True
            if stat in "datastore":
                TestConstants.stat_enable["datastore"] = True
            if stat in "disk":
                TestConstants.stat_enable["disk"] = True
            if stat in "cpu":
                TestConstants.stat_enable["cpu"] = True
            if stat in "mem":
                TestConstants.stat_enable["mem"] = True


        #print "Debug %s"%test_data

        #Reflect the Test Type and Start Run

        testclass = locate('framework.operation.%s'%ops_name)
        testclass.runTest()



    except vmodl.MethodFault as e:
        TestConstants.logger.exception('Caught vmodl fault %'+ str(e))

    except Exception as e:
        TestConstants.logger.exception('Caught exception: ' + str(e))

    TestConstants.logger.info('Finished all tasks')
    if log_file != 'nolog':
        TestConstants.logger.info('The output is logged to '+ log_file)

    return 0



if __name__ == "__main__":
    main()
    print "End of Main Function"
