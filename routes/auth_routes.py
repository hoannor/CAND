from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
from config import settings
from models.user import UserCreate, UserUpdate, UserResponse, UserInDB
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_user_by_username,
    authenticate_user,
    update_last_login,
    create_user_response
)
from database.mongodb import Database
from bson import ObjectId
import jwt
import logging

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

logger = logging.getLogger(__name__)

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """
    Đăng ký tài khoản mới
    """
    db = await Database.get_database()
    
    # Kiểm tra username đã tồn tại
    if await db.users.find_one({"username": user_data.username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username đã tồn tại"
        )
    
    # Kiểm tra email đã tồn tại
    if await db.users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã tồn tại"
        )
    
    # Nếu là researcher và có class_id, kiểm tra lớp tồn tại
    if user_data.role == "researcher" and user_data.class_id:
        class_data = await db.classes.find_one({"_id": ObjectId(user_data.class_id)})
        if not class_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy lớp học"
            )
    
    # Hash mật khẩu
    hashed_password = hash_password(user_data.password)
    
    # Tạo user dict
    user_dict = user_data.dict()
    user_dict["hashed_password"] = hashed_password
    del user_dict["password"]  # Xóa password gốc
    
    # Thêm các trường bổ sung
    user_dict["created_at"] = datetime.now()
    user_dict["updated_at"] = datetime.now()
    user_dict["status"] = "pending"  # Thêm trạng thái mặc định
    
    # Chuyển đổi class_id thành ObjectId nếu có
    if user_data.class_id:
        user_dict["class_id"] = ObjectId(user_data.class_id)
    
    # Lưu vào database
    result = await db.users.insert_one(user_dict)
    
    # Cập nhật researcher_id cho lớp sau khi có user ID
    if user_data.role == "researcher" and user_data.class_id:
        await db.classes.update_one(
            {"_id": ObjectId(user_data.class_id)},
            {"$set": {"researcher_id": result.inserted_id}}
        )
    
    # Lấy user vừa tạo từ database để đảm bảo có đầy đủ thông tin
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    # Chuyển đổi các ObjectId thành string
    created_user["id"] = str(created_user["_id"])
    del created_user["_id"]  # Xóa _id vì đã có id
    if "class_id" in created_user:
        created_user["class_id"] = str(created_user["class_id"])
    
    return UserResponse(**created_user)

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # Xác thực user
        user = await authenticate_user(form_data.username, form_data.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username hoặc mật khẩu không chính xác",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Kiểm tra trạng thái tài khoản
        if user.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đang chờ được duyệt",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đã bị khóa",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Cập nhật thời gian đăng nhập
        await update_last_login(user.id)
        
        # Tạo token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.username,
                "role": user.role
            },
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": create_user_response(user)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể đăng nhập. Vui lòng thử lại sau.",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Giải mã token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ"
            )
            
        # Lấy thông tin user
        user = await get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User không tồn tại"
            )
            
        # Kiểm tra trạng thái tài khoản
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đã bị khóa"
            )
            
        return create_user_response(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
