import sys
import math
import json
import types

import tkinter as tk
from tkinter import ttk

class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.tipwindow = None

    def enter(self, event=None):
        self.showtip()

    def leave(self, event=None):
        self.hidetip()

    def showtip(self):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Consolas", "9", "normal"), wraplength=500)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class AdvancedTooltip:
    """Advanced tooltip window with comprehensive DDR5 information"""
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        
    def show_advanced_info(self):
        """Show the advanced DDR5 information window"""
        if self.window:
            self.window.destroy()
            
        # Create the advanced info window
        self.window = tk.Toplevel(self.parent)
        self.window.title("DDR5 Advanced Information & Optimization Guide")
        self.window.geometry("900x700")
        self.window.resizable(True, True)
        
        # Make window modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Bind ESC key to close window
        self.window.bind('<Escape>', lambda e: self.close_window())
        self.window.focus_set()  # Ensure window has focus for ESC key
        
        # Main scrollable frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollable text widget
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Text widget with monospace font for better formatting
        text_widget = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 10),
                             yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        v_scrollbar.config(command=text_widget.yview)
        h_scrollbar.config(command=text_widget.xview)
        
        # Get comprehensive information
        advanced_info = self.get_comprehensive_info()
        
        # Insert the text
        text_widget.insert(tk.END, advanced_info)
        text_widget.config(state=tk.DISABLED)  # Make read-only
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        close_btn = ttk.Button(button_frame, text="Close", command=self.close_window)
        close_btn.pack(side=tk.RIGHT)
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
        
    def close_window(self):
        """Close the advanced info window"""
        if self.window:
            self.window.destroy()
            self.window = None
            
    def get_comprehensive_info(self):
        """Get comprehensive DDR5 information that's not in regular tooltips"""
        return """
═══════════════════════════════════════════════════════════════════════════════════
                    DDR5 ADVANCED OPTIMIZATION & VALIDATION GUIDE
═══════════════════════════════════════════════════════════════════════════════════

OPTIMAL CONFIGURATIONS (6000-9000 MT/s)
═══════════════════════════════════════════════════════════════════════════════════

PERFECT TIMING SET (Hynix 3GB ICs & Micron 3/4GB):
   • tRRD_S: 8 tCK    ← NEVER LOWER! (Ruins DDR5 parallelization)
   • tRRD_L: 12 tCK   ← Perfect for IC density & roundtrip timing
   • tWTR_S: 4 tCK    ← Half of tRRD_S (optimal burst alignment)
   • tWTR_L: 24 tCK   ← Perfect baseline (may tune to 18 or 12+3/4)
   • tFAW: 32 tCK     ← OPTIMAL for DDR5 UDIMM 1KB pagesize
   • tWR: 30 tCK      ← Standard recommendation
   • tRTP: 15 tCK     ← Used in tRAS formula



CRITICAL WARNINGS:
   • NEVER lower tRRD_S below 8 tCK - destroys DDR5 dual subchannel benefits
   • NEVER lower tFAW below 32 tCK - completely ruins parallelization
   • Visual "lower timings" may actually hurt performance due to DDR5 architecture

JEDEC Timing Formulas:
   • tRAS = tRCD + tRTP + 8     (OC Formula)
   • tRC = tRP + tRCD           (JEDEC Standard)
   • tRASmax = tRP + CAS + tRCD (Maximum Active)
   • tCWL = tCL - 2             (Typical relationship)

═══════════════════════════════════════════════════════════════════════════════════
DDR5 ARCHITECTURAL INSIGHTS
═══════════════════════════════════════════════════════════════════════════════════

DDR5 DUAL SUBCHANNEL REVOLUTION:
   • Traditional "4 activates in window" constraint is OBSOLETE
   • Each subchannel operates independently with 32-bit data path
   • 4 writes across 4 subchannels within BL16 (burst length 16)
   • Parallelization is key - don't sacrifice for visually lower numbers!

DDR5 WRITE BEHAVIOR:
   • Writes DON'T follow BurstChop8 pattern
   • Sequential: 4+8+break, 4+8+break pattern per subchannel
   • Dynamic scheduling capability allows 6, 7, or 12 tCK variations
   • Zero relation to BurstChop - separated but read-aligned

ELECTRICAL DESIGN FACTS:
   • DDR5 UDIMM 1KB pagesize electrical design optimized for tFAW = 32
   • Lowering tFAW creates barely utilized burst length
   • CPU PHY interleaving has matured - respect the architecture
   • Physical design moved beyond legacy DDR4 constraints

═══════════════════════════════════════════════════════════════════════════════════
PLATFORM-SPECIFIC OPTIMIZATIONS
═══════════════════════════════════════════════════════════════════════════════════

Z890 CHIPSET SPECIFIC:
   • WTR 3-18 on CCDLWR 48 works well
   • WTR 4-16 on CCDLWR 32 works well  
   • WTR 4-20 on CCDLWR 48 also works
   • Better CCDL_WR control available vs previous generations

COMPLEX TIMINGS - TRUST UEFI/BIOS:
   • Keep RDPRE/PDEN, WRPRE/DEN, DR/DD on AUTO
   • RDWR/WRRD calculations are complex and PHY-dependent
   • All depend on CAS/CWL/Dec-Add_tCWL mix & Board Layout
   • 2DPC configurations have higher minimums than 1DPC


═══════════════════════════════════════════════════════════════════════════════════
ADVANCED TURNAROUND TIMINGS
═══════════════════════════════════════════════════════════════════════════════════

INTEL BIOS FORMULAS:
   • tWRRD_sg = tCWL + BurstLength + tWTR_L + 2
   • tWRRD_dg = tCWL + BurstLength + tWTR_S + 2
   • tWRPRE = tCWL + BurstLength + tWR
   • tWRPDEN may use alternative tWR calculation

 OPTIMAL ADVANCED TIMINGS:
   • tRDRD_sg: 16 tCK (Same bank group reads)
   • tWRWR_sg: 12 tCK (Same bank group writes)
   • These values perfect for Hynix 3GB & Micron 3/4GB ICs

═══════════════════════════════════════════════════════════════════════════════════
REFRESH & THERMAL CONSIDERATIONS
═══════════════════════════════════════════════════════════════════════════════════

REFRESH TIMING SAFETY:
   • tREFI Standard: 7.8μs (1x refresh)
   • tREFI Extended: 3.9μs (2x refresh)
   • SAFE: 32767, Aggressive: 65535, Extreme: 131071, Max: 262143
   • WARNING: Higher tREFI without proper cooling = data loss!

TEMPERATURE-DEPENDENT REFRESH:
   • Normal: tREFI trigger
   • >85°C: tREFI/2 trigger (Fine Granularity Refresh)
   • FGR enables per-bank refresh with tRFCpb timing

RFC TIMING BY DENSITY:
   DDR5 Density │ tRFC1  │ tRFC2  │ tRFCpb │
   ─────────────┼────────┼────────┼────────┤
   8Gb          │ 195ns  │ 130ns  │ 115ns  │
   16Gb         │ 295ns  │ 160ns  │ 130ns  │
   24Gb         │ 410ns  │ 220ns  │ 190ns  │
   32Gb         │ 410ns  │ 220ns  │ 190ns  │

═══════════════════════════════════════════════════════════════════════════════════
PERFORMANCE BOTTLENECKS & LIMITS
═══════════════════════════════════════════════════════════════════════════════════

AT EXTREME SPEEDS (9400+ MT/s):
   • L3 cache becomes bottleneck (90% cache fills)
   • Board tuning & thermal design critical
   • Mature ICs required (tested silicon)
   • 4nCK speeds push CPU PHY limits

OVERCLOCKING PRIORITIES:
   1. Maintain DDR5 parallelization (tFAW ≥ 32, tRRD_S ≥ 8)
   2. Optimize for IC characteristics (density-dependent timings)
   3. Respect JEDEC minimums for stability
   4. Use UEFI/BIOS calculations for complex turnarounds
   5. Monitor thermals for refresh stability

═══════════════════════════════════════════════════════════════════════════════════
REFERENCE STANDARDS
═══════════════════════════════════════════════════════════════════════════════════

JEDEC Standards:
   • JESD79-5C: DDR5 SDRAM Standard
   • Section 13.2: nCK Calculation Methods
   • Timing parameter specifications by speed grade

═══════════════════════════════════════════════════════════════════════════════════


Press ESC or click Close to return to the main application.
"""

