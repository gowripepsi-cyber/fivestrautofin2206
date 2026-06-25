import sqlite3

DB_NAME = "nagudi_auto.db"

def check_transactions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    reg_number = "TN 55 - BH 9477"
    print(f"Checking transactions for: {reg_number}")
    
    cursor.execute("SELECT * FROM transactions WHERE description LIKE ?", (f"%{reg_number}%",))
    transactions = cursor.fetchall()
    for t in transactions:
        print(f"Transaction: {t}")
        
    cursor.execute("SELECT * FROM vehicles WHERE reg_number = ?", (reg_number,))
    vehicle = cursor.fetchone()
    if vehicle:
        print(f"Vehicle details: {vehicle}")
        # index 12 is sale_date, 13 is customer_id, 15 is status
        # Based on database.py:
        # 0: id
        # 1: vehicle_name
        # 2: make_id
        # 3: model_id
        # 4: model_year
        # 5: reg_number
        # 6: chassis_number
        # 7: engine_number
        # 8: purchase_price
        # 9: purchase_date
        # 10: rc_book
        # 11: rc_remark
        # 12: insurance_status
        # 13: insurance_remark
        # 14: tentative_sale_price
        # 15: status
        # 16: sale_price
        # 17: sale_date
        # 18: customer_id
        # ...
        
        # Wait, let me check the actual columns
        cursor.execute("PRAGMA table_info(vehicles)")
        cols = cursor.fetchall()
        for i, col in enumerate(cols):
            print(f"{i}: {col[1]}")

    conn.close()

if __name__ == "__main__":
    check_transactions()
