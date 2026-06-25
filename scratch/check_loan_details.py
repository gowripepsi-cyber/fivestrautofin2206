import sqlite3

def check_loan_details():
    conn = sqlite3.connect('nagudi_auto.db')
    cursor = conn.cursor()
    loan_id = 201
    query = """
        SELECT l.id, l.loan_number, l.customer_id, c.name, l.vehicle_id, v.reg_number, l.status
        FROM loans l
        LEFT JOIN customers c ON l.customer_id = c.id
        LEFT JOIN vehicles v ON l.vehicle_id = v.id
        WHERE l.id = ?;
    """
    cursor.execute(query, (loan_id,))
    row = cursor.fetchone()
    print(f"Loan Details for ID {loan_id}:")
    print(row)
    conn.close()

if __name__ == "__main__":
    check_loan_details()
