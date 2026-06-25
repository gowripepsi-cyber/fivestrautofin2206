import sqlite3
from datetime import datetime, timedelta
import calendar
from database import get_connection

def get_income_stats(start_date=None, end_date=None, cursor=None):
    """
    Calculates income from Documentation Fees, Interest, Penalties, and Misc.
    """
    conn = None
    if cursor is None:
        conn = get_connection()
        cursor = conn.cursor()
    
    # Helper for SQL date conversion: substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)
    def date_sql(col):
        return f"substr({col}, 7, 4) || '-' || substr({col}, 4, 2) || '-' || substr({col}, 1, 2)"

    # Convert start/end to yyyy-mm-dd if provided
    s_iso = f"{start_date[6:10]}-{start_date[3:5]}-{start_date[0:2]}" if start_date else None
    e_iso = f"{end_date[6:10]}-{end_date[3:5]}-{end_date[0:2]}" if end_date else None
    
    # 1. Documentation Fees (from loans created in range)
    query_doc = "SELECT SUM(document_fee) FROM loans"
    params = []
    if s_iso and e_iso:
        query_doc += f" WHERE {date_sql('loan_date')} BETWEEN ? AND ?"
        params = [s_iso, e_iso]
    cursor.execute(query_doc, params)
    doc_fees = cursor.fetchone()[0] or 0.0
    
    # 2. Interest Income (Portion of payments received)
    query_int = f"""
        SELECT SUM((l.loan_amount * (l.interest_rate / 100.0)) / l.loan_tenure)
        FROM payments p
        JOIN loans l ON p.loan_id = l.id
    """
    if s_iso and e_iso:
        query_int += f" WHERE {date_sql('p.payment_date')} BETWEEN ? AND ?"
    cursor.execute(query_int, params)
    interest_income = cursor.fetchone()[0] or 0.0
    
    # 3. Penalty Income
    query_p1 = "SELECT SUM(amount) FROM penalty_payments"
    if s_iso and e_iso:
        query_p1 += f" WHERE {date_sql('payment_date')} BETWEEN ? AND ?"
    cursor.execute(query_p1, params)
    penalties_1 = cursor.fetchone()[0] or 0.0
    
    query_p2 = "SELECT SUM(penalty_amount) FROM payments"
    if s_iso and e_iso:
        query_p2 += f" WHERE {date_sql('payment_date')} BETWEEN ? AND ?"
    cursor.execute(query_p2, params)
    penalties_2 = cursor.fetchone()[0] or 0.0
    
    penalty_income = penalties_1 + penalties_2
    
    # 4. Other Income (from transactions)
    query_misc = "SELECT SUM(amount) FROM transactions WHERE transaction_type = 'INCOME'"
    if s_iso and e_iso:
        query_misc += f" AND {date_sql('transaction_date')} BETWEEN ? AND ?"
    cursor.execute(query_misc, params)
    misc_income = cursor.fetchone()[0] or 0.0
    
    if conn:
        conn.close()
    
    return {
        "documentation": doc_fees,
        "interest": interest_income,
        "penalty": penalty_income,
        "other": misc_income,
        "total": doc_fees + interest_income + penalty_income + misc_income
    }

def get_expense_stats(start_date=None, end_date=None, cursor=None):
    """
    Calculates expenses from the expenses table, payroll, and lender interest.
    """
    conn = None
    if cursor is None:
        conn = get_connection()
        cursor = conn.cursor()
    
    def date_sql(col):
        return f"substr({col}, 7, 4) || '-' || substr({col}, 4, 2) || '-' || substr({col}, 1, 2)"

    s_iso = f"{start_date[6:10]}-{start_date[3:5]}-{start_date[0:2]}" if start_date else None
    e_iso = f"{end_date[6:10]}-{end_date[3:5]}-{end_date[0:2]}" if end_date else None
    
    # 1. Categorized Expenses
    query_exp = f"""
        SELECT ec.name, SUM(e.amount)
        FROM expenses e
        JOIN expense_categories ec ON e.category_id = ec.id
    """
    params = []
    if s_iso and e_iso:
        query_exp += f" WHERE {date_sql('e.expense_date')} BETWEEN ? AND ?"
        params = [s_iso, e_iso]
    query_exp += " GROUP BY ec.name"
    cursor.execute(query_exp, params)
    categorized = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 2. Payroll (from payroll table)
    query_payroll = "SELECT SUM(net_salary) FROM payroll"
    if s_iso and e_iso:
        query_payroll += f" WHERE {date_sql('payment_date')} BETWEEN ? AND ?"
    cursor.execute(query_payroll, params)
    payroll_total = cursor.fetchone()[0] or 0.0
    
    # 3. Lender Interest (from borrowing_payments)
    query_lender = "SELECT SUM(amount) FROM borrowing_payments WHERE payment_type = 'INTEREST'"
    if s_iso and e_iso:
        query_lender += f" AND {date_sql('payment_date')} BETWEEN ? AND ?"
    cursor.execute(query_lender, params)
    lender_interest = cursor.fetchone()[0] or 0.0
    
    # 4. Misc Expenses (from transactions)
    query_misc = "SELECT SUM(amount) FROM transactions WHERE transaction_type = 'EXPENSE'"
    if s_iso and e_iso:
        query_misc += f" AND {date_sql('transaction_date')} BETWEEN ? AND ?"
    cursor.execute(query_misc, params)
    misc_transactions = cursor.fetchone()[0] or 0.0
    
    if conn:
        conn.close()
    
    # Merge categorized with specifics
    stats = {
        "Salary": payroll_total + categorized.get("Salary", 0),
        "Office Expense": categorized.get("Office Expense", 0),
        "Lender Interest": lender_interest + categorized.get("Lender Interest", 0),
        "Miscellaneous": misc_transactions + categorized.get("Miscellaneous", 0),
    }
    
    for cat, val in categorized.items():
        if cat not in stats:
            stats[cat] = val
            
    stats["total"] = sum(stats.values())
    return stats

