__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

"""
from collections import namedtuple,defaultdict

"""

global testname
global stressparam
global test_data
global instance
global logger
"""


test_start = None
testname = None
stressparam = None
test_data = None
process = None
logger = None
pool = None
task_pool = None
task_results = []
METRICS_DATA = {}

HOST_METRICS_COLLECT = True

instance = 1
stat_enable = {"nic" : False , "datastore" : False , "disk" : False, "cpu" : False , "mem" : False}

plottervmlist = []
vmdb = []
host_stat_spec = defaultdict(list)
hs_data = {}

PRIMARY_LDU_NAME = None
SECONDARY_LDU_NAME = None
PRIMARY_LDU_USER_NAME = None
PRIMARY_LDU_PASSWD = None
SECONDARY_LDU_USER_NAME = None
SECONDARY_LDU_PASSWD = None
PRIMARY_LDU_ROOT = None
SECONDARY_LDU_ROOT = None
SECONDARY_LDU_ROOT_PASS=None
SRC_DATACENTER=None
DEST_DATACENTER=None
HOST_NAME=None
DEST_HOST_NAME=None
DATASTORE=None
DEST_DATASTORE=None
SRC_CLUSTER=None
DEST_CLUSTER=None
VM_NAME=None
PNIC = None
STAT_COLLLECTION_LIST=None
SRC_PNIC = None


POWER_STATE=None
SRC_VM_NAME = None


SRC_DISK = None
DEST_DISK = None





def getLDU():
    return getData(test_data,"PRIMARY_LDU_NAME")

def getXLDU():
    return getData(test_data,"SECONDARY_LDU_NAME")

def getLDULocalUser():
    return getData(test_data,"PRIMARY_LDU_USER_NAME")

def getLDULocalPass():
    return getData(test_data,"PRIMARY_LDU_PASSWD")



def getXLDULocalUser():
    return getData(test_data,"SECONDARY_LDU_USER_NAME")

def getXLDULocalPass():
    return getData(test_data,"SECONDARY_LDU_PASSWD")

def getLDURoot():
    return getData(test_data,"PRIMARY_LDU_ROOT")

def getLDURootPass():
    return getData(test_data,"PRIMARY_LDU_ROOT_PASS")

def getXLDURoot():
    return getData(test_data,"SECONDARY_LDU_ROOT")

def getXLDURootPass():
    return getData(test_data,"SECONDARY_LDU_ROOT_PASS")

def getDatacenter():
    return getData(test_data,"DATACENTER")

def getXDatacenter():
    return getData(test_data,"DEST_DATACENTER")


def getHost():
    return getData(test_data,"HOST_NAME")

def getXHost():
    return getData(test_data,"DEST_HOST_NAME")

def getDatastore():
    return getData(test_data,"DATASTORE")

def getXDatastore():
    return getData(test_data,"DEST_DATASTORE")


def getCluster():
    return getData(test_data,"CLUSTER")

def getXCluster():
    return getData(test_data,"DEST_CLUSTER")


def getVM():
    return getData(test_data,"VM_NAME")

def getPnic():
    return getData(test_data,"PNIC")

def getSrcPnic():
    return getData(test_data,"SRC_PNIC")


def getStatsList():
    stats =  getData(test_data,"STAT_COLLLECTION_LIST").split(",")
    return stats


def getPowerState():
    if  getData(test_data,"POWER_STATE") in ["On", "True" , "on" , "oN"]:
        return True
    else:
        return False


def getSrcVM():
    return getData(test_data,"SRC_VM_NAME")



def getSrcDisk():
    return getData(test_data, "SRC_DISK")

def getDestDisk():
    return getData(test_data, "DEST_DISK")


######################## DATA GETER METHOD ###############

def getData(test_data,variable_name):
    data = None
    instance_data_value=None
    common_instance = None

    common_instance = test_data[testname].get("common",None)



    if common_instance:
        data = common_instance.get(variable_name,None)


    instance_data = test_data[testname].get("instance", None)
    #print "Debug %s"%instance_data
    if instance_data:
        instance_data_value = instance_data[str(instance)].get(variable_name,None)

    if instance_data_value:
        return instance_data_value
    else:
        return data

##########################################################

"""
test_data = DataParser.DataGenerator("vmotion.txt","HLMMigration")

for ins in range (1,3):

    instance = str(ins)


    print "Instance %s"%instance

    print "VC %s xVC %s Cluster %s xCluster %s Datacenter %s xDatacenter %s"%(getLDU(),getXLDU(),getCluster(),getXCluster(),getDatacenter(),getXDatacenter())

"""