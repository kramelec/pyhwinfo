import ctypes
from ctypes.wintypes import *
from ctypes import CFUNCTYPE
from ctypes import byref

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

INVALID_HANDLE_VALUE = HANDLE(-1).value

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
    return (val + bnum - 1) & ~(bnum - 1)

def ROUNDUP4(value):
    return (value + 3) & 0xFFFFFFFC

def divRoundUp(n, d):
    return (n + d - 1) // d

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

_kernel32 = ctypes.WinDLL('kernel32')

class Win32FileHandle:
    def __init__(self):
        global _kernel32
        self.handle = None
        self.CreateFileA = _kernel32.CreateFileA
        self.CreateFileA.argtypes = [ LPCSTR, DWORD, DWORD, LPVOID, DWORD, DWORD, HANDLE ]
        self.CreateFileA.restype = HANDLE
        self.CloseHandle = _kernel32.CloseHandle
        self.CloseHandle.argtypes = [ HANDLE ]
        self.CloseHandle.restype = BOOL
    
    def __del__(self):
        self.close()
        
    def __repr__(self):
        return f'<HANDLE:0x{self.handle:X}>'
        
    def create(self, file_path, access = GENERIC_READ, share_mode = 0, creation = OPEN_EXISTING, attributes = FILE_ATTRIBUTE_NORMAL):
        if self.handle:
            raise RuntimeError('Handle needded close!')
        if isinstance(file_path, str):
            file_path = file_path.encode('latin-1')
        handle = self.CreateFileA(
            file_path,
            access,
            share_mode,
            None,
            creation,
            attributes,
            None
        )
        if handle == INVALID_HANDLE_VALUE:
            error_code = ctypes.get_last_error()
            raise ctypes.WinError(error_code)
        self.handle = handle
        return self
    
    def close(self):
        if self.handle:
            self.CloseHandle(self.handle)
            #if not self.CloseHandle(self.handle):
            #    error_code = ctypes.get_last_error()
            #    raise ctypes.WinError(error_code)

def CreateFileA(file_path, access = GENERIC_READ, share_mode = 0, creation = OPEN_EXISTING, attributes = FILE_ATTRIBUTE_NORMAL):
    hnd = Win32FileHandle()
    hnd.create(file_path, access, share_mode, creation, attributes)
    return hnd

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

fnDeviceIoControl = _kernel32.DeviceIoControl
fnDeviceIoControl.argtypes = [ HANDLE, DWORD, LPVOID, DWORD, LPVOID, DWORD, LPDWORD, LPOVERLAPPED ]
fnDeviceIoControl.restype = BOOL

def rawDeviceIoControl(hDevice, ioctl, lpInBuffer, nInBufferSize, lpOutBuffer, nOutBufferSize, lpBytesReturned, lpOverlapped):
    rc = fnDeviceIoControl(hDevice, ioctl, lpInBuffer, nInBufferSize, lpOutBuffer, nOutBufferSize, lpBytesReturned, lpOverlapped)
    return True if rc != 0 else False

def DeviceIoControl(hDevice, ioctl, inbuf, outbufsize, dummy):
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
    rc = fnDeviceIoControl(hDevice, ioctl, lpInBuffer, nInBufferSize, lpOutBuffer, outbufsize, byref(bytesReturned), None)
    if rc == 0:
        return False
    if bytesReturned.value > 0x4000:
        raise RuntimeError()
    if bytesReturned.value > outbufsize:
        raise RuntimeError()
    if not lpOutBuffer or bytesReturned.value == 0:
        return b''
    return bytes(ctypes.cast(lpOutBuffer, ctypes.POINTER(ctypes.c_ubyte * bytesReturned.value)).contents)

