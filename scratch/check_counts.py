import sqlite3
conn = sqlite3.connect("nagudi_auto.db")
cursor = conn.cursor()
tables = ["loans", "payments", "customers", "vehicles", "transactions", "expenses"]
for t in tables:
    try:
        cursor.execute(f"SELECT count(*) FROM {t}")
        print(f"{t}: {cursor.fetchone()[0]}")
    except:
        print(f"{t}: Error")
conn.close()
