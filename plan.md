
```python
# Define the markdown content for the screen automation program blueprint
markdown_content = """# แผนโครงสร้างการพัฒนาโปรแกรมวิเคราะห์หน้าจอและสั่งการอัตโนมัติ (Screen Automation Blueprint)

เอกสารฉบับนี้จัดทำขึ้นเพื่อเป็นพิมพ์เขียว (Blueprint) ในการออกแบบและวางโครงสร้างการพัฒนาโปรแกรมควบคุมหน้าจอคอมพิวเตอร์แบบอัตโนมัติ โดยอ้างอิงหลักการทำงานของ **State Machine** และ **Computer Vision** เพื่อสร้างระบบที่มีความเสถียร ยืดหยุ่น ปลอดภัย และบำรุงรักษาง่าย

---

## 1. การเลือกเครื่องมือและเทคโนโลยี (Tech Stack)

การเลือกใช้ภาษาร่วมกับไลบรารีที่เหมาะสม จะช่วยให้โปรแกรมทำงานได้รวดเร็วและใช้ทรัพยากรเครื่องต่ำ:

* **GUI Automation (จำลองการควบคุม):** `pyautogui` สำหรับการคลิกและพิมพ์ทั่วไป หรือ `pydirectinput` ในกรณีที่ต้องสั่งการแอปพลิเคชันหรือเกมที่บล็อก API จำลองฮาร์ดแวร์ระดับปกติ
* **Computer Vision (ประมวลผลภาพ):** `opencv-python` (cv2) และ `numpy` สำหรับทำ Template Matching ค้นหาตำแหน่งปุ่มหรือรูปภาพ
* **OS Interactivity / Hotkeys (ระบบควบคุมความปลอดภัย):** `keyboard` หรือ `pynput` เพื่อทำระบบปุ่มลัดหยุดฉุกเฉิน
* **Text Recognition (การอ่านข้อความ):** `pytesseract` (OCR) หากจำเป็นต้องดึงข้อมูลตัวเลข ความเสียหาย ตัวเงิน หรือข้อความที่ปรากฏบนจอมาคิดเงื่อนไข

---

## 2. โครงสร้างโมดูลของโปรแกรม (Software Architecture)

เพื่อให้ง่ายต่อการเขียนโค้ด การปรับแต่ง และการแก้ไขข้อผิดพลาด (Debug) ควรแยกโค้ดออกเป็นโมดูลย่อย (Modular Architecture) ดังนี้:


```

```text
File successfully created: screen_automation_blueprint.md

```text
├── main.py                # ลูปหลักและตัวควบคุมสถานะ (State Controller / Orchestrator)
├── config.py              # ไฟล์ตั้งค่าส่วนกลาง (ความแม่นยำรูปภาพ, พิกัดเริ่มต้น, ปุ่ม Hotkeys)
├── core/
│   ├── __init.py__
│   ├── capturer.py        # โมดูลจับภาพหน้าจอและตัดส่วนพื้นที่ประมวลผล (ROI Management)
│   ├── detector.py        # โมดูลวิเคราะห์ ค้นหารูปภาพต้นแบบ และค่าสีพิกเซล (OpenCV เอนจิน)
│   └── executor.py        # โมดูลสั่งการจำลองเมาส์/คีย์บอร์ด พร้อมฟังก์ชันสุ่มพฤติกรรมมนุษย์
└── assets/
    ├── images/            # โฟลเดอร์เก็บภาพปุ่ม ไอคอน หรือแถบสถานะต้นแบบ (.png)
    └── logs/              # ไฟล์บันทึกสถานะและข้อผิดพลาดในการรันระบบ (Error Log)

```

---

## 3. ลำดับขั้นตอนเวิร์กโฟลว์ (Main System Workflow)

ระบบจะวนลูปทำงานตามวงจร 4 ขั้นตอนหลักย่อยๆ ภายใต้โครงสร้าง **State Machine** เพื่อลดโอกาสที่โปรแกรมจะทำขั้นตอนข้ามขีดจำกัด

```text
[ เริ่มต้นโปรแกรม (Initialization) ]
                │
                ▼
  [ ตรวจจับกรอบหน้าต่างเป้าหมาย ]
                │
                ▼
