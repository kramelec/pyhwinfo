#
# Copyright (C) 2025 remittor
#

import os
import sys
import time
import copy
import struct
import ctypes as ct
import ctypes.wintypes as wintypes
from ctypes import byref
from types import SimpleNamespace
import json
from datetime import datetime

__author__ = 'remittor'

from cpuidsdk64 import *
from hardware import *
from jep106 import *

# Intel® 700 Series Chipset Family Platform Controller Hub
# ref: vol1: https://cdrdv2-public.intel.com/743835/743835-004.pdf
# ref: vol2: https://cdrdv2-public.intel.com/743845/743845_001.pdf

LOCAL_SMBUS_MUTEX_NAME  = r"Local\Access_SMBUS.HTP.Method"
GLOBAL_SMBUS_MUTEX_NAME = r"Global\Access_SMBUS.HTP.Method"

g_mem_info = None
g_mutex = None
g_smbus = {
    'port': None,
    'cfg_addr': None,   # list of [ bus, dev, fun ]
    'pch_vid': None,
    'pch_did': None,
    'pch_name': None,
    'ddr_ver': None,
}
smb_addr = None   # pci I/O port

SMBUS_SPD_DEVICE  = 0x50     # Typical SPD address for first DIMM
SMBUS_PMIC_DEVICE = 0x48     # ????????

I2C_WRITE  = 0
I2C_READ   = 1

# The SPD5 Hub device has totally 128 volatile registers as shown in Table 72
# source: https://www.ablic.com/en/doc/datasheet/dimm_serial_eeprom_spd/S34HTS08AB_E.pdf
SPD5_MR3   = 0x03   # Vendor ID (two bytes)
SPD5_MR5   = 0x05   # Device Capability
SPD5_MR11  = 0x0B   # I2C Legacy Mode Device Configuration
SPD5_MR18  = 0x12   # Device Configuration
SPD5_MR48  = 0x30   # Device Status
SPD5_MR49  = 0x31   # TS Current Sensed Temperature (two bytes)
SPD5_MR52  = 0x34   # Hub, Thermal and NVM Error Status

# i801 Hosts Addresses
SMBHSTSTS   = 0
SMBHSTCNT   = 2
SMBHSTCMD   = 3
SMBHSTADD   = 4
SMBHSTDAT0  = 5
SMBHSTDAT1  = 6
SMBBLKDAT   = 7
SMBPEC      = 8
SMBAUXSTS   = 12
SMBAUXCTL   = 13

# i801 Hosts Status register bits
SMBHSTSTS_BYTE_DONE     = 0x80
SMBHSTSTS_INUSE_STS     = 0x40
SMBHSTSTS_SMBALERT_STS  = 0x20
SMBHSTSTS_FAILED        = 0x10
SMBHSTSTS_BUS_ERR       = 0x08
SMBHSTSTS_DEV_ERR       = 0x04
SMBHSTSTS_INTR          = 0x02
SMBHSTSTS_HOST_BUSY     = 0x01

SMBHSTSTS_XXX = 0xFF & (~SMBHSTSTS_INUSE_STS)   # 0xBF : all flags except SMBHSTSTS_INUSE_STS

# i801 Hosts Control register bits
SMBHSTCNT_QUICK             = 0x00
SMBHSTCNT_BYTE              = 0x04
SMBHSTCNT_BYTE_DATA         = 0x08
SMBHSTCNT_WORD_DATA         = 0x0C
SMBHSTCNT_PROC_CALL         = 0x10
SMBHSTCNT_BLOCK_DATA        = 0x14
SMBHSTCNT_I2C_BLOCK_DATA    = 0x18
SMBHSTCNT_LAST_BYTE         = 0x20
SMBHSTCNT_START             = 0x40

# =================================================================================================

# source: S34HTS08AB_E.pdf   Table 82 Register MR11
# bit3 = 0 => 1 Byte Addressing for SPD5 Hub Device Memory
def _mem_spd_set_page(slot, page, check_status = True, ret_status = False):    
    if page < 0 or page >= 8:   # DDR5 SPD has 8 pages
        raise ValueError()    
    rc = smbus_write_u2(smb_addr, SMBUS_SPD_DEVICE + slot, SPD5_MR11, page)
    if not rc:
        return False
    if not check_status and not ret_status:
        return True
    status = smbus_read_u1(smb_addr, SMBUS_SPD_DEVICE + slot, SPD5_MR48)  # Device status
    if ret_status:
        return status
    status &= 0x7F  # exclude Pending IBI_STATUS = 0x80    # see S34HTS08AB_E.pdf (Table 107)
    return True if status == 0 else False

