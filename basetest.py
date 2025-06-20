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

def base_test():
    #CreateInstance()
    cfg = CPUIDSDK_CONFIG_USE_SOFTWARE + CPUIDSDK_CONFIG_USE_PROCESSOR
    cfg += CPUIDSDK_CONFIG_USE_CHIPSET
    #cfg += CPUIDSDK_CONFIG_USE_DMI
    #cfg += CPUIDSDK_CONFIG_USE_HWMONITORING
    #cfg += CPUIDSDK_CONFIG_USE_SPD
    cfg += CPUIDSDK_CONFIG_USE_PCI
    #cfg += CPUIDSDK_CONFIG_USE_SMBUS
    drv = SdkInit(cfg)
    ver = GetDLLVersion()
    print(f'DLL version: 0x{ver:X}')
    print('RefreshInformation:', RefreshInformation())
    print('Processors:', GetNbProcessors())
    print('Processor Family: 0x%X' % GetProcessorFamily())
    print('Processor Family Ext: 0x%X' % GetProcessorExtendedFamily())
    print('Processor Model: 0x%X' % GetProcessorModel())
    print('Processor Model Ext: 0x%X' % GetProcessorExtendedModel())
    print('Processor SteppingID: 0x%X' % GetProcessorSteppingID())
    print('Processor Cores: %d' % GetProcessorCoreCount())
    print('Processor Threads: %d' % GetProcessorThreadCount())
    print('Processor Core[0] threads: %d' % GetProcessorCoreThreadCount())
    print('Processor Name:', GetProcessorName())
    print('Processor Code Name:', GetProcessorCodeName())
    print('Processor Package:', GetProcessorPackage())
    print('Processor Specification:', GetProcessorSpecification())
    print('Processor Stepping:', GetProcessorStepping())
    print('Processor TDP:', GetProcessorTDP())
    print('proc_EA5DD4BB:', proc_EA5DD4BB())
    print('proc_D3B9A773:', proc_D3B9A773())
    print('IsProcessorInstructionSetAvailable:', IsProcessorInstructionSetAvailable())
    print('proc_71CAE395:', proc_71CAE395())
    print('proc_09141228:', proc_09141228())
    print('proc_7862F0C5:', proc_7862F0C5())
    print('proc_D15DA2BB:', proc_D15DA2BB())
    #print('proc_D1FBA3F7:', proc_D1FBA3F7())
    print('proc_B85B70B6:', proc_B85B70B6())
    print('proc_578EAF1D:', proc_578EAF1D())
    print('GetProcessorMaxCacheLevel:', GetProcessorMaxCacheLevel())
    #print('GetProcessorCacheParameters:', GetProcessorCacheParameters())
    #print('GetProcessorExtendedCacheParameters:', GetProcessorExtendedCacheParameters())
    print('GetHyperThreadingStatus:', GetHyperThreadingStatus())
    print('GetVirtualTechnologyStatus:', GetVirtualTechnologyStatus())
    print('GetProcessorID: 0x%X' % GetProcessorID())
    print('GetProcessorVoltage:', GetProcessorVoltage())

    #print('GetNorthBridgeVendor:', GetNorthBridgeVendor())

    print('GetMemoryType:', GetMemoryType())
    print('GetMemorySize:', GetMemorySize())
    print('Memory Chan:', GetMemoryNumberOfChannels())
    print('Memory Freq:', GetMemoryClockFrequency())
    print('CASLatency:', GetMemoryCASLatency())
    print('GetMemoryRAStoCASDelay:', GetMemoryRAStoCASDelay())
    print('GetMemoryRASPrecharge:', GetMemoryRASPrecharge())
    print('GetMemoryTRAS:', GetMemoryTRAS())
    print('GetMemoryTRC:', GetMemoryTRC())
    print('GetMemoryCommandRate:', GetMemoryCommandRate())
    print('ComputeMemoryFrequency:', ComputeMemoryFrequency())

    print('GetBIOSVendor:', GetBIOSVendor())
    print('[END]')

if __name__ == "__main__":
    base_test()
    
    
