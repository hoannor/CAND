from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RFIDCard(BaseModel):
    id: Optional[str] = None
    card_id: str
    user_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = datetime.now()
    last_used: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "card_id": "1234567890",
                "user_id": "user123",
                "is_active": True,
                "last_used": "2024-03-13T10:00:00"
            }
        } 