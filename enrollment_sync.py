from database1 import add_student as add_student_local


def add_student_everywhere(name, student_id, grade, photo_dir, category="eleve"):
    """Save a student in the local SQLite-compatible store and in Supabase."""
    add_student_local(name, student_id, grade, photo_dir, category)

    try:
        from database import add_student as add_student_supabase
        add_student_supabase(student_id=student_id, name=name, grade=grade, category=category)
        print(f"[SYNC] Student '{name}' saved to Supabase and local database.")
    except Exception as exc:
        print(f"[SYNC] Supabase sync failed for '{name}': {exc}")