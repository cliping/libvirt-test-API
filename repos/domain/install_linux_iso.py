#!/usr/bin/env python
# Install a linux domain from CDROM

import os
import sys
import re
import time
import commands
import shutil
import urllib

import libvirt
from libvirt import libvirtError

from src import sharedmod
from src import env_parser
from utils import utils

ISO_DIR = "/var/lib/libvirt/images/"

required_params = ('guestname', 'guestos', 'guestarch')
optional_params = {
                   'memory': 1048576,
                   'vcpu': 1,
                   'disksize' : 10,
                   'imageformat' : 'qcow2',
                   'qcow2version': 'v3',
                   'hddriver' : 'virtio',
                   'nicdriver': 'virtio',
                   'type' : 'define',
                   'xml': 'xmls/kvm_linux_guest_install_iso.xml',
                   'guestmachine': 'pc',
                   'graphic' : 'spice',
                   'diskpath' : '/var/lib/libvirt/images',
                   'disksymbol' : 'sdb',
                  }

VIRSH_QUIET_LIST = "virsh --quiet list --all|awk '{print $2}'|grep \"^%s$\""
VM_STAT = "virsh --quiet list --all| grep \"\\b%s\\b\"|grep off"
VM_DESTROY = "virsh destroy %s"
VM_UNDEFINE = "virsh undefine %s"

BOOT_DIR = "/var/lib/libvirt/boot"
VMLINUZ = os.path.join(BOOT_DIR, 'vmlinuz')
INITRD = os.path.join(BOOT_DIR, 'initrd.img')
HOME_PATH = os.getcwd()

def prepare_iso(isolink, cache_floder):
    """ Download iso file from isolink to cache_floder
        file into it for automatic guest installation
    """
    cmd = "wget " + isolink + " -P " + cache_floder
    utils.exec_cmd(cmd, shell=True)

def prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger):
    """ After guest installation is over, undefine the guest with
        bootting off cdrom, to define the guest to boot off harddisk.
    """
    xmlstr = xmlstr.replace('<boot dev="cdrom"/>', '<boot dev="hd"/>')
    xmlstr = re.sub('<disk device="cdrom".*\n.*\n.*\n.*\n.*\n', '', xmlstr)

    if installtype != 'create':
        domobj.undefine()
        logger.info("undefine %s : \n" % guestname)

    try:
        conn = domobj._conn
        domobj = conn.defineXML(xmlstr)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        logger.error("fail to define domain %s" % guestname)
        return 1

    logger.info("define guest %s " % guestname)
    logger.debug("the xml description of guest booting off harddisk is %s" %
                 xmlstr)

    logger.info('boot guest up ...')

    try:
        domobj.create()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        logger.error("fail to start domain %s" % guestname)
        return 1

    return 0

