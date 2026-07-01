import sqlite3

conn = sqlite3.connect('nagudi_auto.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Search for customer PANNIR SELVAM
cur.execute("SELECT id, name, phone, balance FROM customers WHERE name LIKE ? OR phone=?", ('%PANNIR%', '9715840321'))
customers = cur.fetchall()
print('=== CUSTOMERS ===')
for c in customers:
    print(dict(c))

# Search for loans for this customer
if customers:
    for c in customers:
        cid = c['id']
        cur.execute('SELECT id, loan_number, loan_amount, installment_amount, loan_tenure, loan_date, due_beginning_date, status, vehicle_id FROM loans WHERE customer_id=?', (cid,))
        loans = cur.fetchall()
        print(f'\n=== LOANS for customer_id={cid} ===')
        for l in loans:
            print(dict(l))

        # Also check vehicles
        cur.execute('SELECT id, vehicle_name, reg_number, status, sale_price, customer_id FROM vehicles WHERE customer_id=? OR reg_number LIKE ?', (cid, '%AV 7696%'))
        vehs = cur.fetchall()
        print(f'\n=== VEHICLES for customer_id={cid} or reg TN55AV7696 ===')
        for v in vehs:
            print(dict(v))

# Also search by reg number directly
cur.execute("SELECT id, vehicle_name, reg_number, status, sale_price, customer_id FROM vehicles WHERE reg_number LIKE ?", ('%AV 7696%',))
vehs2 = cur.fetchall()
print('\n=== VEHICLES with reg AV7696 ===')
for v in vehs2:
    print(dict(v))

conn.close()
