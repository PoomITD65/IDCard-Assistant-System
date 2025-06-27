# ==============================================================================
# firebase_processor_service.py (เวอร์ชันจัดระเบียบใหม่)
# ==============================================================================
#
# ภาพรวมการทำงาน:
# 1. โปรแกรมนี้จะทำงานเป็น Service ที่เฝ้าดู Path `/processed_photos` ใน Firebase
# 2. เมื่อมีข้อมูลภาพดิบ (Base64) ถูกส่งเข้ามาที่ Path นี้
# 3. โปรแกรมจะดึงข้อมูลภาพนั้นมา "ประมวลผล" (ค้นหาใบหน้า, จัดองค์ประกอบ, ลบพื้นหลัง)
# 4. เมื่อประมวลผลเสร็จ จะส่งผลลัพธ์สุดท้ายไปเก็บที่ Path `/finish_photos`
# 5. จากนั้นจะลบข้อมูลภาพดิบออกจาก Path `/processed_photos` เพื่อเคลียร์คิว
#
# ==============================================================================


# --- [ส่วนที่ 1] การนำเข้า Library ที่จำเป็น (Import Libraries) ---
# ------------------------------------------------------------------------------
# เครื่องมือพื้นฐานของ Python
import os
import sys
import threading
import time
import math
import io
import base64

# Library จากภายนอกที่ต้องติดตั้งด้วย 'pip'
from PIL import Image           # สำหรับจัดการรูปภาพ (เปิด, ตัด, ปรับขนาด)
import face_recognition         # สำหรับค้นหาใบหน้าและจุดสำคัญบนใบหน้า
from rembg import remove        # สำหรับลบพื้นหลังออกจากภาพ
import firebase_admin           # สำหรับเชื่อมต่อกับ Firebase
from firebase_admin import credentials, db # เครื่องมือยืนยันตัวตนและส่วนติดต่อกับ Realtime Database


# --- [ส่วนที่ 2] การตั้งค่าและเชื่อมต่อกับ Firebase (Firebase Setup) ---
# ------------------------------------------------------------------------------
print("--- [Cloud Processor] กำลังเริ่มต้นและเชื่อมต่อกับ Firebase ---")
try:
    # --- กรุณาตรวจสอบว่าค่าเหล่านี้ถูกต้อง ---
    # ระบุตำแหน่งของไฟล์ Service Account Key
    SERVICE_ACCOUNT_KEY_PATH = ""
    # ระบุ URL ของ Realtime Database
    FIREBASE_DATABASE_URL = ""
    
    # ตั้งชื่อเฉพาะสำหรับการเชื่อมต่อนี้ เพื่อป้องกันการเชื่อมต่อซ้ำซ้อน
    app_name = 'cloud_processor'

    # ตรวจสอบว่าเคยมีการเชื่อมต่อด้วยชื่อนี้แล้วหรือยัง
    if app_name not in firebase_admin._apps:
        # ถ้ายังไม่เคย ให้สร้างการเชื่อมต่อใหม่
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL}, name=app_name)
    
    # ดึง reference ของ app ที่เราสร้างหรือเชื่อมต่อแล้ว มาเก็บไว้ในตัวแปร
    app = firebase_admin.get_app(name=app_name)

    print("✅ (Cloud Processor) เชื่อมต่อ Firebase สำเร็จแล้ว!")
except Exception as e:
    # ถ้าเชื่อมต่อไม่สำเร็จ ให้แสดงสาเหตุและปิดโปรแกรม
    print(f"❌ (Cloud Processor) เกิดข้อผิดพลาดในการเชื่อมต่อ Firebase: {e}")
    sys.exit()


# --- [ส่วนที่ 3] การตั้งค่าสำหรับการประมวลผลภาพ (Image Processing Config) ---
# ------------------------------------------------------------------------------
FINAL_IMAGE_WIDTH = 350
FINAL_IMAGE_HEIGHT = 425
NEW_BACKGROUND_COLOR = (107, 142, 232)
# สัดส่วนที่จะ Crop ภาพเทียบกับใบหน้า (ยิ่งมาก ยิ่งเห็นลำตัวเยอะ)
FRAME_TO_FACE_HEIGHT_RATIO = 3.0
# ตำแหน่งของดวงตาในแนวตั้ง (0.0 คือขอบบน, 1.0 คือขอบล่าง)
EYE_LINE_POSITION_RATIO = 0.35


