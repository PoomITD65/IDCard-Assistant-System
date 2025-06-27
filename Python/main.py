# ==============================================================================
# main.py (FastAPI Data Viewer)
# ทำหน้าที่: สร้าง API สำหรับเรียกดูข้อมูลภาพที่ประมวลผลเสร็จแล้วจาก Firebase
# ==============================================================================

# --- ส่วนที่ 1: การนำเข้า Library ที่จำเป็น ---
import os
import sys
from contextlib import asynccontextmanager

# Library จากภายนอก
from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, db

# ==============================================================================
# ส่วนที่ 2: การตั้งค่าและฟังก์ชันสำหรับเชื่อมต่อ Firebase
# ==============================================================================
# --- กรุณาตรวจสอบว่าค่าเหล่านี้ถูกต้อง ---
SERVICE_ACCOUNT_KEY_PATH = "key/idphoto-e5a75-firebase-adminsdk-fbsvc-d0a07f9bab.json"
FIREBASE_DATABASE_URL = "https://idphoto-e5a75-default-rtdb.asia-southeast1.firebasedatabase.app/"
app_name = 'fastapi_viewer' # ตั้งชื่อ app ให้ไม่ซ้ำกับ service อื่น

# Lifespan manager: โค้ดส่วนนี้จะทำงานแค่ครั้งเดียวตอนที่ FastAPI เริ่มและหยุดทำงาน
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- โค้ดที่จะทำงานตอน "เริ่ม" server ---
    print("--- [FastAPI Viewer] กำลังเริ่มต้นและเชื่อมต่อกับ Firebase ---")
    try:
        if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
            raise FileNotFoundError(f"ไม่พบไฟล์ Service Account Key ที่ {SERVICE_ACCOUNT_KEY_PATH}")

        if app_name not in firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL}, name=app_name)
        
        print("✅ (FastAPI Viewer) เชื่อมต่อ Firebase สำเร็จแล้ว!")
    except Exception as e:
        print(f"❌ (FastAPI Viewer) เกิดข้อผิดพลาดร้ายแรงในการเชื่อมต่อ Firebase: {e}")
    
    yield # เริ่มการทำงานของแอปพลิเคชัน

    # --- โค้ดที่จะทำงานตอน "หยุด" server (ถ้ามี) ---
    print("--- [FastAPI Viewer] กำลังปิดการทำงาน... ---")

# สร้าง FastAPI app และกำหนด lifespan manager
app = FastAPI(lifespan=lifespan)

# ==============================================================================
# ส่วนที่ 3: API Endpoint สำหรับเรียกดูข้อมูล
# ==============================================================================
@app.get("/get-finished-image/{student_id}")
async def get_image_data(student_id: str):
    """
    API Endpoint นี้จะรับรหัสนักเรียนเข้ามา แล้วไปดึงข้อมูลจาก Path 'finish_photos'
    ใน Firebase Realtime Database
    """
    try:
        # ดึง reference ของ app ที่เราสร้างขึ้นมาเพื่อใช้ในการอ้างอิง
        current_app = firebase_admin.get_app(name=app_name)
        
        # อ้างอิงไปยัง Path ของข้อมูลที่ต้องการ
        ref = db.reference(f'finish_photos/{student_id}', app=current_app)
        
        # ดึงข้อมูล
        data = ref.get()
        
        # ตรวจสอบว่ามีข้อมูลหรือไม่
        if data:
            # ถ้ามี ให้ส่งข้อมูลนั้นกลับไป
            return data
        else:
            # ถ้าไม่มี ให้แจ้งกลับไปว่าไม่พบข้อมูล (404 Not Found)
            raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูลสำหรับรหัสนักเรียน: {student_id}")

    except Exception as e:
        # กรณีที่เกิดข้อผิดพลาดอื่นๆ ในฝั่งเซิร์ฟเวอร์
        raise HTTPException(status_code=500, detail=str(e))

