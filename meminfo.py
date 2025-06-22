import json
import math
import tkinter as tk
from tkinter import ttk

from hardware import *

g_root = None
g_win = None

def create_window_memory(mem_info, dimm_info, dimm_id = 0, mc_id = 0, ch_id = 0):
    global g_root, g_win
    if g_root:
        root = g_root
    else:
        root = tk.Tk()
        root.title("pyhwinfo v0.1 - memory info")
        root.resizable(False, False)
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Segoe UI', 10))
        style.configure('Section.TLabelframe.Label', font=('Segoe UI', 9))
        style.configure('Value.TLabel', font=('Consolas', 10))
        style.configure('val.TLabel', font=('Consolas', 10), padding=2, background="white", foreground="black", relief="groove", borderwidth=2)
        style.configure('Small.TLabel', font=('Consolas', 8))
        style.configure('fixT.TLabel', font=('Fixedsys', 10), padding=2)
        style.configure('fixV.TLabel', font=('Fixedsys', 10), padding=2, background="white", foreground="black", relief="groove", borderwidth=2)
        style.configure('fixA.TLabel', font=('Fixedsys', 8))
        g_root = root

    if g_win:
        g_win.destroy()
        g_win = None
    
    mem = None
    if mem_info:
        mem = mem_info['memory']

    dimm = None
    pmic = None
    if dimm_info:
        dimm = dimm_info['DIMM'][dimm_id]
        if 'PMIC' in dimm:
            pmic = dimm['PMIC']
    
    # Main container
    main_frame = ttk.Frame(root, padding=(10, 5))
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    mboard_frame = ttk.Frame(main_frame)
    mboard_frame.pack(fill=tk.X, pady=1)
    ttk.Label(mboard_frame, text="Motherboard:", style='Title.TLabel').pack(side=tk.LEFT, padx = 5, pady = 5)
    mb_name = '?????????'
    mb_label = ttk.Label(mboard_frame, text=mb_name, style='Title.TLabel')
    mb_label.pack(side=tk.LEFT, padx = 5, pady = 5)
    
    dimm_frame = ttk.LabelFrame(main_frame, text="DIMM", style='Section.TLabelframe')
    dimm_frame.pack(fill=tk.X, pady=5)

    frame1 = ttk.Frame(dimm_frame)
    frame1.pack(fill=tk.X, pady=1)
    options = ("DIMM 0", "DIMM 1", "DIMM 3")
    combobox = ttk.Combobox(frame1, values=options, width = 40)
    combobox.pack(side=tk.LEFT, padx = 5)
    combobox.current(0)
    combobox.pack()
    dimm_slot = ttk.Label(frame1, text="#0: [MC 0] [CH A] [DIMM 0]", style='Value.TLabel')
    dimm_slot.pack(side=tk.LEFT, pady = 5)
    pmic_vendor = '?????????'
    if pmic:
        pmic_vid = pmic['vid']
        if pmic_vid == VENDOR_ID_RICHTEK:
            pmic_vendor = 'Richtek'
    dimm_pmic = ttk.Label(dimm_frame, text=f"PMIC5100: {pmic_vendor}", style='Value.TLabel')
    dimm_pmic.pack(side=tk.LEFT, padx = 5, pady = 5)

    freq_volt_frame = ttk.Frame(main_frame)
    freq_volt_frame.pack(fill=tk.X, pady=5)

    freq_chan_frame = ttk.Frame(freq_volt_frame)
    freq_chan_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=3)
    
    # Frequency information
    freq_frame = ttk.LabelFrame(freq_chan_frame, text="Frequency", style='Section.TLabelframe')
    freq_frame.pack(side=tk.TOP, fill=tk.Y, expand=False, padx=5)

    def create_freq_col(vlist: list, w, vs: list = None, anchor = 'center'):
        nonlocal freq_frame
        col = ttk.Frame(freq_frame)
        col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=1)
        for value in vlist:
            vstyle = 'fixT.TLabel'
            if isinstance(value, float) and math.isnan(value):
                vstyle = 'fixV.TLabel'
                value = ''
            elif isinstance(value, int) or isinstance(value, float):
                vstyle = 'fixV.TLabel'
                value = str(value)
            if vs and row in vs:
                vstyle = 'fixV.TLabel'
            ttk.Label(col, text=value, style=vstyle, width=w, anchor=anchor).pack(fill=tk.X, pady=1)
        
    BCLK = mem['BCLK_FREQ'] if mem else '???'
    QCLK_RATIO = mem['SA']['QCLK_RATIO'] if mem else '???'
    QCLK_FREQ = mem['SA']['QCLK'] if mem else '???'
    UCLK_RATIO = mem['SA']['UCLK_RATIO'] if mem else '???'
    UCLK_FREQ = mem['SA']['UCLK'] if mem else '???'
    
    create_freq_col([ "", "MCLK", "UCLK" ], w = 5)
    create_freq_col([ "Rate", QCLK_RATIO, UCLK_RATIO ], w = 6)
    create_freq_col([ "", "x", "x" ], w = 1)
    create_freq_col([ "BCLK", BCLK, BCLK ], w = 7)
    create_freq_col([ "", "=", "=" ], w = 1)
    create_freq_col([ "Frequency", QCLK_FREQ, UCLK_FREQ ], w = 10)
    create_freq_col([ "", "MHz", "MHz" ], w = 4, anchor = tk.W)

    # Channel info
    channel_frame = ttk.Frame(freq_chan_frame)
    channel_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False, pady=(5,0))
    
    chan_count = '?'
    gear_mode = '?'
    if mem:
        chan_count = len(mem['mc']) * len(mem['mc'][0]['channels'])
        chan_count = str(chan_count)
        gear_mode = str(mem['GEAR'])
    
    ttk.Label(channel_frame, text="Channels", width=10, anchor='e').pack(side=tk.LEFT)
    ttk.Label(channel_frame, text=chan_count, width=2, style='val.TLabel', anchor='center').pack(side=tk.LEFT, padx=1)
    ttk.Label(channel_frame, text="  ", width=1).pack(side=tk.LEFT)
    ttk.Label(channel_frame, text="Gear Mode", width=11, anchor='e').pack(side=tk.LEFT)
    ttk.Label(channel_frame, text=gear_mode, width=2, style='val.TLabel', anchor='center').pack(side=tk.LEFT, padx=1)
    
    # Sensors info
    sens_frame = ttk.LabelFrame(freq_volt_frame, text="DIMM Sensors", style='Section.TLabelframe')
    sens_frame.pack(fill=tk.BOTH, expand=True, pady=3)
    
    sensA = ttk.Frame(sens_frame)
    sensA.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
    sensB = ttk.Frame(sens_frame)
    sensB.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
    
    def create_sens_val(sframe, name, value, vt, w = 6):
        if isinstance(value, float) and math.isnan(value):
            value = ''
        elif isinstance(value, float):
            value = str(round(value, 3))
        else:
            value = str(value)
        frame = ttk.Frame(sframe)
        frame.pack(fill=tk.X, pady=1)
        ttk.Label(frame, text=name,  width=w, style='fixT.TLabel', anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(frame, text=value, width=7, style='fixV.TLabel', anchor='center').pack(side=tk.LEFT)
        if vt:
            ttk.Label(frame, text=vt, width=2, style='Title.TLabel', anchor='w').pack(side=tk.LEFT)
        
    VIN = '???'
    LVDO18 = '???'
    LVDO10 = '???'
    vlist = [ '???', '???', '???', '???' ]
    if pmic:
        v_id = 0
        for vname in [ 'SWA', 'SWB', 'SWC', 'SWD' ]:
            if pmic[vname] is not None and pmic[vname] != 0.0:
                vlist[v_id] = pmic[vname]
                v_id += 1
        VIN = pmic['VIN']
        LVDO18 = pmic['1.8V']
        LVDO10 = pmic['1.0V']
    
    create_sens_val(sensA, 'VDD', vlist[0], 'V')
    create_sens_val(sensA, 'VDDQ', vlist[1], 'V')
    create_sens_val(sensA, 'VPP', vlist[2], 'V')
    create_sens_val(sensA, 'VIN', VIN, 'V')

    temp = dimm['temp'] if dimm and 'temp' in dimm else '???'
    
    create_sens_val(sensB, 'Temp', temp, 'C°')
    create_sens_val(sensB, '1.8V', LVDO18, 'V')
    create_sens_val(sensB, '1.0V', LVDO10, 'V')
    
    # Main timings section
    timings_frame = ttk.LabelFrame(main_frame, text="Timings", style='Section.TLabelframe')
    timings_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def create_col_timings(tlist, wn = 8, wv = 5):
        nonlocal timings_frame
        col = ttk.Frame(timings_frame)
        col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        for name, value in tlist:
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
            ttk.Label(frame, text=name,  style='fixT.TLabel', width=_wn, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=value, style='fixV.TLabel', width=_wv, anchor='center').pack(side=tk.LEFT)

    mctl = None
    chan = None
    ch = None
    if mem:
        mctl = mem['mc'][mc_id]
        chan = mctl['channels'][ch_id]
        ch = chan['info']
    
    col_timings = [
        ( "", "" ),
        ( "tCL",    ch['tCL']  if ch else '??' ),
        ( "tRCD",   ch['tRCD'] if ch else '??' ),
        ( "tRCDwr", ''),
        ( "tRP",    ch['tRP']  if ch else '??' ),
        ( "tRAS",   ch['tRAS'] if ch else '??' ),
        ( "tRC",    ch['tRAS'] + ch['tRP'] if ch else '??' ),
    ]
    create_col_timings(col_timings, wn = 7)
    
    col_timings = [
        ( "tCR",    ch['tCR']    if ch else '??' ),
        ( "tCWL",   ch['tCWL']   if ch else '??' ),
        ( "tRFC",   ch['tRFC']   if ch else '??' ),
        ( "tRFC2",  ch['tRFC2']  if ch and 'tRFC2' in ch else '' ),
        ( "tRFCpb", ch['tRFCpb'] if ch else '??' ),
        ( "tXSR",   ch['tXSR']   if ch else '??' ),
        ( "tREFI",  ch['tREFI']  if ch else '??' ),
    ]
    create_col_timings(col_timings)
    
    col_timings = [
        ( "tFAW",    ch['tFAW']    if ch else '??' ),
        ( "tRRD_L",  ch['tRRD_L']  if ch else '??' ),
        ( "tRRD_S",  ch['tRRD_S']  if ch else '??' ),
        ( "tRDPRE",  ch['tRDPRE']  if ch else '??' ),
        ( "tRDPDEN", ch['tRDPDEN'] if ch else '??' ),
    ]
    create_col_timings(col_timings)
    
    col_timings = [
        ( "tWR",     ch['tWR']     if ch else '??' ),
        ( "tWTR_L",  ch['tWTR_L']  if ch else '??' ),
        ( "tWTR_S",  ch['tWTR_S']  if ch else '??' ),
        ( "tWRPRE",  ch['tWRPRE']  if ch else '??' ),
        ( "tWRPDEN", ch['tWRPDEN'] if ch else '??' ),
        ( "tWTP",    ch['tWTP']    if ch and 'tWTP' in ch else '' ),
    ]
    create_col_timings(col_timings)

    RTL = '??/??/??/??'
    if ch:
        rtl_list = [ '??', '??', '??', '??' ]
        for key, val in ch.items():
            if key.startswith('tRTL_'):
                num = int(key.split('_')[1])
                rtl_list[num] = str(val)
        RTL = '/'.join(rtl_list)

    col_timings = [
        ( "tCKE",    ch['tCKE']    if ch else '??' ),
        ( "tCPDED",  ch['tCPDED']  if ch else '??' ),
        ( "tXP",     ch['tXP']     if ch else '??' ),
        ( "tXPDLL",  ch['tXPDLL']  if ch else '??' ),
        ( "tXSDLL",  ch['tXSDLL']  if ch else '??' ),
        ( "RTL", RTL),
    ]
    create_col_timings(col_timings, wv = 6)
    
    adv_frame = ttk.Frame(main_frame)
    adv_frame.pack(fill=tk.X, pady=5)

    def create_adv_timings(tframe, tlist, caption, wn = 9, wv = 5):
        col = ttk.LabelFrame(tframe, text=caption, style='Section.TLabelframe')
        col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
        for name, value in tlist:
            value = str(value)
            _wn = wn
            _wv = wv
            frame = ttk.Frame(col)
            frame.pack(fill=tk.X, pady=1)
            ttk.Label(frame, text=name,  style='fixT.TLabel', width=_wn, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=value, style='fixV.TLabel', width=_wv, anchor='center').pack(side=tk.LEFT)

    adv_timings = [
        ( "tRDRD_sg", ch['tRDRD_sg'] if ch else '??' ),
        ( "tRDWR_sg", ch['tRDWR_sg'] if ch else '??' ),
        ( "tWRRD_sg", ch['tWRRD_sg'] if ch else '??' ),
        ( "tWRWR_sg", ch['tWRWR_sg'] if ch else '??' ),
    ]
    create_adv_timings(adv_frame, adv_timings, "Same Bank Group")
    adv_timings = [
        ( "tRDRD_dg", ch['tRDRD_dg'] if ch else '??' ),
        ( "tRDWR_dg", ch['tRDWR_dg'] if ch else '??' ),
        ( "tWRRD_dg", ch['tWRRD_dg'] if ch else '??' ),
        ( "tWRWR_dg", ch['tWRWR_dg'] if ch else '??' ),
    ]
    create_adv_timings(adv_frame, adv_timings, "Different Bank Group")
    adv_timings = [
        ( "tRDRD_dr", ch['tRDRD_dr'] if ch else '??' ),
        ( "tRDWR_dr", ch['tRDWR_dr'] if ch else '??' ),
        ( "tWRRD_dr", ch['tWRRD_dr'] if ch else '??' ),
        ( "tWRWR_dr", ch['tWRWR_dr'] if ch else '??' ),
    ]
    create_adv_timings(adv_frame, adv_timings, "Same DIMM")
    adv_timings = [
        ( "tRDRD_dd", ch['tRDRD_dd'] if ch else '??' ),
        ( "tRDWR_dd", ch['tRDWR_dd'] if ch else '??' ),
        ( "tWRRD_dd", ch['tWRRD_dd'] if ch else '??' ),
        ( "tWRWR_dd", ch['tWRWR_dd'] if ch else '??' ),
    ]
    create_adv_timings(adv_frame, adv_timings, "Different DIMM")
    
    # Refresh button
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill=tk.X, pady=6)
    btn_refresh = ttk.Button(btn_frame, text="Refresh", command = button_click_refresh)
    btn_refresh.pack(side=tk.RIGHT)
    
    g_win = main_frame
    return g_root

def button_click_refresh():
    print("Button refresh clicked!")
    mem_info = get_mem_info()
    dimm_info = get_mem_spd_all(mem_info, with_pmic = True)
    create_window_memory(mem_info, dimm_info)
    print('Main window recreated!')

if __name__ == "__main__":
    from cpuidsdk64 import SdkInit
    from memory import get_mem_info
    from memspd import get_mem_spd_all
    SdkInit(None, verbose = 0)
    mem_info = get_mem_info()
    dimm_info = get_mem_spd_all(mem_info, with_pmic = True)
    root = create_window_memory(mem_info, dimm_info)
    root.mainloop()


