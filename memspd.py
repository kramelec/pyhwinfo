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
import logging

from datetime import datetime
from datetime import timedelta

__author__ = 'remittor'

from cpuidsdk64 import *
from hardware import *
from jep106 import *
from pci_ids import *
from smbus import *

from pprint import pprint

# Intel® 700 Series Chipset Family Platform Controller Hub
# ref: vol1: https://cdrdv2-public.intel.com/743835/743835-004.pdf
# ref: vol2: https://cdrdv2-public.intel.com/743845/743845_001.pdf

g_smb = None    # class MemSmb

SMBUS_SPD_DEVICE  = 0x50     # Typical SPD address for first DIMM
SMBUS_PMIC_DEVICE = 0x48     # ????????

# The SPD5 Hub device has totally 128 volatile registers as shown in Table 72
# ref: https://www.ablic.com/en/doc/datasheet/dimm_serial_eeprom_spd/S34HTS08AB_E.pdf
SPD5_MR3   = 0x03   # Vendor ID (two bytes)
SPD5_MR5   = 0x05   # Device Capability
SPD5_MR11  = 0x0B   # I2C Legacy Mode Device Configuration
SPD5_MR18  = 0x12   # Device Configuration
SPD5_MR48  = 0x30   # Device Status
SPD5_MR49  = 0x31   # TS Current Sensed Temperature (two bytes)
SPD5_MR52  = 0x34   # Hub, Thermal and NVM Error Status

# ref: https://www.richtek.com/assets/product_file/RTQ5119A/DSQ5119A-02.pdf
PMIC_RICHTEK_R1A = 0x1A  # VIN state    (RW)
PMIC_RICHTEK_R1B = 0x1B  # VIN state    (RW)
PMIC_RICHTEK_R30 = 0x30  # ADC state    (RW)     # ADC (Analog to Digital Conversion)
PMIC_RICHTEK_R31 = 0x31  # ADC Read Out (RO)
PMIC_RICHTEK_R3B = 0x3B  # Revision ID
PMIC_RICHTEK_R3C = 0x3C  # Vendor ID (2 bytes)

PMIC_RICHTEK_ADC_ENABLE  = 0x80  # look desc of PMIC_RICHTEK_R30

# ref: DSQ5119A-02.pdf   page    Table: "R30 - ADC Enable"
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

# =================================================================================================