def _mem_spd_init(slot, page):
    status = _mem_spd_set_page(slot, page, ret_status = True)
    if status == False:
        return -1
    if (status & 0x80) != 0:
        print(f'detect Pending IBI_STATUS : status = 0x{status:X}')  # IBI = In Band Interrupt
    return 0

def _mem_spd_read_reg(slot, reg_offset, set_page = None):
    if set_page is not None:
        rc = _mem_spd_set_page(slot, set_page)
        if not rc:
            return None
    return smbus_read_u1(smb_addr, SMBUS_SPD_DEVICE + slot, reg_offset)

def mem_spd_read_reg(slot, reg_offset, size = 1):
    g_mutex.acquire()
    try:
        offset = reg_offset & 0x7F   # read reg, not SPD page !!!
        val = _mem_spd_read_reg(slot, offset, set_page = 0)
        if val is None:
            return None
        if size == 1:
            return val
        elif size == 2:
            val_HI = _mem_spd_read_reg(slot, offset + 1)
            if val_HI is None:
                return None
            return (val_HI << 8) + val
        else:
            return None
    finally:
        g_mutex.release()
    return None

def _mem_spd_get_status(slot, ret_raw = False):
    status = _mem_spd_read_reg(slot, SPD5_MR48)
    if not ret_raw:
        status &= 0x7F  # exclude Pending IBI_STATUS = 0x80    # see S34HTS08AB_E.pdf (Table 107)
    return status

def _mem_spd_read_byte(slot, offset):
    if offset < 0 or offset >= 0x80:
        raise ValueError()
    return smbus_read_u1(smb_addr, SMBUS_SPD_DEVICE + slot, offset | 0x80)

def mem_spd_read_byte(slot, offset):
    if offset < 0 or offset >= 0x400:   # DDR5 SPD of 1024 bytes len
        raise ValueError()
    g_mutex.acquire()
    try:
        spd_page = offset // 0x80
        rc = _mem_spd_set_page(slot, spd_page)
        if not rc:
            return None
        status = _mem_spd_get_status(slot)
        if status != 0:
            return None
        return _mem_spd_read_byte(slot, offset - spd_page * 0x80)
    finally:
        g_mutex.release()
    return None

def mem_spd_read_full(slot):
    buf = b''
    g_mutex.acquire()
    try:
        for spd_page in range(0, 8):
            rc = _mem_spd_set_page(slot, spd_page)
            if not rc:
                if spd_page == 0:
                    return None
                break
            status = _mem_spd_get_status(slot)
            if status != 0:
                break
            for offset in range(0, 0x80):
                val = _mem_spd_read_byte(slot, offset)
                if val is None:
                    break
                buf += int_encode(val, 1)
        # restore page 0
        _mem_spd_set_page(slot, page = 0)
    finally:
        g_mutex.release()
    return buf

def _mem_pmic_init(slot):
    rc = _mem_spd_set_page(slot, page = 0)
    if not rc:
        return None
    status = port_read_u1(smb_addr + SMBHSTSTS)
    if status != 0:
        print(f'ERROR: PMIC status = 0x{status:X}')
        return None
    port_write_u1(smb_addr + SMBHSTSTS, SMBHSTSTS_XXX)  # init SMBus state
    dev = 0x18   # https://i2cdevices.org/addresses/0x18
    port_write_u1(smb_addr + SMBHSTADD, (dev << 2) | I2C_READ)  # set SMBUS device
    cmd = 0x05   # ???????
    port_write_u1(smb_addr + SMBHSTCMD, cmd)
    cnt = port_read_u1(smb_addr + SMBHSTCNT)
    print(f'cnt = 0x{cnt:X}')
    port_write_u1(smb_addr + SMBHSTCNT, SMBHSTCNT_START + SMBHSTCNT_WORD_DATA)
    code = port_read_u1(smb_addr + SMBHSTSTS)
    print(f'CODE = 0x{code:X}')
    code = port_read_u1(smb_addr + SMBHSTSTS)
    print(f'CODE = 0x{code:X}')
    port_write_u1(smb_addr + SMBHSTSTS, code)
    return code

