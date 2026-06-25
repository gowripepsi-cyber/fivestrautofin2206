import sqlite3

def delete_orphaned_loan():
    conn = sqlite3.connect('nagudi_auto.db')
    cursor = conn.cursor()
    loan_id = 201
    
    # Check if it exists
    cursor.execute("SELECT id, loan_number FROM loans WHERE id = ?", (loan_id,))
    loan = cursor.fetchone()
    
    if loan:
        print(f"Deleting loan {loan[1]} (ID: {loan[0]}) which has no customer assigned.")
        cursor.execute("DELETE FROM loans WHERE id = ?", (loan_id,))
        conn.commit()
        print("Loan deleted successfully.")
    else:
        print("Loan not found or already deleted.")
        
    conn.close()

if __name__ == "__main__":
    delete_orphaned_loan()
