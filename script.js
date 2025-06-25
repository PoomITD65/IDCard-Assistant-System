// รอให้หน้าเว็บโหลดเสร็จสมบูรณ์ก่อนเริ่มทำงาน
document.addEventListener('DOMContentLoaded', function() {
    
    // หา element ของปุ่มและเพิ่ม event listener เข้าไป
    const displayButton = document.getElementById('displayButton');
    if (displayButton) {
        displayButton.addEventListener('click', displayImage);
    }

});

function displayImage() {
    // ดึง element ที่จำเป็นจากหน้า HTML
    const base64Input = document.getElementById('base64Input');
    const imageContainer = document.getElementById('image-container');

    // ดึงข้อมูลข้อความ Base64 จากช่อง textarea
    const base64String = base64Input.value;

    // ตรวจสอบว่าข้อมูลที่ได้มาถูกต้องหรือไม่
    if (base64String && base64String.startsWith('data:image')) {
        // สร้าง element <img> ขึ้นมาใหม่ในหน่วยความจำ
        const img = document.createElement('img');
        
        // กำหนด src ของรูปภาพให้เป็นข้อมูล base64
        img.src = base64String;
        
        // ล้างข้อมูลเก่าใน container ก่อน
        imageContainer.innerHTML = '';
        
        // นำ element รูปภาพใหม่ที่สร้างขึ้นไปใส่ใน container เพื่อแสดงผล
        imageContainer.appendChild(img);
    } else {
        // ถ้าข้อมูลไม่ถูกต้อง ให้แสดงข้อความเตือน
        imageContainer.innerHTML = '<p style="color: red;">ข้อมูลไม่ถูกต้อง กรุณาวางข้อมูล Base64 ที่ขึ้นต้นด้วย "data:image..."</p>';
    }
}