# source: https://www.richtek.com/assets/product_file/RTQ5119A/DSQ5119A-02.pdf
PMIC_RICHTEK_R1A = 0x1A  # VIN state    (RW)
PMIC_RICHTEK_R1B = 0x1B  # VIN state    (RW)
PMIC_RICHTEK_R30 = 0x30  # ADC state    (RW)     # ADC (Analog to Digital Conversion)
PMIC_RICHTEK_R31 = 0x31  # ADC Read Out (RO)
PMIC_RICHTEK_R3B = 0x3B  # Revision ID
PMIC_RICHTEK_R3C = 0x3C  # Vendor ID (2 bytes)

PMIC_RICHTEK_ADC_ENABLE  = 0x80  # look desc of PMIC_RICHTEK_R30

# source: DSQ5119A-02.pdf   page    Table: "R30 - ADC Enable"
PMIC_RICHTEK_ADC_SWA      = 0x00
PMIC_RICHTEK_ADC_SWB      = 0x01
PMIC_RICHTEK_ADC_SWC      = 0x02
PMIC_RICHTEK_ADC_SWD      = 0x03
PMIC_RICHTEK_ADC_NULL     = 0x04   # Reserved
PMIC_RICHTEK_ADC_VIN_BULK = 0x05
PMIC_RICHTEK_ADC_VIN_MGMT = 0x06
PMIC_RICHTEK_ADC_VIN_BIAS = 0x07
PMIC_RICHTEK_ADC_LVDO_18V = 0x08   # 1.8V
PMIC_RICHTEK_ADC_LVDO_10V = 0x09   # 1.0V

