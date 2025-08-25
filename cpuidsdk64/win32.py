#
# Copyright (C) 2025 remittor
#

import os
import sys
import atexit
import ctypes
from ctypes.wintypes import *
from ctypes import CFUNCTYPE, POINTER
from ctypes import byref
from types import SimpleNamespace
import struct

__author__ = 'remittor'

INT64 = LARGE_INTEGER
UINT64 = ULARGE_INTEGER

if ctypes.sizeof(ctypes.c_long) == ctypes.sizeof(ctypes.c_void_p):
    SIZE_T = ULONG
    ULONG_PTR = ULONG 
elif ctypes.sizeof(ctypes.c_longlong) == ctypes.sizeof(ctypes.c_void_p):
    SIZE_T = ULARGE_INTEGER
    ULONG_PTR = ULARGE_INTEGER 

GENERIC_READ  = 0x80000000
GENERIC_WRITE = 0x40000000

FILE_READ_DATA = 1
FILE_LIST_DIRECTORY = 1
FILE_WRITE_DATA = 2
FILE_ADD_FILE = 2
FILE_APPEND_DATA = 4
FILE_ADD_SUBDIRECTORY = 4
FILE_CREATE_PIPE_INSTANCE = 4
FILE_READ_EA = 8
FILE_WRITE_EA = 16
FILE_EXECUTE = 32
FILE_TRAVERSE = 32
FILE_DELETE_CHILD = 64
FILE_READ_ATTRIBUTES = 128
FILE_WRITE_ATTRIBUTES = 256

FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4 

FILE_ATTRIBUTE_READONLY = 1
FILE_ATTRIBUTE_HIDDEN = 2
FILE_ATTRIBUTE_SYSTEM = 4
FILE_ATTRIBUTE_DIRECTORY = 16
FILE_ATTRIBUTE_ARCHIVE = 32
FILE_ATTRIBUTE_DEVICE = 64
FILE_ATTRIBUTE_NORMAL = 128

CREATE_NEW = 1
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
TRUNCATE_EXISTING = 5

METHOD_BUFFERED = 0
METHOD_IN_DIRECT = 1
METHOD_OUT_DIRECT = 2
METHOD_NEITHER = 3
METHOD_DIRECT_TO_HARDWARE = METHOD_IN_DIRECT
METHOD_DIRECT_FROM_HARDWARE = METHOD_OUT_DIRECT

FILE_ANY_ACCESS = 0
FILE_SPECIAL_ACCESS = FILE_ANY_ACCESS
FILE_READ_ACCESS = 0x0001
FILE_WRITE_ACCESS = 0x0002

AC_DELETE       = 0x00010000
AC_READ_CONTROL = 0x00020000
AC_WRITE_DAC    = 0x00040000
AC_SYNCHRONIZE  = 0x00100000
AC_WRITE_OWNER  = 0x00800000

# Exception/Status codes from winuser.h and winnt.h
STATUS_WAIT_0 = 0
STATUS_ABANDONED_WAIT_0 = 128
STATUS_USER_APC = 192
STATUS_TIMEOUT = 258
STATUS_PENDING = 259

WAIT_FAILED = -1
WAIT_OBJECT_0 = STATUS_WAIT_0 + 0

WAIT_ABANDONED = STATUS_ABANDONED_WAIT_0 + 0
WAIT_ABANDONED_0 = STATUS_ABANDONED_WAIT_0 + 0

WAIT_TIMEOUT = STATUS_TIMEOUT
WAIT_IO_COMPLETION = STATUS_USER_APC
STILL_ACTIVE = STATUS_PENDING

ERROR_SUCCESS = 0
ERROR_HANDLE_EOF = 38
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_ALREADY_EXISTS = 183
ERROR_NO_MORE_ITEMS = 259
ERROR_IO_INCOMPLETE = 996
ERROR_IO_PENDING = 997

INVALID_HANDLE_VALUE = HANDLE(-1).value

