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
from hardware import *
from memory import *
from smbus import *
from msrbox import *

# ref: https://cdrdv2.intel.com/v1/dl/getContent/671200  (Intel SDM vol.1)

LOCAL_BIOS_MAILBOX_MUTEX_NAME  = r"Local\Access_Intel_BIOS_Mailbox"
GLOBAL_BIOS_MAILBOX_MUTEX_NAME = r"Global\Access_Intel_BIOS_Mailbox"

MAILBOX_TYPE_PCODE        = 1  # CPU_BIOS_MAILBOX  : MMIO MCHBAR_REG = 0x5DA4 [dw_CMD] / MCHBAR_REG = 0x5DA0 [dw_DATA]

PCODE_MAILBOX_INTERFACE_OFFSET      = 0x5DA4
PCODE_MAILBOX_DATA_OFFSET           = 0x5DA0

CPU_MAILBOX_CMD_SAGV_SET_POLICY                     = 0x00000122

CPU_MAILBOX_CMD_SAGV_CONFIG_HANDLER                 = 0x00000022
CPU_MAILBOX_CMD_SAGV_CONFIG_HEURISTICS_SUBCOMMAND   = 0x00000003
CPU_MAILBOX_CMD_SAGV_CONFIG_HEURISTICS_DOWN     = 0x00000000
CPU_MAILBOX_CMD_SAGV_CONFIG_HEURISTICS_UP       = 0x00000001
CPU_MAILBOX_CMD_SAGV_CONFIG_FACTOR_IA_DDR_BW    = 0x00000002
CPU_MAILBOX_CMD_SAGV_CONFIG_FACTOR_GT_DDR_BW    = 0x00000003
CPU_MAILBOX_CMD_SAGV_CONFIG_FACTOR_IO_DDR_BW    = 0x00000004
CPU_MAILBOX_CMD_SAGV_CONFIG_FACTOR_IAGT_STALL   = 0x00000005

SET_EPG_BIOS_POWER_OVERHEAD_0_CMD       = 0x00000020
SET_EPG_BIOS_POWER_OVERHEAD_1_CMD       = 0x00000120
MAILBOX_BIOS_CMD_READ_BIOS_MC_REQ_ERROR = 0x00000009  # Allows reading the error indication for DDR checks where the memory does not lock.

# PARAM1[15:8] - subcommand
# PARAM2[28:16] - MC0 or MC1
CPU_MAILBOX_BIOS_CMD_MRC_CR_INTERFACE                  = 0x3E
CPU_MRC_CR_INTERFACE_SUBCMD_READ_RCH_STALL_PHASE       = 0
CPU_MRC_CR_INTERFACE_SUBCMD_WRITE_RCH_STALL_PHASE      = 1

CPU_MAILBOX_BCLK_CONFIG_CMD                            = 0x0000003F
CPU_MAILBOX_BCLK_CONFIG_READ_BCLK_RFI_RANGE_MIN_MASK   = 0xFFFF
CPU_MAILBOX_BCLK_CONFIG_READ_BCLK_RFI_RANGE_MAX_MASK   = 0xFFFF0000
CPU_MAILBOX_BCLK_CONFIG_READ_BCLK_RFI_RANGE_SUBCOMMAND = 0
CPU_MAILBOX_BCLK_CONFIG_GET_BCLK_RFI_FREQ_SUBCOMMAND   = 1
CPU_MAILBOX_BCLK_CONFIG_SET_BCLK_RFI_FREQ_SUBCOMMAND   = 2
CPU_MAILBOX_BCLK_CONFIG_GET_SSC_CONTROL_SUBCOMMAND     = 3
CPU_MAILBOX_BCLK_CONFIG_SET_SSC_CONTROL_SUBCOMMAND     = 4

CPU_MAILBOX_BIOS_CMD_MRC_CONFIG                        = 65
CPU_MAILBOX_BIOS_CMD_MRC_CONFIG_VCCIO_SUBCOMMAND       = 3 
CPU_MAILBOX_BIOS_CMD_MRC_CONFIG_VCCIO_READ_SUBCOMMAND  = 4
CPU_MAILBOX_BIOS_CMD_MRC_CONFIG_VCCIO_WRITE_SUBCOMMAND = 5

