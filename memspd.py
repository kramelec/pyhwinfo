import os
import sys
import time
import struct
import ctypes as ct
import ctypes.wintypes as wintypes
from ctypes import byref
from types import SimpleNamespace
import json

from cpuidsdk64 import *
from memory import *

# https://github.com/torvalds/linux/blob/fb4d33ab452ea254e2c319bac5703d1b56d895bf/drivers/i2c/busses/i2c-i801.c#L240
PCI_ID_SMBUS_INTEL = {
    0x31d4: {'name': 'INTEL_GEMINILAKE_SMBUS' },
    0x34a3: {'name': 'INTEL_ICELAKE_LP_SMBUS' },
    0x38a3: {'name': 'INTEL_ICELAKE_N_SMBUS' },
    0x3b30: {'name': 'INTEL_5_3400_SERIES_SMBUS' },
    0x43a3: {'name': 'INTEL_TIGERLAKE_H_SMBUS' },
    0x4b23: {'name': 'INTEL_ELKHART_LAKE_SMBUS' },
    0x4da3: {'name': 'INTEL_JASPER_LAKE_SMBUS' },
    0x51a3: {'name': 'INTEL_ALDER_LAKE_P_SMBUS' },
    0x54a3: {'name': 'INTEL_ALDER_LAKE_M_SMBUS' },
    0x5796: {'name': 'INTEL_BIRCH_STREAM_SMBUS' },
    0x5ad4: {'name': 'INTEL_BROXTON_SMBUS' },
    0x7722: {'name': 'INTEL_ARROW_LAKE_H_SMBUS' },
    0x7a23: {'name': 'INTEL_RAPTOR_LAKE_S_SMBUS' },
    0x7aa3: {'name': 'INTEL_ALDER_LAKE_S_SMBUS' },
    0x7e22: {'name': 'INTEL_METEOR_LAKE_P_SMBUS' },
    0x7f23: {'name': 'INTEL_METEOR_LAKE_PCH_S_SMBUS' },
    0x8c22: {'name': 'INTEL_LYNXPOINT_SMBUS' },
    0x8ca2: {'name': 'INTEL_WILDCATPOINT_SMBUS' },
    0x8d22: {'name': 'INTEL_WELLSBURG_SMBUS' },
    0x8d7d: {'name': 'INTEL_WELLSBURG_SMBUS_MS0' },
    0x8d7e: {'name': 'INTEL_WELLSBURG_SMBUS_MS1' },
    0x8d7f: {'name': 'INTEL_WELLSBURG_SMBUS_MS2' },
    0x9c22: {'name': 'INTEL_LYNXPOINT_LP_SMBUS' },
    0x9ca2: {'name': 'INTEL_WILDCATPOINT_LP_SMBUS' },
    0x9d23: {'name': 'INTEL_SUNRISEPOINT_LP_SMBUS' },
    0x9da3: {'name': 'INTEL_CANNONLAKE_LP_SMBUS' },
    0xa0a3: {'name': 'INTEL_TIGERLAKE_LP_SMBUS' },
    0xa123: {'name': 'INTEL_SUNRISEPOINT_H_SMBUS' },
    0xa1a3: {'name': 'INTEL_LEWISBURG_SMBUS' },
    0xa223: {'name': 'INTEL_LEWISBURG_SSKU_SMBUS' },
    0xa2a3: {'name': 'INTEL_KABYLAKE_PCH_H_SMBUS' },
    0xa323: {'name': 'INTEL_CANNONLAKE_H_SMBUS' },
    0xa3a3: {'name': 'INTEL_COMETLAKE_V_SMBUS' },
    0xae22: {'name': 'INTEL_METEOR_LAKE_SOC_S_SMBUS' },
    0xe322: {'name': 'INTEL_PANTHER_LAKE_H_SMBUS' },
    0xe422: {'name': 'INTEL_PANTHER_LAKE_P_SMBUS' },
}

LOCAL_SMBUS_MUTEX_NAME  = r"Local\Access_SMBUS.HTP.Method"
GLOBAL_SMBUS_MUTEX_NAME = r"Global\Access_SMBUS.HTP.Method"

g_mem_info = None
smb_addr = None
smb_vid = None
smb_ddr_ver = None

SMBUS_SPD_ADDRESS = 0x50       # Typical SPD address for first DIMM

DDR4_VDDQ_OFFSET = 0x0B       # DDR4 VDDQ info offset
DDR5_VDDQ_OFFSET = 0x0C       # DDR5 VDDQ info offset

I2C_WRITE  = 0
I2C_READ   = 1

# The SPD5 Hub device has totally 128 volatile registers as shown in Table 72
# source: https://www.ablic.com/en/doc/datasheet/dimm_serial_eeprom_spd/S34HTS08AB_E.pdf
SPD5_MR3   = 0x03   # Vendor ID (two bytes)
SPD5_MR11  = 0x0B   # I2C Legacy Mode Device Configuration
SPD5_MR18  = 0x12   # Device Configuration
SPD5_MR49  = 0x31   # TS Current Sensed Temperature (two bytes)

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