def mem_pmic_read(slot):
    out = { "smbus_dev": SMBUS_PMIC_DEVICE + slot }
    g_mutex.acquire()
    try:
        rc = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0)
        if rc != 0:
            g_mutex.release()
            time.sleep(0.02)
            g_mutex.acquire()
            rc = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0)
            if rc != 0:
                print('ERROR: PMIC not inited!')
                return None
        vid_HI = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R3C)  # PMIC Vendor ID
        vid_LO = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R3C + 1)
        vid = jep106decode(vid_HI, vid_LO)
        vendor = jep106[vid] if vid in jep106 else None
        print(f'PMIC Vendor ID = 0x{vid:04X} "{vendor}"')
        out['vid'] = vid
        out['vendor'] = vendor 
        
        if vid != 0x0A0C:   # Richtek
            print(f'ERROR: pmic 0x{vid:04X} not supported')
            return out
        
        val = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R3B)  # PMIC Revision ID
        cur_capab = get_bits(val, 0, 0)     # PMIC Current Capability
        rev_minor = get_bits(val, 0, 1, 3)  # Minor Revision ID
        rev_major = get_bits(val, 0, 4, 5)  # Minor Revision ID
        print(f'PMIC Revision = {rev_major}.{rev_minor}  [{cur_capab}]')
        out['revision'] = f'{rev_major}.{rev_minor}'
        out['current_capability'] = cur_capab

        def get_pmic_adc_command(adc_sel, upd_freq = 1):
            ADC_REGISTER_UPDATE_FREQUENCY = [ 1, 2, 4, 8 ]  # milisec table  # ref: DSQ5119A-02.pdf  page 106  
            if upd_freq in ADC_REGISTER_UPDATE_FREQUENCY:
                updFreq = ADC_REGISTER_UPDATE_FREQUENCY.index(upd_freq)  # select code for 1 ms
            else:
                raise RuntimeError()
            return PMIC_RICHTEK_ADC_ENABLE | (SETDIM(adc_sel, 4) << 3) | updFreq  # ref: "ADC Select" in doc DSQ5119A-02.pdf
        
        def pmic_read_adc(adc_sel):
            # prepare R31 for NULL value
            cmd = get_pmic_adc_command(PMIC_RICHTEK_ADC_NULL)
            smbus_write_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R30, cmd)
            ok = False
            for trynum in range(0, 4):
                state = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R30)
                if state != cmd:
                    return None  # ERROR
                value = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R31)
                if value == 0:
                    ok = True
                    break
            if not ok:
                return None
            # process requested ADC reading
            cmd = get_pmic_adc_command(adc_sel)
            smbus_write_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R30, cmd)
            for trynum in range(0, 4):
                state = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R30)
                if state != cmd:
                    return None  # ERROR
                value = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R31)
                if value != 0:
                    return value
            return None

        def voltage_decode(val, mult = 0.015):  # look doc: DSQ5119A-02.pdf  page 107  table "R31 - ADC Read"
            if val is None:
                return None
            val = val * mult
            return round(val, 3)

        saved_st = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R30)  # ADC state
        if saved_st is None:
            return out
        print(f'PMIC state = 0x{saved_st:02X} (SAVED)')
        try:
            swa = pmic_read_adc(PMIC_RICHTEK_ADC_SWA)
            swa = voltage_decode(swa)
            print(f'PMIC[SWA] = {swa} V')
            out['SWA'] = swa

            swb = pmic_read_adc(PMIC_RICHTEK_ADC_SWB)
            swb = voltage_decode(swb)
            print(f'PMIC[SWB] = {swb} V')
            out['SWB'] = swb

            swc = pmic_read_adc(PMIC_RICHTEK_ADC_SWC)
            swc = voltage_decode(swc)
            print(f'PMIC[SWC] = {swc} V')
            out['SWC'] = swc

            swd = pmic_read_adc(PMIC_RICHTEK_ADC_SWD)
            swd = voltage_decode(swd)
            print(f'PMIC[SWD] = {swd} V')
            out['SWD'] = swd

            lvdo = pmic_read_adc(PMIC_RICHTEK_ADC_LVDO_18V)
            lvdo = voltage_decode(lvdo)
            print(f'PMIC[LVDO 1.8V] = {lvdo} V')
            out['1.8V'] = lvdo

            lvdo = pmic_read_adc(PMIC_RICHTEK_ADC_LVDO_10V)
            lvdo = voltage_decode(lvdo)
            print(f'PMIC[LVDO 1.0V] = {lvdo} V')
            out['1.0V'] = lvdo

            vin = pmic_read_adc(PMIC_RICHTEK_ADC_VIN_BULK)
            vin = voltage_decode(vin, 0.070)
            print(f'PMIC[VIN] = {vin} V')
            out['VIN'] = vin
        finally:
            # restore ADC state
            smbus_write_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R30, saved_st)
            print(f'PMIC state restored (value = 0x{saved_st:02X})')
        '''
        x1 = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x1A)
        x2 = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x1B)
        smbus_write_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x1A, 0x02)
        smbus_write_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x1B, 0x45)
        val_LO = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x1A)
        val_HI = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x0C)
        value = (val_HI << 8) + val_LO
        print(f'pmic[1A_0C] = 0x{val_LO:02X}  0x{val_HI:02X}')
        smbus_write_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x1A, x1)
        smbus_write_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, 0x1B, x2)
        '''
    finally:
        g_mutex.release()
    return out
    
# =================================================================================================

