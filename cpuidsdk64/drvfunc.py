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
from cpuidsdk64 import _get_drv

def ioctl_encode(DeviceType, Access, Function, Method):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method

def IOCTL(func_num):
    return ioctl_encode(CPUZ_DEVICE_TYPE, FILE_ANY_ACCESS, func_num, METHOD_BUFFERED)

def ioctl_decode(ioctl, ret_dict = False):
    DeviceType = (ioctl & 0xffff0000) >> 16
    Access     = (ioctl & 0x0000c000) >> 14
    Function   = (ioctl & 0x00003ffc) >> 2
    Method     = (ioctl & 0x00000003)
    if ret_dict:
        return { 'DeviceType': DeviceType, 'Access': Access, 'Function': Function, 'Method': Method }
    else:
        return f'DeviceType: 0x{DeviceType:X}, Access: 0x{Access:X}, Function: 0x{Function:X}, Method: 0x{Method:X}'

# ioctl: 9C402480 , 9C402484, 0x9C402488 
def port_read(port, size):
    _drv = _get_drv()
    if size == 1:
        func_num = CPUZ_PORT_READ_1
        buf_fmt = "<BBBBI" # BYTE,BYTE,BYTE,BYTE,DWORD
    elif size == 2:
        func_num = CPUZ_PORT_READ_2
        buf_fmt = "<HHI" # WORD,WORD,DWORD
    elif size == 4:
        func_num = CPUZ_PORT_READ_4
        buf_fmt = "<II" # DWORD,DWORD
    else:
        raise ValueError()
    inbuf = struct.pack('<I', port)
    buf_size = struct.calcsize(buf_fmt)
    buf = DeviceIoControl(_drv, IOCTL(func_num), inbuf, buf_size, None)
    out = struct.unpack(buf_fmt, buf)
    return out[0]

def port_read_u1(port):
    return port_read(port, 1)

def port_read_u4(port):
    return port_read(port, 4)

# ioctl: 9C4024C0 , 9C4024C4 , 9C4024C8
def port_write(port, value, size = None):
    _drv = _get_drv()
    if isinstance(value, bytes):
        if size is not None and size != len(value):
            raise ValueError()
        size = len(value)
        value = int.from_bytes(value, 'little', signed = False)
    if size == 1:
        func_num = CPUZ_PORT_WRITE_1
    elif size == 2:
        func_num = CPUZ_PORT_WRITE_2
    elif size == 4:
        func_num = CPUZ_PORT_WRITE_4
    else:
        raise ValueError()
    inbuf = struct.pack('<II', port, value)
    DeviceIoControl(_drv, IOCTL(func_num), inbuf, 8, None)

def port_write_u1(port, value):
    return port_write(port, value, 1)

def port_write_u4(port, value):
    return port_write(port, value, 4)


def CFG_ADDR(bus, dev, fun, reg):
    bus = SETDIM(bus, 15)
    dev = SETDIM(dev, 5)
    fun = SETDIM(fun, 3)
    reg = SETDIM(reg, 8)
    return 0x80000000 | (bus << 16) | (dev << 11) | (fun << 8) | reg

CFG_ADDR_PORT = 0xCF8
CFG_DATA_PORT = 0xCFC

# ioctl: 9C402700
def pci_cfg_read(bus, dev, fun, offset, size, method = 1):
    _drv = _get_drv()
    out_decimal = False
    if isinstance(size, str):
        out_decimal = True
        size = int(size)
    if size < 0:
        raise ValueError(f'Incorrect size argument')
    if method == 1:
        data_addr = 0
        if size > 0:
            data = bytearray(size)
            data_addr = get_bytes_addr(data)
        inbuf = struct.pack('<IIIIIII', bus, dev, fun, offset, size, HIDWORD(data_addr), LODWORD(data_addr))
        # BusDataType = PCIConfiguration  # 4
        # BusNumber = bus
        # SlotNumber = (SETDIM(fun, 3) << 5) | SETDIM(dev, 5)
        # Buffer = HIDWORD(data_addr) << 32 + LODWORD(data_addr)
        # Offset = offset
        # Length = size 
        # ULONG HalGetBusDataByOffset(BUS_DATA_TYPE BusDataType, ULONG BusNumber, ULONG SlotNumber, PVOID Buffer, ULONG Offset, ULONG Length);
        buf = DeviceIoControl(_drv, IOCTL(CPUZ_PCI_CFG_READ), inbuf, 4, None)
        if not buf or len(buf) != 4:
            raise RuntimeError(f'DeviceIoControl failed') # GetLastError
        sz = int.from_bytes(buf, 'little', signed = True)
        if sz == 2:
            #if size > 0:
            #    data = b'\xFF\xFF\xFF\xFF' * ((size - 1) // 4 + 1)
            return bytes(data) if not out_decimal else int.from_bytes(data, 'little')
        if sz == size:
            return bytes(data) if not out_decimal else int.from_bytes(data, 'little')
        return None
    if size == 0:
        raise ValueError(f'Incorrect size argument')
    buf = b''
    while len(buf) < size:
        addr = CFG_ADDR(bus, dev, fun, offset + len(buf))
        prev_state = port_read_u4(CFG_ADDR_PORT)
        try:
            port_write_u4(CFG_ADDR_PORT, addr & 0xFFFFFFFC)
            value = port_read_u4(CFG_DATA_PORT)
        finally:
            port_write_u4(CFG_ADDR_PORT, prev_state)
        value = value >> ((addr & 3) * 8)
        buf += struct.pack('<I', value)
    return buf if not out_decimal else int.from_bytes(buf, 'little')

