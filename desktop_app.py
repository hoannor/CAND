import sys
import uvicorn
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap
import threading
import webbrowser
import time
import socket
import os
import signal
import psutil

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    for proc in psutil.process_iter():
        try:
            # Lấy thông tin kết nối của process
            connections = proc.connections()
            for conn in connections:
                if conn.laddr.port == port:
                    proc.kill()
                    time.sleep(1)  # Đợi process kết thúc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

def run_fastapi():
    try:
        uvicorn.run("main:app", host="127.0.0.1", port=8888, reload=False)
    except Exception as e:
        print(f"Error starting FastAPI server: {e}")

class MainWindow(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Research Management System")
        self.resize(1200, 800)
        self.setWindowIcon(QIcon("static/logo.png"))
        
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Xác nhận thoát',
                                   "Bạn có chắc chắn muốn thoát ứng dụng?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Kill process trên cổng 8888
            kill_process_on_port(8888)
            event.accept()
        else:
            event.ignore()

def main():
    # Kill process cũ nếu có
    kill_process_on_port(8888)
    
    # Kiểm tra xem cổng 8888 đã được sử dụng chưa
    if is_port_in_use(8888):
        QMessageBox.critical(None, "Error", "Port 8888 is already in use. Please close other applications using this port.")
        sys.exit(1)

    # Khởi tạo ứng dụng PyQt
    app = QApplication(sys.argv)
    
    # Thiết lập icon cho ứng dụng
    app_icon = QIcon("static/logo.png")
    app.setWindowIcon(app_icon)
    
    # Hiển thị splash screen
    splash_pix = QPixmap("static/logo.png")
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.setEnabled(False)
    splash.show()
    app.processEvents()
    
    # Khởi tạo FastAPI server trong một thread riêng
    api_thread = threading.Thread(target=run_fastapi)
    api_thread.daemon = True
    api_thread.start()
    
    # Đợi server khởi động
    time.sleep(2)
    
    # Tạo cửa sổ trình duyệt
    web = MainWindow()
    web.load(QUrl("http://127.0.0.1:8888"))
    
    # Hiển thị cửa sổ
    web.show()
    
    # Đóng splash screen
    splash.finish(web)
    
    # Chạy ứng dụng
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 