# https://github.com/memtest86plus/memtest86plus/blob/2f9b165eec4de20ec4b23725c90d3989517ee3fe/system/x86/i2c.c#L624
def _smbus_process():
    timeout = 0
    status = port_read_u1(smb_addr + SMBHSTSTS)
    if (status & 0x1F) != 0:
        port_write_u1(smb_addr + SMBHSTSTS, status & 0x1F)
        time.sleep(0.0005)
        status = port_read_u1(smb_addr + SMBHSTSTS)
        if (status & 0x1F) != 0:
            return 1

    cnt = port_read_u1(smb_addr + SMBHSTCNT)
    port_write_u1(smb_addr + SMBHSTCNT, cnt | SMBHSTCNT_START)

    # Some SMB controllers need this quirk.
    #if (extra_initial_sleep_for_smb_transaction) {
    #    usleep(extra_initial_sleep_for_smb_transaction);
    #}
    while True:
        time.sleep(0.0005)
        status = port_read_u1(smb_addr + SMBHSTSTS)
        if (status & 1) == 0:
            break
        timeout += 1
        if timeout >= 100:
            break

    if timeout >= 100:
        return 2

    if (status & 0x1C) != 0:
        return status

    status = port_read_u1(smb_addr + SMBHSTSTS)
    if (status & 0x1F) != 0:
        status = port_read_u1(smb_addr + SMBHSTSTS)
        port_write_u1(smb_addr + SMBHSTSTS, status)

    return 0

# https://github.com/memtest86plus/memtest86plus/blob/2f9b165eec4de20ec4b23725c90d3989517ee3fe/system/x86/i2c.c#L548
def _mem_spd_read_byte(addr, offset):
    global g_mutex, smb_addr, smb_vid, smb_ddr_ver
    if smb_ddr_ver == 4:
        raise NotImplementedError()
    elif smb_ddr_ver == 5:
        spd_page = offset // 0x80
        if smb_vid == PCI_VENDOR_ID_INTEL:
            # On Intel, we use the process call method because the SMBUS write command
            # is sometimes disabled by BIOS to avoid unexpected SPD corruption
            port_write_u1(smb_addr + SMBHSTADD, (addr << 1) | I2C_READ)  # set SMBUS addr
            port_write_u1(smb_addr + SMBHSTCMD, SPD5_MR11)             # set I2C Legacy Mode Device Configuration   # see doc: S34HTS08AB_E.pdf
            port_write_u1(smb_addr + SMBHSTDAT0, SETDIM(spd_page, 3))  # set page number   # see doc: S34HTS08AB_E.pdf
            port_write_u1(smb_addr + SMBHSTDAT1, 0)                    # ????
            port_write_u1(smb_addr + SMBHSTCNT, SMBHSTCNT_PROC_CALL)
            _smbus_process()
            # These dummy read are mandatory to terminate a Proc Call
            port_read_u1(smb_addr + SMBHSTDAT0)
            port_read_u1(smb_addr + SMBHSTDAT1)
        else:  # PCI_VENDOR_ID_AMD:
            # On AMD, we continue to use the standard smbus write command as it seems
            # more reliable than the process call method. This may be reevaluated later.
            port_write_u1(smb_addr + SMBHSTADD, (addr << 1) | I2C_WRITE)
            port_write_u1(smb_addr + SMBHSTCMD, SPD5_MR11)
            port_write_u1(smb_addr + SMBHSTDAT0, SETDIM(spd_page, 3))
            port_write_u1(smb_addr + SMBHSTCNT, SMBHSTCNT_BYTE_DATA)
            _smbus_process()
        spd_adr = offset - spd_page * 0x80
        spd_adr |= 0x80
    else:
        raise RuntimeError(f'ERROR: DDR_ver = {smb_ddr_ver} not supported')

    port_write_u1(smb_addr + SMBHSTADD, (addr << 1) | I2C_READ)
    port_write_u1(smb_addr + SMBHSTCMD, spd_adr)
    port_write_u1(smb_addr + SMBHSTCNT, SMBHSTCNT_BYTE_DATA)

    rc = _smbus_process()
    if rc == 0:
        return port_read_u1(smb_addr + SMBHSTDAT0)

    #print(f'err = 0x{rc:X}')
    return None

def mem_spd_read_byte(slot, offset):
    g_mutex.acquire()
    try:
        return _mem_spd_read_byte(SMBUS_SPD_ADDRESS + slot, offset)
    finally:
        g_mutex.release()

def _smbus_read_byte(addr, offset):
    port_write_u1(smb_addr + SMBHSTADD, (addr << 1) | I2C_READ)
    port_write_u1(smb_addr + SMBHSTCMD, offset)
    port_write_u1(smb_addr + SMBHSTCNT, SMBHSTCNT_BYTE_DATA)
    rc = _smbus_process()
    if rc == 0:
        return port_read_u1(smb_addr + SMBHSTDAT0)
    return None

def mem_spd_read_reg(slot, reg, size = 1):
    g_mutex.acquire()
    try:
        offset = reg & 0x7F   # read reg, not SPD page !!!
        val = _smbus_read_byte(SMBUS_SPD_ADDRESS + slot, offset)
        if size == 1:
            return val
        elif size == 2:
            val_HI = _smbus_read_byte(SMBUS_SPD_ADDRESS + slot, offset + 1)
            return (val_HI << 8) + val
        else:
            return None
    finally:
        g_mutex.release()

