from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os
import requests
from database import User

# Configuración para la codificación de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Clave secreta y algoritmo para JWT
SECRET_KEY = os.getenv("SECRET_KEY", "PB(7-/BN$qZShi'6.F#3>z46AW\r&H")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60  # 7 días

# Función para obtener el usuario por nombre de usuario
def get_user_by_username(usuario: str, db):
    return db.query(User).filter(User.usuario == usuario).first()

# Función para hashear contraseñas
def get_password_hash(contraseña: str):
    return pwd_context.hash(contraseña)

# Verificar contraseña
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# Generar token de acceso
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Verificar token de JWT
def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario: str = payload.get("sub")
        if usuario is None:
            raise credentials_exception
        return usuario
    except jwt.JWTError:
        raise credentials_exception