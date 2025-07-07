#
# Copyright (C) 2025 remittor
#

import os
import sys
import time
import struct
import ctypes as ct
import ctypes.wintypes as wintypes
from ctypes import byref
from types import SimpleNamespace
import json

__author__ = 'remittor'

from cpuidsdk64 import *
from hardware import *

# DOC: 13th Generation Intel ® Core™ Processor Datasheet, Volume 2 of 2
# ref: https://cdrdv2-public.intel.com/743846/743846-001.pdf

proc_fam = None
proc_model_id = None
MCHBAR_BASE = None
DMIBAR_BASE = None
gdict = { }

ADL_FAM = [ INTEL_ALDERLAKE, INTEL_ALDERLAKE_L, INTEL_RAPTORLAKE, INTEL_RAPTORLAKE_P, INTEL_RAPTORLAKE_S]

def get_mchbar_info(info, controller, channel):
    global gdict, proc_model_id, MCHBAR_BASE 
    MCHBAR_addr = MCHBAR_BASE + (0x10000 * controller)
    tm = { }    
    if proc_model_id in ADL_FAM:
        MC_REGS_OFFSET = 0xE000
        MC_REGS_SIZE = 0x800
        offset = MC_REGS_OFFSET + (MC_REGS_SIZE * channel)
        data = phymem_read(MCHBAR_addr + offset, MC_REGS_SIZE)
        tm["__channel"] = channel
        IMC_CR_TC_ODT = 0x070     # ODT timing parameters
        tm["tCL"] = get_bits(data, IMC_CR_TC_ODT, 16, 22)
        tm["tCWL"] = get_bits(data, IMC_CR_TC_ODT, 24, 31)
        IMC_CR_TC_PRE = 0         # Timing constraints to PRE commands
        tm["tRP"] = get_bits(data, IMC_CR_TC_PRE, 0, 7)
        tm["tRPab_ext"] = get_bits(data, IMC_CR_TC_PRE, 8, 12)
        tm["tRDPRE"] = get_bits(data, IMC_CR_TC_PRE, 13, 19)
        tm["tRTP"] = tm["tRDPRE"]
        tm["tPPD"] = get_bits(data, IMC_CR_TC_PRE, 20, 23)
        tm["tWRPRE"] = get_bits(data, IMC_CR_TC_PRE, 32, 41)
        tm["tRAS"] = get_bits(data, IMC_CR_TC_PRE, 42, 50)
        tm["tRCD"] = get_bits(data, IMC_CR_TC_PRE, 51, 58)
        tm["DERATING_EXT"] = get_bits(data, IMC_CR_TC_PRE, 59, 62)
        IMC_REFRESH_TC = 0x43C     # Refresh timing parameters
        tm["tREFI"] = get_bits(data, IMC_REFRESH_TC, 0, 17)
        tm["tRFC"]  = get_bits(data, IMC_REFRESH_TC, 18, 30)
        IMC_REFRESH_AUX = 0x438
        tm["oref_ri"]  = get_bits(data, IMC_REFRESH_AUX, 0, 7)
        tm["REFRESH_HP_WM"]  = get_bits(data, IMC_REFRESH_AUX, 8, 11)
        tm["REFRESH_PANIC_WM"]  = get_bits(data, IMC_REFRESH_AUX, 12, 15)
        tm["COUNTTREFIWHILEREFENOFF"]  = get_bits(data, IMC_REFRESH_AUX, 16, 16)
        tm["HPREFONMRS"]  = get_bits(data, IMC_REFRESH_AUX, 17, 17)
        tm["SRX_REF_DEBITS"]  = get_bits(data, IMC_REFRESH_AUX, 18, 19)
        tm["RAISE_BLK_WAIT"]  = get_bits(data, IMC_REFRESH_AUX, 20, 23)
        tm["tREFIx9"]  = get_bits(data, IMC_REFRESH_AUX, 24, 31)   # Should be programmed to 8 * tREFI / 1024 (to allow for possible delays from ZQ or ISOC).
        IMC_REFRESH_EXT = 0x488
        tm["PBR_DISABLE"]  = get_bits(data, IMC_REFRESH_EXT, 0, 0)
        tm["PBR_OOO_DIS"]  = get_bits(data, IMC_REFRESH_EXT, 1, 1)
        tm["PBR_DISABLE_ON_HOT"]  = get_bits(data, IMC_REFRESH_EXT, 3, 3)
        tm["PBR_EXIT_ON_IDLE_CNT"]  = get_bits(data, IMC_REFRESH_EXT, 4, 9)
        tm["tRFCpb"]   = get_bits(data, IMC_REFRESH_EXT, 10, 20)
        tm["tRFM"]     = get_bits(data, 0x40C, 0, 10)    # Default is same as tRFCpb
        IMC_CR_TC_ACT = 0x008     # Timing constraints to ACT commands
        tm["tFAW"]     = get_bits(data, IMC_CR_TC_ACT, 0, 8)
        tm["tRRD_sg"]  = get_bits(data, IMC_CR_TC_ACT, 9, 14)
        tm["tRRD_L"] = tm["tRRD_sg"]
        tm["tRRD_dg"]  = get_bits(data, IMC_CR_TC_ACT, 15, 21)
        tm["tRRD_S"] = tm["tRRD_dg"]
        tm["tREFSBRD"] = get_bits(data, IMC_CR_TC_ACT, 24, 31)
        IMC_TC_PWDEN = 0x050     # Power Down Timing
        tm["tCKE"] = get_bits(data, IMC_TC_PWDEN, 0, 6)
        tm["tXP"] = get_bits(data, IMC_TC_PWDEN, 7, 13)
        tm["tXPDLL"] = get_bits(data, IMC_TC_PWDEN, 14, 20)
        tm["tRDPDEN"] = get_bits(data, IMC_TC_PWDEN, 21, 28)
        tm["tWRPDEN"] = get_bits(data, IMC_TC_PWDEN, 32, 41)
        tm["tCSH"] = get_bits(data, IMC_TC_PWDEN, 42, 47)
        tm["tCSL"] = get_bits(data, IMC_TC_PWDEN, 48, 53)
        tm["tPRPDEN"] = get_bits(data, IMC_TC_PWDEN, 59, 63)
        IMC_SC_GS_CFG = 0x088   # Scheduler configuration
        tm["CMD_STRETCH"] = get_bits(data, IMC_SC_GS_CFG, 3, 4)
        CR_map = { 0: "1N", 1: '2N', 2: '3N', 3: "N:1" }
        tm["tCR"] = CR_map[tm["CMD_STRETCH"]]
        tm["N_TO_1_RATIO"] = get_bits(data, IMC_SC_GS_CFG, 5, 7)
        tm["ADDRESS_MIRROR"] = get_bits(data, IMC_SC_GS_CFG, 8, 11)
        tm["GEAR4"] = get_bits(data, IMC_SC_GS_CFG, 15, 15)
        tm["NO_GEAR4_PARAM_DIVIDE"] = get_bits(data, IMC_SC_GS_CFG, 16, 16)
        tm["X8_DEVICE"] = get_bits(data, IMC_SC_GS_CFG, 28, 29)
        tm["NO_GEAR2_PARAM_DIVIDE"] = get_bits(data, IMC_SC_GS_CFG, 30, 30)
        tm["GEAR2"] = get_bits(data, IMC_SC_GS_CFG, 31, 31)
        tm["DDR_1DPC_SPLIT_RANKS_ON_SUBCH"] = get_bits(data, IMC_SC_GS_CFG, 32, 33)
        tm["WRITE0_ENABLE"] = get_bits(data, IMC_SC_GS_CFG, 49, 49)
        tm["WCKDIFFLOWINIDLE"] = get_bits(data, IMC_SC_GS_CFG, 54, 54)
        tm["tCPDED"] = get_bits(data, IMC_SC_GS_CFG, 56, 60)
        
        tm["ALLOW_2CYC_B2B_LPDDR"] = get_bits(data, 0x00C, 7, 7)
        tm["tRDRD_sg"] = get_bits(data, 0x00C, 0, 6)
        tm["tRDRD_dg"] = get_bits(data, 0x00C, 8, 14)
        tm["tRDRD_dr"] = get_bits(data, 0x00C, 16, 23)
        tm["tRDRD_dd"] = get_bits(data, 0x00C, 24, 31)
        
        tm["tRDWR_sg"] = get_bits(data, 0x010, 0, 7)
        tm["tRDWR_dg"] = get_bits(data, 0x010, 8, 15)
        tm["tRDWR_dr"] = get_bits(data, 0x010, 16, 23)
        tm["tRDWR_dd"] = get_bits(data, 0x010, 24, 31)
        
        tm["tWRRD_sg"] = get_bits(data, 0x014, 0, 8)
        tm["tWRRD_dg"] = get_bits(data, 0x014, 9, 17)
        tm["tWRRD_dr"] = get_bits(data, 0x014, 18, 24)
        tm["tWRRD_dd"] = get_bits(data, 0x014, 25, 31)

        tm["tWRWR_sg"] = get_bits(data, 0x018, 0, 6)
        tm["tWRWR_dg"] = get_bits(data, 0x018, 8, 14)
        tm["tWRWR_dr"] = get_bits(data, 0x018, 16, 22)
        tm["tWRWR_dd"] = get_bits(data, 0x018, 24, 31)

        tm["tXSDLL"] = get_bits(data, 0x440, 0, 12)
        tm["tZQOPER"] = get_bits(data, 0x440, 16, 23)   # UNDOC
        tm["tMOD"] = get_bits(data, 0x440, 24, 31)   # UNDOC
        
        tm["DEC_tCWL"] = get_bits(data, 0x478, 0, 5)   # The number of cycles (DCLK) decreased from tCWL.
        tm["ADD_tCWL"] = get_bits(data, 0x478, 6, 11)  # The number of cycles (DCLK) increased to tCWL.
        tm["ADD_1QCLK_DELAY"] = get_bits(data, 0x478, 12, 12)  # In Gear2, MC QCLK is actually 1xClk of the DDR, the regular MC register can only set even number of cycles (working in Dclk == 2 * 1xClk)
        xCWL = tm['tCWL']
        xCWL -= tm['DEC_tCWL']  # UNDOC
        xCWL += tm['ADD_tCWL']  # UNDOC
        tm["tWTR_L"] = tm['tWRRD_sg'] - xCWL - 10
        tm["tWTR_S"] = tm['tWRRD_dg'] - xCWL - 10
        #tm["tWTR_L"] = tm['tWRRD_sg'] - tm['tCWL'] - 10  # if ASRock then -6
        #tm["tWTR_S"] = tm['tWRRD_dg'] - tm['tCWL'] - 10  # if ASRock then -6 

        tm["tXSR"] = get_bits(data, 0x4C0, 0, 12)
        tm["tSR"] = get_bits(data, 0x4C0, 52, 57)

        if info["DDR_TYPE"] in [ 0, 3 ]:
            tWR_quantity = 4  # DDR4 and LPDDR4
        else:
            tWR_quantity = 8  # DDR5 and LPDDR5

        #if tm['tWRPRE'] > tm['tCWL'] + tWR_quantity:
        tm['tWR'] = tm['tWRPRE'] - tm['tCWL'] - tWR_quantity

        if tm['GEAR4']:
            tm['GEAR'] = 4
        elif tm['GEAR2']:
            tm['GEAR'] = 2
        else:
            tm['GEAR'] = 1

        tm["tRTL_0"] = get_bits(data, 0x020, 0, 7)
        tm["tRTL_1"] = get_bits(data, 0x020, 8, 15)
        tm["tRTL_2"] = get_bits(data, 0x020, 16, 23)
        tm["tRTL_3"] = get_bits(data, 0x020, 24, 31)
        
        tm["Banks"] = 8 if get_bits(data, IMC_SC_GS_CFG, 0, 2) else 16  # UNDOC
        #tm["Columns"] = 1 << 10
        
    else:
        raise RuntimeError(f'ERROR: Processor model 0x{proc_model_id:X} not supported')
    return tm

