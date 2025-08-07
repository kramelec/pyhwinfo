#
# Copyright (C) 2025 remittor
#

import ctypes
from ctypes.wintypes import *
from ctypes import CFUNCTYPE

from .win32 import *

#####################################/
#   Error codes
#####################################/

CPUIDSDK_ERROR_NO_ERROR            = 0x00000000

CPUIDSDK_ERROR_EVALUATION          = 0x00000001
CPUIDSDK_ERROR_DRIVER              = 0x00000002
CPUIDSDK_ERROR_VM_RUNNING          = 0x00000004
CPUIDSDK_ERROR_LOCKED              = 0x00000008
CPUIDSDK_ERROR_INVALID_DLL         = 0x00000010

CPUIDSDK_EXT_ERROR_EVAL_1          = 0x00000001
CPUIDSDK_EXT_ERROR_EVAL_2          = 0x00000002

#####################################/
#   Configuration flags
#####################################/

CPUIDSDK_CONFIG_USE_SOFTWARE       = 0x00000002
CPUIDSDK_CONFIG_USE_DMI            = 0x00000004
CPUIDSDK_CONFIG_USE_PCI            = 0x00000008
CPUIDSDK_CONFIG_USE_ACPI           = 0x00000010
CPUIDSDK_CONFIG_USE_CHIPSET        = 0x00000020
CPUIDSDK_CONFIG_USE_SMBUS          = 0x00000040
CPUIDSDK_CONFIG_USE_SPD            = 0x00000080
CPUIDSDK_CONFIG_USE_STORAGE        = 0x00000100
CPUIDSDK_CONFIG_USE_GRAPHICS       = 0x00000200
CPUIDSDK_CONFIG_USE_HWMONITORING   = 0x00000400
CPUIDSDK_CONFIG_USE_PROCESSOR      = 0x00000800
CPUIDSDK_CONFIG_USE_DISPLAY_API    = 0x00001000

CPUIDSDK_CONFIG_USE_ACPI_TIMER     = 0x00004000

CPUIDSDK_CONFIG_CHECK_VM           = 0x01000000
CPUIDSDK_CONFIG_WAKEUP_HDD         = 0x02000000

CPUIDSDK_CONFIG_SERVER_SAFE        = 0x80000000

CPUIDSDK_CONFIG_USE_EVERYTHING     = 0x7FFFFFFF

#####################################/
#   Function table
#####################################/

_sdk_func_table = [ ]

def _afunc(name):
    func = { 'name': name, 'fid': None, 'addr': None, 'func': None }
    _sdk_func_table.append( func )

def get_sdkfunc(name):
    for func in _sdk_func_table:
        if func['name'] == name:
            return func
    return None

_afunc('CreateInstance')
_afunc('DestroyInstance')
_afunc('SdkInit')
_afunc('SdkClose')
_afunc('RefreshInformation')
_afunc('GetDLLVersion')

_afunc('GetNbProcessors')
_afunc('GetProcessorFamily')
_afunc('GetProcessorExtendedFamily')
_afunc('GetProcessorModel')
_afunc('GetProcessorExtendedModel')
_afunc('GetProcessorSteppingID')
_afunc('proc_C16F82DF')
_afunc('proc_5CFCB9F9')
_afunc('GetProcessorCoreCount')
_afunc('GetProcessorThreadCount')
_afunc('GetProcessorCoreThreadCount')
_afunc('GetProcessorThreadAPICID')
_afunc('GetProcessorName')
_afunc('GetProcessorCodeName')
_afunc('GetProcessorSpecification')
_afunc('GetProcessorPackage')
_afunc('GetProcessorStepping')
_afunc('GetProcessorTDP')
_afunc('proc_EA5DD4BB') # _afunc('GetProcessorManufacturingProcess')
_afunc('proc_D3B9A773')
_afunc('IsProcessorInstructionSetAvailable')
_afunc('proc_71CAE395') # _afunc('GetProcessorStockClockFrequency')
_afunc('proc_09141228') # _afunc('GetProcessorStockBusFrequency')
_afunc('proc_7862F0C5') # _afunc('GetProcessorCoreClockFrequency')
_afunc('proc_D15DA2BB') # _afunc('GetProcessorCoreClockMultiplier')
_afunc('proc_D1FBA3F7') 
_afunc('proc_B85B70B6') # _afunc('GetProcessorCoreTemperature')
_afunc('proc_578EAF1D')
_afunc('GetProcessorMaxCacheLevel')
_afunc('GetProcessorCacheParameters')
_afunc('GetProcessorExtendedCacheParameters')
_afunc('GetHyperThreadingStatus')
_afunc('GetVirtualTechnologyStatus')
_afunc('GetProcessorID')
_afunc('GetProcessorVoltage')
_afunc('GetNorthBridgeVendor')
_afunc('GetNorthBridgeModel')
_afunc('GetNorthBridgeRevision')
_afunc('GetSouthBridgeVendor')
_afunc('GetSouthBridgeModel')
_afunc('GetSouthBridgeRevision')
_afunc('proc_AA???')
_afunc('GetMemoryType')
_afunc('GetMemorySize')
_afunc('GetMemoryNumberOfChannels')
_afunc('GetMemoryClockFrequency')
_afunc('GetMemoryCASLatency')
_afunc('GetMemoryRAStoCASDelay')
_afunc('GetMemoryRASPrecharge')
_afunc('GetMemoryTRAS')
_afunc('GetMemoryTRC')
_afunc('GetMemoryCommandRate')
_afunc('ComputeMemoryFrequency')
_afunc('GetBIOSVendor')

#####################################/
#   DRIVER codes
#####################################/

CPUZ_DEVICE_TYPE = 40000

#CPUZ_READ_PHYSMEMORY   = 2312
#CPUZ_READ_CRX          = 2314
#CPUZ_WRITE_PHYSMEMORY  = 2316

CPUZ_PHYMEM_READ       = 0x950
CPUZ_PHYMEM_PC_READ64  = 0x951  # Base Addr get from PciCfg
CPUZ_PHYMEM_WR_XXX     = 0x953
CPUZ_PHYMEM_MAP        = 0x954
CPUZ_PHYMEM_UNMAP      = 0x955
CPUZ_PHYMEM_PC_WRITE32 = 0x958  # Base Addr get from PciCfg

CPUZ_PORT_READ_1       = 0x920
CPUZ_PORT_READ_2       = 0x921
CPUZ_PORT_READ_4       = 0x922

CPUZ_PORT_WRITE_1      = 0x930
CPUZ_PORT_WRITE_2      = 0x931
CPUZ_PORT_WRITE_4      = 0x932

CPUZ_PCI_CFG_READ      = 0x9C0
CPUZ_PCI_CFG_WRITE     = 0x9C1
CPUZ_PCI_CFG_CMD       = 0x9C2

CPUZ_SMBUS_READ_1      = 0x9A0
CPUZ_SMBUS_READ_X      = 0x9A2
CPUZ_SMBUS_WRITE_1     = 0x9A4
CPUZ_SMBUS_PCALL       = 0x9A7  # I2C_SMBUS_PROC_CALL

CPUZ_MSR_READ          = 0x910
CPUZ_MSR_WRITE         = 0x911
CPUZ_MSR_CMD           = 0x912

CPUZ_MSR_GET_TICKS     = 0x982

