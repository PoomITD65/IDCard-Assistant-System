<h2>Firebase Realtime Image Processor Service</h2>
<p>สคริปต์นี้ทำงานเป็น Service เบื้องหลัง (Background Service) ที่คอยเฝ้าดูและประมวลผลรูปภาพที่ถูกส่งเข้ามายัง Firebase Realtime Database โดยอัตโนมัติ</p>

<hr>

<h3>ภาพรวมการทำงาน</h3>
<ul>
    <li><strong>เฝ้าดู (Listen):</strong> โปรแกรมจะเชื่อมต่อกับ Firebase และเฝ้าดู Path <code>/processed_photos</code> ตลอดเวลา</li>
    <li><strong>รับข้อมูล:</strong> เมื่อมีข้อมูลภาพใหม่ (ในรูปแบบ Base64) ถูกเพิ่มเข้ามาที่ Path ดังกล่าว โปรแกรมจะเริ่มทำงานทันที</li>
    <li><strong>ประมวลผล (Process):</strong>
        <ul>
            <li>ค้นหาใบหน้าและจุดสำคัญบนใบหน้า (Face Landmarks) ด้วย <code>face_recognition</code></li>
            <li>คำนวณเพื่อจัดองค์ประกอบภาพให้อยู่ในตำแหน่งที่เหมาะสม (Auto-cropping)</li>
            <li>ลบพื้นหลังออกจากรูปภาพด้วย <code>rembg</code></li>
            <li>เติมพื้นหลังใหม่ (สีน้ำเงินตามที่ตั้งค่าไว้)</li>
            <li>ปรับขนาดภาพให้เป็นขนาดสุดท้ายที่ต้องการ (350x425 pixels)</li>
        </ul>
    </li>
    <li><strong>ส่งผลลัพธ์:</strong>
        <ul>
            <li><strong>หากสำเร็จ:</strong> ภาพสุดท้ายจะถูกบันทึกไปที่ Path <code>/finish_photos</code></li>
            <li><strong>หากล้มเหลว:</strong> ข้อมูลข้อผิดพลาด (เช่น ไม่พบใบหน้า, พบมากกว่า 1 ใบหน้า) จะถูกบันทึกไปที่ Path <code>/error_photos</code></li>
        </ul>
    </li>
    <li><strong>เคลียร์คิว:</strong> หลังจากประมวลผลเสร็จ (ไม่ว่าจะสำเร็จหรือล้มเหลว) ข้อมูลภาพดิบจาก <code>/processed_photos</code> จะถูกลบออกไป เพื่อเตรียมรอรับงานถัดไป</li>
</ul>

<hr>

<h3>วิธีการติดตั้งและใช้งาน</h3>

<h4>1. ข้อกำหนดเบื้องต้น (Prerequisites)</h4>
<ul>
    <li>Python 3.7+</li>
    <li>บัญชี Firebase พร้อมกับเปิดใช้งาน Realtime Database</li>
</ul>

<h4>2. การติดตั้ง</h4>
<p><strong>ขั้นตอนที่ 1: สร้างและเปิดใช้งาน Virtual Environment (แนะนำ)</strong></p>
<p>เพื่อป้องกันปัญหาเรื่องเวอร์ชันของไลบรารี ควรสร้างสภาพแวดล้อมเสมือนสำหรับโปรเจกต์นี้</p>
<pre><code># สร้าง virtual environment ชื่อ 'venv'
python -m venv venv

# เปิดใช้งาน (Activate)
# บน Windows:
venv\Scripts\activate

# บน macOS/Linux:
source venv/bin/activate</code></pre>

<p><strong>ขั้นตอนที่ 2: ติดตั้ง Dependencies</strong></p>
<p>สร้างไฟล์ชื่อ <code>requirements.txt</code> แล้วคัดลอกเนื้อหาข้างล่างนี้ไปใส่:</p>
<pre><code>Pillow
face_recognition
rembg
firebase-admin</code></pre>
<p>จากนั้นรันคำสั่งติดตั้งผ่าน pip:</p>
<pre><code>pip install -r requirements.txt</code></pre>
<p><em>หมายเหตุ: การติดตั้ง dlib (ซึ่งเป็นส่วนหนึ่งของ face_recognition) อาจใช้เวลานานและอาจต้องการ CMake และ C++ compiler ในระบบของคุณ</em></p>

