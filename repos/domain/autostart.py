#!/usr/bin/evn python
"""this test case is used for testing
   domain start automatically capability
   mandatory arguments:guestname
                       autostart
"""

import os
import re
import sys

import libvirt
from libvirt import libvirtError

from utils import utils

def usage(params):
    """Verify inputing parameter dictionary"""
    logger = params['logger']
    keys = ['guestname', 'autostart']
    for key in keys:
        if key not in params:
            logger.error("%s is required" % key)
            return 1

def check_guest_autostart(*args):
    """Check domain start automatically result, if setting domain is
       successful, guestname.xml will exist under
       /etc/libvirt/{hypervisor}/autostart/
    """
    (guestname, hypervisor, flag, logger) = args
    if 'xen' in hypervisor:
        domxml = "/etc/%s/auto/%s" % (hypervisor, guestname)
    else:
        domxml = "/etc/libvirt/%s/autostart/%s.xml" % (hypervisor, guestname)
    logger.debug("guest xml file is: %s" %domxml)

    if flag == 1:
        if os.access(domxml, os.F_OK):
            return True
        else:
            return False
    elif flag == 0:
        if not os.access(domxml, os.F_OK):
            return True
        else:
            return False
    else:
        return False

def autostart(params):
    """Set domain autostart capability"""
    # Initiate and check parameters
    usage(params)
    logger = params['logger']
    guestname = params['guestname']
    autostart = params['autostart']
    test_result = False
    flag = -1
    if autostart == "enable":
        flag = 1
    elif autostart == "disable":
        flag = 0
    else:
        logger.error("Error: autostart value is invalid")
        return 1

    # Connect to local hypervisor connection URI
    util = utils.Utils()
    uri = params['uri']
    conn = libvirt.open(uri)

    domobj = conn.lookupByName(guestname)

    try:
        try:
            domobj.setAutostart(flag)
            if check_guest_autostart(guestname, uri.split(":")[0], flag, logger):
                logger.info("current %s autostart: %s" %
                            (guestname, domobj.autostart()))
                logger.info("executing autostart operation is successful")
                test_result = True
            else:
                logger.error("Error: fail to check autostart domain")
                test_result = False
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s" \
                         % (e.message, e.get_error_code()))
            logger.error("Error: fail to autostart %s domain" %guestname)
            test_result = False
    finally:
        conn.close()
        logger.info("closed hypervisor connection")

    if test_result:
        return 0
    else:
        return 1

def autostart_clean(params):
    """ clean testing environment """
    pass