def get_mem_ctrl(ctrl_num):
    global gdict, proc_fam, proc_model_id, MCHBAR_BASE
   
    mi = { }
    mi['controller'] = ctrl_num
   
    MC_REGS_SIZE = None
    MCHBAR_addr = MCHBAR_BASE + (0x10000 * ctrl_num)
    if proc_model_id in ADL_FAM:
        MC_REGS_SIZE = 0x800
        data_offset = 0xD800  # Inter-Channel Decode Parameters
        MADCH = phymem_read(MCHBAR_addr + data_offset, 4)
        mi["DDR_TYPE"]     = get_bits(MADCH, 0, 0, 2)
        mi["CH_L_MAP"]     = get_bits(MADCH, 0, 4, 4)  # Channel L mapping to physical channel.  0 = Channel 0  1 = Channel 1
        mi["CH_S_SIZE"]    = get_bits(MADCH, 0, 12, 19)
        mi["CH_WIDTH"]     = get_bits(MADCH, 0, 27, 28)
        mi["HALFCACHELINEMODE"] = get_bits(MADCH, 0, 31, 31)   # HALF_CL_MODE
        if mi["DDR_TYPE"] in [ 0, 3 ]:
            mi["DDR_ver"] = 4  # DDR4 and LPDDR4
        else:
            mi["DDR_ver"] = 5  # DDR5 and LPDDR5
    else:
        raise RuntimeError(f'ERROR: Processor model 0x{proc_model_id:X} not supported')
    #print(json.dumps(mi, indent = 4))
    mchan = [ ]
    # 0xD804 - Intra-Channel 0 Decode Parameters
    # 0xD808 - Intra-Channel 1 Decode Parameters
    # 0xD80C - Channel 0 DIMM Characteristics
    # 0xD810 - Channel 1 DIMM Characteristics
    for cnum in range(0, 2):
        mc = { }
        mc["__channel"] = cnum
        data = phymem_read(MCHBAR_addr + 0xD804 + cnum * 4, 4)
        if data == b'\xFF\xFF\xFF\xFF':
            raise RuntimeError()
        mc["DIMM_L_MAP"] = get_bits(data, 0, 0, 0)  # Virtual DIMM L mapping to physical DIMM: 0 = DIMM0, 1 = DIMM1
        mc["EIM"] = get_bits(data, 0, 8, 8)
        mc["ECC"] = get_bits(data, 0, 12, 13)
        mc["CRC"] = get_bits(data, 0, 14, 14)   # CRC Mode: 0 = Disabled  1 = Enabled
        data = phymem_read(MCHBAR_addr + 0xD80C + cnum * 4, 4)
        if data == b'\xFF\xFF\xFF\xFF':
            raise RuntimeError()
        mc["Dimm_L_Size"] = get_bits(data, 0, 0, 6)   # DIMM L Size in 512 MB multiples
        mc["DLW"]         = get_bits(data, 0, 7, 8)   # DIMM L width: 0=x8, 1=x16, 2=x32 
        mc["DLNOR"]       = get_bits(data, 0, 9, 10)  # DIMM L ranks: 0=1, 1=2, 2=3, 3=4
        mc["DDR5_DS_8GB"] = get_bits(data, 0, 11, 11) # DIMM S: 1 = 8Gb , 0 = more than 8Gb capacity
        mc["DDR5_DL_8GB"] = get_bits(data, 0, 12, 12) # DIMM L: 0 = DDR5 capacity is more than 8Gb, 1 = DDR5 capacity is 8Gb
        mc["Dimm_S_Size"] = get_bits(data, 0, 16, 22)
        mc["DSW"]         = get_bits(data, 0, 24, 25) # DIMM S width: 0=x8, 1=x16, 2=x32
        mc["DSNOR"]       = get_bits(data, 0, 26, 27) # DIMM S ranks: 0=1, 1=2, 2=3, 3=4
        mc["BG0_BIT_OPTIONS"] = get_bits(data, 0, 28, 29)
        mc["DECODER_EBH"] = get_bits(data, 0, 30, 31)
        mchan.append( mc )
    #if mi["CH_L_MAP"]:
    #    mchan.reverse()
    mi['channels'] = mchan
    for channel in range(0, 2):    
        mchan[channel]['info'] = get_mchbar_info(mi, ctrl_num, channel)
    return mi

