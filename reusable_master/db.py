import sqlite3
import os

class MasterDatabase:
    _instance = None
    DB_NAME = "nagudi_auto.db"

    def __new__(cls, db_name=None):
        if cls._instance is None:
            cls._instance = super(MasterDatabase, cls).__new__(cls)
            if db_name:
                cls._instance.DB_NAME = db_name
            cls._instance.init_db()
        return cls._instance

    def get_connection(self):
        conn = sqlite3.connect(self.DB_NAME, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migration: Add created_at column to users if it doesn't exist
        try:
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'created_at' not in columns:
                # SQLite on some versions doesn't allow CURRENT_TIMESTAMP in ALTER TABLE ADD COLUMN
                cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
                # Update existing rows
                cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
                print("Migration (Master): Added created_at column to users table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Migration Warning (Master users): {e}")
        conn.commit()

        # Settings Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')



        # Default users
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           ('admin', 'gowri@11221', 'super_admin'))

        cursor.execute("SELECT * FROM users WHERE username = 'superadmin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           ('superadmin', 'gowri@11221', 'super_admin'))

        # Default settings
        defaults = {
            'receipt_language': 'Tamil',
            'ui_language': 'English',
            'software_activation': 'INACTIVE',
            'loan_limit': '15',
            'company_name': '',
            'company_address': '',
            'company_contact': ''
        }
        for k, v in defaults.items():
            cursor.execute("SELECT * FROM settings WHERE key = ?", (k,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))

        conn.commit()
        conn.close()

    def execute_query(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except sqlite3.Error as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def fetch_all(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def fetch_one(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return row

    def get_setting(self, key, default=None):
        row = self.fetch_one("SELECT value FROM settings WHERE key=?", (key,))
        return row[0] if row else default

    def set_setting(self, key, value):
        self.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
