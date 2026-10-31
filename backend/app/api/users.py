import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_admin, require_staff, get_current_user
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import StaffCreate, UserOut
from app.utils.pagination import Page, paged

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
    page: Page = Depends(paged(100)),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    return page.apply(q, User.created_at.desc())


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/customers", response_model=List[UserOut])
def list_customers(
    search: Optional[str] = Query(None, description="Matches name, email or company"),
    page: Page = Depends(paged(50)),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Customer picker for the team; staff cannot use the full user list."""
    q = db.query(User).filter(User.role == UserRole.customer, User.is_active.is_(True))
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(User.full_name.ilike(term), User.email.ilike(term), User.company_name.ilike(term))
        )
    return page.apply(q, User.email)


def _get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return _get_user(db, user_id)


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(400, "You cannot deactivate your own account")
    user = _get_user(db, user_id)
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/activate", response_model=UserOut)
def activate_user(user_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = _get_user(db, user_id)
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
