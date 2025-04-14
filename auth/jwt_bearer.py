from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from config import settings
import logging

logger = logging.getLogger(__name__)

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        # Thử lấy token từ cookie trước
        token = request.cookies.get("access_token")
        if token:
            logger.debug("Found token in cookie")
            if self.verify_jwt(token):
                return token
        
        # Nếu không có cookie hoặc cookie không hợp lệ, thử Authorization header
        try:
            credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
            if credentials:
                if not credentials.scheme == "Bearer":
                    raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
                if not self.verify_jwt(credentials.credentials):
                    raise HTTPException(status_code=403, detail="Invalid token or expired token.")
                logger.debug("Found valid token in Authorization header")
                return credentials.credentials
        except Exception as e:
            logger.debug(f"Error checking Authorization header: {str(e)}")
            pass

        raise HTTPException(status_code=403, detail="Invalid authorization. Please login again.")

    def verify_jwt(self, jwtoken: str) -> bool:
        try:
            payload = jwt.decode(jwtoken, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return True if payload else False
        except Exception as e:
            logger.debug(f"Error verifying JWT: {str(e)}")
            return False 