# https://github.com/memtest86plus/memtest86plus/blob/2f9b165eec4de20ec4b23725c90d3989517ee3fe/system/x86/i2c.c#L80
def find_smb_controller(check_pci_did = True):
    for bus in range(0, 0xFF, 0x80):
        for dev in range(0, 32):
            for fun in range(0, 8):
                vid = pci_cfg_read(bus, dev, fun, 0, '2')
                if not vid or vid == 0xFFFF:
                    continue
                if vid != PCI_VENDOR_ID_INTEL:
                    continue
                did = pci_cfg_read(bus, dev, fun, 2, '2')
                if did is None or did == 0xFFFF:
                    continue
                if check_pci_did:
                    if did not in PCI_ID_SMBUS_INTEL:
                        continue
                class_code  = pci_cfg_read(bus, dev, fun, 0x08 + 3, size = '1') # source: https://wiki.osdev.org/PCI
                subclass    = pci_cfg_read(bus, dev, fun, 0x08 + 2, size = '1')
                header_type = pci_cfg_read(bus, dev, fun, 0x0C + 2, size = '1')
                if header_type != 0:
                    continue
                if class_code != 0x0C:   # Serial Bus Controller   # source: https://wiki.osdev.org/PCI
                    continue
                if subclass != 0x05:     # SMBus Controller        # source: https://wiki.osdev.org/PCI
                    continue
                return (vid, did, bus, dev, fun)
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

if __name__ == "__main__":
    check_smbus_mutex()
    SdkInit(None, 0)

    g_mem_info = get_mem_info()
    g_mutex = CreateMutexW(GLOBAL_SMBUS_MUTEX_NAME)

    cpu = g_mem_info['cpu']
    if cpu['family'] != 6:
        raise RuntimeError(f'ERROR: Currently support only Intel processors')

    if cpu['model_id'] < INTEL_ALDERLAKE:
        raise RuntimeError(f'ERROR: Processor model 0x{cpu["model_id"]:X} not supported')

    smbus_dev = find_smb_controller(check_pci_did = True)
    if not smbus_dev:
        raise RuntimeError('ERROR: Cannot found PCH with SMBus controller')
    (vid, did, bus, dev, fun) = smbus_dev
    if vid == PCI_VENDOR_ID_INTEL:
        smbus_dev_name = PCI_ID_SMBUS_INTEL[did]
        print(f'Founded PCH device with SMBus: "{smbus_dev_name}"')
        print(f'VID = 0x{vid:04X}  DID = 0x{did:04X}  > {bus:02X}:{dev:02X}:{fun:02X}')
    else:
        raise RuntimeError('ERROR: Currently siupported only Intel platform')

    smb_vid = vid
    smb_ddr_ver = g_mem_info['memory']['mc'][0]['info']['DDR_ver']
    print(f'DDR_ver: {smb_ddr_ver}')

    offset = 0x10 + 4 * 4   # BAR4 - SMBus Addr
    smb_addr = pci_cfg_read(bus, dev, fun, offset, size = '4')
    if (smb_addr & 1) == 0:
        raise RuntimeError(f'ERROR: Cannot detect SMBus addr!')
    smb_addr -= 1
    print(f'Intel PCH SMBus addr = 0x{smb_addr:X}')

    spd_vid = mem_spd_read_reg(0, SPD5_MR3, 2)  # MR3 + MR4 => Vendor ID
    print(f'SPD Vendor ID = 0x{spd_vid:04X}')

    val = mem_spd_read_reg(0, SPD5_MR18)  # Device Configuration
    PEC_EN = get_bits(val, 0, 7)
    print(f'{PEC_EN=}')
    PAR_DIS = get_bits(val, 0, 6)
    print(f'{PAR_DIS=}')
    INF_SEL = get_bits(val, 0, 5)
    print(f'{INF_SEL=}')
    DEF_RD_ADDR_POINT_EN = get_bits(val, 0, 4)
    print(f'{DEF_RD_ADDR_POINT_EN=}')
    DEF_RD_ADDR_POINT_BL = get_bits(val, 0, 1)
    print(f'{DEF_RD_ADDR_POINT_BL=}')
    DEF_RD_ADDR_POINT_START = get_bits(val, 0, 2, 3)
    print(f'{DEF_RD_ADDR_POINT_START=:X}')

    if INF_SEL == 1:  # i3c protocol
        raise RuntimeError('ERROR: i3c protocol not supported!')

    val = mem_spd_read_byte(slot = 0, offset = 0)
    print(f'SPD[0] = 0x{val:02X}')
    val = mem_spd_read_byte(slot = 0, offset = 1)
    print(f'SPD[1] = 0x{val:02X}')
    val = mem_spd_read_reg(0, SPD5_MR49, 2)  # MR49 + MR50 => TS Current Sensed Temperature
    print(f'spd[MR49] = 0x{val:04X}  =>  {temp_decode(val)} degC')




