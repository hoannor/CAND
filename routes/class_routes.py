from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from models.class_model import ClassCreate, ClassUpdate, ClassResponse
from database.mongodb import get_database
from bson import ObjectId
from models.user import UserResponse, UserInDB
from services.auth_service import get_current_user

router = APIRouter(
    prefix="/api/classes",
    tags=["classes"]
)

# Endpoint không yêu cầu xác thực để lấy danh sách lớp học cho form đăng ký
@router.get("/public", response_model=List[ClassResponse])
async def get_public_classes():
    """
    Lấy danh sách lớp học cho form đăng ký (không yêu cầu xác thực)
    """
    db = await get_database()
    
    # Lấy danh sách lớp chưa có researcher quản lý
    query = {
        "$or": [
            {"researcher_id": None},
            {"researcher_id": {"$exists": False}}
        ]
    }
    classes = await db.classes.find(query).to_list(100)
    
    # Chuyển đổi ObjectId thành string
    formatted_classes = []
    for class_item in classes:
        try:
            # Chuyển đổi ObjectId thành string
            class_dict = {
                "id": str(class_item["_id"]),
                "code": class_item.get("code", ""),
                "name": class_item.get("name", ""),
                "academic_year": class_item.get("academic_year", ""),
                "semester": int(class_item.get("semester", 0)),  # Chuyển đổi sang số nguyên, mặc định là 0
                "description": class_item.get("description", ""),
                "researcher_id": None,  # Luôn là None vì đây là các lớp chưa có researcher
                "students": [str(student_id) for student_id in class_item.get("students", [])],
                "created_at": class_item.get("created_at", datetime.now()),
                "updated_at": class_item.get("updated_at", datetime.now())
            }
            formatted_classes.append(class_dict)
        except Exception as e:
            print(f"Error formatting class: {e}")
            continue
    
    return [ClassResponse(**class_item) for class_item in formatted_classes]

# Router cho các endpoint yêu cầu xác thực
router_with_auth = APIRouter(
    prefix="/api/classes",
    tags=["classes"]
)

@router_with_auth.get("/my-class", response_model=ClassResponse)
async def get_my_class(current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy thông tin lớp học của researcher hiện tại
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền truy cập lớp học"
        )
    
    db = await get_database()
    
    # Tìm lớp học mà researcher quản lý
    class_item = await db.classes.find_one({"researcher_id": ObjectId(current_user.id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp học được phân công"
        )
    
    # Chuyển đổi ObjectId thành string
    class_item["id"] = str(class_item.pop("_id"))
    class_item["researcher_id"] = str(class_item["researcher_id"])
    class_item["students"] = [str(student_id) for student_id in class_item.get("students", [])]
    
    return ClassResponse(**class_item)

@router_with_auth.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy thông tin chi tiết của một lớp
    """
    db = await get_database()
    
    # Lấy thông tin lớp
    class_item = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp"
        )
    
    # Kiểm tra quyền truy cập
    if current_user.role == "researcher" and str(class_item["researcher_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập lớp này"
        )
    
    # Chuyển đổi ObjectId thành string
    class_item["id"] = str(class_item.pop("_id"))
    class_item["researcher_id"] = str(class_item["researcher_id"])
    class_item["students"] = [str(student_id) for student_id in class_item["students"]]
    
    return ClassResponse(**class_item)

@router_with_auth.post("/", response_model=ClassResponse)
async def create_class(class_data: ClassCreate, current_user: UserInDB = Depends(get_current_user)):
    """
    Tạo một lớp mới (chỉ researcher mới có quyền)
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền tạo lớp"
        )
    
    db = await get_database()
    
    # Kiểm tra mã lớp đã tồn tại chưa
    existing_class = await db.classes.find_one({"code": class_data.code})
    if existing_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã lớp đã tồn tại"
        )
    
    # Tạo lớp mới
    class_dict = class_data.dict()
    class_dict["researcher_id"] = ObjectId(current_user.id)
    class_dict["created_at"] = datetime.now()
    class_dict["updated_at"] = datetime.now()
    class_dict["students"] = []
    
    result = await db.classes.insert_one(class_dict)
    class_dict["id"] = str(result.inserted_id)
    
    return ClassResponse(**class_dict)