# --- [ส่วนที่ 4] ฟังก์ชันหลักสำหรับประมวลผลรูปภาพ (Image Processing Function) ---
# ------------------------------------------------------------------------------
def process_image_from_base64(base64_string_with_prefix):
    """
    ฟังก์ชันนี้รับ 'ข้อมูลภาพ Base64' เข้ามาประมวลผลโดยตรง
    """
    # ขั้นตอนที่ 4.1: ถอดรหัส Base64 ให้กลับมาเป็นรูปภาพที่โปรแกรมเข้าใจ
    try:
        base64_string = base64_string_with_prefix.split(',')[1]
        image_bytes = base64.b64decode(base64_string)
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_array = face_recognition.load_image_file(io.BytesIO(image_bytes))
    except Exception as e:
        return False, f"ไม่สามารถถอดรหัส Base64 หรือเปิดภาพได้: {e}"

    # ขั้นตอนที่ 4.2: ค้นหาใบหน้าและตรวจสอบความถูกต้อง
    face_landmarks_list = face_recognition.face_landmarks(image_array)
    if not face_landmarks_list: return False, "ไม่พบใบหน้า"
    if len(face_landmarks_list) > 1: return False, f"พบ {len(face_landmarks_list)} ใบหน้า"
    
    landmarks = face_landmarks_list[0]
    
    # ขั้นตอนที่ 4.3: คำนวณและประมวลผลภาพ
    try:
        # หาขนาดและตำแหน่งของใบหน้าจาก Landmark ที่แม่นยำ
        eyebrow_pts = landmarks['left_eyebrow'] + landmarks['right_eyebrow']
        chin_pts = landmarks['chin']
        top_of_face_y, bottom_of_face_y = min(p[1] for p in eyebrow_pts), max(p[1] for p in chin_pts)
        face_height = bottom_of_face_y - top_of_face_y
        if face_height <= 0: return False, "คำนวณความสูงใบหน้าไม่ได้"
        
        # หา "จุดกึ่งกลางระหว่างดวงตา" เพื่อใช้เป็นจุดอ้างอิงหลัก
        left_eye_pts, right_eye_pts = landmarks['left_eye'], landmarks['right_eye']
        eye_center_x = sum(p[0] for p in left_eye_pts + right_eye_pts) / len(left_eye_pts + right_eye_pts)
        eye_center_y = sum(p[1] for p in left_eye_pts + right_eye_pts) / len(left_eye_pts + right_eye_pts)
        
        # คำนวณขนาดและตำแหน่งของกรอบที่จะใช้ตัดภาพ (Crop Box)
        aspect_ratio = FINAL_IMAGE_WIDTH / FINAL_IMAGE_HEIGHT
        crop_height = face_height * FRAME_TO_FACE_HEIGHT_RATIO
        crop_width = crop_height * aspect_ratio
        eye_position_in_crop = crop_height * EYE_LINE_POSITION_RATIO
        top_offset = eye_center_y - eye_position_in_crop
        left_offset = eye_center_x - (crop_width / 2)
        initial_crop_box = (int(left_offset), int(top_offset), int(left_offset + crop_width), int(top_offset + crop_height))
        
        # ทำการประมวลผลตามลำดับที่ถูกต้อง
        cropped_image = pil_image.crop(initial_crop_box)
        foreground_image = remove(cropped_image)
        new_background = Image.new("RGB", cropped_image.size, NEW_BACKGROUND_COLOR)
        new_background.paste(foreground_image, (0, 0), foreground_image)
        final_image = new_background.resize((FINAL_IMAGE_WIDTH, FINAL_IMAGE_HEIGHT), Image.LANCZOS)
        
        # ส่งคืนผลลัพธ์ว่าทำสำเร็จ พร้อมกับ Object ของภาพสุดท้าย
        return True, final_image
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดระหว่างประมวลผล: {e}"


