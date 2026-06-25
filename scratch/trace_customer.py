import sqlite3

DB_NAME = "nagudi_auto.db"

def trace_customer():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cid = 206
    print(f"Tracing customer ID: {cid}")
    
    # Check transactions by description (searching for MURALI)
    cursor.execute("SELECT * FROM transactions WHERE description LIKE '%MURALI%'")
    transactions = cursor.fetchall()
    for t in transactions:
        print(f"Transaction (MURALI): {t}")
        
    # Check if there are any payments for this customer
    cursor.execute("SELECT * FROM payments p JOIN loans l ON p.loan_id = l.id WHERE l.customer_id = ?", (cid,))
    payments = cursor.fetchall()
    for p in payments:
        print(f"Payment: {p}")
        
    # Check if there are any loans (even closed ones)
    cursor.execute("SELECT * FROM loans WHERE customer_id = ?", (cid,))
    loans = cursor.fetchall()
    for l in loans:
        print(f"Loan: {l}")

    conn.close()

if __name__ == "__main__":
    trace_customer()
