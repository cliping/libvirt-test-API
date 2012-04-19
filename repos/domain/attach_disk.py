#!/usr/bin/env python
# Attach a disk device to domain

import os
import re
import sys
import time
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils
from utils import xml_builder

required_params = ('guestname',
                   'virt_type',
                   'imagename',
                   'imagesize',
                   'hdmodel',)
optional_params = ()

def create_image(name, size, logger):
    """Create a image file"""
    disk = "/var/lib/libvirt/images/%s.img" % name
    stat, ret = commands.getstatusoutput("dd if=/dev/zero of=%s bs=1 \
                                          count=1 seek=%dM" % (disk, size))
    if stat == 0:
        logger.debug("create image result:\n%s" % ret)
        return True
    else:
        return False

def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or state == libvirt.VIR_DOMAIN_SHUTDOWN:
    # add check function
        return False
    else:
        return True

def check_attach_disk(num1, num2):
    """Check attach disk result via simple disk number comparison """
    if num2 > num1:
        return True
    else:
        return False

def attach_disk(params):
    """Attach a disk to domain from xml"""
    logger = params['logger']
    guestname = params['guestname']
    imagename = params['imagename']
    imagesize = int(params['imagesize'])
    disktype = params['hdmodel']

    conn = sharedmod.libvirtobj['conn']

    # Create image
    if create_image(imagename, imagesize, logger):
        del params['imagesize']
    else:
        logger.error("fail to create a image file")
        return 1

    domobj = conn.lookupByName(guestname)

    # Generate disk xml
    xmlobj = xml_builder.XmlBuilder()
    diskxml = xmlobj.build_disk(params)
    logger.debug("disk xml:\n%s" %diskxml)

    disk_num1 = utils.dev_num(guestname, "disk")
    logger.debug("original disk number: %s" %disk_num1)

    if disktype == "virtio":
        if check_guest_status(domobj):
            pass
        else:
            domobj.create()
            time.sleep(90)

    # Attach disk to domain
    try:
        domobj.attachDevice(diskxml)
        disk_num2 = utils.dev_num(guestname, "disk")
        logger.debug("update disk number to %s" %disk_num2)
        if  check_attach_disk(disk_num1, disk_num2):
            logger.info("current disk number: %s\n" %disk_num2)
        else:
            logger.error("fail to attach a disk to guest: %s\n" %disk_num2)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        logger.error("attach %s disk to guest %s" % (imagename, guestname))
        return 1

    return 0