# --- [ส่วนที่ 5] ฟังก์ชันสำหรับจัดการเมื่อมีข้อมูลเปลี่ยนแปลงใน Firebase (Listener Callback) ---
# ------------------------------------------------------------------------------
def listener_callback(event):
    """
    ฟังก์ชันนี้จะถูกเรียกโดยอัตโนมัติเมื่อมีข้อมูลใหม่ใน /processed_photos
    """
    # เราจะสนใจเฉพาะเหตุการณ์ที่มีการ "เพิ่ม" ข้อมูลใหม่ ('put') เท่านั้น
    if event.event_type == 'put' and event.path != "/" and event.data is not None:
        # ดึงรหัสนักเรียนออกมาจาก Path ที่มีการเปลี่ยนแปลง (เช่น "/11873" -> "11873")
        student_id = event.path.strip("/")
        print(f"\n[!] ตรวจพบภาพดิบใหม่ของ: {student_id} ที่ /processed_photos")

        # ดึงข้อมูล Base64 ของภาพดิบออกมาจากข้อมูลที่ได้รับ
        raw_base64_data = event.data.get('imageBase64')
        if not raw_base64_data:
            print("    -> ⚠️ ไม่พบข้อมูล imageBase64")
            return

        # ส่งภาพดิบ Base64 ไปประมวลผลในฟังก์ชันด้านบน
        print(f"    -> [▶️] กำลังส่งไปประมวลผล...")
        success, result = process_image_from_base64(raw_base64_data)

        # ตรวจสอบผลลัพธ์จากการประมวลผล
        if success:
            # ถ้าสำเร็จ จะได้ Object ของภาพที่ประมวลผลแล้วกลับมา
            processed_image = result
            print(f"    -> [✅] ประมวลผลสำเร็จ!")
            
            # เข้ารหัสภาพที่ประมวลผลแล้วกลับเป็น Base64 เพื่อส่งไปเก็บ
            buffered = io.BytesIO()
            processed_image.save(buffered, format="JPEG")
            processed_base64_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # เตรียมข้อมูลสุดท้ายเพื่อบันทึกใน Path /finish_photos
            final_data = {
                'studentId': student_id,
                'imageBase64': f"data:image/jpeg;base64,{processed_base64_string}",
                'status': 'finish',
                'finishedAt': {'.sv': 'timestamp'}
            }

            try:
                # บันทึกข้อมูลสุดท้ายไปยัง Path /finish_photos
                db.reference(f'finish_photos/{student_id}', app=app).set(final_data)
                print(f"    -> [✅] บันทึกภาพที่เสร็จแล้วไปยัง /finish_photos สำเร็จ")
                
                # ลบข้อมูลภาพดิบออกจาก Path /processed_photos (เพื่อเคลียร์คิว)
                db.reference(f'processed_photos/{student_id}', app=app).delete()
                print(f"    -> [✅] ลบภาพดิบออกจาก /processed_photos เรียบร้อย")
                print("\n======================================================")
                print("                  กำลังรอข้อมูลเพิ่มเข้ามา")
                print("======================================================")
            except Exception as e:
                print(f"    -> [❌] เกิดข้อผิดพลาดตอนบันทึก/ลบข้อมูล: {e}")
        else:
            # ถ้าประมวลผลไม่สำเร็จ จะย้ายข้อมูลไปเก็บที่ /error_photos แทน
            error_message = result
            print(f"    -> [❌] ประมวลผลไม่สำเร็จ: {error_message}")
            db.reference(f'error_photos/{student_id}', app=app).set({'error': error_message, 'at': {'.sv': 'timestamp'}})
            db.reference(f'processed_photos/{student_id}', app=app).delete()


# --- [ส่วนที่ 6] ส่วนหลักสำหรับรันโปรแกรม Service (Main Execution) ---
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # ระบุ Path ใน Firebase ที่เราต้องการเฝ้าฟัง
    path_to_listen = '/processed_photos'
    print(f"✅ เริ่มการเฝ้าดู Path '{path_to_listen}' แบบ Real-time")
    print("(กด Ctrl+C เพื่อหยุด)")

    # เพิ่มส่วนแสดงสถานะ "กำลังรอ"
    print("\n======================================================")
    print("                  กำลังรอข้อมูลเพิ่มเข้ามา")
    print("======================================================")

    try:
        # สั่งให้ Firebase เริ่มการเฝ้าฟัง (Listen) ที่ Path ที่กำหนด
        # โดยให้เรียกใช้ฟังก์ชัน listener_callback ทุกครั้งที่มีการเปลี่ยนแปลง
        firebase_admin.db.reference(path_to_listen, app=app).listen(listener_callback)
    except KeyboardInterrupt:
        # ทำให้เราสามารถกด Ctrl+C เพื่อปิดโปรแกรมได้อย่างสวยงาม
        print("\n gracefully shutting down...")
