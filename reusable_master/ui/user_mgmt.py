import customtkinter as ctk
from tkinter import messagebox
from db import MasterDatabase
import styles as s
from translations import t

class UserManagementPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.db = MasterDatabase()

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header ---
        self.header = ctk.CTkLabel(self, text=t("user_management"), font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.header.grid(row=0, column=0, padx=s.PAD_LG, pady=s.PAD_MD, sticky="w")

        # --- Content Container (Scrollable) ---
        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=s.PAD_LG, pady=(0, s.PAD_LG))
        self.content.grid_columnconfigure(0, weight=1)

        # --- Create User Form Card ---
        self.form_card, self.form_inner = self.create_card(self.content, t("add_new_user"))
        
        # Grid container for the form
        self.form_grid = ctk.CTkFrame(self.form_inner, fg_color="transparent")
        self.form_grid.pack(fill="x", expand=True)

        # Username
        ctk.CTkLabel(self.form_grid, text=t("username"), font=s.Styles.FONT_TINY, text_color=s.MUTED).grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
        self.username_entry = ctk.CTkEntry(self.form_grid, width=200, height=35, corner_radius=8, font=s.Styles.FONT_DEFAULT)
        self.username_entry.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Password
        ctk.CTkLabel(self.form_grid, text=t("password"), font=s.Styles.FONT_TINY, text_color=s.MUTED).grid(row=0, column=1, sticky="w", padx=5, pady=(5, 0))
        self.password_entry = ctk.CTkEntry(self.form_grid, width=200, height=35, corner_radius=8, font=s.Styles.FONT_DEFAULT, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Role
        ctk.CTkLabel(self.form_grid, text=t("role"), font=s.Styles.FONT_TINY, text_color=s.MUTED).grid(row=0, column=2, sticky="w", padx=5, pady=(5, 0))
        self.role_var = ctk.StringVar(value="admin")
        self.role_dropdown = ctk.CTkOptionMenu(self.form_grid, values=["admin", "user"], variable=self.role_var, width=150, height=35, 
                                               fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT, button_color=s.BORDER)
        self.role_dropdown.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        # Save Button
        self.btn_save = ctk.CTkButton(self.form_grid, text=t("create_user"), height=35, width=150, fg_color=s.PRIMARY, 
                                     hover_color=s.PRIMARY_HOVER, font=s.Styles.FONT_BOLD, command=self.save_user)
        self.btn_save.grid(row=1, column=3, padx=15, pady=5, sticky="w")

        # --- User List Card ---
        self.list_card, self.list_inner = self.create_card(self.content, t("existing_users"))
        self.users_container = ctk.CTkFrame(self.list_inner, fg_color="transparent")
        self.users_container.pack(fill="x", expand=True)

        self.on_show()

    def create_card(self, master, title=None):
        card = ctk.CTkFrame(master, fg_color=s.CARD, corner_radius=s.Styles.RADIUS, border_width=1, border_color=s.BORDER)
        card.pack(fill="x", pady=s.PAD_SM)
        
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=s.PAD_MD, pady=s.PAD_MD)
        
        if title:
            header = ctk.CTkFrame(inner, fg_color="transparent")
            header.pack(fill="x", pady=(0, 15))
            ctk.CTkLabel(header, text=title.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.PRIMARY).pack(side="left")
            line = ctk.CTkFrame(header, height=2, width=100, fg_color=s.BORDER)
            line.pack(side="left", padx=10)
        return card, inner

    def on_show(self):
        """Refresh user list"""
        # Clear container
        for widget in self.users_container.winfo_children():
            widget.destroy()

        # Load users
        try:
            users = self.db.fetch_all("SELECT id, username, role FROM users ORDER BY created_at DESC")
            
            # Table Header
            head = ctk.CTkFrame(self.users_container, fg_color=s.NAVY_DARK, height=40, corner_radius=6)
            head.pack(fill="x", pady=(0, 5))
            head.pack_propagate(False)
            
            ctk.CTkLabel(head, text=t("username").upper(), font=s.Styles.FONT_TINY_BOLD, text_color="white").place(relx=0.05, rely=0.5, anchor="w")
            ctk.CTkLabel(head, text=t("role").upper(), font=s.Styles.FONT_TINY_BOLD, text_color="white").place(relx=0.4, rely=0.5, anchor="w")
            ctk.CTkLabel(head, text=t("actions").upper(), font=s.Styles.FONT_TINY_BOLD, text_color="white").place(relx=0.75, rely=0.5, anchor="w")

            for i, (uid, uname, role) in enumerate(users):
                row = ctk.CTkFrame(self.users_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=0)
                row.pack(fill="x")
                row.pack_propagate(False)

                ctk.CTkLabel(row, text=uname, font=s.Styles.FONT_SMALL).place(relx=0.05, rely=0.5, anchor="w")
                ctk.CTkLabel(row, text=role.capitalize() if role else "User", font=s.Styles.FONT_SMALL).place(relx=0.4, rely=0.5, anchor="w")

                # Cannot delete self (assuming current_user exists in controller)
                current_uname = getattr(self.controller, 'current_username', None)
                if uname != current_uname and uname not in ['admin', 'superadmin']:
                    btn_del = ctk.CTkButton(row, text="Delete", width=80, height=28, fg_color=s.RED, hover_color="#991b1b", 
                                           font=s.Styles.FONT_TINY_BOLD, command=lambda u=uid, n=uname: self.delete_user(u, n))
                    btn_del.place(relx=0.75, rely=0.5, anchor="w")
                elif uname == current_uname:
                    ctk.CTkLabel(row, text="(Current Session)", font=s.Styles.FONT_TINY, text_color=s.MUTED).place(relx=0.75, rely=0.5, anchor="w")
                else:
                    ctk.CTkLabel(row, text="(System Locked)", font=s.Styles.FONT_TINY, text_color=s.MUTED).place(relx=0.75, rely=0.5, anchor="w")

        except Exception as e:
            print(f"Error loading users: {e}")
            # Fallback if created_at is still missing or query fails
            try:
                users = self.db.fetch_all("SELECT id, username, role FROM users ORDER BY id DESC")
                self._populate_user_list(users)
            except Exception as e2:
                print(f"Fallback loading failed: {e2}")

    def _populate_user_list(self, users):
        # Table Header
        head = ctk.CTkFrame(self.users_container, fg_color=s.NAVY_DARK, height=40, corner_radius=6)
        head.pack(fill="x", pady=(0, 5))
        head.pack_propagate(False)
        
        ctk.CTkLabel(head, text=t("username").upper(), font=s.Styles.FONT_TINY_BOLD, text_color="white").place(relx=0.05, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text=t("role").upper(), font=s.Styles.FONT_TINY_BOLD, text_color="white").place(relx=0.4, rely=0.5, anchor="w")
        ctk.CTkLabel(head, text=t("actions").upper(), font=s.Styles.FONT_TINY_BOLD, text_color="white").place(relx=0.75, rely=0.5, anchor="w")

        for i, (uid, uname, role) in enumerate(users):
            row = ctk.CTkFrame(self.users_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=0)
            row.pack(fill="x")
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=uname, font=s.Styles.FONT_SMALL).place(relx=0.05, rely=0.5, anchor="w")
            ctk.CTkLabel(row, text=role.capitalize() if role else "User", font=s.Styles.FONT_SMALL).place(relx=0.4, rely=0.5, anchor="w")

            # Cannot delete self (assuming current_user exists in controller)
            current_uname = getattr(self.controller, 'current_username', None)
            if uname != current_uname and uname not in ['admin', 'superadmin']:
                btn_del = ctk.CTkButton(row, text="Delete", width=80, height=28, fg_color=s.RED, hover_color="#991b1b", 
                                       font=s.Styles.FONT_TINY_BOLD, command=lambda u=uid, n=uname: self.delete_user(u, n))
                btn_del.place(relx=0.75, rely=0.5, anchor="w")
            elif uname == current_uname:
                ctk.CTkLabel(row, text="(Current Session)", font=s.Styles.FONT_TINY, text_color=s.MUTED).place(relx=0.75, rely=0.5, anchor="w")
            else:
                ctk.CTkLabel(row, text="(System Locked)", font=s.Styles.FONT_TINY, text_color=s.MUTED).place(relx=0.75, rely=0.5, anchor="w")

    def save_user(self):
        uname = self.username_entry.get().strip()
        pwd = self.password_entry.get().strip()
        role = self.role_var.get()

        if not uname or not pwd:
            messagebox.showwarning("Warning", t("field_required"))
            return

        try:
            self.db.execute_query("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (uname, pwd, role))
            messagebox.showinfo("Success", f"User '{uname}' created successfully!")
            self.username_entry.delete(0, 'end')
            self.password_entry.delete(0, 'end')
            self.on_show()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create user: {e}")

    def delete_user(self, uid, uname):
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete user '{uname}'?"):
            try:
                self.db.execute_query("DELETE FROM users WHERE id = ?", (uid,))
                messagebox.showinfo("Success", f"User '{uname}' deleted.")
                self.on_show()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete user: {e}")
