# test_db.py
from database1 import init_db, log_access, get_all_logs

init_db()

print(f"Logs before: {len(get_all_logs())}")

log_access("TEST001", "Test Student", True, "ENTRY")

print(f"Logs after: {len(get_all_logs())}")