def read_smbus_info(bus, dev, fun, full_info = True):
    class_code = pci_cfg_read(bus, dev, fun, 0x0B, size = '1') # ref: 743845_001.pdf  section: Base Class Code (BCC)—Offset Bh
    if class_code != 0x0C:   # Serial Bus Controller   # source: https://wiki.osdev.org/PCI
        return None
    subclass = pci_cfg_read(bus, dev, fun, 0x0A, size = '1') # ref: 743845_001.pdf  section: Sub Class Code (SCC)—Offset Ah
    if subclass != 0x05:     # SMBus Controller        # source: https://wiki.osdev.org/PCI
        return None
    #header_type = pci_cfg_read(bus, dev, fun, 0x0E, size = '1')
    #if header_type != 0:
    #    return None
    vid = pci_cfg_read(bus, dev, fun, 0, '2')   # ref: 743845_001.pdf  section: Vendor ID (VID)—Offset 0h
    did = pci_cfg_read(bus, dev, fun, 2, '2')   # ref: 743845_001.pdf  section: Device ID (DID)—Offset 2h
    smbus = { }
    smbus['cfg_addr'] = [ bus, dev, fun ]
    smbus['pch_vid'] = vid
    smbus['pch_did'] = did
    smbus['pch_name'] = PCI_ID_SMBUS_INTEL[did]['name'] if did and did in PCI_ID_SMBUS_INTEL else None
    # ref: 743845_001.pdf  section: SMB Base Address (SBA)—Offset 20h
    offset = 0x10 + 4 * 4   # BAR4 - SMBus Addr
    smbus['port'] = pci_cfg_read(bus, dev, fun, offset, size = '4')
    if full_info:
        # ref: 743845_001.pdf  section: Command (CMD)—Offset 4h
        offset = 0x4
        CMD = pci_cfg_read(bus, dev, fun, offset, size = 2)
        if CMD:
            smbus['MSE']  = get_bits(CMD, 0, 1)  # Memory Space Enable (MSE): 1= Enables memory mapped config space.
            smbus['IOSE'] = get_bits(CMD, 0, 0)  # I/O Space Enable (IOSE): 1= enables access to the SM Bus I/O space registers as defined by the Base Address Register.
        # ref: 743845_001.pdf  section: SMBus Memory Base Address_31_0
        offset = 0x10
        SMBMBAR = pci_cfg_read(bus, dev, fun, offset, size = 4)
        if SMBMBAR:
            smbus['MSI']    = get_bits(SMBMBAR, 0, 0)     # Memory Space Indicator (MSI): Indicates that the SMB logic is memory mapped.
            smbus['ADDRNG'] = get_bits(SMBMBAR, 0, 1, 2)  # Address Range (ADDRNG): Indicates that this SMBMBAR can be located anywhere in 64 bit address space
            smbus['PREF']   = get_bits(SMBMBAR, 0, 3)     # Prefetchable (PREF): Hardwired to 0. Indicated that SMBMBAR is not pre- fetchable
            smbus['HARDWIRED_0'] = get_bits(SMBMBAR, 0, 4, 7)   # Hardwired_0 (HARDWIRED_0): Hardwired to 0.
            smbus_mem_addr = get_bits(SMBMBAR, 0, 8, 31)
            # ref: 743845_001.pdf  section: SMBus Memory Base Address_63_32
            smbus_mem_addr_HI = pci_cfg_read(bus, dev, fun, 0x14, size = '4')
            if smbus_mem_addr_HI is not None:
                smbus_mem_addr = (smbus_mem_addr_HI << 32) + (smbus_mem_addr << 8)
                smbus['MEMIO_ADDR'] = smbus_mem_addr
        # ref: 743845_001.pdf  section: Host Configuration (HCFG)—Offset 40h
        offset = 0x40
        HCFG = pci_cfg_read(bus, dev, fun, offset, size = 4)
        if HCFG:
            smbus['I2C_EN'] = get_bits(HCFG, 0, 2)   # I2C_EN (I2CEN): When this bit is 1, the PCH is enabled to communicate with I2C devices. This will change the formatting of some commands. When this bit is 0, behavior is for SMBus.
    return smbus

# https://github.com/memtest86plus/memtest86plus/blob/2f9b165eec4de20ec4b23725c90d3989517ee3fe/system/x86/i2c.c#L80
def find_smb_controllers():
    res = [ ]
    for bus in range(0, 0xFF, 0x80):
        for dev in range(0, 32):
            for fun in range(0, 8):
                smb = read_smbus_info(bus, dev, fun)
                if smb:
                    res.append( smb )
    return res

def find_spd_smbus(check_pci_did = True, check_spd = True):
    global smb_addr
    saved_smb_addr = smb_addr
    try:
        smb_list = find_smb_controllers()
        if smb_list:
            for smb in smb_list:
                (bus, dev, fun) = tuple(smb['cfg_addr'])
                vid = smb['pch_vid']
                if vid != PCI_VENDOR_ID_INTEL:
                    continue
                did = smb['pch_did']
                smbus_addr = smb['port']
                if smbus_addr is None or did is None:
                    continue
                print(f'Detect SMBus on [{bus:02X}:{dev:02X}:{fun:02X}] addr = 0x{smbus_addr:X}, VID = 0x{vid:04X}, DID = 0x{did:04X}')
                print(f'INFO: SMBus MSE = {smb["MSE"]}')
                if smb['MEMIO_ADDR']:
                    print(f'INFO: SMBus Mem Addr = 0x{smb["MEMIO_ADDR"]:X}')
                if (smbus_addr & 1) == 0:
                    print(f'WARN: Wrong SMBus addr = 0x{smbus_addr:X}')
                    continue  # incorret value
                if smb['I2C_EN'] == 1:
                    print(f'WARN: SMBus I2C_EN = 1')
                    continue  # incorret value
                if smb['IOSE'] == 0: 
                    print(f'WARN: SMBus IOSE = 0')
                    continue  # incorret value
                if did not in PCI_ID_SMBUS_INTEL and check_pci_did:
                    print(f'WARN: unsupported DID = 0x{did:04X}')
                    continue
                if check_spd:
                    smb_addr = smbus_addr - 1
                    vendorid = None
                    for slot in range(0, 4):
                        vendorid = mem_spd_read_reg(slot, SPD5_MR3, 2)  # MR3 + MR4 => Vendor ID
                        if vendorid is not None and vendorid > 0:
                            break
                    if not vendorid:
                        print(f'WARN: wrong SMBus addr = 0x{smbus_addr:X}  Reason: VendorID = {vendorid}')
                        continue  # Cannot read VendorID from SPD
                return smb
    finally:
        smb_addr = saved_smb_addr
    return None

