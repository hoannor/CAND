from fastapi import APIRouter, Depends, HTTPException
from database import get_database
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter(
    prefix="/api",
    tags=["Excel Data"]
)

@router.post("/submit-excel-data")
async def submit_excel_data(data: List[List[Any]]):
    """
    Xử lý dữ liệu Excel được gửi từ người dùng
    """
    if not data or len(data) < 2:
        raise HTTPException(status_code=400, detail="Dữ liệu không hợp lệ")
    
    try:
        db = await get_database()
        
        # Lấy header từ dòng đầu tiên
        headers = data[0]
        
        # Tạo collection mới để lưu dữ liệu
        collection_name = f"excel_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        collection = db[collection_name]
        
        # Chuyển đổi dữ liệu thành các document
        documents = []
        for row in data[1:]:
            if len(row) != len(headers):
                continue  # Bỏ qua các dòng không đủ cột
                
            document = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    document[str(header)] = row[i]
            
            documents.append(document)
        
        # Lưu dữ liệu vào database
        if documents:
            await collection.insert_many(documents)
            
        return {
            "message": "Dữ liệu đã được lưu thành công",
            "collection": collection_name,
            "record_count": len(documents)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý dữ liệu: {str(e)}") 