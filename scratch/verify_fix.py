import sqlite3

DB_NAME = "nagudi_auto.db"

def verify():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    reg_number = "TN 55 - BH 9477"
    print(f"Verifying {reg_number} status...")
    
    cursor.execute("SELECT status FROM vehicles WHERE reg_number = ?", (reg_number,))
    status = cursor.fetchone()[0]
    print(f"Status: {status}")
    
    if status == 'Available':
        print("Success: Vehicle is now Available.")
    else:
        print(f"Failure: Vehicle is still {status}.")
        
    # Check if it shows up in the query used by LoanTab
    cursor.execute("""
        SELECT v.id, v.reg_number
        FROM vehicles v
        WHERE v.reg_number = ? AND (v.status='Available' OR v.id IN (SELECT vehicle_id FROM loans WHERE id=-1))
    """, (reg_number,))
    res = cursor.fetchone()
    if res:
        print(f"Success: Vehicle would show up in New Loan selection: {res}")
    else:
        print("Failure: Vehicle would NOT show up in New Loan selection.")

    conn.close()

if __name__ == "__main__":
    verify()
