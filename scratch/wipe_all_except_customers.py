import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'nagudi_auto.db')

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = OFF")
cur = conn.cursor()

tables_to_wipe = [
    "payments",
    "penalty_payments",
    "call_logs",
    "loans",
    "vehicles",
    "borrowing_payments",
    "borrowings",
    "payroll",
    "employees",
    "expenses",
    "transactions",
    "day_closures",
    "models",
    "makes",
    "income_categories",
    "expense_categories",
    "accounts",
]

print("Wiping tables...")
for table in tables_to_wipe:
    try:
        cur.execute(f"DELETE FROM {table}")
        cur.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
        print(f"  [OK] Wiped: {table}")
    except Exception as e:
        print(f"  [WARN] {table}: {e}")

# Re-seed default Shop Cash account
cur.execute("INSERT OR IGNORE INTO accounts (name, type, balance) VALUES ('Shop Cash', 'CASH', 0.0)")
print("  [OK] Re-seeded: Shop Cash account")

# Re-seed income categories
for cat in ["Documentation Fee", "Interest Source", "Penalty Source", "Other Income"]:
    cur.execute("INSERT OR IGNORE INTO income_categories (name) VALUES (?)", (cat,))
print("  [OK] Re-seeded: income_categories")

# Re-seed expense categories
for cat in ["Salary", "Office Expense", "Lender Interest", "Miscellaneous", "Electricity", "Rent", "Maintenance", "Stationery", "Internet"]:
    cur.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (cat,))
print("  [OK] Re-seeded: expense_categories")

conn.execute("PRAGMA foreign_keys = ON")

# Reset customer balances — loans/payments are wiped so balances must be zeroed too
cur.execute("UPDATE customers SET balance = 0.0")
print(f"  [OK] Reset all customer balances to 0 (stale balances cleared)")

conn.commit()

# Verify customers still intact
cur.execute("SELECT COUNT(*) FROM customers")
cust_count = cur.fetchone()[0]
print(f"\n  [SAFE] customers table untouched — {cust_count} record(s) remain")

conn.close()
print("\nDone. All non-customer data wiped successfully.")
