"""
Authentication API routes
"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.models import UserCreate
from core.config import Config
from core.auth.jwt_handler import create_jwt_token
from core.templates.fallbacks import get_register_html, get_login_html

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    try:
        return templates.TemplateResponse("register.html", {"request": request})
    except:
        # Fallback if template not found
        return HTMLResponse(content=get_register_html())


@router.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None)
):
    """Register new user"""
    try:
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            full_name=full_name if full_name else None
        )
        
        db = request.app.state.db
        user = await db.create_user(user_data)
        
        # Create JWT token
        token = create_jwt_token(str(user["_id"]))
        print(f"✅ Registration: Created JWT token for user: {user['email']}")
        
        # Redirect to dashboard with cookie
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key=Config.COOKIE_NAME,
            value=token,
            max_age=Config.SESSION_EXPIRE_HOURS * 3600,
            httponly=True,
            secure=Config.COOKIE_SECURE,
            samesite="strict" if Config.IS_PRODUCTION else "lax"
        )
        print(f"🍪 Registration: Set cookie - Name: {Config.COOKIE_NAME}, Secure: {Config.COOKIE_SECURE}, Production: {Config.IS_PRODUCTION}")
        
        return response
        
    except HTTPException as e:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": e.detail
        }, status_code=e.status_code)
    except Exception as e:
        print(f"Registration error: {e}")
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Registration failed. Please try again."
        }, status_code=500)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    try:
        return templates.TemplateResponse("login.html", {"request": request})
    except:
        # Fallback if template not found
        return HTMLResponse(content=get_login_html())


@router.post("/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Login user"""
    try:
        db = request.app.state.db
        user = await db.authenticate_user(email, password)
        
        if not user:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid email or password"
            }, status_code=401)
        
        # Create JWT token
        token = create_jwt_token(str(user["_id"]))
        print(f"✅ Login: Created JWT token for user: {user['email']}")
        
        # Redirect to dashboard with cookie
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key=Config.COOKIE_NAME,
            value=token,
            max_age=Config.SESSION_EXPIRE_HOURS * 3600,
            httponly=True,
            secure=Config.COOKIE_SECURE,
            samesite="strict" if Config.IS_PRODUCTION else "lax"
        )
        print(f"🍪 Login: Set cookie - Name: {Config.COOKIE_NAME}, Secure: {Config.COOKIE_SECURE}, Production: {Config.IS_PRODUCTION}")
        
        return response
        
    except Exception as e:
        print(f"Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Login failed. Please try again."
        }, status_code=500)


@router.post("/logout")
async def logout_user():
    """Logout user"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=Config.COOKIE_NAME)
    return response