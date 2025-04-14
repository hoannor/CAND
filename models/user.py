from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any
from datetime import datetime
from bson import ObjectId
from config import settings

class UserBase(BaseModel):
    username: str = Field(..., description="Tên đăng nhập")
    email: EmailStr = Field(..., description="Email")
    full_name: Optional[str] = Field(None, description="Họ và tên")
    role: str = Field(..., description="Vai trò: admin, approver, researcher, student")
    department: Optional[str] = Field(None, description="Khoa/Phòng ban")
    position: Optional[str] = Field(None, description="Chức vụ")
    class_id: Optional[str] = Field(None, description="ID lớp học mà researcher quản lý")
    managed_classes: Optional[List[str]] = Field(default=[], description="Danh sách ID lớp học mà approver quản lý")

class UserCreate(UserBase):
    password: str = Field(..., description="Mật khẩu")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    password: Optional[str] = None
    class_id: Optional[str] = None
    managed_classes: Optional[List[str]] = None

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str = Field(..., description="Mật khẩu đã được mã hóa")
    is_active: bool = Field(default=True, description="Trạng thái tài khoản")
    status: str = Field(default="active", description="Trạng thái tài khoản (active/inactive)")
    last_login: Optional[datetime] = Field(default=None, description="Thời gian đăng nhập cuối cùng")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_verified: bool = False

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    @classmethod
    def from_mongo(cls, data: dict):
        """Convert MongoDB data to Pydantic model."""
        if not data:
            return None
        
        id = data.pop('_id', None)
        if id:
            data['id'] = str(id)
        
        return cls(**data)

class UserResponse(UserInDB):
    pass
