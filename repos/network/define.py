#!/usr/bin/evn python
# Define a network

import time
import os
import re
import sys

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import xml_builder

required_params = ('networkname',
                   'bridgename',
                   'bridgeip',
                   'bridgenetmask',
                   'netstart',
                   'netend',
                   'netmode',)
optional_params = ()

def check_network_define(networkname, logger):
    """Check define network result, if define network is successful,
       networkname.xml will exist under /etc/libvirt/qemu/networks/
       and can use virt-xml-validate tool to check the file validity
    """
    path = "/etc/libvirt/qemu/networks/%s.xml" % networkname
    logger.debug("%s xml file path: %s" % (networkname, path))
    #valid = "virt-xml-validate %s" % path
    #stat, ret = commands.getstatusoutput(valid)
    #logger.debug("virt-xml-validate exit status: %d" % stat)
    #logger.debug("virt-xml-validate exit result: %s" % ret)
    #if os.access(path, os.R_OK) and stat == 0:
    if os.access(path, os.R_OK):
        return True
    else:
        return False

def define(params):
    """Define a network from xml"""
    logger = params['logger']
    networkname = params['networkname']

    conn = sharedmod.libvirtobj['conn']

    if check_network_define(networkname, logger):
        logger.error("%s network is defined" % networkname)
        return 1

    xmlobj = xml_builder.XmlBuilder()
    netxml = xmlobj.build_network(params)
    logger.debug("network xml:\n%s" % netxml)

    net_num1 = conn.numOfDefinedNetworks()
    logger.info("original network define number: %s" % net_num1)

    try:
        conn.networkDefineXML(netxml)
        net_num2 = conn.numOfDefinedNetworks()
        if check_network_define(networkname, logger) and net_num2 > net_num1:
            logger.info("current network define number: %s" % net_num2)
            logger.info("define %s network is successful" % networkname)
        else:
            logger.error("%s network is undefined" % networkname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        logger.error("define a network from xml: \n%s" % netxml)
        return 1

    return 0
