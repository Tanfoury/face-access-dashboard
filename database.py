import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, date, timedelta

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# ============================================================
#  CONFIGURATION — Variables d'environnement obligatoires (.env)
# ============================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("⚠️ ERREUR : SUPABASE_URL et SUPABASE_KEY doivent être définis en variable d'environnement (ex: fichier .env)")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
#  CLASSES COMPATIBLES (pour ne pas casser dash.py)
# ============================================================
class Student:
    def __init__(self, data: dict):
        self.id         = data.get("id")
        self.student_id = data.get("student_id")
        self.name       = data.get("name")
        self.grade      = data.get("grade")
        self.category   = data.get("category", "eleve")
        self.enrolled   = data.get("enrolled", False)
        self.inside     = data.get("inside", False)

class AccessLog:
    def __init__(self, data: dict):
        self.id         = data.get("id")
        self.student_id = data.get("student_id")
        self.name       = data.get("name")
        self.granted    = data.get("granted", True)
        self.action     = data.get("action")
        ts = data.get("timestamp")
        if isinstance(ts, str):
            try:
                self.timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                self.timestamp = datetime.now()
        elif isinstance(ts, datetime):
            self.timestamp = ts
        else:
            self.timestamp = datetime.now()

class Schedule:
    def __init__(self, data: dict):
        self.id          = data.get("id")
        self.target_type = data.get("target_type")
        self.target_id   = data.get("target_id")
        self.day_of_week = data.get("day_of_week")
        self.morning     = data.get("morning", True)
        self.afternoon   = data.get("afternoon", True)


# ============================================================
#  SESSION COMPATIBLE (utilisé dans dash.py)
# ============================================================
class FakeSession:
    """Simule l'ancienne session SQLAlchemy pour dash.py"""

    def query(self, model):
        return FakeQuery(model)

    def close(self):
        pass

class FakeQuery:
    def __init__(self, model):
        self.model = model
        self._order = None

    def order_by(self, *args):
        self._order = "desc"
        return self

    def all(self):
        if self.model == Student:
            return get_all_students()
        elif self.model == AccessLog:
            return get_all_logs(self._order)
        elif self.model == Schedule:
            return get_schedules()
        return []

class Session:
    def __new__(cls):
        return FakeSession()


# ============================================================
#  INIT DB (tables déjà créées sur Supabase, juste un check)
# ============================================================
def init_db():
    print("[DB] Supabase connecté ✓")


# ============================================================
#  STUDENTS
# ============================================================
def get_all_students():
    res = supabase.table("students").select("*").execute()
    return [Student(r) for r in res.data]

def get_student_by_name(name: str):
    res = supabase.table("students").select("*").eq("name", name).execute()
    if res.data:
        return Student(res.data[0])
    return None

def get_student_by_id(student_id: str):
    res = supabase.table("students").select("*").eq("student_id", student_id).execute()
    if res.data:
        return Student(res.data[0])
    return None

def add_student(student_id: str, name: str, grade: str = "", category: str = "eleve"):
    supabase.table("students").upsert({
        "student_id": student_id,
        "name":       name,
        "grade":      grade,
        "category":   category,
        "enrolled":   True,
        "inside":     False
    }).execute()

def update_inside(name: str, inside: bool):
    supabase.table("students").update({"inside": inside}).eq("name", name).execute()

def is_inside(name: str) -> bool:
    res = supabase.table("students").select("inside").eq("name", name).execute()
    if res.data:
        return res.data[0].get("inside", False)
    return False

def daily_reset():
    """Remet inside=False pour tout le monde au démarrage."""
    supabase.table("students").update({"inside": False}).neq("id", 0).execute()
    print("[DB] Daily reset effectué ✓")


# ============================================================
#  ACCESS LOGS
# ============================================================
def get_all_logs(order=None):
    query = supabase.table("access_logs").select("*").order("timestamp", desc=True).limit(500)
    res   = query.execute()
    return [AccessLog(r) for r in res.data]

def log_access(student_id: str, name: str, granted: bool, action: str):
    supabase.table("access_logs").insert({
        "student_id": student_id,
        "name":       name,
        "granted":    granted,
        "action":     action,
        "timestamp":  datetime.utcnow().isoformat()
    }).execute()

def has_entry_today(name: str) -> bool:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()
    res = supabase.table("access_logs")\
        .select("id")\
        .eq("name", name)\
        .eq("action", "ENTRY")\
        .gte("timestamp", today_start)\
        .execute()
    return len(res.data) > 0

def has_exit_today(name: str) -> bool:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()
    res = supabase.table("access_logs")\
        .select("id")\
        .eq("name", name)\
        .eq("action", "EXIT")\
        .gte("timestamp", today_start)\
        .execute()
    return len(res.data) > 0

def clear_all_logs():
    supabase.table("access_logs").delete().neq("id", 0).execute()
    print("[DB] Tous les logs effacés ✓")

def cleanup_old_logs(days: int = 30):
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    supabase.table("access_logs").delete().lt("timestamp", cutoff).execute()
    print(f"[DB] Logs de plus de {days} jours supprimés ✓")


# ============================================================
#  SCHEDULES (Emplois du temps)
# ============================================================
def get_schedules():
    res = supabase.table("schedules").select("*").execute()
    return [Schedule(r) for r in res.data]

def save_schedule(target_type: str, target_id: str, day_of_week: str,
                  morning: bool, afternoon: bool):
    # Vérifier si existe déjà
    res = supabase.table("schedules")\
        .select("id")\
        .eq("target_type", target_type)\
        .eq("target_id", target_id)\
        .eq("day_of_week", day_of_week)\
        .execute()

    data = {
        "target_type": target_type,
        "target_id":   target_id,
        "day_of_week": day_of_week,
        "morning":     morning,
        "afternoon":   afternoon
    }

    if res.data:
        supabase.table("schedules").update(data).eq("id", res.data[0]["id"]).execute()
    else:
        supabase.table("schedules").insert(data).execute()
        