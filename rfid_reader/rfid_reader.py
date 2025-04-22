import serial
import requests
import json
import time

# Cấu hình cổng Serial và các thông số
SERIAL_PORT = "COM3"  # Thay đổi nếu cần
BAUD_RATE = 9600

# URL của API FastAPI
API_URL = "http://localhost:8888/api/admin/students/{student_id}/rfid"
# Token JWT của admin
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc0NTM0NjQzN30.j04scZlJBR4tnR-wqa6crAZk_a-FOdIiezlvuIvEH44"  # Thay bằng token thực tế

def update_rfid(student_id, rfid_code):
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"rfid_code": rfid_code}
    response = requests.put(API_URL.format(student_id=student_id), headers=headers, json=data)
    if response.status_code == 200:
        print(f"Đã cập nhật mã RFID {rfid_code} cho sinh viên {student_id}")
    else:
        print(f"Lỗi khi cập nhật RFID: {response.text}")

def main():
    # Kết nối với Arduino qua cổng Serial
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print("Đang kết nối với Arduino...")

    # Nhập student_id từ người dùng
    student_id = input("Nhập ID của sinh viên để cập nhật RFID: ")

    while True:
        try:
            # Đọc dữ liệu từ Serial
            line = ser.readline().decode('utf-8').strip()
            if line.startswith("RFID:"):
                rfid_code = line.split("RFID:")[1]
                print(f"Đã nhận mã RFID: {rfid_code}")
                # Gửi mã RFID lên API
                update_rfid(student_id, rfid_code)
                # Yêu cầu nhập student_id mới
                student_id = input("Nhập ID của sinh viên tiếp theo để cập nhật RFID: ")
        except Exception as e:
            print(f"Lỗi: {e}")
        time.sleep(0.1)

if __name__ == "__main__":
    main()