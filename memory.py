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

PCI_VENDOR_ID_INTEL = 0x8086

INTEL_ALDERLAKE           = 0x97   # 12th gen
INTEL_ALDERLAKE_L         = 0x9A   # 12th gen
INTEL_RAPTORLAKE          = 0xB7   # 13th gen + 14th gen
INTEL_RAPTORLAKE_P        = 0xBA   #
INTEL_RAPTORLAKE_S        = 0xBF   #
INTEL_BARTLETTLAKE        = 0xD7   # Raptor Cove
INTEL_METEORLAKE          = 0xAC   # Redwood Cove / Crestmont
INTEL_METEORLAKE_L        = 0xAA   #
INTEL_ARROWLAKE_H         = 0xC5   # Lion Cove / Skymont
INTEL_ARROWLAKE           = 0xC6
INTEL_ARROWLAKE_U         = 0xB5
INTEL_LUNARLAKE_M         = 0xBD   # Lion Cove / Skymont
INTEL_PANTHERLAKE_L       = 0xCC   # Crestmont

def read_bits(buf, offset, firts_bit, last_bit = None, bits = None):
    if offset is None:
        offset = 0
    if last_bit is None and bits is None:
        raise ValueError()
    if last_bit is None:
        last_bit = firts_bit + bits - 1
    if last_bit < firts_bit:
        raise ValueError()
    size = ((last_bit + 1) // 8) + 1
    value = int.from_bytes(buf[offset:offset+size], 'little', signed = False)
    if firts_bit > 0:
        value >>= firts_bit
    return SETDIM(value, last_bit - firts_bit + 1)

proc_fam = None
proc_model_id = None
MCHBAR_BASE = None

ADL_FAM = [ INTEL_ALDERLAKE, INTEL_ALDERLAKE_L, INTEL_RAPTORLAKE, INTEL_RAPTORLAKE_P, INTEL_RAPTORLAKE_S]

def get_mchbar_info(info, channel):
    global proc_model_id, MCHBAR_BASE 
    tm = { }    
    if proc_model_id in ADL_FAM:
        MC_REGS_OFFSET = 0xE000
        MC_REGS_SIZE = 0x800
        offset = MC_REGS_OFFSET + MC_REGS_SIZE * channel
        data = phymem_read(MCHBAR_BASE + offset, MC_REGS_SIZE)
        tm["__channel"] = channel
        IMC_CR_TC_ODT = 0x070     # ODT timing parameters
        tm["tCL"] = read_bits(data, IMC_CR_TC_ODT, 16, 22)
        tm["tCWL"] = read_bits(data, IMC_CR_TC_ODT, 24, 31)
        IMC_CR_TC_PRE = 0         # Timing constraints to PRE commands
        tm["tRP"] = read_bits(data, IMC_CR_TC_PRE, 0, 7)
        tm["tRPab_ext"] = read_bits(data, IMC_CR_TC_PRE, 8, 12)
        tm["tRDPRE"] = read_bits(data, IMC_CR_TC_PRE, 13, 19)
        tm["tRTP"] = tm["tRDPRE"]
        tm["tPPD"] = read_bits(data, IMC_CR_TC_PRE, 20, 23)
        tm["tWRPRE"] = read_bits(data, IMC_CR_TC_PRE, 32, 41)
        tm["tRAS"] = read_bits(data, IMC_CR_TC_PRE, 42, 50)
        tm["tRCD"] = read_bits(data, IMC_CR_TC_PRE, 51, 58)
        tm["DERATING_EXT"] = read_bits(data, IMC_CR_TC_PRE, 59, 62)
        IMC_REFRESH_TC = 0x43C     # Refresh timing parameters
        tm["tREFI"] = read_bits(data, IMC_REFRESH_TC, 0, 17)
        tm["tRFC"]  = read_bits(data, IMC_REFRESH_TC, 18, 30)
        IMC_REFRESH_AUX = 0x438
        tm["oref_ri"]  = read_bits(data, IMC_REFRESH_AUX, 0, 7)
        tm["REFRESH_HP_WM"]  = read_bits(data, IMC_REFRESH_AUX, 8, 11)
        tm["REFRESH_PANIC_WM"]  = read_bits(data, IMC_REFRESH_AUX, 12, 15)
        tm["COUNTTREFIWHILEREFENOFF"]  = read_bits(data, IMC_REFRESH_AUX, 16, 16)
        tm["HPREFONMRS"]  = read_bits(data, IMC_REFRESH_AUX, 17, 17)
        tm["SRX_REF_DEBITS"]  = read_bits(data, IMC_REFRESH_AUX, 18, 19)
        tm["RAISE_BLK_WAIT"]  = read_bits(data, IMC_REFRESH_AUX, 20, 23)
        tm["tREFIx9"]  = read_bits(data, IMC_REFRESH_AUX, 24, 31)   # Should be programmed to 8 * tREFI / 1024 (to allow for possible delays from ZQ or ISOC).
        IMC_REFRESH_EXT = 0x488
        tm["PBR_DISABLE"]  = read_bits(data, IMC_REFRESH_EXT, 0, 0)
        tm["PBR_OOO_DIS"]  = read_bits(data, IMC_REFRESH_EXT, 1, 1)
        tm["PBR_DISABLE_ON_HOT"]  = read_bits(data, IMC_REFRESH_EXT, 3, 3)
        tm["PBR_EXIT_ON_IDLE_CNT"]  = read_bits(data, IMC_REFRESH_EXT, 4, 9)
        tm["tRFCpb"]   = read_bits(data, IMC_REFRESH_EXT, 10, 20)
        tm["tRFM"]     = read_bits(data, 0x40C, 0, 10)    # Default is same as tRFCpb
        IMC_CR_TC_ACT = 0x008     # Timing constraints to ACT commands
        tm["tFAW"]     = read_bits(data, IMC_CR_TC_ACT, 0, 8)
        tm["tRRD_sg"]  = read_bits(data, IMC_CR_TC_ACT, 9, 14)
        tm["tRRD_L"] = tm["tRRD_sg"]
        tm["tRRD_dg"]  = read_bits(data, IMC_CR_TC_ACT, 15, 21)
        tm["tRRD_S"] = tm["tRRD_dg"]
        tm["tREFSBRD"] = read_bits(data, IMC_CR_TC_ACT, 24, 31)
        IMC_TC_PWDEN = 0x050     # Power Down Timing
        tm["tCKE"] = read_bits(data, IMC_TC_PWDEN, 0, 6)
        tm["tXP"] = read_bits(data, IMC_TC_PWDEN, 7, 13)
        tm["tXPDLL"] = read_bits(data, IMC_TC_PWDEN, 14, 20)
        tm["tRDPDEN"] = read_bits(data, IMC_TC_PWDEN, 21, 28)
        tm["tWRPDEN"] = read_bits(data, IMC_TC_PWDEN, 32, 41)
        tm["tCSH"] = read_bits(data, IMC_TC_PWDEN, 42, 47)
        tm["tCSL"] = read_bits(data, IMC_TC_PWDEN, 48, 53)
        tm["tPRPDEN"] = read_bits(data, IMC_TC_PWDEN, 59, 63)
        IMC_SC_GS_CFG = 0x088   # Scheduler configuration
        tm["CMD_STRETCH"] = read_bits(data, IMC_SC_GS_CFG, 3, 4)
        CR_map = { 0: "1N", 1: '2N', 2: '3N', 3: "N:1" }
        tm["tCR"] = CR_map[tm["CMD_STRETCH"]]
        tm["N_TO_1_RATIO"] = read_bits(data, IMC_SC_GS_CFG, 5, 7)
        tm["ADDRESS_MIRROR"] = read_bits(data, IMC_SC_GS_CFG, 8, 11)
        tm["GEAR4"] = read_bits(data, IMC_SC_GS_CFG, 15, 15)
        tm["NO_GEAR4_PARAM_DIVIDE"] = read_bits(data, IMC_SC_GS_CFG, 16, 16)
        tm["X8_DEVICE"] = read_bits(data, IMC_SC_GS_CFG, 28, 29)
        tm["NO_GEAR2_PARAM_DIVIDE"] = read_bits(data, IMC_SC_GS_CFG, 30, 30)
        tm["GEAR2"] = read_bits(data, IMC_SC_GS_CFG, 31, 31)
        tm["DDR_1DPC_SPLIT_RANKS_ON_SUBCH"] = read_bits(data, IMC_SC_GS_CFG, 32, 33)
        tm["WRITE0_ENABLE"] = read_bits(data, IMC_SC_GS_CFG, 49, 49)
        tm["WCKDIFFLOWINIDLE"] = read_bits(data, IMC_SC_GS_CFG, 54, 54)
        tm["tCPDED"] = read_bits(data, IMC_SC_GS_CFG, 56, 60)
        
        tm["tRDRD_sg"] = read_bits(data, 0x00C, 0, 6)
        tm["ALLOW_2CYC_B2B_LPDDR"] = read_bits(data, 0x00C, 7, 7)
        tm["tRDRD_dg"] = read_bits(data, 0x00C, 8, 14)
        tm["tRDRD_dr"] = read_bits(data, 0x00C, 16, 23)
        tm["tRDRD_dd"] = read_bits(data, 0x00C, 24, 31)
        
        tm["tRDWR_sg"] = read_bits(data, 0x010, 0, 7)
        tm["tRDWR_dg"] = read_bits(data, 0x010, 8, 15)
        tm["tRDWR_dr"] = read_bits(data, 0x010, 16, 23)
        tm["tRDWR_dd"] = read_bits(data, 0x010, 24, 31)
        
        tm["tWRRD_sg"] = read_bits(data, 0x014, 0, 8)
        tm["tWRRD_dg"] = read_bits(data, 0x014, 9, 17)
        tm["tWRRD_dr"] = read_bits(data, 0x014, 18, 24)
        tm["tWRRD_dd"] = read_bits(data, 0x014, 25, 31)

        tm["tWRWR_sg"] = read_bits(data, 0x018, 0, 6)
        tm["tWRWR_dg"] = read_bits(data, 0x018, 8, 14)
        tm["tWRWR_dr"] = read_bits(data, 0x018, 16, 22)
        tm["tWRWR_dd"] = read_bits(data, 0x018, 24, 31)

        tm["tXSDLL"] = read_bits(data, 0x440, 0, 12)
        tm["tZQOPER"] = read_bits(data, 0x440, 16, 23)   # UNDOC
        tm["tMOD"] = read_bits(data, 0x440, 24, 31)   # UNDOC
        
        tm["DEC_tCWL"] = read_bits(data, 0x478, 0, 5)   # The number of cycles (DCLK) decreased from tCWL.
        tm["ADD_tCWL"] = read_bits(data, 0x478, 6, 11)  # The number of cycles (DCLK) increased to tCWL.
        tm["ADD_1QCLK_DELAY"] = read_bits(data, 0x478, 12, 12)  # In Gear2, MC QCLK is actually 1xClk of the DDR, the regular MC register can only set even number of cycles (working in Dclk == 2 * 1xClk)
        xCWL = tm['tCWL']
        xCWL -= tm['DEC_tCWL']  # UNDOC
        xCWL += tm['ADD_tCWL']  # UNDOC
        tm["tWTR_L"] = tm['tWRRD_sg'] - xCWL - 10
        tm["tWTR_S"] = tm['tWRRD_dg'] - xCWL - 10
        #tm["tWTR_L"] = tm['tWRRD_sg'] - tm['tCWL'] - 10  # if ASRock then -6
        #tm["tWTR_S"] = tm['tWRRD_dg'] - tm['tCWL'] - 10  # if ASRock then -6 

        tm["tXSR"] = read_bits(data, 0x4C0, 0, 12)
        tm["tSR"] = read_bits(data, 0x4C0, 52, 57)

        if info["DDR_TYPE"] in [ 0, 3 ]:
            tWR_quantity = 4  # DDR4 and LPDDR4
        else:
            tWR_quantity = 8  # DDR5 and LPDDR5

        if tm['tWRPRE'] > tm['tCWL'] + tWR_quantity:
            tm['tWR'] = tm['tWRPRE'] - tm['tCWL'] - tWR_quantity

        if tm['GEAR4']:
            tm['GEAR'] = 4
        elif tm['GEAR2']:
            tm['GEAR'] = 2
        else:
            tm['GEAR'] = 1

        tm["tRTL_0"] = read_bits(data, 0x020, 0, 7)
        tm["tRTL_1"] = read_bits(data, 0x020, 8, 15)
        tm["tRTL_2"] = read_bits(data, 0x020, 16, 23)
        tm["tRTL_3"] = read_bits(data, 0x020, 24, 31)
        
        tm["Banks"] = 8 if read_bits(data, IMC_SC_GS_CFG, 0, 2) else 16  # UNDOC
        #tm["Columns"] = 1 << 10
        
    else:
        raise RuntimeError(f'ERROR: Processor model 0x{proc_model_id:X} not supported')
    return tm

def get_mem_ctrl(ctrl_num):
    global proc_fam, proc_model_id, MCHBAR_BASE
    MCHBAR_BASE = pci_cfg_read(0, 0, 0, 0x48, '4')
    if (MCHBAR_BASE & 1) != 1:
        raise RuntimeError(f'ERROR: Readed incorrect MCHBAR_BASE = 0x{MCHBAR_BASE:X}')
    if MCHBAR_BASE < 0xFE000000:
        raise RuntimeError(f'ERROR: Readed incorrect MCHBAR_BASE = 0x{MCHBAR_BASE:X}')
    MCHBAR_BASE = MCHBAR_BASE - 1
    print(f'MCHBAR_BASE = 0x{MCHBAR_BASE:X}')
    mchbar_mmio = MCHBAR_BASE + 0x6000
    if proc_model_id < INTEL_ALDERLAKE:
        raise RuntimeError(f'ERROR: Processor model 0x{proc_model_id:X} not supported')
    MCHBAR_BASE += 0x10000 * ctrl_num
    if proc_model_id in ADL_FAM:
        MADCH = phymem_read(MCHBAR_BASE + 0xD800, 8)
        mi = { }
        mi["DDR_TYPE"]     = read_bits(MADCH, 0, 0, 2)
        mi["CH_L_MAP"]     = read_bits(MADCH, 0, 4, 4)  # Channel L mapping to physical channel.  0 = Channel 0  1 = Channel 1
        mi["CH_S_SIZE"]    = read_bits(MADCH, 0, 12, 19)
        mi["tPPD"]         = read_bits(MADCH, 0, 20, 23)
        mi["CH_WIDTH"]     = read_bits(MADCH, 0, 27, 28)
        mi["HALF_CL_MODE"] = read_bits(MADCH, 0, 31, 31)
        mi["Dimm_L_Map"]   = read_bits(MADCH, 1, 0, 0)
        mi["EIM"]          = read_bits(MADCH, 1, 8, 8)
        mi["ECC"]          = read_bits(MADCH, 1, 12, 13)
        mi["CRC"]          = read_bits(MADCH, 1, 14, 14)
        if mi["DDR_TYPE"] in [ 0, 3 ]:
            mi["DDR_ver"] = 4  # DDR4 and LPDDR4
        else:
            mi["DDR_ver"] = 5  # DDR5 and LPDDR5
    else:
        raise RuntimeError(f'ERROR: Processor model 0x{proc_model_id:X} not supported')
    #print(json.dumps(mi, indent = 4))
    mchan = [ ]
    for cnum in range(0, 2):
        data = phymem_read(MCHBAR_BASE + 0xD804 + cnum * 4, 4)
        if data == b'\xFF\xFF\xFF\xFF':
            raise RuntimeError()
        mc = { }
        mc["__channel"] = cnum
        mc["DIMM_L_MAP"] = read_bits(data, 0, 0, 0)  # Virtual DIMM L mapping to physical DIMM: 0 = DIMM0, 1 = DIMM1
        mc["EIM"] = read_bits(data, 0, 8, 8)
        mc["ECC"] = read_bits(data, 0, 12, 13)
        mc["CRC"] = read_bits(data, 0, 14, 14)   # CRC Mode: 0 = Disabled  1 = Enabled
        data = phymem_read(MCHBAR_BASE + 0xD80C + cnum * 4, 4)
        if data == b'\xFF\xFF\xFF\xFF':
            raise RuntimeError()
        mc["Dimm_L_Size"] = read_bits(data, 0, 0, 6)   # DIMM L Size in 512 MB multiples
        mc["DLW"]         = read_bits(data, 0, 7, 8)   # DIMM L width: 0=x8, 1=x16, 2=x32 
        mc["DLNOR"]       = read_bits(data, 0, 9, 10)  # DIMM L ranks: 0=1, 1=2, 2=3, 3=4
        mc["DDR5_DS_8GB"] = read_bits(data, 0, 11, 11) # DIMM S: 1 = 8Gb , 0 = more than 8Gb capacity
        mc["DDR5_DL_8GB"] = read_bits(data, 0, 12, 12) # DIMM L: 0 = DDR5 capacity is more than 8Gb, 1 = DDR5 capacity is 8Gb
        mc["Dimm_S_Size"] = read_bits(data, 0, 16, 22)
        mc["DSW"]         = read_bits(data, 0, 24, 25) # DIMM S width: 0=x8, 1=x16, 2=x32
        mc["DSNOR"]       = read_bits(data, 0, 26, 27) # DIMM S ranks: 0=1, 1=2, 2=3, 3=4
        mc["BG0_BIT_OPTIONS"] = read_bits(data, 0, 28, 29)
        mc["DECODER_EBH"] = read_bits(data, 0, 30, 31)
        mchan.append( mc )
    #if mi["CH_L_MAP"]:
    #    mchan.reverse()
    memory = { }
    memory['controller'] = ctrl_num
    memory['info'] = mi
    memory['channels'] = mchan
    for channel in range(0, 2):    
        mchan[channel]['info'] = get_mchbar_info(mi, channel)
    return memory

def get_mem_info():
    global proc_fam, proc_model_id, MCHBAR_BASE
    print('Processor Specification:', GetProcessorSpecification())
    proc_fam = GetProcessorFamily()
    print('Processor Family: 0x%X' % proc_fam)
    proc_model_id = GetProcessorExtendedModel() 
    print('Processor Model ID: 0x%X' % proc_model_id)    
    if proc_fam != 6:
        raise RuntimeError(f'ERROR: Currently support only Intel processors')
    memory = [ ]
    for ctrl_num in range(0, 2):
        mem = get_mem_ctrl(ctrl_num)
        memory.append( mem )
    return memory

if __name__ == "__main__":
    SdkInit(None, 0)
    out = get_mem_info()
    #print(json.dumps(memory, indent = 4))
    with open('IMC.json', 'w') as file:
        json.dump(out, file, indent=4)
    
