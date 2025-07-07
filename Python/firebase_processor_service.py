# ==============================================================================
# firebase_processor_service.py (เวอร์ชันใช้ remove.bg API)
# ทำหน้าที่: เฝ้าดู Path /processed_photos ใน Firebase, เมื่อมีภาพใหม่เข้ามา
#           จะดึงมาประมวลผลด้วย remove.bg API แล้วส่งไปเก็บที่ /finish_photos
# ==============================================================================

# --- ส่วนที่ 1: การนำเข้า Library ที่จำเป็น ---
import os
import sys
import threading
import time
import math
import io
import base64
import requests # <--- เพิ่ม Library สำหรับส่ง API request

from PIL import Image
import face_recognition
# from rembg import remove # <--- ไม่ใช้ rembg แล้ว
import firebase_admin
from firebase_admin import credentials, db

# ==============================================================================
# ส่วนที่ 2: การตั้งค่าและเชื่อมต่อกับ Firebase
# ==============================================================================
print("--- [Cloud Processor] กำลังเริ่มต้นและเชื่อมต่อกับ Firebase ---")
try:
    # --- ค่าการเชื่อมต่อที่ถูกต้อง ---
    SERVICE_ACCOUNT_KEY_PATH = "key/idphoto-e5a75-firebase-adminsdk-fbsvc-fd771fc15f.json"
    FIREBASE_DATABASE_URL = "https://idphoto-e5a75-default-rtdb.asia-southeast1.firebasedatabase.app/"
    
    app_name = 'cloud_processor'
    if app_name not in firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL}, name=app_name)
    
    app = firebase_admin.get_app(name=app_name)
    print("✅ (Cloud Processor) เชื่อมต่อ Firebase สำเร็จแล้ว!")
except Exception as e:
    print(f"❌ (Cloud Processor) เกิดข้อผิดพลาดในการเชื่อมต่อ Firebase: {e}")
    sys.exit()

# ==============================================================================
# ส่วนที่ 3: การตั้งค่าสำหรับการประมวลผลภาพ
# ==============================================================================
# --- [สำคัญ] ใส่ API Key ของคุณเรียบร้อยแล้ว ---
REMOVE_BG_API_KEY = "pqu1NRMuig7fvvePphcoWqn5"

FINAL_IMAGE_WIDTH = 350
FINAL_IMAGE_HEIGHT = 425
NEW_BACKGROUND_COLOR = "6b8ee8" # ใช้เป็นรหัสสี HEX สำหรับ API
FRAME_TO_FACE_HEIGHT_RATIO = 3.0
EYE_LINE_POSITION_RATIO = 0.35

# ==============================================================================
# ส่วนที่ 4: ฟังก์ชันหลักสำหรับประมวลผลรูปภาพ
# ==============================================================================
def process_image_from_base64(base64_string_with_prefix):
    """
    ฟังก์ชันนี้จะรับ 'ข้อมูลภาพ Base64' เข้ามาประมวลผลโดยตรง
    """
    try:
        base64_string = base64_string_with_prefix.split(',')[1]
        image_bytes = base64.b64decode(base64_string)
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_array = face_recognition.load_image_file(io.BytesIO(image_bytes))
    except Exception as e:
        return False, f"ไม่สามารถถอดรหัส Base64 หรือเปิดภาพได้: {e}"

    face_landmarks_list = face_recognition.face_landmarks(image_array)
    if not face_landmarks_list: return False, "ไม่พบใบหน้า"
    if len(face_landmarks_list) > 1: return False, f"พบ {len(face_landmarks_list)} ใบหน้า"
    
    landmarks = face_landmarks_list[0]
    try:
        eyebrow_pts = landmarks['left_eyebrow'] + landmarks['right_eyebrow']
        chin_pts = landmarks['chin']
        top_of_face_y, bottom_of_face_y = min(p[1] for p in eyebrow_pts), max(p[1] for p in chin_pts)
        face_height = bottom_of_face_y - top_of_face_y
        if face_height <= 0: return False, "คำนวณความสูงใบหน้าไม่ได้"
        
        left_eye_pts, right_eye_pts = landmarks['left_eye'], landmarks['right_eye']
        eye_center_x = sum(p[0] for p in left_eye_pts + right_eye_pts) / len(left_eye_pts + right_eye_pts)
        eye_center_y = sum(p[1] for p in left_eye_pts + right_eye_pts) / len(left_eye_pts + right_eye_pts)
        
        aspect_ratio = FINAL_IMAGE_WIDTH / FINAL_IMAGE_HEIGHT
        crop_height = face_height * FRAME_TO_FACE_HEIGHT_RATIO
        crop_width = crop_height * aspect_ratio
        eye_position_in_crop = crop_height * EYE_LINE_POSITION_RATIO
        top_offset = eye_center_y - eye_position_in_crop
        left_offset = eye_center_x - (crop_width / 2)
        initial_crop_box = (int(left_offset), int(top_offset), int(left_offset + crop_width), int(top_offset + crop_height))
        
        cropped_image = pil_image.crop(initial_crop_box)
        
        # --- เปลี่ยนมาเรียกใช้ remove.bg API ---
        # 1. แปลงภาพที่ Crop แล้วกลับเป็น Bytes เพื่อส่ง
        buffered = io.BytesIO()
        cropped_image.save(buffered, format="PNG") # ส่งเป็น PNG เพื่อคุณภาพที่ดีที่สุด
        image_to_send_bytes = buffered.getvalue()

        # 2. ส่ง Request ไปที่ remove.bg API
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': image_to_send_bytes},
            data={
                'size': 'auto',
                'bg_color': NEW_BACKGROUND_COLOR, # ส่งรหัสสี HEX ไปได้เลย
                'format': 'jpg'
            },
            headers={'X-Api-Key': REMOVE_BG_API_KEY},
        )
        
        # 3. ตรวจสอบผลลัพธ์
        if response.status_code == requests.codes.ok:
            # ถ้าสำเร็จ API จะส่งข้อมูลภาพที่ทำเสร็จแล้วกลับมา
            # เราจะเปิดภาพนั้นด้วย Pillow แล้ว Resize เป็นขั้นตอนสุดท้าย
            final_image_from_api = Image.open(io.BytesIO(response.content))
            final_image = final_image_from_api.resize((FINAL_IMAGE_WIDTH, FINAL_IMAGE_HEIGHT), Image.LANCZOS)
            return True, final_image
        else:
            # ถ้าไม่สำเร็จ ให้ส่งข้อความ Error กลับไป
            return False, f"Remove.bg API Error: {response.status_code} {response.text}"

    except Exception as e:
        return False, f"เกิดข้อผิดพลาดระหว่างประมวลผล: {e}"

