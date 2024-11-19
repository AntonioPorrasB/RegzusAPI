from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import PasswordUpdateRequest, get_db, User, UserUpdate
from utils import get_user_by_username, get_password_hash, verify_password
from oauth import get_current_user

adm_users_router = APIRouter()


# Eliminar usuario
@adm_users_router.delete("/delete/{username}", tags=['AdmUsers'])
def delete_user(username: str, db: Session = Depends(get_db)):
    user = get_user_by_username(username, db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(user)
    db.commit()
    return {"detail": "Usuario eliminado exitosamente"}

# Actualizar usuario por ID
@adm_users_router.put("/update/me", tags=['AdmUsers'])
def update_user(updated_user: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if updated_user.nombre:
        user.nombre = updated_user.nombre
    if updated_user.usuario:
        user.usuario = updated_user.usuario
        
    print("Datos recibidos del cliente:", updated_user.dict())

    db.commit()
    return {"detail": "Usuario actualizado exitosamente"}

# Actualizar contraseña del usuario
@adm_users_router.put("/update_password", tags=['AdmUsers'])
def update_password(passwords: PasswordUpdateRequest, 
                    db: Session = Depends(get_db), 
                    current_user: User = Depends(get_current_user)):
    
    # Verificar si la contraseña actual es correcta
    if not verify_password(passwords.current_password, current_user.contraseña):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")

    # Verificar si la nueva contraseña y la confirmación coinciden
    if passwords.new_password != passwords.confirm_password:
        raise HTTPException(status_code=400, detail="Las nuevas contraseñas no coinciden")

    # Actualizar la contraseña
    current_user.contraseña = get_password_hash(passwords.new_password)
    db.commit()
    
    return {"detail": "Contraseña actualizada exitosamente"}
