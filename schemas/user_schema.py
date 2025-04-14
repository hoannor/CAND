from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    INSPECTOR = "inspector"  # Người kiểm tra
    APPROVER = "approver"    # Người duyệt phiếu
    APPLICANT = "applicant"  # Người đăng ký phiếu
    RESEARCHER = "researcher"  # Nhà nghiên cứu

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "researcher"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "role": "researcher",
                "id": "507f1f77bcf86cd799439011"
            }
        }
