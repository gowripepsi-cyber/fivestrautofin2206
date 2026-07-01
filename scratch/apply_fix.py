import sqlite3

DB_NAME = "nagudi_auto.db"

def fix_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    reg_number = "TN 55 - BH 9477"
    customer_id = 206
    transaction_id = 812
    sale_price = 65000.0
    account_id = 1 # Shop Cash based on previous trace
    
    print(f"Starting data correction for {reg_number}...")
    
    try:
        # 1. Revert vehicle status
        cursor.execute("""
            UPDATE vehicles 
            SET status = 'Available', sale_price = NULL, sale_date = NULL, customer_id = NULL 
            WHERE reg_number = ?
        """, (reg_number,))
        print(f"  Vehicle {reg_number} reverted to 'Available'.")
        
        # 2. Reset customer balance (Add back the sale price that was deducted)
        cursor.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (sale_price, customer_id))
        print(f"  Customer {customer_id} balance increased by {sale_price}.")
        
        # 3. Revert account balance (Deduct the sale deposit)
        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (sale_price, account_id))
        print(f"  Account {account_id} balance decreased by {sale_price}.")
        
        # 4. Remove stale transaction
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        print(f"  Transaction {transaction_id} removed.")
        
        conn.commit()
        print("Data correction completed successfully.")
        
        # Final verification
        cursor.execute("SELECT status, customer_id FROM vehicles WHERE reg_number = ?", (reg_number,))
        print(f"New Vehicle State: {cursor.fetchone()}")
        cursor.execute("SELECT balance FROM customers WHERE id = ?", (customer_id,))
        print(f"New Customer Balance: {cursor.fetchone()}")
        cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        print(f"New Account Balance: {cursor.fetchone()}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during data correction: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_data()
