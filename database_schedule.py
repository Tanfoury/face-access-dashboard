"""
database_schedule.py
====================
Nouveau modèle de Schedule pour école primaire.

Structure :
  - Un créneau = 1 heure fixe (8h-9h, 9h-10h, 10h-11h, 11h-12h, 13h-14h, 14h-15h)
  - Chaque créneau lie : 1 prof + 1 classe + 1 jour de la semaine
  - L'admin travaille toujours 8h-15h (pause 12h-13h) → géré automatiquement, pas besoin de schedule
  - Une classe peut avoir plusieurs profs le même jour (un par créneau/matière)

Tables ajoutées / modifiées :
  - Schedule  → supprimée et remplacée par TimeSlot
  - Subject   → nouvelle table pour les matières
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "school.db")

engine  = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base    = declarative_base()


# ---------------------------------------------------------------------------
# Modèles existants (inchangés)
# ---------------------------------------------------------------------------

class Student(Base):
    __tablename__ = "students"
    id         = Column(Integer, primary_key=True)
    student_id = Column(String, unique=True, nullable=False)
    name       = Column(String, nullable=False)
    grade      = Column(String)          # classe ex: "6A", ou fonction admin/prof
    category   = Column(String)          # "eleve" | "prof" | "admin"
    enrolled   = Column(Boolean, default=False)
    inside     = Column(Boolean, default=False)
    face_path  = Column(String)


class AccessLog(Base):
    __tablename__ = "access_logs"
    id         = Column(Integer, primary_key=True)
    student_id = Column(String)
    name       = Column(String)
    timestamp  = Column(DateTime, default=datetime.now)
    action     = Column(String)          # "ENTRY" | "EXIT"
    granted    = Column(Boolean, default=True)


# ---------------------------------------------------------------------------
# NOUVEAU : Matières
# ---------------------------------------------------------------------------

class Subject(Base):
    """
    Catalogue des matières enseignées dans l'école.
    Ex : Mathématiques, Français, Sciences, Arabe...
    """
    __tablename__ = "subjects"
    id   = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)   # "Mathématiques"
    code = Column(String, unique=True, nullable=False)   # "MATH"

    # Relation vers les créneaux
    slots = relationship("TimeSlot", back_populates="subject", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# NOUVEAU : Créneaux horaires (remplace Schedule)
# ---------------------------------------------------------------------------

# Créneaux fixes disponibles (hors pause 12h-13h)
CRENEAUX = [
    ("08:00", "09:00"),
    ("09:00", "10:00"),
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    # --- PAUSE 12:00-13:00 ---
    ("13:00", "14:00"),
    ("14:00", "15:00"),
]

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]


class TimeSlot(Base):
    """
    Un créneau horaire = 1 prof + 1 classe + 1 matière + 1 jour + heure début/fin.

    Contrainte d'unicité :
      - Un prof ne peut pas être dans 2 classes en même temps
        → unique sur (prof_name, day, start_time)
      - Une classe ne peut pas avoir 2 profs en même temps
        → unique sur (class_name, day, start_time)
    """
    __tablename__ = "time_slots"

    id         = Column(Integer, primary_key=True)
    day        = Column(String,  nullable=False)   # "Lundi" ... "Samedi"
    start_time = Column(String,  nullable=False)   # "08:00"
    end_time   = Column(String,  nullable=False)   # "09:00"
    class_name = Column(String,  nullable=False)   # "6A"
    prof_name  = Column(String,  nullable=False)   # nom du prof
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    subject = relationship("Subject", back_populates="slots")

    # Un prof ne peut pas avoir 2 cours en même temps
    __table_args__ = (
        UniqueConstraint("prof_name", "day", "start_time", name="uq_prof_slot"),
        UniqueConstraint("class_name", "day", "start_time", name="uq_class_slot"),
    )

    def __repr__(self):
        return (
            f"<TimeSlot {self.day} {self.start_time}-{self.end_time} "
            f"| {self.class_name} | {self.prof_name}>"
        )


# ---------------------------------------------------------------------------
# Ancienne table Schedule (conservée pour compatibilité si nécessaire)
# ---------------------------------------------------------------------------

class Schedule(Base):
    """
    Ancienne table conservée pour rétrocompatibilité.
    Préférer TimeSlot pour les nouvelles fonctions.
    """
    __tablename__ = "schedules"
    id          = Column(Integer, primary_key=True)
    target_type = Column(String)    # "classe" | "prof"
    target_id   = Column(String)
    day_of_week = Column(String)
    morning     = Column(Boolean, default=True)
    afternoon   = Column(Boolean, default=True)


# ---------------------------------------------------------------------------
# Fonctions CRUD
# ---------------------------------------------------------------------------

def init_db():
    """Crée toutes les tables si elles n'existent pas."""
    Base.metadata.create_all(engine)


