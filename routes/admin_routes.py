from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi.security import OAuth2PasswordBearer
import jwt
from config import settings
from auth.jwt_bearer import JWTBearer
from database import get_database
from pydantic import BaseModel
from bson import ObjectId
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserBase(BaseModel):
    username: str
    email: str
    role: str

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    pass

class UploadData(BaseModel):
    className: str
    data: List[List[Any]]

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    blocked_at: Optional[datetime]
    approved_at: Optional[datetime]
    class_id: Optional[str]
    managed_classes: List[str]

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(JWTBearer())]
)

@router.get("/users", response_model=List[UserResponse])
async def get_users():
    try:
        db = await get_database()
        users = await db.users.find().to_list(None)
        
        # Chuyển đổi dữ liệu cho mỗi user
        formatted_users = []
        for user in users:
            # Chuyển đổi _id và các ObjectId khác thành string
            user_dict = {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "status": user.get("status", "pending"),
                "created_at": user.get("created_at", datetime.now()),
                "updated_at": user.get("updated_at"),
                "last_login": user.get("last_login"),
                "blocked_at": user.get("blocked_at"),
                "approved_at": user.get("approved_at"),
                "class_id": str(user["class_id"]) if "class_id" in user and user["class_id"] else None,
                "managed_classes": [str(class_id) for class_id in user.get("managed_classes", [])] if user.get("managed_classes") else []
            }
            formatted_users.append(UserResponse(**user_dict))
        
        return formatted_users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users")
async def create_user(user: UserCreate):
    try:
        db = await get_database()
        
        # Kiểm tra username và email đã tồn tại chưa
        if await db.users.find_one({"username": user.username}):
            raise HTTPException(status_code=400, detail="Username đã tồn tại")
        if await db.users.find_one({"email": user.email}):
            raise HTTPException(status_code=400, detail="Email đã tồn tại")
        
        # Hash mật khẩu
        hashed_password = pwd_context.hash(user.password)
        
        # Tạo user mới
        user_data = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "hashed_password": hashed_password,
            "status": "active",  # Admin tạo user thì mặc định active
            "created_at": datetime.utcnow()
        }
        
        result = await db.users.insert_one(user_data)
        return {"id": str(result.inserted_id), "message": "Tạo user thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}")
async def update_user(user_id: str, user: UserUpdate):
    try:
        db = await get_database()
        
        # Kiểm tra user tồn tại
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        # Kiểm tra username và email đã tồn tại chưa (trừ user hiện tại)
        if await db.users.find_one({"username": user.username, "_id": {"$ne": ObjectId(user_id)}}):
            raise HTTPException(status_code=400, detail="Username đã tồn tại")
        if await db.users.find_one({"email": user.email, "_id": {"$ne": ObjectId(user_id)}}):
            raise HTTPException(status_code=400, detail="Email đã tồn tại")
        
        # Cập nhật thông tin
        update_data = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "updated_at": datetime.utcnow()
        }
        
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        return {"message": "Cập nhật user thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    try:
        db = await get_database()
        
        # Kiểm tra user tồn tại
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        # Xóa user
        await db.users.delete_one({"_id": ObjectId(user_id)})
        return {"message": "Xóa user thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/approve")
async def approve_user(user_id: str):
    """
    Duyệt tài khoản người dùng mới đăng ký
    """
    try:
        db = await get_database()
        
        # Kiểm tra định dạng user_id hợp lệ
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID người dùng không hợp lệ"
            )
            
        # Kiểm tra user tồn tại
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tồn tại"
            )
        
        # Kiểm tra trạng thái hiện tại
        if existing_user.get("status") != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ có thể duyệt tài khoản đang ở trạng thái chờ duyệt"
            )
        
        # Cập nhật trạng thái
        update_result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": "active",
                    "approved_at": datetime.now()
                }
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể cập nhật trạng thái user"
            )
        
        # Ghi log hoạt động
        await db.activities.insert_one({
            "action": "approve_user",
            "user_id": ObjectId(user_id),
            "admin_action": True,
            "timestamp": datetime.now(),
            "details": f"Đã duyệt tài khoản người dùng {existing_user.get('username')}"
        })
        
        return {"message": "Đã duyệt user thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/reject")
