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
from datetime import timedelta

__author__ = 'remittor'

from cpuidsdk64 import *
from hardware import *
from jep106 import *
from pci_ids import *

# Intel® 700 Series Chipset Family Platform Controller Hub
# ref: vol1: https://cdrdv2-public.intel.com/743835/743835-004.pdf
# ref: vol2: https://cdrdv2-public.intel.com/743845/743845_001.pdf

LOCAL_SMBUS_MUTEX_NAME  = r"Local\Access_SMBUS.HTP.Method"
GLOBAL_SMBUS_MUTEX_NAME = r"Global\Access_SMBUS.HTP.Method"

I2C_WRITE  = 0
I2C_READ   = 1

# i801 Hosts Addresses  # ref: 743845_001.pdf  section: SMBus I/O and Memory Mapped I/O Registers Summary
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

STATUS_ERROR_FLAGS = SMBHSTSTS_FAILED | SMBHSTSTS_BUS_ERR | SMBHSTSTS_DEV_ERR
STATUS_FLAGS       = SMBHSTSTS_BYTE_DONE | SMBHSTSTS_INTR | STATUS_ERROR_FLAGS
SMBHSTSTS_XXX = (SMBHSTSTS_INUSE_STS ^ 0xFF)   # 0xBF : all flags except SMBHSTSTS_INUSE_STS

# i801 Hosts Control register bits
SMBHSTCNT_QUICK             = 0x00
SMBHSTCNT_INTREN            = 0x01
SMBHSTCNT_KILL              = 0x02
SMBHSTCNT_BYTE              = 0x04
SMBHSTCNT_BYTE_DATA         = 0x08
SMBHSTCNT_WORD_DATA         = 0x0C
SMBHSTCNT_PROC_CALL         = 0x10
SMBHSTCNT_BLOCK_DATA        = 0x14
SMBHSTCNT_I2C_BLOCK_DATA    = 0x18
SMBHSTCNT_LAST_BYTE         = 0x20
SMBHSTCNT_START             = 0x40
SMBHSTCNT_PEC_EN            = 0x80

# Auxiliary control register bits, ICH4+ only
SMBAUXCTL_CRC     = 0x01
SMBAUXCTL_E32B    = 0x02 

# =================================================================================================

