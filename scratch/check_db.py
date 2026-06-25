import sqlite3

def check_loan():
    conn = sqlite3.connect('nagudi_auto.db')
    cursor = conn.cursor()
    reg_no = 'TN 63 - AT 7051'
    query = """
        SELECT l.id, l.loan_number, l.status, v.reg_number 
        FROM loans l 
        JOIN vehicles v ON l.vehicle_id = v.id 
        WHERE v.reg_number = ?;
    """
    cursor.execute(query, (reg_no,))
    rows = cursor.fetchall()
    print(f"Loans for vehicle {reg_no}:")
    for row in rows:
        print(row)
    conn.close()

if __name__ == "__main__":
    check_loan()
