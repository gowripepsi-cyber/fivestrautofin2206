import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'nagudi_auto.db')

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = OFF")
cur = conn.cursor()

print("Wiping makes and models...")

for table in ["models", "makes"]:
    cur.execute(f"DELETE FROM {table}")
    cur.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
    print(f"  [OK] Wiped: {table}")

conn.execute("PRAGMA foreign_keys = ON")
conn.commit()
conn.close()

print("\nDone. Makes and Models cleared. You can now add fresh data.")
