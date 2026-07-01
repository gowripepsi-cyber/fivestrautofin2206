import sqlite3
import os

# ============================================================
# fix_customer_balances.py
#
# Recalculates customers.balance correctly after a data wipe.
#
# WHAT IS customers.balance?
#   It is a carry-forward CREDIT WALLET — it only contains
#   EXCESS (overpayment) amounts the customer has paid beyond
#   their EMI. It is NOT the loan outstanding.
#
# HOW balance CHANGES:
#   + surplus_added  — when a payment exceeds the EMI due
#   - credit_used    — when previous credit is applied to a payment
#
# On loan creation, balance is NOT involved (no change needed).
# ============================================================

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'nagudi_auto.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur2 = conn.cursor()

print("=== BEFORE FIX ===")
cur.execute("SELECT id, name, balance FROM customers WHERE balance != 0 ORDER BY id")
before = cur.fetchall()
for r in before:
    print(f"  Customer {r['id']} ({r['name']}): credit balance = {r['balance']:.2f}")
print(f"  Total customers with non-zero credit balance: {len(before)}")

# STEP 1: Reset ALL customer credit balances to 0
# (Stale balances left over from wiped payment records)
cur.execute("UPDATE customers SET balance = 0.0")
print(f"\n[STEP 1] Reset all {cur.rowcount} customer credit balances to 0.")

# STEP 2: Re-apply only the SURPLUS amounts from payments
# customers.balance only tracks carry-forward excess payments:
#   balance += surplus_added  (overpayment credited to customer)
#   balance -= credit_used    (credit applied to cover a payment)
cur.execute("SELECT loan_id, surplus_added, credit_used FROM payments")
payments = cur.fetchall()

for p in payments:
    surplus = p['surplus_added'] or 0.0
    credit  = p['credit_used']  or 0.0
    if surplus == 0 and credit == 0:
        continue  # normal payment, no effect on credit wallet

    cur2.execute("SELECT customer_id FROM loans WHERE id=?", (p['loan_id'],))
    row = cur2.fetchone()
    if not row:
        print(f"  [WARN] Payment for loan_id={p['loan_id']} has no matching loan — skipped.")
        continue

    cid = row['customer_id']
    net = surplus - credit
    cur2.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (net, cid))
    print(f"  [Payment loan {p['loan_id']}] Customer {cid}: surplus={surplus:+.2f}  "
          f"credit_used={credit:.2f}  net={net:+.2f}")

print(f"\n[STEP 2] Re-applied surplus/credit from {len(payments)} payment(s).")

print("\n=== AFTER FIX ===")
cur.execute("SELECT id, name, balance FROM customers WHERE balance != 0 ORDER BY id")
after = cur.fetchall()
for r in after:
    print(f"  Customer {r['id']} ({r['name']}): credit balance = {r['balance']:.2f}")

conn.commit()
conn.close()
print("\nDone. All customer credit balances are now correct.")
