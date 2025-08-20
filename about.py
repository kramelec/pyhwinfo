import tkinter as tk
from tkinter import ttk
import webbrowser
import platform

class AboutDialog:
    def __init__(self, parent, appver):
        self.parent = parent
        self.appver = appver
        self.window = tk.Toplevel(parent)
        self.setup_window()
        self.create_widgets()
    
    def setup_window(self):
        self.window.title("About")
        #self.window.geometry("450x300")
        self.window.resizable(False, False)
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.window.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
    
    def open_url(self, url):
        webbrowser.open(url)
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        icon_frame = ttk.Frame(main_frame)
        icon_frame.pack(pady = (0, 15))
        
        title_label = ttk.Label( main_frame, text = "pyhwinfo - memory info", font = ("Segoe UI", 18, "bold") )
        title_label.pack(pady = (0, 5))
        
        version_label = ttk.Label( main_frame, text = f"Version {self.appver}", font = ("Arial", 12) )
        version_label.pack(pady = (0, 10))
        
        #desc_text = """A powerful application built with Python and Tkinter."""
        #desc_label = ttk.Label( main_frame, text = desc_text, font=("Arial", 10), justify = tk.CENTER )
        #desc_label.pack(pady=(0, 15))

        author_frame = ttk.Frame(main_frame)
        author_frame.pack(pady = (0, 15))
        ttk.Label(author_frame, text="Author:").pack()
        author_link = ttk.Label( author_frame, text = "remittor", font=("Consolas", 10, "underline"), foreground = "blue", cursor = "hand2" )
        author_link.pack()
        author_link.bind("<Button-1>", lambda e: self.open_url("https://github.com/remittor"))
        
        github_frame = ttk.Frame(main_frame)
        github_frame.pack(pady = (0, 15))
        ttk.Label(github_frame, text="Source code:").pack()
        github_link = ttk.Label( github_frame, text = "GitHub Repository", font=("Consolas", 10, "underline"), foreground = "blue", cursor = "hand2" )
        github_link.pack()
        github_link.bind("<Button-2>", lambda e: self.open_url("https://github.com/remittor/pyhwinfo"))
        
        sys_info = f"Python {platform.python_version()} | {platform.system()} {platform.release()}"
        sys_label = ttk.Label( main_frame, text = sys_info, font=("Arial", 9), foreground = "gray" )
        sys_label.pack(pady = (10, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady = (20, 0))
        close_btn = ttk.Button( button_frame, text = "Close", command = self.window.destroy, width = 15 )
        close_btn.pack()
        
        self.window.bind('<Return>', lambda e: self.window.destroy())
        close_btn.focus_set()
