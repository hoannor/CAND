from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB settings
    MONGODB_URL: str = "mongodb+srv://hoan7203:Halongyeu123@cluster0.xfi7y.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    MONGODB_DB_NAME: str = "research_db"
    
    # JWT settings
    SECRET_KEY: str = "hoan7203"  # Thay bằng khóa mạnh hơn trong production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:8888",  # Thêm cổng bạn đang dùng
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8888",  # Thêm cổng bạn đang dùng
        "*"
    ]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # Security settings
    PASSWORD_HASH_SCHEME: str = "bcrypt"
    PASSWORD_HASH_DEPRECATED: str = "auto"
    
    # User settings
    DEFAULT_USER_ROLE: str = "researcher"
    USER_STATUSES: list = ["pending", "active", "blocked"]
    USER_ROLES: list = ["admin", "inspector", "approver", "researcher"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()