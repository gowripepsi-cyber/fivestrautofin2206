import sqlite3

DB_NAME = "nagudi_auto.db"

def check_vehicle():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    reg_number = "TN 55 - BH 9477"
    # Try with and without spaces/hyphens just in case
    variants = [reg_number, "TN55-BH9477", "TN55BH9477", "TN 55 BH 9477"]
    
    for variant in variants:
        print(f"Checking for: {variant}")
        cursor.execute("SELECT id, vehicle_name, reg_number, status, customer_id FROM vehicles WHERE reg_number = ?", (variant,))
        vehicle = cursor.fetchone()
        if vehicle:
            print(f"Found Vehicle: {vehicle}")
            # Also check if it has any active loans
            cursor.execute("SELECT id, loan_number, status FROM loans WHERE vehicle_id = ?", (vehicle[0],))
            loans = cursor.fetchall()
            print(f"Loans for this vehicle: {loans}")
            break
    else:
        print("Vehicle not found with exact match. Searching with LIKE...")
        cursor.execute("SELECT id, vehicle_name, reg_number, status FROM vehicles WHERE reg_number LIKE '%BH 9477%'")
        results = cursor.fetchall()
        for res in results:
            print(f"Possible match: {res}")
            # Check loans for possible matches
            cursor.execute("SELECT id, loan_number, status FROM loans WHERE vehicle_id = ?", (res[0],))
            loans = cursor.fetchall()
            print(f"Loans for {res[2]}: {loans}")

    conn.close()

if __name__ == "__main__":
    check_vehicle()
