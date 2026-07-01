import sqlite3
conn = sqlite3.connect('nagudi_auto.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, name, balance FROM customers WHERE balance != 0 ORDER BY balance DESC")
rows = cur.fetchall()
print("Customers with non-zero credit balance:")
for r in rows:
    print("  ID=%d %s: balance=%.2f" % (r['id'], r['name'], r['balance']))
print("Total:", len(rows))

print()
cur.execute("SELECT l.id, l.loan_number, l.customer_id, c.name, l.loan_amount, l.down_payment, l.status FROM loans l JOIN customers c ON l.customer_id=c.id")
for l in cur.fetchall():
    print("  Loan %d (%s): %s  amt=%.2f  dp=%.2f  status=%s" % (l['id'], l['loan_number'], l['name'], l['loan_amount'], l['down_payment'] or 0, l['status']))

print()
cur.execute("SELECT loan_id, amount, surplus_added, credit_used FROM payments")
for p in cur.fetchall():
    print("  Payment loan_id=%d  amount=%.2f  surplus=%.2f  credit_used=%.2f" % (p['loan_id'], p['amount'], p['surplus_added'] or 0, p['credit_used'] or 0))

conn.close()