# PCODE Mailbox OC Interface 0x37 command set
MAILBOX_OC_CMD_OC_INTERFACE                            = 0x00000037
MAILBOX_OC_SUBCMD_READ_OC_MISC_CONFIG                  = 0x00000000
MAILBOX_OC_SUBCMD_WRITE_OC_MISC_CONFIG                 = 0x00000001
MAILBOX_OC_SUBCMD_READ_OC_PERSISTENT_OVERRIDES         = 0x00000002
MAILBOX_OC_SUBCMD_WRITE_OC_PERSISTENT_OVERRIDES        = 0x00000003
MAILBOX_OC_SUBCMD_READ_TJ_MAX_OFFSET                   = 0x00000004
MAILBOX_OC_SUBCMD_WRITE_TJ_MAX_OFFSET                  = 0x00000005
MAILBOX_OC_SUBCMD_READ_PLL_VCC_TRIM_OFFSET             = 0x00000006
MAILBOX_OC_SUBCMD_WRITE_PLL_VCC_TRIM_OFFSET            = 0x00000007
MAILBOX_OC_SUBCMD_READ_PVD_RATIO_THRESHOLD_OVERRIDE    = 0x00000008
MAILBOX_OC_SUBCMD_WRITE_PVD_RATIO_THRESHOLD_OVERRIDE   = 0x00000009
MAILBOX_OC_SUBCMD_READ_DISABLED_IA_CORES_MASK          = 0x0000000E
MAILBOX_OC_SUBCMD_WRITE_DISABLED_IA_CORES_MASK         = 0x0000000F
MAILBOX_OC_SUBCMD_READ_PLL_MAX_BANDING_RATIO_OVERRIDE  = 0x00000010
MAILBOX_OC_SUBCMD_WRITE_PLL_MAX_BANDING_RATIO_OVERRIDE = 0x00000011
MAILBOX_OC_SUBCMD_READ_UNDERVOLT_PROTECTION            = 0x00000016
MAILBOX_OC_SUBCMD_WRITE_UNDERVOLT_PROTECTION           = 0x00000017

# OC Interface (0x37) Sub-Command definitions
PLL_MAX_BANDING_RATIO_MINIMUM           = 1
PLL_MAX_BANDING_RATIO_MAXIMUM           = 120
PLL_MAX_BANDING_RATIO_MASK              = 0x000000FF

# =============================================================================

