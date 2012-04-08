#!/usr/bin/env python
"""this test case is used for testing delete
   a volume from dir type storage pool
"""

import os
import re
import sys

import libvirt
from libvirt import libvirtError

from utils import utils

def usage(params):
    """Verify inputing parameter dictionary"""
    keys = ['poolname', 'volname']
    for key in keys:
        if key not in params:
            logger.error("%s is required" %key)
            logger.info("please input the following argument:")
            logger.info(keys)
            return False
        elif len(params[key]) == 0:
            logger.error("%s value is empty, please inputting a value" %key)
            return False
        else:
            return True

def display_volume_info(poolobj):
    """Display current storage volume information"""
    logger.debug("current storage volume list: %s" \
% poolobj.listVolumes())

def get_storage_volume_number(poolobj):
    """Get storage volume number"""
    vol_num = poolobj.numOfVolumes()
    logger.info("current storage volume number: %s" % vol_num)
    return vol_num

def check_volume_delete(volkey):
    """Check storage volume result, volname {volkey} will don't exist
       if deleting volume is successful
    """
    logger.debug("volume file path: %s" % volkey)
    if not os.access(volkey, os.R_OK):
        return True
    else:
        logger.debug("%s file don't exist" % volkey)
        return False

def delete_dir_volume(params):
    """Delete a dir type storage volume"""
    global logger
    logger = params['logger']

    if not usage(params):
        return 1

    poolname = params['poolname']
    volname = params['volname']

    util = utils.Utils()
    uri = params['uri']

    conn = libvirt.open(uri)
    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        poolobj = conn.storagePoolLookupByName(poolname)
    else:
        logger.error("%s not found\n" % poolname);
        conn.close()
        return 1

    if not poolobj.isActive():
        logger.error("can't delete volume from inactive %s pool" % poolname)
        conn.close()
        logger.info("closed hypervisor connection")
        return 1

    volobj = poolobj.storageVolLookupByName(volname)
    volkey = volobj.key()
    logger.debug("volume key: %s" % volkey)

    vol_num1 = get_storage_volume_number(poolobj)
    display_volume_info(poolobj)

    try:
        try:
            logger.info("delete %s storage volume" % volname)
            volobj.delete(0)
            vol_num2 = get_storage_volume_number(poolobj)
            display_volume_info(poolobj)
            if check_volume_delete(volkey) and vol_num1 > vol_num2:
                logger.info("delete %s storage volume is successful" % volname)
                return 0
            else:
                logger.error("%s storage volume is undeleted" % volname)
                return 1
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s" \
                         % (e.message, e.get_error_code()))
            return 1
    finally:
        conn.close()
        logger.info("closed hypervisor connection")

    return 0
