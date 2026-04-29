import sqlite3

conn = sqlite3.connect('bms_database.db')
rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'").fetchall()
print(f"Total triggers in live DB: {len(rows)}")
for name, sql in rows:
    print(f"  - {name}")
conn.close()