class SMBus():
    def __init__(self, port):
        self.info = { }
        self.debug = False
        self.method = 0
        self.port = port
        self.sts = 0
        self.status = 0
        self.timedout = False
        self.mutex = None
        self.mutex_wait_timeout = 2000
        self.inuse_timeout = 500
        self.lock_status = SMBHSTSTS_INUSE_STS
        self.init_status = SMBHSTSTS_INUSE_STS # actuality only for method 0
        self.wait_intr_timeout = 100
        self.init_mutex()

    def acquire(self, throwable = True):
        self.mutex.acquire(wait_ms = self.mutex_wait_timeout, throwable = throwable)
        is_inuse = True
        try:
            # Wait for device to be unlocked by BIOS/ACPI
            # Linux doesn't do this, since some BIOSes might not unlock it
            start_time = datetime.now()
            while datetime.now() - start_time <= timedelta(milliseconds = self.inuse_timeout):
                self.sts = port_read_u1(self.port + SMBHSTSTS)
                is_inuse = (self.sts & SMBHSTSTS_INUSE_STS) != 0
                if not is_inuse:
                    break
            if not is_inuse and self.lock_status is not None:
                port_write_u1(self.port + SMBHSTSTS, self.lock_status ^ 0xFF)
        finally:    
            if is_inuse:
                print(f'ERROR: SMBus device is in use by BIOS/ACPI')
                self.mutex.release()
                if throwable:
                    raise RuntimeError(f'ERROR: SMBus device is in use by BIOS/ACPI')
                return False
        return True

    def release(self):
        try:
            # Unlock the SMBus device for use by BIOS/ACPI, and clear status flags
            # if not done already.
            port_write_u1(self.port + SMBHSTSTS, SMBHSTSTS_INUSE_STS | STATUS_FLAGS)
        finally:
            self.mutex.release()

    def check_pre(self):
        # Make sure the SMBus host is ready to start transmitting.
        sts = port_read_u1(self.port + SMBHSTSTS)
        self.sts = sts
        if (sts & SMBHSTSTS_HOST_BUSY) != 0:
            print(f'ERROR: SMBus: check_pre: SMBus on port 0x{self.port:04X} is busy, cannot use it! (sts = 0x{sts:02X})')
            return False
        sts &= STATUS_FLAGS
        if sts != 0:
            if self.debug:
                print(f'SMBus: Clearing status flags: 0x{sts:02X}');
            port_write_u1(self.port + SMBHSTSTS, sts)
            sts = port_read_u1(self.port + SMBHSTSTS)
            self.sts = sts
            if (sts & STATUS_FLAGS) != 0:
                print(f'ERROR: SMBus: cannot clear status (sts = 0x{self.sts:02X})')
                return False
        return True
     
    def kill(self):
        # try to stop the current command
        port_write_u1(self.port + SMBHSTCNT, SMBHSTCNT_KILL)
        time.sleep(0.01)
        port_write_u1(self.port + SMBHSTCNT, 0)
        # Check if it worked
        sts = port_read_u1(self.port + SMBHSTSTS)
        self.sts = sts
        if (sts & SMBHSTSTS_HOST_BUSY) != 0 or (sts & SMBHSTSTS_FAILED) == 0:
            print(f'WARN: SMBus: Failed terminating the transaction')

    def wait_intr(self):
        self.timedout = False
        #time.sleep(0.001)
        start_time = datetime.now()
        while True:            
            sts = port_read_u1(self.port + SMBHSTSTS)
            self.sts = sts
            self.status = sts & (STATUS_ERROR_FLAGS | SMBHSTSTS_INTR)
            if (self.status & SMBHSTSTS_HOST_BUSY) == 0:
                if (sts & STATUS_ERROR_FLAGS) != 0:
                    print(f'WARN: wait_intr: detect ERROR = 0x{sts:02X}')
                    return False
                if (sts & SMBHSTSTS_INTR) != 0:                    
                    return True
                #print(f'WARN: wait_intr: not detect INTR (sts = 0x{sts:02X})')
                #return True
            if datetime.now() - start_time > timedelta(milliseconds = self.wait_intr_timeout):
                self.timedout = True
                print(f'WARN: wait_intr: timed out (sts = 0x{sts:02X})')
                return False
            #time.sleep(0.25 / 1000)
        return False

    def check_post(self):
        '''
        * If the SMBus is still busy, we give up
        * Note: This timeout condition only happens when using polling transactions.
        * For interrupt operation, NAK/timeout is indicated by DEV_ERR.
        '''
        if self.timedout:
            # try to stop the current command
            cnt = port_read_u1(self.port + SMBHSTCNT)
            port_write_u1(self.port + SMBHSTCNT, cnt | SMBHSTCNT_KILL)
            print(f'WARN: SMBus: kill')
            time.sleep(1)
            cnt = port_read_u1(self.port + SMBHSTCNT)
            port_write_u1(self.port + SMBHSTCNT, cnt | (SMBHSTCNT_KILL ^ 0xFF))
            port_write_u1(self.port + SMBHSTSTS, STATUS_FLAGS)
            return False
        try:
            if (self.status & SMBHSTSTS_FAILED) != 0:
                return False
            if (self.status & SMBHSTSTS_DEV_ERR) != 0:
                return False
            if (self.status & SMBHSTSTS_BUS_ERR) != 0:
                return False
        finally:
            # Clear status flags
            port_write_u1(self.port + SMBHSTSTS, self.status)
        return True

    def do_transaction(self, xact):
        cnt = port_read_u1(self.port + SMBHSTCNT)
        port_write_u1(self.port + SMBHSTCNT, cnt & (SMBHSTCNT_INTREN ^ 0xFF))

        # the current contents of SMBHSTCNT can be overwritten, since PEC, SMBSCMD are passed in xact 
        port_write_u1(self.port + SMBHSTCNT, SMBHSTCNT_START | xact)

        rc = self.wait_intr()
        # restore previous HSTCNT, enabling interrupts if previously enabled
        #port_write_u1(self.port + SMBHSTCNT, cnt)   # FIXME
        return self.check_post()

    def do_command(self, direction, xact, dev, command, value):
        self.timedout = False
        self.status = 0
        if not self.check_pre():
            return False if direction == I2C_WRITE else None

        if xact == SMBHSTCNT_QUICK:
            port_write_u1(self.port + SMBHSTADD, (dev << 1) | direction)
        elif xact == SMBHSTCNT_BYTE:
            port_write_u1(self.port + SMBHSTADD, (dev << 1) | direction)
            if direction == I2C_WRITE:
                port_write_u1(self.port + SMBHSTCMD, command)
        elif xact == SMBHSTCNT_BYTE_DATA:
            port_write_u1(self.port + SMBHSTADD, (dev << 1) | direction)
            port_write_u1(self.port + SMBHSTCMD, command)
            if direction == I2C_WRITE:
                port_write_u1(self.port + SMBHSTDAT0, value)
        elif xact == SMBHSTCNT_WORD_DATA:
            port_write_u1(self.port + SMBHSTADD, (dev << 1) | direction)
            port_write_u1(self.port + SMBHSTCMD, command)
            if direction == I2C_WRITE:
                port_write_u1(self.port + SMBHSTDAT0, value & 0xFF)
                port_write_u1(self.port + SMBHSTDAT1, (value >> 8) & 0xFF)
        elif xact == SMBHSTCNT_PROC_CALL:
            port_write_u1(self.port + SMBHSTADD, (dev << 1) | direction)
            port_write_u1(self.port + SMBHSTCMD, command)
            if value is not None:
                port_write_u1(self.port + SMBHSTDAT0, value & 0xFF)
                port_write_u1(self.port + SMBHSTDAT1, (value >> 8) & 0xFF)
        else:
            raise RuntimeError(f'Unsupported transaction = 0x{xact:02X}')

        aux = port_read_u1(self.port + SMBAUXCTL)
        port_write_u1(SMBAUXCTL, aux & (SMBAUXCTL_CRC ^ 0xFF))
        
        self.status = 0
        rc = self.do_transaction(xact)
        
        # Some BIOSes don't like it when PEC is enabled at reboot or resume time, so we forcibly disable it after every transaction. Turn off E32B for the same reason.
        aux = port_read_u1(self.port + SMBAUXCTL)
        port_write_u1(self.port + SMBAUXCTL, aux & ((SMBAUXCTL_CRC | SMBAUXCTL_E32B) ^ 0xFF))
        
        if not rc:
            print(f'ERROR: do_command: Failed do_transaction: status = 0x{self.sts:02X}')
            #self.kill()
            return False if direction == I2C_WRITE else None

        if direction == I2C_WRITE or xact == SMBHSTCNT_QUICK:
            return True

        if direction == I2C_READ:
            if xact in [ SMBHSTCNT_BYTE, SMBHSTCNT_BYTE_DATA ]:
                return port_read_u1(self.port + SMBHSTDAT0)
            elif xact in [ SMBHSTCNT_WORD_DATA, SMBHSTCNT_PROC_CALL ]:
                val_LO = port_read_u1(self.port + SMBHSTDAT0)
                val_HI = port_read_u1(self.port + SMBHSTDAT1)
                return (val_HI << 8) + val_LO
            return None

        return False if direction == I2C_WRITE else None

    def read_byte(self, dev, command):
        if self.debug:
            print(f'INFO: SMBus: read_byte: dev = 0x{dev:02X}, command = 0x{command:02X} ...')
        if self.method == 0:
            return smbus_read_u1(self.port, dev, command, status = self.init_status ^ 0xFF)
        return self.do_command(I2C_READ, SMBHSTCNT_BYTE_DATA, dev, command, None)

    def write_byte(self, dev, command, value):
        if self.debug:
            print(f'INFO: SMBus: write_byte: dev = 0x{dev:02X}, command = 0x{command:02X}, value = 0x{value:02X} ...')
        if self.method == 0:
            return smbus_write_u1(self.port, dev, command, value, status = self.init_status ^ 0xFF)
        return self.do_command(I2C_WRITE, SMBHSTCNT_BYTE_DATA, dev, command, value)

    def write_word(self, dev, command, value):
        if self.debug:
            print(f'INFO: SMBus: write_word: dev = 0x{dev:02X}, command = 0x{command:02X}, value = 0x{value:04X} ...')
        #if self.method == 0:
        #    raise NotImplementedError()
        return self.do_command(I2C_WRITE, SMBHSTCNT_WORD_DATA, dev, command, value)

    def proc_call(self, dev, command, value):
        if self.debug:
            print(f'INFO: SMBus: proc_call: dev = 0x{dev:02X}, command = 0x{command:02X}, value = 0x{value:04X} ...')
        if self.method == 0:
            return smbus_pcall(self.port, dev, command, value, status = self.init_status ^ 0xFF)
        return self.do_command(I2C_READ | I2C_WRITE, SMBHSTCNT_PROC_CALL, dev, command, value)

    def read_info(self, bus, dev, fun, full_info = True):
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
            # ref: 743845_001.pdf  section: Subsystem Vendor Identifiers (SVID)—Offset 2Ch
            offset = 0x2c
            SVID = pci_cfg_read(bus, dev, fun, offset, size = '2')
            if SVID:
                smbus['subsys_vid'] = SVID
                smbus["subsys_vendor"] = pci_ids[SVID] if SVID in pci_ids else None
            else:
                smbus['subsys_vid'] = None
                smbus["subsys_vendor"] = None
            # ref: 743845_001.pdf  section: Host Configuration (HCFG)—Offset 40h
            offset = 0x40
            HCFG = pci_cfg_read(bus, dev, fun, offset, size = 4)
            if HCFG:
                smbus['I2C_EN'] = get_bits(HCFG, 0, 2)   # I2C_EN (I2CEN): When this bit is 1, the PCH is enabled to communicate with I2C devices. This will change the formatting of some commands. When this bit is 0, behavior is for SMBus.
        return smbus

    # https://github.com/memtest86plus/memtest86plus/blob/2f9b165eec4de20ec4b23725c90d3989517ee3fe/system/x86/i2c.c#L80
    def find_smb_controllers(self):
        res = [ ]
        for bus in range(0, 0xFF, 0x80):
            for dev in range(0, 32):
                for fun in range(0, 8):
                    smb = self.read_info(bus, dev, fun)
                    if smb:
                        res.append( smb )
        return res

    def find_smbus(self, check_pci_did = True, aux_check = None):
        smb_list = self.find_smb_controllers()
        if not smb_list:
            return None
        for smb in smb_list:
            (bus, dev, fun) = tuple(smb['cfg_addr'])
            vid = smb['pch_vid']
            if vid != PCI_VENDOR_ID_INTEL:
                continue
            did = smb['pch_did']
            smbus_addr = smb['port']
            smb['port'] = smbus_addr & 0xFFFE
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
            if aux_check:
                rc = aux_check(self, smb)
                if not rc:
                    continue
            return smb
        return None

    def check_smbus_mutex(self):
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

    def init_mutex(self):
        if not self.mutex:
            self.check_smbus_mutex()
            mutex = CreateMutexW(GLOBAL_SMBUS_MUTEX_NAME)
            if not mutex:
                raise RuntimeError(f'Cannot open or create global mutex "{GLOBAL_SMBUS_MUTEX_NAME}"')
            self.mutex = mutex


if __name__ == "__main__":
    pass
    
