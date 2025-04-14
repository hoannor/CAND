from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from config import settings
from typing import Optional, Dict, Any
from models.user import UserInDB, UserResponse
from database.mongodb import Database, get_database
from bson import ObjectId
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from bson.errors import InvalidId

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Cấu hình mã hóa mật khẩu
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng bcrypt"""
    try:
        hashed = pwd_context.hash(password)
        logger.debug(f"Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu có khớp với mật khẩu đã mã hóa không"""
    try:
        logger.debug("Attempting to verify password")
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Password verification result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Tạo access token với JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_user_by_username(username: str) -> Optional[UserInDB]:
    """Lấy thông tin user từ database theo username"""
    try:
        users_collection = await Database.get_collection("users")
        user_dict = await users_collection.find_one({"username": username})
        
        if user_dict is not None:
            logger.debug(f"Found user in database: {username}")
            # Chuyển đổi _id thành string
            user_dict["id"] = str(user_dict.pop("_id"))
            
            # Chuyển đổi class_id từ ObjectId sang string nếu có
            if "class_id" in user_dict and isinstance(user_dict["class_id"], ObjectId):
                user_dict["class_id"] = str(user_dict["class_id"])
                
            # Chuyển đổi managed_classes từ ObjectId sang string nếu có
            if "managed_classes" in user_dict and user_dict["managed_classes"]:
                user_dict["managed_classes"] = [str(class_id) for class_id in user_dict["managed_classes"]]
                
            return UserInDB(**user_dict)
            
        logger.debug(f"User not found: {username}")
        return None
    except Exception as e:
        logger.error(f"Error in get_user_by_username: {str(e)}")
        return None

async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Xác thực user với username và password"""
    try:
        logger.debug(f"Attempting to authenticate user: {username}")
        user = await get_user_by_username(username)
        
        if user is None:
            logger.debug(f"User not found: {username}")
            return None
            
        logger.debug("User found, verifying password")
        if not verify_password(password, user.hashed_password):
            logger.debug("Password verification failed")
            return None
            
        # Kiểm tra trạng thái tài khoản
        if user.status == "pending":
            logger.debug("User account is pending approval")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đang chờ được duyệt"
            )
        elif user.status == "blocked":
            logger.debug("User account is blocked")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đã bị khóa"
            )
            
        logger.debug("Authentication successful")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in authenticate_user: {str(e)}")
        return None

async def update_last_login(user_id: str) -> None:
    """Cập nhật thời gian đăng nhập cuối cùng"""
    try:
        users_collection = await Database.get_collection("users")
        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login": datetime.utcnow()}}
        )
    except Exception as e:
        logger.error(f"Error in update_last_login: {str(e)}")

def create_user_response(user: UserInDB) -> UserResponse:
    """Tạo response cho user"""
    try:
        # Chuyển đổi user thành dict
        user_dict = user.dict()
        
        # Thêm các trường mặc định nếu không tồn tại
        if "status" not in user_dict:
            user_dict["status"] = "active"
        
        if "last_login" not in user_dict:
            user_dict["last_login"] = None
            
        # Tạo UserResponse từ dict
        return UserResponse(**user_dict)
    except Exception as e:
        logger.error(f"Error in create_user_response: {str(e)}")
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = await get_database()
    user = await db.users.find_one({"username": username})
    
    if user is None:
        raise credentials_exception
        
    # Convert ObjectId to string if present
    if user.get('class_id'):
        user['class_id'] = str(user['class_id'])
    
    return UserInDB(**user)