def get_mem_info():
    global gdict, proc_fam, proc_model_id, MCHBAR_BASE, DMIBAR_BASE
    proc_name = GetProcessorSpecification()
    print('Processor:', proc_name)
    proc_fam = GetProcessorFamily()
    print('Processor Family: 0x%X' % proc_fam)
    proc_model_id = GetProcessorExtendedModel() 
    print('Processor Model ID: 0x%X' % proc_model_id)    
    if proc_fam != 6:
        raise RuntimeError(f'ERROR: Currently support only Intel processors')

    if proc_model_id < INTEL_ALDERLAKE:
        raise RuntimeError(f'ERROR: Processor model 0x{proc_model_id:X} not supported')

    MCHBAR_BASE = pci_cfg_read(0, 0, 0, 0x48, '8')
    if (MCHBAR_BASE & 1) != 1:
        raise RuntimeError(f'ERROR: Readed incorrect MCHBAR_BASE = 0x{MCHBAR_BASE:X}')
    if MCHBAR_BASE < 0xFE000000:
        raise RuntimeError(f'ERROR: Readed incorrect MCHBAR_BASE = 0x{MCHBAR_BASE:X}')
    MCHBAR_BASE = MCHBAR_BASE - 1
    print(f'MCHBAR_BASE = 0x{MCHBAR_BASE:X}')

    DMIBAR_BASE = pci_cfg_read(0, 0, 0, 0x68, '8')
    if (DMIBAR_BASE & 1) != 1:
        raise RuntimeError(f'ERROR: Readed incorrect DMIBAR_BASE = 0x{DMIBAR_BASE:X}')
    if DMIBAR_BASE < 0xFE000000:
        raise RuntimeError(f'ERROR: Readed incorrect DMIBAR_BASE = 0x{DMIBAR_BASE:X}')
    DMIBAR_BASE = DMIBAR_BASE - 1
    print(f'DMIBAR_BASE = 0x{DMIBAR_BASE:X}')

    DMI_DeviceId = phymem_read(DMIBAR_BASE, 4)
    DMI_VID = get_bits(DMI_DeviceId, 0, 0, 15)
    DMI_DID = get_bits(DMI_DeviceId, 0, 16, 31)
    print(f'DMI_VID = 0x{DMI_VID:X}  DMI_DID = 0x{DMI_DID:X}')
    if DMI_VID != PCI_VENDOR_ID_INTEL:
        raise RuntimeError(f'ERROR: Currently support only Intel processors')

    #mchbar_mmio = MCHBAR_BASE + 0x6000

    gdict = { }
    cpu = gdict['cpu'] = { }
    board = gdict['board'] = { }
    cpu['family'] = proc_fam
    cpu['model_id'] = proc_model_id
    cpu['name'] = proc_name
    
    gdict['CAP'] = { }
    cap = gdict['CAP']

    CAP_A = pci_cfg_read(0, 0, 0, 0xE4, 4)  # Capabilities A. Processor capability enumeration.
    cap['NVME_F7D'] = get_bits(CAP_A, 0, 1, 1)
    cap['DDR_OVERCLOCK'] = get_bits(CAP_A, 0, 3, 3)
    cap['CRID'] = get_bits(CAP_A, 0, 4, 7)
    cap['2LM_SUPPORTED'] = get_bits(CAP_A, 0, 8, 8)
    cap['DID0OE'] = get_bits(CAP_A, 0, 10, 10)
    cap['IntGpu'] = True if get_bits(CAP_A, 0, 11, 11) == 0 else False     # IGD: Internal Graphics Status
    cap['DualMemChan'] = True if get_bits(CAP_A, 0, 12, 12) == 0 else False  # PDCD: Dual Memory Channel Support
    cap['X2APIC_EN'] = get_bits(CAP_A, 0, 13, 13)
    cap['TwoDimmPerChan'] = True if get_bits(CAP_A, 0, 14, 14) == 0 else False   # DDPCD: 2 DIMMs Per Channel Status
    cap['DTT_dev'] = True if get_bits(CAP_A, 0, 15, 15) == 0 else False     # CDD: DTT Device Status
    cap['D1NM'] = True if get_bits(CAP_A, 0, 17, 17) == 0 else False       # DRAM 1N Timing Status
    cap['PEG60'] = True if get_bits(CAP_A, 0, 18, 18) == 0 else False      # PEG60D: PCIe Controller Device 6 Function 0 Status
    cap['DDRSZ'] = get_bits(CAP_A, 0, 19, 20)  # DRAM Maximum Size per Channel
    DRAM_SIZE_map = { 0: None, 1: '8GB', 2: '4GB', 3: '2GB' }
    cap['DDRSZ_max'] = DRAM_SIZE_map[cap['DDRSZ']]
    cap['DMIG2'] = True if get_bits(CAP_A, 0, 22, 22) == 0 else False  # DMIG2DIS: DMI GEN2 Status
    cap['VTD'] = True if get_bits(CAP_A, 0, 23, 23) == 0 else False  # VTDD:  VT-d status
    cap['FDEE'] = get_bits(CAP_A, 0, 24, 24)  # Force DRAM ECC Enable
    cap['ECC'] = True if get_bits(CAP_A, 0, 25, 25) == 0 else False  # ECCDIS : DRAM ECC status
    cap['DW'] = 'x4' if get_bits(CAP_A, 0, 26, 26) == 0 else 'x2'   # DMI Width
    cap['PELWU'] = True if get_bits(CAP_A, 0, 27, 27) == 0 else False  # PELWUD : PCIe Link Width Up-config
    CAP_B = pci_cfg_read(0, 0, 0, 0xE8, 4)  # Capabilities B. Processor capability enumeration.
    cap['SPEGFX1'] = get_bits(CAP_B, 0, 0)    
    cap['DPEGFX1'] = get_bits(CAP_B, 0, 1)    
    cap['VMD'] = True if get_bits(CAP_B, 0, 2) == 0 else False    # VMD_DIS
    cap['SH_OPI_EN'] = get_bits(CAP_B, 0, 3)    
    cap['Debug'] = True if get_bits(CAP_B, 0, 7) == 0 else False   # Debug mode status
    cap['GNA'] = True if get_bits(CAP_B, 0, 8) == 0 else False     # GNA_DIS
    cap['DEV10'] = True if get_bits(CAP_B, 0, 10) == 0 else False    # DEV10_DISABLED
    cap['HDCP'] = True if get_bits(CAP_B, 0, 11) == 0 else False     # HDCPD
    cap['LTECH'] = get_bits(CAP_B, 0, 12, 14)    
    cap['DMIG3'] = True if get_bits(CAP_B, 0, 15) == 0 else False   # DMIG3DIS 
    cap['PEGX16'] = True if get_bits(CAP_B, 0, 16) == 0 else False    # PEGX16D
    cap['PKGTYP'] = get_bits(CAP_B, 0, 19)    
    cap['PEGG3'] = True if get_bits(CAP_B, 0, 20) == 0 else False    # PEGG3_DIS
    cap['PLL_REF100_CFG'] = get_bits(CAP_B, 0, 21, 23)  # DDR Maximum Frequency Capability with 100MHz memory reference clock (ref_clk). 0: 100 MHz memory reference clock is not supported / 1-6: Reserved / 7: Unlimited
    cap['SVM'] = True if get_bits(CAP_B, 0, 24) == 0 else False  # SVM_DISABLE  
    cap['CACHESZ'] = get_bits(CAP_B, 0, 25, 27)    
    cap['SMT'] = get_bits(CAP_B, 0, 28)    
    cap['OC_ENABLED'] = get_bits(CAP_B, 0, 29)   # Overclocking Enabled 
    cap['TRACE_HUB'] = True if get_bits(CAP_B, 0, 30) == 0 else False   # TRACE_HUB_DIS 
    cap['IPU'] = True if get_bits(CAP_B, 0, 31) == 0 else False   # IPU_DIS  
    CAP_C = pci_cfg_read(0, 0, 0, 0xEC, 4)  # Capabilities C. Processor capability enumeration.
    cap['DISPLAY_PIPE3'] = get_bits(CAP_C, 0, 5)
    cap['IDD'] = get_bits(CAP_C, 0, 6)
    cap['BCLKOCRANGE'] = get_bits(CAP_C, 0, 7, 8)  # BCLK Overclocking maximum frequency
    BCLK_OC_map = { 0: 'disabled', 1: 'max=115MHz', 2: 'max=130MHz', 3: 'unlimited' }
    cap['BCLKOC_freq_limit'] = BCLK_OC_map[cap['BCLKOCRANGE']]
    cap['QCLK_GV'] = True if get_bits(CAP_C, 0, 14) == 0 else False   # QCLK_GV_DIS
    cap['LPDDR4_EN'] = get_bits(CAP_C, 0, 16)
    cap['MAX_DATA_RATE_LPDDR4'] = get_bits(CAP_C, 0, 17, 21)
    cap['DDR4_EN'] = get_bits(CAP_C, 0, 22)
    cap['MAX_DATA_RATE_DDR4'] = get_bits(CAP_C, 0, 23, 27)
    cap['PEGG4'] = True if get_bits(CAP_C, 0, 28) == 0 else False   # PEGG4_DIS
    cap['PEGG5'] = True if get_bits(CAP_C, 0, 29) == 0 else False   # PEGG5_DIS
    cap['PEG61'] = True if get_bits(CAP_C, 0, 30) == 0 else False   # PEG61D
    CAP_E = pci_cfg_read(0, 0, 0, 0xF0, 4)  # Capabilities E. Processor capability enumeration.
    cap['LPDDR5_EN'] = get_bits(CAP_E, 0, 0)
    cap['MAX_DATA_RATE_LPDDR5'] = get_bits(CAP_E, 0, 1, 5)
    cap['MAX_DATA_FREQ_LPDDR5'] = cap['MAX_DATA_RATE_LPDDR5'] * 266
    cap['DDR5_EN'] = get_bits(CAP_E, 0, 6)
    cap['MAX_DATA_RATE_DDR5'] = get_bits(CAP_E, 0, 7, 11)
    cap['MAX_DATA_FREQ_DDR5'] = cap['MAX_DATA_RATE_DDR5'] * 266
    cap['IBECC'] = True if get_bits(CAP_E, 0, 12) == 0 else False  # IBECC_DIS
    #cap['VDDQ_VOLTAGE_MAX'] = get_bits(CAP_E, 0, 13, 23)  # VDDQ_TX Maximum VID value
    cap['VDDQ_VOLTAGE_MAX'] = round(get_bits(CAP_E, 0, 13, 23) * 5 / 1000, 3)  # VDDQ_TX Maximum VID value (granularity UNDOC !!!)

    gdict['memory'] = { }
    mi = gdict['memory']

    data = phymem_read(MCHBAR_BASE + 0x5F58, 8)
    mi['MC_TIMING_RUNTIME_OC_ENABLED'] = get_bits(data, 0, 0, 0)  # Adjusting memory timing values for overclocking is enabled
    data = phymem_read(MCHBAR_BASE + 0x5F60, 8)
    BCLK_FREQ = get_bits(data, 0, 0, 31) / 1000.0  # Reported BCLK Frequency in KHz
    mi['BCLK_FREQ'] = round(BCLK_FREQ, 3)

    pw = mi['POWER'] = { }
    data = phymem_read(MCHBAR_BASE + 0x58E0, 8)   # DDR Power Limit
    pw['LIMIT1_POWER'] = get_bits(data, 0, 0, 14) / 100 # Power Limit 1 (PL1) for DDR domain in Watts. Format is U11.3: Resolution 0.125W, Range 0-2047.875W
    pw['LIMIT1_ENABLE'] = get_bits(data, 0, 15, 15)  # Power Limit 1 (PL1) enable bit for DDR domain
    pw['LIMIT1_TIME_WINDOW_Y'] = get_bits(data, 0, 17, 21)  # Power Limit 1 (PL1) time window Y value, for DDR domain. Actual time window for RAPL is: (1/1024 seconds) * (1+(X/4)) * (2Y)
    pw['LIMIT1_TIME_WINDOW_X'] = get_bits(data, 0, 22, 23)  # Power Limit 1 (PL1) time window X value, for DDR domain. Actual time window for RAPL is: (1/1024 seconds) * (1+(X/4)) * (2Y) 
    pw['LIMIT2_POWER'] = get_bits(data, 0, 32, 46) / 100 # Power Limit 2 (PL2) for DDR domain in Watts. Format is U11.3: Resolution 0.125W, Range 0-2047.875W.
    pw['LIMIT2_ENABLE'] = get_bits(data, 0, 47, 47)  # Power Limit 2 (PL2) enable bit for DDR domain.
    pw['limits_LOCKED'] = get_bits(data, 0, 63, 63)  # When set, this entire register becomes read-only. This bit will typically be set by BIOS during boot.
    data = phymem_read(MCHBAR_BASE + 0x58F0, 4)   # Package RAPL Performance Status
    pw['RAPL_COUNTS'] = get_bits(data, 0, 0, 31)
    data = phymem_read(MCHBAR_BASE + 0x5920, 4)   # Primary Plane Turbo Policy
    pw['PRIPTP'] = get_bits(data, 0, 0, 4)  # Priority Level. A higher number implies a higher priority.
    data = phymem_read(MCHBAR_BASE + 0x5924, 4)   # Secondary Plane Turbo Policy
    pw['SECPTP'] = get_bits(data, 0, 0, 4)  # Priority Level. A higher number implies a higher priority.
    data = phymem_read(MCHBAR_BASE + 0x5928, 4)   # Primary Plane Energy Status
    pw['PRI_DATA'] = get_bits(data, 0, 0, 31)  # Energy Value. The value of this register is updated every 1mSec.
    data = phymem_read(MCHBAR_BASE + 0x592C, 4)   # Primary Plane Energy Status
    pw['SEC_DATA'] = get_bits(data, 0, 0, 31)  # Energy Value. The value of this register is updated every 1mSec.
    data = phymem_read(MCHBAR_BASE + 0x5938, 4)   # Package Power SKU Unit
    pw['PWR_UNIT'] = get_bits(data, 0, 0, 3)  # Power Units used for power control registers. The actual unit value is calculated by 1 W / Power(2, PWR_UNIT). The default value of 0011b corresponds to 1/8 W.
    pw['ENERGY_UNIT'] = get_bits(data, 0, 8, 12)
    pw['TIME_UNIT'] = get_bits(data, 0, 16, 19)
    data = phymem_read(MCHBAR_BASE + 0x593C, 4)   # Package Energy Status
    pw['PKG_ENG_STATUS'] = get_bits(data, 0, 0, 31)  # Package energy consumed by the entire CPU (including IA, GT and uncore). The counter will wrap around and continue counting when it reaches its limit.

    sa = mi['SA'] = { }
    data = phymem_read(MCHBAR_BASE + 0x5918, 8)   # System Agent Performance Status
    sa['LAST_DE_WP_REQ_SERVED'] = get_bits(data, 0, 0, 1)   # Last display engine workpoint request served by the PCU
    sa['QCLK_REFERENCE'] = get_bits(data, 0, 10, 10)  # 0 = 133.34Mhz  1 = 100 MHz
    sa['QCLK_RATIO'] = get_bits(data, 0, 2, 9)  # Reference clock is determined by the QCLK_REFERENCE field.
    sa['QCLK'] = round(sa['QCLK_RATIO'] * mi['BCLK_FREQ'], 3)
    if sa['QCLK_REFERENCE'] == 0:
        sa['QCLK'] = round(sa['QCLK'] * 1.33, 3)
    sa['OPI_LINK_SPEED'] = get_bits(data, 0, 11, 11)  # 0: 2Gb/s    1: 4Gb/s
    sa['IPU_IS_DIVISOR'] = get_bits(data, 0, 12, 17)  # The frequency is 1600MHz/Divisor 
    sa['IPU_IS_freq'] = 1600 / sa['IPU_IS_DIVISOR'] if sa['IPU_IS_DIVISOR'] > 0 else None
    sa['IPU_PS_RATIO'] = get_bits(data, 0, 18, 23)  # IPU PS RATIO. The frequency is 25MHz * Ratio.
    sa['IPU_PS_freq'] = 25.0 * sa['IPU_PS_RATIO']
    sa['UCLK_RATIO'] = get_bits(data, 0, 24, 31)  # Used to calculate the ring's frequency. Ring Frequency = UCLK_RATIO * BCLK
    sa['UCLK'] = round(sa['UCLK_RATIO'] * mi['BCLK_FREQ'], 3)
    sa['PSF0_RATIO'] = get_bits(data, 0, 32, 39)  # Reports the PSF0 PLL ratio. The PSF0 frequency is: Ratio * 16.67MHz.
    sa['PSF0_freq'] = round(16.67 * sa['PSF0_RATIO'], 3)
    sa['SA_VOLTAGE'] = get_bits(data, 0, 40, 55)  # Reports the System Agent voltage in u3.13 format. Conversion to Volts: V = SA_VOLTAGE / 8192.0
    sa['SA_VOLTAGE'] = round(sa['SA_VOLTAGE'] / 8192, 3)

    bios = mi['BIOS_REQUEST'] = { }
    data = phymem_read(MCHBAR_BASE + 0x5E00, 4)   # Memory Controller BIOS Request
    MC_PLL_RATIO = get_bits(data, 0, 0, 7) # This field holds the memory controller frequency (QCLK).
    bios['MC_PLL_REF'] = get_bits(data, 0, 8, 11)
    bios['MC_PLL_RATIO'] = MC_PLL_RATIO
    bios['MC_PLL_freq'] = MC_PLL_RATIO * 100.0 if bios['MC_PLL_REF'] == 1 else round(MC_PLL_RATIO * 133.33, 3)
    bios['GEAR'] = 1 << get_bits(data, 0, 12, 13)
    bios['REQ_VDDQ_TX_VOLTAGE'] = round(get_bits(data, 0, 17, 26) * 5 / 1000, 3) # Voltage of the VDDQ TX rail at this clock frequency and gear configuration. Described in 5mV resolution
    bios['REQ_VDDQ_TX_ICCMAX'] = round(get_bits(data, 0, 27, 30) * 0.25, 3)  # Described in 0.25A resolution. IccMax: 32 * 0.25 = 8A
    bios['RUN_BUSY'] = get_bits(data, 0, 31, 31)

    #bios = mi['BIOS_DATA'] = { }
    bios = mi
    data = phymem_read(MCHBAR_BASE + 0x5E04, 4)   # Memory Controller BIOS Data
    MC_PLL_RATIO = get_bits(data, 0, 0, 7) # This field holds the memory controller frequency (QCLK).
    bios['MC_PLL_REF'] = get_bits(data, 0, 8, 11)
    bios['MC_PLL_RATIO'] = MC_PLL_RATIO
    bios['MC_PLL_freq'] = MC_PLL_RATIO * 100.0 if bios['MC_PLL_REF'] == 1 else round(MC_PLL_RATIO * 133.33, 3)
    bios['GEAR'] = 1 << get_bits(data, 0, 12, 13)
    bios['REQ_VDDQ_TX_VOLTAGE'] = round(get_bits(data, 0, 17, 26) * 5 / 1000, 3) # Voltage of the VDDQ TX rail at this clock frequency and gear configuration. Described in 5mV resolution
    bios['REQ_VDDQ_TX_ICCMAX'] = round(get_bits(data, 0, 27, 30) * 0.25, 3)  # Described in 0.25A resolution. IccMax: 32 * 0.25 = 8A

    data = phymem_read(MCHBAR_BASE + 0x5F00, 4)   # System Agent Power Management Control
    mi['SACG_ENA'] = get_bits(data, 0, 0, 0)  # This bit is used to enable or disable the System Agent Clock Gating (FCLK) : 0 = Not Allow , 1 = Allow
    mi['MPLL_OFF_ENA'] = get_bits(data, 0, 1, 1)  # This bit is used to enable shutting down the Memory Controller PLLs (MCPLL and GDPLL).   0b: PLL shutdown is not allowed   1b: PLL shutdown is allowed
    mi['PPLL_OFF_ENA'] = get_bits(data, 0, 2, 2)  # This bit is used to enable shutting down the PCIe/DMI PLL
    mi['SACG_SEN'] = get_bits(data, 0, 8, 8)  # This bit indicates when the System Agent clock gating is possible based on link active power states.
    mi['MPLL_OFF_SEN'] = get_bits(data, 0, 9, 9) # This bit indicates when the Memory PLLs (MCPLL and GDPLL) may be shutdown based on link active power states.
    mi['MDLL_OFF_SEN'] = get_bits(data, 0, 10, 10) # This bit indicates when the Memory Master DLL may be shutdown based on link active power states.
    mi['SACG_SREXIT'] = get_bits(data, 0, 11, 11)  # The Display Engine can indicate to the PCU that it wants the Memory Controller to exit self-refresh
    mi['NSWAKE_SREXIT'] = get_bits(data, 0, 12, 12)  # When this bit is set to 1b, a Non-Snoop wakeup signal from the PCH will cause the PCU to force the memory controller to exit from Self-Refresh
    mi['SACG_MPLL'] = get_bits(data, 0, 13, 13)  # When this bit is set to 1b, FCLK will never be gated when the memory controller PLL is ON.
    mi['MPLL_ON_DE'] = get_bits(data, 0, 14, 14)
    mi['MDLL_ON_DE'] = get_bits(data, 0, 15, 15)
    
    # BCLKOCRANGE

    if True:
        mb = get_motherboard_info()
        board['manufacturer'] = mb['manufacturer']
        board['product'] = mb['product']

    mc = gdict['memory']['mc'] = [ ]
    for ctrl_num in range(0, 2):
        mem = get_mem_ctrl(ctrl_num)
        mc.append( mem )
    return gdict

if __name__ == "__main__":
    SdkInit(None, 0)
    out = get_mem_info()
    #print(json.dumps(memory, indent = 4))
    with open('IMC.json', 'w') as file:
        json.dump(out, file, indent = 4)
    
