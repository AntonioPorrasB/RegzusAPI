import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import jwt  # Asegúrate de tener jwt importado
import logging
from utils import verify_token  # Asegúrate de importar tu función de verificación
# Importar las rutas
from session import session_router
from oauth import oauth_router
from crud import crud_router
from fastapi.staticfiles import StaticFiles
from adm_users import adm_users_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://retzius-web.vercel.app",
        "https://regzusapi.onrender.com",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.title = "Asistencia Automatica"
app.version = "2.0.0"

# Middleware para verificar la sesión
@app.middleware("http")
async def verify_session(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Excluye las rutas de login y registro, docs, openapi.json
    if request.url.path in ["/login", "/register", "/token", "/docs", "/openapi.json"]:
        return await call_next(request)

    # Intenta obtener el token primero de las cookies
    token = request.cookies.get("token")
    print(f"Token recibido de la cookie: {token}")

    # Si no hay token en las cookies, intenta obtenerlo del header Authorization
    if not token:
        auth_header = request.headers.get("Authorization")
        print(f"Authorization header recibido: {auth_header}")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]  # Obtiene el token después de 'Bearer'

    print(f"Token final después de verificar cookie y header: {token}")

    # Si no hay token ni en cookies ni en headers, lanza una excepción
    if not token:
        raise HTTPException(status_code=401, detail="No se ha proporcionado el token de acceso.")

    # Verifica el token usando tu función `verify_token`
    try:
        username = verify_token(token, HTTPException(status_code=401, detail="Token no válido."))
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token no válido.")

    # Si la verificación es exitosa, continúa con la solicitud
    response = await call_next(request)
    return response

# Ruta principal (home)
@app.get("/", tags=['Home'])
async def read_root():
    return {"message": "Welcome to the Asistencia Automatica API!"}

# Incluir las rutas
app.include_router(session_router)
app.include_router(oauth_router)
app.include_router(crud_router)
app.include_router(adm_users_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
