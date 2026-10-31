from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_admin, get_current_user
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import StaffCreate, UserOut, ProfileUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserOut, status_code=201)
def create_staff_user(
    payload: StaffCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin-only: create a staff or admin user."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    return q.order_by(User.created_at.desc()).all()


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

