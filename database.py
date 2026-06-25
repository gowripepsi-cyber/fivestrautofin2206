import sqlite3
import os

DB_NAME = "nagudi_auto.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn

def initialize_db():
    conn = get_connection()
    conn.execute("PRAGMA journal_mode=WAL") # Enable WAL mode for better performance
    cursor = conn.cursor()
    cursor.execute("BEGIN")
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Migration: Add created_at column to users if it doesn't exist
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'created_at' not in columns:
            # SQLite on some versions doesn't allow CURRENT_TIMESTAMP in ALTER TABLE ADD COLUMN
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
            # Update existing rows
            cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            print("Migration: Added created_at column to users table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            print(f"Migration Warning (users): {e}")
    
    # Also ensure vehicles table has customer_id (fixing previous identified gap)
    try:
        cursor.execute("PRAGMA table_info(vehicles)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'customer_id' not in columns:
            cursor.execute("ALTER TABLE vehicles ADD COLUMN customer_id INTEGER")
            print("Migration: Added customer_id column to vehicles table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            print(f"Migration Warning (vehicles): {e}")

    conn.commit()
    
    # Create customers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        father_name TEXT,
        phone TEXT,
        street TEXT,
        city TEXT,
        pincode TEXT,
        aadhaar TEXT,
        gender TEXT,
        business TEXT,
        rating TEXT,
        introducer TEXT,
        photo_path TEXT,
        docs_path TEXT,
        balance REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Migration: Add balance column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE customers ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Create makes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS makes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    
    # Create models table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        make_id INTEGER,
        name TEXT NOT NULL,
        UNIQUE(make_id, name),
        FOREIGN KEY (make_id) REFERENCES makes (id)
    )
    """)

    # Create vehicles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_name TEXT NOT NULL,
        make_id INTEGER,
        model_id INTEGER,
        model_year INTEGER,
        reg_number TEXT,
        chassis_number TEXT,
        engine_number TEXT,
        purchase_price REAL,
        purchase_date TEXT,
        rc_book TEXT,
        rc_remark TEXT,
        insurance_status TEXT,
        insurance_until TEXT,
        insurance_remark TEXT,
        tentative_sale_price REAL,
        status TEXT DEFAULT 'Available',
        sale_price REAL,
        sale_date TEXT,
        customer_id INTEGER,
        purchase_account_id INTEGER,
        purchased_from_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (purchased_from_id) REFERENCES customers (id),
        FOREIGN KEY (purchase_account_id) REFERENCES accounts (id),
        FOREIGN KEY (make_id) REFERENCES makes (id),
        FOREIGN KEY (model_id) REFERENCES models (id)
    )
    """)
    
    # Migration: Remove global UNIQUE constraint on vehicles.reg_number and replace with Partial Unique Index
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_vehicles_reg_unique'")
        if not cursor.fetchone():
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vehicles'")
            sql = cursor.fetchone()[0]
            if "reg_number TEXT UNIQUE" in sql or "UNIQUE" in sql:
                print("Running database migration to remove UNIQUE constraint from vehicles.reg_number...")
                # 1. Rename existing table
                cursor.execute("ALTER TABLE vehicles RENAME TO vehicles_old")
                # 2. Create new vehicles table
                cursor.execute("""
                CREATE TABLE vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_name TEXT NOT NULL,
                    make_id INTEGER,
                    model_id INTEGER,
                    model_year INTEGER,
                    reg_number TEXT,
                    chassis_number TEXT,
                    engine_number TEXT,
                    purchase_price REAL,
                    purchase_date TEXT,
                    rc_book TEXT,
                    rc_remark TEXT,
                    insurance_status TEXT,
                    insurance_until TEXT,
                    insurance_remark TEXT,
                    tentative_sale_price REAL,
                    status TEXT DEFAULT 'Available',
                    sale_price REAL,
                    sale_date TEXT,
                    customer_id INTEGER,
                    purchase_account_id INTEGER,
                    purchased_from_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id),
                    FOREIGN KEY (purchased_from_id) REFERENCES customers (id),
                    FOREIGN KEY (purchase_account_id) REFERENCES accounts (id),
                    FOREIGN KEY (make_id) REFERENCES makes (id),
                    FOREIGN KEY (model_id) REFERENCES models (id)
                )
                """)
                # 3. Copy data
                cursor.execute("""
                INSERT INTO vehicles (
                    id, vehicle_name, make_id, model_id, model_year, reg_number, chassis_number, engine_number,
                    purchase_price, purchase_date, rc_book, rc_remark, insurance_status, insurance_until, insurance_remark,
                    tentative_sale_price, status, sale_price, sale_date, customer_id, purchase_account_id,
                    purchased_from_id, created_at
                ) SELECT 
                    id, vehicle_name, make_id, model_id, model_year, reg_number, chassis_number, engine_number,
                    purchase_price, purchase_date, rc_book, rc_remark, insurance_status, insurance_until, insurance_remark,
                    tentative_sale_price, status, sale_price, sale_date, customer_id, purchase_account_id,
                    purchased_from_id, created_at
                FROM vehicles_old
                """)
                # 4. Drop old table
                cursor.execute("DROP TABLE vehicles_old")
                print("Database migration completed.")
    except Exception as e:
        print(f"Migration Error (vehicles UNIQUE constraint): {e}")
    
    # Migration: Add tentative_sale_price column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE vehicles ADD COLUMN tentative_sale_price REAL")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add purchase_account_id column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE vehicles ADD COLUMN purchase_account_id INTEGER REFERENCES accounts(id)")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Migration: Add purchased_from_id column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE vehicles ADD COLUMN purchased_from_id INTEGER REFERENCES customers(id)")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Create accounts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT CHECK(type IN ('CASH', 'BANK')),
        balance REAL DEFAULT 0,
        bank_name TEXT,
        account_number TEXT,
        branch_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER,
        transaction_type TEXT CHECK(transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_OUT', 'TRANSFER_IN', 'INCOME', 'EXPENSE')),
        amount REAL NOT NULL,
        description TEXT,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        related_account_id INTEGER,
        FOREIGN KEY (account_id) REFERENCES accounts (id),
        FOREIGN KEY (related_account_id) REFERENCES accounts (id)
    )
    """)

    # Create loans table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_number TEXT UNIQUE,
        customer_id INTEGER,
        loan_amount REAL NOT NULL,
        loan_tenure INTEGER NOT NULL,
        interest_rate REAL NOT NULL,
        installment_amount REAL,
        loan_date TEXT,
        vehicle_id INTEGER,
        status TEXT DEFAULT 'Active',
        document_fee REAL DEFAULT 0,
        loan_doc_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    """)

    # Create payments (EMI) table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER,
        amount REAL NOT NULL,
        payment_date TEXT,
        account_id INTEGER,
        remarks TEXT,
        penalty_amount REAL DEFAULT 0,
        penalty_per_emi REAL DEFAULT 300,
        overdue_count INTEGER DEFAULT 0,
        emi_numbers TEXT DEFAULT '',
        credit_used REAL DEFAULT 0,
        surplus_added REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (loan_id) REFERENCES loans (id),
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    """)

    # Migration: Add new columns to payments table (idempotent)
    for col_def in [
        ("penalty_per_emi", "REAL DEFAULT 300"),
        ("overdue_count", "INTEGER DEFAULT 0"),
        ("emi_numbers", "TEXT DEFAULT ''"),
        ("credit_used", "REAL DEFAULT 0"),
        ("surplus_added", "REAL DEFAULT 0")
    ]:
        col_name, col_type = col_def
        try:
            cursor.execute(f"ALTER TABLE payments ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists or other known issue


    # Create call_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER,
        call_date TEXT,
        call_time TEXT,
        response_text TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (loan_id) REFERENCES loans (id)
    )
    """)

    # Create borrowings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS borrowings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lender_name TEXT NOT NULL,
        amount REAL NOT NULL,
        interest_rate REAL NOT NULL,
        borrow_date TEXT,
        account_id INTEGER,
        status TEXT DEFAULT 'Active',
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    """)

    # Create borrowing_payments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS borrowing_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        borrowing_id INTEGER,
        payment_date TEXT,
        amount REAL NOT NULL,
        payment_type TEXT CHECK(payment_type IN ('INTEREST', 'PRINCIPAL')),
        account_id INTEGER,
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (borrowing_id) REFERENCES borrowings (id),
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    """)

    # Migration: Add vehicle_id column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE loans ADD COLUMN vehicle_id INTEGER REFERENCES vehicles(id)")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add down_payment column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE loans ADD COLUMN down_payment REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add document_fee column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE loans ADD COLUMN document_fee REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add loan_doc_path column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE loans ADD COLUMN loan_doc_path TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add due_beginning_date column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE loans ADD COLUMN due_beginning_date TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add closed_date column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE loans ADD COLUMN closed_date TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add loan_number column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE loans ADD COLUMN loan_number TEXT")
        # Backfill existing loans
        cursor.execute("UPDATE loans SET loan_number = 'L-' || id WHERE loan_number IS NULL")
    except sqlite3.OperationalError:
        pass # Column already exists

    # --- New Modules Tables ---

    # Create income_categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS income_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    
    # Default income categories
    income_cats = ['Documentation Fee', 'Interest Source', 'Penalty Source', 'Other Income']
    for cat in income_cats:
        cursor.execute("INSERT OR IGNORE INTO income_categories (name) VALUES (?)", (cat,))

    # Create expense_categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expense_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    
    # Default expense categories
    expense_cats = ['Salary', 'Office Expense', 'Lender Interest', 'Miscellaneous', 'Electricity', 'Rent', 'Maintenance', 'Stationery', 'Internet']
    for cat in expense_cats:
        cursor.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (cat,))

    # Create expenses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_date TEXT NOT NULL,
        category_id INTEGER,
        amount REAL NOT NULL,
        account_id INTEGER,
        description TEXT,
        approved_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES expense_categories (id),
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    """)

    # Create employees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        role TEXT,
        phone TEXT,
        address TEXT,
        salary_type TEXT CHECK(salary_type IN ('Monthly', 'Daily')),
        basic_salary REAL,
        joining_date TEXT,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create payroll table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payroll (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        month INTEGER,
        year INTEGER,
        basic_salary REAL,
        advance_deduction REAL DEFAULT 0,
        bonus REAL DEFAULT 0,
        other_deductions REAL DEFAULT 0,
        net_salary REAL,
        payment_date TEXT,
        account_id INTEGER,
        status TEXT DEFAULT 'Paid',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees (id),
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    """)

    # Create penalty_payments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS penalty_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER,
        amount REAL NOT NULL,
        payment_date TEXT,
        account_id INTEGER,
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (loan_id) REFERENCES loans (id),
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    """)

    # Migration: Add penalty_amount column to payments if desired (for easier tracking)
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN penalty_amount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Check if default Shop Cash account exists
    cursor.execute("SELECT * FROM accounts WHERE name = 'Shop Cash'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)", 
                       ('Shop Cash', 'CASH', 0.0))
    
    # Create day_closures table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS day_closures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        closure_date TEXT UNIQUE NOT NULL,
        opening_cash REAL,
        closing_cash REAL,
        total_bank_balance REAL,
        total_stock_value REAL,
        total_assets REAL,
        closed_by TEXT,
        report_number TEXT UNIQUE,
        summary_json TEXT, -- Store full snapshot for reprinting
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Migration: Add summary_json to day_closures if missing
    try:
        cursor.execute("ALTER TABLE day_closures ADD COLUMN summary_json TEXT")
    except: pass
    
    # Check if admin user exists, if not create one
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       ('admin', 'gowri@11221', 'Administrator'))
        print("Default admin user created: admin / admin123")
    
    # Add Indices for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_customer ON loans(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_vehicle ON loans(vehicle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_loan ON payments(loan_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_customer ON vehicles(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)")
    
    # Partial Unique index for vehicles (only Available reg_numbers are unique)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicles_reg_unique ON vehicles(reg_number) WHERE status = 'Available'")

    # Missing customer indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_created ON customers(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)")

    conn.commit()
    conn.close()

def get_dashboard_stats():
    """Returns a dictionary of statistics for the dashboard."""
    stats = {
        "total_vehicles": 0,
        "active_loans": 0,
        "total_customers": 0,
        "total_balance": 0.0,
        "overdue_loans": 0
    }
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Total vehicles in-house (Available status)
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'Available'")
        stats["total_vehicles"] = cursor.fetchone()[0]
        
        # 2. Total active loans (Sold with active finance)
        cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'Active'")
        stats["active_loans"] = cursor.fetchone()[0]
        
        # 3. Total customers
        cursor.execute("SELECT COUNT(*) FROM customers")
        stats["total_customers"] = cursor.fetchone()[0]
        
        # 4. Total balance across all accounts
        cursor.execute("SELECT SUM(balance) FROM accounts")
        res = cursor.fetchone()[0]
        stats["total_balance"] = res if res is not None else 0.0
        
        # 5. Overdue Loans (Optimized check)
        cursor.execute("""
            SELECT l.due_beginning_date, l.loan_tenure, 
                   COALESCE(p_count.cnt, 0) as paid_count
            FROM loans l 
            LEFT JOIN (SELECT loan_id, COUNT(*) as cnt FROM payments GROUP BY loan_id) p_count ON l.id = p_count.loan_id
            WHERE l.status = 'Active' AND l.due_beginning_date IS NOT NULL
        """)
        active_loans = cursor.fetchall()
        overdue_count = 0
        from datetime import datetime
        import calendar
        now = datetime.now().date()
        
        for due_start, tenure, paid_count in active_loans:
            if paid_count >= tenure: continue
            try:
                # Basic check: if paid_count is less than months elapsed since start, it's likely overdue
                start_dt = datetime.strptime(due_start, "%d-%m-%Y")
                
                # Calculate the date for the NEXT pending payment
                i = paid_count 
                month = (start_dt.month + i - 1) % 12 + 1
                year = start_dt.year + (start_dt.month + i - 1) // 12
                last_day = calendar.monthrange(year, month)[1]
                due_date = datetime(year, month, min(start_dt.day, last_day)).date()
                if due_date < now:
                    overdue_count += 1
            except: continue
        stats["overdue_loans"] = overdue_count
        
        conn.close()
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        
    return stats

if __name__ == "__main__":
    initialize_db()