<h4>3. การตั้งค่า (Configuration)</h4>
<p><strong>ขั้นตอนที่ 1: ดาวน์โหลด Firebase Service Account Key</strong></p>
<ol>
    <li>ไปที่ Firebase Console ของโปรเจกต์คุณ</li>
    <li>คลิกที่ไอคอนรูปเฟือง (ข้างๆ Project Overview) > Project settings</li>
    <li>ไปที่แท็บ Service accounts</li>
    <li>คลิกที่ปุ่ม Generate new private key แล้วบันทึกไฟล์ .json ที่ได้มาลงในโปรเจกต์ (เช่น ในโฟลเดอร์ชื่อ key/)</li>
</ol>

<p><strong>ขั้นตอนที่ 2: แก้ไขค่าในสคริปต์</strong></p>
<p>เปิดไฟล์ <code>firebase_processor_service.py</code> และแก้ไขค่าใน ส่วนที่ 2 (Firebase Setup):</p>
<ul>
    <li><code>SERVICE_ACCOUNT_KEY_PATH</code>: แก้ไขเป็นตำแหน่งที่ถูกต้องของไฟล์ .json ที่คุณดาวน์โหลดมา
        <pre><code>SERVICE_ACCOUNT_KEY_PATH = "key/your-service-account-file.json"</code></pre>
    </li>
    <li><code>FIREBASE_DATABASE_URL</code>: คัดลอก URL ของ Realtime Database ของคุณมาใส่ (ดูได้จากหน้า Realtime Database ใน Firebase Console)
        <pre><code>FIREBASE_DATABASE_URL = "https://your-project-id-default-rtdb.firebaseio.com/"</code></pre>
    </li>
</ul>

<h4>4. การรัน Service</h4>
<p>เมื่อตั้งค่าทุกอย่างเรียบร้อยแล้ว ให้รันสคริปต์จาก Terminal หรือ Command Prompt:</p>
<pre><code>python firebase_processor_service.py</code></pre>
<p>หากสำเร็จ โปรแกรมจะแสดงข้อความว่าเชื่อมต่อ Firebase สำเร็จ และเข้าสู่สถานะ "กำลังรอข้อมูลเพิ่มเข้ามา" ซึ่งหมายความว่า Service ของคุณพร้อมทำงานแล้ว</p>
<pre><code>--- [Cloud Processor] กำลังเริ่มต้นและเชื่อมต่อกับ Firebase ---
✅ (Cloud Processor) เชื่อมต่อ Firebase สำเร็จแล้ว!
✅ เริ่มการเฝ้าดู Path '/processed_photos' แบบ Real-time
(กด Ctrl+C เพื่อหยุด)

======================================================
                             กำลังรอข้อมูลเพิ่มเข้ามา
======================================================</code></pre>

<h4>5. การปรับแต่งค่าการประมวลผล</h4>
<p>คุณสามารถปรับแต่งพารามิเตอร์ต่างๆ ในการประมวลผลภาพได้ใน ส่วนที่ 3 (Image Processing Config) ของสคริปต์:</p>
<ul>
    <li><code>FINAL_IMAGE_WIDTH</code>, <code>FINAL_IMAGE_HEIGHT</code>: ขนาดของภาพสุดท้าย (หน่วยเป็น pixel)</li>
    <li><code>NEW_BACKGROUND_COLOR</code>: สีพื้นหลังใหม่ (ในรูปแบบ RGB)</li>
    <li><code>FRAME_TO_FACE_HEIGHT_RATIO</code>: สัดส่วนของกรอบภาพเทียบกับความสูงของใบหน้า (ยิ่งค่ามาก ยิ่งเห็นช่วงลำตัวมากขึ้น)</li>
    <li><code>EYE_LINE_POSITION_RATIO</code>: ตำแหน่งของเส้นดวงตาในแนวตั้งของภาพสุดท้าย (เช่น 0.35 คืออยู่ที่ 35% จากขอบบน)</li>
</ul>