def get_all_subjects():
    session = Session()
    subjects = session.query(Subject).order_by(Subject.name).all()
    session.close()
    return subjects


def add_subject(name: str, code: str):
    """Ajoute une matière. Retourne (subject, created: bool)."""
    session = Session()
    existing = session.query(Subject).filter_by(code=code.upper()).first()
    if existing:
        session.close()
        return existing, False
    subj = Subject(name=name, code=code.upper())
    session.add(subj)
    session.commit()
    session.refresh(subj)
    session.close()
    return subj, True


def save_time_slot(day: str, start_time: str, end_time: str,
                   class_name: str, prof_name: str, subject_id: int = None):
    """
    Crée ou met à jour un créneau.
    Si un créneau existe déjà pour (classe, jour, heure), il est mis à jour.
    Retourne (slot, error_message).
    """
    session = Session()
    try:
        # Vérifier conflit prof
        conflict_prof = session.query(TimeSlot).filter_by(
            prof_name=prof_name, day=day, start_time=start_time
        ).filter(TimeSlot.class_name != class_name).first()

        if conflict_prof:
            return None, f"⚠️ {prof_name} est déjà assigné à la classe {conflict_prof.class_name} à {start_time} le {day}."

        # Chercher s'il existe déjà pour cette classe/jour/heure
        existing = session.query(TimeSlot).filter_by(
            class_name=class_name, day=day, start_time=start_time
        ).first()

        if existing:
            existing.prof_name  = prof_name
            existing.end_time   = end_time
            existing.subject_id = subject_id
            session.commit()
            return existing, None
        else:
            slot = TimeSlot(
                day=day, start_time=start_time, end_time=end_time,
                class_name=class_name, prof_name=prof_name, subject_id=subject_id
            )
            session.add(slot)
            session.commit()
            return slot, None
    except Exception as e:
        session.rollback()
        return None, str(e)
    finally:
        session.close()


def delete_time_slot(slot_id: int):
    """Supprime un créneau par ID."""
    session = Session()
    slot = session.query(TimeSlot).filter_by(id=slot_id).first()
    if slot:
        session.delete(slot)
        session.commit()
    session.close()


def get_time_slots(day: str = None, class_name: str = None, prof_name: str = None):
    """Récupère les créneaux avec filtres optionnels."""
    session = Session()
    q = session.query(TimeSlot)
    if day:
        q = q.filter_by(day=day)
    if class_name:
        q = q.filter_by(class_name=class_name)
    if prof_name:
        q = q.filter_by(prof_name=prof_name)
    slots = q.order_by(TimeSlot.day, TimeSlot.start_time).all()
    # Détacher les objets de la session
    result = []
    for s in slots:
        result.append({
            "id":         s.id,
            "day":        s.day,
            "start_time": s.start_time,
            "end_time":   s.end_time,
            "class_name": s.class_name,
            "prof_name":  s.prof_name,
            "subject":    s.subject.name if s.subject else "-",
        })
    session.close()
    return result


def get_schedule_grid(class_name: str = None, prof_name: str = None):
    """
    Retourne l'emploi du temps sous forme de grille :
    { jour: { "08:00": {slot_info} } }
    """
    slots = get_time_slots(class_name=class_name, prof_name=prof_name)
    grid = {jour: {} for jour in JOURS}
    for s in slots:
        grid[s["day"]][s["start_time"]] = s
    return grid


# ---------------------------------------------------------------------------
# Fonctions héritées (compatibilité avec dash existant)
# ---------------------------------------------------------------------------

def save_schedule(target_type, target_id, day_of_week, morning, afternoon):
    session = Session()
    existing = session.query(Schedule).filter_by(
        target_type=target_type, target_id=target_id, day_of_week=day_of_week
    ).first()
    if existing:
        existing.morning   = morning
        existing.afternoon = afternoon
    else:
        session.add(Schedule(
            target_type=target_type, target_id=target_id,
            day_of_week=day_of_week, morning=morning, afternoon=afternoon
        ))
    session.commit()
    session.close()


def get_schedules():
    session = Session()
    schedules = session.query(Schedule).all()
    session.close()
    return schedules
