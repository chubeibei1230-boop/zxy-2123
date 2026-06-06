from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_current_user, require_role
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[schemas.UserResponse], dependencies=[Depends(require_role(["admin"]))])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@router.post("/users", response_model=schemas.UserResponse, dependencies=[Depends(require_role(["admin"]))])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if user.role not in ["admin", "employee_a", "employee_b"]:
        raise HTTPException(status_code=400, detail="无效的角色，可选值: admin, employee_a, employee_b")
    if user.department_id:
        dept = crud.get_department(db, user.department_id)
        if not dept:
            raise HTTPException(status_code=400, detail="部门不存在")
    return crud.create_user(db=db, user=user)


@router.put("/users/{user_id}", response_model=schemas.UserResponse, dependencies=[Depends(require_role(["admin"]))])
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    if user_update.role and user_update.role not in ["admin", "employee_a", "employee_b"]:
        raise HTTPException(status_code=400, detail="无效的角色，可选值: admin, employee_a, employee_b")
    if user_update.department_id:
        dept = crud.get_department(db, user_update.department_id)
        if not dept:
            raise HTTPException(status_code=400, detail="部门不存在")
    db_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return db_user
