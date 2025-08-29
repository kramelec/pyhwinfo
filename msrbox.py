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

# ref: https://cdrdv2.intel.com/v1/dl/getContent/671200  (Intel SDM vol.1)
# ref: https://cdrdv2-public.intel.com/858465/335592-088-sdm-vol-4.pdf  ( Intel SDM vol.4 )

LOCAL_OC_MAILBOX_MUTEX_NAME  = r"Local\Access_Intel_OC_Mailbox"
GLOBAL_OC_MAILBOX_MUTEX_NAME = r"Global\Access_Intel_OC_Mailbox"

MAILBOX_TYPE_PCODE        = 1  # CPU_BIOS_MAILBOX  : MMIO MCHBAR_REG = 0x5DA4 [dw_CMD] / MCHBAR_REG = 0x5DA0 [dw_DATA]
MAILBOX_TYPE_OC           = 2  # OC_MAILBOX        : via MSR_REG = 0x150  struct{dw_DATA,dw_CMD}
MAILBOX_TYPE_VR_MSR       = 3  # MSR_BIOS_MAILBOX  : via MSR_REG = 0x607 [dw_CMD] / MSR_REG = 0x608 [dw_DATA]
                               # IMC_BIOS_MAILBOX  : MMIO MCHBAR_REG = 0x5E00 {dw_CMD} / MCHBAR_REG = 0x5E04 [dw_DATA]
                               # VCU_MAILBOX       : MMIO MCHBAR_REG = 0x6C00 {dw_CMD} / MCHBAR_REG = 0x6C04 [dw_DATA]

if cpu_id is None:
    cpu_id = get_cpu_id()

PCU_CR_BCLK_FREQ_MCHBAR             = 0x00005F60

MSR_IA32_PLATFORM_ID                = 0x00000017  # RSHIFT 50 , MASK 7
MSR_BIOS_SIGN_ID                    = 0x0000008B  # struct MSR_BIOS_SIGN_ID_REGISTER
MSR_PLATFORM_INFO                   = 0x000000CE 
MSR_OC_MAILBOX                      = 0x00000150
MSR_IA32_PERF_STATUS                = 0x00000198

if cpu_id in i12_FAM:
    MSR_VR_CURRENT_CONFIG           = 0x00000601
if cpu_id in i15_FAM:    
    MSR_PKG_POWER_LIMIT_4           = 0x00000601
    
VR_MAILBOX_MSR_INTERFACE            = 0x00000607
VR_MAILBOX_MSR_DATA                 = 0x00000608
MSR_BIOS_MAILBOX_INTERFACE          = 0x00000607  # struct MSR_BIOS_MAILBOX_INTERFACE_REGISTER / BIOS_MAILBOX_INTERFACE_PCU_STRUCT
MSR_BIOS_MAILBOX_DATA               = 0x00000608

MSR_PST_CONFIG_CONTROL              = 0x00000609  # struct MSR_PST_CONFIG_CONTROL_REGISTER
MSR_DDR_RAPL_LIMIT                  = 0x00000618

MAILBOX_OC_CMD_GET_OC_CAPABILITIES            = 0x01
MAILBOX_OC_CMD_GET_PER_CORE_RATIO_LIMIT       = 0x02
MAILBOX_OC_CMD_GET_DDR_CAPABILITIES           = 0x03
MAILBOX_OC_CMD_GET_VR_TOPOLOGY                = 0x04
MAILBOX_OC_CMD_GET_BCLK_FREQUENCY_CMD         = 0x05  # MAILBOX_OC_CMD_BCLK_FREQUENCY_CMD
MAILBOX_OC_CMD_GET_FUSED_P0_RATIO_VOLTAGE     = 0x07
MAILBOX_OC_CMD_GET_VOLTAGE_FREQUENCY          = 0x10
MAILBOX_OC_CMD_SET_VOLTAGE_FREQUENCY          = 0x11
MAILBOX_OC_CMD_GET_MISC_GLOBAL_CONFIG         = 0x14
MAILBOX_OC_CMD_SET_MISC_GLOBAL_CONFIG         = 0x15
MAILBOX_OC_CMD_GET_ICCMAX                     = 0x16
MAILBOX_OC_CMD_SET_ICCMAX                     = 0x17
MAILBOX_OC_CMD_GET_MISC_TURBO_CONTROL         = 0x18
MAILBOX_OC_CMD_SET_MISC_TURBO_CONTROL         = 0x19
MAILBOX_OC_CMD_GET_AVX_RATIO_OFFSET           = 0x1A
MAILBOX_OC_CMD_SET_AVX_RATIO_OFFSET           = 0x1B
MAILBOX_OC_CMD_GET_AVX_VOLTAGE_GUARDBAND      = 0x20
MAILBOX_OC_CMD_SET_AVX_VOLTAGE_GUARDBAND      = 0x21
MAILBOX_OC_CMD_GET_BCLK_FREQ                  = 0x22  # func OcGetCpuBclkFreqCmd
MAILBOX_OC_CMD_SET_BCLK_FREQ                  = 0x23
MAILBOX_OC_CMD_GET_OC_TVB_CONFIG              = 0x24
MAILBOX_OC_CMD_SET_OC_TVB_CONFIG              = 0x25 