# ==============================================================================
# ส่วนที่ 5: ฟังก์ชันสำหรับจัดการเมื่อมีข้อมูลเปลี่ยนแปลงใน Firebase
# ==============================================================================
def listener_callback(event):
    if event.event_type == 'put' and event.path != "/" and event.data is not None:
        student_id = event.path.strip("/")
        print(f"\n[!] ตรวจพบภาพดิบใหม่ของ: {student_id} ที่ /processed_photos")

        raw_base64_data = event.data.get('imageBase64')
        if not raw_base64_data:
            print("    -> ⚠️ ไม่พบข้อมูล imageBase64")
            return

        print(f"    -> [▶️] กำลังส่งไปประมวลผลด้วย remove.bg API...")
        success, result = process_image_from_base64(raw_base64_data)

        if success:
            processed_image = result
            print(f"    -> [✅] ประมวลผลสำเร็จ!")
            
            buffered = io.BytesIO()
            processed_image.save(buffered, format="JPEG")
            processed_base64_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

            final_data = {
                'studentId': student_id,
                'imageBase64': f"data:image/jpeg;base64,{processed_base64_string}",
                'status': 'finish',
                'finishedAt': {'.sv': 'timestamp'}
            }

            try:
                db.reference(f'finish_photos/{student_id}', app=app).set(final_data)
                print(f"    -> [✅] บันทึกภาพที่เสร็จแล้วไปยัง /finish_photos สำเร็จ")
                
                db.reference(f'processed_photos/{student_id}', app=app).delete()
                print(f"    -> [✅] ลบภาพดิบออกจาก /processed_photos เรียบร้อย")
                print("\n======================================================")
                print("                  กำลังรอข้อมูลเพิ่มเข้ามา")
                print("======================================================")
            except Exception as e:
                print(f"    -> [❌] เกิดข้อผิดพลาดตอนบันทึก/ลบข้อมูล: {e}")
        else:
            error_message = result
            print(f"    -> [❌] ประมวลผลไม่สำเร็จ: {error_message}")
            db.reference(f'error_photos/{student_id}', app=app).set({'error': error_message, 'at': {'.sv': 'timestamp'}})
            db.reference(f'processed_photos/{student_id}', app=app).delete()

# ==============================================================================
# ส่วนที่ 6: ส่วนหลักสำหรับรันโปรแกรม Service
# ==============================================================================
if __name__ == "__main__":
    if REMOVE_BG_API_KEY == "YOUR_REMOVE_BG_API_KEY":
        print("❌ กรุณาใส่ API Key ของ remove.bg ในส่วน Configuration ก่อนรันโปรแกรม")
        sys.exit()

    path_to_listen = '/processed_photos'
    print(f"✅ เริ่มการเฝ้าดู Path '{path_to_listen}' แบบ Real-time")
    print("(กด Ctrl+C เพื่อหยุด)")
    print("\n======================================================")
    print("                  กำลังรอข้อมูลเพิ่มเข้ามา")
    print("======================================================")
    try:
        firebase_admin.db.reference(path_to_listen, app=app).listen(listener_callback)
    except KeyboardInterrupt:
        print("\n gracefully shutting down...")