@router_with_auth.get("/", response_model=List[ClassResponse])
async def get_classes(current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy danh sách lớp (researcher chỉ thấy lớp của mình)
    """
    db = await get_database()
    
    # Xây dựng query dựa trên role
    query = {}
    if current_user.role == "researcher":
        query["researcher_id"] = ObjectId(current_user.id)
    
    # Lấy danh sách lớp
    classes = await db.classes.find(query).to_list(100)
    
    # Chuyển đổi ObjectId thành string
    for class_item in classes:
        class_item["id"] = str(class_item.pop("_id"))
        class_item["researcher_id"] = str(class_item["researcher_id"])
        class_item["students"] = [str(student_id) for student_id in class_item["students"]]
    
    return [ClassResponse(**class_item) for class_item in classes]

@router_with_auth.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: str,
    class_data: ClassUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Cập nhật thông tin lớp (chỉ researcher quản lý mới có quyền)
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền cập nhật lớp"
        )
    
    db = await get_database()
    
    # Kiểm tra lớp tồn tại và quyền quản lý
    class_item = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp"
        )
    
    if str(class_item["researcher_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền cập nhật lớp này"
        )
    
    # Cập nhật thông tin lớp
    update_data = class_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.now()
    
    await db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$set": update_data}
    )
    
    # Lấy thông tin lớp đã cập nhật
    updated_class = await db.classes.find_one({"_id": ObjectId(class_id)})
    updated_class["id"] = str(updated_class.pop("_id"))
    updated_class["researcher_id"] = str(updated_class["researcher_id"])
    updated_class["students"] = [str(student_id) for student_id in updated_class["students"]]
    
    return ClassResponse(**updated_class)

@router_with_auth.delete("/{class_id}")
async def delete_class(class_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Xóa lớp (chỉ researcher quản lý mới có quyền)
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền xóa lớp"
        )
    
    db = await get_database()
    
    # Kiểm tra lớp tồn tại và quyền quản lý
    class_item = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp"
        )
    
    if str(class_item["researcher_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền xóa lớp này"
        )
    
    # Xóa lớp
    await db.classes.delete_one({"_id": ObjectId(class_id)})
    
    # Cập nhật class_id của sinh viên trong lớp
    await db.users.update_many(
        {"class_id": ObjectId(class_id)},
        {"$unset": {"class_id": ""}}
    )
    
    return {"message": "Đã xóa lớp thành công"}

@router_with_auth.post("/{class_id}/students/{student_id}")
async def add_student_to_class(
    class_id: str,
    student_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Thêm sinh viên vào lớp (chỉ researcher quản lý mới có quyền)
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền thêm sinh viên vào lớp"
        )
    
    db = await get_database()
    
    # Kiểm tra lớp tồn tại và quyền quản lý
    class_item = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp"
        )
    
    if str(class_item["researcher_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thêm sinh viên vào lớp này"
        )
    
    # Kiểm tra sinh viên tồn tại
    student = await db.users.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sinh viên"
        )
    
    # Thêm sinh viên vào lớp
    await db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$addToSet": {"students": ObjectId(student_id)}}
    )
    
    # Cập nhật class_id của sinh viên
    await db.users.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"class_id": ObjectId(class_id)}}
    )
    
    return {"message": "Đã thêm sinh viên vào lớp thành công"}

@router_with_auth.delete("/{class_id}/students/{student_id}")
async def remove_student_from_class(
    class_id: str,
    student_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Xóa sinh viên khỏi lớp (chỉ researcher quản lý mới có quyền)
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền xóa sinh viên khỏi lớp"
        )
    
    db = await get_database()
    
    # Kiểm tra lớp tồn tại và quyền quản lý
    class_item = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp"
        )
    
    if str(class_item["researcher_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền xóa sinh viên khỏi lớp này"
        )
    
    # Xóa sinh viên khỏi lớp
    await db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$pull": {"students": ObjectId(student_id)}}
    )
    
    # Cập nhật class_id của sinh viên
    await db.users.update_one(
        {"_id": ObjectId(student_id)},
        {"$unset": {"class_id": ""}}
    )
    
    return {"message": "Đã xóa sinh viên khỏi lớp thành công"}

@router_with_auth.get("/my-classes", response_model=List[ClassResponse])
async def get_my_classes(current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy danh sách lớp mà researcher đang quản lý
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền truy cập"
        )
    
    db = await get_database()
    
    # Lấy danh sách lớp mà researcher quản lý
    classes = await db.classes.find({"researcher_id": ObjectId(current_user.id)}).to_list(100)
    
    # Chuyển đổi ObjectId thành string
    for class_item in classes:
        class_item["id"] = str(class_item.pop("_id"))
        class_item["researcher_id"] = str(class_item["researcher_id"])
        class_item["students"] = [str(student_id) for student_id in class_item["students"]]
    
    return [ClassResponse(**class_item) for class_item in classes]

@router_with_auth.get("/available", response_model=List[ClassResponse])
async def get_available_classes(current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy danh sách lớp có sẵn mà researcher có thể đăng ký quản lý
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền truy cập"
        )
    
    db = await get_database()
    
    # Lấy danh sách lớp mà researcher đang quản lý
    my_classes = await db.classes.find({"researcher_id": ObjectId(current_user.id)}).to_list(100)
    my_class_ids = [class_item["_id"] for class_item in my_classes]
    
    # Lấy danh sách lớp có sẵn (không có researcher_id hoặc researcher_id khác)
    query = {"_id": {"$nin": my_class_ids}}
    available_classes = await db.classes.find(query).to_list(100)
    
    # Chuyển đổi ObjectId thành string
    for class_item in available_classes:
        class_item["id"] = str(class_item.pop("_id"))
        if "researcher_id" in class_item:
            class_item["researcher_id"] = str(class_item["researcher_id"])
        class_item["students"] = [str(student_id) for student_id in class_item["students"]]
    
    return [ClassResponse(**class_item) for class_item in available_classes]

@router_with_auth.post("/{class_id}/register")
async def register_class(class_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Đăng ký quản lý một lớp học
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền đăng ký quản lý lớp"
        )
    
    db = await get_database()
    
    # Kiểm tra lớp tồn tại
    class_item = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp"
        )
    
    # Cập nhật researcher_id cho lớp
    await db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$set": {"researcher_id": ObjectId(current_user.id), "updated_at": datetime.now()}}
    )
    
    return {"message": "Đăng ký quản lý lớp thành công"}

@router_with_auth.post("/{class_id}/unregister")
async def unregister_class(class_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Hủy đăng ký quản lý một lớp học
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ researcher mới có quyền hủy đăng ký quản lý lớp"
        )
    
    db = await get_database()
    
    # Kiểm tra lớp tồn tại
    class_item = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lớp"
        )
    
    # Kiểm tra researcher có quyền quản lý lớp không
    if "researcher_id" not in class_item or str(class_item["researcher_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền hủy đăng ký quản lý lớp này"
        )
    
    # Cập nhật researcher_id cho lớp (xóa researcher_id)
    await db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$unset": {"researcher_id": ""}, "$set": {"updated_at": datetime.now()}}
    )
    
    return {"message": "Hủy đăng ký quản lý lớp thành công"}

@router_with_auth.get("/{class_id}/students", response_model=List[UserResponse])
async def get_class_students(class_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy danh sách sinh viên trong lớp học
    """
    if current_user.role != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only researchers can access this endpoint"
        )
    
    db = await get_database()
    
    # Lấy thông tin lớp học
    class_data = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found"
        )
    
    # Kiểm tra xem researcher có quản lý lớp này không
    if str(class_data["researcher_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this class"
        )
    
    # Lấy danh sách sinh viên
    student_ids = class_data.get("students", [])
    students = []
    
    for student_id in student_ids:
        student = await db.users.find_one({"_id": student_id})
        if student:
            student["id"] = str(student.pop("_id"))
            students.append(UserResponse(**student))
    
    return students

@router_with_auth.get("/my-class/students")
async def get_my_class_students(current_user: UserInDB = Depends(get_current_user)):
    """
    Lấy danh sách sinh viên trong lớp của researcher hiện tại
    """
    try:
        if current_user.role != "researcher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ giảng viên mới có thể xem danh sách lớp"
            )
        
        db = await get_database()
        
        # Tìm lớp học mà researcher quản lý
        class_data = await db.classes.find_one({"researcher_id": ObjectId(current_user.id)})
        if not class_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy lớp học được phân công"
            )
            
        # Lấy danh sách sinh viên từ collection students
        pipeline = [
            {
                "$match": {
                    "class_id": str(class_data["_id"])
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "stt": 1,
                    "ho_ten": 1,
                    "ngay_sinh": 1,
                    "tinh": 1,
                    "gioi_tinh": 1,
                    "ghi_chu": 1,
                    "created_at": 1
                }
            }
        ]
        
        students = await db.students.aggregate(pipeline).to_list(None)
        
        # Chuyển đổi ObjectId thành string và format dữ liệu trả về
        formatted_students = []
        for student in students:
            student["id"] = str(student.pop("_id"))
            formatted_students.append(student)
            
        return {
            "students": formatted_students,
            "class_info": {
                "id": str(class_data["_id"]),
                "code": class_data.get("code", ""),
                "name": class_data.get("name", ""),
                "academic_year": class_data.get("academic_year", ""),
                "semester": class_data.get("semester", "")
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 