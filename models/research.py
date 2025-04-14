from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

class Research(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., description="Tiêu đề nghiên cứu")
    description: str = Field(..., description="Mô tả nghiên cứu")
    category: str = Field(..., description="Danh mục nghiên cứu")
    file_path: str = Field(..., description="Đường dẫn file nghiên cứu")
    user_id: str = Field(..., description="ID người dùng tạo nghiên cứu")
    status: str = Field(default="pending", description="Trạng thái nghiên cứu")
    created_at: datetime = Field(default_factory=datetime.now, description="Thời gian tạo")
    updated_at: datetime = Field(default_factory=datetime.now, description="Thời gian cập nhật")
    attachments: List[str] = []
    comments: List[dict] = []

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Research on AI Applications",
                "description": "A study on practical applications of AI in daily life",
                "category": "AI",
                "file_path": "https://example.com/research.pdf",
                "user_id": "user123",
                "status": "pending",
                "attachments": ["file1.pdf", "file2.docx"],
                "comments": [
                    {
                        "user_id": "reviewer1",
                        "comment": "Interesting approach",
                        "timestamp": "2024-03-13T10:00:00"
                    }
                ]
            }
        }

class ResearchResponse(BaseModel):
    id: str = Field(..., description="ID nghiên cứu")
    title: str = Field(..., description="Tiêu đề nghiên cứu")
    description: str = Field(..., description="Mô tả nghiên cứu")
    category: str = Field(..., description="Danh mục nghiên cứu")
    file_path: str = Field(..., description="Đường dẫn file nghiên cứu")
    user_id: str = Field(..., description="ID người dùng tạo nghiên cứu")
    status: str = Field(..., description="Trạng thái nghiên cứu")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")

    class Config:
        from_attributes = True 