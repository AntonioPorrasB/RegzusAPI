from datetime import timedelta
from fastapi.responses import JSONResponse
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from database import get_db, User, UserCreate, UserResponse
from utils import create_access_token, get_password_hash, verify_password

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
session_router = APIRouter()

SECRET_KEY = "PB(7-/BN$qZShi'6.F#3>z46AW\r&H"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60 * 60

class LoginRequest(BaseModel):
    usuario: str
    contraseña: str

@session_router.post("/register", response_model=UserResponse, tags=['Session'])
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.usuario == user.usuario).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Nombre de usuario ya registrado")

    hashed_password = get_password_hash(user.contraseña)
    new_user = User(
        nombre=user.nombre,
        usuario=user.usuario,
        contraseña=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        nombre=new_user.nombre,
        usuario=new_user.usuario
    )

@session_router.post("/login", response_model=UserResponse, tags=['Session'])
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.usuario == request.usuario).first()
    if not user:
        raise HTTPException(status_code=400, detail="El usuario no existe")

    if not verify_password(request.contraseña, user.contraseña):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.usuario},
        expires_delta=access_token_expires
    )

    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "nombre": user.nombre,
                "usuario": user.usuario
            }
        }
    )
    response.set_cookie(
        key="token", 
        value=access_token,  # Puedes incluir el prefijo Bearer si es necesario
        httponly=False,  # HttpOnly para que solo sea accesible por el servidor
        expires=7 * 24 * 60 * 60,  # Tiempo de expiración en segundos
        samesite="Lax",  # Ajusta SameSite según tus necesidades ('Strict', 'Lax', 'None')
        secure=False,  # Cambia esto a True si usas HTTPS
        domain="retzius-web.vercel.app",
    )

    return UserResponse(
        id=user.id,
        nombre=user.nombre,
        usuario=user.usuario
    )
