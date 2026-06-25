import sqlite3

def fix_vignesh_balance():
    conn = sqlite3.connect("nagudi_auto.db")
    cursor = conn.cursor()
    
    # 1. Check current balance
    cursor.execute("SELECT balance FROM customers WHERE id = 205")
    curr_balance = cursor.fetchone()[0]
    print(f"Current balance for Vignesh: {curr_balance}")
    
    # 2. Update balance to 39500.0
    # (Loan Amount: 29500 + Down Payment: 10000)
    print("Updating balance to 39500.0...")
    cursor.execute("UPDATE customers SET balance = 39500.0 WHERE id = 205")
    
    conn.commit()
    
    # 3. Verify
    cursor.execute("SELECT balance FROM customers WHERE id = 205")
    new_balance = cursor.fetchone()[0]
    print(f"New balance for Vignesh: {new_balance}")
    
    conn.close()

if __name__ == "__main__":
    fix_vignesh_balance()