class MemSmb(SMBus):
    def __init__(self):
        super().__init__(0)
        self.mem_info = None
        self.slot_dict = None
        self.slot = 0  # selected DIMM slot
        self.spd_dev = None
        self.pmic_dev = None
        self.page = None

    def set_slot(self, slot):
        self.slot = slot
        self.spd_dev = SMBUS_SPD_DEVICE + slot
        self.pmic_dev = SMBUS_PMIC_DEVICE + slot

    def find_all_devices(self):
        self.acquire()
        log.change_log_level(log.CRITICAL)
        try:
            slot_dict = { }
            for slot in range(0, 4):
                self.set_slot(slot)
                slot_dict[slot] = { }
                val = self.read_BYTE(self.spd_dev)
                if val is not None:
                    slot_dict[slot]['spd_dev'] = self.spd_dev
                val = self.read_BYTE(self.pmic_dev)
                if val is not None:
                    slot_dict[slot]['pmic_dev'] = self.pmic_dev
            slot_dict = { key: value for key, value in slot_dict.items() if value }
            return slot_dict
        finally:
            log.restore_log_level()
            self.release()

    def init_slots(self):
        for slot, info in self.slot_dict.items():
            info['proc_call_allowed'] = True
            info['is_page_protected'] = False

    def _mem_spd_set_page(self, page, check_status = True, ret_status = False):    
        if page < 0 or page >= 8:   # DDR5 SPD has 8 pages
            raise ValueError()    
        if not self.slot_dict[self.slot]['proc_call_allowed']:
            if self.slot_dict[self.slot]['is_page_protected']:
                return False
        # ref: S34HTS08AB_E.pdf   Table 82 Register MR11
        # bit[3] = 0 ==> 1 Byte Addressing for SPD5 Hub Device Memory
        val = None
        if self.slot_dict[self.slot]['proc_call_allowed']:
            val = self.proc_call(self.spd_dev, SPD5_MR11, page)
        if val is None:
            if self.slot_dict[self.slot]['proc_call_allowed']:
                print(f'INFO: SMBus: PROC_CALL method not available for slot #{self.slot}!!!')
                self.slot_dict[self.slot]['proc_call_allowed'] = False
            rc = self.write_byte(self.spd_dev, SPD5_MR11, page)
            if not rc:
                log.error(f'_mem_spd_set_page({page}): cannot set page')
                if not self.slot_dict[self.slot]['is_page_protected']:
                    print(f'INFO: It is very likely that SPD write protection is enabled for slot #{self.slot}')
                    self.slot_dict[self.slot]['is_page_protected'] = True
                return False
        if not check_status and not ret_status:
            return True
        status = self._mem_spd_get_status()  # SPD Device status
        if ret_status:
            return status
        if status is None:
            log.error(f'SMBus: cannot get status for SPD device = 0x{self.spd_dev:02X}')
            return False
        status &= 0x7F  # exclude Pending IBI_STATUS = 0x80    # ref: S34HTS08AB_E.pdf (Table 107)
        if status != 0:
            log.error(f'_mem_spd_set_page: status = 0x{status:02X}')
        return True if status == 0 else False

    def _mem_spd_init(self, page):
        status = self._mem_spd_set_page(page, ret_status = True)
        if status is None:
            return -2
        if status == False:
            return -1
        if (status & 0x80) != 0:
            log.info(f'SMBus: detect Pending IBI_STATUS : status = 0x{status:X}')  # IBI = In Band Interrupt
        return 0

    def _mem_spd_get_status(self, ret_raw = False):
        status = self._mem_spd_read_reg(SPD5_MR48)  # Device status
        if status is None:
            return None
        if not ret_raw:
            status &= 0x7F  # exclude Pending IBI_STATUS = 0x80    # ref: S34HTS08AB_E.pdf (Table 107)
        return status

    def _mem_spd_read_reg(self, reg_offset, set_page = None):
        if set_page is not None:
            rc = self._mem_spd_set_page(set_page)
            if not rc:
                return None
        log.debug(f'_mem_spd_read_reg(0x{reg_offset:02X}) ...')
        return self.read_byte(self.spd_dev, reg_offset)

    def mem_spd_read_reg(self, reg_offset, size = 1):
        self.acquire()
        try:
            offset = reg_offset & 0x7F   # read reg, not SPD page !!!
            val = self._mem_spd_read_reg(offset, set_page = 0)
            if val is None:
                log.error(f'mem_spd_read_reg({self.slot}): val = {val}')
                return None
            if size == 1:
                return val
            elif size == 2:
                val_HI = self._mem_spd_read_reg(offset + 1)
                if val_HI is None:
                    log.error(f'mem_spd_read_reg({self.slot}): VAL = {val_HI}')
                    return None
                return (val_HI << 8) + val
            else:
                return None
        finally:
            self.release()
        return None

    def _mem_spd_read_byte(self, offset):
        if offset < 0 or offset >= 0x80:
            raise ValueError()
        return self.read_byte(self.spd_dev, offset | 0x80)

    def _mem_spd_read_word(self, offset):
        if offset < 0 or offset >= 0x7F:
            raise ValueError()
        return self.read_word(self.spd_dev, offset | 0x80)

    def mem_spd_read_byte(self, offset):
        if offset < 0 or offset >= 0x400:   # DDR5 SPD of 1024 bytes len
            raise ValueError()
        self.acquire()
        try:
            spd_page = offset // 0x80
            rc = self._mem_spd_set_page(spd_page)
            if not rc:
                return None
            status = self._mem_spd_get_status()
            if status != 0:
                return None
            return self._mem_spd_read_byte(offset - spd_page * 0x80)
        finally:
            self.release()
        return None

    def mem_spd_read_full(self):
        log.info(f'SMBus: mem_spd_read_full({self.slot}) ...')
        buf = b''
        self.acquire()
        try:
            size = 1 if self.io_mode == IOMODE.CPUZMODE else 2
            for spd_page in range(0, 8):
                rc = self._mem_spd_set_page(spd_page)
                if not rc:
                    if spd_page == 0:
                        return None
                    break
                status = self._mem_spd_get_status()
                if status != 0:
                    break
                for offset in range(0, 0x80, size):
                    if size == 1:
                        val = self._mem_spd_read_byte(offset)
                    else:
                        val = self._mem_spd_read_word(offset)
                    if val is None:
                        break
                    buf += int_encode(val, size)
                if val is None:
                    break
            # restore page 0
            self._mem_spd_set_page(0)
        finally:
            self.release()
            log.info(f'SMBus: mem_spd_read_full({self.slot}) readed {len(buf)} bytes')
        return buf

    def _mem_pmic_init(self):
        rc = self._mem_spd_set_page(0)
        if not rc:
            return None
        #status = port_read_u1(self.port + SMBHSTSTS)
        #if status != 0:
        #    log.error(f'PMIC status = 0x{status:X}')
        #    return None
        port_write_u1(self.port + SMBHSTSTS, SMBHSTSTS_XXX)  # init SMBus state
        dev = 0x18   # https://i2cdevices.org/addresses/0x18
        port_write_u1(self.port + SMBHSTADD, (dev << 2) | I2C_READ)  # set SMBUS device
        cmd = 0x05   # ???????
        port_write_u1(self.port + SMBHSTCMD, cmd)
        cnt = port_read_u1(self.port + SMBHSTCNT)
        log.debug(f'cnt = 0x{cnt:X}')
        port_write_u1(self.port + SMBHSTCNT, SMBHSTCNT_START + SMBHSTCNT_WORD_DATA)
        code = port_read_u1(self.port + SMBHSTSTS)
        log.debug(f'CODE = 0x{code:X}')
        code = port_read_u1(self.port + SMBHSTSTS)
        log.debug(f'CODE = 0x{code:X}')
        port_write_u1(self.port + SMBHSTSTS, code)
        return code

    def get_pmic_adc_command(self, adc_sel, upd_freq = 1):
        ADC_REGISTER_UPDATE_FREQUENCY = [ 1, 2, 4, 8 ]  # milisec table  # ref: DSQ5119A-02.pdf  page 106  
        if upd_freq in ADC_REGISTER_UPDATE_FREQUENCY:
            updFreq = ADC_REGISTER_UPDATE_FREQUENCY.index(upd_freq)  # select code for 1 ms
        else:
            raise RuntimeError()
        return PMIC_RICHTEK_ADC_ENABLE | (SETDIM(adc_sel, 4) << 3) | updFreq  # ref: "ADC Select" in doc DSQ5119A-02.pdf
    
    def _pmic_read_adc(self, adc_sel):
        # prepare R31 for NULL value
        cmd = self.get_pmic_adc_command(PMIC_RICHTEK_ADC_NULL)
        self.write_byte(self.pmic_dev, PMIC_RICHTEK_R30, cmd)
        ok = False
        for trynum in range(0, 4):
            state = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R30)
            if state != cmd:
                return None  # ERROR
            value = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R31)
            if value == 0:
                ok = True
                break
        if not ok:
            return None
        # process requested ADC reading
        cmd = self.get_pmic_adc_command(adc_sel)
        self.write_byte(self.pmic_dev, PMIC_RICHTEK_R30, cmd)
        for trynum in range(0, 4):
            state = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R30)
            if state != cmd:
                return None  # ERROR
            value = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R31)
            if value != 0:
                return value
        return None

    def voltage_decode(self, val, mult = 0.015):  # look doc: DSQ5119A-02.pdf  page 107  table "R31 - ADC Read"
        if val is None:
            return None
        val = val * mult
        return round(val, 3)

    def mem_pmic_read(self):
        out = { "smbus_dev": self.pmic_dev }
        self.acquire()
        try:
            rc = self.read_byte(self.pmic_dev, 0)
            if rc != 0:
                rc = self.read_byte(self.pmic_dev, 0)
                if rc != 0:
                    log.error('PMIC not inited!')
                    return None
            vid_HI = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R3C)  # PMIC Vendor ID
            vid_LO = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R3C + 1)
            vid = jep106decode(vid_HI, vid_LO)
            vendor = jep106[vid] if vid in jep106 else None
            print(f'PMIC Vendor ID = 0x{vid:04X} "{vendor}"')
            out['vid'] = vid
            out['vendor'] = vendor 
            
            if vid != 0x0A0C:   # Richtek
                log.error(f'pmic 0x{vid:04X} not supported')
                return out
            
            val = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R3B)  # PMIC Revision ID
            cur_capab = get_bits(val, 0, 0)     # PMIC Current Capability
            rev_minor = get_bits(val, 0, 1, 3)  # Minor Revision ID
            rev_major = get_bits(val, 0, 4, 5)  # Minor Revision ID
            print(f'PMIC Revision = {rev_major}.{rev_minor}  [{cur_capab}]')
            out['revision'] = f'{rev_major}.{rev_minor}'
            out['current_capability'] = cur_capab

            '''
            val = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R1A)
            print('VLDO_1.0V_POWER_GOOD_THRESHOLD_VOLTAGE =', get_bits(val, 0, 0))
            print('OUTPUT_POWER_SELECT =', get_bits(val, 0, 1))
            print('VLDO_1.8V_POWER_GOOD_THRESHOLD_VOLTAGE =', get_bits(val, 0, 2))
            print('V_BIAS_POWER_GOOD_THRESHOLD_VOLTAGE =', get_bits(val, 0, 3))
            print('VIN_BULK_POWER_GOOD_THRESHOLD_VOLTAGE =', get_bits(val, 0, 5, 7))
            val = smbus_read_u1(smb_addr, SMBUS_PMIC_DEVICE + slot, PMIC_RICHTEK_R1B)
            print('PMIC_HIGH_TEMPERATURE_WARNING_THRESHOL =', get_bits(val, 0, 0, 2))
            print('GSI_N_OUTPUT_PIN_ENABLE =', get_bits(val, 0, 3))
            print('GLOBAL_CAMP_PIN_STATUS_MASK =', get_bits(val, 0, 4))
            print('VIN_MGMT_OVER_VOLTAGE_THRESHOLD =', get_bits(val, 0, 5))
            print('CURRENT_OR_POWER_METER_SELECT =', get_bits(val, 0, 6))
            print('VIN_BULK_OVER_VOLTAGE_THRESHOLD =', get_bits(val, 0, 7))
            '''
            
            saved_st = self.read_byte(self.pmic_dev, PMIC_RICHTEK_R30)  # ADC state
            if saved_st is None:
                return out
            print(f'PMIC state = 0x{saved_st:02X} (SAVED)')
            
            def get_pmic_param(name, adc_sel, mult = 0.015):
                nonlocal self, out
                val = self._pmic_read_adc(adc_sel)
                val = self.voltage_decode(val, mult)
                print(f'PMIC[{name}] = {val} V')
                out[name] = val
            
            try:
                get_pmic_param('SWA', PMIC_RICHTEK_ADC_SWA)
                get_pmic_param('SWB', PMIC_RICHTEK_ADC_SWB)
                get_pmic_param('SWC', PMIC_RICHTEK_ADC_SWC)
                get_pmic_param('SWD', PMIC_RICHTEK_ADC_SWD)
                get_pmic_param('1.8V', PMIC_RICHTEK_ADC_LVDO_18V)
                get_pmic_param('1.0V', PMIC_RICHTEK_ADC_LVDO_10V)
                get_pmic_param('VIN', PMIC_RICHTEK_ADC_VIN_BULK, 0.070)
            finally:
                # restore ADC state
                self.write_byte(self.pmic_dev, PMIC_RICHTEK_R30, saved_st)
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
            self.release()
        return out
    
