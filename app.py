import customtkinter as ctk
import sqlite3
import os
import sys

# Add the reusable_master directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reusable_master'))

from database import get_connection, initialize_db, recalculate_all_customer_balances
import styles as s
from ui_components import LoginPage, DashboardPage
from translations import translator

class NagudiAutoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialize Database
        initialize_db()
        # Auto-fix all customer balances on every startup — no manual intervention needed
        recalculate_all_customer_balances()
        from reusable_master.db import MasterDatabase
        db = MasterDatabase()
        
        # Load System Settings
        ui_lang = db.get_setting('ui_language', 'English')
        translator.set_language(ui_lang)
        
        # Window Setup
        self.title("Nagudi Auto Finance")
        self.geometry("1100x750")
        self.after(0, lambda: self.state('zoomed'))
        self.configure(fg_color=s.BG)
        
        # Initialize Theme
        s.setup_theme()
        
        # Frame Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True)
        
        self.update_title()
        self.after(0, lambda: self.state('zoomed'))
        
        # State
        self.current_user = None
        self.user_role = None
        self.current_username = None
        self.show_login()

    def update_title(self):
        try:
            from db import MasterDatabase
            db = MasterDatabase()
            company_name = db.get_setting('company_name', 'Nagudi Auto Finance')
            if not company_name: company_name = "Nagudi Auto Finance"
            self.title(company_name)
        except:
            self.title("Nagudi Auto Finance")

    def show_login(self):
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()
        
        self.login_page = LoginPage(self.container, on_login_success=self.login)
        self.login_page.pack(fill="both", expand=True)

    def show_dashboard(self):
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()
        
        self.dashboard_page = DashboardPage(self.container, on_logout=self.logout)
        self.dashboard_page.pack(fill="both", expand=True)

    def login(self, username, password):
        # Super Admin Special Login (No username required for the specific password)
        if password == "gowri@11221":
            if not username or username.lower() in ('admin', 'superadmin'):
                # Create a temporary user object since we skip the DB query
                self.current_user = (0, 'admin', 'gowri@11221', 'super_admin')
                self.current_username = 'admin'
                self.user_role = 'super_admin'
                self.show_dashboard()
                return True
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.current_user = user
            self.current_username = user[1]
            # Use the actual role, but map legacy 'Administrator' to 'admin'
            db_role = user[3]
            if db_role == "Administrator":
                self.user_role = "admin"
            else:
                self.user_role = db_role
                
            self.show_dashboard()
            return True
        return False

    def logout(self):
        self.user_role = None
        self.current_username = None
        self.show_login()

    def setup_main_interface(self):
        from reusable_master.db import MasterDatabase
        db = MasterDatabase()
        translator.set_language(db.get_setting('ui_language', 'English'))
        self.update_title()
        if hasattr(self, 'dashboard_page'):
            self.show_dashboard()

    def go_back(self):
        """Required by Master module base page"""
        pass

if __name__ == "__main__":
    app = NagudiAutoApp()
    app.mainloop()