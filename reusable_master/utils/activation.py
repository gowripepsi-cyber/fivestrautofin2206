import sqlite3
import os
import time

class ActivationManager:
    _cache = {}
    _CACHE_TTL = 60 # Seconds for activation/limit
    _LOAN_TTL = 5   # Seconds for loan count

    @classmethod
    def is_activated(cls):
        now = time.time()
        if 'is_activated' in cls._cache:
            val, ts = cls._cache['is_activated']
            if now - ts < cls._CACHE_TTL:
                return val

        # Check settings in nagudi_auto.db
        try:
            from db import MasterDatabase
            db = MasterDatabase()
            status = db.get_setting('software_activation', 'INACTIVE')
            result = status == 'ACTIVE'
            cls._cache['is_activated'] = (result, now)
            return result
        except:
            return False

    @classmethod
    def get_loan_limit(cls):
        now = time.time()
        if 'loan_limit' in cls._cache:
            val, ts = cls._cache['loan_limit']
            if now - ts < cls._CACHE_TTL:
                return val

        try:
            from db import MasterDatabase
            db = MasterDatabase()
            limit = db.get_setting('loan_limit', '15')
            result = int(limit)
            cls._cache['loan_limit'] = (result, now)
            return result
        except:
            return 15

    @classmethod
    def get_current_loan_count(cls):
        now = time.time()
        if 'loan_count' in cls._cache:
            val, ts = cls._cache['loan_count']
            if now - ts < cls._LOAN_TTL:
                return val

        try:
            # Import database connection from root
            import sys
            import os
            # Ensure root is in path or use absolute import
            from database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            # Count only active loans - closed loans are done and don't count against the limit
            cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'Active'")
            count = cursor.fetchone()[0]
            conn.close()
            cls._cache['loan_count'] = (count, now)
            return count
        except Exception as e:
            print(f"Error getting loan count: {e}")
            return 0

    @staticmethod
    def invalidate_cache():
        ActivationManager._cache = {}

    @staticmethod
    def verify_key(key):
        # A simple algorithm: NAGUDI + YEAR + RANDOM
        # Example valid keys: NAGUDI-2026-ACTV, NAGUDI-ADMIN-FULL
        valid_keys = ["NAGUDI-2026-ACTV", "NAGUDI-ADMIN-FULL", "AUTO-FINANCE-PRO"]
        if key in valid_keys:
            return True
        # Or a more algorithmic check:
        if key.startswith("NAGUDI-") and key.endswith("-2026"):
            return True
        return False
