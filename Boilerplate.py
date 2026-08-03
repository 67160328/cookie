import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
import numpy as np
import pyautogui
import keyboard
import threading
import time
import random
from PIL import Image, ImageTk
import os
import json
import queue
import mss
import win32api
import win32con
import re
import winocr

# Disable pyautogui safety pause for high speed
pyautogui.PAUSE = 0.0

def nms(boxes, overlap_thresh=0.4):
    """
    boxes: list of [x, y, w, h, score]
    """
    if not boxes:
        return []
    
    # Sort by score descending
    boxes = sorted(boxes, key=lambda x: x[4], reverse=True)
    keep = []
    
    while boxes:
        current = boxes.pop(0)
        keep.append(current)
        
        remaining = []
        cx, cy, cw, ch = current[0], current[1], current[2], current[3]
        for box in boxes:
            bx, by, bw, bh = box[0], box[1], box[2], box[3]
            
            # Distance check for same sized templates
            dist_x = abs(cx - bx)
            dist_y = abs(cy - by)
            if dist_x < cw * overlap_thresh and dist_y < ch * overlap_thresh:
                continue
            remaining.append(box)
        boxes = remaining
        
    return keep

# Set customtkinter appearance and light mode for blue & white theme
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Theme Colors (Premium Modern Slate Blue & White)
BG_COLOR = "#F8FAFC"        # Slate 50 - Very clean, light blue-gray background
CARD_BG = "#FFFFFF"         # Pure white card background
HEADER_BG = "#1E3A8A"       # Premium Slate/Navy blue header banner
ACCENT_ORANGE = "#3B82F6"   # Soft Slate Blue accent (Tailwind Blue 500)
ACCENT_HOVER = "#2563EB"    # Blue 600
TEXT_MUTED = "#64748B"      # Slate 500 - Muted text
STATUS_ACTIVE = "#10B981"   # Emerald 500
STATUS_IDLE = "#EF4444"     # Red 500
DELETE_RED = "#EF4444"      # Red 500
DELETE_HOVER = "#DC2626"    # Red 600
POINT_TAG_COLOR = "#E2E8F0" # Slate 200

# Adaptive Text Color
TEXT_COLOR = ("#1E293B", "#FFFFFF")

class CoordinatePicker:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        
        # Hide parent main window
        self.parent.withdraw()
        
        # Create full-screen translucent overlay
        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.35)
        self.overlay.attributes("-topmost", True)
        self.overlay.config(cursor="crosshair")
        self.overlay.configure(bg="#000000")
        
        # Title/Instructions overlay text
        instruction_frame = tk.Frame(self.overlay, bg="#1A1A1E", bd=2, highlightbackground=ACCENT_ORANGE, highlightthickness=1)
        instruction_frame.place(relx=0.5, rely=0.1, anchor="center")
        
        label = tk.Label(
            instruction_frame, 
            text=" คลิกซ้ายจุดที่ต้องการบนหน้าจอเพื่อเลือกพิกัด | กด ESC เพื่อยกเลิก ", 
            fg="#FFFFFF", 
            bg="#1A1A1E", 
            font=("Segoe UI", 14, "bold")
        )
        label.pack(padx=15, pady=10)
        
        self.overlay.bind("<Button-1>", self.on_click)
        self.overlay.bind("<Escape>", self.on_cancel)
        
    def on_click(self, event):
        x, y = event.x_root, event.y_root
        self.overlay.destroy()
        self.parent.deiconify()  # Restore parent
        self.callback(x, y)
        
    def on_cancel(self, event):
        self.overlay.destroy()
        self.parent.deiconify()  # Restore parent


class RegionPicker:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        
        # Hide parent main window
        self.parent.withdraw()
        
        # Create full-screen translucent overlay
        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.35)
        self.overlay.attributes("-topmost", True)
        self.overlay.config(cursor="crosshair")
        self.overlay.configure(bg="#000000")
        
        self.canvas = tk.Canvas(self.overlay, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        # Title/Instructions overlay text
        instruction_frame = tk.Frame(self.canvas, bg="#1A1A1E", bd=2, highlightbackground=ACCENT_ORANGE, highlightthickness=1)
        instruction_frame.place(relx=0.5, rely=0.1, anchor="center")
        
        label = tk.Label(
            instruction_frame, 
            text=" คลิกซ้ายค้างไว้แล้วลากเพื่อกำหนดขอบเขตตรวจจับ | ปล่อยเมาส์เพื่อยืนยัน | กด ESC เพื่อยกเลิก ", 
            fg="#FFFFFF", 
            bg="#1A1A1E", 
            font=("Segoe UI", 14, "bold")
        )
        label.pack(padx=15, pady=10)
        
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.overlay.bind("<Escape>", self.on_cancel)
        
    def on_press(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, 
            outline=ACCENT_ORANGE, width=2
        )
        
    def on_drag(self, event):
        if self.rect_id:
            cur_x, cur_y = event.x_root, event.y_root
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)
            
    def on_release(self, event):
        end_x = event.x_root
        end_y = event.y_root
        
        x = min(self.start_x, end_x)
        y = min(self.start_y, end_y)
        w = abs(self.start_x - end_x)
        h = abs(self.start_y - end_y)
        
        self.overlay.destroy()
        self.parent.deiconify()  # Restore parent
        
        if w > 5 and h > 5:
            self.callback(x, y, w, h)
            
    def on_cancel(self, event):
        self.overlay.destroy()
        self.parent.deiconify()  # Restore parent


class RegionViewer:
    def __init__(self, parent, x, y, w, h):
        self.parent = parent
        
        # Hide parent main window
        self.parent.withdraw()
        
        # Create full-screen translucent overlay
        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.35)
        self.overlay.attributes("-topmost", True)
        self.overlay.config(cursor="arrow")
        self.overlay.configure(bg="#000000")
        
        self.canvas = tk.Canvas(self.overlay, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Draw target rectangle
        self.canvas.create_rectangle(
            x, y, x + w, y + h, 
            outline="#3B82F6", fill="#3B82F6", stipple="gray25", width=3
        )
        
        # Instructions/Title text
        instruction_frame = tk.Frame(self.canvas, bg="#1A1A1E", bd=2, highlightbackground="#3B82F6", highlightthickness=1)
        instruction_frame.place(relx=0.5, rely=0.1, anchor="center")
        
        label = tk.Label(
            instruction_frame, 
            text=f" ขอบเขตที่คุณตั้งไว้: X={x}, Y={y}, กว้าง={w}, สูง={h} | คลิกเมาส์หรือกดปุ่มใดๆ เพื่อกลับสู่โปรแกรม ", 
            fg="#FFFFFF", 
            bg="#1A1A1E", 
            font=("Segoe UI", 13, "bold")
        )
        label.pack(padx=15, pady=10)
        
        self.overlay.bind("<Button-1>", self.on_close)
        self.overlay.bind("<Button-3>", self.on_close)
        self.overlay.bind("<Key>", self.on_close)
        
    def on_close(self, event):
        self.overlay.destroy()
        self.parent.deiconify()


class ScreenCapturePicker:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        
        # Hide parent main window
        self.parent.withdraw()
        
        # Create full-screen translucent overlay
        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.35)
        self.overlay.attributes("-topmost", True)
        self.overlay.config(cursor="crosshair")
        self.overlay.configure(bg="#000000")
        
        self.canvas = tk.Canvas(self.overlay, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        # Title/Instructions overlay text
        instruction_frame = tk.Frame(self.canvas, bg="#1A1A1E", bd=2, highlightbackground=ACCENT_ORANGE, highlightthickness=1)
        instruction_frame.place(relx=0.5, rely=0.1, anchor="center")
        
        label = tk.Label(
            instruction_frame, 
            text=" คลิกซ้ายค้างไว้แล้วลากเพื่อครอบตัดรูปภาพเงื่อนไข | ปล่อยเมาส์เพื่อแคปเจอร์ | กด ESC เพื่อยกเลิก ", 
            fg="#FFFFFF", 
            bg="#1A1A1E", 
            font=("Segoe UI", 14, "bold")
        )
        label.pack(padx=15, pady=10)
        
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.overlay.bind("<Escape>", self.on_cancel)
        
    def on_press(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, 
            outline=ACCENT_ORANGE, width=2
        )
        
    def on_drag(self, event):
        if self.rect_id:
            cur_x, cur_y = event.x_root, event.y_root
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)
            
    def on_release(self, event):
        end_x = event.x_root
        end_y = event.y_root
        
        x = min(self.start_x, end_x)
        y = min(self.start_y, end_y)
        w = abs(self.start_x - end_x)
        h = abs(self.start_y - end_y)
        
        # Hide overlay before taking screenshot to avoid capturing the overlay itself
        self.overlay.withdraw()
        self.parent.update()
        time.sleep(0.15)  # Safety buffer for overlay window to hide
        
        if w > 5 and h > 5:
            # Capture using pyautogui screenshot
            try:
                # pyautogui.screenshot takes (left, top, width, height) on Windows
                img = pyautogui.screenshot(region=(x, y, w, h))
                self.callback(img)
            except Exception as e:
                print(f"Error capturing screen: {e}")
                self.callback(None)
        else:
            self.callback(None)
            
        self.overlay.destroy()
        self.parent.deiconify()  # Restore parent
        
    def on_cancel(self, event):
        self.overlay.destroy()
        self.parent.deiconify()  # Restore parent
        self.callback(None)


