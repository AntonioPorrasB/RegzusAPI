from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File,Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Date
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import cloudinary
import cloudinary.uploader
from database import (
    EnrollmentRequest, User, get_db, Student, Subject, Enrollment, Attendance,
    StudentCreate, StudentResponse, SubjectCreate, SubjectResponse,
    EnrollmentCreate, AttendanceCreate, AttendanceResponse, StudentEnrollmentResponse
)
from oauth import get_current_user

#Falta poner porcentaje de asistencia de los alumnos y un indicador de si la materia esta activa.

crud_router = APIRouter()



class CloudinaryPhotoManager:
    def __init__(self):
        cloudinary.config(
           cloud_name='',
           api_key='',
           api_secret=''
        )
        self.base_folder = "alumnos"  # Carpeta base para todos los alumnos
    
    def get_subject_folder(self, teacher_name: str, subject_name: str) -> str:
        """Genera el path de la carpeta para una materia específica"""
        return f"{teacher_name}_{subject_name}"
    
    async def upload_student_photo(
        self,
        photo: UploadFile,
        numero_control: str
    ) -> str:
        """Sube la foto inicial del estudiante a la carpeta general de alumnos"""
        if not photo.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="El archivo debe ser una imagen"
            )
        
        try:
            result = cloudinary.uploader.upload(
                photo.file,
                folder=self.base_folder,
                public_id=numero_control,
                overwrite=True,
                format="png"
            )
            return result['secure_url']
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al subir la imagen: {str(e)}"
            )
    
    async def copy_to_subject_folder(
        self,
        numero_control: str,
        teacher_name: str,
        subject_name: str
    ) -> str:
        """Copia la foto del estudiante a la carpeta de la materia"""
        subject_folder = self.get_subject_folder(teacher_name, subject_name)
        try:
            # Obtener la imagen de la carpeta general
            source_url = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/image/upload/v1/{self.base_folder}/{numero_control}"
            
            # Copiar a la carpeta de la materia
            result = cloudinary.uploader.upload(
                source_url,
                folder=f"{self.base_folder}/{subject_folder}",
                public_id=numero_control,
                overwrite=True,
                format="png"
            )
            return result['secure_url']
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al copiar la imagen: {str(e)}"
            )
    
    async def delete_from_subject(
        self,
        numero_control: str,
        teacher_name: str,
        subject_name: str
    ):
        """Elimina la foto de un estudiante de una materia específica"""
        try:
            subject_folder = self.get_subject_folder(teacher_name, subject_name)
            cloudinary.uploader.destroy(
                f"{self.base_folder}/{subject_folder}/{numero_control}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al eliminar la imagen: {str(e)}"
            )

    async def delete_student_photo(self, numero_control: str):
        """Elimina la foto del estudiante de la carpeta general"""
        try:
            cloudinary.uploader.destroy(f"{self.base_folder}/{numero_control}")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al eliminar la imagen: {str(e)}"
            )
            
        

# Estudiantes
@crud_router.post("/students/", response_model=StudentResponse, tags=['Students'])
async def create_student(
    nombre: str = Form(...),
    apellido: str = Form(...),
    numero_control: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Verificar si el estudiante ya existe
    existing_student = db.query(Student).filter(
        Student.numero_control == numero_control
    ).first()
    if existing_student:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un estudiante con ese número de control"
        )
    
    # Inicializar el gestor de fotos
    photo_manager = CloudinaryPhotoManager()
    
    try:
        # Subir la foto a la carpeta general de alumnos
        foto_url = await photo_manager.upload_student_photo(photo, numero_control)
        
        # Crear el estudiante en la base de datos
        new_student = Student(
            nombre=nombre,
            apellido=apellido,
            numero_control=numero_control,
            foto_url=foto_url
        )
        db.add(new_student)
        db.commit()
        db.refresh(new_student)
        
        return new_student
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear el estudiante: {str(e)}"
        )

