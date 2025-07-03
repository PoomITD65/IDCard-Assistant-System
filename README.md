Firebase Realtime Image Processor Serviceสคริปต์นี้ทำงานเป็น Service เบื้องหลัง (Background Service) ที่คอยเฝ้าดูและประมวลผลรูปภาพที่ถูกส่งเข้ามายัง Firebase Realtime Database โดยอัตโนมัติภาพรวมการทำงานเฝ้าดู (Listen): โปรแกรมจะเชื่อมต่อกับ Firebase และเฝ้าดู Path /processed_photos ตลอดเวลารับข้อมูล: เมื่อมีข้อมูลภาพใหม่ (ในรูปแบบ Base64) ถูกเพิ่มเข้ามาที่ Path ดังกล่าว โปรแกรมจะเริ่มทำงานทันทีประมวลผล (Process):ค้นหาใบหน้าและจุดสำคัญบนใบหน้า (Face Landmarks) ด้วย face_recognitionคำนวณเพื่อจัดองค์ประกอบภาพให้อยู่ในตำแหน่งที่เหมาะสม (Auto-cropping)ลบพื้นหลังออกจากรูปภาพด้วย rembgเติมพื้นหลังใหม่ (สีน้ำเงินตามที่ตั้งค่าไว้)ปรับขนาดภาพให้เป็นขนาดสุดท้ายที่ต้องการ (350x425 pixels)ส่งผลลัพธ์:หากสำเร็จ: ภาพสุดท้ายจะถูกบันทึกไปที่ Path /finish_photosหากล้มเหลว: ข้อมูลข้อผิดพลาด (เช่น ไม่พบใบหน้า, พบมากกว่า 1 ใบหน้า) จะถูกบันทึกไปที่ Path /error_photosเคลียร์คิว: หลังจากประมวลผลเสร็จ (ไม่ว่าจะสำเร็จหรือล้มเหลว) ข้อมูลภาพดิบจาก /processed_photos จะถูกลบออกไป เพื่อเตรียมรอรับงานถัดไปวิธีการติดตั้งและใช้งาน1. ข้อกำหนดเบื้องต้น (Prerequisites)Python 3.7+บัญชี Firebase พร้อมกับเปิดใช้งาน Realtime Database2. การติดตั้งขั้นตอนที่ 1: สร้างและเปิดใช้งาน Virtual Environment (แนะนำ)เพื่อป้องกันปัญหาเรื่องเวอร์ชันของไลบรารี ควรสร้างสภาพแวดล้อมเสมือนสำหรับโปรเจกต์นี้# สร้าง virtual environment ชื่อ 'venv'
python -m venv venv

# เปิดใช้งาน (Activate)
# บน Windows:
venv\Scripts\activate

# บน macOS/Linux:
source venv/bin/activate
ขั้นตอนที่ 2: ติดตั้ง Dependenciesสร้างไฟล์ชื่อ requirements.txt แล้วคัดลอกเนื้อหาข้างล่างนี้ไปใส่:Pillow
face_recognition
rembg
firebase-admin
จากนั้นรันคำสั่งติดตั้งผ่าน pip:pip install -r requirements.txt
หมายเหตุ: การติดตั้ง dlib (ซึ่งเป็นส่วนหนึ่งของ face_recognition) อาจใช้เวลานานและอาจต้องการ CMake และ C++ compiler ในระบบของคุณ3. การตั้งค่า (Configuration)ขั้นตอนที่ 1: ดาวน์โหลด Firebase Service Account Keyไปที่ Firebase Console ของโปรเจกต์คุณคลิกที่ไอคอนรูปเฟือง (ข้างๆ Project Overview) > Project settingsไปที่แท็บ Service accountsคลิกที่ปุ่ม Generate new private key แล้วบันทึกไฟล์ .json ที่ได้มาลงในโปรเจกต์ (เช่น ในโฟลเดอร์ชื่อ key/)ขั้นตอนที่ 2: แก้ไขค่าในสคริปต์เปิดไฟล์ firebase_processor_service.py และแก้ไขค่าใน ส่วนที่ 2 (Firebase Setup):SERVICE_ACCOUNT_KEY_PATH: แก้ไขเป็นตำแหน่งที่ถูกต้องของไฟล์ .json ที่คุณดาวน์โหลดมาSERVICE_ACCOUNT_KEY_PATH = "key/your-service-account-file.json"
FIREBASE_DATABASE_URL: คัดลอก URL ของ Realtime Database ของคุณมาใส่ (ดูได้จากหน้า Realtime Database ใน Firebase Console)FIREBASE_DATABASE_URL = "[https://your-project-id-default-rtdb.firebaseio.com/](https://your-project-id-default-rtdb.firebaseio.com/)"
4. การรัน Serviceเมื่อตั้งค่าทุกอย่างเรียบร้อยแล้ว ให้รันสคริปต์จาก Terminal หรือ Command Prompt:python firebase_processor_service.py
หากสำเร็จ โปรแกรมจะแสดงข้อความว่าเชื่อมต่อ Firebase สำเร็จ และเข้าสู่สถานะ "กำลังรอข้อมูลเพิ่มเข้ามา" ซึ่งหมายความว่า Service ของคุณพร้อมทำงานแล้ว--- [Cloud Processor] กำลังเริ่มต้นและเชื่อมต่อกับ Firebase ---
✅ (Cloud Processor) เชื่อมต่อ Firebase สำเร็จแล้ว!
✅ เริ่มการเฝ้าดู Path '/processed_photos' แบบ Real-time
(กด Ctrl+C เพื่อหยุด)

======================================================
                             กำลังรอข้อมูลเพิ่มเข้ามา
======================================================
5. การปรับแต่งค่าการประมวลผลคุณสามารถปรับแต่งพารามิเตอร์ต่างๆ ในการประมวลผลภาพได้ใน ส่วนที่ 3 (Image Processing Config) ของสคริปต์:FINAL_IMAGE_WIDTH, FINAL_IMAGE_HEIGHT: ขนาดของภาพสุดท้าย (หน่วยเป็น pixel)NEW_BACKGROUND_COLOR: สีพื้นหลังใหม่ (ในรูปแบบ RGB)FRAME_TO_FACE_HEIGHT_RATIO: สัดส่วนของกรอบภาพเทียบกับความสูงของใบหน้า (ยิ่งค่ามาก ยิ่งเห็นช่วงลำตัวมากขึ้น)EYE_LINE_POSITION_RATIO: ตำแหน่งของเส้นดวงตาในแนวตั้งของภาพสุดท้าย (เช่น 0.35 คืออยู่ที่ 35% จากขอบบน)
