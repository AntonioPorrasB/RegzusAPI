from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional

#DATABASE_URL = "postgresql://postgres:R4kav3liYT@localhost/reconasist"
DATABASE_URL = "postgresql://regzusdb_calr_user:TdvWVRiJ0Zli8vGLiq8MNOgVwHiVxkff@dpg-csuef6jqf0us738qtg50-a.frankfurt-postgres.render.com/regzusdb_calr"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
# Crear la base de datos
Base.metadata.create_all(bind=engine)

# Crear una sesión de la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Función para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelos SQLAlchemy
class User(Base):
    __tablename__ = "usuarios"  # Cambiado para coincidir con el SQL

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)  # Ajustado según SQL
    usuario = Column(String(50), unique=True, nullable=False)  # Ajustado según SQL
    contraseña = Column(String(255), nullable=False)  # Ajustado según SQL
    
    # Relación con materias
    materias = relationship("Subject", back_populates="maestro")

class Student(Base):
    __tablename__ = "alumnos"  # Cambiado para coincidir con el SQL

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    numero_control = Column(String(20), unique=True, nullable=False)
    foto_url = Column(Text)

    # Relación con materias a través de matriculas
    materias = relationship("Subject", secondary="matriculas", back_populates="alumnos")

class Subject(Base):
    __tablename__ = "materias"  # Cambiado para coincidir con el SQL

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    horario = Column(String(50))
    descripcion = Column(Text)
    id_maestro = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"))

    # Relaciones
    maestro = relationship("User", back_populates="materias")
    alumnos = relationship("Student", secondary="matriculas", back_populates="materias")

class Enrollment(Base):
    __tablename__ = "matriculas"  # Cambiado para coincidir con el SQL

    id = Column(Integer, primary_key=True, index=True)
    id_alumno = Column(Integer, ForeignKey("alumnos.id", ondelete="CASCADE"))
    id_materia = Column(Integer, ForeignKey("materias.id", ondelete="CASCADE"))

    # Relación con asistencias
    asistencias = relationship("Attendance", back_populates="matricula")

class Attendance(Base):
    __tablename__ = "asistencias"  # Cambiado para coincidir con el SQL

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    presente = Column(Boolean, nullable=False)
    id_matricula = Column(Integer, ForeignKey("matriculas.id", ondelete="CASCADE"))

    # Relación con matrícula
    matricula = relationship("Enrollment", back_populates="asistencias")

# Modelos Pydantic
class UserBase(BaseModel):
    nombre: str
    usuario: str

class UserCreate(UserBase):
    nombre: str
    usuario: str
    contraseña: str

class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True

class StudentBase(BaseModel):
    nombre: str
    apellido: str
    numero_control: str
    foto_url: Optional[str] = None

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: int

    class Config:
        orm_mode = True

class SubjectBase(BaseModel):
    nombre: str
    horario: Optional[str] = None
    descripcion: Optional[str] = None
    id_maestro: Optional[int] = None
    
class SubjectCreate(SubjectBase):
    pass

class SubjectResponse(SubjectBase):
    id: int

    class Config:
        orm_mode = True

class EnrollmentCreate(BaseModel):
    id_alumno: int
    id_materia: int

class AttendanceCreate(BaseModel):
    fecha: date
    presente: bool
    id_matricula: int
    
    class Config:
        arbitrary_types_allowed = True

class AttendanceResponse(AttendanceCreate):
    id: int

    class Config:
        orm_mode = True
        
class EnrollmentRequest(BaseModel):
    student_id: int


class UserUpdate(BaseModel):
    nombre: str = None
    usuario: str = None
    
class PasswordUpdateRequest(BaseModel):
    current_password: str = Field(..., description="La contraseña actual del usuario")
    new_password: str = Field(..., description="La nueva contraseña del usuario")
    confirm_password: str = Field(..., description="Confirmación de la nueva contraseña")


class StudentEnrollmentResponse(BaseModel):
    numero_control: str
    nombre: str
    apellido: str

    class Config:
        orm_mode = True