@crud_router.get("/students/", response_model=List[StudentResponse], tags=['Students'])
async def get_students(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    students = db.query(Student).offset(skip).limit(limit).all()
    return students

@crud_router.get("/students/{student_id}", response_model=StudentResponse, tags=['Students'])
async def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return student

@crud_router.get("/students/by_control/{numero_control}", response_model=StudentResponse, tags=['Students'])
async def get_student_by_control(
    numero_control: str, 
    db: Session = Depends(get_db)
):
    # Buscar al estudiante por número de control
    student = db.query(Student).filter(Student.numero_control == numero_control).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return student

@crud_router.put("/students/{student_id}", response_model=StudentResponse, tags=['Students'])
async def update_student(
    student_id: int,
    nombre: str = None,
    apellido: str = None,
    numero_control: str = None,
    photo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    if nombre:
        student.nombre = nombre
    if apellido:
        student.apellido = apellido
    if numero_control:
        # Si se cambia el número de control, hay que actualizar las fotos
        old_numero_control = student.numero_control
        student.numero_control = numero_control
    
    photo_manager = CloudinaryPhotoManager()
    
    try:
        if photo:
            # Eliminar la foto anterior de Cloudinary
            await photo_manager.delete_student_photo(old_numero_control if numero_control else student.numero_control)
            
            # Subir la nueva foto
            new_foto_url = await photo_manager.upload_student_photo(
                photo,
                numero_control if numero_control else student.numero_control
            )
            student.foto_url = new_foto_url
            
            # Si el estudiante está matriculado en materias, actualizar las fotos en esas materias
            enrollments = db.query(Enrollment).filter(Enrollment.id_alumno == student_id).all()
            for enrollment in enrollments:
                subject = db.query(Subject).filter(Subject.id == enrollment.id_materia).first()
                teacher = db.query(User).filter(User.id == subject.id_maestro).first()
                
                # Eliminar la foto anterior de la carpeta de la materia
                await photo_manager.delete_from_subject(
                    old_numero_control if numero_control else student.numero_control,
                    teacher.nombre,
                    subject.nombre
                )
                
                # Copiar la nueva foto a la carpeta de la materia
                new_subject_photo_url = await photo_manager.copy_to_subject_folder(
                    numero_control if numero_control else student.numero_control,
                    teacher.nombre,
                    subject.nombre
                )
                enrollment.foto_url = new_subject_photo_url
        
        db.commit()
        db.refresh(student)
        return student
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el estudiante: {str(e)}"
        )

@crud_router.delete("/students/{student_id}", tags=['Students'])
async def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    # Eliminar la foto si existe
    if student.foto_url:
        photo_path = os.path.join("static", student.foto_url.lstrip("/static/"))
        if os.path.exists(photo_path):
            os.remove(photo_path)
    
    db.delete(student)
    db.commit()
    return {"message": "Estudiante eliminado"}

# Materias
@crud_router.post("/subjects/", response_model=SubjectResponse, tags=['Subjects'])
async def create_subject(
    subject: SubjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Crear la materia usando los datos del usuario autenticado
    subject_data = subject.dict()
    subject_data["id_maestro"] = current_user.id  # Sobrescribir el id_maestro con el del usuario actual
    
    new_subject = Subject(**subject_data)
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    return new_subject


@crud_router.get("/subjects/{subject_id}/enrollments", response_model=List[StudentEnrollmentResponse], tags=['Enrollments'])
async def get_subject_enrollments(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que la materia pertenezca al profesor actual
    subject = db.query(Subject)\
        .filter(
            Subject.id == subject_id,
            Subject.id_maestro == current_user.id
        ).first()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    # Obtener todos los estudiantes matriculados en la materia
    enrollments = db.query(Enrollment)\
        .join(Student, Enrollment.id_alumno == Student.id)\
        .filter(Enrollment.id_materia == subject_id)\
        .all()
    
    # Mapear los resultados para incluir los detalles del estudiante
    enrollment_details = [{
        "numero_control": enrollment.student.numero_control,
        "nombre": enrollment.student.nombre,
        "apellido": enrollment.student.apellido
    } for enrollment in enrollments]
    
    return enrollment_details

@crud_router.get("/subjects/", response_model=List[SubjectResponse], tags=['Subjects'])
async def get_subjects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Obtener solo las materias del profesor actual
    subjects = db.query(Subject)\
        .filter(Subject.id_maestro == current_user.id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    return subjects

@crud_router.get("/subjects/{subject_id}", response_model=SubjectResponse, tags=['Subjects'])
async def get_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que la materia pertenezca al profesor actual
    subject = db.query(Subject)\
        .filter(
            Subject.id == subject_id,
            Subject.id_maestro == current_user.id
        ).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    return subject

@crud_router.get("/students/", response_model=List[StudentResponse], tags=['Students'])
async def get_students(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Obtener los IDs de las materias del profesor
    teacher_subjects = db.query(Subject.id)\
        .filter(Subject.id_maestro == current_user.id)\
        .subquery()
    
    # Obtener los estudiantes matriculados en las materias del profesor
    students = db.query(Student)\
        .join(Enrollment, Student.id == Enrollment.id_alumno)\
        .filter(Enrollment.id_materia.in_(teacher_subjects))\
        .distinct()\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return students

@crud_router.get("/students/{student_id}", response_model=StudentResponse, tags=['Students'])
async def get_student(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que el estudiante esté matriculado en alguna materia del profesor
    student = db.query(Student)\
        .join(Enrollment, Student.id == Enrollment.id_alumno)\
        .join(Subject, Enrollment.id_materia == Subject.id)\
        .filter(
            Student.id == student_id,
            Subject.id_maestro == current_user.id
        ).first()
    
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return student

@crud_router.put("/subjects/{subject_id}", response_model=SubjectResponse, tags=['Subjects'])
async def update_subject(
    subject_id: int,
    subject_update: SubjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que la materia pertenezca al profesor actual
    subject = db.query(Subject)\
        .filter(
            Subject.id == subject_id,
            Subject.id_maestro == current_user.id
        ).first()
    
    if subject is None:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    # Mantener el id_maestro original
    update_data = subject_update.dict(exclude={'id_maestro'})
    for key, value in update_data.items():
        setattr(subject, key, value)
    
    db.commit()
    db.refresh(subject)
    return subject

@crud_router.delete("/subjects/{subject_id}", tags=['Subjects'])
async def delete_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que la materia pertenezca al profesor actual
    subject = db.query(Subject)\
        .filter(
            Subject.id == subject_id,
            Subject.id_maestro == current_user.id
        ).first()
    
    if subject is None:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    db.delete(subject)
    db.commit()
    return {"message": "Materia eliminada"}

# Matrículas
# Endpoints para matrículas
@crud_router.post("/subjects/{subject_id}/enrollments/", tags=['Enrollments'])
async def create_enrollment(
    subject_id: int,
    enrollment: EnrollmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student_id = enrollment.student_id
    
    # Verificaciones iniciales
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.id_maestro == current_user.id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.id_alumno == student_id,
        Enrollment.id_materia == subject_id
    ).first()
    if existing_enrollment:
        raise HTTPException(
            status_code=400,
            detail="El estudiante ya está matriculado en esta materia"
        )
    
    photo_manager = CloudinaryPhotoManager()
    
    try:
        # Copiar la foto a la carpeta de la materia
        subject_photo_url = await photo_manager.copy_to_subject_folder(
            student.numero_control,
            current_user.nombre,
            subject.nombre
        )
        
        # Crear la matrícula
        new_enrollment = Enrollment(
            id_alumno=student_id,
            id_materia=subject_id,
        )
        db.add(new_enrollment)
        db.commit()
        db.refresh(new_enrollment)
        
        return new_enrollment
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la matrícula: {str(e)}"
        )

@crud_router.get("/subjects/{subject_id}/enrollments/", tags=['Enrollments'])
async def get_subject_enrollments(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que la materia pertenezca al profesor actual
    subject = db.query(Subject)\
        .filter(
            Subject.id == subject_id,
            Subject.id_maestro == current_user.id
        ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    # Obtener los estudiantes matriculados en esta materia
    enrolled_students = db.query(Student)\
        .join(Enrollment, Student.id == Enrollment.id_alumno)\
        .filter(Enrollment.id_materia == subject_id)\
        .all()
    
    return enrolled_students

@crud_router.delete("/subjects/{subject_id}/enrollments/{student_id}", tags=['Enrollments'])
async def delete_enrollment(
    subject_id: int,
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificaciones
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.id_maestro == current_user.id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    enrollment = db.query(Enrollment).filter(
        Enrollment.id_materia == subject_id,
        Enrollment.id_alumno == student_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
    
    photo_manager = CloudinaryPhotoManager()
    
    try:
        # Eliminar la foto de la carpeta de la materia
        await photo_manager.delete_from_subject(
            student.numero_control,
            current_user.nombre,
            subject.nombre
        )
        
        # Eliminar la matrícula
        db.delete(enrollment)
        db.commit()
        
        return {"message": "Matrícula y foto eliminadas correctamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la matrícula: {str(e)}"
        )

# Endpoints para asistencias
@crud_router.post("/subjects/{subject_id}/attendance/", response_model=List[AttendanceResponse], tags=['Attendance'])
async def create_attendance(
    subject_id: int,
    attendance_data: List[dict],  # Lista de {student_id: int, presente: bool}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que la materia pertenezca al profesor actual
    subject = db.query(Subject)\
        .filter(
            Subject.id == subject_id,
            Subject.id_maestro == current_user.id
        ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    # Obtener todas las matrículas de la materia con información de alumno
    enrollments = db.query(Enrollment)\
        .filter(Enrollment.id_materia == subject_id)\
        .all()
    
    attendance_records = []
    current_date = datetime.now().date()
    
    # Verificar si ya existe registro de asistencia para hoy
    existing_attendance = db.query(Attendance)\
        .join(Enrollment)\
        .filter(
            Enrollment.id_materia == subject_id,
            Attendance.fecha == current_date
        ).first()
    if existing_attendance:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un registro de asistencia para hoy"
        )
    
    # Crear registros de asistencia
    for data in attendance_data:
        student_id = data.get('student_id')
        
        # Buscar específicamente la matrícula para este alumno y esta materia
        enrollment = db.query(Enrollment)\
            .filter(
                Enrollment.id_alumno == student_id,
                Enrollment.id_materia == subject_id
            ).first()
        
        if not enrollment:
            continue  # Ignorar estudiantes no matriculados
            
        attendance = Attendance(
            fecha=current_date,
            presente=data.get('presente', False),
            id_matricula=enrollment.id  # Usar el id de la matrícula encontrada
        )
        db.add(attendance)
        attendance_records.append(attendance)
    
    db.commit()
    for record in attendance_records:
        db.refresh(record)
    
    return attendance_records

@crud_router.get("/subjects/{subject_id}/attendance/", tags=['Attendance'])
async def get_subject_attendance(
    subject_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar que la materia pertenezca al profesor actual
    subject = db.query(Subject)\
        .filter(
            Subject.id == subject_id,
            Subject.id_maestro == current_user.id
        ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    # Construir la consulta base
    query = db.query(
        Student.id,
        Student.nombre,
        Student.apellido,
        Attendance.fecha,
        Attendance.presente
    )\
    .join(Enrollment, Student.id == Enrollment.id_alumno)\
    .join(Attendance, Enrollment.id == Attendance.id_matricula)\
    .filter(Enrollment.id_materia == subject_id)
    
    # Aplicar filtros de fecha si se proporcionan
    if start_date:
        query = query.filter(Attendance.fecha >= start_date)
    if end_date:
        query = query.filter(Attendance.fecha <= end_date)
    
    # Ordenar por fecha y nombre del estudiante
    attendance_records = query.order_by(Attendance.fecha, Student.apellido, Student.nombre).all()
    
    # Organizar los resultados
    results = []
    for student_id, nombre, apellido, fecha, presente in attendance_records:
        results.append({
            "student_id": student_id,
            "nombre": nombre,
            "apellido": apellido,
            "fecha": fecha,
            "presente": presente
        })
    
    return results