def check_smbus_mutex():
    rc = 0
    mtx = OpenMutexW(LOCAL_SMBUS_MUTEX_NAME, throwable = False)
    if mtx.handle:
        print(f'Mutex "{LOCAL_SMBUS_MUTEX_NAME}" opened! (already exist)')
    else:
        mtx = CreateMutexW(GLOBAL_SMBUS_MUTEX_NAME, throwable = False)
        if mtx.handle:
            print(f'Mutex "{LOCAL_SMBUS_MUTEX_NAME}" created!')
        else:
            print(f'Mutex "{LOCAL_SMBUS_MUTEX_NAME}" cannot opened and cteated!')
            rc = -1
    mtx = OpenMutexW(GLOBAL_SMBUS_MUTEX_NAME, throwable = False)
    if mtx.handle:
        print(f'Mutex "{GLOBAL_SMBUS_MUTEX_NAME}" opened! (already exist)')
    else:
        mtx = CreateMutexW(GLOBAL_SMBUS_MUTEX_NAME, throwable = False)
        if mtx.handle:
            print(f'Mutex "{GLOBAL_SMBUS_MUTEX_NAME}" created!')
        else:
            print(f'Mutex "{GLOBAL_SMBUS_MUTEX_NAME}" cannot opened and cteated!')
            rc = -2
    return rc

def CHKBIT(val, bit):
    mask = 1 << bit
    return False if (val & mask) == 0 else True

def temp_decode(val):  # see doc: S34HTS08AB_E.pdf  page 63  table 99  (Thermal Register - Low Byte and High Byte)
    val >>= 2
    sign = CHKBIT(val, 10)
    temp = SETDIM(val, 10) / 4
    return -temp if sign else temp