class CTkToolTip:
    """Sleek, modern floating tooltip window helper for CustomTkinter widgets"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        
    def enter(self, event=None):
        self.schedule()
        
    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()
        
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(200, self.show_tip) # 200ms delay for snappiness
        
    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
            
    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        
        # Position tooltip slightly to the left of the button to prevent overlap
        x = self.widget.winfo_rootx() - 170
        y = self.widget.winfo_rooty() + 2
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Premium dark mode style tooltip for high contrast
        bg_color = "#0F172A" # slate-900
        fg_color = "#F8FAFC" # slate-50
        border_color = "#F97316" # accent orange highlight
        
        label = tk.Label(
            tw, 
            text=self.text, 
            justify="left",
            background=bg_color, 
            foreground=fg_color, 
            relief="solid", 
            borderwidth=1,
            highlightcolor=border_color,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4
        )
        label.pack()
        
    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class FreecameAutoApp(ctk.CTk):
    def flash_card_border(self, card, count=0):
        if not card.winfo_exists():
            return
        colors = ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE", "#F8FAFC"]
        if count < len(colors):
            card.configure(border_color=colors[count], border_width=2)
            self.after(55, lambda: self.flash_card_border(card, count + 1))
        else:
            card.configure(border_width=0)

    def flash_point_row(self, row_frame, count=0):
        if not row_frame.winfo_exists():
            return
        colors = ["#3B82F6", "#60A5FA", "#93C5FD", "#E2E8F0", POINT_TAG_COLOR]
        if count < len(colors):
            row_frame.configure(fg_color=colors[count])
            self.after(65, lambda: self.flash_point_row(row_frame, count + 1))
        else:
            row_frame.configure(fg_color=POINT_TAG_COLOR)

    def __init__(self):
        super().__init__()
        
        self.title("FREECAME AUTO CLICKER")
        self.geometry("1100x860")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        
        # Threading / State variables
        self.bot_running = False
        self.bot_thread = None
        self.log_queue = queue.Queue()
        
        # Multi-Step Sequence Data
        self.steps = []
        self.turbo_mode_var = tk.BooleanVar(value=True)
        
        # Telegram Notification Settings
        self.telegram_bot_token_var = tk.StringVar(value="")
        self.telegram_chat_id_var = tk.StringVar(value="")
        self.telegram_global_enabled_var = tk.BooleanVar(value=False)
        self.telegram_monitor_normal_var = tk.BooleanVar(value=True)
        self.telegram_monitor_counting_var = tk.BooleanVar(value=True)
        self.telegram_monitor_ocr_var = tk.BooleanVar(value=True)
        
        # Analytics Data
        self.stats_data = {
            "start_time": None,
            "total_scan_cycles": 0,
            "triggers_count": {},        # step_id -> count
            "ocr_sum_history": [],        # list of floats (last 30 sum values)
            "counting_history": {}        # template_filename -> list of counts
        }
        
        # Sidebar Toggle State
        self.show_jump_sidebar = True

        # Initialize UI Components
        self.setup_ui()
        
        # Add default first step
        self.add_step()
        
        # Register global keyboard emergency kill switch
        keyboard.add_hotkey("esc", self.emergency_stop)
        
        # Register tkinter window-level keyboard shortcuts
        self.register_shortcuts()
        
        # Start log polling loop
        self.poll_logs()

    def add_step_from_active_tab(self):
        active_tab = self.tabview.get()
        if active_tab == "🤖 ตั้งค่าบอตปกติ":
            self.add_step("บอตปกติ")
        elif active_tab == "🔍 นับวัตถุ & OCR":
            self.add_step("นับวัตถุ")
        else:
            self.add_step("บอตปกติ")

    def register_shortcuts(self):
        """Register all keyboard shortcuts for the main window."""
        # Ctrl+N → เพิ่มขั้นตอนใหม่
        self.bind_all("<Control-n>", lambda e: self.add_step_from_active_tab())
        self.bind_all("<Control-N>", lambda e: self.add_step_from_active_tab())

        # Ctrl+S → บันทึก
        self.bind_all("<Control-s>", lambda e: self.save_config())
        self.bind_all("<Control-S>", lambda e: self.save_config())

        # Ctrl+O → โหลด
        self.bind_all("<Control-o>", lambda e: self.load_config())
        self.bind_all("<Control-O>", lambda e: self.load_config())

        # F5 → Start / Stop bot toggle
        self.bind_all("<F5>", lambda e: self.toggle_bot())

        # Ctrl+T → Toggle Turbo Mode
        self.bind_all("<Control-t>", lambda e: self.turbo_mode_var.set(not self.turbo_mode_var.get()))
        self.bind_all("<Control-T>", lambda e: self.turbo_mode_var.set(not self.turbo_mode_var.get()))

        self.add_log("[★] Shortcuts: Ctrl+N=เพิ่มขั้นตอนตามแท็บปัจจุบัน  Ctrl+S=บันทึก  Ctrl+O=โหลด  F5=เริ่ม/หยุด  Ctrl+T=Turbo  ESC=หยุดฉุกเฉิน")

    def setup_ui(self):
        # --- HEADER BANNER ---
        header_frame = ctk.CTkFrame(self, fg_color=HEADER_BG, corner_radius=10, height=80)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        header_frame.pack_propagate(False)
        
        # Title Label
        title_label = ctk.CTkLabel(
            header_frame, 
            text="FREECAME AUTO", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(side="left", padx=20)
        
        # Status Badge
        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="IDLE",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#FFFFFF",
            fg_color=STATUS_IDLE,
            corner_radius=6,
            width=80,
            height=28
        )
        self.status_badge.pack(side="right", padx=20)

        # =========================================================================
        # GLOBAL TOOLBAR & CONTROLS (Always Visible)
        # =========================================================================
        global_toolbar = ctk.CTkFrame(self, fg_color="transparent")
        global_toolbar.pack(fill="x", padx=20, pady=(0, 5))

        # Save/Load/Turbo buttons on the left
        left_controls = ctk.CTkFrame(global_toolbar, fg_color="transparent")
        left_controls.pack(side="left")

        # Save Config Button
        self.save_btn = ctk.CTkButton(
            left_controls,
            corner_radius=8,
            text="💾 บันทึก [Ctrl+S]",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.save_config,
            height=30,
            width=100
        )
        self.save_btn.pack(side="left", padx=2)

        # Load Config Button
        self.load_btn = ctk.CTkButton(
            left_controls,
            corner_radius=8,
            text="📂 โหลด [Ctrl+O]",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.load_config,
            height=30,
            width=100
        )
        self.load_btn.pack(side="left", padx=2)

        # Delete Multiple Steps Button
        self.del_multi_steps_btn = ctk.CTkButton(
            left_controls,
            corner_radius=8,
            text="🗑️ ลบหลายขั้นตอน",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1.5,
            hover_color=("#FEE2E2", "#450a0a"),
            text_color=("#EF4444", "#F87171"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.open_delete_multiple_steps_dialog,
            height=30,
            width=120
        )
        self.del_multi_steps_btn.pack(side="left", padx=2)

        # Turbo switch
        self.turbo_switch = ctk.CTkSwitch(
            left_controls,
            text="Turbo [Ctrl+T]",
            variable=self.turbo_mode_var,
            progress_color=ACCENT_ORANGE,
            button_color=ACCENT_ORANGE,
            button_hover_color=ACCENT_HOVER,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.turbo_switch.pack(side="left", padx=10)

        # Shortcut hints bar (Left-aligned container on the right)
        hint_frame = ctk.CTkFrame(global_toolbar, fg_color=("#E2E8F0", "#13131A"), corner_radius=6, height=28)
        hint_frame.pack(side="right", fill="y", padx=5)
        hint_frame.pack_propagate(False)

        hints = [
            ("Ctrl+N", "เพิ่มขั้นตอน"),
            ("Ctrl+S", "บันทึก"),
            ("Ctrl+O", "โหลด"),
            ("F5", "เริ่ม/หยุดบอต"),
            ("Ctrl+T", "Turbo"),
            ("ESC", "หยุดฉุกเฉิน"),
        ]

        hints_inner = ctk.CTkFrame(hint_frame, fg_color="transparent")
        hints_inner.pack(side="left", padx=10, pady=2)

        for key, desc in hints:
            chip = ctk.CTkFrame(hints_inner, fg_color=("#F1F5F9", "#252530"), corner_radius=4)
            chip.pack(side="left", padx=4)
            ctk.CTkLabel(
                chip,
                text=key,
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color=ACCENT_ORANGE
            ).pack(side="left", padx=(5, 2), pady=2)
            ctk.CTkLabel(
                chip,
                text=desc,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=TEXT_MUTED
            ).pack(side="left", padx=(0, 5), pady=2)

        # =========================================================================
        # GLOBAL LOGS & CONTROL PANEL (Always Visible at the Bottom)
        # =========================================================================
        log_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=8, height=110)
        log_card.pack(side="bottom", fill="x", padx=20, pady=(5, 10))
        log_card.pack_propagate(False)
        
        ctk.CTkLabel(
            log_card, 
            text="ประวัติการทำงาน (Console Log)", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_ORANGE
        ).pack(anchor="w", padx=15, pady=(4, 1))
        
        self.log_textbox = ctk.CTkTextbox(
            log_card, 
            fg_color="#0F0F11", 
            text_color="#E0E0E5", 
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 6))
        self.log_textbox.configure(state="disabled")

        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 5))
        
        self.toggle_bot_btn = ctk.CTkButton(
            actions_frame,
            corner_radius=8,
            text="▶  เริ่มระบบบอต  (START BOT)  [F5]",
            fg_color=ACCENT_ORANGE, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self.toggle_bot
        )
        self.toggle_bot_btn.pack(fill="x")

        # --- TAB VIEW FOR MAIN NAVIGATION (In the Center) ---
        # Global layout container to hold Tabview and the Right Sidebar side-by-side
        center_layout_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_layout_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.tabview = ctk.CTkTabview(
            center_layout_frame,
            segmented_button_selected_color=ACCENT_ORANGE,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=("#E2E8F0", "#252530"),
            text_color=TEXT_COLOR,
            fg_color=BG_COLOR
        )
        self.tabview.pack(side="left", fill="both", expand=True)
        
        # Single unified global Jump Sidebar on the right side of the entire window
        self.jump_sidebar = ctk.CTkFrame(center_layout_frame, fg_color="transparent", width=40)
        self.jump_sidebar.pack(side="right", fill="y", padx=(10, 0))
        
        # Add Tabs
        self.tab_bot = self.tabview.add("🤖 ตั้งค่าบอตปกติ")
        self.tab_detection = self.tabview.add("🔍 นับวัตถุ & OCR")
        self.tab_analytics = self.tabview.add("📊 แดชบอร์ดวิเคราะห์ผล")
        self.tab_settings = self.tabview.add("⚙️ ตั้งค่าระบบ")
        
        # =========================================================================
        # TAB 1: NORMAL BOT SETUP
        # =========================================================================
        normal_toolbar = ctk.CTkFrame(self.tab_bot, fg_color="transparent")
        normal_toolbar.pack(fill="x", padx=10, pady=5)
        
        self.add_step_btn = ctk.CTkButton(
            normal_toolbar,
            corner_radius=8,
            text="+ เพิ่มขั้นตอนปกติ  [Ctrl+N]",
            fg_color=ACCENT_ORANGE, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda: self.add_step("บอตปกติ"),
            height=34
        )
        self.add_step_btn.pack(side="left", padx=0)
        
        self.btn_toggle_sidebar_normal = ctk.CTkButton(
            normal_toolbar,
            corner_radius=8,
            text="📍 ซ่อนแถบทางลัด",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=ACCENT_ORANGE,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.toggle_jump_sidebars,
            width=110,
            height=34
        )
        self.btn_toggle_sidebar_normal.pack(side="right", padx=0)

        self.steps_scroll_normal = ctk.CTkScrollableFrame(
            self.tab_bot, 
            fg_color=BG_COLOR, 
            scrollbar_button_color=CARD_BG,
            height=300
        )
        self.steps_scroll_normal.pack(fill="both", expand=True, padx=10, pady=5)
        self.apply_smooth_scroll(self.steps_scroll_normal)

        # =========================================================================
        # TAB 2: DETECTION SETUP (OBJECT COUNTING & OCR)
        # =========================================================================
        detection_toolbar = ctk.CTkFrame(self.tab_detection, fg_color="transparent")
        detection_toolbar.pack(fill="x", padx=10, pady=5)
        
        self.add_counting_btn = ctk.CTkButton(
            detection_toolbar,
            corner_radius=8,
            text="+ เพิ่มงานนับวัตถุ",
            fg_color=ACCENT_ORANGE, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda: self.add_step("นับวัตถุ"),
            height=34
        )
        self.add_counting_btn.pack(side="left", padx=(0, 6))

        self.add_ocr_btn = ctk.CTkButton(
            detection_toolbar,
            corner_radius=8,
            text="+ เพิ่มงานบวกเลข OCR",
            fg_color=ACCENT_ORANGE, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda: self.add_step("บวกเลข OCR"),
            height=34
        )
        self.add_ocr_btn.pack(side="left", padx=0)
        
        self.btn_toggle_sidebar_detection = ctk.CTkButton(
            detection_toolbar,
            corner_radius=8,
            text="📍 ซ่อนแถบทางลัด",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=ACCENT_ORANGE,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.toggle_jump_sidebars,
            width=110,
            height=34
        )
        self.btn_toggle_sidebar_detection.pack(side="right", padx=0)

        self.steps_scroll_detection = ctk.CTkScrollableFrame(
            self.tab_detection, 
            fg_color=BG_COLOR, 
            scrollbar_button_color=CARD_BG,
            height=300
        )
        self.steps_scroll_detection.pack(fill="both", expand=True, padx=10, pady=5)
        self.apply_smooth_scroll(self.steps_scroll_detection)
        
        # =========================================================================
        # TAB 2: ANALYTICS DASHBOARD
        # =========================================================================
        self.setup_analytics_tab()
        self.setup_settings_tab()

        # Log status info
        self.add_log("[*] ระบบ Freecame Auto Multi-Step พร้อมใช้งาน")
        self.add_log("[*] แต่ละเงื่อนไขสามารถเพิ่มจุดคลิกได้หลายจุด กดปุ่ม '+ เพิ่มจุดคลิก' เพื่อระบุหลายพิกัด")
        self.add_log("[*] กดปุ่ม 'ESC' ที่คีย์บอร์ดเพื่อหยุดการทำงานฉุกเฉินได้ตลอดเวลา")

    def setup_settings_tab(self):
        # Settings frame container
        settings_container = ctk.CTkScrollableFrame(
            self.tab_settings,
            fg_color=BG_COLOR,
            scrollbar_button_color=CARD_BG
        )
        settings_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Telegram Notification Settings Card
        tele_card = ctk.CTkFrame(settings_container, fg_color=CARD_BG, corner_radius=8, border_color=("#CBD5E1", "#1E293B"), border_width=1)
        tele_card.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            tele_card,
            text="✈️ ตั้งค่าการแจ้งเตือน Telegram (Telegram Alert Settings)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=ACCENT_ORANGE
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Enable Switch
        switch_frame = ctk.CTkFrame(tele_card, fg_color="transparent")
        switch_frame.pack(fill="x", padx=20, pady=5)
        
        tele_switch = ctk.CTkSwitch(
            switch_frame,
            text="เปิดใช้งานระบบแจ้งเตือนผ่าน Telegram (Global Telegram Alerts)",
            variable=self.telegram_global_enabled_var,
            progress_color=ACCENT_ORANGE,
            button_color=ACCENT_ORANGE,
            button_hover_color=ACCENT_HOVER,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        tele_switch.pack(side="left")
        
        # Bot Token Input
        token_frame = ctk.CTkFrame(tele_card, fg_color="transparent")
        token_frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(token_frame, text="Telegram Bot Token:", font=ctk.CTkFont(size=12), text_color=TEXT_COLOR, width=150, anchor="w").pack(side="left")
        
        token_entry = ctk.CTkEntry(
            token_frame,
            textvariable=self.telegram_bot_token_var,
            placeholder_text="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ...",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=TEXT_COLOR,
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            height=28
        )
        token_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Chat ID Input
        chat_frame = ctk.CTkFrame(tele_card, fg_color="transparent")
        chat_frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(chat_frame, text="Telegram Chat ID:", font=ctk.CTkFont(size=12), text_color=TEXT_COLOR, width=150, anchor="w").pack(side="left")
        
        chat_entry = ctk.CTkEntry(
            chat_frame,
            textvariable=self.telegram_chat_id_var,
            placeholder_text="-100123456789 (หรือ Chat ID ส่วนตัว)",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=TEXT_COLOR,
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            height=28
        )
        chat_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Checkboxes for mode monitoring selection
        modes_frame = ctk.CTkFrame(tele_card, fg_color="transparent")
        modes_frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(modes_frame, text="โหมดที่ต้องการตรวจสอบแจ้งเตือน:", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", pady=(0, 4))
        
        chk_mon_normal = ctk.CTkCheckBox(
            modes_frame,
            text="🤖 บอตปกติ",
            variable=self.telegram_monitor_normal_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            checkbox_width=16,
            checkbox_height=16,
            border_width=1.5,
            fg_color=ACCENT_ORANGE
        )
        chk_mon_normal.pack(side="left", padx=(0, 15))
        
        chk_mon_counting = ctk.CTkCheckBox(
            modes_frame,
            text="🔍 นับวัตถุ",
            variable=self.telegram_monitor_counting_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            checkbox_width=16,
            checkbox_height=16,
            border_width=1.5,
            fg_color=ACCENT_ORANGE
        )
        chk_mon_counting.pack(side="left", padx=(0, 15))
        
        chk_mon_ocr = ctk.CTkCheckBox(
            modes_frame,
            text="🔢 บวกเลข OCR",
            variable=self.telegram_monitor_ocr_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            checkbox_width=16,
            checkbox_height=16,
            border_width=1.5,
            fg_color=ACCENT_ORANGE
        )
        chk_mon_ocr.pack(side="left")

        # Test Connection Button
        btn_test = ctk.CTkButton(
            tele_card,
            corner_radius=8,
            text="⚡ ทดสอบส่งข้อความ (Test Telegram Alert)",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=ACCENT_ORANGE,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.send_test_telegram_alert,
            height=30
        )
        btn_test.pack(anchor="w", padx=20, pady=(10, 20))

    def send_test_telegram_alert(self):
        token = self.telegram_bot_token_var.get().strip()
        chat_id = self.telegram_chat_id_var.get().strip()
        
        if not token or not chat_id:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอก Telegram Bot Token และ Chat ID ให้ครบถ้วนก่อนการทดสอบ")
            return
            
        self.add_log("[*] กำลังส่งข้อความทดสอบไปยัง Telegram...")
        
        def worker():
            try:
                import urllib.request
                import urllib.parse
                import urllib.error
                import json
                
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                msg_text = "<b>[Freecame Auto Test]</b>\n🔔 การทดสอบเชื่อมต่อแจ้งเตือน Telegram สำเร็จเรียบร้อยแล้ว!"
                data = urllib.parse.urlencode({
                    "chat_id": chat_id,
                    "text": msg_text,
                    "parse_mode": "HTML"
                }).encode("utf-8")
                
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    res = json.loads(response.read().decode("utf-8"))
                    if res.get("ok"):
                        self.add_log(f"[✓] ส่งข้อความทดสอบ Telegram สำเร็จ!")
                        messagebox.showinfo("สำเร็จ", "ส่งข้อความทดสอบสำเร็จ! กรุณาตรวจสอบในห้องแชท Telegram ของคุณ")
                    else:
                        desc = res.get('description', 'Unknown API Error')
                        self.add_log(f"[Error] Telegram API error: {desc}")
                        messagebox.showerror("ล้มเหลว", f"เกิดข้อผิดพลาดจาก Telegram API:\n{desc}")
            except urllib.error.HTTPError as he:
                try:
                    err_body = he.read().decode("utf-8")
                    err_json = json.loads(err_body)
                    desc = err_json.get("description", err_body)
                except Exception:
                    desc = he.reason
                self.add_log(f"[Error] Telegram API HTTP Error {he.code}: {desc}")
                messagebox.showerror("ล้มเหลว", f"เกิดข้อผิดพลาดจาก Telegram API (HTTP {he.code}):\n{desc}\n\n*หมายเหตุ: บอตจะไม่สามารถส่งข้อความหาคุณได้จนกว่าคุณจะเข้าไปในแชทบอตตัวนั้นในแอป Telegram แล้วกดปุ่ม START (หรือส่งข้อความหาบอตก่อนอย่างน้อย 1 ครั้ง)")
            except Exception as e:
                self.add_log(f"[Error] ไม่สามารถส่งแจ้งเตือน Telegram ได้: {e}")
                messagebox.showerror("ล้มเหลว", f"ไม่สามารถเชื่อมต่อหรือส่งสัญญาณไปยัง Telegram ได้:\n{e}")
                
        threading.Thread(target=worker, daemon=True).start()

    def send_telegram_notification(self, message):
        token = self.telegram_bot_token_var.get().strip()
        chat_id = self.telegram_chat_id_var.get().strip()
        
        if not token or not chat_id:
            return
            
        def worker():
            try:
                import urllib.request
                import urllib.parse
                import urllib.error
                import json
                
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = urllib.parse.urlencode({
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }).encode("utf-8")
                
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    res = json.loads(response.read().decode("utf-8"))
                    if res.get("ok"):
                        self.add_log(f"[✓] ส่งแจ้งเตือน Telegram สำเร็จ")
                    else:
                        self.add_log(f"[Error] Telegram API error: {res.get('description')}")
            except urllib.error.HTTPError as he:
                try:
                    err_body = he.read().decode("utf-8")
                    err_json = json.loads(err_body)
                    desc = err_json.get("description", err_body)
                except Exception:
                    desc = he.reason
                self.add_log(f"[Error] Telegram API HTTP Error {he.code}: {desc}")
            except Exception as e:
                self.add_log(f"[Error] ไม่สามารถส่งแจ้งเตือน Telegram ได้: {e}")
                
        threading.Thread(target=worker, daemon=True).start()

    def setup_analytics_tab(self):
        # Top metric cards container
        metrics_frame = ctk.CTkFrame(self.tab_analytics, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=10, pady=10)
        
        # Grid layout for 3 metric cards
        metrics_frame.columnconfigure((0, 1, 2), weight=1, uniform="equal")
        
        # Card 1: Total Scan Cycles
        card1 = ctk.CTkFrame(metrics_frame, fg_color=CARD_BG, corner_radius=8, border_color=("#CBD5E1", "#1E293B"), border_width=1)
        card1.grid(row=0, column=0, padx=5, sticky="nsew")
        ctk.CTkLabel(card1, text="รอบสแกนสะสม (Total Cycles)", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=15, pady=(8, 2))
        self.lbl_metric_cycles = ctk.CTkLabel(card1, text="0", font=ctk.CTkFont(family="Consolas", size=24, weight="bold"), text_color=ACCENT_ORANGE)
        self.lbl_metric_cycles.pack(anchor="w", padx=15, pady=(0, 8))
        
        # Card 2: Uptime / Running Time
        card2 = ctk.CTkFrame(metrics_frame, fg_color=CARD_BG, corner_radius=8, border_color="#1E3A5F", border_width=1)
        card2.grid(row=0, column=1, padx=5, sticky="nsew")
        ctk.CTkLabel(card2, text="ระยะเวลาการทำงาน (Active Time)", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=15, pady=(8, 2))
        self.lbl_metric_uptime = ctk.CTkLabel(card2, text="00:00:00", font=ctk.CTkFont(family="Consolas", size=24, weight="bold"), text_color=("#1E293B", "#F8FAFC"))
        self.lbl_metric_uptime.pack(anchor="w", padx=15, pady=(0, 8))
        
        # Card 3: Total Triggers
        card3 = ctk.CTkFrame(metrics_frame, fg_color=CARD_BG, corner_radius=8, border_color=("#CBD5E1", "#1E293B"), border_width=1)
        card3.grid(row=0, column=2, padx=5, sticky="nsew")
        ctk.CTkLabel(card3, text="รวมการตรวจพบสำเร็จ (Triggers)", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=15, pady=(8, 2))
        self.lbl_metric_triggers = ctk.CTkLabel(card3, text="0 ครั้ง", font=ctk.CTkFont(family="Consolas", size=24, weight="bold"), text_color="#00E676")
        self.lbl_metric_triggers.pack(anchor="w", padx=15, pady=(0, 8))
        
        # Main split panel (Left = Graph, Right = Summary Stats)
        main_panels = ctk.CTkFrame(self.tab_analytics, fg_color="transparent")
        main_panels.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left Panel: Canvas Chart
        self.chart_container = ctk.CTkFrame(main_panels, fg_color=CARD_BG, corner_radius=8)
        self.chart_container.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(
            self.chart_container, 
            text="📈 กราฟแนวโน้มผลลัพธ์ (Analytics Trend)", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=ACCENT_ORANGE
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.chart_canvas = tk.Canvas(
            self.chart_container, 
            bg="#F8FAFC", 
            highlightthickness=0
        )
        self.chart_canvas.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.chart_canvas.bind("<Configure>", lambda e: self.draw_chart())
        
        # Right Panel: Detailed Summary list of counts & OCR
        self.stats_summary_panel = ctk.CTkFrame(main_panels, fg_color=CARD_BG, corner_radius=8, width=320)
        self.stats_summary_panel.pack(side="right", fill="both", padx=(5, 0))
        self.stats_summary_panel.pack_propagate(False)
        
        ctk.CTkLabel(
            self.stats_summary_panel, 
            text="📋 รายละเอียดผลลัพธ์ล่าสุด", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.stats_scroll_frame = ctk.CTkScrollableFrame(
            self.stats_summary_panel,
            fg_color="transparent",
            scrollbar_button_color="#252530"
        )
        self.stats_scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Bottom controls (Export & Clear)
        bottom_panel = ctk.CTkFrame(self.tab_analytics, fg_color="transparent")
        bottom_panel.pack(fill="x", padx=10, pady=(10, 15))
        
        self.btn_export = ctk.CTkButton(
            bottom_panel,
            corner_radius=8,
            text="📤 ส่งออกรายงาน (Export CSV)",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=36,
            command=self.export_stats_csv
        )
        self.btn_export.pack(side="left", padx=(0, 5))
        
        self.btn_clear_stats = ctk.CTkButton(
            bottom_panel,
            corner_radius=8,
            text="🧹 ล้างสถิติ (Clear Stats)",
            fg_color=DELETE_RED,
            hover_color=DELETE_HOVER,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=36,
            command=self.clear_analytics
        )
        self.btn_clear_stats.pack(side="left", padx=5)
        
        # Start periodic update timer loop
        self.periodic_dashboard_update()

    def periodic_dashboard_update(self):
        if self.tabview.get() == "📊 แดชบอร์ดวิเคราะห์ผล":
            self.update_dashboard_ui()
        self.after(1000, self.periodic_dashboard_update)

    def update_dashboard_ui(self):
        # 1. Update Scan Cycles
        self.lbl_metric_cycles.configure(text=str(self.stats_data["total_scan_cycles"]))
        
        # 2. Update Active Running Time
        if self.bot_running and self.stats_data["start_time"] is not None:
            elapsed = int(time.time() - self.stats_data["start_time"])
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            uptime_str = "00:00:00"
        self.lbl_metric_uptime.configure(text=uptime_str)
        
        # 3. Update Total Triggers
        total_triggers = sum(self.stats_data["triggers_count"].values())
        self.lbl_metric_triggers.configure(text=f"{total_triggers} ครั้ง")
        
        # 4. Update or Build the Right Side Summary Stats list
        valid_cards = set()
        for step in self.steps:
            if "stats_card" in step and step["stats_card"] and step["stats_card"].winfo_exists():
                valid_cards.add(step["stats_card"])
                
        for widget in self.stats_scroll_frame.winfo_children():
            if widget not in valid_cards:
                widget.destroy()
                
        # Update or render details for each step
        for i, step in enumerate(self.steps):
            name_val = step.get("step_name", "")
            step_name = f"ขั้นตอนที่ {i+1} ({name_val if name_val else step['mode']})"
            
            # Prepare content text depending on mode
            if step["mode"] == "บอตปกติ":
                triggers = self.stats_data["triggers_count"].get(step["id"], 0)
                content_text = f"• จำนวนการกระตุ้น (Triggers): {triggers} ครั้ง\n• ความแม่นยำเฉลี่ย: {step.get('confidence', 0.80):.2f}"
            elif step["mode"] == "นับวัตถุ":
                lbl_text = "• ภาพเป้าหมายตรวจนับ:\n"
                if not step.get("counting_targets", []):
                    lbl_text += "  (ยังไม่มีภาพสำหรับนับ)"
                else:
                    for t in step["counting_targets"]:
                        fname = os.path.basename(t["path"])
                        acc = t.get('accum_count', 0)
                        last_c = t.get('last_count', 0)
                        lbl_text += f"  - {fname}: สะสม {acc} ชิ้น (รอบนี้: {last_c})\n"
                content_text = lbl_text.strip()
            elif step["mode"] == "บวกเลข OCR":
                val = step.get("last_ocr_sum", 0.0)
                txt = step.get("last_ocr_text", "").replace("\n", " ").strip()
                if len(txt) > 25:
                    txt = txt[:25] + "..."
                content_text = f"• ผลรวมตัวเลขล่าสุด: {val:.2f}\n• ข้อความดิบ: \"{txt}\""
            else:
                content_text = ""
                
            # Check if card already exists in cache
            if ("stats_card" in step and step["stats_card"] and 
                step["stats_card"].winfo_exists() and 
                "stats_label" in step and step["stats_label"] and 
                step["stats_label"].winfo_exists() and
                "stats_title" in step and step["stats_title"] and 
                step["stats_title"].winfo_exists()):
                
                # Direct configure values
                step["stats_title"].configure(text=step_name)
                step["stats_label"].configure(text=content_text)
                step["stats_card"].pack(fill="x", pady=4, padx=2)
            else:
                # Create new widgets and store references
                card_sub = ctk.CTkFrame(self.stats_scroll_frame, fg_color=("#E2E8F0", "#13131A"), corner_radius=6)
                card_sub.pack(fill="x", pady=4, padx=2)
                
                title_lbl = ctk.CTkLabel(
                    card_sub,
                    text=step_name,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color=ACCENT_ORANGE
                )
                title_lbl.pack(anchor="w", padx=10, pady=(6, 2))
                
                label_val = ctk.CTkLabel(
                    card_sub,
                    text=content_text,
                    font=ctk.CTkFont(size=10),
                    text_color=("#1E293B", "#E0E0E5"),
                    justify="left"
                )
                label_val.pack(anchor="w", padx=10, pady=(0, 6))
                
                step["stats_card"] = card_sub
                step["stats_title"] = title_lbl
                step["stats_label"] = label_val
                
        # 5. Redraw the custom chart
        self.draw_chart()

    def draw_chart(self):
        self.chart_canvas.delete("all")
        w = self.chart_canvas.winfo_width()
        h = self.chart_canvas.winfo_height()
        if w < 15 or h < 15:
            w, h = 480, 240
            
        # Draw grid
        is_dark = ctk.get_appearance_mode() == "Dark"
        grid_color = "#222228" if is_dark else "#E2E8F0"
        for i in range(1, 5):
            y_grid = h - (i * (h // 5))
            self.chart_canvas.create_line(0, y_grid, w, y_grid, fill=grid_color, width=1)
            
        # Retrieve history to plot
        history = self.stats_data.get("ocr_sum_history", [])
        
        if not history:
            merged_counts = []
            for tname, counts in self.stats_data.get("counting_history", {}).items():
                if counts:
                    merged_counts = counts
                    break
            history = merged_counts
            
        if not history:
            self.chart_canvas.create_text(w//2, h//2, text="ไม่มีข้อมูลกราฟประวัติย้อนหลังในขณะนี้\n(จะเริ่มบันทึกประวัติเมื่อเปิดระบบบอต)", fill=TEXT_MUTED, font=("Segoe UI", 11), justify="center")
            return
            
        max_val = max(history) if history else 1.0
        if max_val == 0:
            max_val = 1.0
            
        points = []
        num_points = len(history)
        x_step = w / max(1, num_points - 1) if num_points > 1 else w
        
        for idx, val in enumerate(history):
            x = idx * x_step
            y = h - 25 - (val / max_val) * (h - 50)
            points.append((x, y))
            
        # Draw line
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            self.chart_canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=ACCENT_ORANGE, width=3)
            
        # Draw dots
        for p in points:
            self.chart_canvas.create_oval(p[0]-3, p[1]-3, p[0]+3, p[1]+3, fill="#FFFFFF", outline=ACCENT_ORANGE, width=2)
            
        # Draw labels
        self.chart_canvas.create_text(25, 15, text=f"Max: {max_val:.1f}", fill=TEXT_MUTED, font=("Consolas", 9), anchor="w")
        self.chart_canvas.create_text(25, h - 12, text="Min: 0.0", fill=TEXT_MUTED, font=("Consolas", 9), anchor="w")

    def clear_analytics(self):
        self.stats_data["total_scan_cycles"] = 0
        self.stats_data["triggers_count"].clear()
        self.stats_data["ocr_sum_history"].clear()
        self.stats_data["counting_history"].clear()
        if self.bot_running:
            self.stats_data["start_time"] = time.time()
        else:
            self.stats_data["start_time"] = None
            
        for step in self.steps:
            if "counting_targets" in step:
                for t in step["counting_targets"]:
                    t["last_count"] = 0
            step["last_ocr_sum"] = 0.0
            step["last_ocr_text"] = ""
            
        self.update_dashboard_ui()
        self.add_log("[✓] ล้างประวัติสถิติแดชบอร์ดเรียบร้อยแล้ว")
        messagebox.showinfo("ล้างสำเร็จ", "ล้างสถิติแดชบอร์ดทั้งหมดเรียบร้อยแล้ว")

    def export_stats_csv(self):
        file_path = filedialog.asksaveasfilename(
            title="ส่งออกรายงานวิเคราะห์ CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile="freecame_analytics_report.csv"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, "w", encoding="utf-8-sig") as f:
                f.write("ลำดับขั้นตอน,รูปแบบการทำงาน,จำนวนครั้งที่รันสำเร็จ,รายละเอียดล่าสุุด\n")
                for i, step in enumerate(self.steps):
                    triggers = self.stats_data["triggers_count"].get(step["id"], 0)
                    detail = ""
                    if step["mode"] == "บอตปกติ":
                        detail = f"ความแม่นยำเฉลี่ย {step.get('confidence', 0.8):.2f}"
                    elif step["mode"] == "นับวัตถุ":
                        detail = "พบวัตถุ: " + " | ".join([f"{os.path.basename(t['path'])}={t.get('last_count', 0)}ชิ้น" for t in step.get("counting_targets", [])])
                    elif step["mode"] == "บวกเลข OCR":
                        detail = f"ผลรวมตัวเลขล่าสุด: {step.get('last_ocr_sum', 0.0):.2f}"
                        
                    f.write(f"ขั้นตอนที่ {i+1},{step['mode']},{triggers},{detail}\n")
                    
            filename = os.path.basename(file_path)
            self.add_log(f"[✓] ส่งออกรายงานวิเคราะห์สำเร็จ → {filename}")
            messagebox.showinfo("ส่งออกสำเร็จ", f"ส่งออกรายงานสำเร็จ:\n{filename}")
        except Exception as e:
            self.add_log(f"[Error] ส่งออกรายงานไม่สำเร็จ: {e}")
            messagebox.showerror("เกิดข้อผิดพลาด", f"ไม่สามารถบันทึกรายงานได้:\n{e}")

    # --- MULTI-STEP LOGIC AND INTERFACE ---
    def change_step_mode(self, step_id, mode_val):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if not step:
            return
        
        step["mode"] = mode_val
        
        # Hide all sub UI frames
        step["normal_ui_frame"].pack_forget()
        step["counting_ui_frame"].pack_forget()
        step["ocr_ui_frame"].pack_forget()
        
        # Show chosen UI frame
        if mode_val == "บอตปกติ":
            step["normal_ui_frame"].pack(fill="x", expand=True)
        elif mode_val == "นับวัตถุ":
            step["counting_ui_frame"].pack(fill="x", expand=True)
        elif mode_val == "บวกเลข OCR":
            step["ocr_ui_frame"].pack(fill="x", expand=True)
            
        self.add_log(f"[*] ขั้นตอนที่ {self.steps.index(step) + 1}: เปลี่ยนโหมดเป็น {mode_val}")

    def add_step(self, mode="บอตปกติ"):
        step_id = str(random.randint(100000, 999999))
        
        if mode == "บอตปกติ":
            scroll_container = self.steps_scroll_normal
        elif mode == "นับวัตถุ" or mode == "บวกเลข OCR":
            scroll_container = self.steps_scroll_detection
        else:
            scroll_container = self.steps_scroll_normal

        step_data = {
            "id": step_id,
            "mode": "บอตปกติ",
            "click_targets": [],
            "template_path": None,
            "confidence": 0.80,
            "delay": 1.5,
            "action_type": "คลิกเมาส์",
            "type_text": "",
            "search_region": None,
            
            # Counting Targets
            "counting_targets": [],
            
            # OCR Stats
            "last_ocr_text": "",
            "last_ocr_sum": 0.0,
            
            # UI references
            "card_frame": None,
            "title_label": None,
            "image_label": None,
            "preview_label": None,
            "region_label": None,
            "conf_val_label": None,
            "delay_val_label": None,
            "text_entry_frame": None,
            "conf_row": None,
            "click_targets_frame": None,
            "click_targets_placeholder": None,
            
            # Counting references
            "counting_region_label": None,
            "counting_list_frame": None,
            "counting_placeholder_lbl": None,
            
            # OCR references
            "ocr_region_label": None,
            "lbl_ocr_result_sum": None,
            "lbl_ocr_result_text": None,
            
            # Dashboard Stats Cache
            "stats_card": None,
            "stats_title": None,
            "stats_label": None,
            
            # Step Name
            "step_name": "",
            "step_name_entry": None,
            
            # Telegram alerting fields
            "telegram_alert_enabled": False,
            "telegram_timeout": 300,
            "telegram_alert_enabled_checkbox": None,
            "telegram_timeout_entry": None,
            "_last_trigger_time": time.time(),
            "_telegram_alert_sent": False,
        }
        
        card = ctk.CTkFrame(scroll_container, fg_color=CARD_BG, corner_radius=8)
        card.pack(fill="x", pady=8, padx=5)
        self.flash_card_border(card)
        step_data["card_frame"] = card
        
        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=15, pady=(10, 5))
        
        title_lbl = ctk.CTkLabel(
            header_row, 
            text=f"ขั้นตอนที่ {len(self.steps) + 1}", 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=ACCENT_ORANGE
        )
        title_lbl.pack(side="left")
        step_data["title_label"] = title_lbl
        
        name_lbl = ctk.CTkLabel(
            header_row,
            text=" | ชื่อ:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=TEXT_MUTED
        )
        name_lbl.pack(side="left", padx=(5, 2))
        
        step_name_entry = ctk.CTkEntry(
            header_row,
            placeholder_text="ตั้งชื่อขั้นตอน...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            height=24,
            width=180
        )
        step_name_entry.pack(side="left", padx=2)
        
        def on_name_keypress(event, s_id=step_id, entry=step_name_entry):
            self.on_step_name_change(s_id, entry.get())
            
        step_name_entry.bind("<KeyRelease>", on_name_keypress)
        step_name_entry.bind("<FocusOut>", on_name_keypress)
        step_data["step_name_entry"] = step_name_entry
        
        header_actions = ctk.CTkFrame(header_row, fg_color="transparent")
        header_actions.pack(side="right")

        # Move to index input
        move_lbl = ctk.CTkLabel(
            header_actions,
            text="ย้ายไปลำดับที่:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_COLOR
        )
        move_lbl.pack(side="left", padx=(0, 2))

        move_entry = ctk.CTkEntry(
            header_actions,
            width=35,
            height=24,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=("#FFFFFF", "#1E293B"),
            text_color=("#0F172A", "#F8FAFC"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center"
        )
        move_entry.insert(0, str(len(self.steps) + 1))
        move_entry.pack(side="left", padx=(0, 10))
        step_data["index_entry"] = move_entry

        move_entry.bind("<Return>", lambda event, sid=step_id, entry=move_entry: self.on_move_entry_submit(sid, entry))
        move_entry.bind("<FocusOut>", lambda event, sid=step_id, entry=move_entry: self.on_move_entry_submit(sid, entry))

        move_up_btn = ctk.CTkButton(
            header_actions,
            corner_radius=8,
            text="▲ เลื่อนขึ้น",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            width=65,
            height=24,
            command=lambda sid=step_id: self.move_step_up(sid)
        )
        move_up_btn.pack(side="left", padx=2)

        move_down_btn = ctk.CTkButton(
            header_actions,
            corner_radius=8,
            text="▼ เลื่อนลง",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            width=65,
            height=24,
            command=lambda sid=step_id: self.move_step_down(sid)
        )
        move_down_btn.pack(side="left", padx=2)

        delete_btn = ctk.CTkButton(
            header_actions,
            corner_radius=8,
            text="ลบขั้นตอนนี้",
            fg_color=DELETE_RED,
            hover_color=DELETE_HOVER,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=80,
            height=24,
            command=lambda sid=step_id: self.delete_step(sid)
        )
        delete_btn.pack(side="left", padx=(10, 0))
        
        body_frame = ctk.CTkFrame(card, fg_color="transparent")
        body_frame.pack(fill="x", padx=15, pady=5)
        
        # =========================================================================
        # SUB-FRAME 1: NORMAL AUTOMATION UI
        # =========================================================================
        normal_ui = ctk.CTkFrame(body_frame, fg_color="transparent")
        normal_ui.pack(fill="x", expand=True)
        step_data["normal_ui_frame"] = normal_ui
        
        left_col = ctk.CTkFrame(normal_ui, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(
            left_col, 
            text="1. เงื่อนไขตรวจจับ (Trigger Image)", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", pady=(0, 3))
        
        img_lbl = ctk.CTkLabel(
            left_col, 
            text="ยังไม่ได้เลือกรูปภาพ", 
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        img_lbl.pack(anchor="w", fill="x")
        step_data["image_label"] = img_lbl
        
        preview_lbl = ctk.CTkLabel(
            left_col,
            text="ไม่มีภาพตัวอย่าง",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            fg_color=("#F1F5F9", "#121214"),
            width=150,
            height=70,
            corner_radius=4
        )
        preview_lbl.pack(anchor="w", pady=5)
        step_data["preview_label"] = preview_lbl
        
        btn_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_frame.pack(anchor="w", fill="x", pady=2)

        browse_btn = ctk.CTkButton(
            btn_frame,
            corner_radius=8,
            text="เลือกรูปภาพ",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            command=lambda sid=step_id: self.browse_trigger_image(sid)
        )
        browse_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        capture_btn = ctk.CTkButton(
            btn_frame,
            corner_radius=8,
            text="แคปเจอร์รูป",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            command=lambda sid=step_id: self.open_capture_picker(sid)
        )
        capture_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))
        
        region_lbl = ctk.CTkLabel(
            left_col, 
            text="ขอบเขตตรวจจับ: ทั่วทั้งหน้าจอ", 
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        region_lbl.pack(anchor="w", fill="x", pady=(5, 1))
        step_data["region_label"] = region_lbl
        
        region_btn_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        region_btn_frame.pack(anchor="w", fill="x", pady=2)
        
        select_region_btn = ctk.CTkButton(
            region_btn_frame,
            corner_radius=8,
            text="เลือกขอบเขต",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=80,
            command=lambda sid=step_id: self.open_region_picker(sid)
        )
        select_region_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        view_region_btn = ctk.CTkButton(
            region_btn_frame,
            corner_radius=8,
            text="ดูขอบเขต",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=65,
            command=lambda sid=step_id: self.view_search_region(sid)
        )
        view_region_btn.pack(side="left", fill="x", expand=True, padx=(2, 2))
        
        clear_region_btn = ctk.CTkButton(
            region_btn_frame,
            corner_radius=8,
            text="ล้าง",
            fg_color="transparent",
            border_color=DELETE_RED, border_width=1.5, hover_color=("#FEE2E2", "#30151a"), text_color=DELETE_RED,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=40,
            command=lambda sid=step_id: self.clear_search_region(sid)
        )
        clear_region_btn.pack(side="left", padx=(2, 0))
        
        right_col = ctk.CTkFrame(normal_ui, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        click_section_header = ctk.CTkFrame(right_col, fg_color="transparent")
        click_section_header.pack(fill="x", pady=(0, 3))
        
        ctk.CTkLabel(
            click_section_header, 
            text="2. จุดคลิกเป้าหมาย (Click Targets)", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(side="left")
        
        add_point_btn = ctk.CTkButton(
            click_section_header,
            corner_radius=8,
            text="+ เพิ่มจุดคลิก",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1.5,
            hover_color=("#DBEAFE", "#30201a"),
            text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=90,
            height=22,
            command=lambda sid=step_id: self.open_coordinate_picker_add(sid)
        )
        add_point_btn.pack(side="right")
        
        # Clear All Click Targets Button
        clear_points_btn = ctk.CTkButton(
            click_section_header,
            corner_radius=8,
            text="🗑️ ลบทั้งหมด",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1.5,
            hover_color=("#FEE2E2", "#450a0a"),
            text_color=("#EF4444", "#F87171"),
            font=ctk.CTkFont(size=10, weight="bold"),
            width=70,
            height=22,
            command=lambda sid=step_id: self.clear_all_click_targets(sid)
        )
        clear_points_btn.pack(side="right", padx=(0, 5))
        
        # Delete Selected Click Targets Button
        del_sel_points_btn = ctk.CTkButton(
            click_section_header,
            corner_radius=8,
            text="🗑️ ลบที่เลือก",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1.5,
            hover_color=("#FEE2E2", "#450a0a"),
            text_color=("#EF4444", "#F87171"),
            font=ctk.CTkFont(size=10, weight="bold"),
            width=70,
            height=22,
            command=lambda sid=step_id: self.delete_selected_click_targets(sid)
        )
        del_sel_points_btn.pack(side="right", padx=(0, 5))
        
        click_targets_frame = ctk.CTkFrame(right_col, fg_color=("#F1F5F9", "#121214"), corner_radius=5)
        click_targets_frame.pack(fill="x", pady=(0, 6))
        step_data["click_targets_frame"] = click_targets_frame
        
        placeholder_lbl = ctk.CTkLabel(
            click_targets_frame,
            text="ยังไม่มีจุดคลิก — กด '+ เพิ่มจุดคลิก' ด้านบน",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED
        )
        placeholder_lbl.pack(padx=8, pady=6)
        step_data["click_targets_placeholder"] = placeholder_lbl
        
        action_row = ctk.CTkFrame(right_col, fg_color="transparent")
        action_row.pack(fill="x", pady=(2, 6))
        ctk.CTkLabel(action_row, text="รูปแบบการทำงาน:", font=ctk.CTkFont(size=11), text_color=TEXT_COLOR).pack(side="left")
        
        action_selector = ctk.CTkSegmentedButton(
            action_row,
            corner_radius=8,
            values=["คลิกเมาส์", "พิมพ์ข้อความ"],
            font=ctk.CTkFont(size=11, weight="bold"),
            selected_color=ACCENT_ORANGE,
            selected_hover_color=ACCENT_HOVER,
            height=24,
            command=lambda val, sid=step_id: self.toggle_action_type(sid, val)
        )
        action_selector.set("คลิกเมาส์")
        action_selector.pack(side="right")
        step_data["action_selector"] = action_selector
        
        text_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        step_data["text_entry_frame"] = text_frame
        
        ctk.CTkLabel(text_frame, text="ข้อความที่ต้องการให้พิมพ์:", font=ctk.CTkFont(size=11), text_color=TEXT_COLOR).pack(anchor="w")
        text_entry = ctk.CTkEntry(
            text_frame,
            placeholder_text="กรอกข้อความที่นี่...",
            font=ctk.CTkFont(size=11),
            height=26,
            fg_color="#0F0F11",
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1
        )
        text_entry.pack(fill="x", pady=2)
        text_entry.bind("<KeyRelease>", lambda event, sid=step_id, entry=text_entry: self.update_step_text(sid, entry.get()))
        step_data["text_entry"] = text_entry
        
        hint_lbl = ctk.CTkLabel(
            text_frame,
            text="ใส่ {enter}, {esc}, {tab} เพื่อกดปุ่มตามลำดับ เช่น admin{tab}1234{enter}",
            font=ctk.CTkFont(size=9),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        hint_lbl.pack(anchor="w", pady=(0, 2))
        
        conf_row = ctk.CTkFrame(right_col, fg_color="transparent")
        conf_row.pack(fill="x")
        step_data["conf_row"] = conf_row
        ctk.CTkLabel(conf_row, text="ความแม่นยำ (Confidence):", font=ctk.CTkFont(size=11), text_color=TEXT_COLOR).pack(side="left")
        conf_val_lbl = ctk.CTkLabel(conf_row, text="0.80", font=ctk.CTkFont(size=11, weight="bold"), text_color=ACCENT_ORANGE)
        conf_val_lbl.pack(side="right")
        step_data["conf_val_label"] = conf_val_lbl
        
        conf_slider = ctk.CTkSlider(
            right_col,
            from_=0.40,
            to=1.00,
            number_of_steps=60,
            height=14,
            progress_color=ACCENT_ORANGE,
            button_color=ACCENT_ORANGE,
            button_hover_color=ACCENT_HOVER,
            command=lambda val, sid=step_id: self.update_step_confidence(sid, val)
        )
        conf_slider.set(0.80)
        conf_slider.pack(fill="x", pady=(2, 8))
        step_data["conf_slider"] = conf_slider
        
        delay_row = ctk.CTkFrame(right_col, fg_color="transparent")
        delay_row.pack(fill="x")
        ctk.CTkLabel(delay_row, text="หน่วงเวลาหลังคลิก (วินาที):", font=ctk.CTkFont(size=11), text_color=TEXT_COLOR).pack(side="left")
        
        delay_entry = ctk.CTkEntry(
            delay_row,
            width=50,
            height=20,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            fg_color="#0F0F11",
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            text_color=ACCENT_ORANGE,
            justify="center"
        )
        delay_entry.insert(0, "1.5")
        delay_entry.pack(side="right")
        step_data["delay_entry"] = delay_entry
        
        delay_slider = ctk.CTkSlider(
            right_col,
            from_=0.1,
            to=10.0,
            number_of_steps=99,
            height=14,
            progress_color=ACCENT_ORANGE,
            button_color=ACCENT_ORANGE,
            button_hover_color=ACCENT_HOVER,
            command=lambda val, sid=step_id, entry=delay_entry: self.update_step_delay(sid, val, entry)
        )
        delay_slider.set(1.5)
        delay_slider.pack(fill="x", pady=(2, 8))
        step_data["delay_slider"] = delay_slider

        delay_entry.bind(
            "<KeyRelease>",
            lambda event, sid=step_id, entry=delay_entry, slider=delay_slider:
                self.on_step_delay_entry_change(sid, entry.get(), slider)
        )

        # =========================================================================
        # SUB-FRAME 2: OBJECT COUNTING UI
        # =========================================================================
        counting_ui = ctk.CTkFrame(body_frame, fg_color="transparent")
        step_data["counting_ui_frame"] = counting_ui
        
        c_left = ctk.CTkFrame(counting_ui, fg_color="transparent")
        c_left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(c_left, text="1. ขอบเขตพื้นที่และเป้าหมาย", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w")
        
        c_region_lbl = ctk.CTkLabel(c_left, text="ขอบเขตตรวจจับ: ทั่วทั้งหน้าจอ", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, anchor="w")
        c_region_lbl.pack(anchor="w", fill="x", pady=2)
        step_data["counting_region_label"] = c_region_lbl
        
        c_region_btn_frame = ctk.CTkFrame(c_left, fg_color="transparent")
        c_region_btn_frame.pack(anchor="w", fill="x", pady=2)
        
        c_select_region_btn = ctk.CTkButton(
            c_region_btn_frame,
            corner_radius=8,
            text="เลือกขอบเขต",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=80,
            command=lambda sid=step_id: self.open_region_picker(sid)
        )
        c_select_region_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        c_view_region_btn = ctk.CTkButton(
            c_region_btn_frame,
            corner_radius=8,
            text="ดูขอบเขต",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=65,
            command=lambda sid=step_id: self.view_search_region(sid)
        )
        c_view_region_btn.pack(side="left", fill="x", expand=True, padx=(2, 2))
        
        c_clear_region_btn = ctk.CTkButton(
            c_region_btn_frame,
            corner_radius=8,
            text="ล้าง",
            fg_color="transparent",
            border_color=DELETE_RED, border_width=1.5, hover_color=("#FEE2E2", "#30151a"), text_color=DELETE_RED,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=40,
            command=lambda sid=step_id: self.clear_search_region(sid)
        )
        c_clear_region_btn.pack(side="left", padx=(2, 0))
        
        c_btn_frame = ctk.CTkFrame(c_left, fg_color="transparent")
        c_btn_frame.pack(fill="x", pady=8)

        add_counting_target_btn = ctk.CTkButton(
            c_btn_frame,
            corner_radius=8,
            text="📁 เลือกไฟล์ภาพ",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            command=lambda sid=step_id: self.add_counting_target(sid)
        )
        add_counting_target_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        capture_counting_btn = ctk.CTkButton(
            c_btn_frame,
            corner_radius=8,
            text="📸 แคปภาพนับ",
            fg_color=ACCENT_ORANGE, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            command=lambda sid=step_id: self.open_counting_capture_picker(sid)
        )
        capture_counting_btn.pack(side="right", fill="x", expand=True, padx=(2, 0))
        
        c_right = ctk.CTkFrame(counting_ui, fg_color="transparent")
        c_right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        c_right_header = ctk.CTkFrame(c_right, fg_color="transparent")
        c_right_header.pack(fill="x")

        ctk.CTkLabel(c_right_header, text="2. รายการภาพที่ต้องการนับจำนวน", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_COLOR).pack(side="left")

        btn_reset_counting_accum = ctk.CTkButton(
            c_right_header,
            corner_radius=8,
            text="🔄 รีเซ็ตผลรวม",
            fg_color="transparent",
            border_color=DELETE_RED,
            border_width=1,
            hover_color=("#FEE2E2", "#30151a"),
            text_color=DELETE_RED,
            font=ctk.CTkFont(size=9, weight="bold"),
            height=20,
            width=70,
            command=lambda sid=step_id: self.reset_counting_accum(sid)
        )
        btn_reset_counting_accum.pack(side="right")
        
        counting_list_frame = ctk.CTkScrollableFrame(c_right, fg_color=("#F1F5F9", "#121214"), corner_radius=5, height=120)
        counting_list_frame.pack(fill="both", expand=True, pady=4)
        step_data["counting_list_frame"] = counting_list_frame
        
        c_placeholder = ctk.CTkLabel(
            counting_list_frame,
            text="ยังไม่มีภาพเป้าหมายตรวจนับ — กด '+ เพิ่มภาพตรวจนับจำนวน' ด้านซ้าย",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED
        )
        c_placeholder.pack(padx=8, pady=10)
        step_data["counting_placeholder_lbl"] = c_placeholder
        
        # =========================================================================
        # SUB-FRAME 3: OCR SUMMATION UI
        # =========================================================================
        ocr_ui = ctk.CTkFrame(body_frame, fg_color="transparent")
        step_data["ocr_ui_frame"] = ocr_ui
        
        o_left = ctk.CTkFrame(ocr_ui, fg_color="transparent")
        o_left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(o_left, text="1. ขอบเขตตัวเลขสำหรับอ่าน (OCR)", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w")
        
        o_region_lbl = ctk.CTkLabel(o_left, text="ขอบเขตตรวจจับ: ทั่วทั้งหน้าจอ", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, anchor="w")
        o_region_lbl.pack(anchor="w", fill="x", pady=2)
        step_data["ocr_region_label"] = o_region_lbl
        
        o_region_btn_frame = ctk.CTkFrame(o_left, fg_color="transparent")
        o_region_btn_frame.pack(anchor="w", fill="x", pady=2)
        
        o_select_region_btn = ctk.CTkButton(
            o_region_btn_frame,
            corner_radius=8,
            text="เลือกขอบเขต",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=80,
            command=lambda sid=step_id: self.open_region_picker(sid)
        )
        o_select_region_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        o_view_region_btn = ctk.CTkButton(
            o_region_btn_frame,
            corner_radius=8,
            text="ดูขอบเขต",
            fg_color="transparent",
            border_color=("#CBD5E1", "#1E293B"), border_width=1.5, hover_color=("#DBEAFE", "#30201a"), text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=65,
            command=lambda sid=step_id: self.view_search_region(sid)
        )
        o_view_region_btn.pack(side="left", fill="x", expand=True, padx=(2, 2))
        
        o_clear_region_btn = ctk.CTkButton(
            o_region_btn_frame,
            corner_radius=8,
            text="ล้าง",
            fg_color="transparent",
            border_color=DELETE_RED, border_width=1.5, hover_color=("#FEE2E2", "#30151a"), text_color=DELETE_RED,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=40,
            command=lambda sid=step_id: self.clear_search_region(sid)
        )
        o_clear_region_btn.pack(side="left", padx=(2, 0))
        
        # Optional Trigger Image for OCR
        ctk.CTkLabel(o_left, text="2. ภาพเงื่อนไข (สแกนเฉพาะเมื่อพบภาพนี้ - ตัวเลือก):", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(anchor="w", pady=(6, 2))
        
        o_img_frame = ctk.CTkFrame(o_left, fg_color="transparent")
        o_img_frame.pack(fill="x", pady=2)
        
        o_img_label = ctk.CTkLabel(o_img_frame, text="ไม่เปิดใช้ (สแกนทุกรอบ)", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED, anchor="w")
        o_img_label.pack(side="left", fill="x", expand=True)
        step_data["ocr_trigger_img_label"] = o_img_label
        
        o_btn_box = ctk.CTkFrame(o_left, fg_color="transparent")
        o_btn_box.pack(fill="x", pady=2)
        
        btn_ocr_browse = ctk.CTkButton(
            o_btn_box,
            corner_radius=8,
            text="📁 ไฟล์",
            fg_color=("#E2E8F0", "#1E293B"),
            hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            font=ctk.CTkFont(size=10, weight="bold"),
            height=26,
            width=55,
            command=lambda sid=step_id: self.browse_trigger_image(sid)
        )
        btn_ocr_browse.pack(side="left", padx=(0, 2))
        
        btn_ocr_cap = ctk.CTkButton(
            o_btn_box,
            corner_radius=8,
            text="📸 แคป",
            fg_color=ACCENT_ORANGE, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
            font=ctk.CTkFont(size=10, weight="bold"),
            height=26,
            width=55,
            command=lambda sid=step_id: self.open_capture_picker(sid)
        )
        btn_ocr_cap.pack(side="left", padx=2)
        
        btn_ocr_clear_img = ctk.CTkButton(
            o_btn_box,
            corner_radius=8,
            text="✕ ล้างภาพ",
            fg_color="transparent",
            border_color=DELETE_RED,
            border_width=1,
            hover_color=("#FEE2E2", "#30151a"),
            text_color=DELETE_RED,
            font=ctk.CTkFont(size=10),
            height=26,
            width=60,
            command=lambda sid=step_id: self.clear_ocr_trigger_image(sid)
        )
        btn_ocr_clear_img.pack(side="left", padx=(2, 0))
        
        o_right = ctk.CTkFrame(ocr_ui, fg_color="transparent")
        o_right.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(o_right, text="2. ผลลัพธ์จากการอ่านค่าด้วย OCR", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w")
        
        ocr_result_card = ctk.CTkFrame(o_right, fg_color=("#F1F5F9", "#121214"), corner_radius=5)
        ocr_result_card.pack(fill="both", expand=True, pady=4)
        
        ocr_sum_header = ctk.CTkFrame(ocr_result_card, fg_color="transparent")
        ocr_sum_header.pack(fill="x", padx=10, pady=(6, 0))

        lbl_ocr_sum_title = ctk.CTkLabel(ocr_sum_header, text="ผลรวมตัวเลขสะสม (Accumulated Sum):", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)
        lbl_ocr_sum_title.pack(side="left")

        btn_reset_ocr_sum = ctk.CTkButton(
            ocr_sum_header,
            corner_radius=8,
            text="🔄 รีเซ็ต",
            fg_color="transparent",
            border_color=DELETE_RED,
            border_width=1,
            hover_color=("#FEE2E2", "#30151a"),
            text_color=DELETE_RED,
            font=ctk.CTkFont(size=9, weight="bold"),
            height=20,
            width=50,
            command=lambda sid=step_id: self.reset_ocr_sum(sid)
        )
        btn_reset_ocr_sum.pack(side="right")
        
        lbl_ocr_sum_val = ctk.CTkLabel(ocr_result_card, text="0.00", font=ctk.CTkFont(family="Consolas", size=20, weight="bold"), text_color="#00E676")
        lbl_ocr_sum_val.pack(anchor="w", padx=10, pady=(0, 2))
        step_data["lbl_ocr_result_sum"] = lbl_ocr_sum_val
        
        lbl_ocr_text_title = ctk.CTkLabel(ocr_result_card, text="ข้อความดิบจากหน้าจอ (Raw text):", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED)
        lbl_ocr_text_title.pack(anchor="w", padx=10, pady=(2, 0))
        
        lbl_ocr_text_val = ctk.CTkLabel(ocr_result_card, text="(ยังไม่ได้สแกน)", font=ctk.CTkFont(size=10), text_color=TEXT_COLOR, wraplength=200, justify="left")
        lbl_ocr_text_val.pack(anchor="w", padx=10, pady=(0, 6))
        step_data["lbl_ocr_result_text"] = lbl_ocr_text_val

        self.steps.append(step_data)
        self.change_step_mode(step_id, mode)
        self.add_log(f"[+] เพิ่มขั้นตอนที่ {len(self.steps)} โหมด: {mode}")
        
        # 4. Telegram Notification Footer settings for each step card
        footer_row = ctk.CTkFrame(card, fg_color="transparent")
        footer_row.pack(fill="x", padx=15, pady=(2, 8))
        
        telegram_alert_var = ctk.BooleanVar(value=step_data["telegram_alert_enabled"])
        
        def toggle_step_telegram_alert(var=telegram_alert_var, sid=step_id):
            self.update_step_telegram_alert(sid, var.get())
            
        chk_tele = ctk.CTkCheckBox(
            footer_row,
            text="🔔 แจ้งเตือน Telegram หากเงื่อนไขค้าง",
            variable=telegram_alert_var,
            command=toggle_step_telegram_alert,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            checkbox_width=14,
            checkbox_height=14,
            border_width=1.5,
            border_color=("#94A3B8", "#475569"),
            hover_color=ACCENT_HOVER,
            fg_color=ACCENT_ORANGE,
            text_color=TEXT_COLOR
        )
        chk_tele.pack(side="left")
        step_data["telegram_alert_enabled_checkbox"] = chk_tele
        
        ctk.CTkLabel(footer_row, text=" เกิน:", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(side="left")
        
        tele_timeout_entry = ctk.CTkEntry(
            footer_row,
            width=45,
            height=20,
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=ACCENT_ORANGE,
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center",
            placeholder_text="300"
        )
        tele_timeout_entry.insert(0, str(step_data["telegram_timeout"]))
        tele_timeout_entry.pack(side="left", padx=2)
        step_data["telegram_timeout_entry"] = tele_timeout_entry
        
        ctk.CTkLabel(footer_row, text="วินาที", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(side="left")
        
        def on_tele_timeout_keypress(event, s_id=step_id, entry=tele_timeout_entry):
            self.update_step_telegram_timeout(s_id, entry.get())
            
        tele_timeout_entry.bind("<KeyRelease>", on_tele_timeout_keypress)
        tele_timeout_entry.bind("<FocusOut>", on_tele_timeout_keypress)

        # Auto scroll to bottom
        scroll_container._parent_canvas.yview_moveto(1.0)

    def update_step_telegram_alert(self, step_id, enabled):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["telegram_alert_enabled"] = enabled

    def update_step_telegram_timeout(self, step_id, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            try:
                val = int(value_str)
                step["telegram_timeout"] = max(1, val)
            except ValueError:
                pass

    def add_counting_target(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if not step:
            return
            
        file_path = filedialog.askopenfilename(
            title="เลือกภาพเป้าหมายสำหรับนับจำนวน",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not file_path:
            return
            
        target = {
            "path": file_path,
            "confidence": 0.80,
            "last_count": 0,
            "row_frame": None,
            "val_lbl": None
        }
        step["counting_targets"].append(target)
        target_idx = len(step["counting_targets"]) - 1
        
        # Hide placeholder
        if target_idx == 0:
            step["counting_placeholder_lbl"].pack_forget()
            
        self._render_counting_target_row(step, target_idx)
        
        idx = self.steps.index(step) + 1
        self.add_log(f"[+] ขั้นตอนที่ {idx}: เพิ่มภาพนับจำนวน → {os.path.basename(file_path)}")

    def reset_counting_accum(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            for target in step.get("counting_targets", []):
                target["accum_count"] = 0
                target["last_count"] = 0
                if "val_lbl" in target and target["val_lbl"].winfo_exists():
                    target["val_lbl"].configure(text="สะสม: 0 (รอบนี้: 0)")
            idx = self.steps.index(step) + 1
            self.add_log(f"[*] ขั้นตอนที่ {idx}: รีเซ็ตผลรวมสะสมการนับวัตถุเป็น 0 เรียบร้อย")

    def clear_ocr_trigger_image(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["template_path"] = None
            step["image_label"].configure(text="เลือกรูปภาพเงื่อนไข...", text_color=TEXT_MUTED)
            if "ocr_trigger_img_label" in step and step["ocr_trigger_img_label"].winfo_exists():
                step["ocr_trigger_img_label"].configure(text="ไม่เปิดใช้ (สแกนทุกรอบ)", text_color=TEXT_MUTED)
            idx = self.steps.index(step) + 1
            self.add_log(f"[-] ขั้นตอนที่ {idx}: ล้างภาพเงื่อนไข OCR (สแกนทุกรอบ)")

    def reset_ocr_sum(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["last_ocr_sum"] = 0.0
            if "lbl_ocr_result_sum" in step and step["lbl_ocr_result_sum"].winfo_exists():
                step["lbl_ocr_result_sum"].configure(text="0.00")
            idx = self.steps.index(step) + 1
            self.add_log(f"[*] ขั้นตอนที่ {idx}: รีเซ็ตผลรวมตัวเลขสะสม OCR เป็น 0.00")

    def open_counting_capture_picker(self, step_id):
        ScreenCapturePicker(self, lambda img: self.set_captured_counting_image(step_id, img))

    def set_captured_counting_image(self, step_id, img):
        if img is None:
            return

        step = next((s for s in self.steps if s["id"] == step_id), None)
        if not step:
            return

        save_dir = os.path.join(os.getcwd(), "captured_templates")
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                self.add_log(f"[Error] ไม่สามารถสร้างโฟลเดอร์เก็บรูปภาพได้: {e}")
                return

        filename = f"counting_{step_id}_{int(time.time())}.png"
        file_path = os.path.join(save_dir, filename)

        try:
            img.save(file_path)
            target = {
                "path": file_path,
                "confidence": 0.80,
                "last_count": 0,
                "row_frame": None,
                "val_lbl": None
            }
            step["counting_targets"].append(target)
            target_idx = len(step["counting_targets"]) - 1

            if target_idx == 0:
                step["counting_placeholder_lbl"].pack_forget()

            self._render_counting_target_row(step, target_idx)

            idx = self.steps.index(step) + 1
            self.add_log(f"[+] ขั้นตอนที่ {idx}: แคปเจอร์และบันทึกภาพนับจำนวน → {filename}")
        except Exception as e:
            self.add_log(f"[Error] ไม่สามารถบันทึกภาพนับจำนวนได้: {e}")

    def remove_counting_target(self, step_id, target_idx):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if not step:
            return
            
        if 0 <= target_idx < len(step["counting_targets"]):
            removed = step["counting_targets"].pop(target_idx)
            self.add_log(f"[-] ลบภาพตรวจนับ → {os.path.basename(removed['path'])}")
            
        # Rebuild the list frame UI
        for widget in step["counting_list_frame"].winfo_children():
            widget.destroy()
            
        if not step["counting_targets"]:
            placeholder = ctk.CTkLabel(
                step["counting_list_frame"],
                text="ยังไม่มีภาพเป้าหมายตรวจนับ — กด '+ เพิ่มภาพตรวจนับจำนวน' ด้านซ้าย",
                font=ctk.CTkFont(size=10),
                text_color=TEXT_MUTED
            )
            placeholder.pack(padx=8, pady=10)
            step["counting_placeholder_lbl"] = placeholder
        else:
            step["counting_placeholder_lbl"] = ctk.CTkLabel(step["counting_list_frame"], text="")
            for idx in range(len(step["counting_targets"])):
                self._render_counting_target_row(step, idx)

    def _render_counting_target_row(self, step, target_idx):
        target = step["counting_targets"][target_idx]
        frame = step["counting_list_frame"]
        
        row = ctk.CTkFrame(frame, fg_color=POINT_TAG_COLOR, corner_radius=4)
        row.pack(fill="x", pady=2, padx=4)
        target["row_frame"] = row
        
        fname = os.path.basename(target["path"])
        
        # Delete button on the right
        del_btn = ctk.CTkButton(
            row,
            corner_radius=8,
            text="✕",
            fg_color="transparent",
            hover_color=DELETE_HOVER,
            text_color=DELETE_RED,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=22,
            height=22,
            command=lambda sid=step["id"], t_idx=target_idx: self.remove_counting_target(sid, t_idx)
        )
        del_btn.pack(side="right", padx=(2, 4))
        
        # Last Count & Accum label
        accum_val = target.get("accum_count", 0)
        last_val = target.get("last_count", 0)
        val_lbl = ctk.CTkLabel(row, text=f"สะสม: {accum_val} (รอบนี้: {last_val})", font=ctk.CTkFont(size=10, weight="bold"), text_color=ACCENT_ORANGE)
        val_lbl.pack(side="right", padx=(4, 10))
        target["val_lbl"] = val_lbl
        
        # Thumbnail preview
        preview = ctk.CTkLabel(row, text="", width=30, height=20, fg_color=("#F1F5F9", "#121214"))
        preview.pack(side="left", padx=(5, 5))
        
        try:
            pil_img = Image.open(target["path"])
            pil_img.thumbnail((30, 20))
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            preview.configure(image=ctk_img)
        except Exception:
            preview.configure(text="N/A")
            
        # Filename label
        name_lbl = ctk.CTkLabel(row, text=fname[:12], font=ctk.CTkFont(size=10), text_color=TEXT_COLOR, anchor="w")
        name_lbl.pack(side="left", padx=(2, 5))
        
        # Confidence slider inside row
        conf_container = ctk.CTkFrame(row, fg_color="transparent")
        conf_container.pack(side="left", fill="x", expand=True)
        
        conf_lbl = ctk.CTkLabel(conf_container, text=f"c={target['confidence']:.2f}", font=ctk.CTkFont(size=8), text_color=TEXT_MUTED)
        conf_lbl.pack(side="left", padx=2)
        
        def update_target_conf(val, lbl=conf_lbl, tgt=target):
            tgt["confidence"] = float(val)
            lbl.configure(text=f"c={val:.2f}")
            
        slider = ctk.CTkSlider(
            conf_container,
            from_=0.40,
            to=1.00,
            number_of_steps=60,
            height=10,
            progress_color=ACCENT_ORANGE,
            button_color=ACCENT_ORANGE,
            button_hover_color=ACCENT_HOVER,
            command=update_target_conf
        )
        slider.set(target["confidence"])
        slider.pack(side="left", fill="x", expand=True, padx=2)

    def delete_step(self, step_id):
        idx = next((i for i, step in enumerate(self.steps) if step["id"] == step_id), None)
        if idx is not None:
            step_data = self.steps.pop(idx)
            step_data["card_frame"].destroy()
            self.add_log(f"[-] ลบขั้นตอนที่ {idx + 1} เรียบร้อย")
            self.reindex_steps()

    def reindex_steps(self):
        for i, step in enumerate(self.steps):
            step["title_label"].configure(text=f"ขั้นตอนที่ {i + 1}")
            if "index_entry" in step and step["index_entry"].winfo_exists():
                step["index_entry"].delete(0, "end")
                step["index_entry"].insert(0, str(i + 1))

    def move_step_up(self, step_id):
        idx = next((i for i, step in enumerate(self.steps) if step["id"] == step_id), None)
        if idx is not None and idx > 0:
            self.steps[idx], self.steps[idx - 1] = self.steps[idx - 1], self.steps[idx]
            self.reorder_step_cards_ui()
            self.flash_card_border(self.steps[idx - 1]["card_frame"])
            self.add_log(f"[*] เลื่อนขั้นตอนที่ {idx + 1} ขึ้นเป็นขั้นตอนที่ {idx}")

    def move_step_down(self, step_id):
        idx = next((i for i, step in enumerate(self.steps) if step["id"] == step_id), None)
        if idx is not None and idx < len(self.steps) - 1:
            self.steps[idx], self.steps[idx + 1] = self.steps[idx + 1], self.steps[idx]
            self.reorder_step_cards_ui()
            self.flash_card_border(self.steps[idx + 1]["card_frame"])
            self.add_log(f"[*] เลื่อนขั้นตอนที่ {idx + 1} ลงเป็นขั้นตอนที่ {idx + 2}")

    def reorder_step_cards_ui(self):
        for step in self.steps:
            step["card_frame"].pack(fill="x", pady=8, padx=5)
        self.reindex_steps()

    def on_move_entry_submit(self, step_id, entry):
        val_str = entry.get().strip()
        if not val_str.isdigit():
            idx = next((i for i, step in enumerate(self.steps) if step["id"] == step_id), None)
            if idx is not None:
                entry.delete(0, "end")
                entry.insert(0, str(idx + 1))
            return
            
        new_idx = int(val_str) - 1
        total_steps = len(self.steps)
        
        if new_idx < 0:
            new_idx = 0
        elif new_idx >= total_steps:
            new_idx = total_steps - 1
            
        current_idx = next((i for i, step in enumerate(self.steps) if step["id"] == step_id), None)
        if current_idx is not None and current_idx != new_idx:
            step_data = self.steps.pop(current_idx)
            self.steps.insert(new_idx, step_data)
            self.reorder_step_cards_ui()
            self.add_log(f"[*] ย้ายขั้นตอนจากลำดับที่ {current_idx + 1} ไปเป็นลำดับที่ {new_idx + 1}")
        else:
            if current_idx is not None:
                entry.delete(0, "end")
                entry.insert(0, str(current_idx + 1))

    def get_randomized_delay(self, delay_val):
        if not delay_val:
            return 0.0
        if isinstance(delay_val, (int, float)):
            return float(delay_val)
        val_str = str(delay_val).strip()
        if "-" in val_str:
            try:
                parts = val_str.split("-")
                low = float(parts[0].strip())
                high = float(parts[1].strip())
                if low > high:
                    low, high = high, low
                val = random.uniform(low, high)
                return val
            except ValueError:
                pass
        try:
            return float(val_str)
        except ValueError:
            return 0.0

    def update_step_confidence(self, step_id, val):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["confidence"] = float(val)
            step["conf_val_label"].configure(text=f"{val:.2f}")

    def update_step_delay(self, step_id, val, entry=None):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["delay"] = val
            if entry and entry.winfo_exists():
                entry.delete(0, "end")
                entry.insert(0, str(val))

    def on_step_delay_entry_change(self, step_id, val_str, slider=None):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["delay"] = val_str.strip()
            try:
                val = float(val_str)
                if slider and slider.winfo_exists():
                    slider.set(min(10.0, max(0.1, val)))
            except ValueError:
                pass

    def toggle_action_type(self, step_id, val):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["action_type"] = val
            idx = self.steps.index(step) + 1
            self.add_log(f"[*] ขั้นตอนที่ {idx}: เปลี่ยนการทำงานเป็น {val}")
            if val == "พิมพ์ข้อความ":
                step["text_entry_frame"].pack(fill="x", pady=(2, 6), before=step["conf_row"])
            else:
                step["text_entry_frame"].pack_forget()

    def update_step_text(self, step_id, text):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["type_text"] = text

    def open_region_picker(self, step_id):
        RegionPicker(self, lambda x, y, w, h: self.set_search_region(step_id, x, y, w, h))

    def view_search_region(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step and step.get("search_region"):
            reg = step["search_region"]
            RegionViewer(self, reg["x"], reg["y"], reg["w"], reg["h"])
        else:
            messagebox.showinfo("แจ้งเตือน", "ยังไม่ได้ตั้งค่าขอบเขตสำหรับขั้นตอนนี้\n(ระบบจะค้นหาทั่วทั้งหน้าจอ)")

    def apply_smooth_scroll(self, scroll_frame):
        canvas = scroll_frame._parent_canvas

        canvas.target_y = canvas.yview()[0]
        canvas.current_y = canvas.yview()[0]
        canvas.scroll_job = None
        
        def animate_scroll():
            diff = canvas.target_y - canvas.current_y
            if abs(diff) > 0.001:
                canvas.current_y += diff * 0.25
                canvas.yview_moveto(canvas.current_y)
                canvas.scroll_job = self.after(16, animate_scroll)
            else:
                canvas.yview_moveto(canvas.target_y)
                canvas.current_y = canvas.target_y
                canvas.scroll_job = None

        def smooth_mouse_wheel(event):
            y_min, y_max = canvas.yview()
            scroll_range = y_max - y_min
            if scroll_range >= 1.0:
                return
                
            step = -1 * (event.delta / 120) * 0.07  # Increased step slightly for better responsiveness
            
            # If not animating, sync start positions with current scrollbar location
            if not canvas.scroll_job:
                canvas.current_y = canvas.yview()[0]
                canvas.target_y = canvas.current_y
                
            # Accumulate scroll target
            canvas.target_y = max(0.0, min(1.0 - scroll_range, canvas.target_y + step))
            
            # Start animation loop only if it's not already running
            if not canvas.scroll_job:
                animate_scroll()
            
        scroll_frame._mouse_wheel = smooth_mouse_wheel

    def set_search_region(self, step_id, x, y, w, h):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["search_region"] = {"x": x, "y": y, "w": w, "h": h}
            region_text = f"ขอบเขต: X={x} Y={y}\nขนาด: {w}x{h}"
            step["region_label"].configure(text=region_text, text_color=TEXT_COLOR)
            step["counting_region_label"].configure(text=region_text, text_color=TEXT_COLOR)
            step["ocr_region_label"].configure(text=region_text, text_color=TEXT_COLOR)
            idx = self.steps.index(step) + 1
            self.add_log(f"[+] ขั้นตอนที่ {idx}: ตั้งค่าขอบเขตแสกน X={x}, Y={y}, กว้าง={w}, สูง={h}")

    def clear_search_region(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step:
            step["search_region"] = None
            step["region_label"].configure(text="ขอบเขตตรวจจับ: ทั่วทั้งหน้าจอ", text_color=TEXT_MUTED)
            step["counting_region_label"].configure(text="ขอบเขตตรวจจับ: ทั่วทั้งหน้าจอ", text_color=TEXT_MUTED)
            step["ocr_region_label"].configure(text="ขอบเขตตรวจจับ: ทั่วทั้งหน้าจอ", text_color=TEXT_MUTED)
            idx = self.steps.index(step) + 1
            self.add_log(f"[-] ขั้นตอนที่ {idx}: ล้างค่าขอบเขตแสกน (ค้นหาทั่วทั้งหน้าจอ)")

    def open_coordinate_picker_add(self, step_id):
        CoordinatePicker(self, lambda x, y: self.add_click_target(step_id, x, y))

    def add_click_target(self, step_id, x, y):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None or x is None or y is None:
            return

        point = {"x": x, "y": y, "delay_after": 0.0, "click_count": 1, "click_interval": 0.1, "random_offset": 3}
        step["click_targets"].append(point)
        point_index = len(step["click_targets"]) - 1

        if point_index == 0:
            step["click_targets_placeholder"].pack_forget()

        self._render_click_point_row(step, point_index, flash=True)

        idx = self.steps.index(step) + 1
        self.add_log(f"[+] ขั้นตอนที่ {idx}: เพิ่มจุดคลิกที่ {point_index + 1} → X={x}, Y={y}")

    def _render_click_point_row(self, step, point_index, flash=False):
        step_id = step["id"]
        point = step["click_targets"][point_index]

        row_frame = ctk.CTkFrame(step["click_targets_frame"], fg_color=POINT_TAG_COLOR, corner_radius=4)
        row_frame.pack(fill="x", padx=6, pady=2)
        if flash:
            self.flash_point_row(row_frame)

        if "action" not in point:
            point["action"] = "click"
        if "click_count" not in point:
            point["click_count"] = 1
        if "type_text" not in point:
            point["type_text"] = ""
        if "delay_before_type" not in point:
            point["delay_before_type"] = 0.2
        if "delay_after" not in point:
            point["delay_after"] = 0.0

        del_pt_btn = ctk.CTkButton(
            row_frame,
            corner_radius=8,
            text="✕",
            fg_color="transparent",
            hover_color=DELETE_HOVER,
            text_color=DELETE_RED,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=22,
            height=22,
            command=lambda pi=point_index, rf=row_frame: self.remove_click_target(step_id, pi, rf)
        )
        del_pt_btn.pack(side="right", padx=(2, 4))

        ctk.CTkLabel(row_frame, text="วิ", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="right", padx=(0, 4))
        
        delay_entry = ctk.CTkEntry(
            row_frame,
            width=46,
            height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center",
            placeholder_text="0.2-0.5"
        )
        current_delay = point.get("delay_after", 0.0)
        if isinstance(current_delay, (int, float)):
            if current_delay > 0:
                delay_entry.insert(0, str(current_delay))
        else:
            if str(current_delay).strip() not in ("", "0", "0.0"):
                delay_entry.insert(0, str(current_delay))
        delay_entry.pack(side="right", padx=(0, 2))
        
        ctk.CTkLabel(row_frame, text="รอ:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="right", padx=(4, 2))

        # Checkbox for batch deletion selection
        chk_var = ctk.BooleanVar(value=False)
        point["_selected_for_del"] = chk_var
        
        chk_select = ctk.CTkCheckBox(
            row_frame,
            text="",
            variable=chk_var,
            width=18,
            height=18,
            checkbox_width=14,
            checkbox_height=14,
            border_width=1.5,
            border_color=("#94A3B8", "#475569"),
            hover_color=ACCENT_HOVER,
            fg_color=ACCENT_ORANGE
        )
        chk_select.pack(side="left", padx=(5, 1))

        badge = ctk.CTkLabel(
            row_frame,
            text=f" {point_index + 1} ",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_COLOR,
            fg_color=ACCENT_ORANGE,
            corner_radius=3,
            width=20,
            height=18
        )
        badge.pack(side="left", padx=(2, 4), pady=4)

        ctk.CTkLabel(row_frame, text="X:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=(2, 1))
        x_entry = ctk.CTkEntry(
            row_frame,
            width=42,
            height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center"
        )
        x_entry.insert(0, str(point["x"]))
        x_entry.pack(side="left", padx=(0, 2))

        ctk.CTkLabel(row_frame, text="Y:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=(2, 1))
        y_entry = ctk.CTkEntry(
            row_frame,
            width=42,
            height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center"
        )
        y_entry.insert(0, str(point["y"]))
        y_entry.pack(side="left", padx=(0, 2))

        repick_btn = ctk.CTkButton(
            row_frame,
            corner_radius=8,
            text="🎯",
            fg_color="transparent",
            hover_color=("#DBEAFE", "#30201a"),
            text_color=ACCENT_ORANGE,
            font=ctk.CTkFont(size=9, weight="bold"),
            width=20,
            height=22,
            command=lambda sid=step_id, pi=point_index, xe=x_entry, ye=y_entry: 
                self.open_coordinate_picker_edit(sid, pi, xe, ye)
        )
        repick_btn.pack(side="left", padx=(1, 6))
        
        # Random Offset Configuration (px)
        ctk.CTkLabel(row_frame, text="สุ่ม:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=(4, 1))
        offset_entry = ctk.CTkEntry(
            row_frame,
            width=28,
            height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center",
            placeholder_text="3"
        )
        offset_entry.insert(0, str(point.get("random_offset", 3)))
        offset_entry.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(row_frame, text="px", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=1)

        mode_menu = ctk.CTkOptionMenu(
            row_frame,
            values=["คลิกอย่างเดียว", "พิมพ์อย่างเดียว", "คลิกแล้วพิมพ์"],
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            width=100,
            height=22,
            fg_color=("#E2E8F0", "#1E293B"),
            button_color="#1E3A5F",
            button_hover_color=("#CBD5E1", "#334155"),
            text_color=("#1E293B", "#FFFFFF"),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=9)
        )
        mode_map_inv = {"click": "คลิกอย่างเดียว", "type": "พิมพ์อย่างเดียว", "click_type": "คลิกแล้วพิมพ์"}
        mode_menu.set(mode_map_inv.get(point["action"], "คลิกอย่างเดียว"))
        mode_menu.pack(side="left", padx=(1, 6))

        action_container = ctk.CTkFrame(row_frame, fg_color="transparent")
        action_container.pack(side="left", fill="both", expand=True, padx=(2, 2))

        click_sub = ctk.CTkFrame(action_container, fg_color="transparent")
        ctk.CTkLabel(click_sub, text="คลิก:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=1)
        click_entry = ctk.CTkEntry(
            click_sub,
            width=28,
            height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center",
            placeholder_text="1"
        )
        click_entry.insert(0, str(point.get("click_count", 1)))
        click_entry.pack(side="left", padx=1)
        ctk.CTkLabel(click_sub, text="ครั้ง ห่าง:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=1)
        
        interval_entry = ctk.CTkEntry(
            click_sub,
            width=32,
            height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center",
            placeholder_text="0.1-0.3"
        )
        interval_entry.insert(0, str(point.get("click_interval", 0.1)))
        interval_entry.pack(side="left", padx=1)
        ctk.CTkLabel(click_sub, text="วิ", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=1)

        delay_before_sub = ctk.CTkFrame(action_container, fg_color="transparent")
        ctk.CTkLabel(delay_before_sub, text="รอพิมพ์:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=1)
        delay_before_entry = ctk.CTkEntry(
            delay_before_sub,
            width=32,
            height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            justify="center",
            placeholder_text="0.2"
        )
        delay_before_entry.insert(0, str(point.get("delay_before_type", 0.2)))
        delay_before_entry.pack(side="left", padx=1)
        ctk.CTkLabel(delay_before_sub, text="วิ", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=1)

        type_sub = ctk.CTkFrame(action_container, fg_color="transparent")
        ctk.CTkLabel(type_sub, text="พิมพ์:", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side="left", padx=1)
        type_entry = ctk.CTkEntry(
            type_sub,
            width=120,
            height=22,
            font=ctk.CTkFont(family="Segoe UI", size=9),
            fg_color=("#FFFFFF", "#0F0F11"),
            text_color=("#0F172A", "#FFFFFF"),
            border_color=("#CBD5E1", "#1E293B"),
            border_width=1,
            placeholder_text="ข้อความ..."
        )
        type_entry.insert(0, str(point.get("type_text", "")))
        type_entry.pack(side="left", fill="x", expand=True, padx=1)

        def update_mode_visibility(selected_mode):
            mode_map = {"คลิกอย่างเดียว": "click", "พิมพ์อย่างเดียว": "type", "คลิกแล้วพิมพ์": "click_type"}
            point["action"] = mode_map.get(selected_mode, "click")
            
            click_sub.pack_forget()
            delay_before_sub.pack_forget()
            type_sub.pack_forget()
            
            if point["action"] == "click":
                click_sub.pack(side="left", padx=2)
            elif point["action"] == "type":
                type_sub.pack(side="left", fill="x", expand=True, padx=2)
            elif point["action"] == "click_type":
                click_sub.pack(side="left", padx=2)
                delay_before_sub.pack(side="left", padx=2)
                type_sub.pack(side="left", fill="x", expand=True, padx=2)

        mode_menu.configure(command=update_mode_visibility)
        update_mode_visibility(mode_map_inv.get(point["action"], "คลิกอย่างเดียว"))

        x_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=x_entry: self.update_point_x(sid, pi, entry.get()))
        y_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=y_entry: self.update_point_y(sid, pi, entry.get()))
        click_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=click_entry: self.update_point_click_count(sid, pi, entry.get()))
        interval_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=interval_entry: self.update_point_click_interval(sid, pi, entry.get()))
        offset_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=offset_entry: self.update_point_random_offset(sid, pi, entry.get()))
        delay_before_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=delay_before_entry: self.update_point_delay_before_type(sid, pi, entry.get()))
        type_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=type_entry: self.update_point_type_text(sid, pi, entry.get()))
        delay_entry.bind("<KeyRelease>", lambda event, sid=step_id, pi=point_index, entry=delay_entry: self.update_point_delay(sid, pi, entry.get()))

        point["_row_frame"] = row_frame

    def update_point_click_count(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            try:
                val = int(value_str)
                step["click_targets"][point_index]["click_count"] = max(1, val)
            except ValueError:
                pass

    def update_point_click_interval(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            step["click_targets"][point_index]["click_interval"] = value_str.strip()

    def update_point_random_offset(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            try:
                val = int(value_str)
                step["click_targets"][point_index]["random_offset"] = max(0, val)
            except ValueError:
                pass

    def update_point_delay(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            step["click_targets"][point_index]["delay_after"] = value_str.strip()

    def update_point_delay_before_type(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            step["click_targets"][point_index]["delay_before_type"] = value_str.strip()

    def update_point_x(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            try:
                val = int(value_str)
                step["click_targets"][point_index]["x"] = val
            except ValueError:
                pass

    def update_point_y(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            try:
                val = int(value_str)
                step["click_targets"][point_index]["y"] = val
            except ValueError:
                pass

    def open_coordinate_picker_edit(self, step_id, point_index, x_entry, y_entry):
        CoordinatePicker(self, lambda x, y: self.edit_click_target(step_id, point_index, x, y, x_entry, y_entry))

    def edit_click_target(self, step_id, point_index, x, y, x_entry, y_entry):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None or x is None or y is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            step["click_targets"][point_index]["x"] = x
            step["click_targets"][point_index]["y"] = y
            
            x_entry.delete(0, "end")
            x_entry.insert(0, str(x))
            y_entry.delete(0, "end")
            y_entry.insert(0, str(y))
            
            idx = self.steps.index(step) + 1
            self.add_log(f"[*] ขั้นตอนที่ {idx}: แก้ไขพิกัดจุดคลิกที่ {point_index + 1} เป็น X={x}, Y={y}")

    def update_point_type_text(self, step_id, point_index, value_str):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if 0 <= point_index < len(step["click_targets"]):
            step["click_targets"][point_index]["type_text"] = value_str

    def type_text_with_keys(self, text, is_turbo=False):
        if not text:
            return
        parts = re.split(r'(\{.*?\})', text)
        interval = 0.01 if is_turbo else 0.04
        
        for part in parts:
            if part.startswith('{') and part.endswith('}'):
                key_name = part[1:-1].lower().strip()
                allowed_keys = {
                    'enter': 'enter',
                    'esc': 'esc',
                    'escape': 'esc',
                    'tab': 'tab',
                    'space': 'space',
                    'backspace': 'backspace',
                    'delete': 'delete',
                    'up': 'up',
                    'down': 'down',
                    'left': 'left',
                    'right': 'right'
                }
                if key_name in allowed_keys:
                    pyautogui.press(allowed_keys[key_name])
                else:
                    try:
                        pyautogui.press(key_name)
                    except Exception:
                        pyautogui.write(part, interval=interval)
            else:
                if part:
                    pyautogui.write(part, interval=interval)

    def remove_click_target(self, step_id, point_index, row_frame):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return

        if 0 <= point_index < len(step["click_targets"]):
            step["click_targets"].pop(point_index)

        self._rebuild_click_targets_ui(step)

        idx = self.steps.index(step) + 1
        self.add_log(f"[-] ลบจุดคลิกที่ {point_index + 1} เรียบร้อย")

    def clear_all_click_targets(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if not step["click_targets"]:
            return
            
        if not messagebox.askyesno("ยืนยัน", "คุณต้องการลบจุดคลิกทั้งหมดของขั้นตอนนี้ใช่หรือไม่?"):
            return
            
        step["click_targets"].clear()
        self._rebuild_click_targets_ui(step)
        
        idx = self.steps.index(step) + 1
        self.add_log(f"[-] ขั้นตอนที่ {idx}: ลบจุดคลิกทั้งหมดเรียบร้อยแล้ว")

    def delete_selected_click_targets(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if step is None:
            return
        if not step["click_targets"]:
            return
            
        selected_points = []
        remaining_points = []
        
        for pt in step["click_targets"]:
            chk_var = pt.get("_selected_for_del")
            if chk_var and chk_var.get():
                selected_points.append(pt)
            else:
                remaining_points.append(pt)
                
        if not selected_points:
            messagebox.showinfo("ข้อมูล", "กรุณาเลือกจุดคลิกที่ต้องการลบอย่างน้อย 1 จุด")
            return
            
        if not messagebox.askyesno("ยืนยัน", f"คุณต้องการลบจุดคลิกที่เลือกทั้งหมด {len(selected_points)} จุดใช่หรือไม่?"):
            return
            
        step["click_targets"] = remaining_points
        self._rebuild_click_targets_ui(step)
        
        idx = self.steps.index(step) + 1
        self.add_log(f"[-] ขั้นตอนที่ {idx}: ลบจุดคลิกที่เลือก {len(selected_points)} จุดเรียบร้อยแล้ว")

    def open_delete_multiple_steps_dialog(self):
        if not self.steps:
            messagebox.showinfo("ข้อมูล", "ไม่มีขั้นตอนในระบบให้ลบ")
            return
            
        dialog = ctk.CTkToplevel(self)
        dialog.title("ลบหลายขั้นตอนพร้อมกัน")
        dialog.geometry("450x550")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 275
        dialog.geometry(f"+{x}+{y}")
        
        dialog.configure(fg_color=BG_COLOR)
        
        lbl_title = ctk.CTkLabel(
            dialog,
            text="เลือกขั้นตอนที่ต้องการลบ",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=ACCENT_ORANGE
        )
        lbl_title.pack(pady=(15, 10))
        
        # Checkboxes list frame
        scroll_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color=CARD_BG,
            scrollbar_button_color=("#CBD5E1", "#334155"),
            height=350
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        checkbox_vars = {}
        checkbox_widgets = []
        
        # Select All Checkbox
        select_all_var = ctk.BooleanVar(value=False)
        
        def toggle_select_all():
            val = select_all_var.get()
            for v in checkbox_vars.values():
                v.set(val)
            update_del_btn_text()
                
        chk_all = ctk.CTkCheckBox(
            dialog,
            text="เลือกทั้งหมด (Select All)",
            variable=select_all_var,
            command=toggle_select_all,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            checkbox_width=18,
            checkbox_height=18,
            border_width=2,
            border_color=("#94A3B8", "#475569"),
            hover_color=ACCENT_HOVER,
            fg_color=ACCENT_ORANGE,
            text_color=TEXT_COLOR
        )
        chk_all.pack(anchor="w", padx=30, pady=5)
        
        # Add checkboxes for each step
        for i, step in enumerate(self.steps):
            step_id = step["id"]
            name_val = step.get("step_name", "")
            mode_val = step["mode"]
            display_name = f"ขั้นตอนที่ {i+1}: {name_val}" if name_val else f"ขั้นตอนที่ {i+1} ({mode_val})"
            
            var = ctk.BooleanVar(value=False)
            checkbox_vars[step_id] = var
            
            chk = ctk.CTkCheckBox(
                scroll_frame,
                text=display_name,
                variable=var,
                command=lambda: update_del_btn_text(),
                font=ctk.CTkFont(family="Segoe UI", size=12),
                checkbox_width=18,
                checkbox_height=18,
                border_width=2,
                border_color=("#94A3B8", "#475569"),
                hover_color=ACCENT_HOVER,
                fg_color=ACCENT_ORANGE,
                text_color=TEXT_COLOR
            )
            chk.pack(anchor="w", padx=10, pady=6)
            checkbox_widgets.append(chk)
            
        def update_del_btn_text():
            count = sum(1 for v in checkbox_vars.values() if v.get())
            btn_del.configure(text=f"🗑️ ลบขั้นตอนที่เลือก ({count})")
            if count == len(self.steps):
                select_all_var.set(True)
            else:
                select_all_var.set(False)
                
        def confirm_delete():
            selected_ids = [sid for sid, v in checkbox_vars.items() if v.get()]
            if not selected_ids:
                messagebox.showinfo("ข้อมูล", "กรุณาเลือกขั้นตอนที่ต้องการลบอย่างน้อย 1 ขั้นตอน")
                return
                
            if not messagebox.askyesno("ยืนยันการลบ", f"คุณต้องการลบขั้นตอนที่เลือกทั้งหมด {len(selected_ids)} ขั้นตอนใช่หรือไม่?"):
                return
                
            # Destroy the deleted step widgets
            for step in self.steps:
                if step["id"] in selected_ids:
                    try:
                        step["card_frame"].destroy()
                    except Exception:
                        pass
                        
            self.steps = [s for s in self.steps if s["id"] not in selected_ids]
            
            self.reorder_step_cards_ui()
            self.rebuild_jump_sidebars()
            
            self.add_log(f"[-] ลบหลายขั้นตอนพร้อมกันสำเร็จ: {len(selected_ids)} ขั้นตอน")
            dialog.destroy()
            
        btn_del = ctk.CTkButton(
            dialog,
            corner_radius=8,
            text="🗑️ ลบขั้นตอนที่เลือก (0)",
            fg_color=("#EF4444", "#DC2626"),
            hover_color=("#DC2626", "#B91C1C"),
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=confirm_delete,
            height=36
        )
        btn_del.pack(fill="x", padx=20, pady=(10, 20))

    def _rebuild_click_targets_ui(self, step):
        frame = step["click_targets_frame"]
        for widget in frame.winfo_children():
            widget.destroy()

        if not step["click_targets"]:
            placeholder_lbl = ctk.CTkLabel(
                frame,
                text="ยังไม่มีจุดคลิก — กด '+ เพิ่มจุดคลิก' ด้านบน",
                font=ctk.CTkFont(size=10),
                text_color=TEXT_MUTED
            )
            placeholder_lbl.pack(padx=8, pady=6)
            step["click_targets_placeholder"] = placeholder_lbl
        else:
            step["click_targets_placeholder"] = ctk.CTkLabel(frame, text="")
            for i in range(len(step["click_targets"])):
                self._render_click_point_row(step, i)

    def browse_trigger_image(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if not step:
            return
            
        file_path = filedialog.askopenfilename(
            title="เลือกรูปภาพต้นแบบตรวจจับสำหรับขั้นตอนนี้",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            step["template_path"] = file_path
            filename = os.path.basename(file_path)
            step["image_label"].configure(text=filename, text_color=TEXT_COLOR)
            idx = self.steps.index(step) + 1
            self.add_log(f"[+] ขั้นตอนที่ {idx}: โหลดภาพ {filename}")
            
            try:
                pil_img = Image.open(file_path)
                pil_img.thumbnail((150, 70))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                step["preview_label"].configure(image=ctk_img, text="")
            except Exception as e:
                self.add_log(f"[Error] ไม่สามารถโหลดรูปพรีวิวได้: {e}")

    def open_capture_picker(self, step_id):
        ScreenCapturePicker(self, lambda img: self.set_captured_image(step_id, img))

    def set_captured_image(self, step_id, img):
        if img is None:
            return
        
        step = next((s for s in self.steps if s["id"] == step_id), None)
        if not step:
            return
            
        save_dir = os.path.join(os.getcwd(), "captured_templates")
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                self.add_log(f"[Error] ไม่สามารถสร้างโฟลเดอร์เก็บรูปภาพได้: {e}")
                return
                
        filename = f"template_{step_id}_{int(time.time())}.png"
        file_path = os.path.join(save_dir, filename)
        
        try:
            img.save(file_path)
            step["template_path"] = file_path
            step["image_label"].configure(text=filename, text_color=TEXT_COLOR)
            idx = self.steps.index(step) + 1
            self.add_log(f"[+] ขั้นตอนที่ {idx}: แคปเจอร์และบันทึกรูป {filename}")
            
            img.thumbnail((150, 70))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            step["preview_label"].configure(image=ctk_img, text="")
        except Exception as e:
            self.add_log(f"[Error] ไม่สามารถบันทึกหรือแสดงรูปแคปเจอร์ได้: {e}")

    def add_log(self, text):
        self.log_queue.put(text)

    def poll_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", msg + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(100, self.poll_logs)

    def toggle_bot(self):
        if self.bot_running:
            self.stop_bot()
        else:
            self.start_bot()

    def start_bot(self):
        if not self.steps:
            self.add_log("[Warning] กรุณาเพิ่มขั้นตอนก่อนเริ่มต้น!")
            return
            
        # Validate all steps based on their active mode
        for i, step in enumerate(self.steps):
            mode = step.get("mode", "บอตปกติ")
            if mode == "บอตปกติ":
                if step["action_type"] == "คลิกเมาส์" and not step["click_targets"]:
                    self.add_log(f"[Warning] ขั้นตอนที่ {i + 1} (บอตปกติ) ยังไม่ได้เพิ่มจุดคลิก!")
                    return
                if not step["template_path"]:
                    self.add_log(f"[Warning] ขั้นตอนที่ {i + 1} (บอตปกติ) ยังไม่ได้เลือกรูปตรวจจับ!")
                    return
            elif mode == "นับวัตถุ":
                if not step.get("counting_targets", []):
                    self.add_log(f"[Warning] ขั้นตอนที่ {i + 1} (นับวัตถุ) ยังไม่ได้เพิ่มภาพสำหรับนับ!")
                    return
            elif mode == "บวกเลข OCR":
                if not step.get("search_region"):
                    self.add_log(f"[Warning] ขั้นตอนที่ {i + 1} (บวกเลข OCR) กรุณากำหนดขอบเขตสแกนเพื่ออ่านค่าตัวเลข!")
                    return
                
        # Initialize Telegram timeout variables
        now = time.time()
        for step in self.steps:
            step["_last_trigger_time"] = now
            step["_telegram_alert_sent"] = False

        self.bot_running = True
        self.stats_data["start_time"] = time.time()
        self.status_badge.configure(text="RUNNING", fg_color=STATUS_ACTIVE)
        self.toggle_bot_btn.configure(
            text="⏹  หยุดการทำงาน  (STOP BOT)  [F5]",
            fg_color=STATUS_IDLE, hover_color="#D01030"
        )
        self.add_log("[+] เริ่มระบบบอตตรวจจับเงื่อนไขใน 2 วินาที... (กด ESC หรือ F5 เพื่อสั่งหยุดฉุกเฉิน)")
        
        # Spawn worker thread
        self.bot_thread = threading.Thread(target=self.bot_sequence_worker, daemon=True)
        self.bot_thread.start()

    def stop_bot(self):
        if not self.bot_running:
            return
        self.bot_running = False
        self.status_badge.configure(text="IDLE", fg_color=STATUS_IDLE)
        self.toggle_bot_btn.configure(
            text="▶  เริ่มระบบบอต  (START BOT)  [F5]",
            fg_color=ACCENT_ORANGE, hover_color=ACCENT_HOVER
        )
        self.add_log("[-] บอตหยุดการทำงานเรียบร้อยแล้ว")

    def emergency_stop(self):
        if self.bot_running:
            self.after(0, self.stop_bot)
            self.add_log("[!] EMERGENCY STOP TRIGGERED via ESC Hotkey!")

    def bot_sequence_worker(self):
        time.sleep(2)
        last_scan_heartbeat = 0
        
        while self.bot_running:
            if not self.steps:
                self.add_log("[Warning] ไม่มีเงื่อนไขขั้นตอน ระบบจะปิดตัวเอง")
                self.after(0, self.stop_bot)
                break
                
            try:
                if time.time() - last_scan_heartbeat >= 1.0:
                    self.stats_data["total_scan_cycles"] += 1
                    last_scan_heartbeat = time.time()
                    
                    # Check Telegram timeouts
                    if self.telegram_global_enabled_var.get():
                        now = time.time()
                        for s_idx, s in enumerate(self.steps):
                            s_mode = s.get("mode", "บอตปกติ")
                            is_monitored = False
                            if s_mode == "บอตปกติ" and self.telegram_monitor_normal_var.get():
                                is_monitored = True
                            elif s_mode == "นับวัตถุ" and self.telegram_monitor_counting_var.get():
                                is_monitored = True
                            elif s_mode == "บวกเลข OCR" and self.telegram_monitor_ocr_var.get():
                                is_monitored = True

                            if is_monitored and s.get("telegram_alert_enabled", False):
                                timeout_limit = int(s.get("telegram_timeout", 300))
                                last_trig = s.get("_last_trigger_time", now)
                                alert_sent = s.get("_telegram_alert_sent", False)
                                
                                if (now - last_trig) > timeout_limit and not alert_sent:
                                    s["_telegram_alert_sent"] = True
                                    step_name_str = s.get("step_name", "").strip()
                                    s_name = f"'{step_name_str}'" if step_name_str else f"หมายเลข {s_idx + 1}"
                                    
                                    alert_msg = (
                                        f"⚠️ <b>[Freecame Auto Alert]</b>\n"
                                        f"ขั้นตอน: <b>{s_name}</b> (โหมด: {s.get('mode')})\n"
                                        f"🚨 <b>ไม่ตรวจพบภาพต้นแบบหรือทำงานตามเงื่อนไขนานเกิน {timeout_limit} วินาทีแล้ว!</b>\n"
                                        f"กรุณาตรวจสอบระบบตัวบอต"
                                    )
                                    self.send_telegram_notification(alert_msg)

                with mss.MSS() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    screen_img = np.array(sct_img)
                    screen_img = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
                
                condition_triggered = False
                
                for i, step in enumerate(self.steps):
                    mode = step.get("mode", "บอตปกติ")
                    
                    if mode == "บอตปกติ":
                        template_path = step["template_path"]
                        if not template_path:
                            continue
                            
                        try:
                            raw = np.fromfile(template_path, dtype=np.uint8)
                            template = cv2.imdecode(raw, cv2.IMREAD_COLOR)
                        except Exception:
                            template = None
                        if template is None:
                            continue
                        
                        threshold = step["confidence"]
                        search_region = step.get("search_region")
                        
                        if search_region:
                            h_max, w_max, _ = screen_img.shape
                            rx, ry, rw, rh = search_region["x"], search_region["y"], search_region["w"], search_region["h"]
                            sliced_x = max(0, min(rx, w_max - 1))
                            sliced_y = max(0, min(ry, h_max - 1))
                            sliced_w = max(1, min(rw, w_max - sliced_x))
                            sliced_h = max(1, min(rh, h_max - sliced_y))
                            
                            cropped_screen = screen_img[sliced_y:sliced_y+sliced_h, sliced_x:sliced_x+sliced_w]
                            
                            th, tw, _ = template.shape
                            if tw <= sliced_w and th <= sliced_h:
                                result = cv2.matchTemplate(cropped_screen, template, cv2.TM_CCOEFF_NORMED)
                                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                            else:
                                max_val = 0.0
                        else:
                            result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(result)
                        
                        if max_val >= threshold:
                            sid = step["id"]
                            self.stats_data["triggers_count"][sid] = self.stats_data["triggers_count"].get(sid, 0) + 1
                            step["_last_trigger_time"] = time.time()
                            step["_telegram_alert_sent"] = False
                            step["_last_trigger_time"] = time.time()
                            step["_telegram_alert_sent"] = False
                            
                            click_targets = step["click_targets"]
                            if not click_targets:
                                if step.get("action_type", "คลิกเมาส์") == "พิมพ์ข้อความ":
                                    self.add_log(f"[+] ตรวจพบเงื่อนไข [ขั้นตอนที่ {i + 1}] (ความแม่นยำ: {max_val:.2f} >= {threshold:.2f}) → พิมพ์ข้อความโดยตรง")
                                    is_turbo = self.turbo_mode_var.get()
                                    self.type_text_with_keys(step.get("type_text", ""), is_turbo=is_turbo)
                                    self.add_log(f"[+] พิมพ์ข้อความสำเร็จ")
                                    
                                    delay_time = self.get_randomized_delay(step["delay"])
                                    self.add_log(f"[*] หน่วงเวลารอระบบเปลี่ยนแปลง: {delay_time:.1f} วินาที...")
                                    time.sleep(delay_time)
                                    
                                    condition_triggered = True
                                    break
                                else:
                                    continue
                                
                            self.add_log(f"[+] ตรวจพบเงื่อนไข [ขั้นตอนที่ {i + 1}] (ความแม่นยำ: {max_val:.2f} >= {threshold:.2f}) → จะทำ {len(click_targets)} จุด")
                            is_turbo = self.turbo_mode_var.get()
                            
                            for pt_idx, point in enumerate(click_targets):
                                if not self.bot_running:
                                    break
                                    
                                target_x = point["x"]
                                target_y = point["y"]
                                pt_action = point.get("action", "click")
                                click_count = int(point.get("click_count", 1))
                                if click_count < 1:
                                    click_count = 1
                                type_text = point.get("type_text", "").strip()
                                delay_before = self.get_randomized_delay(point.get("delay_before_type", 0.2))

                                effective_clicks = 1 if pt_action == "type" else click_count

                                if pt_action != "type" or type_text:
                                    click_interval = point.get("click_interval", 0.1)
                                    for c in range(effective_clicks):
                                        if not self.bot_running:
                                            break
                                            
                                        r_offset = int(point.get("random_offset", 3))
                                        if r_offset > 0:
                                            offset_x = random.randint(-r_offset, r_offset)
                                            offset_y = random.randint(-r_offset, r_offset)
                                        else:
                                            offset_x = 0
                                            offset_y = 0
                                        click_x = target_x + offset_x
                                        click_y = target_y + offset_y

                                        if is_turbo:
                                            win32api.SetCursorPos((click_x, click_y))
                                            # A tiny sleep of 5ms ensures Windows updates coordinates before firing mouse_event
                                            time.sleep(0.005)
                                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, click_x, click_y, 0, 0)
                                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, click_x, click_y, 0, 0)
                                            
                                            if pt_action == "click" and not type_text and step.get("action_type", "คลิกเมาส์") == "พิมพ์ข้อความ" and pt_idx == len(click_targets) - 1 and c == effective_clicks - 1:
                                                self.add_log(f"[+] พิมพ์ข้อความ (Turbo)...")
                                                time.sleep(0.05)
                                                self.type_text_with_keys(step.get("type_text", ""), is_turbo=True)
                                                self.add_log(f"[+] พิมพ์ข้อความสำเร็จ")
                                            else:
                                                self.add_log(f"[+] คลิกจุดที่ {pt_idx + 1}: X={target_x} (สุ่ม {click_x}), Y={target_y} (สุ่ม {click_y}) (สุ่ม ±{r_offset}px) (Turbo) [ครั้งที่ {c + 1}/{effective_clicks}]")
                                        else:
                                            duration = random.uniform(0.2, 0.4)
                                            pyautogui.moveTo(click_x, click_y, duration=duration)
                                            
                                            pyautogui.mouseDown()
                                            time.sleep(random.uniform(0.05, 0.12))
                                            pyautogui.mouseUp()
                                            
                                            if pt_action == "click" and not type_text and step.get("action_type", "คลิกเมาส์") == "พิมพ์ข้อความ" and pt_idx == len(click_targets) - 1 and c == effective_clicks - 1:
                                                self.add_log(f"[+] คลิกเพื่อโฟกัส และกำลังพิมพ์ข้อความ...")
                                                time.sleep(0.2)
                                                self.type_text_with_keys(step.get("type_text", ""), is_turbo=False)
                                                self.add_log(f"[+] พิมพ์ข้อความสำเร็จ")
                                            else:
                                                self.add_log(f"[+] คลิกจุดที่ {pt_idx + 1}: X={target_x} (สุ่ม {click_x}), Y={target_y} (สุ่ม {click_y}) (สุ่ม ±{r_offset}px) [ครั้งที่ {c + 1}/{effective_clicks}]")
                                        
                                        # Delay between clicks if not the last click
                                        if c < effective_clicks - 1:
                                            actual_interval = self.get_randomized_delay(click_interval)
                                            if actual_interval > 0:
                                                self.add_log(f"[*] เว้นช่วงคลิก {actual_interval:.2f} วินาที...")
                                            time.sleep(actual_interval)
                                
                                if pt_action == "click_type" and type_text and self.bot_running:
                                    if delay_before > 0:
                                        self.add_log(f"[*] รอพิมพ์ {delay_before:.2f}s...")
                                        time.sleep(delay_before)

                                if (pt_action == "type" or pt_action == "click_type") and type_text and self.bot_running:
                                    time.sleep(0.05 if is_turbo else 0.10)
                                    self.add_log(f"[+] พิมพ์ข้อความจุดที่ {pt_idx + 1} -> '{type_text}'")
                                    self.type_text_with_keys(type_text, is_turbo=is_turbo)
                                    self.add_log(f"[+] พิมพ์ข้อความสำเร็จ")

                                if pt_idx < len(click_targets) - 1:
                                    point_delay = self.get_randomized_delay(point.get("delay_after", 0.0))
                                    if point_delay > 0:
                                        self.add_log(f"[*] รอ {point_delay:.2f}s ก่อนกดจุดที่ {pt_idx + 2}...")
                                        time.sleep(point_delay)
                                    else:
                                        time.sleep(0.03 if is_turbo else 0.10)
                            
                            delay_time = self.get_randomized_delay(step["delay"])
                            if delay_time > 0:
                                self.add_log(f"[*] หน่วงเวลารอระบบเปลี่ยนแปลง: {delay_time:.2f} วินาที...")
                                time.sleep(delay_time)
                                
                            condition_triggered = True
                            break

                    elif mode == "นับวัตถุ":
                        h_max, w_max, _ = screen_img.shape
                        sliced_x, sliced_y, sliced_w, sliced_h = 0, 0, w_max, h_max
                        search_region = step.get("search_region")
                        
                        if search_region:
                            sliced_x = max(0, min(search_region["x"], w_max - 1))
                            sliced_y = max(0, min(search_region["y"], h_max - 1))
                            sliced_w = max(1, min(search_region["w"], w_max - sliced_x))
                            sliced_h = max(1, min(search_region["h"], h_max - sliced_y))
                            
                        cropped_screen = screen_img[sliced_y:sliced_y+sliced_h, sliced_x:sliced_x+sliced_w]
                        
                        # Create copy for visual detection box overlay
                        vis_screen = cropped_screen.copy()
                        color_palette = [
                            (0, 255, 0),     # Green
                            (255, 105, 180), # Hot Pink
                            (0, 215, 255),   # Cyan/Yellow-Green
                            (255, 165, 0),   # Orange
                            (147, 112, 219)  # Purple
                        ]
                        
                        total_step_count = 0
                        target_results_str = []
                        
                        for t_idx, target in enumerate(step.get("counting_targets", [])):
                            path = target["path"]
                            try:
                                raw = np.fromfile(path, dtype=np.uint8)
                                tmpl = cv2.imdecode(raw, cv2.IMREAD_COLOR)
                            except Exception:
                                tmpl = None
                            if tmpl is None:
                                continue
                                
                            th, tw, _ = tmpl.shape
                            if tw <= sliced_w and th <= sliced_h:
                                res = cv2.matchTemplate(cropped_screen, tmpl, cv2.TM_CCOEFF_NORMED)
                                loc = np.where(res >= target["confidence"])
                                
                                boxes = []
                                for pt in zip(*loc[::-1]):
                                    score = res[pt[1], pt[0]]
                                    boxes.append([pt[0], pt[1], tw, th, float(score)])
                                    
                                keep = nms(boxes)
                                count = len(keep)
                                
                                # Draw detection bounding boxes
                                box_color = color_palette[t_idx % len(color_palette)]
                                for b in keep:
                                    bx, by, bw, bh = b[0], b[1], b[2], b[3]
                                    cv2.rectangle(vis_screen, (bx, by), (bx + bw, by + bh), box_color, 2)
                            else:
                                count = 0
                                
                            target["last_count"] = count
                            target["accum_count"] = target.get("accum_count", 0) + count
                            total_step_count += target["accum_count"]
                            
                            tname = os.path.basename(path)
                            target_results_str.append(f"{tname}: สะสม {target['accum_count']} (พบ {count})")
                            
                            if "val_lbl" in target and target["val_lbl"].winfo_exists():
                                self.after(0, lambda lbl=target["val_lbl"], acc=target["accum_count"], c=count: lbl.configure(text=f"สะสม: {acc} (รอบนี้: {c})"))
                                
                            if tname not in self.stats_data["counting_history"]:
                                self.stats_data["counting_history"][tname] = []
                            self.stats_data["counting_history"][tname].append(target["accum_count"])
                            if len(self.stats_data["counting_history"][tname]) > 30:
                                self.stats_data["counting_history"][tname].pop(0)
                        
                        # Update Visual Preview Label in UI if exists
                        if "counting_preview_lbl" in step and step["counting_preview_lbl"].winfo_exists():
                            try:
                                vis_rgb = cv2.cvtColor(vis_screen, cv2.COLOR_BGR2RGB)
                                pil_vis = Image.fromarray(vis_rgb)
                                pil_vis.thumbnail((200, 100))
                                ctk_vis = ctk.CTkImage(light_image=pil_vis, dark_image=pil_vis, size=pil_vis.size)
                                self.after(0, lambda lbl=step["counting_preview_lbl"], img=ctk_vis: lbl.configure(image=img, text=""))
                            except Exception:
                                pass

                        sid = step["id"]
                        self.stats_data["triggers_count"][sid] = self.stats_data["triggers_count"].get(sid, 0) + 1
                        step["_last_trigger_time"] = time.time()
                        step["_telegram_alert_sent"] = False
                        
                        summary_log = " | ".join(target_results_str)
                        if summary_log:
                            self.add_log(f"[📊 นับวัตถุ] ขั้นตอนที่ {i + 1} → {summary_log} (รวมทั้งหมด: {total_step_count} ชิ้น)")
                        
                        delay_time = self.get_randomized_delay(step["delay"])
                        time.sleep(delay_time)
                        
                    elif mode == "บวกเลข OCR":
                        # Check optional condition template image if defined
                        template_path = step.get("template_path")
                        if template_path and os.path.isfile(template_path):
                            try:
                                raw = np.fromfile(template_path, dtype=np.uint8)
                                template = cv2.imdecode(raw, cv2.IMREAD_COLOR)
                            except Exception:
                                template = None
                                
                            if template is not None:
                                threshold = step.get("confidence", 0.80)
                                result_tmpl = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
                                _, max_val, _, _ = cv2.minMaxLoc(result_tmpl)
                                
                                if max_val < threshold:
                                    # Condition image not matched, skip OCR scan in this cycle
                                    continue
                                else:
                                    self.add_log(f"[+] ตรวจพบภาพเงื่อนไข OCR [ขั้นตอนที่ {i + 1}] (ความแม่นยำ: {max_val:.2f} >= {threshold:.2f}) → เริ่มสแกนอ่านตัวเลข")

                        h_max, w_max, _ = screen_img.shape
                        sliced_x, sliced_y, sliced_w, sliced_h = 0, 0, w_max, h_max
                        search_region = step.get("search_region")
                        
                        if search_region:
                            sliced_x = max(0, min(search_region["x"], w_max - 1))
                            sliced_y = max(0, min(search_region["y"], h_max - 1))
                            sliced_w = max(1, min(search_region["w"], w_max - sliced_x))
                            sliced_h = max(1, min(search_region["h"], h_max - sliced_y))
                            
                        cropped_screen = screen_img[sliced_y:sliced_y+sliced_h, sliced_x:sliced_x+sliced_w]
                        
                        # Auto-upscale small regions for significantly better OCR accuracy
                        ch, cw = cropped_screen.shape[:2]
                        if cw < 150 or ch < 60:
                            scale_factor = 2.5
                            cropped_screen = cv2.resize(cropped_screen, (0, 0), fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
                        
                        try:
                            result = winocr.recognize_cv2_sync(cropped_screen)
                            text = result.get('text', '')
                            
                            text_no_comma = text.replace(",", "")
                            numbers = re.findall(r"\d+\.?\d*", text_no_comma)
                            numbers = [float(n) if '.' in n else int(n) for n in numbers]
                            frame_sum = float(sum(numbers))
                            
                            # Accumulate current scan sum to running total sum
                            current_accum = step.get("last_ocr_sum", 0.0) + frame_sum
                            step["last_ocr_text"] = text_no_comma
                            step["last_ocr_sum"] = current_accum
                            
                            if "lbl_ocr_result_sum" in step and step["lbl_ocr_result_sum"].winfo_exists():
                                self.after(0, lambda lbl=step["lbl_ocr_result_sum"], s=current_accum: lbl.configure(text=f"{s:.2f}"))
                            if "lbl_ocr_result_text" in step and step["lbl_ocr_result_text"].winfo_exists():
                                clean_t = text_no_comma.replace("\n", " ").strip()
                                if len(clean_t) > 30:
                                    clean_t = clean_t[:30] + "..."
                                self.after(0, lambda lbl=step["lbl_ocr_result_text"], t=clean_t: lbl.configure(text=f"\"{t}\" (พบ +{frame_sum:.2f})"))
                                
                            self.stats_data["ocr_sum_history"].append(current_accum)
                            if len(self.stats_data["ocr_sum_history"]) > 30:
                                self.stats_data["ocr_sum_history"].pop(0)
                                
                            if frame_sum > 0:
                                self.add_log(f"[🔢 OCR บวกสะสม] ขั้นตอนที่ {i + 1} → พบตัวเลข +{frame_sum:.2f} (ยอดรวมสะสม: {current_accum:.2f})")
                                
                            sid = step["id"]
                            self.stats_data["triggers_count"][sid] = self.stats_data["triggers_count"].get(sid, 0) + 1
                            step["_last_trigger_time"] = time.time()
                            step["_telegram_alert_sent"] = False
                        except Exception as e:
                            self.add_log(f"[Error OCR] {e}")
                            
                        delay_time = self.get_randomized_delay(step["delay"])
                        time.sleep(delay_time)
                
                if not condition_triggered:
                    time.sleep(0.2)
                    
            except Exception as e:
                self.add_log(f"[Error ในลูปหลักตรวจจับ] {e}")
                time.sleep(1.0)

    def on_step_name_change(self, step_id, name):
        for step in self.steps:
            if step["id"] == step_id:
                step["step_name"] = name
                # Update dashboard if dashboard exists
                if "stats_title" in step and step["stats_title"] and step["stats_title"].winfo_exists():
                    idx = self.steps.index(step) + 1
                    step["stats_title"].configure(text=f"ขั้นตอนที่ {idx} ({name if name else step['mode']})")
                break

    def toggle_jump_sidebars(self):
        self.show_jump_sidebar = not self.show_jump_sidebar
        if self.show_jump_sidebar:
            self.jump_sidebar.pack(side="right", fill="y", padx=(10, 0))
            self.btn_toggle_sidebar_normal.configure(text="📍 ซ่อนแถบทางลัด")
            self.btn_toggle_sidebar_detection.configure(text="📍 ซ่อนแถบทางลัด")
        else:
            self.jump_sidebar.pack_forget()
            self.btn_toggle_sidebar_normal.configure(text="📍 แสดงแถบทางลัด")
            self.btn_toggle_sidebar_detection.configure(text="📍 แสดงแถบทางลัด")

    def rebuild_jump_sidebars(self):
        # Clear existing sidebar widgets
        for widget in self.jump_sidebar.winfo_children():
            widget.destroy()
            
        lbl_nav = ctk.CTkLabel(
            self.jump_sidebar,
            text="Jump",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=TEXT_MUTED
        )
        lbl_nav.pack(pady=(0, 5))
        
        # Populate buttons globally
        for i, step in enumerate(self.steps):
            btn_txt = f"{i+1}"
            
            # Color-code buttons based on mode
            if step["mode"] == "บอตปกติ":
                btn_bg = ("#E2E8F0", "#1E293B")
                btn_text_color = TEXT_COLOR
            else:
                # Highlight Object Counting / OCR steps with Orange Accent
                btn_bg = ACCENT_ORANGE
                btn_text_color = "#FFFFFF"
                
            btn = ctk.CTkButton(
                self.jump_sidebar,
                text=btn_txt,
                width=24,
                height=24,
                corner_radius=12,
                fg_color=btn_bg,
                hover_color=ACCENT_HOVER,
                text_color=btn_text_color,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                command=lambda idx=i: self.jump_to_step(idx)
            )
            btn.pack(pady=2)
            
            # Setup hover tooltip containing step name or step mode
            name_val = step.get("step_name", "")
            tooltip_txt = f"ขั้นตอนที่ {i+1}: {name_val}" if name_val else f"ขั้นตอนที่ {i+1} ({step['mode']})"
            CTkToolTip(btn, tooltip_txt)

    def jump_to_step(self, step_index):
        if step_index < len(self.steps):
            step = self.steps[step_index]
            
            # Auto-switch to the correct tab first
            if step["mode"] == "บอตปกติ":
                self.tabview.set("🤖 ตั้งค่าบอตปกติ")
            else:
                self.tabview.set("🔍 นับวัตถุ & OCR")
                
            # Allow GUI to map the frames
            self.update_idletasks()
            
            card = step.get("card_frame")
            if card and card.winfo_exists():
                try:
                    canvas = card.master._parent_canvas
                    canvas.update_idletasks()
                    
                    y = card.winfo_y()
                    total_h = canvas.bbox("all")[3]
                    
                    if total_h > 0:
                        fraction = y / total_h
                        canvas.yview_moveto(fraction)
                        self.flash_card_border(card)
                except Exception as e:
                    self.add_log(f"[!] ไม่สามารถกระโดดไปขั้นตอนได้: {e}")

    def save_config(self):
        """บันทึก steps ทั้งหมดลง JSON file ที่ผู้ใช้เลือก"""
        if not self.steps:
            messagebox.showwarning("แจ้งเตือน", "ยังไม่มีขั้นตอนให้บันทึก กรุณาเพิ่มขั้นตอนก่อน")
            return

        file_path = filedialog.asksaveasfilename(
            title="บันทึกการตั้งค่าเงื่อนไขทั้งหมด",
            defaultextension=".json",
            filetypes=[("Freecame Config", "*.json"), ("All Files", "*.*")],
            initialfile="freecame_config.json"
        )
        if not file_path:
            return  # ผู้ใช้กด Cancel

        config_data = {
            "version": 3,
            "turbo_mode": self.turbo_mode_var.get(),
            "telegram_global_enabled": self.telegram_global_enabled_var.get(),
            "telegram_bot_token": self.telegram_bot_token_var.get().strip(),
            "telegram_chat_id": self.telegram_chat_id_var.get().strip(),
            "telegram_monitor_normal": self.telegram_monitor_normal_var.get(),
            "telegram_monitor_counting": self.telegram_monitor_counting_var.get(),
            "telegram_monitor_ocr": self.telegram_monitor_ocr_var.get(),
            "steps": []
        }

        for step in self.steps:
            clean_targets = [
                {
                    "x": pt["x"],
                    "y": pt["y"],
                    "delay_after": pt.get("delay_after", 0.0),
                    "click_count": pt.get("click_count", 1),
                    "click_interval": pt.get("click_interval", 0.1),
                    "random_offset": pt.get("random_offset", 3),
                    "action": pt.get("action", "click"),
                    "type_text": pt.get("type_text", ""),
                    "delay_before_type": pt.get("delay_before_type", 0.2)
                }
                for pt in step["click_targets"]
            ]
            
            clean_counting = [
                {
                    "path": t["path"],
                    "confidence": t["confidence"]
                }
                for t in step.get("counting_targets", [])
            ]

            step_entry = {
                "mode": step.get("mode", "บอตปกติ"),
                "step_name": step.get("step_name", ""),
                "template_path": step["template_path"],
                "confidence": step["confidence"],
                "delay": step["delay"],
                "action_type": step["action_type"],
                "type_text": step.get("type_text", ""),
                "search_region": step.get("search_region"),
                "click_targets": clean_targets,
                "counting_targets": clean_counting,
                "telegram_alert_enabled": step.get("telegram_alert_enabled", False),
                "telegram_timeout": step.get("telegram_timeout", 300)
            }
            config_data["steps"].append(step_entry)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            filename = os.path.basename(file_path)
            self.add_log(f"[✓] บันทึกการตั้งค่า {len(self.steps)} ขั้นตอน → {filename}")
            messagebox.showinfo("บันทึกสำเร็จ", f"บันทึกเงื่อนไขทั้งหมด {len(self.steps)} ขั้นตอน\nไปยังไฟล์: {filename}")
        except Exception as e:
            self.add_log(f"[Error] บันทึกไม่สำเร็จ: {e}")
            messagebox.showerror("เกิดข้อผิดพลาด", f"ไม่สามารถบันทึกได้:\n{e}")

    def load_config(self):
        """โหลด steps จาก JSON file ที่ผู้ใช้เลือก แล้วสร้าง UI ใหม่ทั้งหมด"""
        file_path = filedialog.askopenfilename(
            title="โหลดการตั้งค่าเงื่อนไข",
            filetypes=[("Freecame Config", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return  # ผู้ใช้กด Cancel

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            self.add_log(f"[Error] โหลดไฟล์ไม่สำเร็จ: {e}")
            messagebox.showerror("เกิดข้อผิดพลาด", f"ไม่สามารถโหลดไฟล์ได้:\n{e}")
            return

        steps_data = config_data.get("steps", [])
        if not steps_data:
            messagebox.showwarning("ไฟล์ว่าง", "ไม่พบข้อมูลขั้นตอนในไฟล์นี้")
            return

        if self.steps:
            confirm = messagebox.askyesno(
                "ยืนยันการโหลด",
                f"จะลบขั้นตอนปัจจุบัน {len(self.steps)} ขั้นตอน\nและโหลด {len(steps_data)} ขั้นตอนจากไฟล์ ใช่หรือไม่?"
            )
            if not confirm:
                return

        for step in self.steps:
            step["card_frame"].destroy()
        self.steps.clear()

        if "turbo_mode" in config_data:
            self.turbo_mode_var.set(config_data["turbo_mode"])
        if "telegram_global_enabled" in config_data:
            self.telegram_global_enabled_var.set(config_data["telegram_global_enabled"])
        if "telegram_bot_token" in config_data:
            self.telegram_bot_token_var.set(config_data["telegram_bot_token"])
        if "telegram_chat_id" in config_data:
            self.telegram_chat_id_var.set(config_data["telegram_chat_id"])
        if "telegram_monitor_normal" in config_data:
            self.telegram_monitor_normal_var.set(config_data["telegram_monitor_normal"])
        if "telegram_monitor_counting" in config_data:
            self.telegram_monitor_counting_var.set(config_data["telegram_monitor_counting"])
        if "telegram_monitor_ocr" in config_data:
            self.telegram_monitor_ocr_var.set(config_data["telegram_monitor_ocr"])

        filename = os.path.basename(file_path)
        loaded_count = 0

        for step_entry in steps_data:
            mode_val = step_entry.get("mode", "บอตปกติ")
            self.add_step(mode=mode_val)
            step = self.steps[-1]
            self.change_step_mode(step["id"], mode_val)
            
            # Restore step name
            step_name = step_entry.get("step_name", "")
            step["step_name"] = step_name
            if "step_name_entry" in step and step["step_name_entry"].winfo_exists():
                step["step_name_entry"].delete(0, "end")
                step["step_name_entry"].insert(0, step_name)
                
            # Restore Telegram settings
            tele_enabled = step_entry.get("telegram_alert_enabled", False)
            tele_timeout = step_entry.get("telegram_timeout", 300)
            step["telegram_alert_enabled"] = tele_enabled
            step["telegram_timeout"] = tele_timeout
            
            if "telegram_alert_enabled_checkbox" in step and step["telegram_alert_enabled_checkbox"].winfo_exists():
                if tele_enabled:
                    step["telegram_alert_enabled_checkbox"].select()
                else:
                    step["telegram_alert_enabled_checkbox"].deselect()
                    
            if "telegram_timeout_entry" in step and step["telegram_timeout_entry"].winfo_exists():
                step["telegram_timeout_entry"].delete(0, "end")
                step["telegram_timeout_entry"].insert(0, str(tele_timeout))

            tmpl = step_entry.get("template_path")
            if tmpl and os.path.isfile(tmpl):
                step["template_path"] = tmpl
                step["image_label"].configure(
                    text=os.path.basename(tmpl), text_color=TEXT_COLOR
                )
                try:
                    pil_img = Image.open(tmpl)
                    pil_img.thumbnail((150, 70))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    step["preview_label"].configure(image=ctk_img, text="")
                except Exception:
                    pass
            elif tmpl:
                step["image_label"].configure(
                    text=f"⚠ ไม่พบไฟล์: {os.path.basename(tmpl)}", text_color="#FF8C00"
                )

            step["confidence"] = float(step_entry.get("confidence", 0.80))
            step["conf_val_label"].configure(text=f"{step['confidence']:.2f}")
            if "conf_slider" in step and step["conf_slider"].winfo_exists():
                step["conf_slider"].set(step["confidence"])

            step["delay"] = step_entry.get("delay", 1.5)
            if "delay_entry" in step and step["delay_entry"].winfo_exists():
                step["delay_entry"].delete(0, "end")
                step["delay_entry"].insert(0, str(step["delay"]))
            if "delay_slider" in step and step["delay_slider"].winfo_exists():
                try:
                    step["delay_slider"].set(min(10.0, max(0.1, float(step["delay"]))))
                except ValueError:
                    pass

            step["action_type"] = step_entry.get("action_type", "คลิกเมาส์")
            if "action_selector" in step and step["action_selector"].winfo_exists():
                step["action_selector"].set(step["action_type"])
            self.toggle_action_type(step["id"], step["action_type"])

            step["type_text"] = step_entry.get("type_text", "")
            if "text_entry" in step and step["text_entry"].winfo_exists():
                step["text_entry"].delete(0, "end")
                step["text_entry"].insert(0, step["type_text"])

            reg = step_entry.get("search_region")
            if reg:
                step["search_region"] = reg
                region_text = f"ขอบเขต: X={reg['x']} Y={reg['y']}\nขนาด: {reg['w']}x{reg['h']}"
                step["region_label"].configure(text=region_text, text_color=TEXT_COLOR)
                step["counting_region_label"].configure(text=region_text, text_color=TEXT_COLOR)
                step["ocr_region_label"].configure(text=region_text, text_color=TEXT_COLOR)

            for pt in step_entry.get("click_targets", []):
                x = pt.get("x")
                y = pt.get("y")
                delay_after = pt.get("delay_after", 0.0)
                click_count = pt.get("click_count", 1)
                click_interval = pt.get("click_interval", 0.1)
                random_offset = pt.get("random_offset", 3)
                action = pt.get("action", "click")
                type_text = pt.get("type_text", "")
                delay_before_type = pt.get("delay_before_type", 0.2)
                if x is not None and y is not None:
                    point_index = len(step["click_targets"])
                    new_pt = {
                        "x": x,
                        "y": y,
                        "delay_after": delay_after,
                        "click_count": click_count,
                        "click_interval": click_interval,
                        "random_offset": random_offset,
                        "action": action,
                        "type_text": type_text,
                        "delay_before_type": delay_before_type
                    }
                    step["click_targets"].append(new_pt)
                    if point_index == 0:
                        step["click_targets_placeholder"].pack_forget()
                    self._render_click_point_row(step, point_index)
                    
                    # Update offset entry to match loaded value
                    try:
                        row_frame_childs = step["click_targets"][-1]["_row_frame"].winfo_children()
                        # The offset entry is the CTkEntry after repick_btn
                        # We can configure it if saved value is different from default 3
                        # But since _render_click_point_row handles point.get("random_offset", 3)
                        # inside the widget creation itself, it will render correctly!
                        pass
                    except Exception:
                        pass

            for t_entry in step_entry.get("counting_targets", []):
                path = t_entry.get("path")
                if path:
                    target = {
                        "path": path,
                        "confidence": float(t_entry.get("confidence", 0.80)),
                        "last_count": 0,
                        "row_frame": None,
                        "val_lbl": None
                    }
                    step["counting_targets"].append(target)
                    idx = len(step["counting_targets"]) - 1
                    if idx == 0:
                        step["counting_placeholder_lbl"].pack_forget()
                    self._render_counting_target_row(step, idx)

            loaded_count += 1

        self.rebuild_jump_sidebars()
        self.add_log(f"[✓] โหลดการตั้งค่า {loaded_count} ขั้นตอน จาก {filename} สำเร็จ")
        messagebox.showinfo("โหลดสำเร็จ", f"โหลดเงื่อนไขทั้งหมด {loaded_count} ขั้นตอน\nจากไฟล์: {filename}")

if __name__ == "__main__":
    app = FreecameAutoApp()
    app.mainloop()
