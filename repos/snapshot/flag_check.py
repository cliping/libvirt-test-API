#!/usr/bin/env python
"""check the flag file in the guest OS
   mandatory arguments: guestname, username, password
"""

import os
import sys
import re
import time

import libvirt
from libvirt import libvirtError

from utils import utils
from utils import check

FLAG_FILE = "/tmp/snapshot_flag"
FLAG_CHECK = "ls %s" % FLAG_FILE

def return_close(conn, logger, ret):
    conn.close()
    logger.info("closed hypervisor connection")
    return ret

def check_params(params):
    """Verify the input parameter"""
    logger = params['logger']
    args_required = ['guestname', 'username', 'password']
    for arg in args_required:
        if arg not in params:
            logger.error("Argument '%s' is required" % arg)
            return 1

    return 0

def check_domain_running(conn, guestname, logger):
    """ check if the domain exists and in running state as well """
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if guestname not in guest_names:
        logger.error("%s is not running or does not exist" % guestname)
        return False
    else:
        return True

def flag_check(params):
    """ check if the flag file is present or not"""
    logger = params['logger']
    params_check_result = check_params(params)
    if params_check_result:
        return 1

    guestname = params['guestname']
    username = params['username']
    password = params['password']

    if params.has_key('expectedret'):
        expected_result = params['expectedret']
    else:
        expected_result = "exist"

    util = utils.Utils()
    chk = check.Check()
    uri = params['uri']
    conn = libvirt.open(uri)

    logger.info("the uri is %s" % uri)

    if not check_domain_running(conn, guestname, logger):
        logger.error("need a running guest")
        return return_close(conn, logger, 1)

    logger.info("get the mac address of vm %s" % guestname)
    mac = util.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 300
    while timeout:
        ipaddr = util.mac_to_ip(mac, 180)
        if not ipaddr:
            logger.info(str(timeout) + "s left")
            time.sleep(10)
            timeout -= 10
        else:
            logger.info("the ip address of vm %s is %s" % (guestname, ipaddr))
            break

    if timeout == 0:
        logger.info("vm %s failed to get ip address" % guestname)
        return return_close(conn, logger, 1)

    ret = chk.remote_exec_pexpect(ipaddr, username, password, FLAG_CHECK)
    if ret == "TIMEOUT!!!":
        logger.error("connecting to guest OS timeout")
        return return_close(conn, logger, 1)
    elif ret == FLAG_FILE and expected_result == "exist":
        logger.info("checking flag %s in guest OS succeeded" % FLAG_FILE)
        return return_close(conn, logger, 0)
    elif ret == FLAG_FILE and expected_result == 'noexist':
        logger.error("flag %s still exist, FAILED." % FLAG_FILE)
        return return_close(conn, logger, 1)
    elif ret != None and expected_result == "exist":
        logger.error("no flag %s exists in the guest %s " % (FLAG_FILE,guestname))
        return return_close(conn, logger, 1)
    elif ret != None and expected_result == 'noexist':
        logger.info("flag %s is not present, checking succeeded" % FLAG_FILE)
        return return_close(conn, logger, 0)

    return return_close(conn, logger, 0)

def flag_check_clean(params):
    """ clean testing environment """
    return 0
