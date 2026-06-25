import sqlite3
import os
import tempfile
import webbrowser
from datetime import datetime
from database import get_connection
import finance_logic as fl

def get_daily_summary(target_date=None):
    """
    Aggregates financial and stock data for the giveaway date (format: DD-MM-YYYY).
    """
    if not target_date:
        target_date = datetime.now().strftime("%d-%m-%Y")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    summary = {
        "date": target_date,
        "timestamp": datetime.now().strftime("%I:%M %p"),
        "cash": {},
        "bank": [],
        "income": {},
        "expense": {},
        "stock": [],
        "totals": {}
    }
    
    # 1. CASH SUMMARY
    # Opening Cash = Closing Cash of previous closure
    cursor.execute("SELECT closing_cash FROM day_closures WHERE closure_date < ? ORDER BY closure_date DESC LIMIT 1", (target_date,))
    res = cursor.fetchone()
    opening_cash = res[0] if res else 0.0
    
    # Cash Received/Sales/Expenses/Deposits for the date
    # Note: We filter transactions, payments, and expenses by target_date
    
    # a. Cash Received (EMI Payments + Income Transactions)
    cursor.execute("""
        SELECT SUM(amount) FROM (
            SELECT amount FROM payments WHERE payment_date = ? AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
            UNION ALL
            SELECT amount FROM transactions WHERE (transaction_date LIKE ? OR transaction_date = ?) AND transaction_type = 'INCOME' AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
            UNION ALL
            SELECT amount FROM penalty_payments WHERE payment_date = ? AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
        )
    """, (target_date, f"%{target_date}%", target_date, target_date))
    cash_received = cursor.fetchone()[0] or 0.0
    
    # b. Cash Sales (Vehicle Sales mapped to CASH accounts via transactions)
    cursor.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE (transaction_date LIKE ? OR transaction_date = ?) 
        AND transaction_type = 'DEPOSIT' 
        AND description LIKE 'Vehicle Sale%'
        AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
    """, (f"%{target_date}%", target_date))
    cash_sales = cursor.fetchone()[0] or 0.0
    
    # c. Cash Expenses
    cursor.execute("""
        SELECT SUM(amount) FROM (
            SELECT amount FROM expenses WHERE expense_date = ? AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
            UNION ALL
            SELECT amount FROM transactions WHERE (transaction_date LIKE ? OR transaction_date = ?) AND transaction_type = 'EXPENSE' AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
            UNION ALL
            SELECT net_salary FROM payroll WHERE payment_date = ? AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
            UNION ALL
            SELECT amount FROM borrowing_payments WHERE payment_date = ? AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
        )
    """, (target_date, f"%{target_date}%", target_date, target_date, target_date))
    cash_expenses = cursor.fetchone()[0] or 0.0
    
    # d. Cash deposited to Bank
    cursor.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE (transaction_date LIKE ? OR transaction_date = ?) 
        AND transaction_type = 'TRANSFER_OUT' 
        AND account_id IN (SELECT id FROM accounts WHERE type='CASH')
        AND related_account_id IN (SELECT id FROM accounts WHERE type='BANK')
    """, (f"%{target_date}%", target_date))
    cash_bank_deposit = cursor.fetchone()[0] or 0.0
    
    closing_cash = opening_cash + cash_received + cash_sales - cash_expenses - cash_bank_deposit
    
    summary["cash"] = {
        "opening": opening_cash,
        "received": cash_received,
        "sales": cash_sales,
        "expenses": cash_expenses,
        "deposit": cash_bank_deposit,
        "closing": closing_cash
    }
    
    # 2. BANK SUMMARY
    cursor.execute("SELECT id, name, balance FROM accounts WHERE type='BANK'")
    banks = cursor.fetchall()
    total_bank_balance = 0
    for bid, bname, bbal in banks:
        # For simplicity, we show current balance as closing balance. 
        # Ideal: Track hist balance by subtracting today's movements.
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE account_id = ? AND transaction_date LIKE ? AND transaction_type IN ('DEPOSIT', 'TRANSFER_IN', 'INCOME')", (bid, f"%{target_date}%"))
        dep = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE account_id = ? AND transaction_date LIKE ? AND transaction_type IN ('WITHDRAWAL', 'TRANSFER_OUT', 'EXPENSE')", (bid, f"%{target_date}%"))
        withd = cursor.fetchone()[0] or 0.0
        
        opening_bal = bbal - dep + withd
        summary["bank"].append({
            "name": bname,
            "opening": opening_bal,
            "deposit": dep,
            "withdrawal": withd,
            "closing": bbal
        })
        total_bank_balance += bbal
        
    # 3. INCOME SUMMARY
    inc = fl.get_income_stats(target_date, target_date)
    summary["income"] = inc
    
    # 4. EXPENSE SUMMARY
    exp = fl.get_expense_stats(target_date, target_date)
    summary["expense"] = exp
    
    # 5. STOCK SUMMARY
    cursor.execute("""
        SELECT m.name || ' ' || mo.name, 'Vehicle', COUNT(*), purchase_price
        FROM vehicles v
        JOIN makes m ON v.make_id = m.id
        JOIN models mo ON v.model_id = mo.id
        WHERE status = 'Available'
        GROUP BY v.make_id, v.model_id
    """)
    stock_items = cursor.fetchall()
    total_stock_value = 0
    for name, cat, qty, price in stock_items:
        # In this simple finance app, Opening/In/Out for daily stock is complex without 
        # a movements table. We will show current 'House Stock' snapshot.
        val = qty * price
        summary["stock"].append({
            "name": name,
            "category": cat,
            "closing": qty,
            "unit_price": price,
            "value": val
        })
        total_stock_value += val

    summary["totals"] = {
        "bank": total_bank_balance,
        "stock": total_stock_value,
        "assets": closing_cash + total_bank_balance + total_stock_value
    }
    
    conn.close()
    return summary