# =================================================================================================

def find_spd_smbus(check_pci_did = True, check_spd = True):
    global g_smb

    def find_all_spd_devices(self, smb):
        global g_smb
        g_smb.port = smb['port']
        slot_dict = g_smb.find_all_devices()
        print('SMBus devices:')
        pprint(hex_formatter(slot_dict, '02'))
        g_smb.slot_dict = slot_dict
        g_smb.__init_stage = 1
        return len(slot_dict) > 0
    
    
    aux_check = find_all_spd_devices if check_spd else None
    smb = g_smb.find_smbus(check_pci_did = check_pci_did, aux_check = aux_check)
    if not smb:
        if not g_smb.slot_dict:
            print(f'ERROR: cannot found any SPD/PMIC devices on SMBus 0x{g_smb.port:04X}')
            return None
        print(f'ERROR: wrong SMBus port = 0x{g_smb.port:X}')
        return None
    g_smb.info = smb
    g_smb.__init_stage = 2
    return smb

def CHKBIT(val, bit):
    mask = 1 << bit
    return False if (val & mask) == 0 else True

def temp_decode(val):  # see doc: S34HTS08AB_E.pdf  page 63  table 99  (Thermal Register - Low Byte and High Byte)
    val >>= 2
    sign = CHKBIT(val, 10)
    temp = SETDIM(val, 10) / 4
    return -temp if sign else temp

