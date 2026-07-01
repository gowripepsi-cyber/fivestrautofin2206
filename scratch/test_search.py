import sqlite3

conn = sqlite3.connect('nagudi_auto.db')
c = conn.cursor()

def simulate_search(query_text):
    search_param = f"%{query_text}%"
    c.execute("""
        SELECT DISTINCT c.id, c.name, c.phone
        FROM customers c
        LEFT JOIN loans l ON c.id = l.customer_id
        LEFT JOIN vehicles v ON (l.vehicle_id = v.id OR v.customer_id = c.id OR v.purchased_from_id = c.id)
        WHERE c.name LIKE ? OR c.phone LIKE ? OR v.reg_number LIKE ?
        LIMIT 10
    """, (search_param, search_param, search_param))
    return c.fetchall()

print("Search for SELVARAJ:", simulate_search("SELVARAJ"))
print("Search for 9345328451:", simulate_search("9345328451"))