def save_closure(summary):
    import json
    try:
        user = "Admin" # Extendable for multi-user
        date = summary["date"]
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if already closed
        cursor.execute("SELECT id FROM day_closures WHERE closure_date = ?", (date,))
        if cursor.fetchone():
            conn.close()
            return None
            
        # Get next report number
        cursor.execute("SELECT COUNT(*) FROM day_closures")
        count = cursor.fetchone()[0] + 1
        year = datetime.now().year
        rnum = f"DEC-{year}-{count:04d}"
        
        # Store as JSON for exact reprinting later
        sj = json.dumps(summary)
        
        cursor.execute("""
            INSERT INTO day_closures (closure_date, opening_cash, closing_cash, total_bank_balance, total_stock_value, total_assets, closed_by, report_number, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, summary['cash']['opening'], summary['cash']['closing'], summary['totals']['bank'], summary['totals']['stock'], summary['totals']['assets'], user, rnum, sj))
        
        conn.commit()
        conn.close()
        return rnum
    except Exception as e:
        print(f"Error saving closure: {e}")
        return None
    finally:
        conn.close()

def generate_html_report(summary, report_num, shop_info):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Day End Closure - {report_num}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #333; }}
            .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }}
            .shop-name {{ font-size: 24px; font-weight: bold; margin: 0; }}
            .report-title {{ font-size: 20px; text-decoration: underline; margin-top: 10px; }}
            .meta {{ display: flex; justify-content: space-between; margin-bottom: 20px; font-weight: bold; }}
            
            h3 {{ border-left: 5px solid #444; padding-left: 10px; background: #f4f4f4; padding-top: 5px; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #999; padding: 8px; text-align: left; }}
            th {{ background-color: #eee; }}
            .text-right {{ text-align: right; }}
            .total-row {{ font-weight: bold; background: #fafafa; }}
            .asset-summary {{ background: #333; color: #fff; padding: 15px; border-radius: 5px; }}
            
            .signature-section {{ margin-top: 50px; display: flex; justify-content: space-between; }}
            .sig-box {{ text-align: center; width: 200px; }}
            .sig-line {{ border-top: 1px solid #000; margin-top: 40px; }}

            @media print {{
                body {{ margin: 20px; }}
                button {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <p class="shop-name">{shop_info.get('name', 'Nagudi Auto Finance')}</p>
            <p>{shop_info.get('address', '')}</p>
            <p>Phone: {shop_info.get('contact', '')}</p>
            <p class="report-title">DAY END CLOSURE REPORT</p>
        </div>

        <div class="meta">
            <span>Date: {summary['date']}</span>
            <span>Report No: {report_num}</span>
            <span>Ref Time: {summary['timestamp']}</span>
        </div>

        <h3>SECTION 1: CASH SUMMARY</h3>
        <table>
            <tr><td>Opening Cash</td><td class="text-right">₹ {summary['cash']['opening']:,}</td></tr>
            <tr><td>Cash Sales Today (+)</td><td class="text-right">₹ {summary['cash']['sales']:,}</td></tr>
            <tr><td>Cash Received (+)</td><td class="text-right">₹ {summary['cash']['received']:,}</td></tr>
            <tr><td>Cash Expenses (-)</td><td class="text-right">₹ {summary['cash']['expenses']:,}</td></tr>
            <tr><td>Bank Deposits (-)</td><td class="text-right">₹ {summary['cash']['deposit']:,}</td></tr>
            <tr class="total-row"><td>CLOSING CASH</td><td class="text-right">₹ {summary['cash']['closing']:,}</td></tr>
        </table>

        <h3>SECTION 2: BANK SUMMARY</h3>
        <table>
            <thead>
                <tr><th>Bank Name</th><th>Opening</th><th>Deposit</th><th>Withdr.</th><th>Closing</th></tr>
            </thead>
            <tbody>
                {''.join([f"<tr><td>{b['name']}</td><td>₹{b['opening']:,}</td><td>₹{b['deposit']:,}</td><td>₹{b['withdrawal']:,}</td><td>₹{b['closing']:,}</td></tr>" for b in summary['bank']])}
                <tr class="total-row"><td colspan="4">TOTAL BANK BALANCE</td><td class="text-right">₹ {summary['totals']['bank']:,}</td></tr>
            </tbody>
        </table>

        <div style="display: flex; gap: 20px;">
            <div style="flex: 1;">
                <h3>SECTION 3: INCOME</h3>
                <table>
                    <tr><td>Interest</td><td class="text-right">₹ {summary['income']['interest']:,}</td></tr>
                    <tr><td>Doc. Fees</td><td class="text-right">₹ {summary['income']['documentation']:,}</td></tr>
                    <tr><td>Penalties</td><td class="text-right">₹ {summary['income']['penalty']:,}</td></tr>
                    <tr><td>Other</td><td class="text-right">₹ {summary['income']['other']:,}</td></tr>
                    <tr class="total-row"><td>TOTAL</td><td class="text-right">₹ {summary['income']['total']:,}</td></tr>
                </table>
            </div>
            <div style="flex: 1;">
                <h3>SECTION 4: EXPENSES</h3>
                <table>
                    {''.join([f"<tr><td>{k}</td><td class='text-right'>₹ {v:,}</td></tr>" for k,v in summary['expense'].items() if k != 'total'])}
                    <tr class="total-row"><td>TOTAL</td><td class="text-right">₹ {summary['expense']['total']:,}</td></tr>
                </table>
            </div>
        </div>

        <h3>SECTION 5: STOCK SUMMARY</h3>
        <table>
            <thead>
                <tr><th>Item Name</th><th>Type</th><th>Qty</th><th>Price</th><th>Value</th></tr>
            </thead>
            <tbody>
                {''.join([f"<tr><td>{s['name']}</td><td>{s['category']}</td><td>{s['closing']}</td><td>₹{s['unit_price']:,}</td><td>₹{s['value']:,}</td></tr>" for s in summary['stock']])}
                <tr class="total-row"><td colspan="4">TOTAL STOCK VALUE</td><td class="text-right">₹ {summary['totals']['stock']:,}</td></tr>
            </tbody>
        </table>

        <div class="asset-summary">
            <h2 style="margin: 0; text-align: center;">FINAL ASSET SUMMARY: ₹ {summary['totals']['assets']:,}</h2>
            <p style="text-align: center; margin-top: 5px;">(Cash: ₹{summary['cash']['closing']:,} | Bank: ₹{summary['totals']['bank']:,} | Stock: ₹{summary['totals']['stock']:,})</p>
        </div>

        <div class="signature-section">
            <div class="sig-box"><div class="sig-line"></div>Prepared By</div>
            <div class="sig-box"><div class="sig-line"></div>Checked By</div>
            <div class="sig-box"><div class="sig-line"></div>Shop Incharge</div>
        </div>

        <div style="margin-top: 30px; text-align: center;">
            <button onclick="window.print()">Print Report</button>
        </div>
    </body>
    </html>
    """
    
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
        f.write(html)
        path = f.name
    
    webbrowser.open('file://' + os.path.realpath(path))

def is_date_closed(date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM day_closures WHERE closure_date = ?", (date,))
    closed = cursor.fetchone() is not None
    conn.close()
    return closed
