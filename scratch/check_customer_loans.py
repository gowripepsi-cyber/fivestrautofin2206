import sqlite3

DB_NAME = "nagudi_auto.db"

def check_customer_loans():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cid = 206
    print(f"Checking loans for customer ID: {cid}")
    
    cursor.execute("SELECT * FROM customers WHERE id = ?", (cid,))
    customer = cursor.fetchone()
    print(f"Customer: {customer}")
    
    cursor.execute("SELECT l.id, l.loan_number, l.vehicle_id, v.reg_number, l.status FROM loans l LEFT JOIN vehicles v ON l.vehicle_id = v.id WHERE l.customer_id = ?", (cid,))
    loans = cursor.fetchall()
    for l in loans:
        print(f"Loan: {l}")
        
    conn.close()

if __name__ == "__main__":
    check_customer_loans()
