import sqlite3
from datetime import datetime
import calendar

conn = sqlite3.connect('nagudi_auto.db')
cursor = conn.cursor()
search_param = "%SELVARAJ%"

cursor.execute("""
    SELECT DISTINCT c.id, c.name, c.phone
    FROM customers c
    LEFT JOIN loans l ON c.id = l.customer_id
    LEFT JOIN vehicles v ON (l.vehicle_id = v.id OR v.customer_id = c.id OR v.purchased_from_id = c.id)
    WHERE c.name LIKE ? OR c.phone LIKE ? OR v.reg_number LIKE ?
    LIMIT 10
""", (search_param, search_param, search_param))
customers = cursor.fetchall()

results = []
try:
    for cid, name, phone in customers:
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE customer_id = ?", (cid,))
        sales_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE purchased_from_id = ?", (cid,))
        purch_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT id, installment_amount, due_beginning_date, loan_tenure, status, 
                   (SELECT COUNT(*) FROM payments WHERE loan_id = loans.id) 
            FROM loans WHERE customer_id = ?
        """, (cid,))
        loans_data = cursor.fetchall()
        
        overdue_amt = 0
        active_loan = next((l for l in loans_data if l[4] == 'Active'), None)
        if active_loan:
            lid, emi, due_start, tenure, status, paid_count = active_loan
            if due_start:
                now = datetime.now().date()
                start_dt = datetime.strptime(due_start, "%d-%m-%Y")
                for idx in range(paid_count, tenure):
                    month = (start_dt.month + idx - 1) % 12 + 1
                    year = start_dt.year + (start_dt.month + idx - 1) // 12
                    last_day = calendar.monthrange(year, month)[1]
                    due_date = datetime(year, month, min(start_dt.day, last_day)).date()
                    if due_date < now: overdue_amt += emi
                    else: break
        
        results.append({"id": cid, "name": name})
    print("SUCCESS, results:", results)
except Exception as e:
    import traceback
    traceback.print_exc()
