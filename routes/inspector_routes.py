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

@router.get("/students")
async def get_students_from_list_check():
    """
    Lấy danh sách tên, mã RFID, trạng thái và tên lớp của sinh viên từ collection list_check
    Note: Bản ghi trong list_check sẽ tự động bị xóa sau 24 giờ kể từ approved_at
    nhờ TTL Index được thiết lập trên trường approved_at.
    """
    db = await get_database()
    
    try:
        # Lấy tất cả bản ghi từ list_check
        list_checks = await db.list_check.find().to_list(None)
        
        # Tạo danh sách tất cả student_ids (không trùng lặp)
        student_ids = set()
        for record in list_checks:
            if "students" in record:
                for student_id in record["students"]:
                    student_ids.add(student_id)
        
        # Chuyển đổi student_ids thành danh sách ObjectId
        student_ids = [ObjectId(student_id) for student_id in student_ids]
        
        # Lấy thông tin sinh viên từ collection students
        students = await db.students.find({"_id": {"$in": student_ids}}).to_list(None)
        
        # Chuyển đổi ObjectId thành string và lấy tên, mã RFID, trạng thái, tên lớp
        student_list = []
        for student in students:
            student["_id"] = str(student["_id"])
            # Nếu sinh viên chưa có trạng thái, mặc định là "Trong trường"
            if "status" not in student:
                await db.students.update_one(
                    {"_id": ObjectId(student["_id"])},
                    {"$set": {"status": "Trong trường"}}
                )
                student["status"] = "Trong trường"
            student_list.append({
                "id": student["_id"],
                "ho_ten": student.get("ho_ten", "Không có tên"),
                "rfid_code": student.get("rfid_code", "Chưa có mã RFID"),
                "status": student["status"],
                "class_name": student.get("class_name", "Chưa có lớp")  # Thêm class_name
            })
        
        return student_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách sinh viên: {str(e)}")

@router.post("/students/{student_id}/update-status")
async def update_student_status(student_id: str, request: dict):
    """
    Cập nhật trạng thái của sinh viên
    """
    db = await get_database()
    
    try:
        # Kiểm tra trạng thái hợp lệ
        new_status = request.get("status")
        if new_status not in ["Trong trường", "Đang ra ngoài"]:
            raise HTTPException(status_code=400, detail="Trạng thái không hợp lệ")

        # Kiểm tra sinh viên tồn tại
        student = await db.students.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Sinh viên không tồn tại")
        
        # Cập nhật trạng thái
        await db.students.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
        )
        
        return {"message": f"Cập nhật trạng thái thành công: {new_status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật trạng thái: {str(e)}")