def int_from_bytes(buf, offset, size, signed = False, big = False):
    return int.from_bytes(buf[offset:offset+size], 'big' if big else 'little', signed = signed)

def int_encode(value, width, signed = False, big = False):
    prefix = '>' if big else '<'
    if isinstance(width, int):
        if width == 1:
            width = 'B'
        elif width == 2:
            width = 'H'
        elif width == 4:
            width = 'I'
        elif width == 8:
            width = 'Q'
        else:
            raise RuntimeError()
        if signed:
            width = width.lower()
    return struct.pack(prefix + width, value)

def SETDIM(value, bits):  # set dimension
    if bits <= 1:
        return value & 1
    return value & ((1 << bits) - 1)

def HIDWORD(value):
    return (value >> 32) & 0xFFFFFFFF

def LODWORD(value):
    return value & 0xFFFFFFFF

def HIWORD(value):
    return (value >> 16) & 0xFFFF

def LOWORD(value):
    return value & 0xFFFF

def ALIGN(addr, bnum):
    """round down address to a bnum (bytes) boundary"""
    return addr & ~(bnum - 1)

def MASK(bits):
    """return a mask of width bits"""
    return (1 << bits) - 1

def MASKED(value, bits):
    """mask a value to width bits"""
    return value & ((1 << bits) - 1)

def ROUNDUP(value, bnum):
    """roundup a value to N x bnum"""
    return (value + bnum - 1) & ~(bnum - 1)

def ROUNDUP4(value):
    return (value + 3) & 0xFFFFFFFC

def divRoundUp(n, d):
    return (n + d - 1) // d

