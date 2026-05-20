# clear_today.py
from database1 import Session, AccessLog, Student
from datetime import datetime, date

def clear_today():
    session = Session()

    # Delete ALL logs (for testing purposes)
    deleted = session.query(AccessLog).delete(synchronize_session=False)

    # Reset all students inside status
    session.query(Student).update({"inside": False}, synchronize_session=False)

    session.commit()
    session.close()

    print(f"[CLEAR] Deleted {deleted} logs ENTIRELY from the database.")
    print(f"[CLEAR] Reset all students inside status.")

if __name__ == "__main__":
    clear_today()