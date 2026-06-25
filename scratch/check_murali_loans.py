import sqlite3

def check_customer_loans():
    conn = sqlite3.connect('nagudi_auto.db')
    cursor = conn.cursor()
    
    # First find the customer
    name = 'murali'
    phone = '8925562294'
    
    print(f"Searching for customer: {name} ({phone})")
    
    # Search for customer (using LIKE for name just in case)
    cursor.execute("SELECT id, name, phone FROM customers WHERE name LIKE ? AND phone = ?", (f"%{name}%", phone))
    customers = cursor.fetchall()
    
    if not customers:
        print("Customer not found.")
        conn.close()
        return
    
    for customer in customers:
        cid, cname, cphone = customer
        print(f"\nFound Customer: {cname} (ID: {cid}, Phone: {cphone})")
        
        # Now find loans for this customer
        query = """
            SELECT l.id, l.loan_number, l.loan_amount, l.status, v.reg_number 
            FROM loans l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            WHERE l.customer_id = ?;
        """
        cursor.execute(query, (cid,))
        loans = cursor.fetchall()
        
        if loans:
            print(f"Loans for {cname}:")
            for loan in loans:
                print(f" - ID: {loan[0]}, Loan No: {loan[1]}, Amount: {loan[2]}, Status: {loan[3]}, Vehicle: {loan[4]}")
        else:
            print(f"No loans found for {cname}.")
            
    conn.close()

if __name__ == "__main__":
    check_customer_loans()