def get_mem_spd_info(slot, mem_info: dict, with_pmic = True):
    global g_mem_info, g_smb
    spd = { }

    if mem_info is None:
        raise ValueError('Argument mem_info cannot be None!')
    
    cpu = mem_info['cpu']
    if cpu['family'] != 6:
        raise RuntimeError(f'ERROR: Currently support only Intel processors')

    if cpu['model_id'] < INTEL_ALDERLAKE:
        raise RuntimeError(f'ERROR: Processor model 0x{cpu["model_id"]:X} not supported')

    if not g_smb:
        g_smb = MemSmb()
        g_smb.mem_info = copy.deepcopy(mem_info)

    if not hasattr(g_smb, "__init_stage"):
        g_smb.__init_stage = 0
        _smb = find_spd_smbus(check_pci_did = True, check_spd = True)
        if not _smb:
            print('ERROR: Cannot found PCH with SMBus controller')
            return None

    if not g_smb.info:
        return None
    
    smb = g_smb.info
    if "ddr_ver" not in g_smb.info:
        vid = smb['pch_vid']
        if vid == PCI_VENDOR_ID_INTEL:
            (bus, dev, fun) = tuple(smb['cfg_addr'])
            did = smb['pch_did']
            smbus_dev_name = PCI_ID_SMBUS_INTEL[did]['name']
            print(f'Founded PCH device with SMBus: "{smbus_dev_name}"')
            #print(f'VID = 0x{vid:04X}  DID = 0x{did:04X} >>> {bus:02X}:{dev:02X}:{fun:02X}')
        else:
            raise RuntimeError('ERROR: Currently supported only Intel platform')
        if 'port' in smb and smb["port"] is not None:
            print(f'Intel PCH SMBus addr = 0x{smb["port"]:X}')
        g_smb.info["ddr_ver"] = g_smb.mem_info['memory']['mc'][0]['DDR_ver']
        print(f'DDR_ver: {g_smb.info["ddr_ver"]}')
        g_smb.init_slots()

    if not smb['port']:
        return None

    g_smb.set_slot(slot)
    if slot not in g_smb.slot_dict:
        print(f'Skip DIMM slot #{slot} (Reason: SPD device not founded)')
        return None
    
    print(f'Scan DIMM slot #{slot}')
    vendorid = g_smb.mem_spd_read_reg(SPD5_MR3, 2)  # MR3 + MR4 => Vendor ID
    if not vendorid:
        log.warning(f'Cannot read VendorID from SPD#{slot}')
        return None

    spd_vid = jep106decode(vendorid)

    spd["slot"] = slot
    spd["smbus_dev"] = SMBUS_SPD_DEVICE + slot
    spd["spd_vid"] = spd_vid
    spd["spd_vendor"] = jep106[spd_vid] if spd_vid in jep106 else None
    print(f'SPD Vendor ID = 0x{spd_vid:04X} "{spd["spd_vendor"]}"')

    val = g_smb.mem_spd_read_reg(SPD5_MR18)  # Device Configuration
    if val is None:
        log.warning(f'Cannot read DevConf from SPD#{slot}')
        return None
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

    temp = g_smb.mem_spd_read_reg(SPD5_MR49, 2)  # MR49 + MR50 => TS Current Sensed Temperature
    if temp is not None:
        temp = temp_decode(temp)
        #print(f'spd[{slot}][MR49] = 0x{temp:04X}  =>  {temp} degC')
        spd['temp'] = temp

    spd['PMIC'] = None
    spd['spd_eeprom'] = ""
    spd['SPD'] = None

    spd_data = g_smb.mem_spd_read_full()
    if spd_data:
        log.trace(f'SPD[{slot}] = {spd_data.hex()}')
        log.trace(f'SPD len = {len(spd_data)}')
    if spd_data and len(spd_data) >= 1024:
        spd['spd_eeprom'] = spd_data.hex()

    if with_pmic:
        pmic = g_smb.mem_pmic_read()
        spd['PMIC'] = pmic
        
    return spd

def get_mem_spd_all(mem_info: dict, with_pmic = True, allinone = True):
    global g_mem_info, g_smb
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
            dimm['SMBus'] = g_smb.info.copy()
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
    
