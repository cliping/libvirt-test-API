#!/usr/bin/evn python
"""this test case is used for testing
   virtual network start automatically capability
"""

import time
import os
import re
import sys
import commands

import libvirt
from libvirt import libvirtError


def check_params(params):
    """Verify inputing parameter dictionary"""

    keys = ['networkname', 'autostart']
    for key in keys:
        if key not in params:
            logger.error("%s is required" % key)
            return 1

    return 0

def check_network_autostart(*args):
    """Check network start automatically result, if setting network is
       successful, networkname.xml will exist under
       /etc/libvirt/{hypervisor}/networks/autostart/
    """
    (networkname, hypervisor, flag, logger) = args

    netxml = "/etc/libvirt/%s/networks/autostart/%s.xml" % \
              (hypervisor, networkname)
    logger.debug("virtual network xml file is: %s" % netxml)

    if flag == 1:
        if os.access(netxml, os.F_OK):
            return True
        else:
            return False
    elif flag == 0:
        if not os.access(netxml, os.F_OK):
            return True
        else:
            return False
    else:
        return False

def autostart(params):
    """Set virtual network autostart capability"""

    global logger
    logger = params['logger']

    params.pop('logger')

    params_check_result = check_params(params)

    if params_check_result:
        return 1

    networkname = params['networkname']
    autostart = params['autostart']

    flag = -1
    if autostart == "enable":
        flag = 1
    elif autostart == "disable":
        flag = 0
    else:
        logger.error("Error: autostart value is invalid")
        return 1

    uri = params['uri']

    logger.info("uri address is %s" % uri)

    conn = libvirt.open(uri)
    netobj = conn.networkLookupByName(networkname)

    logger.debug("before setting autostart to virtual network, check status:")
    shell_cmd = "virsh net-list --all"
    (status, text) = commands.getstatusoutput(shell_cmd)
    logger.debug("the output of 'virsh net-list --all' is %s" % text)

    try:
        try:
            netobj.setAutostart(flag)
            if check_network_autostart(networkname,
                                       "qemu",
                                       flag,
                                       logger):
                logger.info("current virtual network %s autostart: %s" % \
                             (networkname, netobj.autostart()))
                logger.info("executing autostart operation is successful")
            else:
                logger.error("Error: fail to check autostart status of \
                              virtual network %s" % networkname)
                return 1
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s" \
                         % (e.message, e.get_error_code()))
            logger.error("Error: fail to autostart virtual network %s " % \
                          networkname)
            return 1
    finally:
        conn.close()
        logger.info("closed hypervisor connection")

    logger.debug("After setting autostart to virtual network, check status:")
    shell_cmd = "virsh net-list --all"
    (status, text) = commands.getstatusoutput(shell_cmd)
    logger.debug("the output of 'virsh net-list --all' is %s" % text)
    time.sleep(3)
    return 0
