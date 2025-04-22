from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from auth.jwt_bearer import JWTBearer
from database import get_database
from bson import ObjectId
from services.auth_service import get_current_user
from models.user import UserInDB

router = APIRouter(
    prefix="/api/approver",
    tags=["approver"],
    dependencies=[Depends(JWTBearer())]
)

def convert_objectid_to_str(data):
    """
    Chuyển đổi tất cả các ObjectId trong dữ liệu thành string
    """
    if isinstance(data, dict):
        return {k: convert_objectid_to_str(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    return data

@router.get("/dashboard")
async def get_approver_dashboard(current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy thông tin dashboard cho approver
    """
    db = await get_database()
    
    # Đếm tổng số sự kiện thuộc các lớp mà approver quản lý
    # Không chuyển managed_classes thành ObjectId, giữ nguyên dạng string
    managed_classes = current_user.managed_classes  # Dạng list of strings
    total_events = await db.events.count_documents({"event_id": {"$in": managed_classes}})
    
    # Lấy hoạt động gần đây
    recent_activities = await db.activities.find().sort("timestamp", -1).limit(10).to_list(10)
    
    # Chuyển đổi tất cả ObjectId thành string
    recent_activities = convert_objectid_to_str(recent_activities)
    
    return {
        "totalEvents": total_events,
        "activities": recent_activities
    }

@router.get("/events")
async def get_event_list(current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy danh sách sự kiện thuộc các lớp mà approver quản lý
    """
    db = await get_database()
    
    # Lấy danh sách managed_classes của approver, giữ nguyên dạng string
    managed_classes = current_user.managed_classes  # Dạng list of strings
    print(f"Managed classes for user {current_user.username}: {managed_classes}")  # Debug log
    
    # Lấy các sự kiện có event_id thuộc managed_classes
    events = await db.events.find({"event_id": {"$in": managed_classes}}).sort("created_at", -1).to_list(100)
    print(f"Events found: {events}")  # Debug log
    
    # Xử lý từng sự kiện để lấy thông tin lớp và sinh viên
    for event in events:
        event["_id"] = str(event["_id"])
        event["researcher_id"] = str(event["researcher_id"])
        
        # Lấy thông tin lớp (event_id chính là class_id), chuyển event_id thành ObjectId để truy vấn classes
        class_info = await db.classes.find_one({"_id": ObjectId(event["event_id"])})
        event["class_name"] = class_info["name"] if class_info else "N/A"
        print(f"Class info for event {event['_id']}: {class_info}")  # Debug log
        
        # Lấy danh sách sinh viên
        student_ids = [ObjectId(student_id) for student_id in event["selected_students"]]
        students = await db.students.find({"_id": {"$in": student_ids}}).to_list(None)
        event["student_names"] = [student["ho_ten"] for student in students if "ho_ten" in student]
        print(f"Students for event {event['_id']}: {event['student_names']}")  # Debug log
    
    return events

@router.post("/events/{event_id}/approve")
async def approve_event(event_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Phê duyệt một sự kiện
    """
    db = await get_database()
    
    # Kiểm tra sự kiện tồn tại
    event = await db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Kiểm tra xem approver có quyền phê duyệt sự kiện này không
    managed_classes = current_user.managed_classes  # Dạng list of strings
    if event["event_id"] not in managed_classes:  # So sánh string với string
        raise HTTPException(status_code=403, detail="Bạn không có quyền phê duyệt sự kiện này")
    
    # Lưu danh sách sinh viên vào collection list_check
    await db.list_check.insert_one({
        "event_id": event["event_id"],
        "students": event["selected_students"],
        "approved_at": datetime.now()
    })
    
    # Xóa sự kiện khỏi collection events
    await db.events.delete_one({"_id": ObjectId(event_id)})
    
    # Thêm hoạt động
    await db.activities.insert_one({
        "action": "approve_event",
        "event_id": event_id,
        "timestamp": datetime.now()
    })
    
    return {"message": "Event approved successfully"}

@router.post("/events/{event_id}/reject")
async def reject_event(event_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Từ chối một sự kiện
    """
    db = await get_database()
    
    # Kiểm tra sự kiện tồn tại
    event = await db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Kiểm tra xem approver có quyền từ chối sự kiện này không
    managed_classes = current_user.managed_classes  # Dạng list of strings
    if event["event_id"] not in managed_classes:  # So sánh string với string
        raise HTTPException(status_code=403, detail="Bạn không có quyền từ chối sự kiện này")
    
    # Xóa sự kiện khỏi collection events
    await db.events.delete_one({"_id": ObjectId(event_id)})
    
    # Thêm hoạt động
    await db.activities.insert_one({
        "action": "reject_event",
        "event_id": event_id,
        "timestamp": datetime.now()
    })
    
    return {"message": "Event rejected successfully"}