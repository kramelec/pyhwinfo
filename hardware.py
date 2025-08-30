import os
import sys
import time
import struct
import ctypes as ct
import ctypes.wintypes as wintypes
import enum

PCI_VENDOR_ID_INTEL = 0x8086
PCI_VENDOR_ID_AMD   = 0x7808

class CPUID(enum.IntEnum):   # only for Intel CPU
    def __new__(cls, value, name):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._name_ = name
        return obj
    ALDERLAKE           = 0x0697, 'INTEL_ALDERLAKE'      # 12th gen
    ALDERLAKE_L         = 0x069A, 'INTEL_ALDERLAKE_L'    # 12th gen
    RAPTORLAKE          = 0x06B7, 'INTEL_RAPTORLAKE'     # 13th gen
    RAPTORLAKE_P        = 0x06BA, 'INTEL_RAPTORLAKE_P'   #
    RAPTORLAKE_S        = 0x06BF, 'INTEL_RAPTORLAKE_S'   # 14th gen
    BARTLETTLAKE        = 0x06D7, 'INTEL_BARTLETTLAKE'   # Raptor Cove
    METEORLAKE          = 0x06AC, 'INTEL_METEORLAKE'     # Redwood Cove / Crestmont
    METEORLAKE_L        = 0x06AA, 'INTEL_METEORLAKE_L'   #
    ARROWLAKE_H         = 0x06C5, 'INTEL_ARROWLAKE_H'    # Lion Cove / Skymont
    ARROWLAKE           = 0x06C6, 'INTEL_ARROWLAKE'     
    ARROWLAKE_U         = 0x06B5, 'INTEL_ARROWLAKE_U'   
    LUNARLAKE_M         = 0x06BD, 'INTEL_LUNARLAKE_M'    # Lion Cove / Skymont
    PANTHERLAKE_L       = 0x06CC, 'INTEL_PANTHERLAKE_L'  # Crestmont

i12_CPU = [ CPUID.ALDERLAKE, CPUID.ALDERLAKE_L ]
i13_CPU = [ CPUID.RAPTORLAKE, CPUID.RAPTORLAKE_P ]
i14_CPU = [ CPUID.RAPTORLAKE_S, CPUID.METEORLAKE, CPUID.METEORLAKE_L ]
i15_CPU = [ CPUID.ARROWLAKE, CPUID.ARROWLAKE_H, CPUID.ARROWLAKE_U ]

i12_FAM = i12_CPU + i13_CPU + i14_CPU
i15_FAM = i15_CPU

# ref: https://github.com/torvalds/linux/blob/fb4d33ab452ea254e2c319bac5703d1b56d895bf/drivers/i2c/busses/i2c-i801.c#L240
PCI_ID_SMBUS_INTEL = {
    0x31d4: {'name': 'INTEL_GEMINILAKE_SMBUS' },
    0x34a3: {'name': 'INTEL_ICELAKE_LP_SMBUS' },
    0x38a3: {'name': 'INTEL_ICELAKE_N_SMBUS' },
    0x3b30: {'name': 'INTEL_5_3400_SERIES_SMBUS' },
    0x43a3: {'name': 'INTEL_TIGERLAKE_H_SMBUS' },
    0x4b23: {'name': 'INTEL_ELKHART_LAKE_SMBUS' },
    0x4da3: {'name': 'INTEL_JASPER_LAKE_SMBUS' },
    0x51a3: {'name': 'INTEL_ALDER_LAKE_P_SMBUS' },
    0x54a3: {'name': 'INTEL_ALDER_LAKE_M_SMBUS' },
    0x5796: {'name': 'INTEL_BIRCH_STREAM_SMBUS' },
    0x5ad4: {'name': 'INTEL_BROXTON_SMBUS' },
    0x7722: {'name': 'INTEL_ARROW_LAKE_H_SMBUS' },
    0x7a23: {'name': 'INTEL_RAPTOR_LAKE_S_SMBUS' },
    0x7aa3: {'name': 'INTEL_ALDER_LAKE_S_SMBUS' },
    0x7e22: {'name': 'INTEL_METEOR_LAKE_P_SMBUS' },
#   0x7f23: {'name': 'INTEL_METEOR_LAKE_PCH_S_SMBUS' },  # may be ERROR !!!
    0x7f23: {'name': 'INTEL_ARROW_LAKE_PCH_S_SMBUS' },   # https://github.com/memtest86plus/memtest86plus/blob/2a58a7cb5310d47212fa2790ec7511bb665c005c/system/x86/i2c.c#L177
    0x8c22: {'name': 'INTEL_LYNXPOINT_SMBUS' },
    0x8ca2: {'name': 'INTEL_WILDCATPOINT_SMBUS' },
    0x8d22: {'name': 'INTEL_WELLSBURG_SMBUS' },
    0x8d7d: {'name': 'INTEL_WELLSBURG_SMBUS_MS0' },
    0x8d7e: {'name': 'INTEL_WELLSBURG_SMBUS_MS1' },
    0x8d7f: {'name': 'INTEL_WELLSBURG_SMBUS_MS2' },
    0x9c22: {'name': 'INTEL_LYNXPOINT_LP_SMBUS' },
    0x9ca2: {'name': 'INTEL_WILDCATPOINT_LP_SMBUS' },
    0x9d23: {'name': 'INTEL_SUNRISEPOINT_LP_SMBUS' },
    0x9da3: {'name': 'INTEL_CANNONLAKE_LP_SMBUS' },
    0xa0a3: {'name': 'INTEL_TIGERLAKE_LP_SMBUS' },
    0xa123: {'name': 'INTEL_SUNRISEPOINT_H_SMBUS' },
    0xa1a3: {'name': 'INTEL_LEWISBURG_SMBUS' },
    0xa223: {'name': 'INTEL_LEWISBURG_SSKU_SMBUS' },
    0xa2a3: {'name': 'INTEL_KABYLAKE_PCH_H_SMBUS' },
    0xa323: {'name': 'INTEL_CANNONLAKE_H_SMBUS' },
    0xa3a3: {'name': 'INTEL_COMETLAKE_V_SMBUS' },
    0xae22: {'name': 'INTEL_METEOR_LAKE_SOC_S_SMBUS' },
    0xe322: {'name': 'INTEL_PANTHER_LAKE_H_SMBUS' },
    0xe422: {'name': 'INTEL_PANTHER_LAKE_P_SMBUS' },
}

def getpidsmb(name):
    for pid, desc in PCI_ID_SMBUS_INTEL.items():
        if name in desc['name']:
            return pid
    return None

i12_SMBUS = [ getpidsmb('ALDER_LAKE_P'), getpidsmb('ALDER_LAKE_M'), getpidsmb('ALDER_LAKE_S') ]
i14_SMBUS = [ getpidsmb('RAPTOR_LAKE_S'), getpidsmb('METEOR_LAKE_P'), getpidsmb('METEOR_LAKE_SOC_S') ]
i15_SMBUS = [ getpidsmb('ARROW_LAKE_PCH_S'), getpidsmb('ARROW_LAKE_H') ]

