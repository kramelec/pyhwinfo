#
# Copyright (C) 2025 remittor
#

import os
import sys
import json
import struct
import ctypes as ct
import ctypes.wintypes as wintypes

from cpuidsdk64.win32 import *

from jep106 import *

def spd_eeprom_decode(data):
    if isinstance(data, str):
        data = bytes.fromhex(data)
    out = { }
    usedBytes = get_bits(data, 0, 0, 3)
    out['UsedBytes']  = 128 * (1 << usedBytes) if usedBytes else 0
    totalBytes = get_bits(data, 0, 4, 6)
    out['TotalBytes'] = 128 * (1 << totalBytes) if totalBytes else 0
    out['CRC'] = get_bits(data, 0, 7) 
    out['revision'] = str(get_bits(data, 1, 4, 7)) + '.' + str(get_bits(data, 1, 0, 3))
    ram_type = get_bits(data, 2, 0, 7)
    if ram_type == 0x0B:
        out['ram_type'] = 'DDR3'
    elif ram_type == 0x0C:
        out['ram_type'] = 'DDR4'
    elif ram_type == 0x12:
        out['ram_type'] = 'DDR5'
    elif ram_type == 0x13:
        out['ram_type'] = 'LPDDR5'
    else:
        out['ram_type'] = ''
    mod_type = get_bits(data, 3, 0, 3)
    if mod_type == 0x02:
        out['mod_type'] = 'UDIMM'
    elif mod_type == 0x03:
        out['mod_type'] = 'SODIMM'
    elif mod_type == 0X0B:
        out['mod_type'] = 'LRDIMM'
    else:
        out['mod_type'] = ''
    
    pkg_list = out['pkg'] = [ ]
    for pkg_num in [ 0, 1 ]:
        x = 4 + pkg_num * 4
        pkg = { 'number': pkg_num }
        pkg_list.append( pkg )
        die_cap = get_bits(data, x, 0, 4)
        die_size_list = [ None, 4, 8, 12, 16, 24, 32, 48, 64 ]
        pkg['die_size'] = die_size_list[die_cap] if die_cap < len(die_size_list) else None
        die_per_pkg = get_bits(data, x, 5, 7)
        if die_per_pkg == 0x00:
            pkg['die_per_pkg'] = 'MONO'  # Monoliphic
        elif die_per_pkg == 0x01:
            pkg['die_per_pkg'] = 'DDP'   # Dual Die Package
        elif die_per_pkg == 0x02:
            pkg['die_per_pkg'] = '2H 3DS'
        elif die_per_pkg == 0x03:
            pkg['die_per_pkg'] = '4H 3DS'
        elif die_per_pkg == 0x04:
            pkg['die_per_pkg'] = '8H 3DS'
        elif die_per_pkg == 0x05:
            pkg['die_per_pkg'] = '16H 3DS'
        else:
            pkg['die_per_pkg'] = None
        pkg['rows'] = 16 + get_bits(data, x+1, 0, 4)
        pkg['columns'] = 10 + get_bits(data, x+1, 5, 7)
        width = get_bits(data, x+2, 5, 7)
        pkg['width'] = 4 * (1 << width)
        bank_grp = get_bits(data, x+3, 0, 2)
        pkg['banks_per_banks_group'] = 1 << bank_grp   # banks per bank group
        bank_grp = get_bits(data, x+3, 5, 7)
        pkg['bank_groups'] = 1 << bank_grp   # bank groups

    out['spd_revision']  = str(get_bits(data, 192, 4, 7)) + '.' + str(get_bits(data, 1, 0, 3))
    out['spd_vendorid'] = jep106decode(get_bits(data, 194, 0, 15))
    out['spd_vendor'] = jep106[out['spd_vendorid']] if out['spd_vendorid'] in jep106 else None
    out['spd_dev_type']  = get_bits(data, 196, 0, 7)
    out['spd_dev_rev']   = get_bits(data, 197, 0, 7)
    
    pmic_list = out['pmic'] = [ ]
    for pmic_num in [ 0, 1, 2 ]:
        x = 198 + pmic_num * 4
        pmic = { 'number': pmic_num }
        pmic_list.append( pmic )
        pmic['vendorid'] = jep106decode(get_bits(data, x, 0, 15))
        pmic['vendor'] = jep106[pmic['vendorid']] if pmic['vendorid'] in jep106 else None
        pmic['dev_type'] = get_bits(data, x+2, 0, 7)
        pmic['dev_rev']  = get_bits(data, x+3, 0, 7)

    out['ranks'] = get_bits(data, 234, 3, 5) + 1
    out['rank_mix'] = 'asymmetrical' if get_bits(data, 234, 6) else 'symmetrical'
    
    out['vendorid'] = jep106decode(get_bits(data, 512, 0, 15))
    out['vendor'] = jep106[out['vendorid']] if out['vendorid'] in jep106 else None
    out['manuf_date'] = get_bits(data, 515, 0, 15)
    out['serial_number'] = data[517:517+2].hex().upper() + '-' + data[519:519+2].hex().upper()
    out['part_number'] = data[521:551].decode('latin-1').strip()
    out['module_rev'] = get_bits(data, 551, 0, 7)
    out['die_vendorid'] = jep106decode(get_bits(data, 552, 0, 15))
    out['die_vendor'] = jep106[out['die_vendorid']] if out['die_vendorid'] in jep106 else None
    out['die_stepping'] = get_bits(data, 554, 0, 7)
    
    return out


if __name__ == "__main__":
    with open('DIMM.json', 'r', encoding='utf-8') as file:
        dimm_info = json.load(file)
    dimm_num = 0
    dimm = dimm_info['DIMM'][dimm_num]
    eeprom = dimm['spd_eeprom']
    out = spd_eeprom_decode(eeprom)
    #print(json.dumps(out, indent=4))
    with open(f'SPD_dimm{dimm_num}.json', 'w') as file:
        json.dump(out, file, indent = 4)
