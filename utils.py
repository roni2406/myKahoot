# utils.py
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

class CustomStyle:
    # Color scheme
    PRIMARY_COLOR = "#4a90e2"  # Blue
    SECONDARY_COLOR = "#2ecc71"  # Green
    BACKGROUND_COLOR = "#f5f6fa"  # Light gray
    TEXT_COLOR = "#2c3e50"  # Dark blue
    BUTTON_HOVER = "#357abd"  # Darker blue
    ERROR_COLOR = "#e74c3c"  # Red
    
    @staticmethod
    def setup_styles():
        style = ttk.Style()
        style.configure("Custom.TButton",
                       padding=10,
                       background=CustomStyle.PRIMARY_COLOR,
                       foreground="black")
        
        style.configure("Success.TButton",
                       padding=10,
                       background=CustomStyle.SECONDARY_COLOR,
                       foreground="black")
        
        style.configure("Custom.TFrame",
                       background=CustomStyle.BACKGROUND_COLOR)
        
        style.configure("Custom.TLabel",
                       background=CustomStyle.BACKGROUND_COLOR,
                       foreground=CustomStyle.TEXT_COLOR,
                       padding=5)

