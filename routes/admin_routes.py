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
    data: List[List[Any]]  # Giữ nguyên schema hiện tại

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

class ClassResponse(BaseModel):
    id: str
    name: str
    total_students: int

class StudentResponse(BaseModel):
    id: str
    ho_ten: str
    rfid_code: Optional[str]
    class_name: Optional[str]

class UpdateRfidRequest(BaseModel):
    rfid_code: Optional[str]

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
        
        formatted_users = []
        for user in users:
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
        
        if await db.users.find_one({"username": user.username}):
            raise HTTPException(status_code=400, detail="Username đã tồn tại")
        if await db.users.find_one({"email": user.email}):
            raise HTTPException(status_code=400, detail="Email đã tồn tại")
        
        hashed_password = pwd_context.hash(user.password)
        
        user_data = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "hashed_password": hashed_password,
            "status": "active",
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
        
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        if await db.users.find_one({"username": user.username, "_id": {"$ne": ObjectId(user_id)}}):
            raise HTTPException(status_code=400, detail="Username đã tồn tại")
        if await db.users.find_one({"email": user.email, "_id": {"$ne": ObjectId(user_id)}}):
            raise HTTPException(status_code=400, detail="Email đã tồn tại")
        
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
        
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        await db.users.delete_one({"_id": ObjectId(user_id)})
        return {"message": "Xóa user thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/approve")
async def approve_user(user_id: str):
    try:
        db = await get_database()
        
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID người dùng không hợp lệ"
            )
            
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User không tồn tại"
            )
        
        if existing_user.get("status") != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ có thể duyệt tài khoản đang ở trạng thái chờ duyệt"
            )
        
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
        
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
        await db.users.delete_one({"_id": ObjectId(user_id)})
        return {"message": "Đã từ chối và xóa user"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/block")
async def block_user(user_id: str):
    try:
        db = await get_database()
        
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
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
        
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        
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
        total_users = await db.users.count_documents({})
        pending_research = await db.research.count_documents({"status": "pending"})
        approved_research = await db.research.count_documents({"status": "approved"})
        total_rfid = await db.rfid_cards.count_documents({})
        
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
        
        existing_class = await db.classes.find_one({"name": upload_data.className})
        if existing_class:
            raise HTTPException(status_code=400, detail=f"Lớp {upload_data.className} đã tồn tại")

        students = []
        student_ids = []
        
        for row in upload_data.data:
            if len(row) >= 1:  # Chỉ cần cột Họ Tên (index 0, vì giờ là [ho_ten])
                student = {
                    "_id": ObjectId(),
                    "ho_ten": str(row[0]),  # Lấy từ index 0
                    "class_name": upload_data.className,
                    "created_at": datetime.utcnow()
                }
                students.append(student)
                student_ids.append(student["_id"])

        if students:
            await db.students.insert_many(students)
            
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

@router.get("/classes", response_model=List[ClassResponse])
async def get_classes():
    try:
        db = await get_database()
        classes = await db.classes.find().to_list(None)
        
        formatted_classes = []
        for cls in classes:
            formatted_classes.append({
                "id": str(cls["_id"]),
                "name": cls["name"],
                "total_students": cls["total_students"]
            })
        
        return formatted_classes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách lớp: {str(e)}")

@router.get("/classes/{class_id}/students", response_model=List[StudentResponse])
async def get_students_in_class(class_id: str):
    try:
        db = await get_database()
        
        class_obj = await db.classes.find_one({"_id": ObjectId(class_id)})
        if not class_obj:
            raise HTTPException(status_code=404, detail="Lớp không tồn tại")
        
        student_ids = [ObjectId(student_id) for student_id in class_obj["student_ids"]]
        
        students = await db.students.find({"_id": {"$in": student_ids}}).to_list(None)
        
        formatted_students = []
        for student in students:
            formatted_students.append({
                "id": str(student["_id"]),
                "ho_ten": student["ho_ten"],
                "rfid_code": student.get("rfid_code"),
                "class_name": student.get("class_name")
            })
        
        return formatted_students
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách sinh viên: {str(e)}")

@router.put("/students/{student_id}/rfid")
async def update_student_rfid(student_id: str, request: UpdateRfidRequest, current_user: dict = Depends(JWTBearer())):
    try:
        db = await get_database()
        
        student = await db.students.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Sinh viên không tồn tại")
        
        update_data = {
            "rfid_code": request.rfid_code,
            "updated_at": datetime.utcnow()
        }
        
        await db.students.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": update_data}
        )
        
        return {"message": "Lưu mã RFID thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu mã RFID: {str(e)}")