class BiosMailBox():
    def __init__(self):
        self.cpu_id = None
        self.port = 0
        self.mutex = None
        self.mutex_wait_timeout = 2000
        self.init_mutex()
        self.mailbox_wait_timeout = 50

    def acquire(self, throwable = True):
        rc = self.mutex.acquire(wait_ms = self.mutex_wait_timeout, throwable = throwable)
        if not throwable and rc == False:
            return False
        return True

    def release(self):
        try:
            pass
        finally:
            self.mutex.release()

    def make_bios_mailbox_cmd(self, command, p1, p2):
        # ref: ICÈ_TÈA_BIOS  (leaked BIOS sources)  # file "MrcApi.h"  define CPU_MAILBOX_CMD
        # struct MSR_BIOS_MAILBOX_INTERFACE_REGISTER
        Param1 = p1 & 0xFF
        Param2 = p2 & 0x1FFF
        RunBusy = 1
        return (RunBusy << 31) | (Param2 << 16) | (Param1 << 8) | (command & 0xFF)
    
    def _bios_pcode_mailbox(self, command, p1, p2, data = None):
        # ref: ICÈ_TÈA_BIOS  (leaked BIOS sources)  # file "MailboxLibrary.c"  func  MailboxRead 
        self.status = 0xFFF
        cmd = self.make_bios_mailbox_cmd(command, p1, p2)
        SA_MC_BUS = 0
        SA_MC_DEV = 0
        SA_MC_FUN = 0
        R_SA_MCHBAR = 0x48
        rc = phymem_pc_write32(SA_MC_BUS, SA_MC_DEV, SA_MC_FUN, R_SA_MCHBAR, MCHBAR_ADDR_MASK, PCODE_MAILBOX_DATA_OFFSET, data if data else 0)
        if not rc:
            log.error(f'_bios_pcode_mailbox(0x{cmd:X}): cannot write MMIO data!')
            return None
        rc = phymem_pc_write32(SA_MC_BUS, SA_MC_DEV, SA_MC_FUN, R_SA_MCHBAR, MCHBAR_ADDR_MASK, PCODE_MAILBOX_INTERFACE_OFFSET, cmd)
        if not rc:
            log.error(f'_bios_pcode_mailbox(0x{cmd:X}): cannot write MMIO reg!')
            return None
        start_time = datetime.now()
        while True:
            data = phymem_pc_read64(SA_MC_BUS, SA_MC_DEV, SA_MC_FUN, R_SA_MCHBAR, MCHBAR_ADDR_MASK, PCODE_MAILBOX_DATA_OFFSET)
            if data is None:
                log.error(f'_bios_pcode_mailbox(0x{cmd:X}): cannot read MMIO reg and data!')
                return None
            self.status = (data >> 32) & 0xFFFFFFFF
            RunBusy = True if (self.status & 0x80000000) != 0 else False
            if not RunBusy:
                break
            if datetime.now() - start_time > timedelta(milliseconds = self.mailbox_wait_timeout):
                log.error(f'_bios_pcode_mailbox(0x{cmd:X}): timedout!')
                return None
            pass
        return data & 0xFFFFFFFF

    def _get_vccio_value(self):
        VccIO = None
        data = self._bios_pcode_mailbox(CPU_MAILBOX_BIOS_CMD_MRC_CONFIG, CPU_MAILBOX_BIOS_CMD_MRC_CONFIG_VCCIO_SUBCOMMAND, 0)
        if data is None:
            log.error(f'CPU_MAILBOX_BIOS_CMD_MRC_CONFIG({CPU_MAILBOX_BIOS_CMD_MRC_CONFIG_VCCIO_SUBCOMMAND},{0}): status = 0x{self.status:X}')
        else:
            ddr = { }
            # struct DDRPHY_CR_MISCS_CR_AFE_BG_CTRL1
            ddr['bg_ctrl_lvrtargetcode_distlvr_north'] = get_bits(data, 0, 0, 5)
            ddr['bg_ctrl_lvrtargetcode_distlvr_south'] = get_bits(data, 0, 6, 11)
            ddr['bg_ctrl_lvrtargetcode_iolvr_north'] = get_bits(data, 0, 12, 17)
            ddr['bg_ctrl_lvrtargetcode_iolvr_south'] = get_bits(data, 0, 18, 23)
            ddr['bg_ctrl_phase_detector_reset_n'] = get_bits(data, 0, 24)
            ddr['spare'] = get_bits(data, 0, 25, 31)
            VccIO = round( ( ddr['bg_ctrl_lvrtargetcode_iolvr_south'] + 115 ) / 192, 3)  # ref: func MrcDdrIoPreInit

        if not VccIO:
            data = self._bios_pcode_mailbox(CPU_MAILBOX_BIOS_CMD_MRC_CONFIG, CPU_MAILBOX_BIOS_CMD_MRC_CONFIG_VCCIO_READ_SUBCOMMAND, 0)
            if data is None:
                log.error(f'CPU_MAILBOX_BIOS_CMD_MRC_CONFIG({CPU_MAILBOX_BIOS_CMD_MRC_CONFIG_VCCIO_READ_SUBCOMMAND},{0}): status = 0x{self.status:X}')
            else:
                # struct DDRPHY_CR_MISCS_CR_AFE_BG_CTRL1
                bg_ctrl_lvrtargetcode_iolvr_south = get_bits(data, 0, 18, 23)
                VccIO = round( ( bg_ctrl_lvrtargetcode_iolvr_south + 115 ) / 192, 3)  # ref: func MrcDdrIoPreInit
        
        return VccIO
        
    def get_vccio_value(self):
        self.acquire()
        try:
            return self._get_vccio_value()
        finally:
            self.release()        

    def _read_base_info(self):
        out = { }
        out['VccIO'] = self._get_vccio_value()
        
        data = self._bios_pcode_mailbox(MAILBOX_OC_CMD_OC_INTERFACE, MAILBOX_OC_SUBCMD_READ_OC_MISC_CONFIG, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_OC_INTERFACE({MAILBOX_OC_SUBCMD_READ_OC_MISC_CONFIG},{0}): status = 0x{self.status:X}')
        else:
            out['Current Realtime Memory Timing'] = data 

        data = self._bios_pcode_mailbox(MAILBOX_OC_CMD_OC_INTERFACE, MAILBOX_OC_SUBCMD_READ_UNDERVOLT_PROTECTION, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_OC_INTERFACE({MAILBOX_OC_SUBCMD_READ_UNDERVOLT_PROTECTION},{0}): status = 0x{self.status:X}')
        else:
            out['UnderVoltProtection'] = get_bits(data, 0, 0, 1)

        data = self._bios_pcode_mailbox(MAILBOX_OC_CMD_OC_INTERFACE, MAILBOX_OC_SUBCMD_READ_OC_PERSISTENT_OVERRIDES, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_OC_INTERFACE({MAILBOX_OC_SUBCMD_READ_OC_PERSISTENT_OVERRIDES},{0}): status = 0x{self.status:X}')
        else:
            # struct B2PMB_OC_PERSISTENT_OVERRIDES_DATA
            out['FullRangeMultiplierUnlockEn'] = get_bits(data, 0, 0)
            out['SaPllFrequencyOverride'] = get_bits(data, 0, 1)
            out['FllOverclockingMode'] = get_bits(data, 0, 2, 3)
            out['FllOcModeEn'] = get_bits(data, 0, 4)
            out['TscHwFixUp'] = get_bits(data, 0, 5)
        
        return out

    def _read_common_info(self):
        out = { }
        val = msr_read(MSR_BIOS_SIGN_ID)
        if val is not None:
            # struct MSR_BIOS_SIGN_ID_REGISTER
            ver = get_bits(val, 0, 32, 63)
            out['MICROCODE_VER'] = ver
            out['MICROCODE_VER_HEX'] = f'0x{ver:X}'
        return out

    def read_full_info(self):
        out = { }
        self.acquire()
        try:
            out.update( self._read_common_info() )
            out.update( self._read_base_info() )
        finally:
            self.release()
        return out
    
    def check_mailbox_mutex(self):
        rc = 0
        mtx_list = [ LOCAL_BIOS_MAILBOX_MUTEX_NAME, GLOBAL_BIOS_MAILBOX_MUTEX_NAME ]
        for mtx_name in mtx_list:
            mtx = OpenMutexW(mtx_name, throwable = False)
            if mtx.handle:
                print(f'Mutex "{mtx_name}" opened! (already exist)')
            else:
                mtx = CreateMutexW(mtx_name, throwable = False)
                if mtx.handle:
                    print(f'Mutex "{mtx_name}" created!')
                else:
                    print(f'Mutex "{mtx_name}" cannot opened and cteated!')
                    rc -= 1
        return rc

    def init_mutex(self):
        if not self.mutex:
            self.check_mailbox_mutex()
            mutex = CreateMutexW(GLOBAL_BIOS_MAILBOX_MUTEX_NAME)
            if not mutex:
                raise RuntimeError(f'Cannot open or create global mutex "{GLOBAL_BIOS_MAILBOX_MUTEX_NAME}"')
            self.mutex = mutex


if __name__ == "__main__":
    import cpuinfo
    SdkInit(None, 0)
    cpu_id = cpuinfo.get_cpu_id()
    print('CPU ID: 0x%X' % cpu_id)
    log.change_log_level(log.TRACE)
    bmb = BiosMailBox()
    bmb.cpu_id = cpu_id
    
    out = bmb.read_full_info()
    print(json.dumps(out, indent=4))
    
    