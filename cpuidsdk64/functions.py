import os
import sys
import inspect
import atexit
import struct
import ctypes
from ctypes.wintypes import *
from ctypes import byref
from ctypes import CFUNCTYPE

from cpuidsdk64 import *
from cpuidsdk64 import get_objptr, _set_objptr
from cpuidsdk64 import _get_drv, _set_drv
from cpuidsdk64 import _init_sdk_dll

_sdk_base_dir = os.path.dirname(os.path.abspath(__file__))

#################################################/
# Instance management
#################################################/

def CreateInstance(verbose = 0):
    objptr = get_objptr(check = False)
    if objptr:
        raise RuntimeError()
    func_get_ver = get_sdkfunc('GetDLLVersion')
    if not func_get_ver['addr']:
        _init_sdk_dll(verbose)
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPVOID))
    ptr = func()
    if not ptr:
        raise RuntimeError(f'Cannot create CPUIDSDK object')
    _set_objptr(ptr)
    if verbose:
        print(f'CPUIDSDK: objptr = 0x{ptr:X}')
    return True

def DestroyInstance():
    objptr = get_objptr(check = False)
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(None, LPVOID))
    objptr = get_objptr()
    func(objptr)
    _set_objptr(None)

def SdkInit(cfg = None, verbose = 0):
    global _sdk_base_dir
    objptr = get_objptr(check = False)
    if not objptr:
        CreateInstance(verbose = verbose)
    func = get_sdk_func('SdkInit', CFUNCTYPE(BOOL, LPVOID, LPCSTR, LPCSTR, INT, LPINT, LPINT))
    objptr = get_objptr()
    szDllPath = _sdk_base_dir.encode('latin_1') + b'\0'
    szDllFilename = b'cpuidsdk64.dll\0'
    if cfg is None:
        config_flag = CPUIDSDK_CONFIG_USE_SOFTWARE + CPUIDSDK_CONFIG_USE_PROCESSOR
        config_flag += CPUIDSDK_CONFIG_USE_CHIPSET
        config_flag += CPUIDSDK_CONFIG_USE_PCI
    else:
        config_flag = int(cfg)
    errorcode = INT(0)
    extended_errorcode = INT(0)
    print(f'Initialization of cpuidsdk64.dll and cpuz.sys ...')
    rc = func(objptr, szDllPath, szDllFilename, config_flag, byref(errorcode), byref(extended_errorcode))
    print('SdkInit =', rc, ' errorcode =', errorcode.value, ' code =', extended_errorcode.value)
    if rc != 1:
        if errorcode.value == CPUIDSDK_ERROR_DRIVER:
            raise RuntimeError(f'Cannot load driver cpuz152.sys (errcode = {extended_errorcode.value})')
        raise RuntimeError(f'Cannot init cpuidsdk (errcode = {errorcode.value})')
    drv_obj_path = r"\\.\cpuz152"
    drv = CreateFileA(drv_obj_path, GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING, 0)    
    if verbose:
        print(f'driver handle =', drv)
    _set_drv(drv)
    return drv

def SdkClose():
    drv = _get_drv(check = False)
    if drv:
        try:
            drv.close()
        except Exception:
            pass
        _set_drv(None)
    func = get_sdk_func('SdkClose', CFUNCTYPE(None, LPVOID))
    objptr = get_objptr()
    func(objptr)

def RefreshInformation():
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetDLLVersion():
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(None, LPVOID, LPINT))
    objptr = get_objptr()
    version = INT(0)
    func(objptr, byref(version))
    return version.value

def SdkCleanup():
    objptr = get_objptr(check = False)
    print("SdkCleanup...")
    if objptr:
        SdkClose()
        DestroyInstance()

atexit.register(SdkCleanup)
 
#################################################/
# Processor
#################################################/

def GetNbProcessors():
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetProcessorFamily(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorExtendedFamily(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorModel(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorExtendedModel(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorSteppingID(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorCoreCount(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorThreadCount(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorCoreThreadCount(proc_index = 0, core_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT, INT))
    objptr = get_objptr()
    return func(objptr, proc_index, core_index)

def GetProcessorThreadAPICID(proc_index = 0, core_index = 0, thread_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID, INT, INT, INT))
    objptr = get_objptr()
    return func(objptr, proc_index, core_index, thread_index)

def GetProcessorName(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPSTR, LPVOID, INT))
    objptr = get_objptr()
    buf = func(objptr, proc_index)
    if not buf:
        return None
    pname = buf.decode()
    SysFreeString(buf)
    return pname

def GetProcessorCodeName(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPSTR, LPVOID, INT))
    objptr = get_objptr()
    buf = func(objptr, proc_index)
    if not buf:
        return None
    pname = buf.decode()
    SysFreeString(buf)
    return pname

def GetProcessorPackage(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPSTR, LPVOID, INT))
    objptr = get_objptr()
    buf = func(objptr, proc_index)
    if not buf:
        return None
    pname = buf.decode()
    SysFreeString(buf)
    return pname

def GetProcessorSpecification(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPSTR, LPVOID, INT))
    objptr = get_objptr()
    buf = func(objptr, proc_index)
    if not buf:
        return None
    pname = buf.decode()
    SysFreeString(buf)
    return pname

def GetProcessorStepping(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPSTR, LPVOID, INT))
    objptr = get_objptr()
    buf = func(objptr, proc_index)
    if not buf:
        return None
    pname = buf.decode()
    SysFreeString(buf)
    return pname

