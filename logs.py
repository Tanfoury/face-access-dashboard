# view_logs.py
from database1 import init_db, get_all_logs

def view_logs():
    init_db()
    
    logs = get_all_logs()
    
    if not logs:
        print("\n[LOGS] No access logs found yet.")
        return
    
    print("\n" + "="*70)
    print(f"{'ID':<5} {'NAME':<20} {'STUDENT ID':<15} {'TIME':<25} {'ACTION'}")
    print("="*70)
    
    for log in logs:
        action    = f"✅ ENTRY" if log.action else"exit"
        timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{log.id:<5} {log.name:<20} {log.student_id:<15} {timestamp:<25} {action}")
    
    print("="*70)
    print(f"\nTotal entries: {len(logs)}")
    
    # Summary
    entries = sum(1 for log in logs if log.action == "ENTRY")
    exits   = sum(1 for log in logs if log.action == "EXIT")

    print(f"✅ Entries : {entries}")
    print(f"🚪 Exits   : {exits}")
    print("="*70)

if __name__ == "__main__":
    view_logs()