# ioctl: 9C402704
def pci_cfg_write(bus, dev, fun, offset, data, method = 1):
    _drv = _get_drv()
    if isinstance(data, int):
        data_size = 4 if data <= 0xFFFFFFFF else 8
        data = data.to_bytes(data_size, 'little')
    if not data:
        raise ValueError(f'Incorrect data argument')
    if (len(data) & 3) != 0:
        raise ValueError(f'Incorrect data argument')
    if method == 1:
        size = len(data)
        data_addr = get_bytes_addr(data)
        inbuf = struct.pack('<IIIIIII', bus, dev, fun, offset, size, HIDWORD(data_addr), LODWORD(data_addr))
        # ULONG HalSetBusDataByOffset(BUS_DATA_TYPE BusDataType, ULONG BusNumber, ULONG SlotNumber, PVOID Buffer, ULONG Offset, ULONG Length);
        buf = DeviceIoControl(_drv, IOCTL(CPUZ_PCI_CFG_WRITE), inbuf, 4, None)
        if not buf or len(buf) != 4:
            raise RuntimeError(f'DeviceIoControl failed')
        rc = int.from_bytes(buf, 'little', signed = True)
        return True if rc != 0 else False
    pos = 0
    while pos < len(data):
        addr = CFG_ADDR(bus, dev, fun, offset + pos)
        if (addr & 3) != 0:
            raise ValueError(f'Incorrect offset argument')
        prev_state = port_read_u4(CFG_ADDR_PORT)
        try:
            port_write_u4(CFG_ADDR_PORT, addr & 0xFFFFFFFC)
            port_write_u4(CFG_DATA_PORT, data[pos:pos+4])
        finally:
            port_write_u4(CFG_ADDR_PORT, prev_state)
        pos += 4
    return True

def CFG_ADDR_EX(bus, dev, fun, off):
    bus = SETDIM(bus, 12)
    dev = SETDIM(dev, 5)
    fun = SETDIM(fun, 3)
    off = SETDIM(off, 12)
    return (bus << 20) | (dev << 15) | (fun << 12) | off

# ioctl: 9C402708
def pci_cfg_cmd(cfg_addr, value):
    _drv = _get_drv()
    inbuf = struct.pack('<II', cfg_addr, value)
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_PCI_CFG_CMD), inbuf, 4, None)
    if not buf or len(buf) != 4:
        raise RuntimeError(f'DeviceIoControl failed')
    return int.from_bytes(buf, 'little', signed = False)

# pci_cfg_read_ex    
def pci_cfg_command(bus, dev, fun, offset):
    addr = CFG_ADDR_EX(bus, dev, fun, offset)
    val = pci_cfg_read(bus, dev, fun, 0, 4);
    if not val:
        return None
    val = int.from_buffer(val, 'little')
    resp = pci_cfg_cmd(addr, val)
    return resp >> (8 * (addr & 3))

# ioctl: 0x9C402680
def port_read_xxx(port, a1, a2, a3):
    _drv = _get_drv()
    inbuf = struct.pack('<IIII', port, a1, a2, a3)
    # port_write_u1(port, a3);
    # port_write_u1(port + 4, (a1 << 1) | 1);
    # port_write_u1(port + 3, a2);
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_PORT_READ_XXX), inbuf, 16, None)
    x1, x2, x3, x4 = struct.unpack('<IIII', buf)
    if x1 == 0:
        if (x3 & 0xF0) == 0x40:
            return 4, -1
        return x1, -1
    return (x1, x2 & 0xFF)

# ioctl: 0x9C402690
def port_write_xxx(port, a1, a2, a3, value):
    _drv = _get_drv()
    inbuf = struct.pack('<IIIII', port, a1, a2, a3, value)
    # port_write_u1(port, a3);
    # port_write_u1(port + 4, a1 << 1);
    # port_write_u1(port + 3, a2);
    # port_write_u1(port + 5, value);
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_PORT_WRITE_XXX), inbuf, 8, None)
    x1, x2 = struct.unpack('<II', buf)
    if x2 == 0x22222222:
        pass
    if x2 == 0x33333333:
        pass
    return x1
    
#######################################################
#  MSR
#######################################################    
    
# ioctl: 9C402440
def msr_read(reg):
    _drv = _get_drv()
    inbuf = struct.pack('<I', reg)
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_MSR_READ), inbuf, 8, None)
    val_LO, val_HI = struct.unpack('<II', buf)
    if val_LO == 0xFFFFFFFF and val_HI == 0xFFFFFFFF:
        return None
    return (val_HI, val_LO)

