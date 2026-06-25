import customtkinter as ctk
from ui.base import BasePage
from ui.user_mgmt import UserManagementPage
from db import MasterDatabase
import shutil
import os
from tkinter import filedialog, messagebox
from datetime import datetime
import styles as s
from translations import t
from utils.activation import ActivationManager

class MasterPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, show_back_button=False)
        self.db = MasterDatabase()

        self.configure(fg_color=s.BG)
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(s.PAD_LG, s.PAD_MD), padx=s.PAD_LG, anchor="w", fill="x")
        
        self.header = ctk.CTkLabel(self.header_frame, text=t("master"), font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.header.pack(side="left")

        # Tabview
        self.tabview = ctk.CTkTabview(self, segmented_button_fg_color=s.CARD, 
                                      segmented_button_selected_color=s.GOLD,
                                      segmented_button_selected_hover_color=s.GOLD_DARK,
                                      segmented_button_unselected_hover_color=s.BORDER_ACTIVE,
                                      text_color=s.NAVY)
        self.tabview.pack(pady=(0, s.PAD_LG), padx=s.PAD_LG, fill="both", expand=True)

        # Create Tabs
        self.tab_preferences = self.tabview.add(t("preferences"))
        
        user_role = getattr(self.controller, 'user_role', None)
        is_admin = user_role in ['admin', 'super_admin']
        
        if is_admin:
            self.tab_user_mgmt = self.tabview.add(t("user_management"))
            self.tab_backup = self.tabview.add(t("data_backup"))

        # --- Preferences Tab ---
        self.setup_preferences_tab()

        if is_admin:
            # --- User Management Tab ---
            self.user_mgmt_page = UserManagementPage(self.tab_user_mgmt, controller)
            self.user_mgmt_page.pack(fill="both", expand=True)
            if hasattr(self.user_mgmt_page, 'back_btn'):
                 self.user_mgmt_page.back_btn.place_forget() 
            if hasattr(self.user_mgmt_page, 'header'):
                 self.user_mgmt_page.header.pack_forget()

            # --- Data Backup Tab ---
            self.setup_backup_tab()

        # --- System Settings Tab (Super Admin Only) ---
        if user_role == "super_admin":
            self.tab_settings = self.tabview.add(t("system_settings"))
            self.setup_settings_tab()

    def on_show(self):
        user_role = getattr(self.controller, 'user_role', None)
        is_admin = user_role in ['admin', 'super_admin']
        if is_admin and hasattr(self, 'user_mgmt_page') and hasattr(self.user_mgmt_page, 'on_show'):
            self.user_mgmt_page.on_show()

    def create_card(self, master, title=None):
        card = ctk.CTkFrame(master, fg_color=s.CARD, corner_radius=s.Styles.RADIUS, 
                            border_width=1, border_color=s.BORDER)
        card.pack(fill="x", padx=s.PAD_LG, pady=s.PAD_SM)
        
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=s.PAD_MD, pady=s.PAD_MD)
        
        if title:
            header = ctk.CTkFrame(inner, fg_color="transparent")
            header.pack(fill="x", pady=(0, 15))
            ctk.CTkLabel(header, text=title.upper(), font=s.Styles.FONT_TINY_BOLD, 
                         text_color=s.PRIMARY).pack(side="left")
            line = ctk.CTkFrame(header, height=2, width=100, fg_color=s.BORDER)
            line.pack(side="left", padx=10)
        return card, inner

    def create_setting_input(self, master, label, row):
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.pack(fill="x", pady=5)
        ctk.CTkLabel(f, text=label, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        entry = ctk.CTkEntry(f, width=s.Styles.FIELD_WIDTH + 100, height=s.Styles.FIELD_HEIGHT, 
                             border_color=s.BORDER, corner_radius=8, font=s.Styles.FONT_DEFAULT)
        entry.pack(anchor="w", pady=2)
        return entry

    def setup_preferences_tab(self):
        ui_lang = self.db.get_setting('ui_language', 'English')
        
        scroll = ctk.CTkScrollableFrame(self.tab_preferences, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        card, inner = self.create_card(scroll, t("preferences"))
        
        # UI Language Setting
        l1 = t("Software UI Language:") if ui_lang != "Tamil" else "மென்பொருள் UI மொழி:"
        ctk.CTkLabel(inner, text=l1, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        self.ui_lang_var = ctk.StringVar(value=ui_lang)
        self.ui_lang_dropdown = ctk.CTkOptionMenu(inner, values=["English", "Tamil"], variable=self.ui_lang_var,
                                                 width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT,
                                                 fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT,
                                                 button_color=s.BORDER, button_hover_color=s.BORDER_ACTIVE)
        self.ui_lang_dropdown.pack(pady=(5, 15), anchor="w")

        # Receipt Language Setting
        rl_lang = self.db.get_setting('receipt_language', 'Tamil')
        l2 = "Receipt Language:" if ui_lang != "Tamil" else "ரசீது மொழி:"
        ctk.CTkLabel(inner, text=l2, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        self.receipt_lang_var = ctk.StringVar(value=rl_lang)
        self.receipt_lang_dropdown = ctk.CTkOptionMenu(inner, values=["English", "Tamil"], variable=self.receipt_lang_var,
                                                      width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT,
                                                      fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT,
                                                      button_color=s.BORDER, button_hover_color=s.BORDER_ACTIVE)
        self.receipt_lang_dropdown.pack(pady=(5, 15), anchor="w")
        
        save_btn = ctk.CTkButton(inner, text=t("save"), height=s.Styles.FIELD_HEIGHT, width=200,
                                 fg_color=s.PRIMARY, hover_color=s.PRIMARY_HOVER, 
                                 font=s.Styles.FONT_BOLD, command=self.save_preferences)
        save_btn.pack(pady=(10, 0), anchor="w")

    def save_preferences(self):
        ui_lang = self.ui_lang_var.get()
        receipt_lang = self.receipt_lang_var.get()
        try:
            old_ui_lang = self.db.get_setting('ui_language', 'English')
            self.db.set_setting('ui_language', ui_lang)
            self.db.set_setting('receipt_language', receipt_lang)
            messagebox.showinfo("Success", "Preferences saved successfully!")
            if ui_lang != old_ui_lang and hasattr(self.controller, 'setup_main_interface'):
                self.controller.setup_main_interface()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preferences: {e}")

    def setup_backup_tab(self):
        ui_lang = self.db.get_setting('ui_language', 'English')
        
        scroll = ctk.CTkScrollableFrame(self.tab_backup, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        card, inner = self.create_card(scroll, t("data_backup"))
        
        ctk.CTkLabel(inner, text=t("Regular backup data msg"), 
                     font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(pady=(0, 20), anchor="w")

        self.backup_btn = ctk.CTkButton(inner, text=t("data_backup"), 
                                        height=s.Styles.FIELD_HEIGHT, width=250,
                                        fg_color=s.PRIMARY, hover_color=s.PRIMARY_HOVER, 
                                        font=s.Styles.FONT_BOLD, command=self.backup_data)
        self.backup_btn.pack(pady=5, anchor="w")

        self.restore_btn = ctk.CTkButton(inner, text=t("Restore Data"), 
                                         height=s.Styles.FIELD_HEIGHT, width=250,
                                         fg_color="transparent", border_width=1, border_color=s.RED,
                                         text_color=s.RED, hover_color="#fee2e2",
                                         font=s.Styles.FONT_BOLD, command=self.restore_data)
        self.restore_btn.pack(pady=5, anchor="w")
        
        ctk.CTkLabel(inner, text=t("Restore warning msg"), 
                     font=s.Styles.FONT_TINY, text_color=s.RED).pack(pady=(5, 0), anchor="w")

    def setup_settings_tab(self):
        self.scroll_settings = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.scroll_settings.pack(fill="both", expand=True)
        
        # 1. Company Details
        card1, inner1 = self.create_card(self.scroll_settings, "Company Details")
        
        self.co_name_entry = self.create_setting_input(inner1, "Company Name", 0)
        self.co_addr_entry = self.create_setting_input(inner1, "Company Address", 1)
        self.co_contact_entry = self.create_setting_input(inner1, "Contact Number", 2)
        
        # Login Page Image Upload
        img_f = ctk.CTkFrame(inner1, fg_color="transparent")
        img_f.pack(fill="x", pady=10)
        ctk.CTkLabel(img_f, text="Login Page Image:", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w")
        
        self.img_path_label = ctk.CTkLabel(img_f, text="No image selected", font=s.Styles.FONT_TINY, text_color=s.TEXT)
        self.img_path_label.pack(side="left", pady=2)
        
        ctk.CTkButton(img_f, text="Upload Image", width=120, height=30, fg_color=s.CARD_ALT, text_color=s.TEXT,
                      border_width=1, border_color=s.BORDER, font=s.Styles.FONT_TINY_BOLD,
                      command=self.upload_login_image).pack(side="right")
        self.login_image_path = None
        
        ctk.CTkButton(inner1, text="Save Company Details", height=s.Styles.FIELD_HEIGHT, width=220,
                      fg_color=s.PRIMARY, hover_color=s.PRIMARY_HOVER, font=s.Styles.FONT_BOLD,
                      command=self.save_company_details).pack(pady=(15, 0), anchor="w")

        # 2. Software Activation
        card2, inner2 = self.create_card(self.scroll_settings, "Software Activation")
        
        self.act_status_var = ctk.StringVar(value="Status: LOADING...")
        self.act_status_label = ctk.CTkLabel(inner2, textvariable=self.act_status_var, font=s.Styles.FONT_BOLD)
        self.act_status_label.pack(anchor="w", pady=(0, 10))
        
        self.act_key_entry = ctk.CTkEntry(inner2, placeholder_text="Enter Activation Key", width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT,
                                         border_color=s.BORDER, corner_radius=8, font=s.Styles.FONT_DEFAULT)
        self.act_key_entry.pack(anchor="w", pady=5)
        
        act_btn_f = ctk.CTkFrame(inner2, fg_color="transparent")
        act_btn_f.pack(fill="x", pady=10)
        
        self.act_btn = ctk.CTkButton(act_btn_f, text="Activate Software", width=160, height=35, 
                                     fg_color=s.GREEN, hover_color="#059669", font=s.Styles.FONT_TINY_BOLD,
                                     command=self.activate_software)
        self.act_btn.pack(side="left")
        
        self.deact_btn = ctk.CTkButton(act_btn_f, text="Deactivate", width=100, height=35, 
                                       fg_color="transparent", border_width=1, border_color=s.BORDER,
                                       text_color=s.MUTED, font=s.Styles.FONT_TINY_BOLD,
                                       command=self.deactivate_software)
        self.deact_btn.pack(side="left", padx=10)
        
        # Loan Limit
        ctk.CTkLabel(inner2, text="Demo Mode Loan Limit:", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", pady=(10, 0))
        limit_f = ctk.CTkFrame(inner2, fg_color="transparent")
        limit_f.pack(fill="x", pady=5)
        self.loan_limit_entry = ctk.CTkEntry(limit_f, width=100, height=35, border_color=s.BORDER, corner_radius=8)
        self.loan_limit_entry.pack(side="left")
        ctk.CTkButton(limit_f, text="Save Limit", width=100, height=35, fg_color=s.NAVY, 
                      hover_color=s.NAVY_DARK, font=s.Styles.FONT_TINY_BOLD, command=self.save_loan_limit).pack(side="left", padx=10)

        # 3. Data Maintenance
        card3, inner3 = self.create_card(self.scroll_settings, "Data Maintenance")
        
        ctk.CTkLabel(inner3, text="Warning: This will permanently delete all customers, loans, and payments.", 
                     font=s.Styles.FONT_TINY, text_color=s.RED).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkButton(inner3, text="ERASE ALL DATA (DEMO WIPE)", height=45, width=300,
                      fg_color=s.RED, hover_color="#e11d48", font=s.Styles.FONT_BOLD,
                      command=self.erase_all_data).pack(anchor="w")
        
        self.load_company_details()
        self.update_activation_ui()

    def upload_login_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.login_image_path = file_path
            self.img_path_label.configure(text=os.path.basename(file_path), text_color="black")

    def load_company_details(self):
        self.co_name_entry.delete(0, 'end')
        self.co_name_entry.insert(0, self.db.get_setting('company_name', ''))
        
        self.co_addr_entry.delete(0, 'end')
        self.co_addr_entry.insert(0, self.db.get_setting('company_address', ''))
        
        self.co_contact_entry.delete(0, 'end')
        self.co_contact_entry.insert(0, self.db.get_setting('company_contact', ''))
        
        img_path = self.db.get_setting('login_image_path', '')
        if img_path:
            self.login_image_path = img_path
            self.img_path_label.configure(text=os.path.basename(img_path), text_color="black")

    def save_company_details(self):
        try:
            self.db.set_setting('company_name', self.co_name_entry.get())
            self.db.set_setting('company_address', self.co_addr_entry.get())
            self.db.set_setting('company_contact', self.co_contact_entry.get())
            
            if hasattr(self, 'login_image_path') and self.login_image_path:
                self.db.set_setting('login_image_path', self.login_image_path)
            
            messagebox.showinfo("Success", "Company Details Saved!")
            
            # Refresh main application title
            if hasattr(self.controller, 'setup_main_interface'):
                self.controller.setup_main_interface()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save company details: {e}")

    def update_activation_ui(self):
        status = self.db.get_setting('software_activation', 'INACTIVE')
        limit = self.db.get_setting('loan_limit', '15')
        
        if status == 'ACTIVE':
            self.act_status_var.set("Status: ACTIVE (Full Version)")
            self.act_status_label.configure(text_color="green")
        else:
            self.act_status_var.set("Status: INACTIVE (Demo Mode)")
            self.act_status_label.configure(text_color="orange")
            
        self.loan_limit_entry.delete(0, 'end')
        self.loan_limit_entry.insert(0, limit)

    def activate_software(self):
        key = self.act_key_entry.get().strip()
        if not key:
            messagebox.showwarning("Warning", "Please enter an activation key.")
            return
            
        # Simplified validation (can be more complex)
        if key == "NAGUDI-2026-ACTV" or (key.startswith("NAGUDI-") and key.endswith("-2026")):
            self.db.set_setting('software_activation', 'ACTIVE')
            ActivationManager.invalidate_cache()
            self.update_activation_ui()
            messagebox.showinfo("Success", "Software Activated Successfully! Full Version Enabled.")
            self.act_key_entry.delete(0, 'end')
        else:
            messagebox.showerror("Invalid Key", "The activation key you entered is invalid. Please contact support.")

    def deactivate_software(self):
        self.db.set_setting('software_activation', 'INACTIVE')
        ActivationManager.invalidate_cache()
        self.update_activation_ui()
        messagebox.showinfo("Success", "Software Deactivated.")

    def save_loan_limit(self):
        limit = self.loan_limit_entry.get()
        if limit.isdigit():
            self.db.set_setting('loan_limit', limit)
            ActivationManager.invalidate_cache()
            messagebox.showinfo("Success", "Loan limit updated.")
        else:
            messagebox.showerror("Error", "Invalid limit.")

    def erase_all_data(self):
        if not messagebox.askyesno("CRITICAL WARNING", "This will PERMANENTLY delete all Customers, Loans, and Payments!\nAre you absolutely sure?"):
            return
        
        try:
            # Wipe nagudi_auto.db tables
            import sqlite3
            main_conn = sqlite3.connect("nagudi_auto.db")
            main_cursor = main_conn.cursor()
            tables = ["loans", "customers", "transactions", "vehicles", "makes", "models"]
            for table in tables:
                # Check if table exists before deleting
                main_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if main_cursor.fetchone():
                    main_cursor.execute(f"DELETE FROM {table}")
            main_conn.commit()
            main_conn.close()
            ActivationManager.invalidate_cache()
            messagebox.showinfo("Success", "All application data has been erased.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to erase data: {e}")

    def backup_data(self):
        try:
            source_file = self.db.DB_NAME
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"backup_{timestamp}.db"
            target_file = filedialog.asksaveasfilename(initialfile=default_filename, defaultextension=".db")
            if target_file:
                shutil.copy2(source_file, target_file)
                messagebox.showinfo("Success", f"Backup saved to:\n{target_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to backup:\n{e}")

    def restore_data(self):
        if not messagebox.askyesno("Confirm Restore", "WARNING: This will OVERWRITE all current data."):
            return
        try:
            source_file = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.db")])
            if source_file:
                shutil.copy2(source_file, self.db.DB_NAME)
                messagebox.showinfo("Success", "Data restored! Please restart the app.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore:\n{e}")