# ===============================================================================================

m_inf = types.SimpleNamespace()

# DDR5 OPTIMAL CONFIGURATION GUIDE (6000-9000 MT/s)
# Based on extensive overclocking research and DDR5 electrical design
m_inf.ddr5_optimal_guide = """
DDR5 OPTIMAL TIMING CONFIGURATION (6000-9000 MT/s)

CORE TIMINGS (Hynix 3GB ICs & Micron 3/4GB):
- tRRD_S: 8 tCK    (NEVER lower - ruins parallelization)
- tRRD_L: 12 tCK   (Perfect for IC density & roundtrip)
- tWTR_S: 4 tCK    (Half of tRRD_S, optimal burst alignment)
- tWTR_L: 24 tCK   (Perfect, may tune to 18 or 12+3/4 in special cases)
- tFAW: 32 tCK     (OPTIMAL for DDR5 UDIMM 1KB pagesize - NEVER lower!)

Z890 SPECIFIC OPTIMIZATIONS:
- WTR 3-18 on CCDLWR 48 works well
- WTR 4-16 on CCDLWR 32 works well  
- WTR 4-20 on CCDLWR 48 also works
- Better CCDL_WR control available

CRITICAL RULES:
- Trust UEFI/BIOS for RDWR/WRRD calculations (complex PHY-dependent)
- Keep RDPRE/PDEN, WRPRE/DEN, DR/DD on AUTO
- All depend on CAS/CWL/Dec-Add_tCWL mix & Board Layout
- 2DPC has higher minimums than 1DPC

ELECTRICAL DESIGN FACTS:
- tFAW "4 activates in window" is LEGACY (obsolete in DDR5)
- DDR5 dual subchannel eliminates traditional constraints
- Parallelization is key - don't sacrifice for visually lower numbers!
"""

