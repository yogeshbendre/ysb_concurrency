__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
This is my Hobby Project. There is no guarentee of delivery.

"""

from framework.common import TestConstants as tc
from framework.vcenter import VCOps, Datacenter, Cluster
from pyVmomi import vim, vmodl
import paramiko
import time

logger = tc.logger

_serviceinstance = {}


def getMemSi(vcenter, vcenter_user, vcenter_pass):

    if _serviceinstance.get(vcenter,None):
        logger.info("Returning Memoized SI")
        return _serviceinstance[vcenter]
    else:
        _serviceinstance[vcenter] = VCOps.Login(vcenter, vcenter_user, vcenter_pass, port=443)
        return _serviceinstance[vcenter]

ds_mors = {}



def getMemDatastore(dcMor, datastore_name):
    ds_Mor = None
    try:
        logger.debug("Getting datastore mob %s" % datastore_name)
        if datastore_name in ds_mors:
            logger.info("Returning Memoized DS mor")
            return ds_mors[datastore_name]
        else:

            datastoresMors = dcMor.datastore
            for datastore in datastoresMors:
                ds_name = datastore.info.name

                ds_mors[ds_name] = datastore
                if ds_name == datastore_name:
                    print("Found Datastore %s"%datastore_name)
                    return datastore


    except Exception as e:
        logger.error("Could not find datastore %s due to error %s" % (datastore_name, str(e)))

dc_mors = {}

def getMemDatacenter(si,datacenter_name):
    if dc_mors.get(datacenter_name,None):
        logger.info("Returning Memoized DC mor")
        return dc_mors[datacenter_name]
    else:
        dc_mors[datacenter_name] = Datacenter.GetDatacenter(name=datacenter_name, si=si)
        return dc_mors[datacenter_name]

cluster_mors = {}

def getMemCluster(dcMor,cluster):
    if cluster_mors.get(cluster,None):
        logger.info("Returning Memoized cluster mor")
        return cluster_mors[cluster]
    else:
        #Traverse the entire datacenter and memoize for future calls
        clusterObjlist = Datacenter.GetClusters(dcMor, [])
        for clusterObj in clusterObjlist:
            cluster_mors[clusterObj.name] = clusterObj
    return cluster_mors[cluster]


host_mors = {}
def getMemHost(dcMor, host, cluster):
    if host_mors.get(host,None):
        logger.info("Returning Memoized host mor")
        return host_mors[host]
    else:
        hostObjs = Cluster.GetHostsInClusters(dcMor, clusterNames=[cluster], connectionState=None)
        for hostObj in hostObjs:
            host_mors[hostObj.name] = hostObj
    return host_mors[host]


def get_certificate_value(vcUrl, root_user, root_pass):
    command = "openssl x509 -in /etc/vmware-vpx/ssl/rui.crt -fingerprint -sha256 -noout"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(vcUrl, username=root_user, password=root_pass)
        cert_cmd = "openssl x509 -in /etc/vmware-vpx/ssl/rui.crt -fingerprint -sha256 -noout"
        stdin, stdout, stderr = ssh.exec_command(cert_cmd)
        while not stdout.channel.exit_status_ready():
            time.sleep(2)
        certValue = stdout.readlines()[0].strip().split('=')[-1]
        logger.info("THREAD - get_certificate_value - The Certificate for VC %s " % certValue)
        return certValue
    except Exception as e:
        logger.error("THREAD - get_certificate_value - Error while Certificate for VC %s " % str(e))
        return 1
    finally:
        ssh.close()

thumprints_store = {}

def getMemThumb(vcUrl,root_user,root_pass):
    if vcUrl in thumprints_store:
        logger.info("Returning Memoized VC Thumbprint")
        return thumprints_store[vcUrl]
    else:
        thumprints_store[vcUrl] = get_certificate_value(vcUrl, root_user, root_pass)
        return thumprints_store[vcUrl]