def get_bits(buf, offset, firts_bit, last_bit = None, bits = None):
    if offset is None:
        offset = 0
    if last_bit is None and bits is None:
        last_bit = firts_bit
    if last_bit is None and isinstance(bits, int):
        last_bit = firts_bit + bits - 1
    if last_bit < firts_bit:
        firts_bit, last_bit = last_bit, firts_bit # swap values
    size = (last_bit // 8) + 1
    if isinstance(buf, int) and size <= 8:
        buf = int_encode(buf, 8)
    value = int_from_bytes(buf, offset, size)
    if firts_bit > 0:
        value >>= firts_bit
    return SETDIM(value, last_bit - firts_bit + 1)

def get_bytes_addr(data):
    Buffer = ctypes.c_char * len(data)
    buf = Buffer.from_buffer(data)
    return ctypes.addressof(buf)

def get_file_version_info(filename):
    ver = ctypes.windll.version
    size = ver.GetFileVersionInfoSizeW(filename, None)
    if not size:
        return None
    res = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(filename, None, size, res):
        return None
    value = LPVOID()
    length = UINT(0)
    if not ver.VerQueryValueW(res, '\\', byref(value), byref(length)):
        return None
    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [
            ('dwSignature', DWORD),
            ('dwStrucVersion', DWORD),
            ('dwFileVersionMS', DWORD),
            ('dwFileVersionLS', DWORD),
            ('dwProductVersionMS', DWORD),
            ('dwProductVersionLS', DWORD),
            ('dwFileFlagsMask', DWORD),
            ('dwFileFlags', DWORD),
            ('dwFileOS', DWORD),
            ('dwFileType', DWORD),
            ('dwFileSubtype', DWORD),
            ('dwFileDateMS', DWORD),
            ('dwFileDateLS', DWORD),
        ]
    fixed_file_info = ctypes.cast(value, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
    file_version = (
        (fixed_file_info.dwFileVersionMS >> 16) & 0xFFFF,
        (fixed_file_info.dwFileVersionMS >> 0)  & 0xFFFF,
        (fixed_file_info.dwFileVersionLS >> 16) & 0xFFFF,
        (fixed_file_info.dwFileVersionLS >> 0)  & 0xFFFF,
    )
    product_version = (
        (fixed_file_info.dwProductVersionMS >> 16) & 0xFFFF,
        (fixed_file_info.dwProductVersionMS >> 0)  & 0xFFFF,
        (fixed_file_info.dwProductVersionLS >> 16) & 0xFFFF,
        (fixed_file_info.dwProductVersionLS >> 0)  & 0xFFFF,
    )
    return {
        'file_version': file_version,
        'product_version': product_version,
        'flags': fixed_file_info.dwFileFlags,
        'os': fixed_file_info.dwFileOS,
        'type': fixed_file_info.dwFileType,
    }

##################################################################################################

MAX_DEVICE_PATH_LEN = 2000

class SP_DEVICE_INTERFACE_DETAIL_DATA_A(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('DevicePath', CHAR * MAX_DEVICE_PATH_LEN),
    ]
    _pack_ = 1
    def __str__(self):
        return f'DevicePath: "{self.DevicePath.decode("latin-1")}"'

PSP_DEVICE_INTERFACE_DETAIL_DATA_A = POINTER(SP_DEVICE_INTERFACE_DETAIL_DATA_A)

class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ('nLength', DWORD),
        ('lpSecurityDescriptor', LPVOID),
        ('bInheritHandle', BOOL),
    ]

LPSECURITY_ATTRIBUTES = POINTER(SECURITY_ATTRIBUTES)

class _OFFSET(ctypes.Structure):
    _fields_ = [
        ("Offset",     DWORD),
        ("OffsetHigh", DWORD)
    ]

class _OFFSET_UNION(ctypes.Union):
    _anonymous_ = [ "_offset" ]
    _fields_ = [
        ("_offset", _OFFSET),
        ("Pointer", LPVOID)
    ]

class OVERLAPPED(ctypes.Structure):
    _anonymous_ = [ "_offset_union" ]
    _fields_ = [
        ("Internal",      ULONG_PTR),
        ("InternalHigh",  ULONG_PTR),
        ("_offset_union", _OFFSET_UNION),
        ("hEvent",        HANDLE),
    ]

LPOVERLAPPED = ctypes.POINTER(OVERLAPPED)

###########################################################################################

_kernel32 = ctypes.WinDLL('kernel32')
_win32 = SimpleNamespace()

_win32.CloseHandle = _kernel32.CloseHandle
_win32.CloseHandle.argtypes = [ HANDLE ]
_win32.CloseHandle.restype = BOOL 

_win32.CreateFileA = _kernel32.CreateFileA
_win32.CreateFileA.argtypes = [
    LPCSTR,                # lpFileName,
    DWORD,                 # dwDesiredAccess,
    DWORD,                 # dwShareMode,
    LPSECURITY_ATTRIBUTES, # lpSecurityAttributes,
    DWORD,                 # dwCreationDisposition,
    DWORD,                 # dwFlagsAndAttributes,
    HANDLE                 # hTemplateFile
]
_win32.CreateFileA.restype = HANDLE 

_win32.CreateEventA = _kernel32.CreateEventA
_win32.CreateEventA.argtypes = [
    LPSECURITY_ATTRIBUTES, # lpEventAttributes,
    BOOL,                  # bManualReset,
    BOOL,                  # bInitialState,
    LPCSTR                 # lpName
]
_win32.CloseHandle.restype = BOOL 

_win32.SetEvent = _kernel32.SetEvent
_win32.SetEvent.argtypes = [ HANDLE ]   # hEvent
_win32.SetEvent.restype = BOOL

_win32.ResetEvent = _kernel32.ResetEvent
_win32.ResetEvent.argtypes = [ HANDLE ]   # hEvent
_win32.ResetEvent.restype = BOOL

_win32.CancelIo = _kernel32.CancelIo
_win32.CancelIo.argtypes = [ HANDLE ]   # hFile
_win32.CancelIo.restype = BOOL

_win32.WaitForSingleObject = _kernel32.WaitForSingleObject
_win32.WaitForSingleObject.argtypes = [
    HANDLE,  # hHandle,
    DWORD    # dwMilliseconds
]
_win32.WaitForSingleObject.restype = DWORD 

_win32.DeviceIoControl = _kernel32.DeviceIoControl
_win32.DeviceIoControl.argtypes = [ HANDLE, DWORD, LPVOID, DWORD, LPVOID, DWORD, LPDWORD, LPOVERLAPPED ]
_win32.DeviceIoControl.restype = BOOL

_win32.CreateMutexW = _kernel32.CreateMutexA
_win32.CreateMutexW.argtypes = [
    LPSECURITY_ATTRIBUTES, # lpMutexAttributes,
    BOOL,                  # bInitialOwner,
    LPCWSTR                # lpName
]
_win32.CreateMutexW.restype = HANDLE

_win32.OpenMutexW = _kernel32.OpenMutexW
_win32.OpenMutexW.argtypes = [
    DWORD,     # dwDesiredAccess
    BOOL,      # bInheritHandle,
    LPCWSTR    # lpName
]
_win32.OpenMutexW.restype = HANDLE

_win32.ReleaseMutex = _kernel32.ReleaseMutex
_win32.ReleaseMutex.argtypes = [ HANDLE ]   # hMutex
_win32.ReleaseMutex.restype = BOOL

###############################################################################################

class Win32FileHandle:
    def __init__(self):
        global _win32
        self._init()
        atexit.register(self.cleanup)

    def _init(self, close = False):
        self.handle = None
        self.name = None
        self.is_mutex = False
        self.is_acquired = False
        self.release_on_close = True
        self.msgerr = None
    
    def __del__(self):
        self.close()

    def cleanup(self):
        self.close()

    def close(self):
        global _win32
        if self.handle and _win32 and _win32.CloseHandle:
            if self.is_mutex and self.release_on_close:
                self.release_mutex()
            _win32.CloseHandle(self.handle)
        self._init(close = True)

    def __repr__(self):
        return f'<HANDLE:0x{self.handle:X}>' if self.handle else '<HANDLE:null>'
        
    def create_file(self, file_path, access = GENERIC_READ, share_mode = 0, creation = OPEN_EXISTING, attributes = FILE_ATTRIBUTE_NORMAL):
        global _win32
        self.errcode = 0
        if self.handle:
            raise RuntimeError('Handle already used!')
        if isinstance(file_path, str):
            file_path = file_path.encode('latin-1')
        handle = _win32.CreateFileA(file_path, access, share_mode, None, creation, attributes, None)
        self.errcode = ctypes.get_last_error()
        if not handle or handle == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(self.errcode)
        self.handle = handle
        self.name = file_path.decode('latin-1')
        return self

    def create_mutex(self, obj_path, bInitialOwner = False, release_on_close = True, msgerr = None, open = False, throwable = True):
        global _win32
        self.errcode = 0
        if self.handle:
            raise RuntimeError('Handle already used!')
        self.handle = None
        self.name = obj_path # .decode('utf-16-le')
        if open:
            dwDesiredAccess = AC_SYNCHRONIZE
            bInheritHandle = bInitialOwner
            handle = _win32.OpenMutexW(dwDesiredAccess, bInheritHandle, obj_path)
        else:
            lpMutexAttributes = None
            handle = _win32.CreateMutexW(lpMutexAttributes, bInitialOwner, obj_path)
        self.errcode = ctypes.get_last_error()
        self.release_on_close = release_on_close
        # If we created a mutex with bInitialOwner=True, it starts in acquired state
        self.is_acquired = bInitialOwner and not open
        self.is_mutex = True
        if not handle:
            if throwable:
                raise ctypes.WinError(self.errcode)
            return None
        self.handle = handle        
        return self

    def release_mutex(self, throwable = False):
        global _win32
        if not self.handle:
            if throwable:
                raise ValueError('Incorrect mutex handle!')
            return False
        rc = _win32.ReleaseMutex(self.handle)
        if rc != 0 and self.is_acquired:
            self.is_acquired = False
        return True if rc != 0 else False

    release = release_mutex

    def acquire_mutex(self, wait_ms = 2000, throwable = True):
        global _win32
        if self.is_acquired:
            return True
        if not self.handle:
            if throwable:
                raise ValueError('Incorrect mutex handle!')
            return False
        rc = _win32.WaitForSingleObject(self.handle, wait_ms)
        if rc != STATUS_WAIT_0 and throwable:
            if not self.msgerr:
                raise RuntimeError(f'ERROR: Cannot acquire a mutex "{self.name}"')
            raise RuntimeError(f'ERROR: {self.msgerr}')
        if rc == STATUS_WAIT_0:
            self.is_acquired = True
            return True
        return False

    acquire = acquire_mutex

def CreateFileA(file_path, access = GENERIC_READ, share_mode = 0, creation = OPEN_EXISTING, attributes = FILE_ATTRIBUTE_NORMAL):
    handle = Win32FileHandle()
    handle.create_file(file_path, access, share_mode, creation, attributes)
    return handle

def CreateMutexW(obj_path, bInitialOwner = False, throwable = True):
    handle = Win32FileHandle()
    handle.create_mutex(obj_path, bInitialOwner, throwable = throwable)
    return handle

def OpenMutexW(obj_path, bInheritHandle = False, throwable = True):
    handle = Win32FileHandle()
    handle.create_mutex(obj_path, bInheritHandle, throwable = throwable, open = True)
    return handle

def rawDeviceIoControl(hDevice, ioctl, lpInBuffer, nInBufferSize, lpOutBuffer, nOutBufferSize, lpBytesReturned, lpOverlapped):
    global _win32
    rc = _win32.DeviceIoControl(hDevice, ioctl, lpInBuffer, nInBufferSize, lpOutBuffer, nOutBufferSize, lpBytesReturned, lpOverlapped)
    return True if rc != 0 else False

def DeviceIoControl(hDevice, ioctl, inbuf, outbufsize, dummy = None):
    global _win32
    if isinstance(hDevice, Win32FileHandle):
        hDevice = hDevice.handle
    lpInBuffer = None
    nInBufferSize = 0
    if inbuf:
        if isinstance(inbuf, bytes):
            inbuf = bytearray(inbuf)
        lpInBuffer = get_bytes_addr(inbuf)
        lpInBuffer = ctypes.cast(lpInBuffer, ctypes.POINTER(ctypes.c_char))
        nInBufferSize = len(inbuf)
    lpOutBuffer = None
    if outbufsize > 0:
        lpOutBuffer = ctypes.create_string_buffer(outbufsize)
        lpOutBuffer = ctypes.cast(lpOutBuffer, ctypes.POINTER(ctypes.c_char))
    bytesReturned = DWORD(0)
    rc = _win32.DeviceIoControl(hDevice, ioctl, lpInBuffer, nInBufferSize, lpOutBuffer, outbufsize, byref(bytesReturned), None)
    if rc == 0:
        return False
    if bytesReturned.value > outbufsize:
        raise RuntimeError()
    if not lpOutBuffer or bytesReturned.value == 0:
        return b''
    return bytes(ctypes.cast(lpOutBuffer, ctypes.POINTER(ctypes.c_ubyte * bytesReturned.value)).contents)

def exec_command(cmd):
    import subprocess
    res = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
    return res.stdout.replace('\r\n', '\n').replace('\n\n', '\n')

def get_motherboard_info():
    import subprocess
    out = { }
    cmd = 'Get-WmiObject win32_baseboard | Format-List Manufacturer,Product'
    try:
        res = exec_command( [ 'powershell', '-command', cmd ] )
        lines = res.split('\n')
        lines = list(filter(None, lines))
        out['manufacturer'] = lines[0].split(':')[1].strip()
        out['product'] = lines[1].split(':')[1].strip()
    except Exception:
        return { 'product': '', 'manufacturer': '' }
    return out