async def reject_user(user_id: str):
    try:
        db = await get_database()
        
        # Kiểm tra user tồn tại
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        # Xóa user bị từ chối
        await db.users.delete_one({"_id": ObjectId(user_id)})
        return {"message": "Đã từ chối và xóa user"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/block")
async def block_user(user_id: str):
    try:
        db = await get_database()
        
        # Kiểm tra user tồn tại
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        # Cập nhật trạng thái
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": "blocked",
                    "blocked_at": datetime.utcnow()
                }
            }
        )
        
        return {"message": "Đã khóa user thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: str):
    try:
        db = await get_database()
        
        # Kiểm tra user tồn tại
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        # Cập nhật trạng thái
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": "active",
                    "unblocked_at": datetime.utcnow()
                }
            }
        )
        
        return {"message": "Đã mở khóa user thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
async def get_dashboard_data():
    try:
        db = await get_database()
        # Get total users
        total_users = await db.users.count_documents({})
        
        # Get research statistics
        pending_research = await db.research.count_documents({"status": "pending"})
        approved_research = await db.research.count_documents({"status": "approved"})
        
        # Get total RFID cards
        total_rfid = await db.rfid_cards.count_documents({})
        
        # Get recent activities and format them
        recent_activities_cursor = db.activities.find().sort("timestamp", -1).limit(10)
        recent_activities = []
        async for activity in recent_activities_cursor:
            activity_dict = {
                "id": str(activity["_id"]),
                "action": activity["action"],
                "timestamp": activity["timestamp"],
                "details": activity["details"],
                "admin_action": activity.get("admin_action", False)
            }
            # Convert user_id to string if it exists
            if "user_id" in activity:
                activity_dict["user_id"] = str(activity["user_id"])
            recent_activities.append(activity_dict)
        
        return {
            "totalUsers": total_users,
            "pendingResearch": pending_research,
            "approvedResearch": approved_research,
            "totalRfid": total_rfid,
            "recentActivities": recent_activities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_dashboard_stats():
    try:
        db = await get_database()
        # Lấy thống kê từ database
        total_students = await db.students.count_documents({})
        total_classes = await db.classes.count_documents({})
        total_users = await db.users.count_documents({})

        return {
            "totalStudents": total_students,
            "totalClasses": total_classes,
            "totalUsers": total_users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-class")
async def upload_class_list(upload_data: UploadData):
    try:
        db = await get_database()
        
        # Kiểm tra xem lớp đã tồn tại chưa
        existing_class = await db.classes.find_one({"name": upload_data.className})
        if existing_class:
            raise HTTPException(status_code=400, detail=f"Lớp {upload_data.className} đã tồn tại")

        # Tạo danh sách học sinh
        students = []
        student_ids = []
        
        for row in upload_data.data:
            if len(row) >= 5:  # Đảm bảo đủ số cột cần thiết
                student = {
                    "_id": ObjectId(),  # Tạo ID cho học sinh
                    "stt": str(row[0]),
                    "ho_ten": str(row[1]),
                    "ngay_sinh": str(row[2]),
                    "tinh": str(row[3]),
                    "gioi_tinh": str(row[4]),
                    "ghi_chu": str(row[5]) if len(row) > 5 else "",
                    "created_at": datetime.utcnow()
                }
                students.append(student)
                student_ids.append(student["_id"])

        # Lưu thông tin học sinh
        if students:
            await db.students.insert_many(students)
            
            # Tạo lớp mới và liên kết với học sinh
            class_data = {
                "name": upload_data.className,
                "student_ids": student_ids,
                "created_at": datetime.utcnow(),
                "total_students": len(students)
            }
            await db.classes.insert_one(class_data)
            
            return {
                "message": f"Đã tạo lớp {upload_data.className} với {len(students)} học sinh"
            }
        
        raise HTTPException(status_code=400, detail="Không có dữ liệu hợp lệ để import")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 