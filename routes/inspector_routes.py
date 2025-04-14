from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from auth.jwt_bearer import JWTBearer
from models.research import Research
from models.user import UserResponse
from database import get_database
from bson import ObjectId

router = APIRouter(
    prefix="/api/inspector",
    tags=["inspector"],
    dependencies=[Depends(JWTBearer())]
)

@router.get("/dashboard")
async def get_inspector_dashboard():
    """
    Lấy thông tin dashboard cho inspector
    """
    db = await get_database()
    
    # Lấy thống kê nghiên cứu
    total_research = await db.research.count_documents({})
    pending_research = await db.research.count_documents({"status": "pending"})
    inspected_research = await db.research.count_documents({"status": "inspected"})
    
    # Lấy hoạt động gần đây
    recent_activities = await db.activities.find().sort("timestamp", -1).limit(10).to_list(10)
    
    return {
        "totalResearch": total_research,
        "pendingResearch": pending_research,
        "inspectedResearch": inspected_research,
        "activities": recent_activities
    }

@router.get("/research")
async def get_research_list(status: Optional[str] = None):
    """
    Lấy danh sách nghiên cứu theo trạng thái
    """
    db = await get_database()
    
    # Xây dựng query dựa trên status
    query = {}
    if status:
        query["status"] = status
    
    # Lấy danh sách nghiên cứu
    research_list = await db.research.find(query).sort("created_at", -1).to_list(100)
    
    # Chuyển đổi ObjectId thành string
    for research in research_list:
        research["_id"] = str(research["_id"])
        if "user_id" in research:
            research["user_id"] = str(research["user_id"])
    
    return research_list

@router.get("/research/{research_id}")
async def get_research_detail(research_id: str):
    """
    Lấy chi tiết một nghiên cứu
    """
    db = await get_database()
    
    try:
        research = await db.research.find_one({"_id": ObjectId(research_id)})
        if not research:
            raise HTTPException(status_code=404, detail="Không tìm thấy nghiên cứu")
        
        # Chuyển đổi ObjectId thành string
        research["_id"] = str(research["_id"])
        if "user_id" in research:
            research["user_id"] = str(research["user_id"])
            
        # Lấy thông tin người dùng
        if "user_id" in research:
            user = await db.users.find_one({"_id": ObjectId(research["user_id"])})
            if user:
                user["_id"] = str(user["_id"])
                research["user"] = user
        
        return research
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin nghiên cứu: {str(e)}")

@router.post("/research/{research_id}/inspect")
async def inspect_research(research_id: str):
    """
    Kiểm tra một nghiên cứu
    """
    db = await get_database()
    
    try:
        # Cập nhật trạng thái nghiên cứu
        result = await db.research.update_one(
            {"_id": ObjectId(research_id)},
            {"$set": {"status": "inspected", "inspected_at": datetime.now()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy nghiên cứu")
        
        # Ghi log hoạt động
        await db.activities.insert_one({
            "action": "inspect_research",
            "research_id": research_id,
            "timestamp": datetime.now(),
            "details": f"Đã kiểm tra nghiên cứu {research_id}"
        })
        
        return {"message": "Đã kiểm tra nghiên cứu thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi kiểm tra nghiên cứu: {str(e)}") 