def get_mem_spd_info(slot, mem_info: dict, with_pmic = True):
    global g_mem_info, g_mutex, g_smbus, smb_addr
    spd = { }
    
    if not g_mutex:
        check_smbus_mutex()
        mutex = CreateMutexW(GLOBAL_SMBUS_MUTEX_NAME)
        if not mutex:
            raise RuntimeError(f'Cannot open or create global mutex "{GLOBAL_SMBUS_MUTEX_NAME}"')
        g_mutex = mutex

    if mem_info is None:
        raise ValueError('Argument mem_info cannot be None!')
    
    g_mem_info = copy.deepcopy(mem_info)

    cpu = g_mem_info['cpu']
    if cpu['family'] != 6:
        raise RuntimeError(f'ERROR: Currently support only Intel processors')

    if cpu['model_id'] < INTEL_ALDERLAKE:
        raise RuntimeError(f'ERROR: Processor model 0x{cpu["model_id"]:X} not supported')

    if not g_smbus['cfg_addr']:
        _smb = find_spd_smbus(check_pci_did = True, check_spd = True)
        if not _smb:
            print('ERROR: Cannot found PCH with SMBus controller')
            return None
        smb = _smb
    
    if not smb_addr:
        vid = smb['pch_vid']
        if vid == PCI_VENDOR_ID_INTEL:
            (bus, dev, fun) = tuple(smb['cfg_addr'])
            did = smb['pch_did']
            smbus_dev_name = PCI_ID_SMBUS_INTEL[did]['name']
            print(f'Founded PCH device with SMBus: "{smbus_dev_name}"')
            #print(f'VID = 0x{vid:04X}  DID = 0x{did:04X} >>> {bus:02X}:{dev:02X}:{fun:02X}')
        else:
            raise RuntimeError('ERROR: Currently siupported only Intel platform')

        if not smb['port']:
            return None
        
        g_smbus = smb
        smb_addr = g_smbus['port'] - 1
        print(f'Intel PCH SMBus addr = 0x{smb_addr:X}')
        g_smbus["ddr_ver"] = g_mem_info['memory']['mc'][0]['DDR_ver']
        print(f'DDR_ver: {g_smbus["ddr_ver"]}')

    vendorid = mem_spd_read_reg(slot, SPD5_MR3, 2)  # MR3 + MR4 => Vendor ID
    if not vendorid:
        print(f'WARN: Cannot read VendorID from SPD#{slot}')
        return None

    spd_vid = jep106decode(vendorid)

    print(f'Scan DIMM slot #{slot}')
    spd["slot"] = slot
    spd["smbus_dev"] = SMBUS_SPD_DEVICE + slot
    spd["spd_vid"] = spd_vid
    spd["spd_vendor"] = jep106[spd_vid] if spd_vid in jep106 else None
    print(f'SPD Vendor ID = 0x{spd_vid:04X} "{spd["spd_vendor"]}"')

    val = mem_spd_read_reg(slot, SPD5_MR18)  # Device Configuration
    PEC_EN = get_bits(val, 0, 7)
    #print(f'{PEC_EN=}')
    PAR_DIS = get_bits(val, 0, 6)
    #print(f'{PAR_DIS=}')
    INF_SEL = get_bits(val, 0, 5)
    #print(f'{INF_SEL=}')
    DEF_RD_ADDR_POINT_EN = get_bits(val, 0, 4)
    #print(f'{DEF_RD_ADDR_POINT_EN=}')
    DEF_RD_ADDR_POINT_BL = get_bits(val, 0, 1)
    #print(f'{DEF_RD_ADDR_POINT_BL=}')
    DEF_RD_ADDR_POINT_START = get_bits(val, 0, 2, 3)
    #print(f'{DEF_RD_ADDR_POINT_START=:X}')

    if INF_SEL == 1:  # i3c protocol
        raise RuntimeError('ERROR: i3c protocol not supported!')

    temp = mem_spd_read_reg(slot, SPD5_MR49, 2)  # MR49 + MR50 => TS Current Sensed Temperature
    if temp is not None:
        temp = temp_decode(temp)
        #print(f'spd[{slot}][MR49] = 0x{temp:04X}  =>  {temp} degC')
        spd['temp'] = temp

    spd['PMIC'] = None
    spd['spd_eeprom'] = ""
    spd['SPD'] = None

    spd_data = mem_spd_read_full(slot)
    #print(f'SPD[0] = {spd_data.hex()}')
    if spd_data and len(spd_data) >= 1024:
        spd['spd_eeprom'] = spd_data.hex()

    if with_pmic:
        pmic = mem_pmic_read(slot)
        spd['PMIC'] = pmic
        
    return spd

def get_mem_spd_all(mem_info: dict, with_pmic = True, allinone = True):
    global g_mem_info, g_mutex, g_smbus, smb_addr
    from spd_eeprom import spd_eeprom_decode
    if not mem_info:
        from memory import get_mem_info
        mem_info = get_mem_info()
    dimm = { }
    dimm['SMBus'] = { }
    dimm['DIMM'] = [ ]
    for slot in range(0, 4):
        spd = get_mem_spd_info(slot, mem_info, with_pmic = with_pmic)
        if not spd:
            continue
        if not dimm['SMBus']:
            dimm['SMBus'] = g_smbus.copy()
        spd['SPD'] = spd_eeprom_decode(spd['spd_eeprom'])
        dimm['DIMM'].append(spd)
    if allinone:
        mem_info['memory']['SMBus'] = copy.deepcopy(dimm['SMBus'])
        mem_info['memory']['DIMM']  = copy.deepcopy(dimm['DIMM'])
        mem_info['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return mem_info
    return dimm

if __name__ == "__main__":
    from memory import get_mem_info
    fn = 'IMC.json'
    os.remove(fn) if os.path.exists(fn) else None
    SdkInit(None, verbose = 0)
    mem_info = get_mem_spd_all(None, with_pmic = True, allinone = True)
    with open(fn, 'w') as file:
        json.dump(mem_info, file, indent = 4)
    
