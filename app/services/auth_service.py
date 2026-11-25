from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token
from app.core.security import hash_password, verify_password, create_access_token


class AuthService:
    @staticmethod
    def register_customer(db: Session, data: UserRegister) -> User:
        existing_user = db.query(User).filter(User.email == data.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{data.email}' already exists",
            )

        new_user = User(
            email=data.email.lower(),
            full_name=data.full_name.strip(),
            password_hash=hash_password(data.password),
            role="customer",
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def login(db: Session, data: UserLogin) -> Token:
        user = db.query(User).filter(User.email == data.email.lower()).first()
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(data={"sub": str(user.id), "role": user.role, "email": user.email})
        return Token(access_token=token, token_type="bearer")


auth_service = AuthService()

