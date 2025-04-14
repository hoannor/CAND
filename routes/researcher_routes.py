from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional, Dict, Any
from datetime import datetime
from auth.jwt_bearer import JWTBearer
from models.research import Research, ResearchResponse
from models.user import UserResponse, UserInDB
from database import get_database
from bson import ObjectId
from services.auth_service import get_current_user
import os
import shutil
from pathlib import Path
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/researcher",
    tags=["researcher"],
    dependencies=[Depends(JWTBearer())]
)

class StudentResponse(BaseModel):
    stt: str
    ho_ten: str
    ngay_sinh: str
    tinh: str
    gioi_tinh: str
    ghi_chu: str = ""
    created_at: datetime

@router.get("/dashboard")
async def get_researcher_dashboard(user_id: str = Depends(JWTBearer())):
    """
    Lấy thông tin dashboard cho researcher
    """
    db = await get_database()
    
    # Lấy thống kê nghiên cứu của người dùng
    total_research = await db.research.count_documents({"user_id": ObjectId(user_id)})
    pending_research = await db.research.count_documents({"user_id": ObjectId(user_id), "status": "pending"})
    approved_research = await db.research.count_documents({"user_id": ObjectId(user_id), "status": "approved"})
    rejected_research = await db.research.count_documents({"user_id": ObjectId(user_id), "status": "rejected"})
    
    # Lấy hoạt động gần đây
    recent_activities = await db.activities.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1).limit(10).to_list(10)
    
    return {
        "totalResearch": total_research,
        "pendingResearch": pending_research,
        "approvedResearch": approved_research,
        "rejectedResearch": rejected_research,
        "activities": recent_activities
    }

@router.get("/research", response_model=List[ResearchResponse])
async def get_research_list(
    status: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Lấy danh sách nghiên cứu của researcher
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only researchers can access this endpoint"
        )
    
    db = await get_database()
    
    # Xây dựng query
    query = {"user_id": ObjectId(current_user.id)}
    if status:
        query["status"] = status
    
    # Lấy danh sách nghiên cứu
    researches = await db.research.find(query).to_list(100)
    
    # Chuyển đổi ObjectId thành string
    for research in researches:
        research["id"] = str(research.pop("_id"))
        research["user_id"] = str(research["user_id"])
    
    return [ResearchResponse(**research) for research in researches]

@router.get("/research/{research_id}")
async def get_research_detail(research_id: str, user_id: str = Depends(JWTBearer())):
    """
    Lấy chi tiết một nghiên cứu
    """
    db = await get_database()
    
    try:
        research = await db.research.find_one({"_id": ObjectId(research_id), "user_id": ObjectId(user_id)})
        if not research:
            raise HTTPException(status_code=404, detail="Không tìm thấy nghiên cứu")
        
        # Chuyển đổi ObjectId thành string
        research["_id"] = str(research["_id"])
        research["user_id"] = str(research["user_id"])
        
        return research
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin nghiên cứu: {str(e)}")

@router.post("/research")
async def create_research(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(JWTBearer())
):
    """
    Tạo một nghiên cứu mới
    """
    db = await get_database()
    
    try:
        # Tạo thư mục lưu file nếu chưa tồn tại
        upload_dir = Path("uploads/research")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Lưu file
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Tạo nghiên cứu mới
        research = {
            "title": title,
            "description": description,
            "category": category,
            "file_path": str(file_path),
            "user_id": ObjectId(user_id),
            "status": "pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await db.research.insert_one(research)
        research["_id"] = str(result.inserted_id)
        
        # Ghi log hoạt động
        await db.activities.insert_one({
            "action": "create_research",
            "user_id": ObjectId(user_id),
            "research_id": str(result.inserted_id),
            "timestamp": datetime.now(),
            "details": f"Đã tạo nghiên cứu mới: {title}"
        })
        
        return {"message": "Đã tạo nghiên cứu thành công", "research": research}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo nghiên cứu: {str(e)}")

@router.put("/research/{research_id}")
async def update_research(
    research_id: str,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    file: Optional[UploadFile] = File(None),
    user_id: str = Depends(JWTBearer())
):
    """
    Cập nhật một nghiên cứu
    """
    db = await get_database()
    
    try:
        # Kiểm tra nghiên cứu có tồn tại và thuộc về người dùng không
        research = await db.research.find_one({"_id": ObjectId(research_id), "user_id": ObjectId(user_id)})
        if not research:
            raise HTTPException(status_code=404, detail="Không tìm thấy nghiên cứu")
        
        # Kiểm tra trạng thái nghiên cứu
        if research["status"] != "rejected":
            raise HTTPException(status_code=400, detail="Chỉ có thể cập nhật nghiên cứu bị từ chối")
        
        # Cập nhật thông tin nghiên cứu
        update_data = {
            "title": title,
            "description": description,
            "category": category,
            "status": "pending",
            "updated_at": datetime.now()
        }
        
        # Nếu có file mới
        if file:
            # Tạo thư mục lưu file nếu chưa tồn tại
            upload_dir = Path("uploads/research")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Lưu file mới
            file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Xóa file cũ nếu có
            if "file_path" in research:
                old_file_path = Path(research["file_path"])
                if old_file_path.exists():
                    old_file_path.unlink()
            
            update_data["file_path"] = str(file_path)
        
        # Cập nhật trong database
        await db.research.update_one(
            {"_id": ObjectId(research_id)},
            {"$set": update_data}
        )
        
        # Ghi log hoạt động
        await db.activities.insert_one({
            "action": "update_research",
            "user_id": ObjectId(user_id),
            "research_id": research_id,
            "timestamp": datetime.now(),
            "details": f"Đã cập nhật nghiên cứu: {title}"
        })
        
        return {"message": "Đã cập nhật nghiên cứu thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật nghiên cứu: {str(e)}")

@router.get("/my-class/students")
async def get_class_students(current_user: UserInDB = Depends(get_current_user)):
    try:
        db = await get_database()
        
        # Lấy danh sách sinh viên của lớp hiện tại
        students = await db.students.find({"class_id": current_user.class_id}).to_list(None)
        
        return {
            "students": students
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 