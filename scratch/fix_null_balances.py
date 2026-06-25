import sqlite3

def check_null_balances():
    conn = sqlite3.connect("nagudi_auto.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, balance FROM customers WHERE balance IS NULL")
    nulls = cursor.fetchall()
    print(f"Customers with NULL balance: {nulls}")
    
    if nulls:
        print("Fixing NULL balances...")
        cursor.execute("UPDATE customers SET balance = 0 WHERE balance IS NULL")
        conn.commit()
        print("Fixed.")

if __name__ == "__main__":
    check_null_balances()
