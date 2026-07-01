import sqlite3

def check_vehicle():
    conn = sqlite3.connect('nagudi_auto.db')
    cursor = conn.cursor()
    reg_no = 'TN 63 - AT 7051'
    query = """
        SELECT id, reg_number, status 
        FROM vehicles 
        WHERE reg_number = ?;
    """
    cursor.execute(query, (reg_no,))
    row = cursor.fetchone()
    print(f"Vehicle info for {reg_no}:")
    print(row)
    conn.close()

if __name__ == "__main__":
    check_vehicle()
