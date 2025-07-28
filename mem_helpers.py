import sys
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

