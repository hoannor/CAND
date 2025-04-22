from pymongo import MongoClient
from datetime import datetime

# Kết nối với MongoDB
client = MongoClient("mongodb+srv://hoan7203:Halongyeu123@cluster0.xfi7y.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")  # Thay đổi URI nếu cần
db = client["research_db"]  # Thay "your_database_name" bằng tên database của bạn

# Tạo TTL Index trên trường approved_at với thời gian hết hạn là 24 giờ (86400 giây)
try:
    db.list_check.create_index(
        [("approved_at", 1)],
        expireAfterSeconds=86400
    )
    print("TTL Index created successfully on list_check.approved_at with 24-hour expiration.")
except Exception as e:
    print(f"Error creating TTL Index: {str(e)}")

# Đóng kết nối
client.close()