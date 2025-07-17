import os
import sys
import time
import struct
import ctypes as ct
import ctypes.wintypes as wintypes


PCI_VENDOR_ID_INTEL = 0x8086
PCI_VENDOR_ID_AMD   = 0x7808

INTEL_ALDERLAKE           = 0x97   # 12th gen
INTEL_ALDERLAKE_L         = 0x9A   # 12th gen
INTEL_RAPTORLAKE          = 0xB7   # 13th gen
INTEL_RAPTORLAKE_P        = 0xBA   #
INTEL_RAPTORLAKE_S        = 0xBF   # 14th gen
INTEL_BARTLETTLAKE        = 0xD7   # Raptor Cove
INTEL_METEORLAKE          = 0xAC   # Redwood Cove / Crestmont
INTEL_METEORLAKE_L        = 0xAA   #
INTEL_ARROWLAKE_H         = 0xC5   # Lion Cove / Skymont
INTEL_ARROWLAKE           = 0xC6
INTEL_ARROWLAKE_U         = 0xB5
INTEL_LUNARLAKE_M         = 0xBD   # Lion Cove / Skymont
INTEL_PANTHERLAKE_L       = 0xCC   # Crestmont

i12_CPU = [ INTEL_ALDERLAKE, INTEL_ALDERLAKE_L ]
i13_CPU = [ INTEL_RAPTORLAKE, INTEL_RAPTORLAKE_P ]
i14_CPU = [ INTEL_RAPTORLAKE_S, INTEL_METEORLAKE, INTEL_METEORLAKE_L ]
i15_CPU = [ INTEL_ARROWLAKE, INTEL_ARROWLAKE_H, INTEL_ARROWLAKE_U ]

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
    0x7f23: {'name': 'INTEL_METEOR_LAKE_PCH_S_SMBUS' },
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
i14_SMBUS = [ getpidsmb('RAPTOR_LAKE_S'), getpidsmb('METEOR_LAKE_P'), getpidsmb('METEOR_LAKE_PCH_S'), getpidsmb('METEOR_LAKE_SOC_S') ]
i15_SMBUS = [ getpidsmb('ARROW_LAKE_H') ]

