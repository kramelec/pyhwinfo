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
import enum

__author__ = 'remittor'

from cpuid import CPUID as CPUID_BASE
from cpuidsdk64 import *
from hardware import *

gcpuid = None    # int
gcpuinfo = None  # dict
g_CPUID = None   # class

def get_cpu_id(full = False):
    global g_CPUID
    eax, ebx, ecx, edx = g_CPUID(1)
    stepping = eax & 0xF
    model = (eax >> 4) & 0xF
    family = (eax >> 8) & 0xF
    extModel = (eax >> 16) & 0xF
    extFamily = (eax >> 20) & 0xFF
    cpu_family = family if family != 0xF else family + extFamily
    cpu_model = model if family != 0x6 and family != 0xF else model + (extModel << 4)
    cpu_id = (cpu_family << 8) | cpu_model
    if not full:
        return cpu_id
    else:
        return cpu_id, stepping

def get_cpu_vendor():
    global g_CPUID
    eax, ebx, ecx, edx = g_CPUID(0)
    return struct.pack("III", ebx, edx, ecx).decode("utf-8")

def get_cpu_name():
    global g_CPUID
    name = ''
    for code in range(2, 5):
        eax, ebx, ecx, edx = g_CPUID(0x80000000 + code)
        name += struct.pack("IIII", eax, ebx, ecx, edx).decode("utf-8")
    return name.split('\x00', 1)[0]

def get_cpu_info(log = False):
    cpu = { }
    cpu_id, stepping = get_cpu_id(full = True)
    cpu['family'] = cpu_id >> 8
    cpu['model_id'] = cpu_id & 0xFF
    cpu['stepping'] = stepping
    name = get_cpu_name()
    if not name:
        cpu['name'] = None
    else:
        cpu['name'] = name.replace('(R)', '').replace('(TM)', '').replace('  ', ' ').strip()
    if log:
        print(f'CPU name: "{cpu["name"]}"', '   CPU ID: %02X:%02X:%02X ' % (cpu['family'], cpu['model_id'], cpu['stepping']))
    return cpu

if not g_CPUID:
    g_CPUID = CPUID_BASE()

if not gcpuid:
    gcpuid = get_cpu_id()

if not gcpuinfo:
    gcpuinfo = get_cpu_info(log = False)

if __name__ == "__main__":
    cpu_id = get_cpu_id()
    print(f'cpu_id = 0x{cpu_id:04X}')
    cpu_vnd = get_cpu_vendor()
    print(f'cpu_vnd = "{cpu_vnd}"')
    cpu_name = get_cpu_name()
    print(f'cpu_name = "{cpu_name}"')
    get_cpu_info(log = True)
    