def get_profit_summary(start_date=None, end_date=None, cursor=None):
    income = get_income_stats(start_date, end_date, cursor=cursor)
    expense = get_expense_stats(start_date, end_date, cursor=cursor)
    return {
        "income": income,
        "expense": expense,
        "profit": income["total"] - expense["total"]
    }

def get_growth_chart_data(view_type="monthly"):
    """
    Generates data for matplotlib charts using optimized batch queries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    data = {"labels": [], "profit": [], "income": [], "expense": []}
    now = datetime.now()
    
    # Helper for grouping by month: YYYY-MM
    def month_key_sql(col):
        return f"substr({col}, 7, 4) || '-' || substr({col}, 4, 2)"

    # Helper for grouping by day: YYYY-MM-DD
    def day_key_sql(col):
        return f"substr({col}, 7, 4) || '-' || substr({col}, 4, 2) || '-' || substr({col}, 1, 2)"

    ranges = []
    if view_type == "monthly":
        for i in range(11, -1, -1):
            m = (now.month - i - 1) % 12 + 1
            y = now.year + (now.month - i - 1) // 12
            ranges.append((f"{y}-{m:02d}", calendar.month_name[m][:3] + f" {y}"))
    else: # daily
        for i in range(29, -1, -1):
            d = now - timedelta(days=i)
            ranges.append((d.strftime("%Y-%m-%d"), d.strftime("%d/%m")))

    # Initialize data structures
    income_map = {r[0]: 0.0 for r in ranges}
    expense_map = {r[0]: 0.0 for r in ranges}
    
    key_func = month_key_sql if view_type == "monthly" else day_key_sql
    
    # --- INCOME BATCH QUERIES ---
    # 1. Documentation Fees
    cursor.execute(f"SELECT {key_func('loan_date')}, SUM(document_fee) FROM loans GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in income_map: income_map[k] += (val or 0.0)
        
    # 2. Interest Income (Portion of payments)
    cursor.execute(f"""
        SELECT {key_func('p.payment_date')}, SUM((l.loan_amount * (l.interest_rate / 100.0)) / l.loan_tenure)
        FROM payments p JOIN loans l ON p.loan_id = l.id GROUP BY 1
    """)
    for k, val in cursor.fetchall():
        if k in income_map: income_map[k] += (val or 0.0)
        
    # 3. Penalties
    cursor.execute(f"SELECT {key_func('payment_date')}, SUM(amount) FROM penalty_payments GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in income_map: income_map[k] += (val or 0.0)
    cursor.execute(f"SELECT {key_func('payment_date')}, SUM(penalty_amount) FROM payments GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in income_map: income_map[k] += (val or 0.0)
        
    # 4. Other Income
    cursor.execute(f"SELECT {key_func('transaction_date')}, SUM(amount) FROM transactions WHERE transaction_type='INCOME' GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in income_map: income_map[k] += (val or 0.0)

    # --- EXPENSE BATCH QUERIES ---
    # 1. Categorized Expenses
    cursor.execute(f"SELECT {key_func('expense_date')}, SUM(amount) FROM expenses GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in expense_map: expense_map[k] += (val or 0.0)
        
    # 2. Payroll
    cursor.execute(f"SELECT {key_func('payment_date')}, SUM(net_salary) FROM payroll GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in expense_map: expense_map[k] += (val or 0.0)
        
    # 3. Lender Interest
    cursor.execute(f"SELECT {key_func('payment_date')}, SUM(amount) FROM borrowing_payments WHERE payment_type='INTEREST' GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in expense_map: expense_map[k] += (val or 0.0)
        
    # 4. Misc Transactions
    cursor.execute(f"SELECT {key_func('transaction_date')}, SUM(amount) FROM transactions WHERE transaction_type='EXPENSE' GROUP BY 1")
    for k, val in cursor.fetchall():
        if k in expense_map: expense_map[k] += (val or 0.0)

    # Compile final data
    for key, label in ranges:
        inc = income_map.get(key, 0.0)
        exp = expense_map.get(key, 0.0)
        data["labels"].append(label)
        data["income"].append(inc)
        data["expense"].append(exp)
        data["profit"].append(inc - exp)
        
    conn.close()
    return data