MAILBOX_OC_DOMAIN_ID_DDR                = 0x00
MAILBOX_OC_DOMAIN_ID_IA_CORE            = 0x00
MAILBOX_OC_DOMAIN_ID_GT                 = 0x01
MAILBOX_OC_DOMAIN_ID_RING               = 0x02
MAILBOX_OC_DOMAIN_ID_RESERVED           = 0x03  # UNCORE
MAILBOX_OC_DOMAIN_ID_SYSTEM_AGENT       = 0x04
MAILBOX_OC_DOMAIN_ID_L2_ATOM            = 0x05
MAILBOX_OC_DOMAIN_ID_MEMORY_CONTROLLER  = 0x06

SOC_BCLK        = 0x00
CPU_BCLK        = 0x01
PCH_BCLK        = 0x02

SOC_BCLK_SELECT = 0x0
CPU_BCLK_SELECT = 0x2

CPU_OC_MAX_VF_POINTS = 0xF

QCLK_RATIO_MASK         = 0x000000FF
MC_REF_CLK_MASK         = 0x00000100
MC_REF_CLK_OFFSET       = 8
NUM_DDR_CHANNELS_MASK   = 0x00000C00
NUM_DDR_CHANNELS_OFFSET = 10  

# =============================================================================

MIN_VR_INDEX  = 0x0
MAX_VR_INDEX  = 0x5

MAILBOX_VR_CMD_VR_INTERFACE           = 0x04
MAILBOX_VR_CMD_SVID_COMMAND_GET_REG   = 0x07

MAILBOX_VR_CMD_READ_ACOUSTIC_MITIGATION_RANGE       = 0x07
MAILBOX_VR_CMD_WRITE_ACOUSTIC_MITIGATION_RANGE      = 0x08
MAILBOX_VR_CMD_READ_VR_TDC_CONFIG                   = 0x19
MAILBOX_VR_CMD_WRITE_VR_TDC_CONFIG                  = 0x1A

MAILBOX_VR_CMD_SVID_VR_HANDLER                      = 0x18
MAILBOX_VR_SUBCMD_SVID_GET_STRAP_CONFIGURATION      = 0x00
MAILBOX_VR_SUBCMD_SVID_GET_ACDC_LOADLINE            = 0x01
MAILBOX_VR_SUBCMD_SVID_SET_ACDC_LOADLINE            = 0x02
MAILBOX_VR_SUBCMD_SVID_SET_PS_CUTOFF                = 0x03
MAILBOX_VR_SUBCMD_SVID_SET_IMON_CONFIG              = 0x04
MAILBOX_VR_SUBCMD_SVID_GET_MAX_ICC                  = 0x05
MAILBOX_VR_SUBCMD_SVID_SET_MAX_ICC                  = 0x06
MAILBOX_VR_SUBCMD_SVID_GET_VOLTAGE_LIMIT            = 0x07
MAILBOX_VR_SUBCMD_SVID_SET_VOLTAGE_LIMIT            = 0x08
MAILBOX_VR_SUBCMD_SVID_SET_PMON_CONFIG              = 0x09
MAILBOX_VR_SUBCMD_SVID_GET_PMON_PMAX                = 0x0A
MAILBOX_VR_SUBCMD_SVID_SET_PMON_PMAX                = 0x0B
MAILBOX_VR_SUBCMD_SVID_SET_VR_SLEW_RATE             = 0x0C
MAILBOX_VR_SUBCMD_SVID_SET_DISABLE_FAST_PKGC_RAMP   = 0x0D
MAILBOX_VR_SUBCMD_SVID_SET_PSYS_PS4_DISABLE         = 0x0E
MAILBOX_VR_SUBCMD_SVID_GET_PSYS_PS4_DISABLE         = 0x0F
MAILBOX_VR_SUBCMD_SVID_GET_PSYS_REGISTER            = 0x10
MAILBOX_VR_SUBCMD_SVID_SET_PSYS_REGISTER            = 0x11
MAILBOX_VR_SUBCMD_SVID_EXCLUSIVE_MODE               = 0x12
MAILBOX_VR_SUBCMD_SVID_GET_PS_CUTOFF                = 0x13
MAILBOX_VR_SUBCMD_SVID_GET_IMON_CONFIG              = 0x14
MAILBOX_VR_SUBCMD_SVID_READ_REG_WHITELIST           = 0x15
MAILBOX_VR_SUBCMD_SVID_WRITE_REG_WHITELIST          = 0x16
MAILBOX_VR_SUBCMD_SVID_SET_VCCINAUX_IMON_IMAX       = 0x17
MAILBOX_VR_SUBCMD_SVID_GET_VCCINAUX_IMON_IMAX       = 0x18
MAILBOX_VR_SUBCMD_SVID_GET_PMON_CONFIG              = 0x19
MAILBOX_VR_SUBCMD_SVID_SET_VCCINAUX_IMON_CONFIG     = 0x1A
MAILBOX_VR_SUBCMD_SVID_GET_VCCINAUX_IMON_CONFIG     = 0x1B
MAILBOX_VR_SUBCMD_SVID_GET_VR_SLEW_RATE             = 0x1C