# JEDEC DDR5 timing specifications for validation (JESD79-5C)
# All timing values in nanoseconds, based on JEDEC Standard No. 79-5
m_inf.jedec_timings = {
    # DDR5 Speed Grade Specifications (JEDEC Standard No. 79-5)
    3200: {
        'tCK_avg': 0.625, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 25.0, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    3600: {
        'tCK_avg': 0.555, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 22.2, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    4000: {
        'tCK_avg': 0.500, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 20.0, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    4400: {
        'tCK_avg': 0.454, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 18.16, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    4800: {
        'tCK_avg': 0.416, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 16.64, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    5200: {
        'tCK_avg': 0.384, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 15.36, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    5600: {
        'tCK_avg': 0.357, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 14.28, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    6000: {
        'tCK_avg': 0.333, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 13.32, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    6400: {
        'tCK_avg': 0.312, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 12.48, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    # Extended speeds for overclocking validation
    7200: {
        'tCK_avg': 0.277, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 11.08, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    },
    8000: {
        'tCK_avg': 0.250, 'tAA_min': 13.75, 'tRCD_min': 13.75, 'tRP_min': 13.75, 
        'tRAS_min': 32.0, 'tWR_min': 30.0, 'tRTP_min': 7.5, 'tFAW_min': 10.0, 
        'tRRD_L_min': 5.0, 'tRRD_S_min': 2.5, 'tWTR_L_min': 10.0, 'tWTR_S_min': 2.5,
        'tRFC_min': 295.0, 'tRFC2_min': 160.0, 'tRFCpb_min': 90.0
    }
}
        
# DDR5 MR13 OP[3:0] - Mode Register 13 Operating Parameters
# Maps MR13 values to timing parameters and data rate ranges
m_inf.mr13_timing_table = {
    0 : {'tCCD_L': 8,  'tCCD_L_WR': 16, 'tCCD_L_WR2': 32, 'tDDLK': 1024, 'data_rate_range': (1980, 3200), 'description': '1980 MT/s ≤ data rate ≤ 2100 MT/s and 2933 MT/s ≤ data rate ≤ 3200 MT/s'},
    1 : {'tCCD_L': 9,  'tCCD_L_WR': 18, 'tCCD_L_WR2': 36, 'tDDLK': 1024, 'data_rate_range': (3200, 3600), 'description': '3200 MT/s < data rate ≤ 3600 MT/s'},
    2 : {'tCCD_L': 10, 'tCCD_L_WR': 20, 'tCCD_L_WR2': 40, 'tDDLK': 1280, 'data_rate_range': (3600, 4000), 'description': '3600 MT/s < data rate ≤ 4000 MT/s'},
    3 : {'tCCD_L': 11, 'tCCD_L_WR': 22, 'tCCD_L_WR2': 44, 'tDDLK': 1280, 'data_rate_range': (4000, 4400), 'description': '4000 MT/s < data rate ≤ 4400 MT/s'},
    4 : {'tCCD_L': 12, 'tCCD_L_WR': 24, 'tCCD_L_WR2': 48, 'tDDLK': 1536, 'data_rate_range': (4400, 4800), 'description': '4400 MT/s < data rate ≤ 4800 MT/s'},
    5 : {'tCCD_L': 13, 'tCCD_L_WR': 26, 'tCCD_L_WR2': 52, 'tDDLK': 1536, 'data_rate_range': (4800, 5200), 'description': '4800 MT/s < data rate ≤ 5200 MT/s'},
    6 : {'tCCD_L': 14, 'tCCD_L_WR': 28, 'tCCD_L_WR2': 56, 'tDDLK': 1792, 'data_rate_range': (5200, 5600), 'description': '5200 MT/s < data rate ≤ 5600 MT/s'},
    7 : {'tCCD_L': 15, 'tCCD_L_WR': 30, 'tCCD_L_WR2': 60, 'tDDLK': 1792, 'data_rate_range': (5600, 6000), 'description': '5600 MT/s < data rate ≤ 6000 MT/s'},
    8 : {'tCCD_L': 16, 'tCCD_L_WR': 32, 'tCCD_L_WR2': 64, 'tDDLK': 2048, 'data_rate_range': (6000, 6400), 'description': '6000 MT/s < data rate ≤ 6400 MT/s'},
    9 : {'tCCD_L': 17, 'tCCD_L_WR': 34, 'tCCD_L_WR2': 68, 'tDDLK': 2048, 'data_rate_range': (6400, 6800), 'description': '6400 MT/s ≤ Data Rate ≤ 6800 MT/s'},
    10: {'tCCD_L': 18, 'tCCD_L_WR': 36, 'tCCD_L_WR2': 72, 'tDDLK': 2304, 'data_rate_range': (6800, 7200), 'description': '6800 MT/s ≤ Data Rate ≤ 7200 MT/s'},
    11: {'tCCD_L': 19, 'tCCD_L_WR': 38, 'tCCD_L_WR2': 76, 'tDDLK': 2304, 'data_rate_range': (7200, 7600), 'description': '7200 MT/s ≤ Data Rate ≤ 7600 MT/s'},
    12: {'tCCD_L': 20, 'tCCD_L_WR': 40, 'tCCD_L_WR2': 80, 'tDDLK': 2560, 'data_rate_range': (7600, 8000), 'description': '7600 MT/s ≤ Data Rate ≤ 8000 MT/s'},
    13: {'tCCD_L': 21, 'tCCD_L_WR': 42, 'tCCD_L_WR2': 84, 'tDDLK': 2560, 'data_rate_range': (8000, 8400), 'description': '8000 MT/s ≤ Data Rate ≤ 8400 MT/s'},
    14: {'tCCD_L': 22, 'tCCD_L_WR': 44, 'tCCD_L_WR2': 88, 'tDDLK': 2816, 'data_rate_range': (8400, 8800), 'description': '8400 MT/s ≤ Data Rate ≤ 8800 MT/s'},
    15: {'reserved': True, 'description': 'Reserved'}
}
        
# RECOMMENDED OPTIMAL VALUES (Hynix 3GB ICs & Micron 3/4GB)
# Perfect for 6000-9000 MT/s range - mature ICs may achieve 9400 MT/s!
m_inf._optimal_values = {
    'tFAW': 32,      # NEVER lower - ruins parallelization
    'tRRD_S': 8,     # Architectural minimum for DDR5 dual subchannel
    'tRRD_L': 12,    # Perfect for IC density & roundtrip timing
    'tWTR_S': 4,     # Exactly half of tRRD_S
    'tWTR_L': 24,    # Perfect, may tune to 18 or 12+3/4 in special cases
    'tWR': 30,       # Standard for DDR5
    'tRTP': 15,      # Read to precharge timing
    #  formulas
    'tRAS_formula': 'tRCD + tRTP + 8',     #  formula
    'tRC_formula': 'tRP + tRCD',           # JEDEC/Intel standard  
    'tRASmax_formula': 'tRP + CAS + tRCD', # Maximum active time
    # Advanced turnarounds
    'tRDRD_sg': 16,  # Read to Read same bank group
    'tWRWR_sg': 12,  # Write to Write same bank group
}
        
# Clean, coherent timing formulas with  insights
m_inf.timing_formulas = {
    # ===== PRIMARY TIMINGS =====
    'tCL': """
CAS Latency (Column Address Strobe)
JEDEC: Command to data output delay
Formula: nCK = ceiling((tAA_min / tCK_avg) - 0.01)
Min: 22 tCK (DDR5-4800), typically 32-46 for performance kits

Higher CL allows tighter subtimings for better overall performance
""",
    'tRCD': """
RAS to CAS Delay (Row Command Delay)
JEDEC: Row activate to column command delay
Formula: nCK = ceiling((tRCD_min / tCK_avg) - 0.01)
Min: 22 tCK (DDR5-4800)

Formula: tRAS = tRCD + tRTP + 8
Perfect for Hynix 3GB ICs & Micron 3/4GB (6000-9000 MT/s)
""",
    'tRCDW': """
RAS to CAS Delay for Write
JEDEC: Separate timing for write operations
Usually same as tRCD unless specifically optimized
""",
    'tRP': """
Row Precharge Time
JEDEC: Precharge to activate delay
Formula: nCK = ceiling((tRP_min / tCK_avg) - 0.01)
Min: 22 tCK (DDR5-4800)

Formula: tRC = tRP + tRCD (JEDEC standard)
""",
    'tRAS': """
Row Active Time
JEDEC: Minimum time row must remain active
Formula: nCK = ceiling((tRAS_min / tCK_avg) - 0.01)
Min: 52 tCK (DDR5-4800)

Formula: tRAS = tRCD + tRTP + 8
Perfect for Hynix 3GB ICs & Micron 3/4GB (6000-9000 MT/s)
Ensures data retention during access
""",
    'tRC': """
Row Cycle Time (Complete Row Operation)
JEDEC/Intel: Total row cycle time
Standard: tRC = tRAS + tRP

Formula: tRC = tRP + tRCD
Should equal calculated value for optimal performance
""",
    # ===== WRITE TIMINGS =====
    'tWR': """
Write Recovery Time
JEDEC: Write to precharge delay
Formula: nCK = ceiling((tWR_min / tCK_avg) - 0.01)
Min: 30 tCK (DDR5-4800)

 OPTIMAL: tWR = 30 tCK
Perfect for Hynix 3GB ICs & Micron 3/4GB (6000-9000 MT/s)
""",
    'tCWL': """
CAS Write Latency
JEDEC: Write command to data timing
Formula: nCK = ceiling((tCWL_min / tCK_avg) - 0.01)
Typically: tCWL = tCL - 2

Used in Intel BIOS turnaround calculations
""",
    # ===== BANK GROUP TIMINGS =====
    'tFAW': """
Four Activate Window -

LEGACY ALERT: "4 activates in window" is OBSOLETE in DDR5!
DDR5 dual subchannel eliminates traditional 4-activate constraints

 OPTIMAL: tFAW = 32 tCK (NEVER LOWER!)
Perfect for DDR5 UDIMM 1KB pagesize electrical design
Hynix 3GB ICs & Micron 3/4GB - 6000-9000 MT/s

CRITICAL: Lowering below 32 completely ruins parallelization
- Destroys DDR5's architectural benefits
- Halves PHY work on CPU side  
- Creates barely utilized burst length
- Visually lower timings but worse performance

DDR5 SUBCHANNEL REVOLUTION:
- 4 writes across 4 subchannels within BL16
- Zero relation to BurstChop8
- ForthACT Window timing is DEAD
- Physical design moved on, CPU PHY interleaving matured

JEDEC Formula: nCK = ceiling((tFAW_min / tCK_avg) - 0.01)
""",
    'tRRD_S': """
Row to Row Delay (Short) - Different Bank Group

 OPTIMAL: tRRD_S = 8 tCK (NEVER LOWER!)
Architectural minimum for DDR5 dual subchannel
Perfect for Hynix 3GB ICs & Micron 3/4GB

CRITICAL: Never below 8 tCK - destroys DDR5 parallelization
JEDEC Min: 8 tCK or 2.5ns
Formula: nCK = max(8, ceiling((tRRD_S_min / tCK_avg) - 0.01))
""",
    'tRRD_L': """
Row to Row Delay (Long) - Same Bank Group

 OPTIMAL: tRRD_L = 12 tCK
Perfect for IC density & roundtrip timing  
Hynix 3GB ICs & Micron 3/4GB - 6000-9000 MT/s
Mature ICs may achieve 9400 MT/s with 8-12-4-24

JEDEC Min: 8 tCK or 5.0ns
Fine till ~7600 MT/s: tRRD 8-8 acceptable, 8-10 fully fine
Formula: nCK = max(8, ceiling((tRRD_L_min / tCK_avg) - 0.01))
""",
    'tWTR_S': """
Write to Read Turnaround (Short) - Different Bank Group

 OPTIMAL: tWTR_S = 4 tCK
Exactly half of tRRD_S (optimal burst alignment)
Perfect for Hynix 3GB ICs & Micron 3/4GB

DDR5 WRITE BEHAVIOR:
- Dynamic scheduling capability
- Can be 6, 7, or 12 tCK but optimally half of tRRD_S
- SubChannel design allows burst 3 timing
- Effects of scheduling smaller - 2nd subchannel/DIMM free

JEDEC Min: 4 tCK or 2.5ns
Formula: nCK = max(4, ceiling((tWTR_S_min / tCK_avg) - 0.01))
""",
    'tWTR_L': """
Write to Read Turnaround (Long) - Same Bank Group

 OPTIMAL: tWTR_L = 24 tCK
Perfect for Hynix 3GB ICs & Micron 3/4GB
Special tuning may allow 18 or even 12+3/4 tCK
At extreme ranges, parallelization breaks & averages worsen!

- Writes DON'T follow BurstChop8 (per subchannel individually)
- Sequential: 4+8+break, 4+8+break pattern
- Non-delayed writes to 4 DIMM places
- 4 writes across 4 subchannels within BL16
- Zero relation to BurstChop - separated but read-aligned

JEDEC Min: 16 tCK or 10ns
Formula: nCK = max(16, ceiling((tWTR_L_min / tCK_avg) - 0.01))
Intel BIOS: tWTR_L = tWRRD_sg - tCWL - BurstLength - 2
""",
    'tRTP': """
Read to Precharge
JEDEC: Internal read to precharge delay
Formula: nCK = max(12, ceiling((tRTP_min / tCK_avg) - 0.01))

 OPTIMAL: tRTP = 15 tCK  
Used in  tRAS formula: tRAS = tRCD + tRTP + 8

JEDEC Min: 12 tCK or 7.5ns
""",
    # ===== REFRESH TIMINGS =====
   'tRFC': """
Refresh Cycle Time
JEDEC: the delay from when a refresh starts to when it finishes for any bank group and is triggered by tREFI or when DIMM temp is > 85C by tREFI/2.

| Parameter | 8Gb | 16Gb | 24Gb | 32Gb | Units |
| RFC1,min  | 195 | 295 | 410   | 410  |   ns  |
Critical for stability and data retention
""",
    'tRFC2': """
Fine Granularity Refresh
JEDEC: Used when Fine Granularity Refresh (FGR) mode is enabled and is then triggred by tREFI/2 or when DIMM temp is > 85C by tREFI/4. A Bios may use this value to set tRFC automatically
|  Parameter   | 8Gb | 16Gb | 24Gb | 32Gb | Units |
|  RFC2,min    | 130 | 160  | 220   | 220  |  ns  |
e.g.(
24Gb 8000 MT/s = 4000Mhz = 4000000000Hz = 0.25ns per clock cycle
tRFC2,min = 220ns / 0.25ns = 880 clock cycles
Test in % values of the 220ns such as 80% * 220 = 176ns / 0.25ns = 704 clock cycles.)
""",
    'tRFCpb': """
Refresh Cycle Time per Bank
JEDEC:  delay from when a refresh starts to when it finishes for a single bank group. It enables other bank groups to be used for other operations while one refreshes and is allowed only when Fine granularity Refresh mode is enabled. tRFCpb is shorter than tRFC as its uses an shorter refresh interval of tREFI/(2*n) where the maximum average refresh interval is further divided down by "n" number of banks in a bank group and thus requires less time to charge a cell to it's nominal value as refreshes occur more frequently
|  Parameter   | 8Gb | 16Gb | 24Gb | 32Gb | Units |
|  RFCsb,min   | 115 | 130  | 190  | 190  |  ns   |
e.g.(
24Gb 8000 MT/s = 4000Mhz = 4000000000Hz = 0.25ns per clock cycle
tRFCsb,min = 190ns / 0.25ns = 760 clock cycles
Test in % values of the 220ns such as 80% * 190 = 152ns / 0.25ns = 608 clock cycles.)
""",
    'tXSR': """
Exit Self Refresh
JEDEC: Formula: tXSR ≥ max(tRFC + 10ns, 200 tCK)
tRFC for DDR5.
| Parameter | 8Gb | 16Gb | 24Gb | 32Gb | Units |
| RFC1,min  | 195 | 295  | 410   | 410 |  ns   |
e.g.(
24Gb 8000MT/s = 4000Mhz = 4000000000Hz = 0.25ns per clock cycle
tRFC1,min = 410ns / 0.25ns = 1640 clock cycles
Test in % values of the 410ns such as 80% * 410 = 328ns / 0.25ns = 1312 clock cycles.)
""",
    'tREFI': """
Average Refresh Interval
JEDEC: Time between refresh commands
Standard: 7.8μs (1x), Extended: 3.9μs (2x)
DANGER: Raising this too far without proper cooling will cause data loss!
Typical values: SAFE: 32767, 
            Aggressive: 65535,
            Extreme 131071,
            Max: 262143 (Only for extreme cooling setups)
""",
    'tREFIx9': """
9x Refresh Interval
JEDEC: Extended refresh interval for power saving.
Typically: 255
""",
    'tREFSBRD': """
Refresh to Same Bank Read
JEDEC: Ensures data stability after refresh
""",
    # ===== TURNAROUND TIMINGS =====
    'tRDRD_sg': """
Read to Read (Same Bank Group)
Intel timing: Consecutive read performance

OPTIMAL: tRDRD_sg = 16 tCK
Perfect for Hynix 3GB ICs & Micron 3/4GB
""",
    'tWRWR_sg': """
Write to Write (Same Bank Group)
Intel timing: Burst write optimization

OPTIMAL: tWRWR_sg = 12 tCK
Perfect for Hynix 3GB ICs & Micron 3/4GB
""",
    'tRDWR_sg': """
Read to Write (Same Bank Group)
Intel timing: Includes data bus turnaround
Complex PHY-dependent - trust UEFI/BIOS values!
""",
    'tWRRD_sg': """
Write to Read (Same Bank Group)
Intel BIOS: tWRRD_sg = tCWL + BurstLength + tWTR_L + 2
Used in tWTR_L calculation
""",
    'tRDRD_dg': """
Read to Read (Different Bank Group)
Intel timing: Faster than same bank group
Takes advantage of bank group independence
""",
    'tWRWR_dg': """
Write to Write (Different Bank Group)
Intel timing: Optimized write performance
""",
    'tRDWR_dg': """
Read to Write (Different Bank Group)
Intel timing: Lower latency than same bank group
""",
    'tWRRD_dg': """
Write to Read (Different Bank Group)
Intel BIOS: tWRRD_dg = tCWL + BurstLength + tWTR_S + 2
Used in tWTR_S calculation
""",
    # ===== RANK/DIMM TIMINGS =====
    'tRDRD_dr': """
Read to Read (Same DIMM)
Intel timing: Rank-to-rank delay with switching overhead
""",
    'tRDWR_dr': """
Read to Write (Same DIMM)
Intel timing: Includes rank switching
""",
    'tWRRD_dr': """
Write to Read (Same DIMM)
Intel timing: Accounts for ODT switching
""",
    'tWRWR_dr': """
Write to Write (Same DIMM)
Intel timing: Multi-rank write optimization
""",
    'tRDRD_dd': """
Read to Read (Different DIMM)
Intel timing: Highest turnaround penalty
""",
    'tRDWR_dd': """
Read to Write (Different DIMM)
Intel timing: Cross-DIMM with channel switching
""",
    'tWRRD_dd': """
Write to Read (Different DIMM)
Intel timing: Maximum turnaround delay
""",
    'tWRWR_dd': """
Write to Write (Different DIMM)
Intel timing: Dual-DIMM system optimization
""",
    # ===== POWER & ADVANCED =====
    'tCKE': """
Clock Enable Time
JEDEC: Min 8 tCK - power state transition
""",
    'tXP': """
Exit Precharge Power Down
JEDEC: Formula: tXP ≥ max(8 tCK, 7.5ns)
""",
    'tXPDLL': """
Exit Precharge Power Down (DLL)
JEDEC: Power down exit with DLL relock
""",
    'tXSDLL': """
Exit Self Refresh (DLL)
JEDEC: Self refresh exit with DLL relock
""",
    'RTL': """
Round Trip Latency
Intel: Total read latency (RTL0/RTL1/RTL2/RTL3)
Critical for read timing optimization
""",
    # ===== PRECHARGE & POWER =====
    'tRDPRE': """
Read to Precharge
JEDEC: Ensures read data valid before precharge
""",
    'tRDPDEN': """
Read to Power Down Entry
JEDEC: Power management optimization
""",
    'tWRPRE': """
Write to Precharge
Intel BIOS: tWRPRE = tCWL + BurstLength + tWR
""",
    'tWRPDEN': """
Write to Power Down Entry
Intel BIOS: May use alternative tWR calculation
""",
    'tWTP': """
Write to Precharge (Internal)
JEDEC: Usually calculated from other timings
""",
    'tPRPDEN': """
Precharge to Power Down Entry
JEDEC: Power state transition timing
""",
    'tCPDED': """
Command Pass Disable Delay
JEDEC: Internal timing optimization
""",
    'tPPD': """
Power Down Delay
JEDEC: Power management timing
""",
    # ===== SPECIAL/UNDOCUMENTED =====
    'tCR': """
Command Rate
1N = commands every clock, 2N = every 2 clocks
Affects overall memory bandwidth
""",
    'DEC_tCWL': """
Decrease tCWL (Intel Internal)
Used in alternative tWTR calculations
""",
    'ADD_tCWL': """
Add to tCWL (Intel Internal)  
Used in alternative tWTR calculations
""",
    'tZQOPER': """
ZQ Calibration Time
JEDEC: Typical 512 tCK - signal integrity
""",
    'tMOD': """
Mode Register Set Time
JEDEC: Min 24 tCK after MRS commands
""",
    'tCSL': """
Chip Select Low Time
JEDEC: Min 1 tCK
""",
    'tCSH': """
Chip Select High Time
JEDEC: Min 1 tCK
""",
    'tRFM': """
Refresh Management
JEDEC: Refresh control timing
""",
    'oref_ri': """
Refresh Interval Override
Intel: Overrides standard refresh timing
""",
    'X8_DEVICE': """
x8 Device Configuration
JEDEC: Device width setting
""",
    'N_TO_1_RATIO': """
N:1 Gear Ratio
Intel: Gear mode configuration
""",
    'ADD_1QCLK_DELAY': """
Add 1 QCLK Delay
Intel: Additional clock delay
""",
    # =====  SUMMARY =====
    '_SUMMARY': """
 OPTIMAL VALUES (6000-9000 MT/s)
Hynix 3GB ICs & Micron 3/4GB - PERFECT configuration:

CORE TIMINGS:
- tFAW: 32 tCK     (NEVER lower - ruins parallelization!)
- tRRD_S: 8 tCK    (Architectural minimum)  
- tRRD_L: 12 tCK   (Perfect for IC density)
- tWTR_S: 4 tCK    (Half of tRRD_S)
- tWTR_L: 24 tCK   (Perfect, may tune to 18)
- tWR: 30 tCK      (Standard)
- tRTP: 15 tCK     ( recommended)

CALCULATED FORMULAS:
- tRAS = tRCD + tRTP + 8     ( formula)
- tRC = tRP + tRCD           (JEDEC standard)
- tRASmax = tRP + CAS + tRCD (Maximum active)

ADVANCED TURNAROUNDS:
- tRDRD_sg: 16 tCK  (Same bank group reads)
- tWRWR_sg: 12 tCK  (Same bank group writes)

Mature ICs may achieve 9400 MT/s with 8-12-4-24!
At 4nCK speeds, L3 cache becomes bottleneck (90% cache fills)
Board tuning & thermal design matter for extreme overclocking
"""
}

# ====================================================================================================

def jedec_calculate_nck(timing_ns, tck_avg_ns, use_integer_math = True):
    """Calculate nCK value using JEDEC rounding algorithms
    
    Args:
        timing_ns: Timing parameter in nanoseconds
        tck_avg_ns: Average clock period in nanoseconds
        use_integer_math: Use JEDEC integer math algorithm (preferred)
    
    Returns:
        Integer nCK value
    """
    # Validate inputs
    if not timing_ns or not tck_avg_ns or tck_avg_ns <= 0:
        return 0
        
    if use_integer_math:
        # JEDEC Integer Math Algorithm (Section 13.2.2)
        # nCK = truncate(((parameter_in_ps x 1000) / application_tCK_in_ps_(RD)) + 990) / 1000
        timing_ps = int(timing_ns * 1000)
        tck_avg_ps = int(tck_avg_ns * 1000)  # Rounded down to 1ps
        if tck_avg_ps == 0:
            return 0
        temp_nck = ((timing_ps * 1000) // tck_avg_ps) + 990
        return temp_nck // 1000
    else:
        # JEDEC Real Number Math Algorithm (Section 13.2.1)
        # nCK = ceiling((parameter_in_ns / application_tCK_in_ns_(RD)) - 0.01)
        temp_nck = (timing_ns / tck_avg_ns) - 0.01
        return math.ceil(temp_nck)

def jedec_validate_timing(param_name, actual_nck, memory_speed, tck_avg_ns):
    """Validate timing parameter against JEDEC specifications
    
    Args:
        param_name: Name of timing parameter (e.g., 'tCL', 'tRCD')
        actual_nck: Actual nCK value from memory controller
        memory_speed: Memory speed in MT/s (e.g., 4800, 5600)
        tck_avg_ns: Average clock period in nanoseconds
        
    Returns:
        dict with validation results
    """
    global m_inf
     # Find closest JEDEC speed grade
    closest_speed = min(m_inf.jedec_timings.keys(), key=lambda x: abs(x - memory_speed))
    jedec_spec = m_inf.jedec_timings.get(closest_speed, {})
    
    # Map parameter names to JEDEC specifications
    param_map = {
        'tCL': 'tAA_min',
        'tRCD': 'tRCD_min', 
        'tRP': 'tRP_min',
        'tRAS': 'tRAS_min',
        'tWR': 'tWR_min',
        'tRTP': 'tRTP_min',
        'tFAW': 'tFAW_min',
        'tRRD_L': 'tRRD_L_min',
        'tRRD_S': 'tRRD_S_min',
        'tWTR_L': 'tWTR_L_min',
        'tWTR_S': 'tWTR_S_min'
    }
    
    result = {
        'is_valid': True,
        'jedec_min_nck': None,
        'actual_nck': actual_nck,
        'margin': None,
        'compliance': 'UNKNOWN'
    }
    
    if param_name in param_map and param_map[param_name] in jedec_spec:
        timing_min_ns = jedec_spec[param_map[param_name]]
        
        # Calculate minimum nCK according to JEDEC
        jedec_min_nck = jedec_calculate_nck(timing_min_ns, tck_avg_ns)
        
        # Apply special constraints for DDR5
        # Note: DDR5 dual subchannel design changes traditional timing constraints
        if param_name in ['tRRD_L', 'tRRD_S']:
            jedec_min_nck = max(8, jedec_min_nck)
        elif param_name == 'tWTR_L':
            jedec_min_nck = max(16, jedec_min_nck)
        elif param_name == 'tWTR_S':
            jedec_min_nck = max(4, jedec_min_nck)
        elif param_name == 'tRTP':
            jedec_min_nck = max(12, jedec_min_nck)
        elif param_name == 'tFAW':
            # tFAW DDR5 ELECTRICAL DESIGN ANALYSIS:
            # • tFAW should ALWAYS be 32 on UDIMM electrical design (optimal for 1KB pagesize)
            # • 4-activate window timing is LEGACY - DDR5 dual subchannel design eliminates this constraint
            # • tFAW 32 = perfect parallelization, never lower for optimal DDR5 performance
            # • Lowering below 32 ruins parallelization, halves PHY work, reduces burst efficiency
            # • Only 48 on 2 ICs per subchannel with 2KB pagesize (rare configurations)
            # • ForthACT Window timing is legacy - doesn't apply to DDR5 dual subchannel per side
            # • CPU PHY interleaving matured enough that 4 IC access is not limiting factor
            if actual_nck == 32:
                result['compliance'] = 'OPTIMAL_DDR5'  # Perfect for DDR5 UDIMM 1KB pagesize
                result['is_valid'] = True
                result['margin'] = 0  # Exactly optimal
                return result  # Skip JEDEC calculation - 32 is architecturally optimal
            elif actual_nck >= 32 and actual_nck <= 48:
                result['compliance'] = 'JEDEC_GOOD'   # Acceptable range for special designs
            elif actual_nck < 32:
                result['compliance'] = 'DDR5_SUBOPTIMAL'  # Ruins parallelization
            else:
                # Use JEDEC calculation for values > 48
                pass
            
        result['jedec_min_nck'] = jedec_min_nck
        result['is_valid'] = actual_nck >= jedec_min_nck
        result['margin'] = actual_nck - jedec_min_nck
        
        if result['is_valid']:
            if result['margin'] == 0:
                result['compliance'] = 'JEDEC_MIN'
            elif result['margin'] <= 2:
                result['compliance'] = 'JEDEC_TIGHT'
            else:
                result['compliance'] = 'JEDEC_LOOSE'
        else:
            result['compliance'] = 'VIOLATION'
    
    # Special validation for tRC (should equal tRAS + tRP)
    if param_name == 'tRC':
        # This will be handled separately in the update function
        pass
        
    return result

def get_mr13_for_data_rate(data_rate):
    """Get the expected MR13 OP[3:0] value for a given data rate
    
    Args:
        data_rate: Memory data rate in MT/s
        
    Returns:
        dict with MR13 information or None if not found
    """
    global m_inf
    for mr13_value, config in m_inf.mr13_timing_table.items():
        if 'reserved' not in config:
            min_rate, max_rate = config['data_rate_range']
            if min_rate <= data_rate <= max_rate:
                return {
                    'mr13_value': mr13_value,
                    'binary': f'0b{mr13_value:04b}',
                    'hex': f'0x{mr13_value:X}',
                    'config': config
                }
    return None

def validate_mr13_timings(data_rate, actual_timings):
    """Validate actual timings against MR13 specifications
    
    Args:
        data_rate: Memory data rate in MT/s
        actual_timings: Dict of actual timing values
        
    Returns:
        dict with validation results
    """
    global m_inf
    mr13_info = get_mr13_for_data_rate(data_rate)
    if not mr13_info:
        return {'valid': False, 'reason': 'Data rate not found in MR13 table'}
    
    expected_config = mr13_info['config']
    results = {}
    
    # Check tCCD_L timing parameters if available
    timing_checks = ['tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2', 'tDDLK']
    for timing in timing_checks:
        if timing in expected_config and timing in actual_timings:
            expected = expected_config[timing]
            actual = actual_timings[timing]
            # Handle None values
            if actual is not None and expected is not None:
                results[timing] = {
                    'expected': expected,
                    'actual': actual,
                    'valid': actual >= expected,
                    'margin': actual - expected
                }
            else:
                results[timing] = {
                    'expected': expected,
                    'actual': actual,
                    'valid': None,  # Cannot validate
                    'margin': None
                }
    
    return {
        'valid': all(r.get('valid', True) for r in results.values() if r.get('valid') is not None),
        'mr13_info': mr13_info,
        'timing_results': results
    }

def get_timing_validation_style(validation_result):
    """Get TTK style name based on validation result"""
    if not validation_result['is_valid']:
        return 'fixV_violat.TLabel'     # Red for JEDEC violations
    elif validation_result['compliance'] == 'OPTIMAL_DDR5':
        return 'fixV_optim.TLabel'      # Bright green for optimal DDR5 values
    elif validation_result['compliance'] == 'DDR5_SUBOPTIMAL':
        return 'fixV_violat.TLabel'     # Red for DDR5 architectural violations (tFAW < 32)
    elif validation_result['compliance'] in ['JEDEC_MIN', 'JEDEC_GOOD']:
        return 'fixV_valid.TLabel'      # Green for exactly meeting JEDEC or good range
    elif validation_result['compliance'] == 'JEDEC_TIGHT':
        return 'fixV_tight.TLabel'      # Yellow for tight but valid
    else:
        return 'fixV.TLabel'            # Default white for loose/unknown

def validate_timings(self, ci, MCLK_FREQ):
    global m_inf
    vv = self.vars
    # Get memory speed and clock period for JEDEC validation
    memory_speed = int(vv.mem_freq.value) if vv.mem_freq.value and vv.mem_freq.value != '????' else 4800
    if MCLK_FREQ and MCLK_FREQ > 0:
        tck_avg_ns = 1.0 / (MCLK_FREQ * 2 * 1e6)  # Convert MHz to ns (divide by 2 for DDR)
    else:
        tck_avg_ns = 0.416  # Default for DDR5-4800
    
    # Ensure tck_avg_ns is reasonable (between 0.1ns and 2.0ns for DDR5)
    if tck_avg_ns <= 0 or tck_avg_ns > 2.0:
        tck_avg_ns = 0.416  # Fallback to DDR5-4800 default
    
    # Update timing values with JEDEC validation
    timing_params = [
        ('tCL', ci['tCL']),
        ('tRCD', ci['tRCD']),
        ('tRP', ci['tRP']),
        ('tRAS', ci['tRAS']),
        ('tWR', ci['tWR']),
        ('tRTP', ci['tRTP']),
        ('tFAW', ci['tFAW']),
        ('tRRD_L', ci['tRRD_L']),
        ('tRRD_S', ci['tRRD_S']),
        ('tWTR_L', ci['tWTR_L']),
        ('tWTR_S', ci['tWTR_S'])
    ]
    
    # Validate against MR13 specifications for DDR5
    mr13_validation = None
    if memory_speed:
        actual_timings = {
            'tCCD_L': ci.get('tCCD_L', None),
            'tCCD_L_WR': ci.get('tCCD_L_WR', None), 
            'tCCD_L_WR2': ci.get('tCCD_L_WR2', None),
            'tDDLK': ci.get('tDDLK', None)
        }
        mr13_validation = validate_mr13_timings(memory_speed, actual_timings)
    
    # IMPORTANT: Unlike HWiNFO, ATC, and MemTweak which often use incorrect software math,
    # this implementation reads actual hardware registers and validates against real JEDEC specs.
    # Many tools get RDWR/WRRD calculations wrong due to complex PHY dependencies.
    #
    # WHY OTHER TOOLS GET IT WRONG:
    # - HWiNFO, ATC, MemTweak all use software math instead of reading hardware registers
    # - tRDWR won't work correctly on 2DPC configurations (higher delays required)
    # - RDWR/WRRD/WTR calculations are skewed due to wrong mathematical assumptions
    # - All turnaround timings depend on CAS/CWL/Dec-Add_tCWL mix & Board Layout
    # - Intel + Altera recommend NOT pushing frequent RDWR for max efficiency
    # - FW (UEFI/BIOS) knows best and defaults to higher delays by PHY design
    # - Early FW got math wrong, today software still gets it wrong
    # - Only hardware register readout provides accurate validation
    #
    # DDR5 WRITE BEHAVIOR DEEP ANALYSIS ( Knowledge):
    # - Writes DON'T follow BurstChop8 (per subchannel individually)
    # - Sequential writes: 4+8+break, 4+8+break pattern
    # - Writes within reads: read → write tick 4 → BC8 ends → 2nd subchannel starts
    # - Between writes: 8 ticks optimal, but not BC8 focused
    # - Subchannel individual PHY: non-delayed writes to 4 DIMM places
    # - Optimal: 4 writes across 4 subchannels within BL16 without overlaps
    # - Zero relation to BurstChop - separated but optimally read-aligned
    # - Writes can trigger anytime, optimally burst-aligned, no ongoing limits
    #
    # OPTIMAL DDR5 TARGETS ( Verified 6000-9000 MT/s):
    # - tFAW: 32 tCK (NEVER lower - ruins parallelization) ← THIS IS OPTIMAL!
    # - tRRD_S: 8 tCK (architectural minimum for DDR5 dual subchannel)
    # - tRRD_L: 12 tCK (density dependent, can be 8-10 for some speeds)
    # - tWTR_S: 4 tCK (exactly half of tRRD_S, dynamic scheduling capable)
    # - tWTR_L: 24 tCK (can tune to 18 or 12+3/4 with ise)
    #
    # WHY tFAW < 32 IS HARMFUL:
    # - Completely ruins DDR5 parallelization design
    # - Halves PHY work on CPU side (reduces efficiency)
    # - Creates smaller access possibility with barely utilized burst length
    # - Visually lower timings but destroys DDR5's architectural benefits
    # - ForthACT Window timing is LEGACY - DDR5 dual subchannel eliminates this
    #
    #  INSIGHT: "If you cut FAW, you completely ruin parallelization"
    # "Smaller access possibility and barely utilised burst length"
    # "Lower delay required. Visually lower timings but ruins reason of DDR5s design"
    # "Also halves the work of PHYs on the CPU side and lowers strain"
    # "Please never lower than RRDS 8 or FAW 32"
    
    # Set values and validate against JEDEC
    for param_name, value in timing_params:
        var = getattr(vv, param_name)
        var.value = value
        
        # Perform JEDEC validation
        if value and str(value).isdigit():
            validation = jedec_validate_timing(param_name, int(value), memory_speed, tck_avg_ns)
            label_widget = getattr(vv, param_name + '_label', None)
            if label_widget:
                style_name = get_timing_validation_style(validation)
                label_widget.configure(style=style_name)
                
                # Update tooltip with validation info
                if hasattr(label_widget, 'tooltip'):
                    base_tooltip = m_inf.timing_formulas.get(param_name, f"{param_name} timing parameter")
                    validation_info = f"\n\n--- JEDEC Validation ---\n"
                    validation_info += f"Memory Speed: DDR5-{memory_speed}\n"
                    validation_info += f"tCK(avg): {tck_avg_ns:.3f}ns\n"
                    validation_info += f"Actual: {value} tCK\n"
                    if validation['jedec_min_nck']:
                        validation_info += f"JEDEC Min: {validation['jedec_min_nck']} tCK\n"
                        validation_info += f"Margin: +{validation['margin']} tCK\n"
                    validation_info += f"Status: {validation['compliance']}"
                    
                    # Add MR13 validation info if available
                    if mr13_validation and mr13_validation.get('valid') and mr13_validation.get('mr13_info'):
                        mr13_info = mr13_validation['mr13_info']
                        validation_info += f"\n\n--- MR13 Mode Register Validation ---\n"
                        validation_info += f"Expected MR13 OP[3:0]: {mr13_info['binary']} ({mr13_info['hex']})\n"
                        validation_info += f"Data Rate Range: {mr13_info['config']['description']}\n"
                        
                        timing_results = mr13_validation.get('timing_results', {})
                        for timing_name, result in timing_results.items():
                            if timing_name in ['tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2']:
                                status = "✓ PASS" if result['valid'] else "✗ FAIL"
                                validation_info += f"{timing_name}: {result['actual']} tCK (min: {result['expected']}) {status}\n"
                    
                    # Create new tooltip with validation info
                    old_tooltip = getattr(label_widget, 'tooltip', None)
                    if old_tooltip:
                        old_tooltip.hidetip()
                    label_widget.tooltip = ToolTip(label_widget, base_tooltip + validation_info)

