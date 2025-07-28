#
# Intel Memory Latency Checker (MLC) Integration
# Copyright (C) 2025 remittor
#

import os
import subprocess
import threading
import time
import re
import statistics
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class MLCTool:
    """Intel Memory Latency Checker (MLC) integration tool"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.mlc_path = None
        self.is_running = False
        self.results = []
        self.thread = None
        
    def find_mlc_executable(self):
        """Find MLC executable in common locations"""
        possible_paths = [
            "mlc.exe",  # Current directory
            "./mlc.exe",  # Current directory explicit
            r"C:\Program Files\Intel\MLC\mlc.exe",
            r"C:\Intel\MLC\mlc.exe",
            r"C:\Tools\MLC\mlc.exe",
            r"C:\_system\Intel MLC\mlc.exe",
            os.path.join(os.getcwd(), "mlc.exe"),
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None
    
    def browse_for_mlc(self):
        """Browse for MLC executable"""
        file_path = filedialog.askopenfilename(
            title="Select Intel MLC executable",
            filetypes=[
                ("Executable files", "*.exe"),
                ("All files", "*.*")
            ],
            initialdir=os.getcwd()
        )
        
        if file_path and os.path.isfile(file_path):
            # Verify it's the correct MLC by checking version
            try:
                # Use bundled Python environment for verification too
                project_dir = os.path.dirname(os.path.abspath(__file__))
                python_exe = os.path.join(project_dir, "python", "python.exe")
                
                env = os.environ.copy()
                python_dir = os.path.join(project_dir, "python")
                if os.path.exists(python_exe):
                    env['PATH'] = python_dir + os.pathsep + env.get('PATH', '')
                    env['PYTHONHOME'] = python_dir
                    env['PYTHONPATH'] = python_dir
                
                result = subprocess.run([file_path, "--help"], 
                                      capture_output=True, text=True, timeout=10,
                                      env=env, cwd=project_dir)
                if "Intel(R) Memory Latency Checker" in result.stdout or "Memory Latency Checker" in result.stdout:
                    self.mlc_path = file_path
                    return True
                else:
                    messagebox.showerror("Error", 
                                       "Selected file doesn't appear to be Intel MLC.\n"
                                       "Please select the correct mlc.exe file.")
                    return False
            except Exception as e:
                messagebox.showerror("Error", f"Failed to verify MLC executable:\n{str(e)}")
                return False
        return False
    
    def get_cpu_count(self):
        """Get number of CPU cores for measurement"""
        try:
            import multiprocessing
            return multiprocessing.cpu_count()
        except:
            return 4  # Default fallback
    
    def parse_mlc_output(self, output):
        """Parse MLC output to extract latency and bandwidth values"""
        results = {
            'latency_ns': None,
            'bandwidth_mbps': None,
            'raw_output': output
        }
        
        lines = output.split('\n')
        
        # Look for idle latency results - try multiple patterns
        for line in lines:
            line = line.strip()
            
            # Pattern 1: "Each iteration took X base frequency clocks (Y ns)"
            # This is the main format for MLC idle latency output
            # Handle possible whitespace/tabs around the ns value
            iteration_match = re.search(r'Each iteration took.*?\(\s*(\d+\.?\d*)\s*ns\)', line, re.IGNORECASE)
            if iteration_match:
                try:
                    results['latency_ns'] = float(iteration_match.group(1))
                    continue
                except ValueError:
                    pass
            
            # Pattern 2: "Idle latency (in ns): 123.4"
            latency_match = re.search(r'Idle latency.*?:\s*(\d+\.?\d*)', line, re.IGNORECASE)
            if latency_match:
                try:
                    results['latency_ns'] = float(latency_match.group(1))
                    continue
                except ValueError:
                    pass
            
            # Pattern 3: Look for lines with "ns" that might be latency
            latency_match2 = re.search(r'(\d+\.?\d*)\s*ns', line, re.IGNORECASE)
            if latency_match2 and 'latency' in line.lower():
                try:
                    results['latency_ns'] = float(latency_match2.group(1))
                    continue
                except ValueError:
                    pass
            
            # Pattern for bandwidth: various formats possible
            # Look for bandwidth in MB/s, GB/s
            bandwidth_match = re.search(r'(\d+\.?\d*)\s*MB/s', line, re.IGNORECASE)
            if bandwidth_match:
                try:
                    results['bandwidth_mbps'] = float(bandwidth_match.group(1))
                    continue
                except ValueError:
                    pass
            
            # Look for GB/s and convert to MB/s
            bandwidth_match_gb = re.search(r'(\d+\.?\d*)\s*GB/s', line, re.IGNORECASE)
            if bandwidth_match_gb:
                try:
                    results['bandwidth_mbps'] = float(bandwidth_match_gb.group(1)) * 1024
                    continue
                except ValueError:
                    pass
            
            # Look for MLC typical bandwidth output format
            # "00000  23456.78" where the number after whitespace is the bandwidth
            if re.match(r'^\d+\s+\d+\.?\d*$', line):
                try:
                    parts = line.split()
                    if len(parts) == 2:
                        bandwidth_value = float(parts[1])
                        # Assume it's in MB/s if it's a reasonable value
                        if 100 <= bandwidth_value <= 200000:  # Reasonable bandwidth range
                            results['bandwidth_mbps'] = bandwidth_value
                            continue
                except ValueError:
                    pass
            
            # Look for "Maximum injection bandwidth" or similar
            if 'bandwidth' in line.lower() and ('maximum' in line.lower() or 'peak' in line.lower()):
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    try:
                        bandwidth_value = float(numbers[-1])  # Take the last number
                        if 100 <= bandwidth_value <= 200000:  # Reasonable bandwidth range
                            results['bandwidth_mbps'] = bandwidth_value
                            continue
                    except ValueError:
                        pass
        
        return results
    
    def run_single_measurement(self, cpu_id=4):
        """Run a single MLC measurement"""
        if not self.mlc_path:
            raise RuntimeError("MLC executable not found")
        
        # Use the bundled Python interpreter from the python folder
        project_dir = os.path.dirname(os.path.abspath(__file__))
        python_exe = os.path.join(project_dir, "python", "python.exe")
        
        # Prepare environment to use bundled Python
        env = os.environ.copy()
        python_dir = os.path.join(project_dir, "python")
        if os.path.exists(python_exe):
            # Set PATH to include the bundled Python directory first
            env['PATH'] = python_dir + os.pathsep + env.get('PATH', '')
            env['PYTHONHOME'] = python_dir
            env['PYTHONPATH'] = python_dir
        
        # Only run latency measurement for speed - bandwidth takes much longer
        latency_cmd = [self.mlc_path, "--idle_latency", f"-c{cpu_id}", f"-i{cpu_id}"]
        
        results = {
            'latency_ns': None,
            'bandwidth_mbps': None,
            'raw_output': ''
        }
        
        try:
            # Run latency measurement
            latency_result = subprocess.run(latency_cmd, capture_output=True, text=True, 
                                          timeout=30, creationflags=subprocess.CREATE_NO_WINDOW,
                                          cwd=project_dir, env=env)
            
            results['raw_output'] = f"LATENCY MEASUREMENT:\n{latency_result.stdout}"
            if latency_result.stderr:
                results['raw_output'] += f"\nSTDERR:\n{latency_result.stderr}"
            
            if latency_result.returncode == 0:
                latency_parsed = self.parse_mlc_output(latency_result.stdout)
                results['latency_ns'] = latency_parsed['latency_ns']
            else:
                raise RuntimeError(f"MLC latency measurement failed with return code {latency_result.returncode}\n"
                                 f"Error: {latency_result.stderr}")
            
            return results
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("MLC measurement timed out (30 seconds)")
        except Exception as e:
            raise RuntimeError(f"Failed to run MLC: {str(e)}")
    
    def run_measurements(self, count=5, progress_callback=None, complete_callback=None):
        """Run multiple MLC measurements and calculate averages"""
        
        def measurement_thread():
            try:
                self.is_running = True
                self.results = []
                
                cpu_count = self.get_cpu_count()
                # Use CPU ID that's likely to be valid (usually CPU 4 or middle of range)
                cpu_id = min(4, cpu_count - 1) if cpu_count > 4 else 0
                
                latencies = []
                bandwidths = []
                
                for i in range(count):
                    if not self.is_running:  # Check for cancellation
                        break
                        
                    if progress_callback:
                        progress_callback(i + 1, count, f"Running measurement {i + 1}/{count}...")
                    
                    try:
                        result = self.run_single_measurement(cpu_id)
                        self.results.append(result)
                        
                        if result['latency_ns'] is not None:
                            latencies.append(result['latency_ns'])
                        if result['bandwidth_mbps'] is not None:
                            bandwidths.append(result['bandwidth_mbps'])
                            
                    except Exception as e:
                        error_result = {
                            'latency_ns': None,
                            'bandwidth_mbps': None,
                            'error': str(e),
                            'raw_output': f"Error: {str(e)}"
                        }
                        self.results.append(error_result)
                
                # Calculate averages
                avg_latency = statistics.mean(latencies) if latencies else None
                avg_bandwidth = statistics.mean(bandwidths) if bandwidths else None
                
                final_results = {
                    'individual_results': self.results,
                    'average_latency_ns': avg_latency,
                    'average_bandwidth_mbps': avg_bandwidth,
                    'successful_measurements': len(latencies),
                    'total_measurements': count,
                    'cpu_id_used': cpu_id
                }
                
                if complete_callback:
                    complete_callback(final_results)
                    
            except Exception as e:
                error_results = {
                    'error': str(e),
                    'individual_results': [],
                    'average_latency_ns': None,
                    'average_bandwidth_mbps': None,
                    'successful_measurements': 0,
                    'total_measurements': count
                }
                if complete_callback:
                    complete_callback(error_results)
            finally:
                self.is_running = False
        
        # Start measurement in separate thread
        self.thread = threading.Thread(target=measurement_thread, daemon=True)
        self.thread.start()
    
    def cancel_measurements(self):
        """Cancel running measurements"""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            # Note: We can't forcefully terminate the subprocess from here
            # but we can stop starting new measurements
            pass


class MLCDialog:
    """Dialog window for MLC measurements"""
    
    def __init__(self, parent, mlc_tool):
        self.parent = parent
        self.mlc_tool = mlc_tool
        self.dialog = None
        self.progress_var = None
        self.status_var = None
        self.results_text = None
        self.run_button = None
        self.cancel_button = None
        self.browse_button = None
        self.close_button = None
        self.measurement_count_var = None
        
    def show_dialog(self):
        """Show the MLC measurement dialog"""
        if self.dialog:
            self.dialog.destroy()
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Intel Memory Latency Checker (MLC)")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # MLC path section
        path_frame = ttk.LabelFrame(main_frame, text="MLC Executable")
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        path_inner = ttk.Frame(path_frame, padding=5)
        path_inner.pack(fill=tk.X)
        
        # Check if MLC is already set (manually selected) or auto-detect
        if self.mlc_tool.mlc_path:
            # Use already set path (from manual selection)
            status_text = f"Selected: {self.mlc_tool.mlc_path}"
            status_color = "green"
        else:
            # Try auto-detection
            mlc_path = self.mlc_tool.find_mlc_executable()
            if mlc_path:
                self.mlc_tool.mlc_path = mlc_path
                status_text = f"Found: {mlc_path}"
                status_color = "green"
            else:
                status_text = "Not found - Please browse for mlc.exe"
                status_color = "red"
        
        ttk.Label(path_inner, text="Status:").pack(side=tk.LEFT)
        status_label = ttk.Label(path_inner, text=status_text, foreground=status_color)
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.browse_button = ttk.Button(path_inner, text="Browse...", 
                                      command=self.browse_for_mlc)
        self.browse_button.pack(side=tk.RIGHT)
        
        # Measurement settings
        settings_frame = ttk.LabelFrame(main_frame, text="Measurement Settings")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        settings_inner = ttk.Frame(settings_frame, padding=5)
        settings_inner.pack(fill=tk.X)
        
        ttk.Label(settings_inner, text="Number of measurements:").pack(side=tk.LEFT)
        self.measurement_count_var = tk.StringVar(value="5")
        count_spinbox = ttk.Spinbox(settings_inner, from_=1, to=20, width=5,
                                   textvariable=self.measurement_count_var)
        count_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Info label
        info_text = ("Each measurement runs 'mlc.exe --idle_latency' to measure DDR5 DRAM latency.\n"
                    "Results are averaged across all measurements for better accuracy.")
        info_label = ttk.Label(settings_inner, text=info_text, font=("Segoe UI", 8))
        info_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        progress_inner = ttk.Frame(progress_frame, padding=5)
        progress_inner.pack(fill=tk.X)
        
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_inner, variable=self.progress_var, 
                                     maximum=100, length=300)
        progress_bar.pack(side=tk.LEFT)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(progress_inner, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.run_button = ttk.Button(control_frame, text="Run Measurements",
                                   command=self.start_measurements)
        self.run_button.pack(side=tk.LEFT)
        
        self.cancel_button = ttk.Button(control_frame, text="Cancel",
                                      command=self.cancel_measurements, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=(5, 0))
        
        self.close_button = ttk.Button(control_frame, text="Close",
                                     command=self.close_dialog)
        self.close_button.pack(side=tk.RIGHT)
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        results_inner = ttk.Frame(results_frame, padding=5)
        results_inner.pack(fill=tk.BOTH, expand=True)
        
        # Results text with scrollbar
        text_frame = ttk.Frame(results_inner)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_text = tk.Text(text_frame, yscrollcommand=scrollbar.set,
                                   font=("Consolas", 9), wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.results_text.yview)
        
        # Initial message
        self.results_text.insert(tk.END, 
            "Intel® Memory Latency Checker (MLC) Integration\n"
            "================================================\n\n"
            "This tool runs multiple MLC measurements to determine:\n"
            "• DDR5 DRAM idle latency (nanoseconds)\n"
            "• Fast measurements focused on latency\n\n"
            "Click 'Run Measurements' to start...\n"
        )
        self.results_text.config(state=tk.DISABLED)
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Focus on dialog
        self.dialog.focus_set()
        
        # Enable/disable run button based on MLC availability
        if not self.mlc_tool.mlc_path:
            self.run_button.config(state=tk.DISABLED)
    
    def browse_for_mlc(self):
        """Browse for MLC executable"""
        if self.mlc_tool.browse_for_mlc():
            # Update status without closing dialog
            messagebox.showinfo("Success", f"MLC executable selected:\n{self.mlc_tool.mlc_path}")
            # Enable the run button
            self.run_button.config(state=tk.NORMAL)
            # Don't close and reopen dialog - just update the status display
            # Find and update the status label directly
            for widget in self.dialog.winfo_children():
                self._update_status_labels(widget)
    
    def _update_status_labels(self, widget):
        """Recursively update status labels in the dialog"""
        if isinstance(widget, ttk.Label):
            current_text = widget.cget('text')
            if 'Not found' in current_text or 'Found:' in current_text or 'Selected:' in current_text:
                widget.config(text=f"Selected: {self.mlc_tool.mlc_path}", foreground="green")
        
        # Recursively check children
        for child in widget.winfo_children():
            self._update_status_labels(child)
    
    def start_measurements(self):
        """Start MLC measurements"""
        if not self.mlc_tool.mlc_path:
            messagebox.showerror("Error", "Please select MLC executable first.")
            return
        
        try:
            count = int(self.measurement_count_var.get())
            if count < 1 or count > 20:
                raise ValueError("Count must be between 1 and 20")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of measurements (1-20).")
            return
        
        # Update UI state
        self.run_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.browse_button.config(state=tk.DISABLED)
        
        # Clear results
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Starting MLC measurements...\n\n")
        self.results_text.config(state=tk.DISABLED)
        
        # Start measurements
        self.mlc_tool.run_measurements(
            count=count,
            progress_callback=self.update_progress,
            complete_callback=self.measurement_complete
        )
    
    def update_progress(self, current, total, status):
        """Update progress bar and status"""
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.status_var.set(status)
        
        # Update results text
        self.results_text.config(state=tk.NORMAL)
        self.results_text.insert(tk.END, f"{status}\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=tk.DISABLED)
        
        # Update UI
        self.dialog.update_idletasks()
    
    def measurement_complete(self, results):
        """Handle measurement completion"""
        # Update UI state
        self.run_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.browse_button.config(state=tk.NORMAL)
        self.progress_var.set(100)
        self.status_var.set("Complete")
        
        # Display results
        self.results_text.config(state=tk.NORMAL)
        self.results_text.insert(tk.END, "\n" + "="*50 + "\n")
        self.results_text.insert(tk.END, "MEASUREMENT RESULTS\n")
        self.results_text.insert(tk.END, "="*50 + "\n\n")
        
        if 'error' in results:
            self.results_text.insert(tk.END, f"ERROR: {results['error']}\n")
        else:
            successful = results['successful_measurements']
            total = results['total_measurements']
            
            self.results_text.insert(tk.END, f"Successful measurements: {successful}/{total}\n")
            self.results_text.insert(tk.END, f"CPU ID used: {results['cpu_id_used']}\n\n")
            
            if results['average_latency_ns'] is not None:
                self.results_text.insert(tk.END, 
                    f"AVERAGE LATENCY: {results['average_latency_ns']:.2f} ns\n")
            
            if results['average_bandwidth_mbps'] is not None:
                self.results_text.insert(tk.END, 
                    f"AVERAGE BANDWIDTH: {results['average_bandwidth_mbps']:.2f} MB/s\n")
            
            self.results_text.insert(tk.END, "\nIndividual measurements:\n")
            self.results_text.insert(tk.END, "-" * 30 + "\n")
            
            for i, result in enumerate(results['individual_results']):
                self.results_text.insert(tk.END, f"Measurement {i+1}: ")
                if 'error' in result:
                    self.results_text.insert(tk.END, f"ERROR - {result['error']}\n")
                else:
                    if result['latency_ns'] is not None:
                        self.results_text.insert(tk.END, f"Latency: {result['latency_ns']:.2f} ns")
                    if result['bandwidth_mbps'] is not None:
                        self.results_text.insert(tk.END, f", Bandwidth: {result['bandwidth_mbps']:.2f} MB/s")
                    self.results_text.insert(tk.END, "\n")
            
            # Add debug information - show raw MLC output
            self.results_text.insert(tk.END, "\n" + "="*50 + "\n")
            self.results_text.insert(tk.END, "DEBUG: RAW MLC OUTPUT\n")
            self.results_text.insert(tk.END, "="*50 + "\n")
            for i, result in enumerate(results['individual_results']):
                if 'raw_output' in result and result['raw_output']:
                    self.results_text.insert(tk.END, f"\nMeasurement {i+1} Raw Output:\n")
                    self.results_text.insert(tk.END, "-" * 30 + "\n")
                    self.results_text.insert(tk.END, result['raw_output'])
                    self.results_text.insert(tk.END, "\n" + "-" * 30 + "\n")
        
        self.results_text.see(tk.END)
        self.results_text.config(state=tk.DISABLED)
    
    def cancel_measurements(self):
        """Cancel running measurements"""
        self.mlc_tool.cancel_measurements()
        self.status_var.set("Cancelling...")
        
        # Reset UI state after a short delay
        def reset_ui():
            self.run_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            self.browse_button.config(state=tk.NORMAL)
            self.status_var.set("Cancelled")
        
        self.dialog.after(1000, reset_ui)
    
    def close_dialog(self):
        """Close the dialog"""
        if self.mlc_tool.is_running:
            if messagebox.askyesno("Confirm", "Measurements are running. Cancel and close?"):
                self.mlc_tool.cancel_measurements()
            else:
                return
        
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
