# ==============================================================================
# logger_polling.py (เวอร์ชันบันทึก Log เป็น .csv)
# ==============================================================================
import firebase_admin
from firebase_admin import credentials, db
import sys
import os
import json
import time
from datetime import datetime
import csv # <--- เพิ่ม Library สำหรับจัดการไฟล์ CSV

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

# --- [แก้ไข] ส่วนที่ 2: ฟังก์ชันสำหรับบันทึก Log ลงไฟล์ .csv ---
LOG_FILE_PATH = "activity_log.csv"

def write_log_to_csv(event_type, full_path, data_preview=""):
    """
    ฟังก์ชันสำหรับเขียนข้อมูล Log ลงในไฟล์ .csv
    """
    try:
        # ตรวจสอบว่าไฟล์ Log มีอยู่แล้วหรือยัง เพื่อตัดสินใจว่าจะเขียน Header หรือไม่
        file_exists = os.path.exists(LOG_FILE_PATH)
        
        # เปิดไฟล์ในโหมด 'a' (append) และใช้ newline='' เพื่อป้องกันบรรทัดว่างใน Windows
        with open(LOG_FILE_PATH, "a", encoding="utf-8", newline='') as f:
            # สร้าง writer object
            writer = csv.writer(f)
            
            # ถ้าเป็นไฟล์ใหม่ ให้เขียน Header ก่อน
            if not file_exists:
                writer.writerow(["Timestamp", "EventType", "Path", "DataPreview"])
            
            # รูปแบบเวลา: YYYY-MM-DD HH:MM:SS
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # เขียนข้อมูลแถวใหม่
            writer.writerow([timestamp, event_type, full_path, data_preview])

    except Exception as e:
        print(f"\n[ERROR] ไม่สามารถเขียน Log ลงไฟล์ CSV ได้: {e}")

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
            full_path = f"{watched_path.rstrip('/')}/{key}"
            event_type = "ADD/OVERWRITE"
            
            # แสดง Log ใน Terminal
            print(f"\n------------------- [ตรวจพบ: {event_type}] -------------------")
            print(f"  Path: {full_path}")
            
            data = current_state[key]
            data_preview = ""
            if isinstance(data, dict):
                preview_data = data.copy()
                if 'imageBase64' in preview_data:
                    preview_data['imageBase64'] = preview_data['imageBase64'][:50] + '...'
                data_preview = json.dumps(preview_data)
                print(f"  Data: {json.dumps(preview_data, indent=2)}")
            else:
                data_preview = str(data)
                print(f"  Data: {data_preview}")
            print("-------------------------------------------------------------")
            
            # [แก้ไข] บันทึก Log ลงไฟล์ .csv
            write_log_to_csv(event_type, full_path, data_preview)

    # --- ตรวจสอบการลบ ---
    for key in old_keys:
        if key not in new_keys:
            change_detected = True
            full_path = f"{watched_path.rstrip('/')}/{key}"
            event_type = "DELETE"
            
            # แสดง Log ใน Terminal
            print(f"\n------------------- [ตรวจพบ: {event_type}] -------------------")
            print(f"  Path: {full_path}")
            print("-------------------------------------------------------------")

            # [แก้ไข] บันทึก Log ลงไฟล์ .csv
            write_log_to_csv(event_type, full_path)
    
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
                print("              กำลังรอข้อมูลใหม่เข้ามา")
                print("======================================================")
            else:
                sys.stdout.write(f"\rไม่มีการเคลื่อนไหวของข้อมูล, กำลังตรวจสอบรอบต่อไป{'.' * (int(time.time()) % 4)}")
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n gracefully shutting down...")
    except Exception as e:
        print(f"❌ Logger เกิดข้อผิดพลาดร้ายแรง: {e}")