def check_domain_state(conn, guestname, logger):
    """ if a guest with the same name exists, remove it """
    running_guests = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        running_guests.append(obj.name())

    if guestname in running_guests:
        logger.info("A guest with the same name %s is running!" % guestname)
        logger.info("destroy it...")
        domobj = conn.lookupByName(guestname)
        domobj.destroy()

    defined_guests = conn.listDefinedDomains()

    if guestname in defined_guests:
        logger.info("undefine the guest with the same name %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.undefine()

    return 0

def install_linux_iso(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    graphic = params.get('graphic', 'spice')
    nicdriver = params.get('nicdriver', 'virtio')
    xmlstr = params['xml']

    logger.info("the name of guest is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']
    check_domain_state(conn, guestname, logger)
    macaddr = utils.get_rand_mac()

    logger.info("the macaddress is %s" % macaddr)
    if not os.path.exists(params.get('diskpath', '/var/lib/libvirt/images')):
        os.mkdir(params.get('diskpath', '/var/lib/libvirt/images'))

    diskpath = params.get('diskpath', "/var/lib/libvirt/images") + '/' + guestname
    hddriver = params.get('hddriver', 'virtio')
    if hddriver != "lun" and hddriver != "scsilun":
        logger.info("disk image is %s" % diskpath)
        seeksize = params.get('disksize', 10)
        imageformat = params.get('imageformat', 'qcow2')
        qcow2version = params.get('qcow2version', 'v3')
        logger.info("create disk image with size %sG, format %s" % (seeksize, imageformat))
        # qcow2version includes "v3","v3_lazy_refcounts"
        if qcow2version.startswith('v3'):
            qcow2_options = "-o compat=1.1"
            if qcow2version.endswith('lazy_refcounts'):
                qcow2_options = qcow2_options + " -o lazy_refcounts=on"
            else:
                qcow2_options = ""
        disk_create = "qemu-img create -f %s %s %s %sG" % \
                        (imageformat, qcow2_options, diskpath, seeksize)
        logger.debug("the command line of creating disk images is '%s'" % \
                       disk_create)

        (status, message) = commands.getstatusoutput(disk_create)
        if status != 0:
            logger.debug(message)
            return 1

        os.chown(diskpath, 107, 107)
        logger.info("creating disk images file is successful.")

    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')
    elif hddriver == "sata":
        xmlstr = xmlstr.replace("DEV", 'sda')
    elif hddriver == 'lun':
        xmlstr = xmlstr.replace("'lun'","'virtio'")
        xmlstr = xmlstr.replace('DEV','vda')
        xmlstr = xmlstr.replace('"file"','"block"')
        xmlstr = xmlstr.replace('"disk"','"lun"')
        xmlstr = xmlstr.replace("file='%s'"% params.get('diskpath','/var/lib/libvirt/images'), \
                                "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol','sdb')
        xmlstr = xmlstr.replace('SDX',disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')
    elif hddriver == 'scsilun':
        xmlstr = xmlstr.replace("'scsilun'","'scsi'")
        xmlstr = xmlstr.replace('DEV','sda')
        xmlstr = xmlstr.replace('"file"','"block"')
        xmlstr = xmlstr.replace('"disk"','"lun"')
        xmlstr = xmlstr.replace("file='%s'"% params.get('diskpath','/var/lib/libvirt/images'), \
                                "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol','sdb')
        xmlstr = xmlstr.replace('SDX',disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')

    # Checking the graphic type
    if graphic == 'vnc' or graphic == 'spice':
        logger.info('The format of graphic is %s' % graphic)
    else:
        logger.error('unsupported kind graphic')
        return 1
    # Checking the nicdriver define
    if nicdriver == 'virtio' or nicdriver == 'e1000' or nicdriver == 'rtl8139':
        logger.info('The kind of nicdriver is %s' % nicdriver)
    else:
        logger.error('unsupported nicdirver')
        return 1

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)

    os_arch = guestos + "_" + guestarch

    envparser = env_parser.Envparser(envfile)
    ostree = envparser.get_value("guest", os_arch)
    ks = envparser.get_value("guest", os_arch + "_iso_ks")

    logger.debug('install source:\n    %s' % ostree)
    logger.debug('kisckstart file:\n    %s' % ks)

    if (ostree == 'http://'):
        logger.error("no os tree defined in %s for %s" % (envfile, os_arch))
        return 1

    logger.info('prepare installation...')
    cache_folder = envparser.get_value("variables", "domain_cache_folder")

    logger.info("begin to download the iso file")
    ioslink = envparser.get_value("guest", os_arch + "_iso")
    logger.info("iso link is %s" % ioslink)
    cache_floder = "/var/lib/libvirt/images/"

    bootcd = cache_floder + ioslink.split("/")[-1]
    if not os.path.exists(bootcd):
        prepare_iso(ioslink, cache_floder)

    logger.info("Finish download the iso file: %s" % bootcd)

    if "rhel" in guestos:
        vmlinuzpath = os.path.join(ostree, 'isolinux/vmlinuz')
        initrdpath = os.path.join(ostree, 'isolinux/initrd.img')
    elif "ubuntu" in guestos:
        vmlinuzpath = os.path.join(ostree, 'vmlinuz')
        initrdpath = os.path.join(ostree, 'initrd.img')

    logger.debug("the url of vmlinuz file is %s" % vmlinuzpath)
    logger.debug("the url of initrd file is %s" % initrdpath)

    urllib.urlretrieve(vmlinuzpath, VMLINUZ)
    urllib.urlretrieve(initrdpath, INITRD)
    logger.debug("vmlinuz and initrd.img are located in %s" % BOOT_DIR)

    xmlstr = xmlstr.replace(params.get('diskpath', '/var/lib/libvirt/images'),
                            diskpath)
    xmlstr = xmlstr.replace('MACADDR', macaddr)
    xmlstr_bak = xmlstr

    xmlstr = xmlstr.replace('KERNEL', VMLINUZ)
    xmlstr = xmlstr.replace('INITRD', INITRD)

    xmlstr = xmlstr.replace('CUSTOMISO', bootcd)
    xmlstr = xmlstr.replace('KS', ks)

    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    installtype = params.get('type', 'define')
    if installtype == 'define':
        logger.info('define guest from xml description')
        try:
            domobj = conn.defineXML(xmlstr)
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s" \
                         % (e.message, e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

        logger.info('start installation guest ...')

        try:
            domobj.create()
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s" \
                         % (e.message, e.get_error_code()))
            logger.error("fail to start domain %s" % guestname)
            return 1
    elif installtype == 'create':
        logger.info('create guest from xml description')
        try:
            domobj = conn.createXML(xmlstr, 0)
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s" \
                         % (e.message, e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

    interval = 0
    while(interval < 2400):
        time.sleep(10)
        if installtype == 'define':
            state = domobj.info()[0]
            if(state == libvirt.VIR_DOMAIN_SHUTOFF):
                logger.info("guest installaton of define type is complete.")
                logger.info("boot guest vm off harddisk")
                xmlstr_bak = xmlstr_bak.replace("KERNEL", "")
                xmlstr_bak = xmlstr_bak.replace("INITRD", "")
                xmlstr_bak = xmlstr_bak.replace("ks=KS", "")
                xmlstr_bak = xmlstr_bak.replace("dev=\"cdrom\"", "dev=\"hd\"")
                xmlstr = xmlstr_bak
                ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return 1
                break
            else:
                interval += 10
                logger.info('%s seconds passed away...' % interval)
        elif installtype == 'create':
            guest_names = []
            ids = conn.listDomainsID()
            for id in ids:
                obj = conn.lookupByID(id)
                guest_names.append(obj.name())

            if guestname not in guest_names:
                logger.info("guest installation of create type is complete.")
                logger.info("define the vm and boot it up")
                xmlstr_bak = xmlstr_bak.replace("KERNEL", "")
                xmlstr_bak = xmlstr_bak.replace("INITRD", "")
                xmlstr_bak = xmlstr_bak.replace("ks=KS", "")
                xmlstr_bak = xmlstr_bak.replace("dev=\"cdrom\"", "dev=\"hd\"")
                xmlstr = xmlstr_bak
                ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return 1
                break
            else:
                interval += 10
                logger.info('%s seconds passed away...' % interval)

    if interval == 2400:
        if 'rhel3u9' in guestname:
            logger.info(
            "guest installaton will be destoryed forcelly for rhel3u9 guest")
            domobj.destroy()
            logger.info("boot guest vm off harddisk")
            xmlstr_bak = xmlstr_bak.replace("KERNEL", "")
            xmlstr_bak = xmlstr_bak.replace("INITRD", "")
            xmlstr_bak = xmlstr_bak.replace("ks=KS", "")
            xmlstr_bak = xmlstr_bak.replace("dev=\"cdrom\"", "dev=\"hd\"")
            xmlstr = xmlstr_bak
            ret =  prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger)
            if ret:
                logger.info("booting guest vm off harddisk failed")
                return 1
        else:
            logger.info("guest installation timeout 2400s")
            return 1
    else:
        logger.info("guest is booting up")

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 300

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully" % guestname)
            logger.info("the ip address of vm %s is %s" % (guestname, ip))
            break

    if timeout == 0:
        logger.info("fail to power on vm %s" % guestname)
        return 1

    time.sleep(60)

    return 0

def install_linux_iso_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')

    envfile = os.path.join(HOME_PATH, 'global.cfg')
    os_arch = guestos + "_" + guestarch
    envparser = env_parser.Envparser(envfile)
    ioslink = envparser.get_value("guest", os_arch + "_iso")
    isopath = '/var/lib/libvirt/images/' + ioslink.split('/')[-1]
    if os.path.exists(isopath):
        os.remove(isopath)

    diskpath = params.get('diskpath', "/var/lib/libvirt/images") + '/' + guestname
    (status, output) = commands.getstatusoutput(VIRSH_QUIET_LIST % guestname)
    if not status:
        logger.info("remove guest %s, and its disk image file" % guestname)
        (status, output) = commands.getstatusoutput(VM_STAT % guestname)
        if status:
            (status, output) = commands.getstatusoutput(VM_DESTROY % guestname)
            if status:
                logger.error("failed to destroy guest %s" % guestname)
                logger.error("%s" % output)
            else:
                (status, output) = commands.getstatusoutput(VM_UNDEFINE % guestname)
                if status:
                    logger.error("failed to undefine guest %s" % guestname)
                    logger.error("%s" % output)
        else:
            (status, output) = commands.getstatusoutput(VM_UNDEFINE % guestname)
            if status:
                logger.error("failed to undefine guest %s" % guestname)
                logger.error("%s" % output)

    if os.path.exists(diskpath):
        os.remove(diskpath)

    guest_dir = os.path.join(HOME_PATH, guestname)
    if os.path.exists(guest_dir):
        shutil.rmtree(guest_dir)

    if os.path.exists(diskpath):
        os.remove(diskpath)

    if os.path.exists(VMLINUZ):
        os.remove(VMLINUZ)
    if os.path.exists(INITRD):
        os.remove(INITRD)