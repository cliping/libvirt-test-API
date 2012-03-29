#!/usr/bin/env python
"""this test case is used for testing define
   a disk type storage pool from xml
"""

__author__ = 'Guannan Ren: gren@redhat.com'
__date__ = 'Tue April 30, 2010'
__version__ = '0.1.0'
__credits__ = 'Copyright (C) 2010 Red Hat, Inc.'
__all__ = ['usage', 'check_pool_define', \
           'display_pool_info', 'define_disk_pool']

import os
import re
import sys

from lib import connectAPI
from lib import storageAPI
from utils.Python import utils
from utils.Python import xmlbuilder
from exception import LibvirtAPI

def usage():
    "usage infomation"
    print """mandatory options:
              poolname: Name of the pool to be created
              pooltype: Type of the pool, which in this case must be 'disk'
              sourcepath: Name of the harddisk like '/dev/sdb'
optional options:
              sourceformat: Pool format types of the pool, representing the common patition tables types
                            dos, dvh, gpt, mac, bsd, pc98, sun
              targetpath: the default is /dev"""

def check_params(params):
    """Verify inputing parameter dictionary"""
    #targetpath and sourceformat are optional arguments
    #the default targetpath is /dev
    #the sourceformat is 'dos'
    mandatory_params = ['poolname', 'pooltype', 'sourcepath']
    optional_params = ['sourceformat', 'targetpath']

    for param in mandatory_params:
        if param not in params:
            logger.error("%s is required" % param)
            usage()
            return 1
        elif len(params[param]) == 0:
            logger.error("%s value is empty, please inputting a value" % param)
            return 1
        else:
            pass

def display_pool_info(stgobj):
    """Display current storage pool information"""
    logger.debug("current define storage pool: %s" % \
                  stgobj.defstorage_pool_list())
    logger.debug("current active storage pool: %s" % \
                  stgobj.storage_pool_list())

def check_pool_define(poolname):
    """This function will check if the storage pool with
       the given poolname existed already.It first checks
       if the storagepool xml file exists in /etc/libvirt/storage
       directory
    """
    path = "/etc/libvirt/storage/%s.xml" % poolname
    logger.debug("%s xml file path: %s" % (poolname, path))

    if os.access(path, os.R_OK):
        return True
    else:
        return False

def define_disk_pool(params):
    """Define a disk type storage pool from xml"""

    global logger
    logger = params['logger']

    params.pop('logger')

    params_check_result = check_params(params)

    if params_check_result:
        return 1

    poolname = params['poolname']
    pooltype = params['pooltype']
    sourcepath = params['sourcepath']

    logger.info("the poolname is %s, pooltype is %s, sourcepath is %s" % \
                 (poolname, pooltype, sourcepath))

    util = utils.Utils()
    uri = params['uri']

    conn = connectAPI.ConnectAPI(uri)
    conn.open()

    stgobj = storageAPI.StorageAPI(conn)

    if check_pool_define(poolname):
        logger.error("%s storage pool is defined" % poolname)
        conn.close()
        logger.info("closed hypervisor connection")
        return 1

    xmlobj = xmlbuilder.XmlBuilder()
    poolxml = xmlobj.build_pool(params)
    logger.debug("storage pool xml:\n%s" % poolxml)

    pool_num1 = stgobj.get_number_of_defpools()
    logger.info("original storage pool define number: %s" % pool_num1)
    display_pool_info(stgobj)

    try:
        try:
            logger.info("define %s storage pool" % poolname)
            stgobj.define_pool(poolxml)
            pool_num2 = stgobj.get_number_of_defpools()
            logger.info("current storage pool define number: %s" % pool_num2)
            display_pool_info(stgobj)
            if check_pool_define(poolname) and pool_num2 > pool_num1:
                logger.info("It is successful to define %s storage pool" % poolname)
                return 0
            else:
                logger.error("%s storage pool was not defined successfully" % \
                              poolname)
                return 1
        except LibvirtAPI, e:
            logger.error("API error message: %s, error code is %s" \
                         % (e.response()['message'], e.response()['code']))
            return 1
    finally:
        conn.close()
        logger.info("closed hypervisor connection")

    return 0
