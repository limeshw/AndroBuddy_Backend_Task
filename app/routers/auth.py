from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Register a new customer account."""
    return auth_service.register_customer(db, data)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate and obtain a JWT bearer token."""
    return auth_service.login(db, data)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile details of currently authenticated user without sensitive fields."""
    return current_user

