import sqlite3
import os

DB_NAME = "d:/five str auto fin - slow issue/nagudi_auto.db"

def check_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check what vehicles match the TN 37 - CP 6237 pattern
    cursor.execute("SELECT id, vehicle_name, reg_number, status FROM vehicles WHERE reg_number LIKE '%6237%'")
    vehicles = cursor.fetchall()
    
    if not vehicles:
        print("Vehicle not found!")
    else:
        for v in vehicles:
            vid = v[0]
            print(f"Found Vehicle: ID={vid}, Name={v[1]}, Reg={v[2]}, Status={v[3]}")
            
            cursor.execute("SELECT id, loan_number, customer_id, loan_amount, status FROM loans WHERE vehicle_id = ?", (vid,))
            loans = cursor.fetchall()
            if loans:
                print(f"  Associated Loans for Vehicle {vid}:")
                for l in loans:
                    print(f"    Loan ID={l[0]}, Number={l[1]}, CustID={l[2]}, Amount={l[3]}, Status={l[4]}")
            else:
                print(f"  No loans found for Vehicle {vid}.")
                
    conn.close()

if __name__ == "__main__":
    check_db()
