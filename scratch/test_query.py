import sqlite3
conn = sqlite3.connect('nagudi_auto.db')
c = conn.cursor()
c.execute("SELECT * FROM customers WHERE name LIKE '%SELVARAJ%' OR phone LIKE '%9345328451%'")
print("CUSTOMERS:", c.fetchall())

c.execute("""
    SELECT DISTINCT c.id, c.name, c.phone
    FROM customers c
    LEFT JOIN loans l ON c.id = l.customer_id
    LEFT JOIN vehicles v ON (l.vehicle_id = v.id OR v.customer_id = c.id OR v.purchased_from_id = c.id)
    WHERE c.name LIKE '%SELVARAJ%' OR c.phone LIKE '%9345328451%' OR v.reg_number LIKE '%SELVARAJ%'
""")
print("DASHBOARD SEARCH RESULT:", c.fetchall())
