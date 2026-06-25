import sqlite3

DB_NAME = "nagudi_auto.db"

def find_anomalies():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("Finding vehicles marked 'Sold' but with no active loans and negative customer balance...")
    
    cursor.execute("""
        SELECT v.id, v.reg_number, v.customer_id, c.name, c.balance, v.sale_price
        FROM vehicles v
        JOIN customers c ON v.customer_id = c.id
        WHERE v.status = 'Sold'
        AND v.id NOT IN (SELECT vehicle_id FROM loans WHERE status = 'Active' AND vehicle_id IS NOT NULL)
    """)
    anomalies = cursor.fetchall()
    
    for v_id, reg, c_id, c_name, c_bal, s_price in anomalies:
        # Check transactions for this vehicle to see if it was "Loan Pay"
        cursor.execute("SELECT description FROM transactions WHERE description LIKE ?", (f"%{reg}%",))
        trans = cursor.fetchall()
        is_loan_pay = any("Loan Pay" in t[0] for t in trans)
        
        if is_loan_pay or c_bal < 0:
            print(f"Anomaly Found: Vehicle {reg} (ID {v_id})")
            print(f"  Customer: {c_name} (ID {c_id}), Balance: {c_bal}")
            print(f"  Sale Price: {s_price}")
            print(f"  Is Loan Pay according to transactions: {is_loan_pay}")
            print("-" * 20)

    conn.close()

if __name__ == "__main__":
    find_anomalies()
