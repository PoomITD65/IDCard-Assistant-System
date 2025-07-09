# ==============================================================================
# สคริปต์สำหรับสร้าง Path เริ่มต้นใน Firebase Realtime Database
# ==============================================================================
import firebase_admin
from firebase_admin import credentials, db

# --- 1. การตั้งค่าและเชื่อมต่อกับ Firebase ---
try:
    # กรุณาตรวจสอบให้แน่ใจว่า Path และชื่อไฟล์ Key ถูกต้อง
    SERVICE_ACCOUNT_KEY_PATH = "key/idphoto-e5a75-firebase-adminsdk-fbsvc-fd771fc15f.json"
    FIREBASE_DATABASE_URL = "https://idphoto-e5a75-default-rtdb.asia-southeast1.firebasedatabase.app/"
    
    # เริ่มต้นการเชื่อมต่อ
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred, { 'databaseURL': FIREBASE_DATABASE_URL })
    print("✅ เชื่อมต่อ Firebase สำเร็จแล้ว!")
except Exception as e:
    # กรณีที่เชื่อมต่อไม่สำเร็จ ให้แสดงข้อผิดพลาดและปิดโปรแกรม
    print(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Firebase: {e}")
    exit()

# --- 2. ส่วนหลัก: สร้าง Path ใน Database ---
if __name__ == "__main__":
    # ระบุชื่อ Path หลักที่คุณต้องการสร้าง
    path_to_create = 'account'
    
    try:
        print(f"กำลังพยายามสร้าง Path: '{path_to_create}'...")
        
        # อ้างอิงไปยัง Path ที่ต้องการ
        ref = db.reference(path_to_create)
        
        # การเขียนข้อมูลอะไรบางอย่างลงไป (แม้จะเป็น object ว่าง)
        # จะเป็นการบังคับให้ Firebase สร้าง Path นั้นขึ้นมา
        ref.set({
            '_initialized': True,
            'description': 'This path was created by the setup script.'
        })
        
        print(f"✅ สร้าง Path '{path_to_create}' ใน Realtime Database สำเร็จแล้ว!")
        print("ตอนนี้คุณสามารถไปดูใน Firebase Console ได้เลยครับ")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดระหว่างการสร้าง Path: {e}")

