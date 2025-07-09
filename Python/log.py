# ==============================================================================
# logger_polling.py (เวอร์ชันเฝ้าดู 3 Path และบันทึก Log เป็น .txt)
# ==============================================================================
import firebase_admin
from firebase_admin import credentials, db
import sys
import os
import json
import time
from datetime import datetime # <--- เพิ่ม Library สำหรับจัดการเวลา

# --- 1. การตั้งค่าและเชื่อมต่อกับ Firebase (แบบ Default) ---
print("--- [Polling Logger] กำลังเริ่มต้นและเชื่อมต่อกับ Firebase ---")
try:
    SERVICE_ACCOUNT_KEY_PATH = "key/idphoto-e5a75-firebase-adminsdk-fbsvc-fd771fc15f.json"
    FIREBASE_DATABASE_URL = "https://idphoto-e5a75-default-rtdb.asia-southeast1.firebasedatabase.app/"
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
    
    print("✅ (Polling Logger) เชื่อมต่อ Firebase สำเร็จแล้ว!")
except Exception as e:
    print(f"❌ (Polling Logger) เกิดข้อผิดพลาดในการเชื่อมต่อ Firebase: {e}")
    sys.exit()

# --- [ใหม่] ส่วนที่ 2: ฟังก์ชันสำหรับบันทึก Log ลงไฟล์ .txt ---
LOG_FILE_PATH = "activity_log.txt"

def write_log_to_file(log_message):
    """
    ฟังก์ชันสำหรับเขียนข้อความ Log พร้อมประทับเวลาลงในไฟล์ .txt
    """
    try:
        # เปิดไฟล์ในโหมด 'a' (append) เพื่อเขียนข้อมูลต่อท้ายไฟล์เดิม
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            # รูปแบบเวลา: YYYY-MM-DD HH:MM:SS
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {log_message}\n")
    except Exception as e:
        # แสดงข้อผิดพลาดหากไม่สามารถเขียนไฟล์ได้ แต่โปรแกรมยังทำงานต่อ
        print(f"\n[ERROR] ไม่สามารถเขียน Log ลงไฟล์ได้: {e}")

# --- ส่วนที่ 3: ฟังก์ชันสำหรับเปรียบเทียบและแสดง Log ---
def compare_and_log_changes(previous_state, current_state, watched_path):
    """
    ฟังก์ชันนี้จะเปรียบเทียบข้อมูลสองชุด (เก่ากับใหม่) เพื่อหาการเปลี่ยนแปลง
    และจะ return True หากมีการเปลี่ยนแปลงเกิดขึ้น
    """
    change_detected = False
    old_keys = set(previous_state.keys()) if previous_state else set()
    new_keys = set(current_state.keys()) if current_state else set()

    # --- ตรวจสอบการเพิ่มหรือเขียนทับ ---
    for key in new_keys:
        if key not in old_keys or previous_state[key] != current_state[key]:
            change_detected = True
            # แสดง Log ใน Terminal
            print("\n------------------- [ตรวจพบความเคลื่อนไหว!] -------------------")
            print(f"  ประเภทเหตุการณ์           : [ข้อมูลถูกเพิ่ม หรือ เขียนทับ] (ADD / OVERWRITE)")
            full_path = f"{watched_path.rstrip('/')}/{key}"
            print(f"  ตำแหน่งที่เกิด (Path)      : {full_path}")
            
            data = current_state[key]
            if isinstance(data, dict):
                preview_data = data.copy()
                if 'imageBase64' in preview_data:
                    preview_data['imageBase64'] = preview_data['imageBase64'][:50] + '...'
                print(f"  ข้อมูล (Data)             : {json.dumps(preview_data, indent=2)}")
            else:
                print(f"  ข้อมูล (Data)             : {data}")
            print("-------------------------------------------------------------")
            
            # [ใหม่] บันทึก Log ลงไฟล์ .txt
            log_message = f"EVENT: ADD/OVERWRITE | PATH: {full_path}"
            write_log_to_file(log_message)

    # --- ตรวจสอบการลบ ---
    for key in old_keys:
        if key not in new_keys:
            change_detected = True
            # แสดง Log ใน Terminal
            print("\n------------------- [ตรวจพบความเคลื่อนไหว!] -------------------")
            print(f"  ประเภทเหตุการณ์           : [ข้อมูลถูกลบ] (DELETE)")
            full_path = f"{watched_path.rstrip('/')}/{key}"
            print(f"  ตำแหน่งที่เกิด (Path)      : {full_path}")
            print("-------------------------------------------------------------")

            # [ใหม่] บันทึก Log ลงไฟล์ .txt
            log_message = f"EVENT: DELETE | PATH: {full_path}"
            write_log_to_file(log_message)
    
    return change_detected

# --- ส่วนที่ 4: ส่วนหลักสำหรับรันโปรแกรม Service ---
if __name__ == "__main__":
    paths_to_watch = ['/processed_photos', '/finish_photos', '/error_photos', '/account']

    print(f"\n✅ เริ่มการตรวจสอบ {len(paths_to_watch)} Path ทุกๆ 5 วินาที")
    print(f"✅ Log ทั้งหมดจะถูกบันทึกที่ไฟล์: '{LOG_FILE_PATH}'")
    for p in paths_to_watch:
        print(f"   - {p}")
    print("(กด Ctrl+C เพื่อหยุด)")

    previous_states = {}
    
    print("\nกำลังดึงข้อมูลสถานะเริ่มต้น...")
    for path in paths_to_watch:
        previous_states[path] = db.reference(path).get() or {}
    print("ดึงข้อมูลเริ่มต้นสำเร็จ!")

    try:
        while True:
            time.sleep(5)
            any_changes_this_cycle = False

            for path in paths_to_watch:
                current_state = db.reference(path).get() or {}
                if compare_and_log_changes(previous_states[path], current_state, path):
                    any_changes_this_cycle = True
                previous_states[path] = current_state
            
            if any_changes_this_cycle:
                print("\n======================================================")
                print("              กำลังรอข้อมูลเคลื่อไหว")
                print("======================================================")
            else:
                sys.stdout.write(f"\rไม่มีการเคลื่อนไหวของข้อมูล, กำลังตรวจสอบรอบต่อไป{'.' * (int(time.time()) % 4)}")
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n gracefully shutting down...")
    except Exception as e:
        print(f"❌ Logger เกิดข้อผิดพลาดร้ายแรง: {e}")
