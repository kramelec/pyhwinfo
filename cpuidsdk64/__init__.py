import os
import sys
import inspect
import atexit
import struct
import ctypes
from ctypes.wintypes import *
from ctypes import byref
from ctypes import CFUNCTYPE

from .win32 import *

_sdk_base_dir = os.path.dirname(os.path.abspath(__file__))
_sdk_dll_path = os.path.join(_sdk_base_dir, 'cpuidsdk64.dll')
if not os.path.exists(_sdk_dll_path):
    raise RuntimeError(f'File "{_sdk_dll_path}" not found!')

def get_pe_version(filename):
   info = get_file_version_info(filename)
   return info['file_version']

supported_version = (1, 2, 6, 4)

dll_ver = get_pe_version(_sdk_dll_path)
if dll_ver != supported_version:
    raise RuntimeError(f'Currently support only CPUIDSDK ver {".".join(map(str, supported_version))}')

cpuidsdk64 = ctypes.WinDLL(_sdk_dll_path)
OleAut32 = ctypes.WinDLL('OleAut32.dll')

def __DllFunc(name, ret, args, dll = None):
    func = cpuidsdk64[name] if dll is None else dll[name]
    func.restype = ret
    func.argtype = args
    return func

from .common import *
from .common import _sdk_func_table

QueryInterface = __DllFunc("QueryInterface", LPVOID, (DWORD))
SysFreeString = __DllFunc("SysFreeString", None, (LPSTR), OleAut32)

def _init_sdk_dll(verbose = 0):
    global _sdk_func_table
    qi_addr = ctypes.cast(QueryInterface, ctypes.c_void_p).value
    qia = qi_addr - cpuidsdk64._handle + 0x180000000
    if verbose >= 2:
        print(f'addr[QueryInterface] = 0x{qi_addr:08X} => 0x{qia:08X}')
    qi_size = 0x1400
    qib = ctypes.string_at(qi_addr, qi_size)
    fnum = -1
    pos = 0
    while True:
        fnum += 1
        if qib[pos:pos+2] != b'\x3B\x0D':   # cmp ecx, cs:XXXX
            if verbose >= 2:
                print('END of QueryInterface function')
            break
        fid_addr = int.from_bytes(qib[pos+2:pos+2+4], "little") + qi_addr + pos + 6
        pos += 6
        #print('0x%08X' % func_id_addr)
        fid = ctypes.string_at(fid_addr, 4)
        fid = int.from_bytes(fid, "little")
        #print('0x%08X' % fid)
        pos += 2  # skip jnz opcode
        if qib[pos:pos+3] != b'\x48\x8D\x05':
            raise RuntimeError('Incorrect QueryInterface format (0)')
        func_addr = int.from_bytes(qib[pos+3:pos+3+4], "little") + qi_addr + pos + 7
        pos += 7
        func_ADDR = func_addr - cpuidsdk64._handle + 0x180000000
        pos += 1  # skip retn opcode
        fname = ''
        if fnum < len(_sdk_func_table):
            func = _sdk_func_table[fnum]
            func['fid'] = fid
            func['addr'] = func_addr
            func['ADDR'] = func_ADDR
            fname = func['name']
        if fname and verbose >= 2:
            print(f'0x{fid:08X} : 0x{func_addr:012X}  0x{func_ADDR:012X}  {fname}')
        
def get_sdk_func(fname, ftype = None):
    finfo = get_sdkfunc(fname)
    if not finfo:
        raise ValueError(f'Function "{fname}" not found')
    if not finfo['fid']:
        raise RuntimeError(f'Cannot found id for function "{fname}"')
    func = finfo['func']
    if func:
        return func
    func_addr = QueryInterface(finfo['fid'])
    if not func_addr:
        raise RuntimeError('Used incorrect fid')
    #if not finfo['addr']:
    finfo['addr'] = func_addr
    if not ftype:
        raise ValueError('Function type must be specified')
    func_type = ftype
    func = func_type(func_addr)
    finfo['func'] = func
    return func

_objptr = None
_drv = None

def get_objptr(check = True):
    global _objptr
    if check and not _objptr:
        raise RuntimeError(f'Incorrect global var objptr = {_objptr}')
    return _objptr

def _set_objptr(ptr):
    global _objptr
    _objptr = ptr

def _get_drv(check = True):
    global _drv
    if check and not _drv:
        raise RuntimeError(f'Incorrect global var drv = {_drv}')
    return _drv

def _set_drv(drv):
    global _drv
    _drv = drv

from .functions import *
from .drvfunc import *

