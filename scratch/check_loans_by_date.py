import sqlite3

DB_NAME = "nagudi_auto.db"

def check_loans_by_date():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    date = "2026-05-13"
    print(f"Checking loans created on: {date}")
    
    cursor.execute("SELECT * FROM loans WHERE created_at LIKE ?", (f"{date}%",))
    loans = cursor.fetchall()
    for l in loans:
        print(f"Loan: {l}")
        
    conn.close()

if __name__ == "__main__":
    check_loans_by_date()
