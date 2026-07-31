# -*- coding: utf-8 -*-
"""
สร้าง Desktop Shortcut สำหรับ Freecame Auto Clicker
รันครั้งเดียว จากนั้นลบไฟล์นี้ได้เลย
"""
import sys
import io
# Force UTF-8 stdout to handle Thai paths
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import win32com.client
import winreg
import os

# --- หา Desktop path จริงจาก Registry (รองรับ OneDrive / ชื่อภาษาไทย) ---
def get_desktop_path():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        )
        desktop, _ = winreg.QueryValueEx(key, 'Desktop')
        winreg.CloseKey(key)
        return desktop
    except Exception:
        return os.path.join(os.environ['USERPROFILE'], 'Desktop')

# --- Paths ---
script_path   = os.path.abspath(r'c:\ProjectFreecameAuto\Boilerplate.py')
python_exe    = sys.executable
desktop       = get_desktop_path()
shortcut_path = os.path.join(desktop, 'Freecame Auto.lnk')
ico_path      = os.path.join(os.path.dirname(script_path), 'app_icon.ico')

print(f"Desktop path: {desktop}")
print(f"Desktop exists: {os.path.isdir(desktop)}")

# --- ตรวจสอบว่าโฟลเดอร์ Desktop มีอยู่จริง ---
if not os.path.isdir(desktop):
    print("[Error] ไม่พบโฟลเดอร์ Desktop ที่อ่านจาก Registry")
    sys.exit(1)

# --- แปลงรูปไอคอน PNG เป็น ICO ---
try:
    from PIL import Image
    png_path = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\113e6628-ed43-44fe-9553-3daa21fcabd7\freecame_auto_icon_1784279752441.png"
    if os.path.exists(png_path):
        img = Image.open(png_path)
        img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print(f"[OK] แปลงไฟล์ไอคอนสำเร็จ → {ico_path}")
    else:
        print("[Warning] ไม่พบไฟล์ PNG ต้นฉบับสำหรับแปลงไอคอน")
except Exception as e:
    print(f"[Warning] ไม่สามารถแปลงไฟล์ไอคอนได้: {e}")

# --- สร้าง .lnk Shortcut ---
shell    = win32com.client.Dispatch('WScript.Shell')
shortcut = shell.CreateShortcut(shortcut_path)

shortcut.TargetPath       = python_exe
shortcut.Arguments        = f'"{script_path}"'
shortcut.WorkingDirectory = os.path.dirname(script_path)
shortcut.Description      = 'Freecame Auto Clicker - Multi-Step Bot'
if os.path.exists(ico_path):
    shortcut.IconLocation = ico_path
else:
    shortcut.IconLocation = python_exe + ',0'
shortcut.WindowStyle      = 1  # Normal window
shortcut.Save()

print(f"[OK] สร้าง Shortcut สำเร็จ!")
print(f"     ไฟล์ : {shortcut_path}")
print(f"     Target: {python_exe}")
print(f"     Args  : \"{script_path}\"")