# ioctl: 9C402444
def msr_write(reg, val_HI, val_LO):
    _drv = _get_drv()
    inbuf = struct.pack('<III', reg, val_HI, val_LO)
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_MSR_WRITE), inbuf, 8, None)
    rc = int.from_bytes(buf[:4], 'little', signed = False)
    return True if rc == 0xAAAAAAAA else False

# ioctl: 9C402448
def msr_command(val_HI, val_LO, method = 1):
    _drv = _get_drv()
    reg = 0x150  # ????????
    if method == 1:
        inbuf = struct.pack('<II', val_HI, val_LO)
        buf = DeviceIoControl(_drv, IOCTL(CPUZ_MSR_CMD), inbuf, 8, None)
        val_HI, val_LO = struct.unpack('<II', buf)
        #if val_LO == 0 and val_HI == 0:
        #    return None
        return (val_HI, val_LO)
    xvv = msr_read(reg)
    if xvv is not None:
        msr_write(reg, val_HI, val_LO)
        for tnum in range(0, 1000):
            kv = msr_read(addr)
            if kv is None:
                break
            if (kv[0] & 0x80000000) != 0:
                return kv
    return None        

# ioctl: 0x9C402608   msr_read
def msr_get_ticks(reg):
    _drv = _get_drv()
    inbuf = struct.pack('<I', reg)
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_MSR_GET_TICKS), inbuf, 8, None)
    ticks_HI, ticks_LO = struct.unpack('<II', buf)
    ticks = (ticks_HI << 32) + ticks_LO
    return ticks / 1000000
    
#######################################################
#  PHYS MEMORY
#######################################################    
    
# ioctl: 9C402540
def phymem_read(addr, size, out_decimal = False):
    _drv = _get_drv()
    if size <= 0:
        raise ValueError(f'Incorrect size argument')
    if not addr:
        raise ValueError()
    addr_HI = SETDIM(addr >> 32, 32)
    addr_LO = SETDIM(addr, 32)
    data = bytearray(size)
    data_addr = get_bytes_addr(data)
    inbuf = struct.pack('<IIIII', addr_HI, addr_LO, size, HIDWORD(data_addr), LODWORD(data_addr))
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_PHYMEM_READ), inbuf, 8, None)
    rc, data_addr_LO = struct.unpack('<II', buf)
    if rc == 0x11111111 or rc == 0x22222222 or rc == 0x33333333:
        return bytes(data) if not out_decimal else int.from_bytes(data, 'little')
    return None

# ioctl: 9C402544
def phymem_cfg_read(bus, dev, fun, offset, size):
    raise RuntimeError('Not implemented')

# ioctl: 9C40254C
def phymem_write_u4(bus, dev, fun, offset, value: int):
    _drv = _get_drv()
    dev_fun = (SETDIM(dev, 5) << 3) | SETDIM(fun, 3)
    inbuf = struct.pack('<BBBBII', 0, dev_fun, bus, 0, offset, value)
    # BusDataType = PCIConfiguration = 4
    # BusNumber = bus
    # SlotNumber = (SETDIM(fun, 3) << 5) | SETDIM(dev, 5)
    # Buffer = 
    # Offset = 0xF0
    # Length = 8
    # mem_addr = HalGetBusDataByOffset(BUS_DATA_TYPE BusDataType, ULONG BusNumber, ULONG SlotNumber, PVOID Buffer, ULONG Offset, ULONG Length);
    # phy_addr = mem_addr & 0xFFFFC000
    # addr = phy_addr + offset
    # *addr = value 
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_PHYMEM_WRITE_U4), inbuf, 4, None)
    (rc, ) = struct.unpack('<I', buf)
    if rc == 0xAAAAAAAAA or rc == 0xCCCCCCCC:
        return False
    return True

# ioctl: 9C402550
def phymem_map(phy_addr, size):
    _drv = _get_drv()
    addr_HI = SETDIM(phy_addr >> 32, 32)
    addr_LO = SETDIM(phy_addr, 32)
    inbuf = struct.pack('<III', addr_HI, addr_LO, size)
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_PHYMEM_MAP), inbuf, 8, None)
    (map_addr, ) = struct.unpack('<Q', buf)
    if map_addr == 0:
        return None
    return map_addr

# ioctl: 9C402554
def phymem_unmap(phy_addr, size):
    _drv = _get_drv()
    addr_HI = SETDIM(phy_addr >> 32, 32)
    addr_LO = SETDIM(phy_addr, 32)
    inbuf = struct.pack('<III', addr_HI, addr_LO, size)
    buf = DeviceIoControl(_drv, IOCTL(CPUZ_PHYMEM_UNMAP), inbuf, 8, None)
    (rc0, rc1) = struct.unpack('<II', buf)
    if rc0 == 0x12345678 and rc1 == 0x87654321:
        return True
    return False

    