def GetProcessorTDP(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def proc_EA5DD4BB(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    #print('%08X' % get_sdkfunc(fname)['fid'])
    objptr = get_objptr()
    return func(objptr, proc_index)

def proc_D3B9A773(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def IsProcessorInstructionSetAvailable(proc_index = 0, iset = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(UINT64, LPVOID, INT, INT))
    objptr = get_objptr()
    rc = func(objptr, proc_index, iset)
    #print('%X' % rc)
    return True if rc == 1 else False

def proc_71CAE395(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def proc_09141228(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def proc_7862F0C5(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def proc_D15DA2BB(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

# ?????????????
def proc_D1FBA3F7(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def proc_B85B70B6(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def proc_578EAF1D(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(UINT64, LPVOID, INT))
    objptr = get_objptr()
    rc = func(objptr, proc_index)
    return rc

'''
def GetProcessorStockClockFrequency(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorStockBusFrequency(proc_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(UINT64, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorCoreClockFrequency(proc_index = 0, core_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT, INT))
    objptr = get_objptr()
    return func(objptr, proc_index, core_index)

def GetProcessorCoreClockMultiplier(proc_index = 0, core_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT, INT))
    objptr = get_objptr()
    return func(objptr, proc_index, core_index)

def GetProcessorCoreTemperature(proc_index = 0, core_index = 0):
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT, INT))
    objptr = get_objptr()
    return func(objptr, proc_index, core_index)

def GetBusFrequency():
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID))
    objptr = get_objptr()
    return func(objptr)
'''

def GetProcessorMaxCacheLevel(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(UINT64, LPVOID, INT))
    objptr = get_objptr()
    rc = func(objptr, proc_index)
    return rc

def GetProcessorCacheParameters(proc_index = 0, cache_level = 0, cache_type = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(None, LPVOID, INT, INT, INT, LPINT, LPINT))
    objptr = get_objptr()
    NbCaches = INT(-1)
    size = INT(-1)
    func(objptr, proc_index, cache_level, cache_type, byref(NbCaches), byref(size))
    return (NbCaches.value, size.value)

def GetProcessorExtendedCacheParameters(proc_index = 0, cache_level = 0, cache_type = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(None, LPVOID, INT, INT, INT, LPINT, LPINT))
    objptr = get_objptr()
    associativity = INT(-1)
    line_size = INT(-1)
    func(objptr, proc_index, cache_level, cache_type, byref(associativity), byref(line_size))
    return (associativity.value, line_size.value)

def GetHyperThreadingStatus(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(None, LPVOID, INT, LPINT, LPINT))
    objptr = get_objptr()
    supported = INT(-1)
    enabled = INT(-1)
    func(objptr, proc_index, byref(supported), byref(enabled))
    return (supported.value, enabled.value)

def GetVirtualTechnologyStatus(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(None, LPVOID, INT, LPINT, LPINT))
    objptr = get_objptr()
    supported = INT(-1)
    enabled = INT(-1)
    func(objptr, proc_index, byref(supported), byref(enabled))
    return (supported.value, enabled.value)

def GetProcessorID(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(UINT64, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetProcessorVoltageID(proc_index = 0): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID, INT))
    objptr = get_objptr()
    return func(objptr, proc_index)

def GetNorthBridgeVendor(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPSTR, LPVOID))
    objptr = get_objptr()
    buf = func(objptr)
    if not buf:
        return None
    pname = buf.decode()
    SysFreeString(buf)
    return pname

def GetMemoryType(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)
    
def GetMemorySize(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryNumberOfChannels(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryClockFrequency(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryCASLatency(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryRAStoCASDelay(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryRASPrecharge(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryTRAS(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryTRC(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetMemoryCommandRate(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(INT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def ComputeMemoryFrequency(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(FLOAT, LPVOID))
    objptr = get_objptr()
    return func(objptr)

def GetBIOSVendor(): 
    fname = inspect.currentframe().f_code.co_name
    func = get_sdk_func(fname, CFUNCTYPE(LPSTR, LPVOID))
    objptr = get_objptr()
    buf = func(objptr)
    if not buf:
        return None
    pname = buf.decode()
    SysFreeString(buf)
    return pname

