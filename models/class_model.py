from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(ObjectId(v))

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema: dict, field: Any) -> None:
        field_schema.update(type="string")

class ClassBase(BaseModel):
    name: str = Field(..., description="Tên lớp")
    code: str = Field(..., description="Mã lớp")
    description: Optional[str] = Field(None, description="Mô tả lớp")
    academic_year: str = Field(..., description="Năm học")
    semester: int = Field(..., description="Học kỳ")
    researcher_id: Optional[str] = Field(None, description="ID của researcher quản lý lớp")

class ClassCreate(ClassBase):
    pass

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[int] = None

class ClassInDB(ClassBase):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    students: List[str] = Field(default_factory=list, description="Danh sách ID sinh viên trong lớp")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ClassResponse(ClassInDB):
    pass 