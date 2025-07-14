#
# Copyright (C) 2025 remittor
#

import sys
import json
import types
import math

import tkinter as tk
from tkinter import ttk
from tkextrafont import load_extrafont

from hardware import *
from memory import *

__author__ = 'remittor'

from version import appver
win_caption = f"pyhwinfo v{appver} - memory info"

class WinVar(tk.Variable):
    _default = ""   # Value holder for strings variables

    def __init__(self, value, name = None, root = None):
        master = root if root else None
        value = self.value_to_str(value)
        tk.Variable.__init__(self, master, value, name)
        if value is not None:
            self._default = str(value)

    def value_to_str(self, value):
        if isinstance(value, float) and math.isnan(value):
            return ''
        if isinstance(value, float):
            return str(round(value, 2))
        return str(value)

    def set(self, value):
        value = str(value)
        return self._tk.globalsetvar(self._name, value)

    def get(self):
        value = self._tk.globalgetvar(self._name)
        if isinstance(value, str):
            return value
        return str(value)
        
    @property
    def value(self): 
        return self.get()

    @value.setter 
    def value(self, val): 
        self.set(val)

class WindowMemory():
    def __init__(self):
        global win_caption
        self.root = tk.Tk()
        load_extrafont(self.root)
        self.root.title(win_caption)
        self.root.resizable(False, False)
        self.init_styles()
        self.vars = types.SimpleNamespace()
        self.test = False
        self.sdk_inited = False
        self.mem_info = None
        
    def init_styles(self):
        self.root.load_font("styles/IntelOneMono-Medium.ttf")
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Segoe UI', 10))
        style.configure("TRadiobutton", font=('Segoe UI', 10))
        style.configure('Section.TLabelframe.Label', font=('Segoe UI', 9))
        style.configure('Value.TLabel', font=('Consolas', 10))
        style.configure('val.TLabel', font=('Consolas', 10), padding=1, background="white", foreground="black", relief="groove", borderwidth=2)
        style.configure('Small.TLabel', font=('Consolas', 8))

        style.configure('fixT.TLabel', font=('Intel One Mono Medium', 10), padding=0)
        style.configure('fixV.TLabel', font=('Intel One Mono Medium', 10), padding=0, background="white", foreground="black", relief="groove", borderwidth=2)
        style.configure('fixV2.TLabel', font=('Segoe UI', 10), padding=0, background="white", foreground="black", relief="groove", borderwidth=2)
        style.configure('fixA.TLabel', font=('Intel One Mono Medium', 8))

    def create_window(self):
        vv = self.vars
        mem = None
        if self.mem_info:
            mem = self.mem_info['memory']

        self.dimm_count = 4

        # Main container
        main_frame = ttk.Frame(self.root, padding=(10, 3))
        main_frame.pack(fill=tk.BOTH, expand=True)

        cpu_frame = ttk.Frame(main_frame)
        cpu_frame.pack(fill=tk.X, pady=1)
        ttk.Label(cpu_frame, text="CPU:", style='Title.TLabel').pack(side=tk.LEFT, padx = 5, pady = 1)
        vv.cpu_name = WinVar('?????????')
        cpu_label = ttk.Label(cpu_frame, textvariable=vv.cpu_name, style='Title.TLabel')
        cpu_label.pack(side=tk.LEFT, padx = 5, pady = 1)
        
        mboard_frame = ttk.Frame(main_frame)
        mboard_frame.pack(fill=tk.X, pady=1)
        ttk.Label(mboard_frame, text="Motherboard:", style='Title.TLabel').pack(side=tk.LEFT, padx = 5, pady = 1)
        vv.mb_name = WinVar('?????????')
        if False:
            mb = get_motherboard_info()
            vv.mb_name.value = mb['manufacturer'] + ' ' + mb['product']
        mb_label = ttk.Label(mboard_frame, textvariable=vv.mb_name, style='Title.TLabel')
        mb_label.pack(side=tk.LEFT, padx = 5, pady = 1)
        
        dimm_frame = ttk.LabelFrame(main_frame, text="DIMM", style='Section.TLabelframe')
        dimm_frame.pack(fill=tk.X, pady=3)
        
        dimm_frame2 = ttk.Frame(dimm_frame)
        dimm_frame2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        vv.dimm_radio = tk.StringVar()
        vv.dram_model_list = [ ]
        vv.die_vendor_list = [ ]
        
        def create_dimm(dnum, size, model, mc, ch, die, w = 0, anchor = 'center'):
            nonlocal vv, dimm_frame2
            slot = 'Slot ' + str(dnum)
            size = f'{size} GB' if size else ''
            model_t = 'Model' if size else ''
            model = str(model) if size else ''
            mc_t = 'MC' if size else ''
            mc = str(mc) if size else ''
            ch_t = 'CH' if size else ''
            ch = str(ch) if size else ''
            die_t = 'DIE' if size else ''
            die = str(die) if size else ''
            vstyle = 'fixV.TLabel' if size else 'Title.TLabel'
            vstyle2 = 'fixV2.TLabel' if size else 'Title.TLabel'
            vstyle3 = 'val.TLabel' if size else 'Title.TLabel'
            frame = ttk.Frame(dimm_frame2)
            frame.pack(fill=tk.X, pady=1)
            radio_btn = tk.Radiobutton(frame, text=slot, variable=vv.dimm_radio, value=str(dnum), command=self.on_radio_select)
            radio_btn.pack(side=tk.LEFT)
            if not size:
                radio_btn.config(state = tk.DISABLED)
            dram_var = WinVar(model)
            vv.dram_model_list.append( dram_var )
            die_var = WinVar(die)
            vv.die_vendor_list.append( die_var )
            ttk.Label(frame, text=size, style=vstyle, width=6, anchor=anchor).pack(side=tk.LEFT)
            ttk.Label(frame, text=model_t, style='Title.TLabel', width=6, anchor='e').pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=dram_var, style=vstyle2, width=38, anchor='center').pack(side=tk.LEFT)
            ttk.Label(frame, text=mc_t, style='Title.TLabel', width=3, anchor='e').pack(side=tk.LEFT)
            ttk.Label(frame, text=mc, style=vstyle, width=2, anchor=anchor).pack(side=tk.LEFT)
            ttk.Label(frame, text=ch_t, style='Title.TLabel', width=3, anchor='e').pack(side=tk.LEFT)
            ttk.Label(frame, text=ch, style=vstyle, width=2, anchor=anchor).pack(side=tk.LEFT)
            ttk.Label(frame, text=die_t, style='Title.TLabel', width=3, anchor='e').pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=die_var, style=vstyle2, width=15, anchor='center').pack(side=tk.LEFT)
            
        self.dimm_map = { }
        dnum = 0
        for mc in mem['mc']:
            mc_num = mc['controller']
            chlst = [ mc['channels'][0], mc['channels'][1] ]
            for pnum in range(0, 2):
                size = 0
                ch_num_list = [ ]
                ch_tag_list = [ ]
                for cnum, ch in enumerate(chlst):
                    if pnum == 0:
                        tag = 'L' if ch['DIMM_L_MAP'] == 0 else 'S'
                    else:
                        tag = 'S' if ch['DIMM_L_MAP'] == 0 else 'L'
                    sz = ch[f'Dimm_{tag}_Size']
                    if sz > 0:
                        ch_num_list.append(ch['__channel'])
                        ch_tag_list.append(tag)
                        size += sz
                size = size // 2
                self.dimm_map[dnum] = { 'mc': mc_num, 'ch': ch_num_list, 'CH': '?', 'tag': ch_tag_list, 'size': size }
                dnum += 1
        
        self.current_slot = None
        for dnum in range(0, self.dimm_count):
            if dnum not in self.dimm_map:
                break
            mc_num = self.dimm_map[dnum]['mc']
            mc = mem['mc'][mc_num]
            ch_num_list = self.dimm_map[dnum]['ch']
            ch_tag_list = self.dimm_map[dnum]['tag']
            ch_name = ''
            size = self.dimm_map[dnum]['size']
            model = '????????'
            die_name = '???????'
            if size and (len(ch_tag_list) == 1 or (len(ch_tag_list) == 2 and ch_tag_list[0] == ch_tag_list[1] )):
                ch_name = 'A' if ch_tag_list[0] == 'L' else 'B'
            if size and self.current_slot is None:
                self.current_slot = dnum
                self.current_mc = mc_num
                self.current_ch = ch_num_list[0]
            create_dimm(dnum, size, model, mc_num, ch_name, die_name)

        if self.current_slot is not None:
            vv.dimm_radio.set(str(self.current_slot))
        
        dram_ext_frame = ttk.Frame(main_frame)
        dram_ext_frame.pack(fill=tk.X, pady=1)

        ttk.Label(dram_ext_frame, text=' ', style='Title.TLabel', width=2, anchor='e').pack(side=tk.LEFT, fill=tk.X, expand = True)
        
        vv.PMIC_name = WinVar('???????')
        ttk.Label(dram_ext_frame, text='PMIC', style='Title.TLabel', width=5, anchor='e').pack(side=tk.LEFT)
        ttk.Label(dram_ext_frame, textvariable=vv.PMIC_name, style='fixV2.TLabel', width=26, anchor='center').pack(side=tk.LEFT)
        
        freq_volt_frame = ttk.Frame(main_frame)
        freq_volt_frame.pack(fill=tk.X, pady=0)

        freq_chan_frame = ttk.Frame(freq_volt_frame)
        freq_chan_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=3)
        
        # Frequency information
        freq_frame = ttk.LabelFrame(freq_chan_frame, text="Frequency", style='Section.TLabelframe')
        freq_frame.pack(side=tk.TOP, fill=tk.Y, expand=False, padx=5, pady=0)

        def create_freq_col(vlist: list, w, anchor = 'center'):
            nonlocal freq_frame
            col = ttk.Frame(freq_frame)
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=1)
            for value in vlist:
                vstyle = 'fixT.TLabel'
                if isinstance(value, str):
                    vstyle = 'fixT.TLabel'
                    ttk.Label(col, text=value, style=vstyle, width=w, anchor=anchor).pack(fill=tk.X, pady=1)
                else:    
                    vstyle = 'fixV.TLabel'
                    ttk.Label(col, textvariable=value, style=vstyle, width=w, anchor=anchor).pack(fill=tk.X, pady=1)
            
        vv.BCLK = WinVar('???')
        vv.MCLK_RATIO = WinVar('??')
        vv.MCLK_FREQ  = WinVar('???')
        vv.UCLK_RATIO = WinVar('???')
        vv.UCLK_FREQ  = WinVar('???')
        
        create_freq_col([ "", "MCLK", "UCLK" ], w = 5)
        create_freq_col([ "Rate", vv.MCLK_RATIO, vv.UCLK_RATIO ], w = 6)
        create_freq_col([ "", "x", "x" ], w = 1)
        create_freq_col([ "BCLK", vv.BCLK, vv.BCLK ], w = 8)
        create_freq_col([ "", "=", "=" ], w = 1)
        create_freq_col([ "Frequency", vv.MCLK_FREQ, vv.UCLK_FREQ ], w = 10)
        create_freq_col([ "", "MHz", "MHz" ], w = 4, anchor = tk.W)

        # Channel info
        channel_frame = ttk.Frame(freq_chan_frame)
        channel_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False, pady=(3,0))
        
        vv.chan_count = WinVar('?')
        ttk.Label(channel_frame, text="Channels", width=10, anchor='e').pack(side=tk.LEFT)
        ttk.Label(channel_frame, textvariable=vv.chan_count, width=2, style='val.TLabel', anchor='center').pack(side=tk.LEFT, padx=1)
        
        vv.gear_mode = WinVar('?')
        ttk.Label(channel_frame, text="Gear Mode", width=11, anchor='e').pack(side=tk.LEFT)
        ttk.Label(channel_frame, textvariable=vv.gear_mode, width=2, style='val.TLabel', anchor='center').pack(side=tk.LEFT, padx=1)

        vv.mem_freq = WinVar('????')
        ttk.Label(channel_frame, text="Speed", width=7, anchor='e').pack(side=tk.LEFT)
        ttk.Label(channel_frame, textvariable=vv.mem_freq, width=6, style='fixV.TLabel', anchor='center').pack(side=tk.LEFT, padx=1)
        ttk.Label(channel_frame, text="MT/s", width=5, anchor='w').pack(side=tk.LEFT)
        
        # Sensors info
        sens_frame = ttk.LabelFrame(freq_volt_frame, text="DIMM Sensors", style='Section.TLabelframe')
        sens_frame.pack(fill=tk.BOTH, expand=True, pady=0)
        
        def create_sens_val(sframe, name, value, vt, w = 6):
            nonlocal vv
            var = WinVar(value)
            setattr(vv, 'sens_' + name.replace('.', '_'), var)
            frame = ttk.Frame(sframe)
            frame.pack(fill=tk.X, pady=1)
            ttk.Label(frame, text=name, width=w, style='fixT.TLabel', anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=var, width=7, style='fixV.TLabel', anchor='center').pack(side=tk.LEFT)
            if vt:
                ttk.Label(frame, text=vt, width=2, style='Title.TLabel', anchor='w').pack(side=tk.LEFT)
            
        sensA = ttk.Frame(sens_frame)
        sensA.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        create_sens_val(sensA, 'VDD',  '?????', 'V')
        create_sens_val(sensA, 'VDDQ', '?????', 'V')
        create_sens_val(sensA, 'VPP',  '?????', 'V')
        create_sens_val(sensA, 'VIN',  '?????', 'V')

        sensB = ttk.Frame(sens_frame)
        sensB.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        create_sens_val(sensB, 'Temp', '?????', '°C')
        create_sens_val(sensB, '1.8V', '?????', 'V')
        create_sens_val(sensB, '1.0V', '?????', 'V')

        # Mem Cotroller Settings
        ctrl_frame = ttk.LabelFrame(main_frame, text="MC/PCH Settings", style='Section.TLabelframe')
        ctrl_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        def create_col_ctrl(elems, wn = 8, wv = 4):
            nonlocal vv, ctrl_frame
            col = ttk.Frame(ctrl_frame)
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
            for name, value in elems:
                vt = None
                if value.startswith('@'):
                    vt = value[1:]
                    value = '??'
                if name == '':
                    var = value
                else:
                    var = WinVar(value)
                    var_name = name
                    if name == 'VDDQ_TX' and vt == 'A':
                        var_name += '_ICCMAX'
                    setattr(vv, var_name, var)
                frame = ttk.Frame(col)
                frame.pack(fill=tk.X, pady=1)
                ttk.Label(frame, text=name, style='fixT.TLabel', width=wn, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(frame, textvariable=var, style='fixV.TLabel', width=wv, anchor='center').pack(side=tk.LEFT)
                if vt:
                    ttk.Label(frame, text=vt, width=len(vt)+1, style='Title.TLabel', anchor='w').pack(side=tk.LEFT)

        elems = [
            ( "DDR_OVERCLOCK", '??' ),
            ( "TIMING_RUNTIME_OC", '??' ),
        ]
        create_col_ctrl(elems, wn = 17)
        elems = [
            ( "BCLK_OC", '??' ),
            ( "OC_ENABLED", '??' ),
        ]
        create_col_ctrl(elems, wn = 10)
        elems = [
            ( "SA_VOLTAGE", '@V' ),
            ( "POWER_LIMIT", '??' ),     # On / Off
        ]
        create_col_ctrl(elems, wn = 11, wv = 7)
        elems = [
            ( "VDDQ_TX", '@V' ),
            ( "VDDQ_TX", '@A' ),
        ]
        create_col_ctrl(elems, wn = 7, wv = 7)
        
        # Main timings section
        timings_frame = ttk.LabelFrame(main_frame, text="Timings", style='Section.TLabelframe')
        timings_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        base_timings_frame = ttk.Frame(timings_frame)
        base_timings_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        def create_mc_ch_combo(col, width = 8):
            nonlocal vv, mem
            frame = ttk.Frame(col)
            frame.pack(fill=tk.X, pady=2)
            item_active = 0
            options = [ ]
            for mc in mem['mc']:
                mc_num = mc['controller']
                for ch in mc['channels']:
                    ch_num = ch['__channel']
                    options.append( f'MC #{mc_num}, CH #{ch_num}' )
                    if mc_num == self.current_mc and ch_num == self.current_ch:
                        item_active = len(options) - 1
            vv.mc_ch_combobox = ttk.Combobox(frame, values=options, width = width + 2)
            vv.mc_ch_combobox.pack(side=tk.LEFT, padx = 1)
            vv.mc_ch_combobox.current(item_active)
            vv.mc_ch_combobox.pack()
            vv.mc_ch_combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)
        
        def create_col_timings(tlist, wn = 8, wv = 5, frame = None):
            nonlocal vv, base_timings_frame
            if not frame:
                frame = base_timings_frame
            col = ttk.Frame(frame)
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            for item in tlist:
                value = ''
                if isinstance(item, str):
                    name = item
                else:
                    name, value = item
                if name == '__combobox':
                    create_mc_ch_combo(col, wn + wv)
                    continue
                var = WinVar(value)
                setattr(vv, name, var)
                _wn = wn
                _wv = wv
                if name == 'tREFI':
                    _wn = 6
                    _wv = 7
                if name == 'RTL':
                    _wn = 3
                    _wv = 12
                frame = ttk.Frame(col)
                frame.pack(fill=tk.X, pady=1)
                ttk.Label(frame, text=name, style='fixT.TLabel', width=_wn, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(frame, textvariable=var, style='fixV.TLabel', width=_wv, anchor='center').pack(side=tk.LEFT)

        col_timings = [
            ( "__combobox", "" ),
            ( "tCL",    '??' ),
            ( "tRCD",   '??' ),
            ( "tRCDW",  ''   ),
            ( "tRP",    '??' ),
            ( "tRAS",   '??' ),
            ( "tRC",    '??' ),
        ]
        create_col_timings(col_timings, wn = 7)
        
        col_timings = [
            ( "tCR",    '??' ),
            ( "tCWL",   '??' ),
            ( "tRFC",   '??' ),
            ( "tRFC2",  ''   ),
            ( "tRFCpb", '??' ),
            ( "tXSR",   '??' ),
            ( "tREFI",  '??' ),
        ]
        create_col_timings(col_timings)
        
        col_timings = [
            ( "tFAW",    '??' ),
            ( "tRRD_L",  '??' ),
            ( "tRRD_S",  '??' ),
            ( "tRDPRE",  '??' ),
            ( "tRDPDEN", '??' ),
            ( "tRTP",    '??' ),
            ( "tREFIx9", '??' ),
        ]
        create_col_timings(col_timings)
        
        col_timings = [
            ( "tWR",     '??' ),
            ( "tWTR_L",  '??' ),
            ( "tWTR_S",  '??' ),
            ( "tWRPRE",  '??' ),
            ( "tWRPDEN", '??' ),
            ( "tWTP",    ''   ),
            ( "tREFSBRD", '??' ),
        ]
        create_col_timings(col_timings)

        col_timings = [
            ( "tCKE",    '??' ),
            ( "tCPDED",  '??' ),
            ( "tXP",     '??' ),
            ( "tXPDLL",  '??' ),
            ( "tXSDLL",  '??' ),
            ( "tPRPDEN", ''   ),
            ( "RTL",     '??/??/??/??' ),
        ]
        create_col_timings(col_timings, wv = 6)
        
        adv_frame = ttk.Frame(timings_frame)
        adv_frame.pack(fill=tk.BOTH, expand=True, pady=7, padx=3)

        def create_adv_timings(tlist, caption, wn = 9, wv = 5):
            nonlocal vv, adv_frame
            col = ttk.LabelFrame(adv_frame, text=caption, style='Section.TLabelframe')
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            for name, value in tlist:
                if name == '' or not name.startswith('t'):
                    var = str(value)
                else:
                    var = WinVar(value)
                    setattr(vv, name, var)
                _wn = wn
                _wv = wv
                frame = ttk.Frame(col)
                frame.pack(fill=tk.X, pady=1)
                ttk.Label(frame, text=name, style='fixT.TLabel', width=_wn, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(frame, textvariable=var,  style='fixV.TLabel', width=_wv, anchor='center').pack(side=tk.LEFT)

        adv_timings = [
            ( "tRDRD_sg", '??' ),
            ( "tRDWR_sg", '??' ),
            ( "tWRRD_sg", '??' ),
            ( "tWRWR_sg", '??' ),
        ]
        create_adv_timings(adv_timings, "Same Bank Group")
        adv_timings = [
            ( "tRDRD_dg", '??' ),
            ( "tRDWR_dg", '??' ),
            ( "tWRRD_dg", '??' ),
            ( "tWRWR_dg", '??' ),
        ]
        create_adv_timings(adv_timings, "Different Bank Group")
        adv_timings = [
            ( "tRDRD_dr", '??' ),
            ( "tRDWR_dr", '??' ),
            ( "tWRRD_dr", '??' ),
            ( "tWRWR_dr", '??' ),
        ]
        create_adv_timings(adv_timings, "Same DIMM")
        adv_timings = [
            ( "tRDRD_dd", '??' ),
            ( "tRDWR_dd", '??' ),
            ( "tWRRD_dd", '??' ),
            ( "tWRWR_dd", '??' ),
        ]
        create_adv_timings(adv_timings, "Different DIMM")

        ext_timings_frame = ttk.Frame(timings_frame)
        ext_timings_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        col_timings = [ "DEC_tCWL", "ADD_tCWL", "tPPD", ]
        create_col_timings(col_timings, wn = 8, frame = ext_timings_frame)

        col_timings = [ "tCSL", "tCSH", "tRFM", ]
        create_col_timings(col_timings, wn = 5, frame = ext_timings_frame)

        col_timings = [ "oref_ri", "tZQOPER", "tMOD", ]
        create_col_timings(col_timings, wn = 7, frame = ext_timings_frame)

        col_timings = [ "X8_DEVICE" , "N_TO_1_RATIO", "ADD_1QCLK_DELAY", ]
        create_col_timings(col_timings, wn = 15, frame = ext_timings_frame)

        # ODT section
        odt_frame = ttk.Frame(timings_frame)
        odt_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        odt_rtt_frame = ttk.LabelFrame(odt_frame, text="ODT Rtt", style='Section.TLabelframe')
        odt_rtt_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2, padx=3)

        odt_cxA_frame = ttk.LabelFrame(odt_frame, text="ODT Cfg Group A", style='Section.TLabelframe')
        odt_cxA_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2, padx=3)

        odt_cxB_frame = ttk.LabelFrame(odt_frame, text="ODT Cfg Group B", style='Section.TLabelframe')
        odt_cxB_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2, padx=3)

        def create_odt_val(frame, group, tlist, wn = 8, wv = 4):
            nonlocal vv
            col = ttk.Frame(frame)
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            for name in tlist:
                vvname = 'ODT_' + name
                if group:
                    vvname += f'_{group}'
                var0 = WinVar('')
                setattr(vv, vvname + '__0', var0)
                var1 = WinVar('')
                setattr(vv, vvname + '__1', var1)
                _wn = wn
                _wv = wv
                frame = ttk.Frame(col)
                frame.pack(fill=tk.X, pady=1)
                ttk.Label(frame, text=name, style='fixT.TLabel', width=_wn, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(frame, textvariable=var0,  style='fixV.TLabel', width=_wv, anchor='center').pack(side=tk.LEFT)
                if name != 'Loopback':
                    ttk.Label(frame, textvariable=var1,  style='fixV.TLabel', width=_wv, anchor='center').pack(side=tk.LEFT)

        create_odt_val(odt_rtt_frame, None, [ "Wr", "Park", "ParkDqs" ], wn = 7 )
        create_odt_val(odt_rtt_frame, None, [ "NomRd", "NomWr", "Loopback" ], wn = 8 )
        create_odt_val(odt_cxA_frame, 'A', [ "CA", "CS", "CK" ], wn = 3 )
        create_odt_val(odt_cxB_frame, 'B', [ "CA", "CS", "CK" ], wn = 3 )

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=3)

        btn_dump = ttk.Button(btn_frame, text="Dump to file", command = self.button_click_dump)
        btn_dump.pack(side=tk.LEFT)

        btn_refresh = ttk.Button(btn_frame, text="Refresh", command = self.button_click_refresh)
        btn_refresh.pack(side=tk.RIGHT)

    def update(self, slot_id = None, mc_id = None, ch_id = None):
        vv = self.vars
        if slot_id is None:
            slot_id = self.current_slot
        if mc_id is None:
            mc_id = self.current_mc
        if ch_id is None:
            ch_id = self.current_ch
        cap = self.mem_info['CAP']
        mem = self.mem_info['memory']
        dimm = None
        for elem in self.mem_info['memory']['DIMM']:
            if elem['slot'] == slot_id:
                dimm = elem
                break
        
        if not dimm:
            raise RuntimeError(f'slot = {slot_id}')
        
        pmic = dimm['PMIC'] if dimm and 'PMIC' in dimm else None
        
        vv.cpu_name.value = self.mem_info['cpu']['name']
        board = self.mem_info['board']
        vv.mb_name.value = board['manufacturer'] + ' ' + board['product']

        for elem in vv.dram_model_list:
            elem.set('')
        
        for elem in vv.die_vendor_list:
            elem.set('')
        
        cur_dimm = None
        slot_count = 0
        for elem in self.mem_info['memory']['DIMM']:
            slot = elem['slot']
            if slot == slot_id:
                cur_dimm = elem
            slot_count += 1
            spd = elem['SPD'] if 'SPD' in elem else None
            if spd:
                vendor = spd['vendor']
                if not vendor:
                    vendor = '0x%04X' % spd['vendorid']
                ranks = '  (' + str(spd['ranks']) + 'R)'
                vv.dram_model_list[slot].value = vendor + '  ' + spd['part_number'] + ranks
            if spd and 'die_vendorid' in spd and spd['die_vendorid']:
                vendor = spd['die_vendor'] if 'die_vendor' in spd else None
                if not vendor:
                    vendor = '0x%04X' % spd['die_vendorid']
                if 'die_stepping' in spd:
                    vendor += f' [0x{spd["die_vendorid"]:02X}]'
                vv.die_vendor_list[slot].value = vendor
        
        vv.PMIC_name.value = ''
        if cur_dimm and 'PMIC' in cur_dimm and cur_dimm['PMIC']:
            vendor = cur_dimm['PMIC']['vendor']
            if not vendor:
                vendor = '0x%04X' % cur_dimm['PMIC']['vid']
            vv.PMIC_name.value = vendor
        
        vv.BCLK.value = mem['BCLK_FREQ']
        vv.MCLK_RATIO.value = mem['SA']['QCLK_RATIO']
        vv.MCLK_FREQ.value  = mem['SA']['QCLK']
        vv.UCLK_RATIO.value = mem['SA']['UCLK_RATIO']
        vv.UCLK_FREQ.value  = mem['SA']['UCLK']
        if mem['mc'][0]['DDR_ver'] == 5:
            max_chan_count = len(mem['mc']) * len(mem['mc'][0]['channels'])
            chan_count = 0
            for mc in mem['mc']:
                for ch in mc['channels']:
                    if ch['Dimm_L_Size'] > 0 or ch['Dimm_S_Size'] > 0:
                        chan_count += 1
            if chan_count > max_chan_count:
                chan_count = max_chan_count
            vv.chan_count.value = chan_count
        else:
            vv.chan_count.value = '?'
        
        vv.gear_mode.value = mem['GEAR']
        vv.mem_freq.value = int(float(vv.MCLK_FREQ.value) * 2)
        if mem['BCLK_FREQ'] > 98 and mem['BCLK_FREQ'] < 105:
            vv.mem_freq.value = mem['SA']['QCLK_RATIO'] * 100 * 2
        if pmic:
            vv.sens_VDD.value = pmic['SWA']
            vv.sens_VDDQ.value = pmic['SWC']
            vv.sens_VPP.value = pmic['SWD']
            vv.sens_VIN.value = pmic['VIN']
            vv.sens_1_8V.value = pmic['1.8V']
            vv.sens_1_0V.value = pmic['1.0V']
        else:
            vv.sens_VDD.value = ''
            vv.sens_VDDQ.value = ''
            vv.sens_VPP.value = ''
            vv.sens_VIN.value = ''
            vv.sens_1_8V.value = ''
            vv.sens_1_0V.value = ''
        if dimm and 'temp' in dimm:
            vv.sens_Temp.value = dimm['temp']
        else:
            vv.sens_Temp.value = ''
        vv.DDR_OVERCLOCK.value = 'ON' if cap['DDR_OVERCLOCK'] else 'off'
        vv.TIMING_RUNTIME_OC.value = 'ON' if mem['MC_TIMING_RUNTIME_OC_ENABLED'] else 'off'
        vv.BCLK_OC.value = 'ON' if cap['BCLKOCRANGE'] == 3 else 'off'
        vv.OC_ENABLED.value = 'ON' if cap['OC_ENABLED'] else 'off'
        vv.SA_VOLTAGE.value = mem['SA']['SA_VOLTAGE']
        vv.POWER_LIMIT.value = 'ON' if mem['POWER']['limits_LOCKED'] != 0 else 'off'
        vv.VDDQ_TX.value = mem['REQ_VDDQ_TX_VOLTAGE']
        vv.VDDQ_TX_ICCMAX.value = mem['REQ_VDDQ_TX_ICCMAX']
        
        chan = mem['mc'][mc_id]['channels'][ch_id]
        ci = chan['info']
        vv.tCL.value = ci['tCL']
        vv.tRCD.value = ci['tRCD']
        vv.tRCDW.value = ci['tRCDW'] if 'tRCDW' in ci else ''
        vv.tRP.value = ci['tRP']
        vv.tRAS.value = ci['tRAS']
        vv.tRC.value = ci['tRAS'] + ci['tRP']
        vv.tCR.value = ci['tCR']
        vv.tCWL.value = ci['tCWL']
        vv.tRFC.value = ci['tRFC'] if ci['tRFC'] else ''
        vv.tRFC2.value = ci['tRFC2'] if ci['tRFC2'] else ''
        vv.tRFCpb.value = ci['tRFCpb']
        vv.tXSR.value = ci['tXSR']
        vv.tREFI.value = ci['tREFI']
        vv.tFAW.value = ci['tFAW']
        vv.tRRD_L.value = ci['tRRD_L']
        vv.tRRD_S.value = ci['tRRD_S']
        vv.tRDPRE.value = ci['tRDPRE']
        vv.tRDPDEN.value = ci['tRDPDEN']
        vv.tRTP.value = ci['tRTP']
        vv.tREFIx9.value = ci['tREFIx9']
        vv.tWR.value = ci['tWR']
        vv.tWTR_L.value = ci['tWTR_L']
        vv.tWTR_S.value = ci['tWTR_S']
        vv.tWRPRE.value = ci['tWRPRE']
        vv.tWRPDEN.value = ci['tWRPDEN']
        vv.tWTP.value = ''
        vv.tREFSBRD.value = ci['tREFSBRD']
        vv.tCKE.value = ci['tCKE']
        vv.tCPDED.value = ci['tCPDED']
        vv.tXP.value = ci['tXP']
        vv.tXPDLL.value = ci['tXPDLL']
        vv.tXSDLL.value = ci['tXSDLL']
        vv.tPRPDEN.value = ci['tPRPDEN']
        rtl_list = [ '??', '??', '??', '??' ]
        for key, val in ci.items():
            if key.startswith('tRTL_'):
                num = int(key.split('_')[1])
                rtl_list[num] = str(val)
        vv.RTL.value = '/'.join(rtl_list)

        vv.tRDRD_sg.value = ci['tRDRD_sg']
        vv.tRDWR_sg.value = ci['tRDWR_sg']
        vv.tWRRD_sg.value = ci['tWRRD_sg']
        vv.tWRWR_sg.value = ci['tWRWR_sg']
        vv.tRDRD_dg.value = ci['tRDRD_dg']
        vv.tRDWR_dg.value = ci['tRDWR_dg']
        vv.tWRRD_dg.value = ci['tWRRD_dg']
        vv.tWRWR_dg.value = ci['tWRWR_dg']
        vv.tRDRD_dr.value = ci['tRDRD_dr']
        vv.tRDWR_dr.value = ci['tRDWR_dr']
        vv.tWRRD_dr.value = ci['tWRRD_dr']
        vv.tWRWR_dr.value = ci['tWRWR_dr']
        vv.tRDRD_dd.value = ci['tRDRD_dd']
        vv.tRDWR_dd.value = ci['tRDWR_dd']
        vv.tWRRD_dd.value = ci['tWRRD_dd']
        vv.tWRWR_dd.value = ci['tWRWR_dd']

        vv.DEC_tCWL.value = ci['DEC_tCWL']
        vv.ADD_tCWL.value = ci['ADD_tCWL']
        vv.tPPD.value = ci['tPPD']
        vv.tCSL.value = ci['tCSL']
        vv.tCSH.value = ci['tCSH']
        vv.tRFM.value = ci['tRFM']
        vv.oref_ri.value = ci['oref_ri']
        vv.tZQOPER.value = ci['tZQOPER']
        vv.tMOD.value = ci['tMOD']
        vv.X8_DEVICE.value = ci['X8_DEVICE']
        vv.N_TO_1_RATIO.value = ci['N_TO_1_RATIO']
        vv.ADD_1QCLK_DELAY.value = ci['ADD_1QCLK_DELAY']

        def set_odt_val(mrs, mrs_name, name):
            vv = self.vars
            vvname0 = 'ODT_' + name + '__0'
            vvname1 = 'ODT_' + name + '__1'
            try:
                vv0 = getattr(vv, vvname0)
                vv1 = getattr(vv, vvname1)
            except AttributeError:
                return False
            if mrs_name not in mrs:
                vv0.value = ''
                vv1.value = ''
                return False
            if isinstance(mrs[mrs_name], list):
                vv0.value = mrs[mrs_name][0]
                vv1.value = mrs[mrs_name][1]
            else:
                vv0.value = mrs[mrs_name]
                vv1.value = ''
            return True
        
        if 'MRS' in ci and ci['MRS']:
            mrs = ci['MRS']
            set_odt_val(mrs, 'RttWr', "Wr")
            set_odt_val(mrs, 'RttPark', "Park")
            set_odt_val(mrs, 'RttParkDqs', "ParkDqs")
            set_odt_val(mrs, 'RttLoopback', "Loopback")
            set_odt_val(mrs, 'RttNomWr', "NomWr")
            set_odt_val(mrs, 'RttNomRd', "NomRd")
            set_odt_val(mrs, 'RttCK_A', "CK_A")
            set_odt_val(mrs, 'RttCS_A', "CS_A")
            set_odt_val(mrs, 'RttCA_A', "CA_A")
            set_odt_val(mrs, 'RttCK_B', "CK_B")
            set_odt_val(mrs, 'RttCS_B', "CS_B")
            set_odt_val(mrs, 'RttCA_B', "CA_B")

        self.current_slot = slot_id
        self.current_mc = mc_id
        self.current_ch = ch_id
    
    def refresh(self, update = True):
        if update:
            print('Refresh started...')
        self.update_hardware_info()
        if update:
            self.update()
            print('Main window refreshed!')

    def update_hardware_info(self):
        if self.test:
            with open('IMC.json', 'r', encoding='utf-8') as file:
                self.mem_info = json.load(file)
        else:
            from cpuidsdk64 import SdkInit
            from memspd import get_mem_spd_all
            if not self.sdk_inited:
                SdkInit(None, verbose = 0)
                self.sdk_inited = True
            self.mem_info = get_mem_spd_all(None, with_pmic = True, allinone = True)
    
    def button_click_refresh(self):
        print("Button refresh clicked!")
        self.refresh()

    def on_radio_select(self):
        vv = self.vars
        slot = vv.dimm_radio.get()
        print(f"You selected DIMM: {slot}")
        self.current_slot = int(slot)
        self.update(slot_id = int(slot))
        
    def on_combobox_select(self, event):
        vv = self.vars
        selected_value = vv.mc_ch_combobox.get()
        print(f"You selected: {selected_value}")
        xx = selected_value.split(',')
        mc_num = int(xx[0].split('#')[1].strip())
        ch_num = int(xx[1].split('#')[1].strip())
        self.update(slot_id = self.current_slot, mc_id = mc_num, ch_id = ch_num)

    def button_click_dump(self):
        from datetime import datetime
        print("Button Dump clicked!")
        if 'time' in self.mem_info:
            dt = datetime.strptime(self.mem_info['time'], "%Y-%m-%d %H:%M:%S")
            dt = dt.strftime("%Y-%m-%d_%H%M")
        else:
            dt = datetime.now().strftime("%Y-%m-%d_%H%M")
        fn = f'IMC_{dt}.json'
        with open(fn, 'w') as file:
            json.dump(self.mem_info, file, indent = 4)

if __name__ == "__main__":
    test = False
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test = True

    win = WindowMemory()
    win.test = test
    win.update_hardware_info()
    win.create_window()
    win.update()

    win.root.mainloop()