MAILBOX_VR_SUBCMD_SVID_SET_VR                       = 0x11
MAILBOX_VR_SUBCMD_SVID_SET_PSYS_VR                  = 0xD
MAILBOX_VR_SUBCMD_SVID_SET_VR_VSYS_MODE             = 0x34
MAILBOX_VR_SUBCMD_SVID_SET_VR_CRIT_THRESHOLD        = 0x4A
MAILBOX_VR_SUBCMD_SVID_SET_VR_CONFIG2               = 0x4F
MAILBOX_VR_SUBCMD_SVID_SET_VR_CONFIG1               = 0x49

MAILBOX_VR_SUBCMD_SVID_SET_PS1_PS0_DYNAMIC_CUTOFF   = 0x20
MAILBOX_VR_SUBCMD_SVID_SET_PS2_PS1_DYNAMIC_CUTOFF   = 0x21
MAILBOX_VR_SUBCMD_SVID_GET_PS1_PS0_DYNAMIC_CUTOFF   = 0x22
MAILBOX_VR_SUBCMD_SVID_GET_PS2_PS1_DYNAMIC_CUTOFF   = 0x23
MAILBOX_VR_SUBCMD_SVID_SET_QUIESCENT_POWER_AND_PLATFORM_CAP = 0x1E
MAILBOX_VR_SUBCMD_SVID_GET_QUIESCENT_POWER_AND_PLATFORM_CAP = 0x1F
MAILBOX_VR_SUBCMD_SVID_GET_FAST_VMODE_ICC_LIMIT     = 0x24
MAILBOX_VR_SUBCMD_SVID_SET_FAST_VMODE_ICC_LIMIT     = 0x25

MAILBOX_PCODE_CMD_READ_SOFT_STRAPS = 0x1F
CPU_SOFTSTRAP_SET1_HIGH            = 1
CPU_SOFTSTRAP_SET2_LOW             = 2
CPU_SOFTSTRAP_SET2_HIGH            = 3
STRAP_RAW_VALUE                    = 0
STRAP_RESOLVED_VALUE               = 1 

CPU_VR_DOMAIN_IA = 0x0
CPU_VR_DOMAIN_GT = 0x1
CPU_VR_DOMAIN_SA = 0x2

# Min Voltage Runtime Data[7:0] , Min Voltage C8 Data[15:8]
MAILBOX_VR_CMD_WRITE_VCCIN_MIN_VOLTAGE         = 0x59  # func: ConfigureSvidVrs 

# =============================================================================

def uint_to_float(value: int, fract, rnd = None) -> float:
    value = value / (2**fract)
    return value if rnd is None else round(value, rnd)
    
def sint_to_float(value: int, fract, sign, rnd = None) -> float:
    if value & (1 << (sign - 1)):
        value -= (1 << sign)
    value = value / (2**fract)
    return value if rnd is None else round(value, rnd)
    