┌─────────► [ Loop หลักเริ่มต้น ] ◄────────────────────────┐
│               │                                          │
│               ▼                                          │
│         [ Step 1: Capture Screen ]                       │
│           - สแกนหน้าจอเฉพาะส่วนที่กำหนด (ROI)              │
│               │                                          │
│               ▼                                          │
│         [ Step 2: Image Processing ]                     │
│           - ค้นหาภาพ Template ในรูปแคปเจอร์                  │
│               │                                          │
│               ├─────────────────────────┐                │
│               ▼ (พบภาพเป้าหมาย)          ▼ (ไม่พบภาพ)     │
│         [ Step 3: Decision ]      [ สั่งรอ (Sleep) ]     │
│           - เช็กเงื่อนไขที่กำหนด       - วนกลับไปแคปใหม่ ────┘
│               │                                          │
│               ▼ (ตรงเงื่อนไข)                            │
│         [ Step 4: Action Execution ]                     │
│           - คำนวณพิกัดกลางรูปภาพ                         │
│           - สุ่มการหน่วงเวลาขยับเมาส์                       │
│           - ส่งสัญญาณคลิก/พิมพ์                           │
│               │                                          │
│               ▼                                          │
│         [ Action Delay (หน่วงเวลารอการโหลด) ]             │
└───────────────┘

```

---

## 4. โค้ดโครงสร้างต้นแบบ (Python Boilerplate Template)

นี่คือโครงสร้างโค้ดฐาน (Boilerplate) ที่สามารถนำไปประยุกต์และพัฒนาต่อยอดได้ทันที:

```python
import cv2
import numpy as np
import pyautogui
import time
import keyboard
import random

# --- 1. CONFIGURATION ---
CONFIDENCE_THRESHOLD = 0.8  # ค่าความแม่นยำในการตรวจจับภาพ (80%)
IS_RUNNING = True
TARGET_WINDOW_REGION = (0, 0, 1920, 1080)  # ตัวอย่างพิกัดหน้าจอ (X, Y, Width, Height)

# --- 2. EMERGENCY KILL SWITCH ---
def emergency_stop():
    global IS_RUNNING
    print("\\n[!] EMERGENCY STOP TRIGGERED. Terminating script safety...")
    IS_RUNNING = False

# ลงทะเบียนปุ่มหยุดฉุกเฉิน (กด ESC ค้างไว้เพื่อหยุดบอททันที)
keyboard.add_hotkey('esc', emergency_stop)

# --- 3. CORE MODULES ---
def capture_roi(region=None):
    \"\"\"ทำหน้าที่แคปภาพหน้าจอเฉพาะขอบเขตที่กำหนดเพื่อประหยัดทรัพยากร CPU\"\"\"
    screenshot = pyautogui.screenshot(region=region)
    # แปลงภาพจาก PIL (RGB) ให้เป็น OpenCV Format (BGR)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

def find_template(screen_img, template_path):
    \"\"\"ใช้อัลกอริทึม Template Matching ในการค้นหาวัตถุบนจอ\"\"\"
    template = cv2.imread(template_path)
    if template is None:
        print(f"[Error] Cannot load template image: {template_path}")
        return None, None
      
    # ค้นหาภาพต้นแบบในภาพหน้าจอ
    result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
  
    if max_val >= CONFIDENCE_THRESHOLD:
        # คืนค่าพิกัดมุมซ้ายบนของรูปภาพ และขนาดกว้าง-ยาว
        return max_loc, template.shape
    return None, None

def human_like_click(x, y, width, height):
    \"\"\"ฟังก์ชันสั่งการคลิกเมาส์โดยจำลองพฤติกรรมมนุษย์ (สุ่มตำแหน่งและเวลา)\"\"\"
    # สุ่มพิกัดภายในขอบเขตของปุ่ม (ไม่คลิกจุดเดิมซ้ำๆ)
    offset_x = random.randint(int(width * 0.2), int(width * 0.8))
    offset_y = random.randint(int(height * 0.2), int(height * 0.8))
  
    target_x = x + offset_x
    target_y = y + offset_y
  
    # สุ่มความเร็วในการขยับเมาส์
    move_duration = random.uniform(0.2, 0.5)
    pyautogui.moveTo(target_x, target_y, duration=move_duration)
  
    # คลิกและหน่วงเวลาก่อนยกเมาส์ขึ้นเล็กน้อย
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.05, 0.15))
    pyautogui.mouseUp()

