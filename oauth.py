from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from database import get_db, User
from utils import verify_password, create_access_token, verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth_router = APIRouter()

SECRET_KEY = ""
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60 * 60

@oauth_router.post("/token", tags=['OAUTH&JWT'])
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.usuario == form_data.username).first()
    if not user or not verify_password(form_data.password, user.contraseña):
        raise HTTPException(
            status_code=400,
            detail="Nombre de usuario o contraseña incorrectos"
        )

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
    
    return response

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"}
    )
    username = verify_token(token, credentials_exception)
    user = db.query(User).filter(User.usuario == username).first()
    if user is None:
        raise credentials_exception
    return user

@oauth_router.get("/users/me", tags=['OAUTH&JWT'])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "usuario": current_user.usuario
    }