class MsrMailBox():
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

    def get_platform_info(self):
        out = { }
        self.acquire()
        try:
            val = msr_read(MSR_PLATFORM_INFO)
            if not val:
                return out
            #out['raw_value'] = val
            out['MaxNonTurboLimRatio'] = get_bits(val, 0, 8, 15)
            out['SmmSaveCap'] = get_bits(val, 0, 16)
            out['RarEn'] = get_bits(val, 0, 17)
            out['PpinCap'] = get_bits(val, 0, 23)
            out['OcvoltOvrdAvail'] = get_bits(val, 0, 24)
            out['FivrRfiTuningAvail'] = get_bits(val, 0, 25)
            out['Dcu16kModeAvail'] = get_bits(val, 0, 26)
            out['SamplePart'] = get_bits(val, 0, 27)
            out['PrgTurboRatioEn'] = get_bits(val, 0, 28)
            out['PrgTdpLimEn'] = get_bits(val, 0, 29)
            out['PrgTjOffsetEn'] = get_bits(val, 0, 30)
            out['CpuidFaultingEn'] = get_bits(val, 0, 31)
            out['LpmSupport'] = get_bits(val, 0, 32)
            out['ConfigTdpLevels'] = get_bits(val, 0, 33, 34)
            out['PfatEnable'] = get_bits(val, 0, 35)
            out['Peg2dmidisEn'] = get_bits(val, 0, 36)
            out['TimedMwaitEnable'] = get_bits(val, 0, 37)
            out['AsaEn'] = get_bits(val, 0, 38)
            out['MaxEfficiencyRatio'] = get_bits(val, 0, 40, 47)
            out['MinOperatingRatio'] = get_bits(val, 0, 48, 55)
            out['EdramEnable'] = get_bits(val, 0, 57)
            out['Sxp2lmEnable'] = get_bits(val, 0, 58)
            out['SmmSupovrStateLockEnable'] = get_bits(val, 0, 59)
            out['TioEnable'] = get_bits(val, 0, 60)
        finally:
            self.release()
        return out

    def make_pcode_mailbox_cmd(self, command, p1, p2):
        # ref: ICÈ_TÈA_BIOS  (leaked BIOS sources)    # stcruct PCODE_MAILBOX_INTERFACE
        Param1 = p1 & 0xFF
        Param2 = p2 & 0x1FFF
        RunBusy = 1
        return (RunBusy << 31) | (Param2 << 16) | (Param1 << 8) | (command & 0xFF)
    
    def _msr_pcode_mailbox(self, command, p1, p2, data = None):
        self.status = 0xFFF
        cmd = self.make_pcode_mailbox_cmd(command, p1, p2)
        rc = msr_write(VR_MAILBOX_MSR_DATA, 0, data if data else 0)
        if not rc:
            log.error(f'_msr_pcode_mailbox(0x{cmd:X}): Cannot write MSR reg!')
            return None
        rc = msr_write(VR_MAILBOX_MSR_INTERFACE, 0, cmd)
        if not rc:
            log.error(f'_msr_pcode_mailbox(0x{cmd:X}): cannot write MSR reg!')
            return None
        start_time = datetime.now()
        while True:
            val = msr_read(VR_MAILBOX_MSR_INTERFACE)
            if val is None:
                log.error(f'_msr_pcode_mailbox(0x{cmd:X}): cannot read MSR reg!')
                return None
            self.status = val & 0xFFFFFFFF
            RunBusy = True if (self.status & 0x80000000) != 0 else False
            if not RunBusy:
                break
            if datetime.now() - start_time > timedelta(milliseconds = self.mailbox_wait_timeout):
                log.error(f'_msr_pcode_mailbox(0x{cmd:X}): timedout!')
                return None
            pass
        if self.status != 0:
            log.error(f'_msr_pcode_mailbox(0x{cmd:X}): status = 0x{self.status:X}')
            return None
        return msr_read(VR_MAILBOX_MSR_DATA)

    def make_oc_mailbox_cmd_OLD(self, command, p1, p2):   # ChatGPT ;-)
        Param1 = p1 & 0xFF  # Core ID
        Param2 = p2 & 0x1F  # Domain ID
        Command = command & 0x3FFF
        RunBusy = 1
        return (RunBusy << 31) | (Command << 21) | (Param2 << 16) | Param1

    def make_oc_mailbox_cmd(self, command, p1, p2):
        # ref: ICÈ_TÈA_BIOS  (leaked BIOS sources)  # file "CpuMailboxLib.h"  struct _OC_MAILBOX_FULL 
        Param1 = p1 & 0xFF  # Core ID
        Param2 = p2 & 0xFF  # Domain ID
        RunBusy = 1
        return (RunBusy << 31) | (Param2 << 16) | (Param1 << 8) | (command & 0xFF)

    def _msr_oc_mailbox(self, command, p1, p2, data = None):
        self.status = 0xFFF
        cmd = self.make_oc_mailbox_cmd(command, p1, p2)
        rc = msr_write(MSR_OC_MAILBOX, cmd, data if data else 0)  # struct{dw_DATA,dw_CMD}
        if not rc:
            log.error(f'_msr_oc_mailbox(0x{cmd:X}): cannot write MSR reg!')
            return None
        start_time = datetime.now()
        while True:
            val = msr_read(MSR_OC_MAILBOX)
            if val is None:
                log.error(f'_msr_oc_mailbox(0x{cmd:X}): cannot read MSR reg!')
                return None
            self.status = val >> 32
            RunBusy = True if (self.status & 0x80000000) != 0 else False
            if not RunBusy:
                break
            if datetime.now() - start_time > timedelta(milliseconds = self.mailbox_wait_timeout):
                log.error(f'_msr_oc_mailbox(0x{cmd:X}): timedout!')
                return None
            pass
        if self.status != 0:
            log.error(f'_msr_oc_mailbox(0x{cmd:X}): status = 0x{self.status:X}')
            return None
        return val & 0xFFFFFFFF

    def parse_vr_topology(self, data):
        # struct OCMB_VR_TOPOLOGY_DATA / VR_TOPOLOGY_DATA
        vrt = { }
        vrt['Vcc1p05Cpu'] = get_bits(data, 0, 1)
        vrt['VccStPgExist'] = get_bits(data, 0, 3)
        vrt['VccInAuxLpLevel'] = get_bits(data, 0, 5)
        vrt['VccInAuxImonDisable'] = get_bits(data, 0, 7)
        vrt['VrIaAddress'] = get_bits(data, 0, 8, 11)
        vrt['VrIaSvidType'] = get_bits(data, 0, 12)
        vrt['VrGtAddress'] = get_bits(data, 0, 13, 16)
        vrt['VrGtSvidType'] = get_bits(data, 0, 17)
        vrt['SetIaVrVid'] = get_bits(data, 0, 18)
        vrt['PlatformType'] = get_bits(data, 0, 19)
        vrt['VccInAux_Imon_Add_Sel'] = get_bits(data, 0, 20)
        vrt['VrSaAddress'] = get_bits(data, 0, 21, 24)
        vrt['VrSaSvidType'] = get_bits(data, 0, 25)
        vrt['VrVccAnaAddress'] = get_bits(data, 0, 26, 29)
        vrt['VrVccAnaSvidType'] = get_bits(data, 0, 30)
        vrt['PsysDisable'] = get_bits(data, 0, 31)
        return vrt
    
    def _read_base_info(self):
        out = { }
        self.VrIaAddress = None
        self.VrGtAddress = None
        
        # ref: ICÈ_TÈA_BIOS  (leaked BIOS sources)  # file "OverClockSetup.c"   func: InitVrIccOcStrings
        data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_VR_TOPOLOGY, 0, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_GET_VR_TOPOLOGY({0},{0}): status = 0x{self.status:X}')
        else:
            out['VR_TOPOLOGY'] = self.parse_vr_topology(data)
            self.VrIaAddress = out['VR_TOPOLOGY']['VrIaAddress']
            self.VrGtAddress = out['VR_TOPOLOGY']['VrGtAddress']

        if self.VrIaAddress is not None:
            data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_ICCMAX, self.VrIaAddress, 0)
            if data is None:
                log.error(f'MAILBOX_OC_CMD_GET_ICCMAX({self.VrIaAddress},{0}): status = 0x{self.status:X}')
            else:
                # struct OCMB_ICCMAX_DATA
                out['IccMaxValue'] = get_bits(data, 0, 0, 10) * 0.25
                out['UnlimitedIccMaxMode'] = get_bits(data, 0, 31)

        data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_BCLK_FREQUENCY_CMD, 0, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_GET_BCLK_FREQUENCY_CMD({0},{0}): status = 0x{self.status:X}')
        else:
            out['BCLK_FREQ'] = data / 1000.0 if data else None
        
        data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_BCLK_FREQ, SOC_BCLK_SELECT, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_GET_BCLK_FREQ({SOC_BCLK_SELECT},{0}): status = 0x{self.status:X}')
        else:
            out['SOC_BCLK_FREQ'] = data / 1000.0 if data else None

        data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_BCLK_FREQ, CPU_BCLK_SELECT, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_GET_BCLK_FREQ({CPU_BCLK_SELECT},{0}): status = 0x{self.status:X}')
        else:
            out['CPU_BCLK_FREQ'] = data / 1000.0 if data else None

        data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_DDR_CAPABILITIES, 0, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_GET_DDR_CAPABILITIES({0},{0}): status = 0x{self.status:X}')
        else:
            # struct DDR_CAPABILITIES_ITEM
            ddr = out['DDR_CAP'] = { }
            ddr['raw'] = get_bits(data, 0, 0, 31)
            ddr['QclkRatio'] = get_bits(data, 0, 0, 7)   # QCLK_RATIO_MASK
            ddr['McReferenceClk'] = 100.0 if get_bits(data, 0, 8) else 133.33   # MC_REF_CLK_MASK + MC_REF_CLK_OFFSET
            ddr['NumDdrChannels'] = get_bits(data, 0, 10, 11)  # NUM_DDR_CHANNELS_MASK + NUM_DDR_CHANNELS_OFFSET

        # ref: Intel SDM  section: Table 2-2. IA-32 Architectural MSRs (Contd.)
        data = msr_read(MSR_IA32_PERF_STATUS)
        # ref: https://community.intel.com/t5/Software-Tuning-Performance/MSR-PERF-STATUS-voltage-reading/m-p/1169884
        out['Core_VID'] = get_bits(data, 0, 0, 7)
        out['Core_FID'] = get_bits(data, 0, 8, 15)  # CPU Freq Ratio
        out['CoreVoltage'] = round(get_bits(data, 0, 32, 47) / (2**13), 4)  # Vcore
        
        data = msr_read(MSR_DDR_RAPL_LIMIT)
        if data is not None:
            # struct MSR_DDR_RAPL_LIMIT_REGISTER
            ddr = out['DDR_RAPL'] = { }
            ddr['Limit1Power'] = get_bits(data, 0, 0, 14) * 0.125
            ddr['Limit1Enable'] = get_bits(data, 0, 15)
            ddr['Limit1TimeWindowY'] = get_bits(data, 0, 17, 21)
            ddr['Limit1TimeWindowX'] = get_bits(data, 0, 22, 23)
            ddr['Limit2Power'] = get_bits(data, 0, 32, 46) * 0.125
            ddr['Limit2Enable'] = get_bits(data, 0, 47)
            ddr['Limit2TimeWindowY'] = get_bits(data, 0, 49, 53)
            ddr['Limit2TimeWindowX'] = get_bits(data, 0, 54, 55)
            ddr['Locked'] = get_bits(data, 0, 63)
        
        DomainId = MAILBOX_OC_DOMAIN_ID_IA_CORE
        data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_OC_CAPABILITIES, DomainId, 0)
        if data is None:
            log.error(f'MAILBOX_OC_CMD_GET_OC_CAPABILITIES({DomainId},{0}): status = 0x{self.status:X}')
        else:
            out['MaxOcRatioLimit'] = get_bits(data, 0, 0, 7)
            out['RatioOcSupported'] = get_bits(data, 0, 8)
            out['VoltageOverridesSupported'] = get_bits(data, 0, 9)
            out['VoltageOffsetSupported'] = get_bits(data, 0, 10)

        vfd = out['VF'] = { }
        DOMAIN_list = [                     'IA_CORE',                    'RING',                    'SYSTEM_AGENT',                     'UNCORE' ]
        domain_list = [ MAILBOX_OC_DOMAIN_ID_IA_CORE, MAILBOX_OC_DOMAIN_ID_RING, MAILBOX_OC_DOMAIN_ID_SYSTEM_AGENT, MAILBOX_OC_DOMAIN_ID_RESERVED ]
        for dn, DomainId in enumerate(domain_list):
            vfi = vfd[DOMAIN_list[dn]] = { }
            VfPointIndex = 0    # 0 ... CPU_OC_MAX_VF_POINTS
            data = self._msr_oc_mailbox(MAILBOX_OC_CMD_GET_VOLTAGE_FREQUENCY, DomainId, VfPointIndex)
            if data is None:
                log.error(f'MAILBOX_OC_CMD_GET_VOLTAGE_FREQUENCY({DomainId},{VfPointIndex}): status = 0x{self.status:X}')
                continue
            # struct VF_MAILBOX_COMMAND_DATA
            vfi['MaxOcRatio'] = get_bits(data, 0, 0, 7)
            vfi['VoltageTargetMode'] = 'ADAPTIVE' if get_bits(data, 0, 20) == 0 else 'OVERRIDE'
            vfi['VoltageTarget'] = uint_to_float(get_bits(data, 0, 8,  19), 10, 4)      # U12.2.10V format
            vfi['VoltageOffset'] = sint_to_float(get_bits(data, 0, 21, 31), 10, 11, 4)  # S11.0.10V format
    
        return out

    def _read_PL4_config(self):
        out = { }
        if cpu_id in i12_FAM:
            # ref: ICÈ_TÈA_BIOS  (leaked BIOS sources)  # func: ConfigurePl4PowerLimits
            data = msr_read(MSR_VR_CURRENT_CONFIG)
            if data is None:
                log.error(f'Cannot read MSR MSR_VR_CURRENT_CONFIG')
            else:
                # struct MSR_VR_CURRENT_CONFIG_REGISTER
                out['CurrentLimit'] = get_bits(data, 0, 0, 12) * 0.125 # Current limitation in 0.125 A increments. This field is locked by VR_CURRENT_CONFIG[LOCK]. When the LOCK bit is set to 1b, this field becomes Read Only.
                out['Lock'] = get_bits(data, 0, 31)
                out['Psi1Threshold'] = get_bits(data, 0, 32, 41)
                out['Psi2Threshold'] = get_bits(data, 0, 42, 51)
                out['Psi3Threshold'] = get_bits(data, 0, 52, 61)
                out['Ps4Enable'] = get_bits(data, 0, 62)
        if cpu_id in i15_FAM:
            # ref: 335592-088-sdm-vol-4.pdf  ( Intel SDM vol.4 )
            data = msr_read(MSR_PKG_POWER_LIMIT_4)
            if data is None:
                log.error(f'Cannot read MSR MSR_PKG_POWER_LIMIT_4')
            else:
                out['CurrentLimit'] = get_bits(data, 0, 0, 15) * 0.125
                out['Lock'] = get_bits(data, 0, 31)
        return { 'PowerLimit4': out }

    def make_vr_cmd_payload(self, VrId, VrCommand, VrRegAddr, Lock = 0):
        # struct MAILBOX_VR_INTERFACE_DATA
        return (Lock << 31) | ((VrRegAddr & 0xFF) << 16) | ((VrCommand & 0x1F) << 4) | (VrId & 0xF)

    def _read_vr_info(self):
        out = { }
        if True:
            # ref: ICÈ_TÈA_BIOS  (leaked BIOS sources)  # file "PeiVrFruLib.c"   func: GetVrId
            VrRegAddr = 0x5   # Get ProtocolId
            data = self.make_vr_cmd_payload(0, MAILBOX_VR_CMD_SVID_COMMAND_GET_REG, VrRegAddr)
            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_VR_INTERFACE, 0, 0, data)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_VR_INTERFACE({0},{0}): status = 0x{self.status:X}')
            else:
                out['VR_Protocol_ID'] = data
                out['VR_Protocol_ID_HEX'] = f'0x{data:X}'

            VrRegAddr = 0x0   # Get Vendor ID
            data = self.make_vr_cmd_payload(0, MAILBOX_VR_CMD_SVID_COMMAND_GET_REG, VrRegAddr)
            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_VR_INTERFACE, 0, 0, data)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_VR_INTERFACE({0},{0}): status = 0x{self.status:X}')
            else:
                out['VR_Vendor_ID'] = data
                out['VR_Vendor_ID_HEX'] = f'0x{data:X}'

            VrRegAddr = 0x1   # Get ProdId
            data = self.make_vr_cmd_payload(0, MAILBOX_VR_CMD_SVID_COMMAND_GET_REG, VrRegAddr)
            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_VR_INTERFACE, 0, 0, data)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_VR_INTERFACE({0},{0}): status = 0x{self.status:X}')
            else:
                out['VR_Product_ID'] = data
                out['VR_Product_ID_HEX'] = f'0x{data:X}'
        
        if self.VrIaAddress is None:
            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_SVID_VR_HANDLER, MAILBOX_VR_SUBCMD_SVID_GET_STRAP_CONFIGURATION, 0)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_SVID_VR_HANDLER({MAILBOX_VR_SUBCMD_SVID_GET_STRAP_CONFIGURATION},{0}): status = 0x{self.status:X}')
            else:
                out['VR_TOPOLOGY'] = self.parse_vr_topology(data)
                self.VrIaAddress = out['VR_TOPOLOGY']['VrIaAddress']
                self.VrGtAddress = out['VR_TOPOLOGY']['VrGtAddress']

        if True:
            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_SVID_VR_HANDLER, MAILBOX_VR_SUBCMD_SVID_GET_VCCINAUX_IMON_IMAX, 0)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_SVID_VR_HANDLER({MAILBOX_VR_SUBCMD_SVID_GET_VCCINAUX_IMON_IMAX},{0}): status = 0x{self.status:X}')
            else:
                out['VccInAuxImonIccImax'] = data / 4.0 # (1/4 Amp)  VccIn AUX IccMax Current

        if self.VrIaAddress is not None:
            VR_ADDRESS_MASK = 0xF
            VR_ADDR = self.VrIaAddress & VR_ADDRESS_MASK

            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_SVID_VR_HANDLER, MAILBOX_VR_SUBCMD_SVID_GET_MAX_ICC, VR_ADDR)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_SVID_VR_HANDLER({MAILBOX_VR_SUBCMD_SVID_GET_MAX_ICC},{VR_ADDR}): status = 0x{self.status:X}')
            else:
                out['IccMax'] = (data & 0x07FF) * 0.25 # Amp

            VR_VOLTAGE_LIMIT_MASK = 0xFFFF
 
            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_SVID_VR_HANDLER, MAILBOX_VR_SUBCMD_SVID_GET_VOLTAGE_LIMIT, VR_ADDR)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_SVID_VR_HANDLER({MAILBOX_VR_SUBCMD_SVID_GET_VOLTAGE_LIMIT},{VR_ADDR}): status = 0x{self.status:X}')
            else:
                out['SVID_VCC_MAX'] = uint_to_float(data & VR_VOLTAGE_LIMIT_MASK, 13, 3)  # Mailbox Voltage Limit defined as U16.3.13, Range 0-7.999V

            data = self._msr_pcode_mailbox(MAILBOX_VR_CMD_SVID_VR_HANDLER, MAILBOX_VR_SUBCMD_SVID_GET_ACDC_LOADLINE, VR_ADDR)
            if data is None:
                log.error(f'MAILBOX_VR_CMD_SVID_VR_HANDLER({MAILBOX_VR_SUBCMD_SVID_GET_ACDC_LOADLINE},{VR_ADDR}): status = 0x{self.status:X}')
            else:
                divisor = 100.0
                if cpu_id in i15_FAM:
                    divisor = 1024.0
                out['AC_loadline'] = get_bits(data, 0, 0, 15) / divisor
                out['DC_loadline'] = get_bits(data, 0, 16, 31) / divisor

        return { 'VR': out }
    
    def read_full_info(self):
        out = { }
        self.platform_info = self.get_platform_info()
        out['platform_info'] = self.platform_info
        self.acquire()
        try:
            out.update( self._read_base_info() )
            out.update( self._read_PL4_config() )
            out.update( self._read_vr_info() )
        finally:
            self.release()
        return out
    
    def check_mailbox_mutex(self):
        rc = 0
        mtx_list = [ LOCAL_OC_MAILBOX_MUTEX_NAME, GLOBAL_OC_MAILBOX_MUTEX_NAME ]
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
            mutex = CreateMutexW(GLOBAL_OC_MAILBOX_MUTEX_NAME)
            if not mutex:
                raise RuntimeError(f'Cannot open or create global mutex "{GLOBAL_OC_MAILBOX_MUTEX_NAME}"')
            self.mutex = mutex


if __name__ == "__main__":
    SdkInit(None, 0)
    cpu_id = GetProcessorExtendedModel() 
    print('Processor Model ID: 0x%X' % cpu_id)
    log.change_log_level(log.TRACE)
    mmb = MsrMailBox()
    mmb.cpu_id = cpu_id
    mmb.acquire()
    try:
        val = msr_read(MSR_PLATFORM_INFO)
        if val:
            print(f'MSR_PLATFORM_INFO = 0x{val:08X}')
    finally:
        mmb.release()
    
    out = mmb.read_full_info()
    print(json.dumps(out, indent=4))
    
    
    