from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routes import auth_routes, admin_routes, excel_routes, approver_routes, inspector_routes, researcher_routes, class_routes
from config import settings
from database.mongodb import Database
import logging
import traceback
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from services.auth_service import get_user_by_username
import jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Research Management API",
    description="API for managing research projects",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response

# Add middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

async def get_current_user_from_token(request: Request):
    try:
        # Thử lấy token từ cookie
        token = request.cookies.get("access_token")
        if not token:
            # Nếu không có trong cookie, thử lấy từ header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                logger.debug("No token found in cookie or header")
                return None

        # Giải mã token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            logger.debug("No username in token payload")
            return None
            
        # Lấy thông tin user
        user = await get_user_by_username(username)
        if user:
            logger.debug(f"User authenticated: {username}, role: {user.role}")
            return user
        logger.debug(f"User not found: {username}")
        return None
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except jwt.JWTError as e:
        logger.debug(f"JWT validation error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        return None

@app.on_event("startup")
async def startup_db_client():
    try:
        await Database.connect_to_mongo()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Could not connect to the database: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db_client():
    await Database.close_mongo_connection()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request, user = Depends(get_current_user_from_token)):
    if not user:
        return RedirectResponse(url="/", status_code=303)
    if user.role == "admin":
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse("home.html", {"request": request, "user": user})

@app.get("/inspector")
async def inspector_dashboard(request: Request, user = Depends(get_current_user_from_token)):
    if not user:
        logger.debug("No authenticated user found")
        return RedirectResponse(url="/", status_code=303)
    if user.role != "inspector":
        logger.debug(f"User {user.username} is not inspector")
        return RedirectResponse(url="/home", status_code=303)
    logger.debug(f"Inspector access granted to {user.username}")
    return templates.TemplateResponse("inspector_dashboard.html", {"request": request, "user": user})

@app.get("/approver")
async def approver_dashboard(request: Request, user = Depends(get_current_user_from_token)):
    if not user:
        logger.debug("No authenticated user found")
        return RedirectResponse(url="/", status_code=303)
    if user.role != "approver":
        logger.debug(f"User {user.username} is not approver")
        return RedirectResponse(url="/home", status_code=303)
    logger.debug(f"Approver access granted to {user.username}")
    return templates.TemplateResponse("approver_dashboard.html", {"request": request, "user": user})

@app.get("/researcher")
async def researcher_dashboard(request: Request, user = Depends(get_current_user_from_token)):
    if not user:
        logger.debug("No authenticated user found")
        return RedirectResponse(url="/", status_code=303)
    if user.role != "researcher":
        logger.debug(f"User {user.username} is not researcher")
        return RedirectResponse(url="/home", status_code=303)
    logger.debug(f"Researcher access granted to {user.username}")
    return templates.TemplateResponse("researcher_dashboard.html", {"request": request, "user": user})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, user = Depends(get_current_user_from_token)):
    if not user:
        logger.debug("No authenticated user found")
        return RedirectResponse(url="/", status_code=303)
    if user.role != "admin":
        logger.debug(f"User {user.username} is not admin")
        return RedirectResponse(url="/home", status_code=303)
    logger.debug(f"Admin access granted to {user.username}")
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "user": user})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/auth/logout")
async def logout():
    return {"message": "Đăng xuất thành công"}

# Include routers
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(excel_routes.router)
app.include_router(approver_routes.router)
app.include_router(inspector_routes.router)
app.include_router(researcher_routes.router)
app.include_router(class_routes.router)  # Router không yêu cầu xác thực
app.include_router(class_routes.router_with_auth)  # Router yêu cầu xác thực

# Add debug middleware
@app.middleware("http")
async def add_debug_header(request: Request, call_next):
    try:
        response = await call_next(request)
        response.headers["X-Debug-Path"] = request.url.path
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