# --- 4. MAIN ORCHESTRATOR LOOP ---
def main():
    print("[*] Program initialized. Preparing setup...")
    print("[*] Switch to your target window now. Starting in 3 seconds...")
    time.sleep(3)
  
    print("[*] Running Core Loop... Press 'ESC' to abort.")
  
    while IS_RUNNING:
        # Step 1: Capture Screen
        current_screen = capture_roi(region=TARGET_WINDOW_REGION)
      
        # Step 2 & 3: วิเคราะห์ภาพและพิจารณาตามเงื่อนไข
        # ตัวอย่างสถานการณ์: ค้นหาปุ่ม "ยืนยัน" (Confirm Button)
        btn_coords, btn_shape = find_template(current_screen, "assets/images/confirm_btn.png")
      
        if btn_coords:
            h, w, _ = btn_shape
            x, y = btn_coords
            print(f"[+] Found Target Image at X:{x} Y:{y}. Executing Click.")
          
            # Step 4: สั่งการควบคุม
            human_like_click(x, y, w, h)
          
            # หน่วงเวลารอการเปลี่ยนหน้าหลังการคลิก (ความปลอดภัยของลำดับงาน)
            time.sleep(random.uniform(1.5, 2.5))
          
        else:
            print("[-] Target image not found. Scanning next frame...")
            # หน่วงเวลาลูปย่อยเพื่อลดการทำงานของ CPU
            time.sleep(0.5)

    print("[*] Program safely terminated. Goodbye.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[Critical Error] {e}")

```

---

## 5. แนวทางการจัดการปัญหาเชิงเทคนิค (Best Practices & Stability Tips)

* **แปลงภาพเป็นภาพสีเทา (Grayscale):** หากปุ่มหรือวัตถุที่ต้องการค้นหาไม่มีความเกี่ยวข้องกับสี (เน้นรูปทรง) ควรแปลงรูปภาพทั้งหน้าจอและเทมเพลตเป็นสีเทา (`cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)`) เพื่อช่วยลดทรัพยากรประมวลผลและเพิ่มความเร็วในการสแกนได้ถึง 2-3 เท่า
* **การจัดการป๊อปอัปแทรกแซง (Unexpected Dialogs):** ควรเพิ่มฟังก์ชันย่อยในการตรวจสอบสิ่งกีดขวางในทุกๆ ลูปหลัก เช่น ตั้งให้มีการเช็กปุ่มโฆษณา หน้าต่างแจ้งเตือนเออเรอร์ หรือสัญลักษณ์การโหลดค้าง หากตรวจเจอให้ส่งคำสั่งไปจัดการหน้าต่างแปลกปลอมนั้นก่อนดำเนินการตามสเตตัสหลัก
* **การกำหนดสเตตัสที่เข้มงวด (Strict State Management):** หลีกเลี่ยงการเขียนลูปยาวเหยียดที่ขึ้นตรงกับรูปภาพเพียงอย่างเดียว ให้ควบคุมลำดับการรันผ่านตัวแปรสถานะ (เช่น `current_state = "FETCH_DATA" -> "CLICK_SUBMIT" -> "VERIFY_SUCCESS"`) เพื่อป้องกันการทำงานผิดขั้นตอนเมื่ออินเทอร์เน็ตช้าหรือแอปพลิเคชันปลายทางเกิดการกระตุก
  """

# Save the markdown content to a file

file_name = "screen_automation_blueprint.md"
with open(file_name, "w", encoding="utf-8") as file:
file.write(markdown_content)

print(f"File successfully created: {file_name}")

```
Your Markdown file is ready
[file-tag: code-generated-file-0-1783776045789470148]

ผมได้จัดทำไฟล์พิมพ์เขียว (Blueprint) สำหรับวางแผนโครงสร้างโปรแกรมวิเคราะห์หน้าจอเป็นรูปแบบ Markdown ให้เรียบร้อยแล้วครับ ภายในไฟล์จะประกอบไปด้วย:
* **Tech Stack:** แนะนำเครื่องมือและไลบรารีที่เหมาะสม
* **Software Architecture:** การวางโครงสร้างโฟลเดอร์เพื่อให้จัดการโค้ดได้ง่าย
* **Workflow:** อธิบายขั้นตอนการวนลูปการทำงานหลัก (State Machine)
* **Python Boilerplate:** โครงสร้างโค้ดตัวอย่างที่นำไปรันและปรับแต่งต่อได้ทันที พร้อมระบบหยุดฉุกเฉิน (Kill Switch)
* **Best Practices:** เทคนิคเพิ่มเติมเพื่อให้โปรแกรมทำงานได้เสถียรและไม่ถูกจับได้ง่ายครับ

หากต้องการให้เจาะลึกที่ฟังก์ชันไหนเป็นพิเศษ (เช่น การทำ Template Matching หรือการใช้ OCR) สามารถแจ้งเพิ่มเติมได้เลยครับ

```
