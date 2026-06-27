import customtkinter as ctk
import styles as s

# Patch CTkOptionMenu globally to add a default border for visual consistency with input fields
_original_optionmenu_init = ctk.CTkOptionMenu.__init__
def _patched_optionmenu_init(self, master, *args, **kwargs):
    # Extract layout parameters
    width = kwargs.get('width', 140)
    height = kwargs.get('height', 28)
    fg_color = kwargs.get('fg_color', s.COMBO_BG)
    corner_radius = kwargs.get('corner_radius', 8)
    
    # Create the border frame as the wrapper (using master as its parent)
    border_frame = ctk.CTkFrame(master, fg_color=s.BORDER, corner_radius=corner_radius)
    
    # Strip custom options from kwargs to prevent duplicate parameter conflict
    menu_kwargs = kwargs.copy()
    for k in ['width', 'height', 'corner_radius', 'fg_color']:
        if k in menu_kwargs:
            del menu_kwargs[k]
            
    # Initialize the original CTkOptionMenu inside the border frame
    _original_optionmenu_init(self, border_frame, *args, width=width-2, height=height-2, 
                              corner_radius=corner_radius-1, fg_color=fg_color, **menu_kwargs)
    
    # Pack optionmenu inside the border frame to expand and fill it
    self.pack(padx=1, pady=1, fill="both", expand=True)
    
    # Keep reference to the border frame
    self.border_frame = border_frame
    
    # Redirect pack/grid/place layout calls to the border frame
    def custom_pack(*pargs, **pkwargs):
        border_frame.pack(*pargs, **pkwargs)
    def custom_grid(*gargs, **gkwargs):
        border_frame.grid(*gargs, **gkwargs)
    def custom_place(*plargs, **plkwargs):
        border_frame.place(*plargs, **plkwargs)
    def custom_forget():
        border_frame.pack_forget()
        border_frame.grid_forget()
        border_frame.place_forget()
        
    self.pack = custom_pack
    self.grid = custom_grid
    self.place = custom_place
    self.pack_forget = custom_forget
    self.grid_forget = custom_forget
    self.place_forget = custom_forget

ctk.CTkOptionMenu.__init__ = _patched_optionmenu_init

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import sys
import threading

# Ensure reusable_master is in path for standalone imports/execution
base_dir = os.path.dirname(os.path.abspath(__file__))
reusable_dir = os.path.join(base_dir, 'reusable_master')
if os.path.exists(reusable_dir) and reusable_dir not in sys.path:
    sys.path.append(reusable_dir)

from database import get_connection, get_dashboard_stats
from utils.activation import ActivationManager
import webbrowser
import tempfile
import calendar
from translations import t
import finance_logic as fl
import closure_logic as cl
from reusable_master.db import MasterDatabase

def add_months(sourcedate, months):
    """Adds months to a datetime object, handling year transitions and month length."""
    if not sourcedate: return None
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def get_company_name():
    """
    Fetches the company name from database settings with a fallback.
    """
    try:
        db = MasterDatabase()
        name = db.get_setting("company_name", "NAGUDI AUTO FINANCE")
        return name if name else "NAGUDI AUTO FINANCE"
    except:
        return "NAGUDI AUTO FINANCE"

def get_company_address():
    """
    Fetches the company address from database settings.
    """
    try:
        db = MasterDatabase()
        addr = db.get_setting("company_address", "")
        return addr if addr else ""
    except:
        return ""

def get_company_contact():
    """
    Fetches the company contact from database settings.
    """
    try:
        db = MasterDatabase()
        phone = db.get_setting("company_contact", "")
        return phone if phone else ""
    except:
        return ""

def format_indian_currency(amount):
    """
    Formats a numeric value into Indian currency format (e.g., ₹1,23,456.78).
    """
    try:
        if amount is None or amount == "": return "₹0.00"
        
        is_negative = float(amount) < 0
        amount_str = f"{abs(float(amount)):.2f}"
        
        if "." in amount_str:
            integer_part, decimal_part = amount_str.split(".")
        else:
            integer_part, decimal_part = amount_str, "00"
            
        if len(integer_part) <= 3:
            res = integer_part
        else:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            
            # Groups of two for the rest
            groups = []
            while remaining:
                if len(remaining) > 2:
                    groups.append(remaining[-2:])
                    remaining = remaining[:-2]
                else:
                    groups.append(remaining)
                    remaining = ""
            groups.reverse()
            res = ",".join(groups) + "," + last_three
            
        return ("-" if is_negative else "") + f"₹{res}.{decimal_part}"
    except:
        return f"₹{amount}"

class FloatingLabelEntry(ctk.CTkFrame):
    def __init__(self, master, label_text, is_password=False, show_gradient=False, **kwargs):
        super().__init__(master, fg_color="transparent", height=60, **kwargs)
        self.label_text = label_text
        self.is_password = is_password
        self.show_gradient = show_gradient
        self.pack_propagate(False)
        
        # Static grey line at the very bottom
        self.line = ctk.CTkFrame(self, height=1, fg_color="#cbd5e1")
        self.line.place(relx=0, rely=1, relwidth=1, anchor="sw")
        
        # Entry field
        self.entry = ctk.CTkEntry(self, height=35, fg_color="transparent", border_width=0, 
                                 text_color="#1e293b", font=ctk.CTkFont(size=16),
                                 show="*" if is_password else "")
        self.entry.place(relx=0, rely=1, relwidth=1, anchor="sw", y=-2)
        
        # Label (always visible, floats up on focus or text)
        self.label = ctk.CTkLabel(self, text=label_text, font=ctk.CTkFont(size=14, weight="normal"), text_color="#64748b")
        self.label.place(x=0, y=32)
        self.label.lift() # Fix for initial visibility
        
        self.entry.bind("<FocusIn>", self.on_focus_in)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        self.entry.bind("<KeyRelease>", self.on_key_release)
        self.label.bind("<Button-1>", lambda e: self.entry.focus())

    def on_focus_in(self, event):
        self.animate_label_up()
        if self.show_gradient:
            self.draw_gradient_line()
        else:
            self.line.configure(fg_color="#1e293b", height=2)

    def on_focus_out(self, event):
        if not self.entry.get():
            self.animate_label_down()
        self.line.configure(fg_color="#cbd5e1", height=1)
        if self.show_gradient and hasattr(self, 'gradient_canvas'):
            self.gradient_canvas.destroy()

    def on_key_release(self, event):
        if self.entry.get():
            self.animate_label_up()
        # Simplified: don't move label down on key release if empty, 
        # let FocusOut handle it to avoid flickering or attribute errors.

    def animate_label_up(self):
        self.label.configure(font=ctk.CTkFont(size=12, weight="bold"), text_color="#1e293b")
        self.label.place(x=0, y=0)
        self.label.lift()

    def animate_label_down(self):
        self.label.configure(font=ctk.CTkFont(size=14, weight="normal"), text_color="#64748b")
        self.label.place(x=0, y=32)
        self.label.lift()

    def draw_gradient_line(self):
        if hasattr(self, 'gradient_canvas'): self.gradient_canvas.destroy()
        self.gradient_canvas = ctk.CTkCanvas(self, height=2, highlightthickness=0, bd=0)
        self.gradient_canvas.place(relx=0, rely=1, relwidth=1, anchor="sw")
        
        width = self.winfo_width()
        if width < 10: width = 450 # Default width fallback
        
        # Cyan (#00D2FF) to Magenta (#9733EE)
        c1 = (0, 210, 255)
        c2 = (151, 51, 238)
        
        for i in range(width):
            r = int(c1[0] + (c2[0] - c1[0]) * (i / width))
            g = int(c1[1] + (c2[1] - c1[1]) * (i / width))
            b = int(c1[2] + (c2[2] - c1[2]) * (i / width))
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.gradient_canvas.create_line(i, 0, i, 2, fill=color)

    def get(self):
        return self.entry.get()
        
    def delete(self, *args):
        self.entry.delete(*args)
        self.animate_label_down()

class GradientButton(ctk.CTkCanvas):
    def __init__(self, master, text, command, width=450, height=55, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg="white", cursor="hand2", **kwargs)
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        self.draw_button()

    def draw_button(self, hover=False):
        from PIL import ImageDraw, ImageTk
        self.delete("all")
        
        # Create gradient image
        img = Image.new("RGB", (self.width, self.height), "#ffffff")
        draw = ImageDraw.Draw(img)
        
        # Electric Cyan (#00D2FF) to Vivid Magenta/Purple (#9733EE)
        c1 = (0, 210, 255)
        c2 = (151, 51, 238)
        
        if hover:
            # Slightly brighter or darker on hover
            c1 = (20, 230, 255)
            c2 = (171, 71, 255)

        for i in range(self.width):
            r = int(c1[0] + (c2[0] - c1[0]) * (i / self.width))
            g = int(c1[1] + (c2[1] - c1[1]) * (i / self.width))
            b = int(c1[2] + (c2[2] - c1[2]) * (i / self.width))
            draw.line([(i, 0), (i, self.height)], fill=(r, g, b))
        
        # Rounded corners (pill shape)
        mask = Image.new("L", (self.width, self.height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, self.width, self.height], radius=self.height//2, fill=255)
        
        # Apply mask
        self.button_img = ImageTk.PhotoImage(img)
        self.mask_img = ImageTk.PhotoImage(mask)
        
        # We need to use a trick for transparent background in Canvas
        # For now, just draw the pill shape
        self.create_image(self.width//2, self.height//2, image=self.button_img)
        
        # Text
        self.create_text(self.width//2, self.height//2, text=self.text, fill="white", 
                         font=ctk.CTkFont(size=16, weight="bold"))

    def on_enter(self, event):
        self.draw_button(hover=True)

    def on_leave(self, event):
        self.draw_button(hover=False)

def add_focus_hover_effect(widget):
    """Adds a dynamic background shift when hover/focus as requested by user."""
    def on_enter(e):
        if not getattr(widget, "_focused", False):
            widget.configure(fg_color=s.ENTRY_BG_ACTIVE, text_color=s.ENTRY_TEXT_ACTIVE)
    def on_leave(e):
        if not getattr(widget, "_focused", False):
            widget.configure(fg_color=s.CARD, text_color=s.TEXT)
    def on_focus_in(e):
        widget._focused = True
        widget.configure(fg_color=s.ENTRY_BG_ACTIVE, text_color=s.ENTRY_TEXT_ACTIVE)
    def on_focus_out(e):
        widget._focused = False
        widget.configure(fg_color=s.CARD, text_color=s.TEXT)
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)
    widget.bind("<FocusIn>", on_focus_in)
    widget.bind("<FocusOut>", on_focus_out)

def add_combo_hover_effect(widget):
    """Adds hover feedback for CTkOptionMenu as requested by user."""
    def on_enter(e):
        widget.configure(fg_color=s.COMBO_BG_HOVER)
    def on_leave(e):
        widget.configure(fg_color=s.COMBO_BG)
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)



class CalendarPopup(ctk.CTkToplevel):
    def __init__(self, master, callback, initial_date=None, pos_x=None, pos_y=None, **kwargs):
        from tkcalendar import Calendar
        super().__init__(master, **kwargs)
        self.title("Select Date")
        
        if pos_x is not None and pos_y is not None:
            self.geometry(f"300x320+{pos_x}+{pos_y}")
        else:
            self.geometry("300x320")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.transient(master)
        self.grab_set()
        self.lift()
        self.focus_force()
        
        self.callback = callback
        
        # Style the calendar
        self.cal = Calendar(self, 
                            selectmode='day', 
                            date_pattern='dd-mm-yyyy',
                            background=s.NAVY,
                            foreground='white',
                            headersbackground=s.NAVY_DARK,
                            headersforeground='white',
                            selectbackground=s.GOLD,
                            selectforeground='white',
                            normalbackground='white',
                            normalforeground=s.TEXT,
                            weekendbackground='#f1f5f9',
                            weekendforeground=s.TEXT,
                            othermonthbackground='#f8fafc',
                            othermonthforeground='#94a3b8')
        self.cal.pack(padx=10, pady=10, fill="both", expand=True)
        
        if initial_date:
            try:
                # Expecting DD-MM-YYYY or a datetime object
                if isinstance(initial_date, str):
                    d, m, y = map(int, initial_date.split('-'))
                    self.cal.selection_set(datetime(y, m, d))
                elif isinstance(initial_date, datetime):
                    self.cal.selection_set(initial_date)
            except: pass
            
        btn_frames = ctk.CTkFrame(self, fg_color="transparent")
        btn_frames.pack(fill="x", pady=10)
        
        self.select_btn = ctk.CTkButton(btn_frames, text="Select", width=100, fg_color=s.GOLD, hover_color=s.GOLD_DARK,
                                         command=self.on_select)
        self.select_btn.pack(side="left", padx=(40, 5))
        
        self.cancel_btn = ctk.CTkButton(btn_frames, text="Cancel", width=100, fg_color="transparent", border_width=1,
                                         border_color="#94a3b8", text_color="#1e293b", hover_color="#f1f5f9",
                                         command=self.destroy)
        self.cancel_btn.pack(side="left", padx=5)

    def on_select(self):
        self.callback(self.cal.get_date())
        self.destroy()

class DatePickerWidget(ctk.CTkFrame):
    def __init__(self, master, height=35, default_date=None, entry_width=180, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_change = on_change
        
        self.entry = ctk.CTkEntry(self, width=entry_width, height=height, corner_radius=6, border_color=s.BORDER, 
                                 fg_color=s.CARD, text_color=s.TEXT, font=s.Styles.FONT_DEFAULT)
        self.entry.pack(side="left")
        add_focus_hover_effect(self.entry)
        
        self.btn = ctk.CTkButton(self, text="📅", width=35, height=height, corner_radius=6,
                                 fg_color=s.NAVY, hover_color=s.NAVY_DARK,
                                 command=self.open_calendar)
        self.btn.pack(side="left", padx=(5, 0))
        
        if default_date:
            self.set_date(default_date)

    def open_calendar(self):
        initial = self.get()
        # Calculate screen position
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        
        # Find the root window for Toplevel
        root = self.winfo_toplevel()
        CalendarPopup(root, callback=self.set_date, initial_date=initial, pos_x=x, pos_y=y)

    def get(self):
        return self.entry.get()

    def set_date(self, date_val):
        self.entry.delete(0, 'end')
        if isinstance(date_val, datetime):
            self.entry.insert(0, date_val.strftime("%d-%m-%Y"))
        else:
            # Assume it's a string, if it's in YYYY-MM-DD format (from DB), convert it
            try:
                if len(date_val) == 10 and date_val[4] == '-' and date_val[7] == '-':
                    y, m, d = date_val.split('-')
                    date_val = f"{d}-{m}-{y}"
            except: pass
            self.entry.insert(0, date_val)
        
        if self.on_change:
            self.on_change(self.get())
            
    def delete(self, *args):
        self.entry.delete(*args)

class StarRating(ctk.CTkFrame):
    def __init__(self, master, label_text, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.rating = 0
        self.stars = []
        
        lbl = ctk.CTkLabel(self, text=label_text, font=s.Styles.FONT_TINY, text_color=s.MUTED)
        lbl.pack(anchor="w", padx=2)
        
        self.star_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.star_frame.pack(anchor="w")
        
        for i in range(1, 6):
            star = ctk.CTkLabel(self.star_frame, text="★", font=ctk.CTkFont(size=24), 
                                text_color="#cbd5e1", cursor="hand2")
            star.pack(side="left", padx=2)
            star.bind("<Button-1>", lambda e, r=i: self.set_rating(r))
            star.bind("<Enter>", lambda e, r=i: self.hover_stars(r))
            star.bind("<Leave>", lambda e: self.render_stars())
            self.stars.append(star)

    def set_rating(self, rating):
        self.rating = rating
        self.render_stars()

    def hover_stars(self, rating):
        for i, star in enumerate(self.stars):
            if i < rating:
                star.configure(text_color="#f59e0b") # Gold/Yellow
            else:
                star.configure(text_color="#cbd5e1") # Gray

    def render_stars(self):
        for i, star in enumerate(self.stars):
            if i < self.rating:
                star.configure(text_color="#d97706") # Gold (Darker)
            else:
                star.configure(text_color="#cbd5e1") # Gray

    def get(self):
        return str(self.rating)

    def set(self, rating_val):
        try:
            if isinstance(rating_val, str):
                if rating_val.isdigit():
                    self.rating = int(rating_val)
                else:
                    # Mapping for old data
                    rv = rating_val.capitalize()
                    mapping = {"Excellent": 5, "Good": 4, "Average": 3, "Poor": 2}
                    self.rating = mapping.get(rv, 0)
            else:
                self.rating = int(rating_val or 0)
        except:
            self.rating = 0
        self.render_stars()

class SearchableComboBox(ctk.CTkFrame):
    def __init__(self, master, values=None, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, variable=None, placeholder_text="", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.placeholder = placeholder_text
        self.values = values if values else []
        self.filtered_values = self.values
        self.variable = variable if variable else ctk.StringVar()
        self.variable.trace_add("write", self._on_var_write)
        self.after_id = None
        self._position_after_id = None
        self.popup = None
        self.listbox = None
        self._is_showing = False
        
        self.entry = ctk.CTkEntry(self, width=width-35, height=height, 
                                 placeholder_text=self.placeholder,
                                 corner_radius=8, border_color=s.BORDER, 
                                 fg_color=s.CARD, text_color=s.TEXT, font=s.Styles.FONT_DEFAULT)
        # We don't use direct textvariable to avoid placeholder conflicts
        self.entry.pack(side="left")
        add_focus_hover_effect(self.entry)
        
        self.btn = ctk.CTkButton(self, text="▼", width=30, height=height, corner_radius=8,
                                 fg_color=s.NAVY, hover_color=s.NAVY_DARK, command=self.update_results)
        self.btn.pack(side="left", padx=(5, 0))
        
        self.entry.bind("<KeyRelease>", self.update_results)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        self.entry.bind("<Button-1>", self.update_results)
        self.entry.bind("<FocusIn>", self.update_results)
        
        # New: Bindings to ensure popup closes when tab switched or app minimized
        self.bind("<Unmap>", lambda e: self.close_popup())
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self._position_after_id:
            self.after_cancel(self._position_after_id)
            self._position_after_id = None
        self.close_popup()

    def update_results(self, event=None):
        if not self.winfo_exists(): return
        
        # Get raw text from entry for 100% reliability
        search_term = self.entry.get().strip().lower()
        
        # Filter logic - show all if the entry is empty
        if not search_term:
            self.filtered_values = self.values
        else:
            self.filtered_values = [v for v in self.values if search_term in v.lower()]
        
        # If popup is already open, just refresh the list in-place
        if self._is_showing and self.popup and self.popup.winfo_exists():
            self.render_list()
        else:
            self._position_after_id = None
            self.show_popup()

    def show_popup(self, event=None):
        if self._is_showing: return
        self._is_showing = True
        
        if not self.popup or not self.popup.winfo_exists():
            # Standard tk.Toplevel is less focus-aggressive
            self.popup = tk.Toplevel(self.winfo_toplevel())
            self.popup.overrideredirect(True)
            self.popup.configure(bg=s.CARD)
            
            self.listbox = tk.Listbox(self.popup, font=s.Styles.FONT_DEFAULT, 
                                     fg=s.TEXT, bg=s.CARD, 
                                     selectbackground=s.PRIMARY, selectforeground="white",
                                     borderwidth=1, relief="solid", highlightthickness=0)
            self.listbox.pack(fill="both", expand=True)
            self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
            self.listbox.bind("<Return>", self.on_listbox_select)

        # Update layout coordinates
        self.update_idletasks()
        try:
            ex = self.entry.winfo_rootx()
            ey = self.entry.winfo_rooty()
            ew = self.entry.winfo_width() + self.btn.winfo_width() + 5
            eh = self.entry.winfo_height()
            
            num_items = len(self.filtered_values)
            h = min(300, (num_items * 28) + 10 if num_items > 0 else 50)
            
            self.popup.geometry(f"{ew}x{h}+{ex}+{ey+eh+2}")
            self.popup.start_x = ex
            self.popup.start_y = ey
            
            self.render_list()
            self.popup.deiconify()
            self.popup.lift()
            self.popup.attributes("-topmost", True)
        except:
            self._is_showing = False
            return
        
        self.check_position_loop()

    def check_position_loop(self):
        if not self._is_showing or not self.popup or not self.popup.winfo_exists():
            self._position_after_id = None
            return
        try:
            curr_x = self.entry.winfo_rootx()
            curr_y = self.entry.winfo_rooty()
            # If position changed significantely (likely scrolling), close popup
            if abs(curr_x - self.popup.start_x) > 5 or abs(curr_y - self.popup.start_y) > 5:
                self.close_popup()
                return
            self._position_after_id = self.after(150, self.check_position_loop)
        except: self.close_popup()

    def render_list(self):
        if not self.listbox or not self.listbox.winfo_exists(): return
        self.listbox.delete(0, tk.END)
        
        if not self.filtered_values:
            self.listbox.insert(tk.END, " No matches found")
            return

        for val in self.filtered_values:
            self.listbox.insert(tk.END, f" {val}")

    def on_listbox_select(self, event=None):
        if not self.listbox.curselection(): return
        index = self.listbox.curselection()[0]
        value = self.listbox.get(index).strip()
        if value == "No matches found": return
        self.select_value(value)

    def select_value(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        self.variable.set(value)
        self.close_popup()
        if hasattr(self, "_command") and self._command:
            self._command(value)
        self.entry.focus_set()

    def on_focus_out(self, event):
        # Slightly longer delay for listbox selection to register
        self.after(300, self.close_popup)

    def close_popup(self):
        self._is_showing = False
        if self._position_after_id:
            self.after_cancel(self._position_after_id)
            self._position_after_id = None
            
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
            self.popup = None
            self.listbox = None

    def configure_values(self, new_values):
        self.values = new_values
        self.filtered_values = new_values
        if self.popup and self.popup.winfo_exists():
            self.render_list()

    def _on_var_write(self, *args):
        # Sync entry with variable if it changed programmatically
        new_val = self.variable.get()
        if self.entry.get() != new_val:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, new_val)

    def set(self, value):
        """Set the value programmatically"""
        if value:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, value)
            self.variable.set(value)
        else:
            self.entry.delete(0, tk.END)
            self.variable.set("")

    def get(self):
        """Get the current value from entry"""
        val = self.entry.get().strip()
        if val:
            return val
        return self.variable.get()

class BaseTab(ctk.CTkScrollableFrame):
    def __init__(self, master, title, **kwargs):
        super().__init__(master, fg_color=s.BG, corner_radius=s.Styles.RADIUS, **kwargs)
        self.title = title
        self._last_refresh = 0
        self._is_dirty = True
        self.edit_id = None
        
        # Header with enhanced styling
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(s.PAD_LG, s.PAD_MD), padx=s.PAD_LG, anchor="w", fill="x")
        
        self.header = ctk.CTkLabel(self.header_frame, text=title, font=s.Styles.FONT_H1, text_color=s.TEXT)
        self.header.pack(side="left")

    def run_in_background(self, task_func, on_success):
        """Helper to run a data-fetching function in a background thread."""
        def wrapper():
            try:
                result = task_func()
                if self.winfo_exists():
                    self.after(0, lambda: on_success(result))
            except Exception as e:
                print(f"Background task error: {e}")
        
        import threading
        threading.Thread(target=wrapper, daemon=True).start()

    def render_list_chunked(self, container, data, render_row_func, chunk_size=10, on_complete=None, clear=True, start_row_idx=0):
        """Helper to render a list of widgets in chunks to keep UI responsive."""
        if not self.winfo_exists() or not container.winfo_exists(): return
        
        # Clear existing if requested
        if clear:
            for widget in container.winfo_children():
                widget.destroy()
            
        if not data:
            if on_complete: on_complete(0)
            return

        def render_next_chunk(start_idx):
            if not self.winfo_exists() or not container.winfo_exists(): return
            
            end_idx = min(start_idx + chunk_size, len(data))
            for i in range(start_idx, end_idx):
                # Pass the global row index to ensure correct alternating colors
                render_row_func(start_row_idx + i, data[i])
            
            if end_idx < len(data):
                self.after(10, lambda: render_next_chunk(end_idx))
            elif on_complete:
                on_complete(len(data))
        
        render_next_chunk(0)

    def mark_dirty(self):
        self._is_dirty = True

    def create_card(self, title=None, master=None):
        target = master if master else self
        card = ctk.CTkFrame(target, fg_color=s.CARD, corner_radius=s.Styles.RADIUS, 
                            border_width=1, border_color=s.BORDER)
        if not master:
            card.pack(fill="x", padx=s.PAD_LG, pady=s.PAD_SM)

        
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=s.PAD_MD, pady=s.PAD_MD)
        
        content = inner
        if title:
            # Section header with primary accent
            header = ctk.CTkFrame(inner, fg_color="transparent")
            header.pack(side="top", fill="x", pady=(0, 15))
            
            ctk.CTkLabel(header, text=title.upper(), font=s.Styles.FONT_TINY_BOLD, 
                         text_color=s.PRIMARY).pack(side="left")
            
            # Subtle line
            line = ctk.CTkFrame(header, height=2, width=100, fg_color=s.BORDER)
            line.pack(side="left", padx=10)
            
            # Separate frame for content to avoid grid/pack conflict with header
            content = ctk.CTkFrame(inner, fg_color="transparent")
            content.pack(fill="both", expand=True)
            
        return card, content

    def create_input(self, master, label, row, col, width=s.Styles.FIELD_WIDTH, columnspan=1, **kwargs):
        container = ctk.CTkFrame(master, fg_color="transparent")
        container.grid(row=row, column=col, columnspan=columnspan, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")

        
        ctk.CTkLabel(container, text=label, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        
        entry = ctk.CTkEntry(container, width=width, height=s.Styles.FIELD_HEIGHT, 
                             corner_radius=8, border_color=s.BORDER, 
                             fg_color=s.CARD, text_color=s.TEXT, font=s.Styles.FONT_DEFAULT, **kwargs)
        entry.pack(anchor="w")
        add_focus_hover_effect(entry)
        return entry

    def create_select(self, master, label, options, row, col, width=s.Styles.FIELD_WIDTH, columnspan=1, **kwargs):
        container = ctk.CTkFrame(master, fg_color="transparent")
        container.grid(row=row, column=col, columnspan=columnspan, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")

        
        ctk.CTkLabel(container, text=label, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        
        var = ctk.StringVar(value=t("select") + "...")
        select = ctk.CTkOptionMenu(container, values=options, width=width, height=s.Styles.FIELD_HEIGHT, 
                                   variable=var, corner_radius=8, fg_color=s.COMBO_BG, 
                                   text_color=s.COMBO_TEXT, button_color=s.BORDER,
                                   button_hover_color=s.BORDER_ACTIVE, font=s.Styles.FONT_DEFAULT, **kwargs)
        select.pack(anchor="w")
        add_combo_hover_effect(select)
        return select, var

    def create_searchable_select(self, master, label, options, row, col, width=s.Styles.FIELD_WIDTH, columnspan=1, **kwargs):
        container = ctk.CTkFrame(master, fg_color="transparent")
        container.grid(row=row, column=col, columnspan=columnspan, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")
        
        ctk.CTkLabel(container, text=label, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        
        var = ctk.StringVar()
        placeholder = t("select") + "..."
        search_combo = SearchableComboBox(container, values=options, width=width, height=s.Styles.FIELD_HEIGHT, 
                                         variable=var, placeholder_text=placeholder, **kwargs)
        search_combo.pack(anchor="w")
        return search_combo, var

    def create_radio_group(self, master, label_text, options, row, col, default_value=None, command=None):
        container = ctk.CTkFrame(master, fg_color="transparent")
        container.grid(row=row, column=col, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")
        
        lbl = ctk.CTkLabel(container, text=label_text, font=s.Styles.FONT_TINY, text_color=s.MUTED)
        lbl.pack(anchor="w", padx=2)
        
        radio_frame = ctk.CTkFrame(container, fg_color="transparent")
        radio_frame.pack(anchor="w", pady=(2, 0))
        
        var = ctk.StringVar(value=default_value if default_value else options[0])
        for opt in options:
            rb = ctk.CTkRadioButton(radio_frame, text=opt, variable=var, value=opt, 
                                     font=s.Styles.FONT_DEFAULT, border_color=s.PRIMARY, 
                                     hover_color=s.PRIMARY_HOVER, command=command)
            rb.pack(side="left", padx=(0, 20))
        return var

    def create_date_picker(self, master, label, row, col, default_date=None, on_change=None):
        container = ctk.CTkFrame(master, fg_color="transparent")
        container.grid(row=row, column=col, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")
        
        ctk.CTkLabel(container, text=label, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        
        dp = DatePickerWidget(container, default_date=default_date, height=s.Styles.FIELD_HEIGHT, on_change=on_change)
        dp.pack(anchor="w")
        return dp

    def create_action_buttons(self, master, save_text, save_command, clear_command):
        actions = ctk.CTkFrame(master, fg_color="transparent")
        actions.grid(row=20, column=0, columnspan=10, pady=(s.PAD_MD, 0), sticky="ew")
        
        save_btn = ctk.CTkButton(actions, text=save_text, height=s.Styles.FIELD_HEIGHT+5, width=220, 
                                 fg_color=s.PRIMARY, hover_color=s.PRIMARY_HOVER, 
                                 font=s.Styles.FONT_BOLD, command=save_command)
        save_btn.pack(side="left", padx=(0, s.PAD_MD))
        
        clear_btn = ctk.CTkButton(actions, text=t("clear"), height=s.Styles.FIELD_HEIGHT+5, width=120, 
                                  fg_color="transparent", border_width=1, border_color=s.BORDER,
                                  text_color=s.MUTED, font=s.Styles.FONT_BOLD,
                                  command=clear_command)
        clear_btn.pack(side="left")
        return save_btn, clear_btn

class LoginPage(ctk.CTkFrame):
    def __init__(self, master, on_login_success, **kwargs):
        super().__init__(master, fg_color="#F5F5F5", **kwargs)
        self.on_login_success = on_login_success
        
        # Center the login card
        # Note: Shadow is simulated with a slightly larger frame behind or just border
        self.card = ctk.CTkFrame(self, fg_color="white", corner_radius=30, width=500, height=650, border_width=0)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(False)
        
        # Inner padding frame
        self.inner = ctk.CTkFrame(self.card, fg_color="transparent")
        self.inner.pack(fill="both", expand=True, padx=50, pady=60)
        
        # Header: Bold sans-serif "Welcome"
        self.welcome_label = ctk.CTkLabel(self.inner, text="Welcome", 
                                         font=ctk.CTkFont(family="sans-serif", size=32, weight="bold"), 
                                         text_color="#1e293b")
        self.welcome_label.pack(pady=(40, 20))
        
        # Form
        self.username_entry = FloatingLabelEntry(self.inner, label_text=t("username"), show_gradient=True)
        self.username_entry.pack(fill="x", pady=15)
        
        # Password field container for the toggle
        self.pass_container = ctk.CTkFrame(self.inner, fg_color="transparent")
        self.pass_container.pack(fill="x", pady=15)
        
        self.password_entry = FloatingLabelEntry(self.pass_container, label_text=t("password"), is_password=True)
        self.password_entry.pack(fill="x")
        
        # Eye icon toggle
        self.eye_btn = ctk.CTkLabel(self.pass_container, text="Show", font=ctk.CTkFont(size=12, weight="bold"), cursor="hand2", text_color="#94a3b8")
        self.eye_btn.place(relx=1.0, rely=0.6, anchor="e", x=-5)
        self.eye_btn.bind("<Button-1>", self.toggle_password)
        self.password_is_visible = False
        
        self.error_label = ctk.CTkLabel(self.inner, text="", text_color="#ef4444", font=ctk.CTkFont(size=12))
        self.error_label.pack(pady=5)
        
        # Login Button: Pill-shaped gradient
        self.login_button = GradientButton(self.inner, text="LOGIN", command=self.handle_login, width=400, height=55)
        self.login_button.pack(pady=(30, 20))
        
        # Footer
        self.footer_label = ctk.CTkLabel(self.inner, text="Sun infotech software solutions", 
                                        font=ctk.CTkFont(size=11), text_color="#94a3b8")
        self.footer_label.pack(side="bottom")

    def toggle_password(self, event):
        if self.password_is_visible:
            self.password_entry.entry.configure(show="*")
            self.eye_btn.configure(text="Show")
            self.password_is_visible = False
        else:
            self.password_entry.entry.configure(show="")
            self.eye_btn.configure(text="Hide")
            self.password_is_visible = True

    def handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not password:
            self.error_label.configure(text="Please enter password")
            return

        if not self.on_login_success(username, password):
            self.error_label.configure(text=t("invalid_login"))

class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, on_logout, **kwargs):
        super().__init__(master, fg_color=s.BG, **kwargs)
        self.on_logout = on_logout
        self.current_tab = None
        self.vehicle_menu_open = False
        self.loan_menu_open = False
        self._after_id = None
        self._tab_cache = {}
        self._current_tab_name = None
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=s.SIDEBAR_W, fg_color=s.NAVY_DARK, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Sidebar Header (Compact Red)
        self.logo_wrap = ctk.CTkFrame(self.sidebar, fg_color=s.RED, corner_radius=8, height=35)
        self.logo_wrap.pack(pady=(10, 10), padx=10, fill="x")
        self.logo_wrap.pack_propagate(False)
        
        self.brand_label = ctk.CTkLabel(self.logo_wrap, text="AUTO FINANCE", font=s.Styles.FONT_BOLD, text_color="white")
        self.brand_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Sidebar Buttons
        self.btn_dashboard = self.create_nav_button("🏠  " + t("dashboard"), command=lambda: self.show_tab("Dashboard"))
        self.btn_customers = self.create_nav_button("👤  " + t("customers"), command=lambda: self.show_tab("Customers"))
        
        self.btn_vehicle = self.create_nav_button("▶  " + t("vechicle"), command=self.toggle_vehicle_menu)
        self.submenu_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        
        self.btn_purchase = self.create_nav_button("🛒  " + t("purchase"), command=lambda: self.show_tab("Purchase"), master=self.submenu_frame)
        self.btn_sales = self.create_nav_button("📈  " + t("sales"), command=lambda: self.show_tab("Sales"), master=self.submenu_frame)
        self.btn_masterdata = self.create_nav_button("📋  " + t("master_sub_menus"), command=lambda: self.show_tab("MasterData"), master=self.submenu_frame)

        self.btn_purchase.pack(pady=2, fill="x")
        self.btn_sales.pack(pady=2, fill="x")
        self.btn_masterdata.pack(pady=2, fill="x")

        self.btn_loans = self.create_nav_button("▶  " + t("loans_menu"), command=self.toggle_loan_menu)
        self.submenu_loan_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.btn_loan_history = self.create_nav_button("💰  " + t("new_loan"), command=lambda: self.show_tab("Loans"), master=self.submenu_loan_frame)
        self.btn_payments = self.create_nav_button("💳  " + t("payments"), command=lambda: self.show_tab("Payments"), master=self.submenu_loan_frame)
        
        self.btn_loan_history.pack(pady=2, fill="x")
        self.btn_rc_pledge = self.create_nav_button("📄  " + t("rc_pledge_loan"), command=lambda: self.show_tab("RCPledge"), master=self.submenu_loan_frame)
        self.btn_rc_pledge.pack(pady=2, fill="x")
        self.btn_payments.pack(pady=2, fill="x")

        self.btn_dunning = self.create_nav_button("⚖️  " + t("dunning_register"), command=lambda: self.show_tab("Dunning"))

        self.btn_cashbank = self.create_nav_button("🏦  " + t("cash_bank"), command=lambda: self.show_tab("CashBank"))
        self.btn_reports = self.create_nav_button("📊  " + t("reports"), command=lambda: self.show_tab("Reports"))
        self.btn_master = self.create_nav_button("⚙️  " + t("master"), command=lambda: self.show_tab("Master"))
        
        self.btn_profit = self.create_nav_button("📈  " + t("profit_tracking"), command=lambda: self.show_tab("Profit"))
        self.btn_expense = self.create_nav_button("💸  " + t("expense_management"), command=lambda: self.show_tab("Expense"))
        self.btn_payroll = self.create_nav_button("👥  " + t("payroll_management"), command=lambda: self.show_tab("Payroll"))
        
        self.nav_buttons = {
            "Dashboard": self.btn_dashboard,
            "Customers": self.btn_customers,
            "Purchase": self.btn_purchase,
            "Sales": self.btn_sales,
            "MasterData": self.btn_masterdata,
            "Loans": self.btn_loan_history,
            "RCPledge": self.btn_rc_pledge,
            "Payments": self.btn_payments,
            "Dunning": self.btn_dunning,
            "CashBank": self.btn_cashbank,
            "Reports": self.btn_reports,
            "Master": self.btn_master,
            "Profit": self.btn_profit,
            "Expense": self.btn_expense,
            "Payroll": self.btn_payroll
        }

        self.btn_dashboard.pack(pady=5, padx=10, fill="x")
        self.btn_customers.pack(pady=5, padx=10, fill="x")
        self.btn_vehicle.pack(pady=5, padx=10, fill="x")
        self.btn_loans.pack(pady=5, padx=10, fill="x")
        self.btn_dunning.pack(pady=5, padx=10, fill="x")
        self.btn_cashbank.pack(pady=5, padx=10, fill="x")
        self.btn_reports.pack(pady=5, padx=10, fill="x")
        self.btn_profit.pack(pady=5, padx=10, fill="x")
        self.btn_expense.pack(pady=5, padx=10, fill="x")
        self.btn_payroll.pack(pady=5, padx=10, fill="x")
        self.btn_master.pack(pady=5, padx=10, fill="x")        
        
        # Sidebar Bottom Info
        self.sidebar_bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_bottom.pack(side="bottom", fill="x", pady=20)
        
        # Time Display
        self.sb_time_label = ctk.CTkLabel(self.sidebar_bottom, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="white")
        self.sb_time_label.pack()
        
        self.sb_date_label = ctk.CTkLabel(self.sidebar_bottom, text="", font=ctk.CTkFont(size=11), text_color="white")
        self.sb_date_label.pack(pady=(0, 20))
        
        # Current User Info
        username = getattr(self.winfo_toplevel(), 'current_username', 'Unknown')
        self.sb_user_label = ctk.CTkLabel(self.sidebar_bottom, text=f"{t('user')}: {username}", font=ctk.CTkFont(size=12), text_color="white")
        self.sb_user_label.pack(pady=(0, 10))
        
        # Logout button
        self.sb_logout_btn = ctk.CTkButton(self.sidebar_bottom, text="🚪 " + t("logout"), height=35, width=160,
                                           fg_color="#475569", hover_color="#334155", font=s.Styles.FONT_BOLD,
                                           text_color="white", command=self.on_logout)
        self.sb_logout_btn.pack(padx=20)
        
        # Main Content Area
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", expand=True, fill="both")
        
        # Header
        self.header = ctk.CTkFrame(self.main_container, height=s.HEADER_H, fg_color=s.CARD, corner_radius=0)
        self.header.pack(side="top", fill="x")
        self.header.pack_propagate(False)
        
        self.page_title = ctk.CTkLabel(self.header, text=t("dashboard_overview"), font=s.Styles.FONT_H3, text_color=s.TEXT)
        self.page_title.pack(side="left", padx=20)
        
        # Header Logout button
        self.logout_btn = ctk.CTkButton(self.header, text=t("logout"), width=120, height=35, 
                                        fg_color=s.RED, hover_color="#e11d48", font=s.Styles.FONT_BOLD,
                                        command=self.on_logout)
        self.logout_btn.pack(side="right", padx=20)
        
        self.update_time()
        
        # Demo Mode Banner
        self.demo_banner = ctk.CTkFrame(self.main_container, fg_color="#fff7ed", height=40, corner_radius=0)
        self.demo_label = ctk.CTkLabel(self.demo_banner, text="", font=s.Styles.FONT_BOLD, text_color="#9a3412")
        self.demo_label.pack(side="left", padx=20)
        
        self.btn_activate_now = ctk.CTkButton(self.demo_banner, text="Click to Activate Full Version", 
                                             width=200, height=25, fg_color="#9a3412", hover_color="#7c2d12",
                                             font=s.Styles.FONT_TINY_BOLD, command=lambda: self.show_tab("Master"))
        self.btn_activate_now.pack(side="right", padx=20)

        # Content Area
        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.pack(expand=True, fill="both", padx=20, pady=(0, 20))
        
        self.update_demo_banner()
        # Default tab selected on login
        self.show_tab("Dashboard")

    def mark_tab_dirty(self, tab_name):
        if tab_name in self._tab_cache:
            tab = self._tab_cache[tab_name]
            if hasattr(tab, "mark_dirty"):
                tab.mark_dirty()

    def show_tab(self, tab_name):
        for name, btn in self.nav_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=s.GOLD, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="white")
        
        self.update_demo_banner()
        
        # Explicit cleanup - but now we use caching
        if self._current_tab_name and self._current_tab_name in self._tab_cache:
            # Check if this tab should be cached
            NO_CACHE_TABS = {"Reports", "Profit", "Master"}
            if self._current_tab_name in NO_CACHE_TABS:
                self._tab_cache[self._current_tab_name].destroy()
                del self._tab_cache[self._current_tab_name]
            else:
                self._tab_cache[self._current_tab_name].pack_forget()
        else:
            # Fallback cleanup for any other children
            for widget in self.content_area.winfo_children():
                try: widget.destroy()
                except: pass
        
        self._current_tab_name = tab_name
        NO_CACHE_TABS = {"Reports", "Profit", "Master"}

        try:
            # Check cache
            if tab_name in self._tab_cache and self._tab_cache[tab_name].winfo_exists():
                tab = self._tab_cache[tab_name]
                tab.pack(fill="both", expand=True)
                
                # Smart Refresh: Only refresh if dirty or if 60s passed
                import time
                current_time = time.time()
                is_dirty = getattr(tab, "_is_dirty", True)
                last_ref = getattr(tab, "_last_refresh", 0)
                
                if is_dirty or (current_time - last_ref > 60):
                    for refresh_method in ["load_customers", "load_data", "load_loans", "load_payments", "load_vehicles", "load_pledge_loans", "load_active_loans", "load_dunning_data", "load_sales_data", "load_purchases", "load_accounts", "load_transactions", "load_borrowings", "load_expenses", "load_employees", "load_payroll"]:
                        if hasattr(tab, refresh_method):
                            getattr(tab, refresh_method)()
                    tab._last_refresh = current_time
                    tab._is_dirty = False
                return

            if tab_name == "Dashboard":
                self.dashboard_tab = DashboardTab(self.content_area)
                self.dashboard_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.dashboard_tab
            elif tab_name == "Customers":
                self.customer_tab = CustomerTab(self.content_area)
                self.customer_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.customer_tab
            elif tab_name == "Purchase":
                self.purchase_tab = PurchaseTab(self.content_area)
                self.purchase_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.purchase_tab
            elif tab_name == "Sales":
                self.sales_tab = SalesTab(self.content_area)
                self.sales_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.sales_tab
            elif tab_name == "MasterData":
                self.master_tab = MasterDataTab(self.content_area)
                self.master_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.master_tab
            elif tab_name == "CashBank":
                self.cashbank_tab = CashBankTab(self.content_area)
                self.cashbank_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.cashbank_tab
            elif tab_name == "Loans":
                self.loan_tab = LoanTab(self.content_area)
                self.loan_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.loan_tab
            elif tab_name == "RCPledge":
                self.rc_pledge_tab = RCPledgeTab(self.content_area)
                self.rc_pledge_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.rc_pledge_tab
            elif tab_name == "Payments":
                self.payment_tab = PaymentsTab(self.content_area)
                self.payment_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.payment_tab
            elif tab_name == "Reports":
                self.reports_tab = ReportsTab(self.content_area)
                self.reports_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.reports_tab
            elif tab_name == "Dunning":
                self.dunning_tab = DunningRegisterTab(self.content_area)
                self.dunning_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.dunning_tab
            elif tab_name == "Master":
                from ui.master import MasterPage
                self.master_page = MasterPage(self.content_area, self.winfo_toplevel())
                self.master_page.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.master_page
            elif tab_name == "Profit":
                self.profit_tab = ProfitTab(self.content_area)
                self.profit_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.profit_tab
            elif tab_name == "Expense":
                self.expense_tab = ExpenseTab(self.content_area)
                self.expense_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.expense_tab
            elif tab_name == "Payroll":
                self.payroll_tab = PayrollTab(self.content_area)
                self.payroll_tab.pack(fill="both", expand=True)
                if tab_name not in NO_CACHE_TABS: self._tab_cache[tab_name] = self.payroll_tab
            else:
                label = ctk.CTkLabel(self.content_area, text=f"{tab_name} Section", font=s.Styles.FONT_H3)
                label.pack(expand=True)
        except Exception as e:
            import traceback
            print(f"Error loading tab {tab_name}: {e}")
            traceback.print_exc()
            messagebox.showerror("Tab Error", f"Failed to load {tab_name}: {e}")


    def update_demo_banner(self):
        try:
            if ActivationManager.is_activated():
                self.demo_banner.pack_forget()
            else:
                limit = ActivationManager.get_loan_limit()
                count = ActivationManager.get_current_loan_count()
                balance = max(0, limit - count)
                
                self.demo_label.configure(text=f"⚠️ DEMO MODE: {count}/{limit} Loans Used. ({balance} Remaining)")
                self.demo_banner.pack(side="top", fill="x", before=self.content_area)
                
                user_role = getattr(self.winfo_toplevel(), 'user_role', 'admin')
                if user_role == 'super_admin':
                    self.btn_activate_now.pack(side="right", padx=20)
                else:
                    self.btn_activate_now.pack_forget()
        except Exception as e:
            if self.winfo_exists():
                print(f"Error updating demo banner: {e}")

    def toggle_vehicle_menu(self):
        self.vehicle_menu_open = not self.vehicle_menu_open
        if self.vehicle_menu_open:
            self.submenu_frame.pack(after=self.btn_vehicle, fill="x", padx=10, pady=0)
            self.btn_vehicle.configure(text="▼  VEHICLE")
        else:
            self.submenu_frame.pack_forget()
            self.btn_vehicle.configure(text="▶  VEHICLE")

    def toggle_loan_menu(self):
        self.loan_menu_open = not self.loan_menu_open
        if self.loan_menu_open:
            self.submenu_loan_frame.pack(after=self.btn_loans, fill="x", padx=10, pady=0)
            self.btn_loans.configure(text="▼  LOANS")
        else:
            self.submenu_loan_frame.pack_forget()
            self.btn_loans.configure(text="▶  LOANS")

    def create_nav_button(self, text, command=None, active=False, master=None, indent=10):
        target_master = master if master else self.sidebar
        fg = s.GOLD if active else "transparent"
        txt_color = "white"
        
        btn = ctk.CTkButton(target_master, text=text, height=45, fg_color=fg, text_color=txt_color,
                            hover_color=s.NAVY_DARK, anchor="w", font=s.Styles.FONT_DEFAULT,
                            corner_radius=s.Styles.RADIUS, command=command)
        btn.pack(pady=2, padx=indent, fill="x")
        return btn

    def update_time(self):
        if not self.winfo_exists(): return
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%d/%m/%Y, %A").upper()
        
        self.sb_time_label.configure(text=time_str)
        self.sb_date_label.configure(text=date_str)
        
        if self.winfo_exists():
            self._after_id = self.after(1000, self.update_time)
        else:
            self._after_id = None

    def destroy(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except: pass
        super().destroy()

class DashboardTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._is_dirty = True
        
        # Header & Search Row
        self.header_row = ctk.CTkFrame(self, fg_color="transparent")
        self.header_row.pack(fill="x", pady=(s.PAD_MD, s.PAD_LG), padx=s.PAD_LG)
        
        self.header = ctk.CTkLabel(self.header_row, text=t("dashboard_overview"), font=s.Styles.FONT_H1, text_color=s.TEXT)
        self.header.pack(side="left")
        
        # Day End Closure Button
        self.btn_closure = ctk.CTkButton(self.header_row, text="📅 Day End Closure", width=160, height=35, 
                                        fg_color=s.GOLD, hover_color=s.GOLD_DARK, text_color=s.NAVY_DARK,
                                        font=s.Styles.FONT_SMALL_BOLD, command=self.on_day_end_closure)
        self.btn_closure.pack(side="right", padx=(10, 0))
        
        # Search Bar
        self.search_f = ctk.CTkFrame(self.header_row, fg_color="transparent")
        self.search_f.pack(side="right")
        
        self.search_entry = ctk.CTkEntry(self.search_f, placeholder_text="Search Name / Mobile / Vehicle Reg / Loan No...", width=300, height=35)
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<Return>", lambda e: self.perform_search())
        
        self.btn_search = ctk.CTkButton(self.search_f, text="🔍 Search", width=90, height=35, command=self.perform_search)
        self.btn_search.pack(side="left")
        
        self.btn_clear = ctk.CTkButton(self.search_f, text="✕", width=35, height=35, fg_color=s.MUTED, hover_color="#475569", command=self.clear_search)
        self.btn_clear.pack(side="left", padx=(5,0))

        # Scrollable Container for Dashboard Content
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=5)
        
        # Results area (Initially hidden)
        self.results_area = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.results_area.pack(fill="x", padx=s.PAD_LG, pady=(0, s.PAD_MD))
        
        # Stats Grid Container
        self.stats_container = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.stats_container.pack(fill="x", padx=s.PAD_MD, pady=s.PAD_SM)
        
        # Configure grid for stats cards (5 columns)
        for i in range(5):
            self.stats_container.columnconfigure(i, weight=1)
            
        # Create Cards (Initial empty state)
        self.card_vehicles = self.create_stat_card(
            self.stats_container, t("total_vehicles"), 
            "...", t("in_house_stock"), s.BLUE, 0
        )
        
        self.card_finance = self.create_stat_card(
            self.stats_container, t("active_finance"), 
            "...", t("sold_vehicles"), s.GOLD, 1
        )
        
        self.card_customers = self.create_stat_card(
            self.stats_container, t("total_customers"), 
            "...", t("registered"), s.GREEN, 2
        )
        
        self.card_balance = self.create_stat_card(
            self.stats_container, t("total_balance"), 
            "...", t("cash_bank"), s.PURPLE, 3
        )
        
        self.card_overdue = self.create_stat_card(
            self.stats_container, t("overdue_dues"), 
            "...", t("attention_required"), s.RED, 4
        )
        
        # Start background data loading
        self.load_data()

    def mark_dirty(self):
        self._is_dirty = True

    def load_data(self):
        """Alias for async loading required by DashboardPage's automatic refresh logic."""
        self.load_data_async()

    def load_data_async(self):
        """Fetches dashboard data in a background thread to prevent UI freezing."""
        def fetch():
            try:
                # 1. Fetch Stats
                stats = get_dashboard_stats()
                
                # Update UI on main thread
                if self.winfo_exists():
                    self.after(0, lambda: self.update_dashboard_ui(stats))
            except Exception as e:
                print(f"Error loading dashboard data: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def update_dashboard_ui(self, stats):
        """Updates the UI with fetched data. Must be called from main thread."""
        if not self.winfo_exists(): return
        
        # Update Stat Cards
        self.update_card_value(self.card_vehicles, str(stats["total_vehicles"]))
        self.update_card_value(self.card_finance, str(stats["active_loans"]))
        self.update_card_value(self.card_customers, str(stats["total_customers"]))
        self.update_card_value(self.card_balance, format_indian_currency(stats['total_balance']))
        self.update_card_value(self.card_overdue, str(stats["overdue_loans"]))
        
        # Update overdue command if needed
        if stats["overdue_loans"] > 0:
            # Re-bind click event with actual command
            for widget in self.card_overdue.winfo_children():
                widget.bind("<Button-1>", lambda e: self.show_overdue_details())
            self.card_overdue.bind("<Button-1>", lambda e: self.show_overdue_details())
            self.card_overdue.configure(cursor="hand2")

    def update_card_value(self, card, value):
        """Helper to find and update the value label in a stat card."""
        # The value label is the 2nd child of the 'inner' frame
        try:
            inner = [w for w in card.winfo_children() if isinstance(w, ctk.CTkFrame) and w.cget("fg_color") == "transparent"][0]
            val_lbl = [w for w in inner.winfo_children() if isinstance(w, ctk.CTkLabel)][1]
            val_lbl.configure(text=value)
        except: pass

    def clear_search(self):
        self.search_entry.delete(0, 'end')
        for widget in self.results_area.winfo_children():
            widget.destroy()
        self.results_area.pack_forget()

    def perform_search(self):
        query_text = self.search_entry.get().strip()
        if not query_text: return
        
        # Clear previous results and show loading state
        for widget in self.results_area.winfo_children():
            widget.destroy()
        self.results_area.pack(fill="x", padx=s.PAD_LG, pady=(0, s.PAD_MD), before=self.stats_container)
        
        loading_lbl = ctk.CTkLabel(self.results_area, text="Searching...", font=s.Styles.FONT_TINY, text_color=s.MUTED)
        loading_lbl.pack(pady=10)

        def fetch():
            results = []
            try:
                conn = get_connection()
                cursor = conn.cursor()
                search_param = f"%{query_text}%"
                
                # 1. Find customers
                cursor.execute("""
                    SELECT DISTINCT c.id, c.name, c.phone
                    FROM customers c
                    LEFT JOIN loans l ON c.id = l.customer_id
                    LEFT JOIN vehicles v ON (l.vehicle_id = v.id OR v.customer_id = c.id OR v.purchased_from_id = c.id)
                    WHERE c.name LIKE ? OR c.phone LIKE ? OR v.reg_number LIKE ? OR l.loan_number LIKE ? OR ('L-' || l.id) LIKE ?
                    LIMIT 10
                """, (search_param, search_param, search_param, search_param, search_param))
                customers = cursor.fetchall()
                
                for cid, name, phone in customers:
                    # 2. Get counts & detailed info per customer
                    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE customer_id = ?", (cid,))
                    sales_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE purchased_from_id = ?", (cid,))
                    purch_count = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        SELECT id, installment_amount, due_beginning_date, loan_tenure, status, 
                               (SELECT COUNT(*) FROM payments WHERE loan_id = loans.id) 
                        FROM loans WHERE customer_id = ?
                    """, (cid,))
                    loans_data = cursor.fetchall()
                    
                    # 3. Calculate overdue for active loan
                    overdue_amt = 0
                    active_loan = next((l for l in loans_data if l[4] == 'Active'), None)
                    if active_loan:
                        lid, emi, due_start, tenure, status, paid_count = active_loan
                        if due_start:
                            now = datetime.now().date()
                            try:
                                start_dt = datetime.strptime(due_start, "%d-%m-%Y")
                                for idx in range(paid_count, tenure):
                                    month = (start_dt.month + idx - 1) % 12 + 1
                                    year = start_dt.year + (start_dt.month + idx - 1) // 12
                                    import calendar
                                    last_day = calendar.monthrange(year, month)[1]
                                    due_date = datetime(year, month, min(start_dt.day, last_day)).date()
                                    if due_date < now: overdue_amt += emi
                                    else: break
                            except Exception:
                                pass
                    
                    results.append({
                        "id": cid, "name": name, "phone": phone,
                        "sales": sales_count, "purchases": purch_count,
                        "loans": loans_data, "overdue": overdue_amt
                    })
                conn.close()
            except Exception as e:
                print(f"Fetch error in search: {e}")
            return results

        def render(results):
            if not self.winfo_exists(): return
            for widget in self.results_area.winfo_children():
                widget.destroy()
            
            if not results:
                ctk.CTkLabel(self.results_area, text="No results found for your search.", 
                            font=s.Styles.FONT_DEFAULT, text_color=s.MUTED).pack(pady=20)
                return

            title_f = ctk.CTkFrame(self.results_area, fg_color="transparent")
            title_f.pack(fill="x", pady=(10,5))
            ctk.CTkLabel(title_f, text="GLOBAL SEARCH RESULTS", font=s.Styles.FONT_TINY_BOLD, text_color=s.GOLD).pack(side="left")
            
            for res in results:
                card = ctk.CTkFrame(self.results_area, fg_color=s.CARD, border_width=1, border_color=s.BORDER)
                card.pack(fill="x", pady=5)
                
                # Left side: Info
                info_f = ctk.CTkFrame(card, fg_color="transparent")
                info_f.pack(side="left", padx=20, pady=15)
                ctk.CTkLabel(info_f, text=res["name"], font=s.Styles.FONT_BOLD, text_color=s.TEXT).pack(anchor="w")
                ctk.CTkLabel(info_f, text=f"📞 {res['phone'] or '-'}", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w")
                
                # Middle: Badges
                inv_f = ctk.CTkFrame(card, fg_color="transparent")
                inv_f.pack(side="left", padx=40, pady=15, expand=True)
                
                if res["sales"] > 0:
                    ctk.CTkButton(inv_f, text=f"🛍️ {res['sales']} Sales", width=100, height=28, fg_color=s.PRIMARY, 
                                 font=s.Styles.FONT_TINY_BOLD, command=lambda c=res["id"]: self.show_history(c, "Sales")).pack(side="left", padx=5)
                if res["purchases"] > 0:
                    ctk.CTkButton(inv_f, text=f"📥 {res['purchases']} Purchases", width=100, height=28, fg_color=s.BLUE, 
                                 font=s.Styles.FONT_TINY_BOLD, command=lambda c=res["id"]: self.show_history(c, "Purchases")).pack(side="left", padx=5)
                if res["loans"]:
                    ctk.CTkButton(inv_f, text=f"💳 {len(res['loans'])} Loans", width=100, height=28, fg_color=s.GOLD, text_color=s.NAVY_DARK,
                                 font=s.Styles.FONT_TINY_BOLD, command=lambda c=res["id"]: self.show_history(c, "Loans")).pack(side="left", padx=5)
                
                # Right: Status
                status_f = ctk.CTkFrame(card, fg_color="transparent")
                status_f.pack(side="right", padx=20, pady=15)
                
                if any(l[4] == 'Active' for l in res["loans"]):
                    if res["overdue"] > 0:
                        ctk.CTkLabel(status_f, text=f"⚠️ DUE: {format_indian_currency(res['overdue'])}", font=s.Styles.FONT_TINY_BOLD, text_color=s.RED).pack(anchor="e")
                    else:
                        ctk.CTkLabel(status_f, text="✅ CURRENT", font=s.Styles.FONT_TINY_BOLD, text_color=s.GREEN).pack(anchor="e")

        def run():
            data = fetch()
            if self.winfo_exists():
                self.after(0, lambda: render(data))
        
        import threading
        threading.Thread(target=run, daemon=True).start()

    def show_history(self, customer_id, category):
        CustomerHistoryWindow(self.winfo_toplevel(), customer_id, category)

        # Fetch stats for the welcome message
        stats = get_dashboard_stats()

        # Welcome Card
        self.welcome_card = ctk.CTkFrame(self.scroll_container, fg_color=s.CARD, corner_radius=s.Styles.RADIUS, border_width=1, border_color=s.BORDER)
        self.welcome_card.pack(fill="both", expand=True, padx=s.PAD_LG, pady=s.PAD_LG)
        
        self.welcome_inner = ctk.CTkFrame(self.welcome_card, fg_color="transparent")
        self.welcome_inner.place(relx=0.5, rely=0.5, anchor="center")
        
        self.welcome_title = ctk.CTkLabel(self.welcome_inner, text=t("admin_welcome"), font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.welcome_title.pack(pady=5)
        
        if stats["overdue_loans"] > 0:
            msg = t("overdue_msg").format(n=stats['overdue_loans'])
        else:
            msg = t("loans_msg").format(n=stats['active_loans'])
            
        self.welcome_sub = ctk.CTkLabel(self.welcome_inner, text=msg, 
                                        font=s.Styles.FONT_DEFAULT, text_color=s.RED if stats["overdue_loans"] > 0 else s.MUTED)
        self.welcome_sub.pack(pady=5)

    def on_day_end_closure(self):
        # Check if already closed
        today = datetime.now().strftime("%d-%m-%Y")
        if cl.is_date_closed(today):
            if messagebox.askyesno("Already Closed", f"Day End Closure for {today} is already completed. Do you want to view past closures?"):
                PastClosuresWindow(self.winfo_toplevel())
            return
            
        ClosureWindow(self.winfo_toplevel())

    def show_overdue_details(self):
        win = OverdueLoansWindow(self.winfo_toplevel())
        win.lift()
        win.focus_force()
        
    def create_stat_card(self, master, title, value, subtitle, color, col, command=None):
        card = ctk.CTkFrame(master, fg_color=s.CARD, corner_radius=s.Styles.RADIUS, border_width=1, border_color=s.BORDER,
                           cursor="hand2" if command else "")
        card.grid(row=0, column=col, padx=8, pady=5, sticky="nsew")
        
        # Subtile accent line
        accent = ctk.CTkFrame(card, height=3, fg_color=color, corner_radius=0)
        accent.pack(side="top", fill="x")
        
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=15, pady=15, fill="both", expand=True)
        
        title_lbl = ctk.CTkLabel(inner, text=title.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED)
        title_lbl.pack(anchor="w")
        
        val_lbl = ctk.CTkLabel(inner, text=value, font=s.Styles.FONT_H2, text_color=s.TEXT)
        val_lbl.pack(anchor="w", pady=(5, 0))
        
        sub_lbl = ctk.CTkLabel(inner, text=subtitle, font=s.Styles.FONT_TINY, text_color=color)
        sub_lbl.pack(anchor="w")
        
        if command:
            # Bind to ALL components of the card
            for widget in [card, accent, inner, title_lbl, val_lbl, sub_lbl]:
                widget.bind("<Button-1>", lambda e: command())
        
        return card



class CustomerTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("customer_management"), **kwargs)
        self.edit_id = None
        
        # --- Form Section ---
        self.form_card, self.form = self.create_card(t("personal_details"))
        
        # Row 1: Name, Father Name, Phone
        self.field_name = self.create_input(self.form, t("full_name") + " *", 1, 0)
        self.field_father = self.create_input(self.form, t("father_name"), 1, 1)
        self.field_phone = self.create_input(self.form, t("phone_number"), 1, 2)
        
        # Row 2: Aadhaar, Street, City
        self.field_aadhaar = self.create_input(self.form, t("aadhar_number"), 2, 0)
        self.field_aadhaar.bind("<KeyRelease>", self.format_aadhaar)
        self.field_street = self.create_input(self.form, t("street_area"), 2, 1)
        self.field_city = self.create_input(self.form, t("city"), 2, 2)
        
        # Row 3: Pincode, Gender, Business
        self.field_pincode = self.create_input(self.form, t("pincode"), 3, 0)
        self.field_gender = self.create_radio_group(self.form, t("gender"), [t("male"), t("female")], 3, 1, default_value=t("male"))
        self.field_business = self.create_input(self.form, t("business"), 3, 2)
        
        # Row 4: Introducer, Rating, Photo/Docs
        self.field_introducer = self.create_input(self.form, t("introducer"), 4, 0)
        
        # Rating (Internal Container for StarRating)
        rating_cont = ctk.CTkFrame(self.form, fg_color="transparent")
        rating_cont.grid(row=4, column=1, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")
        self.field_rating = StarRating(rating_cont, t("rating"))
        self.field_rating.pack(anchor="w")
        
        # File Upload Section (Internal Container)
        file_cont = ctk.CTkFrame(self.form, fg_color="transparent")
        file_cont.grid(row=4, column=2, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")
        ctk.CTkLabel(file_cont, text=t("documents").upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED).pack(anchor="w", pady=(0, 5))
        
        self.btn_f_row = ctk.CTkFrame(file_cont, fg_color="transparent")
        self.btn_f_row.pack(anchor="w")
        
        self.photo_path = tk.StringVar(value="")
        self.docs_path = tk.StringVar(value="")
        
        self.btn_photo = ctk.CTkButton(self.btn_f_row, text="📸 " + t("photo"), width=105, height=35, 
                                       fg_color=s.CARD_ALT, text_color=s.TEXT, hover_color=s.BORDER, 
                                       border_width=1, border_color=s.BORDER,
                                       font=s.Styles.FONT_TINY_BOLD, command=self.upload_photo)
        self.btn_photo.pack(side="left", padx=(0, 8))
        
        self.btn_docs = ctk.CTkButton(self.btn_f_row, text="📄 " + t("docs"), width=105, height=35, 
                                      fg_color=s.CARD_ALT, text_color=s.TEXT, hover_color=s.BORDER,
                                      border_width=1, border_color=s.BORDER,
                                      font=s.Styles.FONT_TINY_BOLD, command=self.upload_docs)
        self.btn_docs.pack(side="left")

        # Action Buttons
        self.save_btn, self.clear_btn = self.create_action_buttons(self.form, t("save_customer"), self.save_customer, self.clear_form)
        
        # --- List Section ---
        # --- List Section with Search ---
        list_header_row = ctk.CTkFrame(self, fg_color="transparent")
        list_header_row.pack(pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG, fill="x")
        
        self.list_header = ctk.CTkLabel(list_header_row, text=t("customer_directory"), font=s.Styles.FONT_H2, text_color=s.NAVY)
        self.list_header.pack(side="left")
        
        self.c_search_entry = ctk.CTkEntry(list_header_row, placeholder_text="Filter Name/Phone...", width=200, height=30)
        self.c_search_entry.pack(side="right", padx=(10, 0))
        self.c_search_entry.bind("<KeyRelease>", lambda e: self.load_customers())
        
        # Enhanced Table Header
        self.table_header_card = ctk.CTkFrame(self, fg_color=s.NAVY, height=45, corner_radius=8)
        self.table_header_card.pack(fill="x", padx=s.PAD_LG)
        self.table_header_card.pack_propagate(False)
        
        headers = [(t("name"), 0.02), (t("phone"), 0.28), (t("address"), 0.48), (t("actions"), 0.73)]
        for text, rel_x in headers:
            lbl = ctk.CTkLabel(self.table_header_card, text=text.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.WHITE)
            lbl.place(relx=rel_x, rely=0.5, anchor="w", x=15)

        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True, padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        # Lazy Loading State
        self.customer_offset = 0
        self.has_more = True
        self.loading_more = False
        
        # Bind scroll events for lazy loading
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind("<Configure>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<MouseWheel>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-4>", lambda e: self.check_scroll(), add="+") # Linux scroll up
            self._parent_canvas.bind("<Button-5>", lambda e: self.check_scroll(), add="+") # Linux scroll down

        self.load_customers()

    def format_aadhaar(self, event=None):
        # 1. Capture current cursor position
        try:
            current_pos = self.field_aadhaar._entry.index("insert")
        except:
            current_pos = len(self.field_aadhaar.get())
            
        # 2. Extract only digits and limit to 12
        text = self.field_aadhaar.get()
        digits_before = "".join(filter(str.isdigit, text[:current_pos]))
        all_digits = "".join(filter(str.isdigit, text))[:12]
        
        # 3. Format with spaces
        formatted = ""
        for i in range(len(all_digits)):
            if i > 0 and i % 4 == 0:
                formatted += " "
            formatted += all_digits[i]
            
        # 4. Calculate new cursor position based on digits_before
        new_pos = 0
        digit_count = 0
        for char in formatted:
            if digit_count >= len(digits_before):
                break
            if char.isdigit():
                digit_count += 1
            new_pos += 1
            
        # 5. Set value and restore cursor
        if self.field_aadhaar.get() != formatted:
            self.field_aadhaar.delete(0, 'end')
            self.field_aadhaar.insert(0, formatted)
            if self.field_aadhaar.winfo_exists():
                self.after_idle(lambda: self.field_aadhaar._entry.icursor(new_pos) if self.field_aadhaar.winfo_exists() else None)

    def upload_photo(self):
        filename = filedialog.askopenfilename(title="Select Photo", filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if filename:
            self.photo_path.set(filename)
            self.btn_photo.configure(fg_color=s.GREEN)

    def upload_docs(self):
        filename = filedialog.askopenfilename(title="Select Documents", filetypes=[("PDF/Image Files", "*.pdf *.jpg *.jpeg *.png")])
        if filename:
            self.docs_path.set(filename)
            self.btn_docs.configure(fg_color=s.GREEN)

    def check_scroll(self, event=None):
        if not self.has_more or self.loading_more:
            return
            
        # Check if we are near the bottom of the scrollable frame
        # yview returns (start, end) where end is the bottom position (0 to 1)
        try:
            if self._parent_canvas.yview()[1] > 0.8:
                self.load_customers(append=True)
        except: pass

    def load_customers(self, append=False):
        if self.loading_more or (append and not self.has_more):
            return
            
        self.loading_more = True
        
        if not append:
            self.customer_offset = 0
            self.has_more = True
            # Remove load more button on fresh search
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()
        
        query = self.c_search_entry.get().strip() if hasattr(self, 'c_search_entry') else ""
        offset = self.customer_offset
        limit = 10 # Changed back to 10 as requested
        
        def fetch():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                if query:
                    cursor.execute("""
                        SELECT id, name, phone, street, city 
                        FROM customers 
                        WHERE name LIKE ? OR phone LIKE ? 
                        ORDER BY name ASC 
                        LIMIT ? OFFSET ?
                    """, (f"%{query}%", f"%{query}%", limit, offset))
                else:
                    cursor.execute("""
                        SELECT id, name, phone, street, city 
                        FROM customers 
                        ORDER BY created_at DESC 
                        LIMIT ? OFFSET ?
                    """, (limit, offset))
                data = cursor.fetchall()
            finally:
                conn.close()
            return data

        def render(customers):
            if not self.winfo_exists():
                self.loading_more = False
                return
            
            # Remove existing load more button before rendering new batch
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

            if not customers:
                if not append:
                    for widget in self.list_container.winfo_children(): widget.destroy()
                    lbl = ctk.CTkLabel(self.list_container, text="No customers found.", font=s.Styles.FONT_TINY, text_color="gray")
                    lbl.pack(pady=20)
                self.has_more = False
                self.loading_more = False
                return

            if len(customers) < limit:
                self.has_more = False

            def render_customer_row(i, customer):
                cid, name, phone, street, city = customer
                row = ctk.CTkFrame(self.list_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=0)
                row.pack(fill="x")
                row.pack_propagate(False)
                
                # Columns
                address = f"{street or ''}, {city or ''}".strip(", ")
                ctk.CTkLabel(row, text=name, font=s.Styles.FONT_SMALL, text_color=s.TEXT).place(relx=0.0, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row, text=phone or "-", font=s.Styles.FONT_SMALL, text_color=s.TEXT).place(relx=0.3, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row, text=address or "-", font=s.Styles.FONT_SMALL, text_color=s.TEXT).place(relx=0.5, rely=0.5, anchor="w", x=15)
                
                # Actions
                act_frame = ctk.CTkFrame(row, fg_color="transparent")
                act_frame.place(relx=0.73, rely=0.5, anchor="w", x=15)
                
                ctk.CTkButton(act_frame, text=t("edit"), width=50, height=28, fg_color="#3b82f6", 
                             hover_color="#2563eb", font=s.Styles.FONT_TINY,
                             command=lambda c=cid: self.load_for_edit(c)).pack(side="left", padx=2)
                
                ctk.CTkButton(act_frame, text=t("view"), width=50, height=28, fg_color="#10b981", 
                             hover_color="#059669", font=s.Styles.FONT_TINY,
                             command=lambda c=cid: self.view_customer(c)).pack(side="left", padx=2)
                
                ctk.CTkButton(act_frame, text=t("delete"), width=50, height=28, fg_color=s.RED, 
                             hover_color="#e11d48", font=s.Styles.FONT_TINY,
                             command=lambda c=cid: self.delete_customer(c)).pack(side="left", padx=2)

            def on_chunk_complete(count):
                if not self.winfo_exists(): return
                if self.has_more:
                    self.load_more_btn = ctk.CTkButton(self.list_container, text="Click to Load More Customers...", 
                                                      fg_color="transparent", text_color=s.PRIMARY,
                                                      hover_color=s.BORDER, font=s.Styles.FONT_SMALL_BOLD,
                                                      command=lambda: self.load_customers(append=True))
                    self.load_more_btn.pack(pady=20, fill="x")
                self.loading_more = False

            self.render_list_chunked(self.list_container, customers, render_customer_row, 
                                   clear=not append, start_row_idx=offset, on_complete=on_chunk_complete)
            
            self.customer_offset += len(customers)

        self.run_in_background(fetch, render)

    def load_for_edit(self, customer_id):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            c = cursor.fetchone()
            conn.close()
            
            if c:
                self.edit_id = customer_id
                # Map fields (index based on DB schema)
                self.field_name.delete(0, 'end'); self.field_name.insert(0, c[1])
                self.field_father.delete(0, 'end'); self.field_father.insert(0, c[2] or "")
                self.field_phone.delete(0, 'end'); self.field_phone.insert(0, c[3] or "")
                self.field_street.delete(0, 'end'); self.field_street.insert(0, c[4] or "")
                self.field_city.delete(0, 'end'); self.field_city.insert(0, c[5] or "")
                self.field_pincode.delete(0, 'end'); self.field_pincode.insert(0, c[6] or "")
                self.field_aadhaar.delete(0, 'end'); self.field_aadhaar.insert(0, c[7] or "")
                self.field_gender.set(c[8] or t("male"))
                self.field_business.delete(0, 'end'); self.field_business.insert(0, c[9] or "")
                self.field_rating.set(c[10] or 0)
                self.field_introducer.delete(0, 'end'); self.field_introducer.insert(0, c[11] or "")
                self.photo_path.set(c[12] or "")
                self.docs_path.set(c[13] or "")
                
                if c[12]: self.btn_photo.configure(fg_color=s.GREEN)
                if c[13]: self.btn_docs.configure(fg_color=s.GREEN)
                
                self.save_btn.configure(text=t("update_customer"))
                self.header.configure(text=t("edit_customer"))
                # Scroll to top
                self._parent_canvas.yview_moveto(0)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")

    def view_customer(self, customer_id):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            c = cursor.fetchone()
            conn.close()
            
            if c:
                ViewCustomerWindow(self, c)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open view: {e}")

    def delete_customer(self, customer_id):
        if messagebox.askyesno(t("confirm_delete"), t("are_you_sure_delete") + "?"):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Prevent deleting customer if they have associated loans
                cursor.execute("SELECT COUNT(*) FROM loans WHERE customer_id = ?", (customer_id,))
                loan_count = cursor.fetchone()[0]
                if loan_count > 0:
                    messagebox.showerror("Error", "Cannot delete this customer because they have associated Loan records. You must delete the customer's loans first.")
                    conn.close()
                    return
                
                cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
                conn.commit()
                conn.close()
                self.load_customers()
                self.mark_dirty()
                parent = self.winfo_toplevel()
                if hasattr(parent, 'dashboard_page'):
                    parent.dashboard_page.mark_tab_dirty("Dashboard")
                if self.edit_id == customer_id:
                    self.clear_form()
                messagebox.showinfo("Success", "Customer deleted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")

    def save_customer(self):
        data = {
            "name": self.field_name.get(),
            "father_name": self.field_father.get(),
            "phone": self.field_phone.get(),
            "aadhaar": self.field_aadhaar.get(),
            "street": self.field_street.get(),
            "city": self.field_city.get(),
            "pincode": self.field_pincode.get(),
            "gender": self.field_gender.get(),
            "business": self.field_business.get(),
            "introducer": self.field_introducer.get(),
            "rating": self.field_rating.get(),
            "photo": self.photo_path.get(),
            "docs": self.docs_path.get()
        }
        
        if not data["name"]:
            messagebox.showerror("Error", "Name is required!")
            return
            
        # Validation for Aadhaar
        aadhaar_digits = "".join(filter(str.isdigit, data["aadhaar"]))
        if aadhaar_digits and len(aadhaar_digits) != 12:
            messagebox.showerror("Error", "Aadhaar number must be exactly 12 digits!")
            return
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            if self.edit_id:
                cursor.execute("""
                    UPDATE customers 
                    SET name=?, father_name=?, phone=?, street=?, city=?, pincode=?, aadhaar=?, 
                        gender=?, business=?, rating=?, introducer=?, photo_path=?, docs_path=?
                    WHERE id=?
                """, (data["name"], data["father_name"], data["phone"], data["street"], data["city"], data["pincode"], 
                      data["aadhaar"], data["gender"], data["business"], data["rating"], data["introducer"], 
                      data["photo"], data["docs"], self.edit_id))
            else:
                cursor.execute("""
                    INSERT INTO customers (name, father_name, phone, street, city, pincode, aadhaar, gender, business, rating, introducer, photo_path, docs_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (data["name"], data["father_name"], data["phone"], data["street"], data["city"], data["pincode"], 
                      data["aadhaar"], data["gender"], data["business"], data["rating"], data["introducer"], data["photo"], data["docs"]))
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", t("customer_saved_success"))
            self.clear_form()
            self.load_customers()
            self.mark_dirty()
            parent = self.winfo_toplevel()
            if hasattr(parent, 'dashboard_page'):
                parent.dashboard_page.mark_tab_dirty("Dashboard")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save: {str(e)}")

    def clear_form(self):
        self.edit_id = None
        self.field_name.delete(0, 'end')
        self.field_father.delete(0, 'end')
        self.field_phone.delete(0, 'end')
        self.field_aadhaar.delete(0, 'end')
        self.field_street.delete(0, 'end')
        self.field_city.delete(0, 'end')
        self.field_pincode.delete(0, 'end')
        self.field_gender.set(t("male"))
        self.field_business.delete(0, 'end')
        self.field_introducer.delete(0, 'end')
        self.field_rating.set(0)
        self.photo_path.set("")
        self.docs_path.set("")
        self.btn_photo.configure(fg_color="#475569")
        self.btn_docs.configure(fg_color="#475569")
        self.save_btn.configure(text="SAVE CUSTOMER")
        self.header.configure(text="Customer Management")

class PurchaseTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("vehicle_purchase"), **kwargs)
        self.edit_id = None
        
        # Main Container for dual column layout
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="x", padx=s.PAD_SM)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        
        # Left: Vehicle Details
        self.v_card, self.v_form = self.create_card(t("vehicle_details"), master=self.main_container)
        self.v_card.grid(row=0, column=0, sticky="nsew", padx=s.PAD_SM)
        
        # Row 1: Make, Model
        self.field_make, _ = self.create_select(self.v_form, t("make"), [], 1, 0, width=240, command=self.load_models_for_make)
        self.field_model, _ = self.create_select(self.v_form, t("model"), [], 1, 1, width=240)
        
        # Row 2: Year, Reg Number
        cur_year = datetime.now().year
        years = [str(y) for y in range(cur_year, 1999, -1)]
        self.field_model_year, _ = self.create_select(self.v_form, t("model_year"), years, 2, 0, width=240)
        
        self.reg_var = ctk.StringVar()
        self.reg_trace_id = self.reg_var.trace_add("write", self.format_reg_number)
        self.field_reg = self.create_input(self.v_form, t("registration_no"), 2, 1, width=240, textvariable=self.reg_var)
        
        # Row 3: Purchase Price, Tentative Price (Chassis & Engine fields removed)
        self.field_p_price = self.create_input(self.v_form, t("purchase_price"), 3, 0, width=240)
        self.field_tentative_price = self.create_input(self.v_form, t("tentative_sale_price"), 3, 1, width=240)
        
        self.account_map = {}
        
        # Right: Documentation & Finance
        self.d_card, self.d_form = self.create_card(t("documentation"), master=self.main_container)
        self.d_card.grid(row=0, column=1, sticky="nsew", padx=(s.PAD_SM, 0))
 
        
        # Row 1: Purchase Date, Paid From
        self.field_p_date = self.create_date_picker(self.d_form, t("purchase_date"), 1, 0, default_date=datetime.now())
        self.field_acc, self.acc_var = self.create_select(self.d_form, t("paid_from") + " *", [], 1, 1, width=240)
        
        # Row 2: Bought From (Seller)
        self.customer_map = {}
        self.field_seller, self.seller_var = self.create_searchable_select(self.d_form, t("bought_from"), [], 2, 0, columnspan=2, width=240*2 + 2*s.PAD_MD)
        
        # Row 3: RC Status, RC Remark
        self.rc_var = self.create_radio_group(self.d_form, t("rc_book_status"), [t("received"), t("not_received")], 3, 0, default_value="Not Received")
        self.field_rc_remark = self.create_input(self.d_form, t("rc_remarks"), 3, 1, width=240)
        
        # Row 4: Insurance Status, Insurance Remark
        self.insurance_var = self.create_radio_group(self.d_form, t("insurance_status"), [t("expired"), t("in_live")], 4, 0, default_value="Expired", command=self.toggle_insurance_date)
        self.field_ins_remark = self.create_input(self.d_form, t("ins_remarks"), 4, 1, width=240)
        
        self.ins_until_container = ctk.CTkFrame(self.d_form, fg_color="transparent")
        # Managed by toggle_insurance_date
        ctk.CTkLabel(self.ins_until_container, text=t("insurance_until"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=2)
        self.field_ins_until = DatePickerWidget(self.ins_until_container, default_date=datetime.now(), height=s.Styles.FIELD_HEIGHT)
        self.field_ins_until.pack(anchor="w")

        # Action Buttons
        self.save_btn, self.clear_btn = self.create_action_buttons(self.d_form, t("save_purchase"), self.save_purchase, self.clear_form)

        # --- List Section ---
        self.list_header_f = ctk.CTkFrame(self, fg_color="transparent")
        self.list_header_f.pack(pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG, fill="x")
        
        self.list_header = ctk.CTkLabel(self.list_header_f, text=t("purchase_history"), font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.list_header.pack(side="left")

        # --- Cascade Filters ---
        self.filter_frame = ctk.CTkFrame(self, fg_color=s.CARD, corner_radius=8, border_width=1, border_color=s.BORDER)
        self.filter_frame.pack(fill="x", padx=s.PAD_LG, pady=(0, s.PAD_MD))
        
        # Grid config for filters
        for i in range(4): self.filter_frame.columnconfigure(i, weight=1)
        
        # Make Filter
        self.f_make_cont = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        self.f_make_cont.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(self.f_make_cont, text=t("make"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w")
        self.filter_make_var = ctk.StringVar(value="All Makes")
        self.filter_make = ctk.CTkOptionMenu(self.f_make_cont, variable=self.filter_make_var, values=["All Makes"], 
                                           command=self.on_filter_make_change, fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT)
        self.filter_make.pack(fill="x")
        
        # Model Filter
        self.f_model_cont = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        self.f_model_cont.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(self.f_model_cont, text=t("model"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w")
        self.filter_model_var = ctk.StringVar(value="All Models")
        self.filter_model = ctk.CTkOptionMenu(self.f_model_cont, variable=self.filter_model_var, values=["All Models"], 
                                             command=self.on_filter_model_change, fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT)
        self.filter_model.pack(fill="x")
        
        # Reg No Filter
        self.f_reg_cont = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        self.f_reg_cont.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(self.f_reg_cont, text=t("registration_no"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w")
        self.filter_reg_var = ctk.StringVar(value="All Reg Nos")
        self.filter_reg = ctk.CTkOptionMenu(self.f_reg_cont, variable=self.filter_reg_var, values=["All Reg Nos"], 
                                           command=self.on_filter_reg_change, fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT)
        self.filter_reg.pack(fill="x")
        
        # Clear Button
        self.btn_clear_filter = ctk.CTkButton(self.filter_frame, text="✕ " + t("clear"), width=80, height=32, 
                                             fg_color="transparent", border_width=1, border_color=s.BORDER, 
                                             text_color=s.MUTED, command=self.clear_filters)
        self.btn_clear_filter.grid(row=0, column=3, padx=10, pady=(25, 10))

        # Enhanced Table Header
        self.t_header_card = ctk.CTkFrame(self, fg_color=s.NAVY, height=45, corner_radius=8)
        self.t_header_card.pack(fill="x", padx=s.PAD_LG)
        self.t_header_card.pack_propagate(False)
        
        h_data = [(t("vehicle"), 0.02), (t("reg_no"), 0.32), (t("p_price"), 0.52), (t("actions"), 0.72)]
        for text, rel_x in h_data:
            lbl = ctk.CTkLabel(self.t_header_card, text=text.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.WHITE)
            lbl.place(relx=rel_x, rely=0.5, anchor="w", x=15)

        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True, padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        # Lazy Loading State
        self.vehicle_offset = 0
        self.has_more = True
        self.loading_more = False
        
        # Bind scroll events for lazy loading
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind("<Configure>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<MouseWheel>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-4>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-5>", lambda e: self.check_scroll(), add="+")

        self.load_makes()
        self.load_filter_makes()
        self.load_purchases()
        self.load_accounts_for_purchase()
        self.load_customers_for_purchase()

    def toggle_insurance_date(self):
        if self.insurance_var.get() == "In Live":
            self.ins_until_container.grid(row=5, column=0, columnspan=2, padx=s.PAD_MD, pady=s.PAD_SM, sticky="w")
        else:
            self.ins_until_container.grid_forget()

    def format_reg_number(self, *args):
        try:
            # Capture state: current value and cursor position
            raw = self.reg_var.get().upper()
            pos = self.field_reg._entry.index("insert")
            
            # Identify valid alphanumeric characters and their types by position
            # Pattern: TN (0,1) | District (2,3: num) | Series (4,5: alpha) | Number (6,7,8,9: num)
            alnum_data = [(i, c) for i, c in enumerate(raw) if c.isalnum()]
            
            valid_list = []
            valid_orig_indices = []
            for i, (orig_idx, c) in enumerate(alnum_data[:10]):
                is_valid = False
                if i < 2: is_valid = True # TN (forced later)
                elif i < 4: is_valid = c.isdigit() # District Code
                elif i < 6: is_valid = c.isalpha() # Series Code
                else: is_valid = c.isdigit()      # Registration Number
                
                if is_valid:
                    valid_list.append(c)
                    valid_orig_indices.append(orig_idx)
            
            # Count valid alphanumeric chars before original cursor to track logical position
            alnums_before = sum(1 for idx in valid_orig_indices if idx < pos)
            clean = "".join(valid_list)
            
            # Enforce TN prefix if there's any content
            if clean:
                if not clean.startswith("TN"):
                    if clean == "T":
                        # If just 'T', stay as 'T'
                        pass
                    elif clean.startswith("T"):
                        # If 'T' + something else, force 'TN'
                        clean = "TN" + clean[1:]
                        if alnums_before == 1: alnums_before = 2
                    else:
                        # Anything else, force 'TN' prefix
                        clean = "TN" + clean
                        alnums_before += 2 # Since we added TN
            
            # Reconstruct formatted string based on pattern
            res = ""
            if len(clean) >= 2:
                res += clean[0:2]
                if len(clean) > 2:
                    res += " " + clean[2:4]
                    if len(clean) > 4:
                        res += " - " + clean[4:6]
                        if len(clean) > 6:
                            res += " " + clean[6:10]
            else:
                res += clean

            if res != raw:
                # Update variable without triggering recursion
                self.reg_var.trace_remove("write", self.reg_trace_id)
                self.reg_var.set(res)
                self.reg_trace_id = self.reg_var.trace_add("write", self.format_reg_number)
                
                # Calculate new cursor position relative to valid alnums counted
                new_pos = 0
                if alnums_before > 0:
                    count = 0
                    for i, char in enumerate(res):
                        if char.isalnum(): count += 1
                        new_pos = i + 1
                        if count == alnums_before: break
                
                # If the target position is a separator, move past it
                while new_pos < len(res) and not res[new_pos].isalnum():
                    new_pos += 1
                
                # Use after_idle to ensure cursor is positioned AFTER Tkinter processes the set()
                target_pos = new_pos
                if self.field_reg.winfo_exists():
                    self.field_reg.after_idle(lambda: self.field_reg._entry.icursor(target_pos) if self.field_reg.winfo_exists() else None)
        except Exception as e:
            # Restore trace if something fails
            try:
                self.reg_var.trace_remove("write", self.reg_trace_id)
                self.reg_trace_id = self.reg_var.trace_add("write", self.format_reg_number)
            except: pass

    def save_purchase(self):
        make_name = self.field_make.get()
        model_name = self.field_model.get()
        model_year = self.field_model_year.get()
        data = {
            "reg": self.field_reg.get(),
            "chassis": "",
            "engine": "",
            "p_price": self.field_p_price.get(),
            "p_date": self.field_p_date.get() or datetime.now().strftime('%d-%m-%Y'),
            "rc_book": self.rc_var.get(),
            "rc_remark": self.field_rc_remark.get(),
            "ins_status": self.insurance_var.get(),
            "ins_until": self.field_ins_until.get() if self.insurance_var.get() == "In Live" else None,
            "ins_remark": self.field_ins_remark.get(),
            "acc_name": self.acc_var.get(),
            "seller_name": self.field_seller.get(),
            "tentative_price": self.field_tentative_price.get()
        }
        
        acc_placeholder = t("select") + "..."
        if make_name == t("select") + " " + t("make") + "..." or \
           model_name == t("select") + " " + t("model") + "..." or \
           model_year == t("select") + " " + t("year") + "..." or \
           not data["reg"] or \
           (not self.edit_id and data["acc_name"] == acc_placeholder):
            messagebox.showerror(t("error"), t("field_required"))
            return
        
        if cl.is_date_closed(data["p_date"]):
            messagebox.showerror(t("error"), f"The date {data['p_date']} has already been closed. No new records can be added for this date.")
            return

        acc_id = self.account_map.get(data["acc_name"])
        seller_id = self.customer_map.get(data["seller_name"])
        try:
            p_price = float(data["p_price"] or 0)
        except:
            messagebox.showerror("Error", "Invalid Purchase Price!")
            return

        # Check for sufficient funds (Only for New Purchase)
        if not self.edit_id:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM accounts WHERE id = ?", (acc_id,))
                res = cursor.fetchone()
                if res:
                    current_bal = res[0]
                    if current_bal < p_price:
                        messagebox.showerror("Insufficient Funds", f"Selected account only has ₹{current_bal:,.2f}.\nPurchase price is ₹{p_price:,.2f}.")
                        conn.close()
                        return
                conn.close()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to verify funds: {e}")
                return
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM makes WHERE name=?", (make_name,))
            res_make = cursor.fetchone()
            if not res_make: return
            make_id = res_make[0]
            
            cursor.execute("SELECT id FROM models WHERE name=? AND make_id=?", (model_name, make_id))
            res_model = cursor.fetchone()
            if not res_model: return
            model_id = res_model[0]
            
            vehicle_name = f"{make_name} {model_name} ({model_year})"
            
            if self.edit_id:
                cursor.execute("""
                    UPDATE vehicles SET 
                    vehicle_name=?, make_id=?, model_id=?, model_year=?, reg_number=?, chassis_number=?, engine_number=?, 
                    purchase_price=?, purchase_date=?, rc_book=?, rc_remark=?, insurance_status=?, insurance_until=?, insurance_remark=?, tentative_sale_price=?, purchase_account_id=?, purchased_from_id=?
                    WHERE id=?
                """, (vehicle_name, make_id, model_id, model_year, data["reg"], data["chassis"], data["engine"], 
                      data["p_price"], data["p_date"], data["rc_book"], data["rc_remark"], data["ins_status"], data["ins_until"], data["ins_remark"], data["tentative_price"], acc_id, seller_id, self.edit_id))
            else:
                cursor.execute("""
                    INSERT INTO vehicles (vehicle_name, make_id, model_id, model_year, reg_number, chassis_number, engine_number, 
                                        purchase_price, purchase_date, rc_book, rc_remark, insurance_status, insurance_until, insurance_remark, tentative_sale_price, status, purchase_account_id, purchased_from_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?, ?)
                """, (vehicle_name, make_id, model_id, model_year, data["reg"], data["chassis"], data["engine"], 
                      data["p_price"], data["p_date"], data["rc_book"], data["rc_remark"], data["ins_status"], data["ins_until"], data["ins_remark"], data["tentative_price"], acc_id, seller_id))
                
                # Financial Transaction
                print(f"Deducting Rs. {p_price} from Account ID {acc_id}")
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (p_price, acc_id))
                cursor.execute("""
                    INSERT INTO transactions (account_id, transaction_type, amount, description)
                    VALUES (?, 'WITHDRAWAL', ?, ?)
                """, (acc_id, p_price, f"Vehicle Purchase: {vehicle_name} ({data['reg']})"))
            
            conn.commit()
            conn.close()
            self.clear_form()
            self.load_purchases()
            self.load_accounts_for_purchase()
            messagebox.showinfo("Success", "Purchase saved successfully!")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save: {str(e)}")

    def check_scroll(self, event=None):
        if not self.has_more or self.loading_more:
            return
        try:
            if self._parent_canvas.yview()[1] > 0.8:
                self.load_purchases(append=True)
        except: pass

    def load_purchases(self, append=False):
        if self.loading_more or (append and not self.has_more):
            return
            
        self.loading_more = True
        
        if not append:
            self.vehicle_offset = 0
            self.has_more = True
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()
            
        offset = self.vehicle_offset
        limit = 10
        
        f_make = self.filter_make_var.get()
        f_model = self.filter_model_var.get()
        f_reg = self.filter_reg_var.get()

        def fetch():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                query = """
                    SELECT v.id, v.vehicle_name, v.reg_number, v.purchase_price, v.status, c.name 
                    FROM vehicles v
                    LEFT JOIN customers c ON v.purchased_from_id = c.id
                    LEFT JOIN makes mk ON v.make_id = mk.id
                    LEFT JOIN models md ON v.model_id = md.id
                    WHERE 1=1
                """
                params = []
                
                if f_make != "All Makes":
                    query += " AND mk.name = ?"
                    params.append(f_make)
                
                if f_model != "All Models":
                    query += " AND md.name = ?"
                    params.append(f_model)
                    
                if f_reg != "All Reg Nos":
                    query += " AND v.reg_number = ?"
                    params.append(f_reg)
                    
                query += " ORDER BY v.created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                data = cursor.fetchall()
                conn.close()
                return data
            except Exception as e:
                print(f"Error fetching purchases: {e}")
                return []

        def render(purchases):
            if not self.winfo_exists():
                self.loading_more = False
                return
                
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

            if not purchases:
                if not append:
                    for widget in self.list_container.winfo_children(): widget.destroy()
                    lbl = ctk.CTkLabel(self.list_container, text="No purchases found.", font=s.Styles.FONT_TINY, text_color="gray")
                    lbl.pack(pady=20)
                self.has_more = False
                self.loading_more = False
                return

            if len(purchases) < limit:
                self.has_more = False

            def render_purchase_row(i, purchase):
                vid, name, reg, price, v_status, sname = purchase
                row = ctk.CTkFrame(self.list_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=50, corner_radius=8, border_width=1, border_color=s.BORDER)
                row.pack(fill="x", pady=2)
                row.pack_propagate(False)
                
                ctk.CTkLabel(row, text=name, font=s.Styles.FONT_SMALL, text_color=s.TEXT).place(relx=0.0, rely=0.5, anchor="w", x=15)
                desc = f"{reg}" if not sname else f"{reg} | From: {sname}"
                ctk.CTkLabel(row, text=desc, font=s.Styles.FONT_TINY, text_color=s.TEXT).place(relx=0.3, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row, text=format_indian_currency(price), font=s.Styles.FONT_SMALL, text_color=s.GREEN).place(relx=0.5, rely=0.5, anchor="w", x=15)
                
                act_frame = ctk.CTkFrame(row, fg_color="transparent")
                act_frame.place(relx=0.7, rely=0.5, anchor="w", x=15)
                
                ctk.CTkButton(act_frame, text=t("edit"), width=60, height=28, fg_color="#3b82f6", 
                             hover_color="#2563eb", font=s.Styles.FONT_TINY,
                             command=lambda v=vid: self.load_for_edit(v)).pack(side="left", padx=2)
                
                ctk.CTkButton(act_frame, text=t("delete"), width=60, height=28, fg_color=s.RED, 
                             hover_color="#e11d48", font=s.Styles.FONT_TINY,
                             command=lambda v=vid: self.delete_purchase(v)).pack(side="left", padx=2)
                
                ctk.CTkButton(act_frame, text="🖨️ " + t("print"), width=60, height=28, fg_color=s.NAVY, 
                             hover_color=s.NAVY_DARK, font=s.Styles.FONT_TINY,
                             command=lambda v=vid: self.print_purchase_receipt(v)).pack(side="left", padx=2)
                
                if v_status == 'Available':
                    ctk.CTkButton(act_frame, text="↩️ " + t("purchase_return"), width=100, height=28, fg_color="#d97706", 
                                 hover_color="#b45309", font=s.Styles.FONT_TINY,
                                 command=lambda v=vid: self.handle_purchase_return(v)).pack(side="left", padx=2)

            def on_complete(count):
                if not self.winfo_exists(): return
                if self.has_more:
                    self.load_more_btn = ctk.CTkButton(self.list_container, text="Click to Load More Vehicles...", 
                                                      fg_color="transparent", text_color=s.PRIMARY,
                                                      hover_color=s.BORDER, font=s.Styles.FONT_SMALL_BOLD,
                                                      command=lambda: self.load_purchases(append=True))
                    self.load_more_btn.pack(pady=20, fill="x")
                self.loading_more = False

            self.render_list_chunked(self.list_container, purchases, render_purchase_row, 
                                   clear=not append, start_row_idx=offset, on_complete=on_complete)
            
            self.vehicle_offset += len(purchases)

        self.run_in_background(fetch, render)

    def load_for_edit(self, vid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, mk.name, md.name, c.name
                FROM vehicles v 
                LEFT JOIN makes mk ON v.make_id = mk.id 
                LEFT JOIN models md ON v.model_id = md.id 
                LEFT JOIN customers c ON v.purchased_from_id = c.id
                WHERE v.id=?
            """, (vid,))
            v = cursor.fetchone()
            conn.close()
            
            if v:
                self.edit_id = v[0]
                # Join results: mk.name is -3, md.name is -2, c.name is -1
                make_name = v[-3]
                model_name = v[-2]
                
                self.field_make.set(make_name or "Select Make...")
                self.load_models_for_make(make_name)
                self.field_model.set(model_name or "Select Model...")
                self.field_model_year.set(str(v[4]) if v[4] is not None else "Select Year...") # actual: 4
                
                self.reg_var.set(v[5] or "") # actual: 5
                
                self.field_p_price.delete(0, 'end'); self.field_p_price.insert(0, str(v[8]) if v[8] is not None else "") # actual: 8
                self.field_p_date.set_date(v[9] or datetime.now()) # actual: 9
                
                # RC and Insurance (Actual Indices based on PRAGMA)
                rc_val = v[10] # actual: 10
                if rc_val == "Yes": rc_val = "Received"
                elif rc_val == "No": rc_val = "Not Received"
                self.rc_var.set(rc_val if rc_val else "Not Received")
                
                self.field_rc_remark.delete(0, 'end'); self.field_rc_remark.insert(0, v[11] or "") # actual: 11
                self.insurance_var.set(v[12] if v[12] else "Expired") # actual: 12
                if v[13]: # actual: 13
                    self.field_ins_until.set_date(v[13])
                self.field_ins_remark.delete(0, 'end'); self.field_ins_remark.insert(0, v[14] or "") # actual: 14
                self.field_tentative_price.delete(0, 'end'); self.field_tentative_price.insert(0, str(v[15]) if v[15] is not None else "") # actual: 15
                
                # Paid From (index 20)
                paid_acc_id = v[20] # actual: 20
                if paid_acc_id:
                    for acc_str, aid in self.account_map.items():
                        if aid == paid_acc_id:
                            self.acc_var.set(acc_str)
                            break
                            
                # Seller (index 21)
                paid_from_cid = v[21] # actual: 21
                if paid_from_cid:
                    for c_str, cid in self.customer_map.items():
                        if cid == paid_from_cid:
                            self.seller_var.set(c_str)
                            break
                else:
                    self.seller_var.set(t("select") + " " + t("customer") + "...")
                            
                self.toggle_insurance_date()
                
                self.save_btn.configure(text="UPDATE PURCHASE")
                self.header.configure(text="Edit Purchase")
                self._parent_canvas.yview_moveto(0)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")

    def print_purchase_receipt(self, vid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, mk.name, md.name, c.name 
                FROM vehicles v 
                LEFT JOIN makes mk ON v.make_id = mk.id 
                LEFT JOIN models md ON v.model_id = md.id 
                LEFT JOIN customers c ON v.purchased_from_id = c.id
                WHERE v.id=?
            """, (vid,))
            v = cursor.fetchone()
            conn.close()
            
            if not v:
                messagebox.showerror("Error", "Purchase record not found!")
                return
            
            # Index-based mapping (from verified schema)
            name = v[1]
            reg = v[5]
            chassis = v[6] or "-"
            engine = v[7] or "-"
            try:
                p_price = float(v[8] or 0)
            except:
                p_price = 0.0
            p_date = v[9] or "-"
            year = v[4] or "-"
            rc = v[10] or "Not Received"
            rc_rem = v[11] or ""
            ins = v[12] or "Expired"
            ins_until = v[13] or "-"
            ins_rem = v[14] or ""
            seller_name = v[25] or "-"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Purchase Receipt - {reg}</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #1e293b; max-width: 800px; margin: 0 auto; padding: 40px; background: #f8fafc; }}
                    .receipt-card {{ background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 8px solid #0f172a; position: relative; }}
                    .header {{ text-align: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 20px; margin-bottom: 30px; }}
                    .header h1 {{ margin: 0; color: #0f172a; font-size: 28px; font-weight: 800; letter-spacing: -0.5px; }}
                    .header p {{ margin: 5px 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
                    .details-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 30px; }}
                    .detail-item {{ border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }}
                    .label {{ font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }}
                    .value {{ font-size: 15px; color: #1e293b; font-weight: 600; }}
                    .price-box {{ background: #f1f5f9; padding: 24px; border-radius: 8px; text-align: right; margin-top: 20px; border-left: 4px solid #10b981; }}
                    .price-label {{ font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 4px; }}
                    .price-value {{ font-size: 32px; color: #059669; font-weight: 800; }}
                    .footer {{ margin-top: 60px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 24px; }}
                    .watermark {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); font-size: 80px; color: rgba(0,0,0,0.03); font-weight: 900; z-index: 0; pointer-events: none; white-space: nowrap; }}
                    @media print {{
                        body {{ background: gray; padding: 0; }}
                        .receipt-card {{ box-shadow: none; border: 1px solid #f1f5f9; }}
                        .no-print {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <div class="receipt-card">
                    <div class="watermark">{get_company_name()}</div>
                    <div class="header">
                        <h1>{get_company_name()}</h1>
                        <p>{get_company_address()}</p>
                        <p>Contact: {get_company_contact()}</p>
                        <h3 style="margin-top:20px; color:#334155; border: 1px solid #e2e8f0; display: inline-block; padding: 4px 16px; border-radius: 20px; font-size: 12px;">OFFICIAL PURCHASE RECEIPT</h3>
                    </div>
                    
                    <div class="details-grid">
                        <div class="detail-item">
                            <div class="label">Vehicle Name</div>
                            <div class="value">{name}</div>
                        </div>
                        <div class="detail-item">
                            <div class="label">Registration No</div>
                            <div class="value">{reg}</div>
                        </div>
                        <div class="detail-item">
                            <div class="label">Model Year</div>
                            <div class="value">{year}</div>
                        </div>
                        <div class="detail-item">
                            <div class="label">Purchase Date</div>
                            <div class="value">{p_date}</div>
                        </div>
                        <div class="detail-item">
                            <div class="label">Chassis Number</div>
                            <div class="value">{chassis}</div>
                        </div>
                        <div class="detail-item">
                            <div class="label">Engine Number</div>
                            <div class="value">{engine}</div>
                        </div>
                        <div class="detail-item" style="grid-column: span 2;">
                            <div class="label">Bought From (Seller)</div>
                            <div class="value" style="color: #4338ca; font-weight: 700;">{seller_name}</div>
                        </div>
                        <div class="detail-item" style="grid-column: span 2;">
                            <div class="label">RC Document Status</div>
                            <div class="value">{rc} {f" — {rc_rem}" if rc_rem else ""}</div>
                        </div>
                        <div class="detail-item" style="grid-column: span 2;">
                            <div class="label">Insurance Status</div>
                            <div class="value">{ins} (Valid Until: {ins_until}) {f" — {ins_rem}" if ins_rem else ""}</div>
                        </div>
                    </div>
                    
                    <div class="price-box">
                        <div class="price-label">TOTAL PURCHASE VALUE</div>
                        <div class="price-value">₹{p_price:,.2f}</div>
                    </div>
                    
                    <div class="footer">
                        <p>This is a computer-generated document. It does not require a physical signature.</p>
                        <p>&copy; {datetime.now().year} {get_company_name()}. Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')} | User: {getattr(self.winfo_toplevel(), 'current_username', 'System')}</p>
                    </div>
                </div>
                
                <div class="no-print" style="text-align:center; margin-top:30px;">
                    <button onclick="window.print()" style="padding:12px 24px; background:#0f172a; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600; transition: all 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        🖨️ Click Here to Print Receipt
                    </button>
                    <p style="font-size: 12px; color: #64748b; margin-top: 10px;">Shortcut: Press Ctrl+P to print</p>
                </div>
            </body>
            </html>
            """
            
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open('file://' + os.path.realpath(temp_path))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate receipt: {e}")

    def delete_purchase(self, vid):
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this purchase record?"):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # 1. Check current status
                cursor.execute("SELECT status, vehicle_name, reg_number FROM vehicles WHERE id=?", (vid,))
                res = cursor.fetchone()
                if not res:
                    conn.close()
                    return
                
                v_status = str(res[0]).strip().lower() if res[0] else ""
                v_name = res[1]
                v_reg = res[2]

                # Block if Sold
                if v_status == 'sold':
                    messagebox.showerror("Error", f"Cannot delete Purchase record for {v_name} ({v_reg}).\n\nThis vehicle is marked as SOLD. You must delete the Sales record first.")
                    conn.close()
                    return

                # 2. Check for associated Process (Loan) - even if vehicle status is Available
                cursor.execute("SELECT COUNT(*) FROM loans WHERE vehicle_id = ?", (vid,))
                loan_count = cursor.fetchone()[0]
                if loan_count > 0:
                    messagebox.showerror("Error", f"Cannot delete Purchase record for {v_name} ({v_reg}).\n\nThere is an associated Loan (Process) record. You must delete the Loan first.")
                    conn.close()
                    return
                    
                cursor.execute("DELETE FROM vehicles WHERE id=?", (vid,))
                conn.commit()
                conn.close()
                self.load_purchases()
                messagebox.showinfo("Success", "Purchase record deleted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete purchase: {e}")

    def clear_form(self):
        self.edit_id = None
        self.field_make.set("Select Make...")
        self.field_model.set("Select Model...")
        self.field_model_year.set("Select Year...")
        self.field_model.configure(values=[])
        self.reg_var.set("")
        for entry in [self.field_p_price, self.field_tentative_price]:
            entry.delete(0, 'end')
        self.field_p_date.set_date(datetime.now())
        self.rc_var.set("Not Received")
        self.field_rc_remark.delete(0, 'end')
        self.insurance_var.set("Expired")
        self.field_ins_remark.delete(0, 'end')
        self.toggle_insurance_date()
        self.save_btn.configure(text="SAVE PURCHASE")
        self.acc_var.set("Select Account...")
        self.seller_var.set(t("select") + " " + t("customer") + "...")

    def load_customers_for_purchase(self):
        def fetch():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, phone FROM customers ORDER BY name ASC")
            res = cursor.fetchall()
            conn.close()
            return res

        def render(customers):
            if not self.winfo_exists(): return
            self.customer_map = {f"{name} ({phone})": cid for cid, name, phone in customers}
            self.field_seller.configure_values(list(self.customer_map.keys()))

        self.run_in_background(fetch, render)

    def load_makes(self):
        def fetch():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT name FROM makes ORDER BY name ASC")
            res = [r[0] for r in cursor.fetchall()]
            conn.close()
            return res

        def render(makes):
            if not self.winfo_exists(): return
            self.field_make.configure(values=[t("make")] + makes)

        self.run_in_background(fetch, render)

    def handle_purchase_return(self, vid):
        if not messagebox.askyesno(t("warning"), t("return_confirm")):
            return
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT vehicle_name, reg_number, purchase_price, purchase_account_id FROM vehicles WHERE id=?", (vid,))
            v = cursor.fetchone()
            if not v:
                conn.close()
                return
            
            v_name, reg, price, acc_id = v
            if not acc_id:
                # Fallback: search transactions if migration didn't catch it
                cursor.execute("SELECT account_id FROM transactions WHERE description LIKE ? AND amount = ? ORDER BY transaction_date DESC", (f"%({reg})%", price))
                trans = cursor.fetchone()
                if trans: acc_id = trans[0]
                else:
                    messagebox.showerror("Error", "Could not identify the account used for this purchase!")
                    conn.close()
                    return
            
            # 1. Update Account Balance
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (price, acc_id))
            
            # 2. Add Transaction
            cursor.execute("""
                INSERT INTO transactions (account_id, transaction_type, amount, description)
                VALUES (?, 'DEPOSIT', ?, ?)
            """, (acc_id, price, f"Purchase Return: {v_name} ({reg})"))
            
            # 3. Update Vehicle Status
            cursor.execute("UPDATE vehicles SET status='Purchase Returned' WHERE id=?", (vid,))
            
            conn.commit()
            conn.close()
            messagebox.showinfo(t("success"), t("purchase_return_success"))
            self.load_purchases()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def load_accounts_for_purchase(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = cursor.fetchall()
            conn.close()
            self.account_map = {f"{r[1]} (Rs. {r[2]:,.2f})": r[0] for r in accounts}
            acc_list = list(self.account_map.keys())
            self.field_acc.configure(values=acc_list)
            # Set Shop Cash as default if it exists
            for name in acc_list:
                if "Shop Cash" in name:
                    self.acc_var.set(name)
                    break
        except: pass


    def load_makes(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM makes ORDER BY name")
            makes = [r[0] for r in cursor.fetchall()]
            conn.close()
            self.field_make.configure(values=makes)
        except: pass

    def load_models_for_make(self, make_name):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM makes WHERE name=?", (make_name,))
            res = cursor.fetchone()
            if res:
                make_id = res[0]
                cursor.execute("SELECT name FROM models WHERE make_id=? ORDER BY name", (make_id,))
                models = [r[0] for r in cursor.fetchall()]
                self.field_model.configure(values=models)
                if models: self.field_model.set(models[0])
            conn.close()
        except: pass

    # --- Cascade Filter Logic ---
    def load_filter_makes(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT name FROM makes ORDER BY name")
            makes = ["All Makes"] + [r[0] for r in cursor.fetchall()]
            conn.close()
            self.filter_make.configure(values=makes)
        except: pass

    def on_filter_make_change(self, choice):
        if choice == "All Makes":
            self.filter_model_var.set("All Models")
            self.filter_model.configure(values=["All Models"])
            self.filter_reg_var.set("All Reg Nos")
            self.filter_reg.configure(values=["All Reg Nos"])
        else:
            # Load models for this make from vehicles actually in database
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT m.name 
                    FROM models m
                    JOIN makes mk ON m.make_id = mk.id
                    JOIN vehicles v ON v.model_id = m.id
                    WHERE mk.name = ?
                    ORDER BY m.name
                """, (choice,))
                models = ["All Models"] + [r[0] for r in cursor.fetchall()]
                conn.close()
                self.filter_model.configure(values=models)
                self.filter_model_var.set("All Models")
                
                # Reset Reg No filter too
                self.filter_reg_var.set("All Reg Nos")
                self.filter_reg.configure(values=["All Reg Nos"])
            except: pass
        
        self.load_purchases()

    def on_filter_model_change(self, choice):
        if choice == "All Models":
            self.filter_reg_var.set("All Reg Nos")
            self.filter_reg.configure(values=["All Reg Nos"])
        else:
            # Load reg numbers for selected make and model
            make_name = self.filter_make_var.get()
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT v.reg_number 
                    FROM vehicles v
                    JOIN makes mk ON v.make_id = mk.id
                    JOIN models md ON v.model_id = md.id
                    WHERE mk.name = ? AND md.name = ?
                    ORDER BY v.reg_number
                """, (make_name, choice))
                regs = ["All Reg Nos"] + [r[0] for r in cursor.fetchall()]
                conn.close()
                self.filter_reg.configure(values=regs)
                self.filter_reg_var.set("All Reg Nos")
            except: pass
            
        self.load_purchases()

    def on_filter_reg_change(self, choice):
        self.load_purchases()

    def clear_filters(self):
        self.filter_make_var.set("All Makes")
        self.filter_model_var.set("All Models")
        self.filter_model.configure(values=["All Models"])
        self.filter_reg_var.set("All Reg Nos")
        self.filter_reg.configure(values=["All Reg Nos"])
        self.load_purchases()

class SalesTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("vehicle_sales"), **kwargs)
        self.vehicle_map = {}
        self.customer_map = {}
        self.edit_vid = None
        
        # --- Sale Form Card ---
        self.sale_card, self.sale_form = self.create_card(t("new_sale_transaction"))
        
        # Row 1: Cascading Vehicle Selection
        self.field_make, self.make_var = self.create_select(self.sale_form, t("make"), [], 1, 0)
        self.make_var.trace_add("write", self.on_make_selected)
        
        self.field_model, self.model_var = self.create_select(self.sale_form, t("model"), [], 1, 1)
        self.model_var.trace_add("write", self.on_model_selected)
        
        self.field_vehicle, self.vehicle_var = self.create_select(self.sale_form, t("registration_no"), [], 1, 2)
        self.vehicle_var.trace_add("write", self.update_price_placeholder)
        
        # Row 2: Customer, Payment Source, Sale Price
        self.field_customer, self.customer_var = self.create_searchable_select(self.sale_form, t("customer_selection"), [], 2, 0)
        # Trace for updating payment sources when customer changes
        self.customer_var.trace_add("write", self.update_payment_sources)
        
        self.field_source, self.source_var = self.create_select(self.sale_form, t("received_in"), [], 2, 1)
        
        self.field_s_price = self.create_input(self.sale_form, t("sale_price"), 2, 2)
        
        # Row 3: Sale Date, Destination Account
        self.field_s_date = self.create_date_picker(self.sale_form, t("sale_date"), 3, 0, default_date=datetime.now())
        
        self.field_acc_dest, self.acc_dest_var = self.create_select(self.sale_form, t("destination_account"), [], 3, 1)
        self.acc_dest_map = {}
        self.save_btn, self.clear_btn = self.create_action_buttons(self.sale_form, t("confirm_sale"), self.confirm_sale, self.clear_form)
        self.save_btn.configure(fg_color=s.GREEN, hover_color="#059669")

        # --- Sales History Section ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG)
        
        self.history_header = ctk.CTkLabel(self.header_frame, text=t("sales_history"), font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.history_header.pack(side="left")
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text="Search Reg No or Vehicle...", textvariable=self.search_var, width=250)
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_sales_data())

        
        self.h_header_card = ctk.CTkFrame(self, fg_color=s.NAVY, height=45, corner_radius=8)
        self.h_header_card.pack(fill="x", padx=s.PAD_LG)
        self.h_header_card.pack_propagate(False)
        
        h_data = [(t("vehicle_description"), 0.02), (t("customer"), 0.32), (t("sale_details"), 0.62)]
        for text, rel_x in h_data:
            lbl = ctk.CTkLabel(self.h_header_card, text=text.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.WHITE)
            lbl.place(relx=rel_x, rely=0.5, anchor="w", x=15)

        self.history_container = ctk.CTkFrame(self, fg_color="transparent")
        self.history_container.pack(fill="both", expand=True, padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        # Lazy Loading State
        self.sales_offset = 0
        self.has_more = True
        self.loading_more = False
        
        # Bind scroll events
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind("<Configure>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<MouseWheel>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-4>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-5>", lambda e: self.check_scroll(), add="+")

        self.load_sales_data()

    def check_scroll(self, event=None):
        if not self.has_more or self.loading_more:
            return
        try:
            if self._parent_canvas.yview()[1] > 0.8:
                self.load_sales_data(append=True)
        except: pass

    def load_sales_data(self, append=False):
        if self.loading_more or (append and not self.has_more):
            return
            
        self.loading_more = True
        
        if not append:
            self.sales_offset = 0
            self.has_more = True
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

        offset = self.sales_offset
        limit = 10
        search_text = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        
        def fetch():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Fetch Data for Selection (only on first load)
                form_data = None
                if not append:
                    # 1. Makes
                    cursor.execute("""
                        SELECT DISTINCT mk.name 
                        FROM vehicles v
                        JOIN makes mk ON v.make_id = mk.id
                        WHERE v.status='Available' OR v.id = ?
                    """, (self.edit_vid or -1,))
                    makes = [r[0] for r in cursor.fetchall()]
                    
                    # 2. Customers
                    cursor.execute("SELECT id, name, balance, phone FROM customers ORDER BY name")
                    customers = cursor.fetchall()
                    
                    # 3. Accounts
                    cursor.execute("SELECT id, name, balance FROM accounts")
                    accounts = cursor.fetchall()
                    form_data = (makes, customers, accounts)

                # Fetch History
                query = """
                    SELECT v.id, v.vehicle_name, v.reg_number, v.sale_price, v.sale_date, c.name 
                    FROM vehicles v 
                    LEFT JOIN customers c ON v.customer_id = c.id 
                    WHERE v.status='Sold'
                """
                params = []
                
                if search_text:
                    query += " AND (v.reg_number LIKE ? OR v.vehicle_name LIKE ? OR c.name LIKE ?)"
                    params.extend([f"%{search_text}%", f"%{search_text}%", f"%{search_text}%"])
                
                query += " ORDER BY v.sale_date DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                history = cursor.fetchall()
                conn.close()
                return form_data, history
            except Exception as e:
                print(f"Error fetching sales data: {e}")
                return None, []

        def render(result):
            form_data, history = result
            if not self.winfo_exists():
                self.loading_more = False
                return
                
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

            # Update Form Selectors if available
            if form_data:
                makes, customers, accounts = form_data
                self.field_make.configure(values=makes)
                if not makes: self.make_var.set("No Stock")
                else: self.make_var.set("")
                
                self.customer_map = {f"{name} (ID: {cid}, Mob: {phone or '-'})": (cid, balance) for cid, name, balance, phone in customers}
                c_values = list(self.customer_map.keys())
                self.field_customer.configure_values(c_values if c_values else ["No Customers Found"])
                
                self.acc_dest_map = {f"{r[1]} ({format_indian_currency(r[2] or 0)})": r[0] for r in accounts}
                self.field_acc_dest.configure(values=list(self.acc_dest_map.keys()))

            if not history:
                if not append:
                    for widget in self.history_container.winfo_children(): widget.destroy()
                    lbl = ctk.CTkLabel(self.history_container, text="No sales records found.", font=s.Styles.FONT_TINY, text_color="gray")
                    lbl.pack(pady=20)
                self.has_more = False
                self.loading_more = False
                return

            if len(history) < limit:
                self.has_more = False

            def render_history_row(i, sale):
                vid, name, reg, price, date, cname = sale
                row = ctk.CTkFrame(self.history_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=8)
                row.pack(fill="x", pady=2)
                row.pack_propagate(False)
                
                info_f = ctk.CTkFrame(row, fg_color="transparent")
                info_f.pack(side="left", padx=15)
                ctk.CTkLabel(info_f, text=f"{name} ({reg})", font=s.Styles.FONT_SMALL).pack(side="left")
                ctk.CTkLabel(info_f, text=f" | {cname or 'Unknown'}", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(side="left", padx=5)
                
                act_f = ctk.CTkFrame(row, fg_color="transparent")
                act_f.pack(side="right", padx=10)
                
                ctk.CTkLabel(act_f, text=f"{format_indian_currency(price or 0)} - {date}", font=s.Styles.FONT_SMALL, text_color=s.RED, width=180, anchor="e").pack(side="right", padx=10)
                
                ctk.CTkButton(act_f, text="🗑 " + t("delete"), width=70, height=30, fg_color=s.RED, hover_color="#e11d48", 
                             font=s.Styles.FONT_TINY, command=lambda v=vid: self.delete_sale(v)).pack(side="right", padx=2)
                
                ctk.CTkButton(act_f, text="✏️ " + t("edit"), width=60, height=30, fg_color=s.BLUE, hover_color="#2563eb", 
                             font=s.Styles.FONT_TINY, command=lambda v=vid: self.edit_sale(v)).pack(side="right", padx=2)
                
                ctk.CTkButton(act_f, text="👁 " + t("view"), width=70, height=30, fg_color=s.GREEN, hover_color="#059669", 
                             font=s.Styles.FONT_TINY, command=lambda v=vid: self.view_sale(v)).pack(side="right", padx=2)

                ctk.CTkButton(act_f, text="🖨️ " + t("print"), width=60, height=30, fg_color=s.NAVY, hover_color=s.NAVY_DARK, 
                             font=s.Styles.FONT_TINY, command=lambda v=vid: self.print_sale_receipt(v)).pack(side="right", padx=2)
                
                ctk.CTkButton(act_f, text="↩️ " + t("sales_return"), width=100, height=30, fg_color="#d97706", hover_color="#b45309", 
                             font=s.Styles.FONT_TINY, command=lambda v=vid: self.handle_sales_return(v)).pack(side="right", padx=2)

            def on_complete(count):
                if not self.winfo_exists(): return
                if self.has_more:
                    self.load_more_btn = ctk.CTkButton(self.history_container, text="Click to Load More Sales...", 
                                                      fg_color="transparent", text_color=s.PRIMARY,
                                                      hover_color=s.BORDER, font=s.Styles.FONT_SMALL_BOLD,
                                                      command=lambda: self.load_sales_data(append=True))
                    self.load_more_btn.pack(pady=20, fill="x")
                self.loading_more = False

            self.render_list_chunked(self.history_container, history, render_history_row, 
                                   clear=not append, start_row_idx=offset, on_complete=on_complete)
            
            self.sales_offset += len(history)

        self.run_in_background(fetch, render)

    def on_make_selected(self, *args):
        make_name = self.make_var.get()
        if not make_name or make_name == t("make"): return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT md.name 
                FROM vehicles v
                JOIN makes mk ON v.make_id = mk.id
                JOIN models md ON v.model_id = md.id
                WHERE mk.name = ? AND (v.status='Available' OR v.id = ?)
                ORDER BY md.name
            """, (make_name, self.edit_vid or -1))
            models = [r[0] for r in cursor.fetchall()]
            conn.close()
            
            self.field_model.configure(values=models)
            if models:
                self.model_var.set(models[0])
            else:
                self.model_var.set("")
                self.field_vehicle.configure(values=[])
                self.vehicle_var.set("")
        except Exception as e:
            print(f"Error loading models for sale: {e}")

    def on_model_selected(self, *args):
        make_name = self.make_var.get()
        model_name = self.model_var.get()
        if not model_name: return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, v.reg_number, v.purchase_price, v.tentative_sale_price, l.customer_id
                FROM vehicles v
                JOIN makes mk ON v.make_id = mk.id
                JOIN models md ON v.model_id = md.id
                LEFT JOIN loans l ON v.id = l.vehicle_id AND l.status = 'Active'
                WHERE mk.name = ? AND md.name = ? AND (v.status='Available' OR v.id = ?)
                ORDER BY v.reg_number
            """, (make_name, model_name, self.edit_vid or -1))
            stock = cursor.fetchall()
            conn.close()
            
            self.vehicle_map = {reg: (vid, price, tentative, loan_cid) 
                                for vid, reg, price, tentative, loan_cid in stock}
            regs = list(self.vehicle_map.keys())
            self.field_vehicle.configure(values=regs)
            if regs:
                self.vehicle_var.set(regs[0])
            else:
                self.vehicle_var.set("")
        except Exception as e:
            print(f"Error loading regs for sale: {e}")

    def update_price_placeholder(self, *args):
        selected = self.vehicle_var.get()
        if selected in self.vehicle_map:
            vid, p_price, tentative, loan_cid = self.vehicle_map[selected]
            self.field_s_price.configure(placeholder_text=f"Pur. Price: {format_indian_currency(p_price)}")
            if tentative:
                self.field_s_price.delete(0, 'end')
                self.field_s_price.insert(0, str(tentative))
            
            # Restriction Logic: If vehicle has a linked loan, force the customer selection
            if loan_cid:
                # Find customer string in customer_map
                target_cust = None
                for c_str, (cid, _) in self.customer_map.items():
                    if cid == loan_cid:
                        target_cust = c_str
                        break
                
                if target_cust:
                    self.field_customer.set(target_cust)
                    self.field_customer.entry.configure(state="disabled")
                    # Update payment sources for this customer
                    self.update_payment_sources()
                    
                    # Auto-select Customer Loan source
                    for choice in self.field_source.cget("values"):
                        if choice.startswith("Customer Loan"):
                            self.source_var.set(choice)
                            break
            else:
                self.field_customer.entry.configure(state="normal")
        else:
            self.field_s_price.configure(placeholder_text="0.00")
            self.field_customer.entry.configure(state="normal")

    def update_payment_sources(self, *args):
        selected = self.field_customer.get()
        sources = ["General Cash/Bank"]
        if selected in self.customer_map:
            cid, balance = self.customer_map[selected]
            sources.append(f"Customer Loan (Available: ₹{balance:,.2f})")
        self.field_source.configure(values=sources)
        # Keep current selection if it still exists in new values, otherwise default to [0]
        current = self.source_var.get()
        if current not in sources:
            self.source_var.set(sources[0])

    def confirm_sale(self):
        v_selected = self.vehicle_var.get()
        c_selected = self.field_customer.get()
        s_selected = self.source_var.get()
        acc_selected = self.acc_dest_var.get()
        price = self.field_s_price.get()
        date = self.field_s_date.get() or datetime.now().strftime('%d-%m-%Y')
        
        if cl.is_date_closed(date):
            messagebox.showerror("Error", f"The date {date} has already been closed. No new sales can be recorded for this date.")
            return
        
        if v_selected == "" or v_selected == t("registration_no"):
            messagebox.showerror("Error", "Please select a vehicle registration number!")
            return
        if not c_selected or c_selected in ["Select Customer...", "No Customers Found"]:
            messagebox.showerror("Error", "Please select a customer!")
            return
        if acc_selected == "Select Destination Account...":
            messagebox.showerror("Error", "Please select a destination account!")
            return
        if not price:
            messagebox.showerror("Error", "Sale Price is required!")
            return
            
        # vehicle_map is {reg: (vid, purchase_price, tentative, loan_cid)}
        vid, _, _, loan_cid = self.vehicle_map.get(v_selected, (None, 0, 0, None))
        cid, c_balance = self.customer_map.get(c_selected, (None, 0))
        
        # Validation for loan-linked vehicle
        if loan_cid and cid != loan_cid:
            messagebox.showerror("Error", "This vehicle is reserved for a specific customer due to a sanctioned loan!")
            return
            
        acc_id = self.acc_dest_map.get(acc_selected)
        
        try:
            sale_price = float(price)
        except:
            messagebox.showerror("Error", "Invalid Sale Price!")
            return
            
        # Check if using customer loan balance
        use_loan = s_selected.startswith("Customer Loan")
        if use_loan and c_balance < sale_price:
            messagebox.showerror("Insufficient Funds", f"Customer only has ₹{c_balance:,.2f} in loan balance!")
            return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # If editing, revert previous sale first
            if self.edit_vid:
                self._revert_sale(cursor, self.edit_vid)
            
            cursor.execute("""
                UPDATE vehicles SET status='Sold', sale_price=?, sale_date=?, customer_id=?
                WHERE id=?
            """, (sale_price, date, cid, vid))
            
            # Financial Transaction
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (sale_price, acc_id))
            
            if use_loan:
                # Deduct from customer balance
                cursor.execute("UPDATE customers SET balance = balance - ? WHERE id = ?", (sale_price, cid))
                desc = f"Vehicle Sale (Loan Pay): {v_selected}"
            else:
                desc = f"Vehicle Sale (Cash): {v_selected}"
                
            cursor.execute("""
                INSERT INTO transactions (account_id, transaction_type, amount, description)
                VALUES (?, 'DEPOSIT', ?, ?)
            """, (acc_id, sale_price, desc))
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Sale record UPDATED!" if self.edit_vid else "Vehicle marked as SOLD!")
            self.edit_vid = None # Clear edit state
            
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def clear_form(self):
        self.edit_vid = None
        self.make_var.set("")
        self.model_var.set("")
        self.vehicle_var.set("")
        self.field_model.configure(values=[])
        self.field_vehicle.configure(values=[])
        self.customer_var.set("")
        self.field_customer.set("")
        self.source_var.set("Select Cash Source...")
        self.acc_dest_var.set("Select Destination Account...")
        self.field_s_price.delete(0, 'end')
        self.field_customer.entry.configure(state="normal")
        self.save_btn.configure(text=t("confirm_sale"))
        self.load_sales_data()

    def print_sale_receipt(self, vid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, mk.name, md.name, c.name, c.phone, c.city
                FROM vehicles v 
                LEFT JOIN makes mk ON v.make_id = mk.id 
                LEFT JOIN models md ON v.model_id = md.id 
                LEFT JOIN customers c ON v.customer_id = c.id
                WHERE v.id=?
            """, (vid,))
            v = cursor.fetchone()
            conn.close()
            
            if not v:
                messagebox.showerror("Error", "Sale record not found!")
                return
            
            # Mapping based on typical vehicle + customer join
            # v indices: 0:id, 1:vehicle_name, 2:reg, 3:chassis, 4:engine, 5:purchase_price, 6:purchase_date...
            # sale_price: 11, sale_date: 12, customer_id: 13, model_year: 14...
            # mk.name: -5, md.name: -4, cust_name: -3, cust_phone: -2, cust_city: -1
            
            reg = v[5]
            v_name = v[1]
            chassis = v[6] or "-"
            engine = v[7] or "-"
            year = v[4] or "-"
            
            try:
                s_price = float(v[17] or 0)
            except:
                s_price = 0.0
            s_date = v[18] or "-"
            
            c_name = v[-3] or "Unknown Buyer"
            c_phone = v[-2] or "-"
            c_city = v[-1] or "-"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Sales Receipt - {reg}</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #1e293b; max-width: 800px; margin: 0 auto; padding: 40px; background: #f8fafc; }}
                    .receipt-card {{ background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 8px solid #059669; position: relative; }}
                    .header {{ text-align: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 20px; margin-bottom: 30px; }}
                    .header h1 {{ margin: 0; color: #0f172a; font-size: 28px; font-weight: 800; letter-spacing: -0.5px; }}
                    .header p {{ margin: 5px 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
                    
                    .section-title {{ font-size: 12px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; border-bottom: 1px solid #f1f5f9; padding-bottom: 5px; }}
                    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-bottom: 30px; }}
                    
                    .detail-item {{ margin-bottom: 12px; }}
                    .label {{ font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 700; }}
                    .value {{ font-size: 15px; color: #1e293b; font-weight: 600; }}
                    
                    .price-box {{ background: #f0fdf4; padding: 24px; border-radius: 8px; text-align: right; margin-top: 20px; border-left: 4px solid #10b981; }}
                    .price-label {{ font-size: 13px; color: #166534; font-weight: 600; margin-bottom: 4px; }}
                    .price-value {{ font-size: 32px; color: #15803d; font-weight: 800; }}
                    
                    .footer {{ margin-top: 60px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 24px; }}
                    .watermark {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); font-size: 80px; color: rgba(0,0,0,0.02); font-weight: 900; z-index: 0; pointer-events: none; white-space: nowrap; }}
                    @media print {{
                        body {{ background: white; padding: 0; }}
                        .receipt-card {{ box-shadow: none; border: 1px solid #f1f5f9; }}
                        .no-print {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <div class="receipt-card">
                    <div class="watermark">V-SOLD</div>
                    <div class="header">
                        <h1>{get_company_name()}</h1>
                        <p>{get_company_address()}</p>
                        <p>Contact: {get_company_contact()}</p>
                        <h3 style="margin-top:20px; color:#065f46; border: 1px solid #d1fae5; background: #ecfdf5; display: inline-block; padding: 6px 20px; border-radius: 20px; font-size: 13px; font-weight: 700;">OFFICIAL SALES RECEIPT</h3>
                    </div>
                    
                    <div class="grid">
                        <div class="col">
                            <div class="section-title">Buyer Details</div>
                            <div class="detail-item">
                                <div class="label">Customer Name</div>
                                <div class="value">{c_name}</div>
                            </div>
                            <div class="detail-item">
                                <div class="label">Phone Number</div>
                                <div class="value">{c_phone}</div>
                            </div>
                            <div class="detail-item">
                                <div class="label">City / Address</div>
                                <div class="value">{c_city}</div>
                            </div>
                        </div>
                        <div class="col">
                            <div class="section-title">Vehicle Details</div>
                            <div class="detail-item">
                                <div class="label">Vehicle Model</div>
                                <div class="value">{v_name}</div>
                            </div>
                            <div class="detail-item">
                                <div class="label">Registration No</div>
                                <div class="value">{reg}</div>
                            </div>
                            <div class="detail-item">
                                <div class="label">Model Year / Date</div>
                                <div class="value">{year} | Sold on {s_date}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section-title">Technical Specs</div>
                    <div class="grid" style="gap: 20px;">
                        <div class="detail-item">
                            <div class="label">Chassis Number</div>
                            <div class="value">{chassis}</div>
                        </div>
                        <div class="detail-item">
                            <div class="label">Engine Number</div>
                            <div class="value">{engine}</div>
                        </div>
                    </div>
                    
                    <div class="price-box">
                        <div class="price-label">TOTAL SALE CONSIDERATION</div>
                        <div class="price-value">₹{s_price:,.2f}</div>
                    </div>
                    
                    <div class="footer">
                        <p>This is a computer-generated document. Subject to realization of payments.</p>
                        <p>&copy; {datetime.now().year} Nagudi Auto Finance. Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')} | User: {getattr(self.winfo_toplevel(), 'current_username', 'System')}</p>
                    </div>
                </div>
                
                <div class="no-print" style="text-align:center; margin-top:30px;">
                    <button onclick="window.print()" style="padding:12px 24px; background:#059669; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:700; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        🖨️ Print Sales Receipt
                    </button>
                </div>
            </body>
            </html>
            """
            
            import tempfile
            import webbrowser
            import os
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open('file://' + os.path.realpath(temp_path))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate sales receipt: {e}")

    def view_sale(self, vid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.vehicle_name, v.reg_number, v.sale_price, v.sale_date, c.name, c.phone, v.purchase_price
                FROM vehicles v 
                LEFT JOIN customers c ON v.customer_id = c.id 
                WHERE v.id=?
            """, (vid,))
            sale = cursor.fetchone()
            conn.close()
            if sale:
                SaleDetailsWindow(self.winfo_toplevel(), sale)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sale details: {e}")

    def edit_sale(self, vid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Fetch Make, Model, and Reg for cascade pre-fill
            cursor.execute("""
                SELECT mk.name, md.name, v.reg_number, v.customer_id, v.sale_price, v.sale_date 
                FROM vehicles v
                JOIN makes mk ON v.make_id = mk.id
                JOIN models md ON v.model_id = md.id
                WHERE v.id=?
            """, (vid,))
            v = cursor.fetchone()
            conn.close()
            
            if v:
                make, model, reg, cid, price, date = v
                self.edit_vid = vid # Set edit state
                
                # Pre-fill Cascading Vehicle Dropdowns
                self.make_var.set(make)
                self.on_make_selected()
                self.model_var.set(model)
                self.on_model_selected()
                self.vehicle_var.set(reg)
                
                # Find customer string
                for c_str, (c_id, _) in self.customer_map.items():
                    if c_id == cid:
                        self.customer_var.set(c_str)
                        break
                
                self.field_s_price.delete(0, 'end')
                self.field_s_price.insert(0, str(price))
                self.field_s_date.set_date(date)
                
                # Scroll to top
                self._parent_canvas.yview_moveto(0)
                self.load_sales_data() # Refresh vehicle list to include this vehicle
                
                messagebox.showinfo("Edit Mode", "Sale data loaded into the form. You can modify and confirm the sale again.\nThe old financial records will be automatically corrected on confirmation.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sale for edit: {e}")

    def delete_sale(self, vid):
        def proceed_delete():
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this sale record?\nThis will revert the vehicle to 'Available' and adjust financial records."):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    self._revert_sale(cursor, vid)
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Sale record deleted successfully!")
                    self.load_sales_data()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete sale: {e}")
        
        PasswordDialog(self.winfo_toplevel(), on_success=proceed_delete)

    def _revert_sale(self, cursor, vid):
        # 1. Get Sale Details
        cursor.execute("SELECT sale_price, customer_id, vehicle_name, reg_number FROM vehicles WHERE id=?", (vid,))
        v = cursor.fetchone()
        if not v: return
        price, cid, v_name, reg = v
        
        # 2. Find associated transaction to get account_id and check for loan pay
        # Searching by reg number in description
        cursor.execute("SELECT account_id, description FROM transactions WHERE description LIKE ? AND amount = ?", (f"%({reg})%", price))
        trans = cursor.fetchone()
        
        if trans:
            acc_id, desc = trans
            # Revert account balance
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (price, acc_id))
            # Delete Transaction
            cursor.execute("DELETE FROM transactions WHERE description LIKE ? AND amount = ?", (f"%({reg})%", price))
            
            # If it was a loan payment, revert customer balance
            if "Loan Pay" in desc:
                cursor.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (price, cid))
        
        # 3. Revert Vehicle Status
        cursor.execute("""
            UPDATE vehicles SET status='Available', sale_price=NULL, sale_date=NULL, customer_id=NULL 
            WHERE id=?
        """, (vid,))

    def handle_sales_return(self, vid):
        if not messagebox.askyesno(t("warning"), t("return_confirm")):
            return
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 1. Get Sale Details
            cursor.execute("SELECT sale_price, customer_id, vehicle_name, reg_number FROM vehicles WHERE id=?", (vid,))
            v = cursor.fetchone()
            if not v:
                conn.close()
                return
            price, cid, v_name, reg = v
            
            # 2. Find associated transaction
            cursor.execute("SELECT account_id, description FROM transactions WHERE description LIKE ? AND amount = ? ORDER BY transaction_date DESC", (f"%({reg})%", price))
            trans = cursor.fetchone()
            
            if trans:
                acc_id, desc = trans
                # Revert account balance (withdrawal for return)
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (price, acc_id))
                
                # Add Return Transaction (instead of just deleting)
                cursor.execute("""
                    INSERT INTO transactions (account_id, transaction_type, amount, description)
                    VALUES (?, 'WITHDRAWAL', ?, ?)
                """, (acc_id, price, f"Sales Return: {v_name} ({reg})"))
                
                # If it was a loan payment, revert customer balance
                if "Loan Pay" in desc:
                    cursor.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (price, cid))
            
            # 3. Check for linked active loan
            cursor.execute("SELECT id FROM loans WHERE vehicle_id=? AND status='Active'", (vid,))
            loan = cursor.fetchone()
            if loan:
                # Mark loan as Cancelled/Returned
                cursor.execute("UPDATE loans SET status='Returned' WHERE id=?", (loan[0],))
            
            # 4. Revert Vehicle Status
            cursor.execute("""
                UPDATE vehicles SET status='Available', sale_price=NULL, sale_date=NULL, customer_id=NULL 
                WHERE id=?
            """, (vid,))
            
            conn.commit()
            conn.close()
            messagebox.showinfo(t("success"), t("sales_return_success"))
            self.load_sales_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

class SaleDetailsWindow(ctk.CTkToplevel):
    def __init__(self, master, sale_data, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Sale Details")
        self.geometry("450x550")
        self.resizable(False, False)
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        if master: self.transient(master)
        
        v_name, reg, price, date, c_name, c_phone, p_price = sale_data
        price = float(price or 0)
        p_price = float(p_price or 0)
        
        # Header
        header = ctk.CTkFrame(self, fg_color=s.NAVY_DARK, height=80, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="SALE RECEIPT DETAILS", font=s.Styles.FONT_H3, text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Details Grid
        details = [
            ("Vehicle", f"{v_name}"),
            ("Reg Number", f"{reg}"),
            ("Customer", f"{c_name or 'Unknown'}"),
            ("Phone", f"{c_phone or '-'}"),
            ("Sale Date", f"{date or '-'}"),
            ("Purchase Price", f"₹{p_price:,.2f}"),
            ("Sale Price", f"₹{price:,.2f}"),
            ("Profit/Loss", f"₹{price - p_price:,.2f}")
        ]
        
        for i, (label, val) in enumerate(details):
            row = ctk.CTkFrame(main, fg_color="transparent")
            row.pack(fill="x", pady=8)
            ctk.CTkLabel(row, text=label, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(side="left")
            ctk.CTkLabel(row, text=val, font=s.Styles.FONT_SMALL, text_color=s.TEXT if "Price" not in label else s.GOLD).pack(side="right")
        
        # Footer
        ctk.CTkButton(self, text="Close", fg_color=s.GOLD, command=self.destroy).pack(pady=20)

class ViewLoanWindow(ctk.CTkToplevel):
    def __init__(self, master, loan_data, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change
        self.title("Loan Details")
        self.geometry("550x750")
        self.resizable(False, False)
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        if master: self.transient(master)
        
        lid, c_name, c_phone, v_name, reg, amount, tenure, interest, emi, date, dp, fee, d_path, due_date, status = loan_data
        self.loan_data = loan_data # Save for HTML export
        self.loan_id = lid
        self.loan_status = status
        self.customer_name = c_name
        
        header = ctk.CTkFrame(self, fg_color=s.NAVY_DARK, height=70, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="LOAN ACCOUNT DETAILS", font=s.Styles.FONT_H3, text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        
        btn_print = ctk.CTkButton(header, text="🖨️ Export HTML", width=120, height=32, 
                                  fg_color=s.GOLD, hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD,
                                  command=self.export_loan_to_html)
        btn_print.place(relx=0.95, rely=0.5, anchor="e")
        
        main_container = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        main = ctk.CTkFrame(main_container, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=25, pady=15)
        
        # Upper Section: Info
        info_f = ctk.CTkFrame(main, fg_color=s.CARD, corner_radius=s.Styles.RADIUS, border_width=1, border_color=s.BORDER)
        info_f.pack(fill="x", pady=(0, 10))
        
        details = [
            ("Loan ID", f"L-{lid}"), ("Customer", f"{c_name}"), ("Phone", f"{c_phone or '-'}"),
            ("Vehicle", f"{v_name or '-'}") , ("Reg No", f"{reg or '-'}") , ("Loan Date", f"{date}"),
            ("Loan Amount", f"₹{amount:,.2f}"), ("Down Payment", f"₹{dp:,.2f}"), ("Tenure", f"{tenure} Months"),
            ("Interest Rate", f"{interest}%"), ("EMI Amount", f"₹{emi:,.2f}"), ("Document Fee", f"₹{fee:,.2f}"),
            ("Due Start Date", f"{due_date or '-'}")
        ]
        
        for i, (label, val) in enumerate(details):
            row = ctk.CTkFrame(info_f, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=15)
            ctk.CTkLabel(row, text=label, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(side="left")
            ctk.CTkLabel(row, text=val, font=s.Styles.FONT_SMALL, text_color=s.TEXT).pack(side="right")
            
        if d_path:
            ctk.CTkButton(main, text="📄 View Loan Agreement", fg_color="#10b981", height=32,
                          command=lambda p=d_path: self.master.view_loan_doc(p)).pack(pady=5)
                          
        # EMI History Section
        ctk.CTkLabel(main, text="EMI COLLECTION HISTORY", font=s.Styles.FONT_SMALL, text_color=s.TEXT).pack(pady=(15, 5), anchor="w")
        
        self.hist_scroll = ctk.CTkScrollableFrame(main, fg_color=s.CARD, height=200, corner_radius=s.Styles.RADIUS, border_width=1, border_color=s.BORDER)
        self.hist_scroll.pack(fill="x", pady=5)
        
        # Calculated Summary
        self.sum_frame = ctk.CTkFrame(main, fg_color="#ecfdf5", height=60, corner_radius=8)
        self.sum_frame.pack(fill="x", pady=10)
        self.sum_label = ctk.CTkLabel(self.sum_frame, text="Calculating balance...", font=s.Styles.FONT_TINY, text_color="#065f46")
        self.sum_label.pack(pady=10)
        
        self.load_emi_data(lid, amount)
        
        # Call History Section (Overdue Logs)
        ctk.CTkLabel(main, text="CALL HISTORY (COLLECTION)", font=s.Styles.FONT_SMALL, text_color="#d97706").pack(pady=(15, 5), anchor="w")
        self.call_scroll = ctk.CTkScrollableFrame(main, fg_color="#fff7ed", height=150, corner_radius=8, border_width=1, border_color="#ffedd5")
        self.call_scroll.pack(fill="x", pady=5)
        
        self.load_call_history(lid)
        
        if self.loan_status == 'Closed':
            ctk.CTkButton(self, text="🔓 RE-OPEN LOAN (Revoke Closure)", fg_color=s.RED, hover_color="#e11d48", 
                          font=s.Styles.FONT_SMALL_BOLD, command=self.revoke_closure).pack(pady=(10, 5))
        
        ctk.CTkButton(self, text="Close", fg_color=s.GOLD, command=self.destroy).pack(pady=(10, 15))

    def load_call_history(self, lid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT call_date, call_time, response_text, status FROM call_logs WHERE loan_id=? ORDER BY created_at DESC", (lid,))
            logs = cursor.fetchall()
            conn.close()
            
            if not logs:
                ctk.CTkLabel(self.call_scroll, text="No call logs recorded.", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(pady=20)
                return
                
            for i, (date, time, res, status) in enumerate(logs):
                row = ctk.CTkFrame(self.call_scroll, fg_color=s.CARD if i % 2 == 0 else s.BORDER, corner_radius=4)
                row.pack(fill="x", pady=2, padx=2)
                
                # Header of the log entry
                head = ctk.CTkFrame(row, fg_color="transparent")
                head.pack(fill="x", padx=10, pady=(5, 0))
                ctk.CTkLabel(head, text=f"{date} {time}", font=s.Styles.FONT_TINY_BOLD).pack(side="left")
                
                # Status tag
                color = "#d97706" if status == "Responded" else "#dc2626" if status == "Switch Off" else "#059669" if status == "Promise to Pay" else s.MUTED
                ctk.CTkLabel(head, text=status.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=color).pack(side="right")
                
                # Response body
                body = ctk.CTkLabel(row, text=res, font=s.Styles.FONT_TINY, wraplength=450, justify="left", anchor="w")
                body.pack(fill="x", padx=10, pady=(0, 5))
        except: pass

    def load_emi_data(self, lid, total_amt):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT payment_date, amount, remarks FROM payments WHERE loan_id=? ORDER BY created_at DESC", (lid,))
            payments = cursor.fetchall()
            conn.close()
            
            if not payments:
                ctk.CTkLabel(self.hist_scroll, text="No EMI payments recorded yet.", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(pady=30)
                self.sum_label.configure(text=f"Balance Remaining: ₹{total_amt:,.2f} | 0 EMI Paid")
                return
            
            total_paid = 0
            for i, (date, amt, rem) in enumerate(payments):
                total_paid += amt
                row = ctk.CTkFrame(self.hist_scroll, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=35, corner_radius=0)
                row.pack(fill="x")
                ctk.CTkLabel(row, text=date, font=s.Styles.FONT_TINY).place(relx=0.05, rely=0.5, anchor="w")
                ctk.CTkLabel(row, text=f"₹{amt:,.2f}", font=s.Styles.FONT_TINY, text_color=s.GREEN).place(relx=0.35, rely=0.5, anchor="w")
                ctk.CTkLabel(row, text=rem or "-", font=s.Styles.FONT_TINY, width=150, anchor="w").place(relx=0.6, rely=0.5, anchor="w")
            
            self.sum_label.configure(text=f"Total Paid: ₹{total_paid:,.2f} | Balance Remaining: ₹{max(0, total_amt - total_paid):,.2f} | {len(payments)} EMI Paid")
        except: pass

    def export_loan_to_html(self):
        try:
            lid, c_name, c_phone, v_name, reg, amount, tenure, interest, emi, date, dp, fee, d_path, due_date, status = self.loan_data
            
            # Fetch Payment History
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT payment_date, amount, remarks FROM payments WHERE loan_id=? ORDER BY payment_date ASC", (lid,))
            payments = cursor.fetchall()
            conn.close()
            
            history_rows_html = ""
            total_paid = 0
            for i, (p_date, p_amt, p_rem) in enumerate(payments):
                total_paid += p_amt
                history_rows_html += f"""
                <tr>
                    <td>{i+1}</td>
                    <td>{p_date}</td>
                    <td style="color: #059669; font-weight: 600;">₹{p_amt:,.2f}</td>
                    <td>{p_rem or '-'}</td>
                </tr>
                """
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Loan Account - L-{lid}</title>
                <style>
                    body {{ font-family: 'Segoe UI', system-ui, sans-serif; color: #1e293b; max-width: 900px; margin: 0 auto; padding: 40px; background: #f8fafc; }}
                    .card {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); border-top: 10px solid #1e293b; }}
                    .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #f1f5f9; padding-bottom: 30px; margin-bottom: 30px; }}
                    .company-info h1 {{ margin: 0; color: #0f172a; font-size: 32px; letter-spacing: -1px; }}
                    .company-info p {{ margin: 5px 0; color: #64748b; font-size: 14px; }}
                    .loan-tag {{ background: #1e293b; color: white; padding: 8px 16px; border-radius: 6px; font-weight: 700; font-size: 14px; }}
                    
                    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-bottom: 40px; }}
                    .section-title {{ font-size: 12px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; border-bottom: 1px solid #f1f5f9; padding-bottom: 5px; }}
                    
                    .info-group {{ margin-bottom: 15px; display: flex; justify-content: space-between; font-size: 15px; }}
                    .info-label {{ color: #64748b; }}
                    .info-value {{ font-weight: 600; color: #1e293b; }}
                    
                    .summary-box {{ background: #f0fdf4; border: 1px solid #dcfce7; padding: 25px; border-radius: 12px; display: flex; justify-content: space-around; margin-bottom: 40px; text-align: center; }}
                    .summary-item .label {{ font-size: 12px; color: #166534; text-transform: uppercase; font-weight: 700; margin-bottom: 5px; }}
                    .summary-item .value {{ font-size: 24px; color: #15803d; font-weight: 800; }}
                    .summary-item.balance .value {{ color: #dc2626; }}
                    .summary-item.balance .label {{ color: #991b1b; }}
                    
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th {{ text-align: left; background: #f8fafc; color: #64748b; padding: 12px 15px; font-size: 11px; text-transform: uppercase; border-bottom: 2px solid #e2e8f0; }}
                    td {{ padding: 12px 15px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
                    
                    .footer {{ margin-top: 50px; padding-top: 20px; border-top: 2px solid #f1f5f9; text-align: center; font-size: 12px; color: #64748b; }}
                    @media print {{
                        body {{ background: white; padding: 0; }}
                        .card {{ box-shadow: none; border: 1px solid #e2e8f0; }}
                        .no-print {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="header">
                        <div class="company-info">
                            <h1>{get_company_name()}</h1>
                            <p>{get_company_address()}</p>
                            <p>Contact: {get_company_contact()}</p>
                        </div>
                        <div class="loan-tag">LOAN ID: L-{lid}</div>
                    </div>
                    
                    <div class="grid">
                        <div class="col">
                            <div class="section-title">Customer Details</div>
                            <div class="info-group"><span class="info-label">Name</span> <span class="info-value">{c_name}</span></div>
                            <div class="info-group"><span class="info-label">Phone</span> <span class="info-value">{c_phone or '-'}</span></div>
                            <div class="info-group"><span class="info-label">Loan Date</span> <span class="info-value">{date}</span></div>
                            <div class="info-group"><span class="info-label">Due Start</span> <span class="info-value">{due_date or '-'}</span></div>
                        </div>
                        <div class="col">
                            <div class="section-title">Vehicle & Finance</div>
                            <div class="info-group"><span class="info-label">Vehicle</span> <span class="info-value">{v_name or '-'}</span></div>
                            <div class="info-group"><span class="info-label">Reg Number</span> <span class="info-value">{reg or '-'}</span></div>
                            <div class="info-group"><span class="info-label">Loan Amount</span> <span class="info-value">₹{amount:,.2f}</span></div>
                            <div class="info-group"><span class="info-label">EMI Amount</span> <span class="info-value">₹{emi:,.2f} x {tenure}m</span></div>
                        </div>
                    </div>
                    
                    <div class="summary-box">
                        <div class="summary-item">
                            <div class="label">Total Loan</div>
                            <div class="value">₹{amount:,.2f}</div>
                        </div>
                        <div class="summary-item">
                            <div class="label">Total Paid</div>
                            <div class="value">₹{total_paid:,.2f}</div>
                        </div>
                        <div class="summary-item balance">
                            <div class="label">Outstanding</div>
                            <div class="value">₹{max(0, amount - total_paid):,.2f}</div>
                        </div>
                    </div>
                    
                    <div class="section-title">Payment History</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Sl</th>
                                <th>Payment Date</th>
                                <th>Amount Paid</th>
                                <th>Remarks</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history_rows_html if history_rows_html else '<tr><td colspan="4" style="text-align:center; padding: 40px; color: #64748b;">No payments recorded for this account.</td></tr>'}
                        </tbody>
                    </table>
                    
                    <div class="footer">
                        <p>This is a computer-generated statement and does not require a physical signature.</p>
                        <p>&copy; {datetime.now().year} {get_company_name()}. Generated on {datetime.now().strftime('%d-%m-%Y %I:%M %p')} | User: {getattr(self.winfo_toplevel(), 'current_username', 'System')}</p>
                    </div>
                </div>
                
                <div class="no-print" style="text-align:center; margin-top:30px;">
                    <button onclick="window.print()" style="padding:12px 24px; background:#1e293b; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:700;">🖨️ Print Statement</button>
                </div>
            </body>
            </html>
            """
            
            import tempfile
            import webbrowser
            import os
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open('file://' + os.path.realpath(temp_path))
            
        except Exception as e:
            print(f"Error exporting loan to HTML: {e}")
            messagebox.showerror("Export Error", f"Failed to generate HTML report: {e}")

    def revoke_closure(self):
        if not messagebox.askyesno("Confirm Revoke", "Are you sure you want to RE-OPEN this loan?\n\nThis will:\n1. Revert the settlement payment\n2. Re-activate the loan account."):
            return
            
        from ui_components import PasswordDialog
        
        def proceed_revoke():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # 1. Find pre-closure payment
                cursor.execute("""
                    SELECT id, amount, account_id, payment_date 
                    FROM payments 
                    WHERE loan_id = ? AND remarks LIKE 'PRE-CLOSURE SETTLEMENT%'
                """, (self.loan_id,))
                payment = cursor.fetchone()
                
                if not payment:
                    # If payment is missing, it might have been deleted manually by the user
                    if messagebox.askyesno("Payment Missing", "The settlement payment record for this closure could not be found.\n\nDo you want to re-activate this loan anyway? (Status will be set to 'Active')"):
                        cursor.execute("UPDATE loans SET status = 'Active', closed_date = NULL WHERE id = ?", (self.loan_id,))
                        conn.commit()
                        conn.close()
                        messagebox.showinfo("Success", "Loan re-activated successfully.")
                        if self.on_change: self.on_change()
                        self.destroy()
                    else:
                        conn.close()
                    return
                
                pid, amount, aid, p_date = payment
                
                # 2. Update Loan Status
                cursor.execute("UPDATE loans SET status = 'Active', closed_date = NULL WHERE id = ?", (self.loan_id,))
                
                # 3. Revert Account Balance
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, aid))
                
                # 4. Delete Transaction
                cursor.execute("DELETE FROM transactions WHERE description LIKE ? AND amount = ? AND transaction_date = ?", 
                             (f"Loan Pre-closure: {self.customer_name}%", amount, p_date))
                
                # 5. Delete Payment
                cursor.execute("DELETE FROM payments WHERE id = ?", (pid,))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Success", "Loan re-opened and financial impact reverted.")
                if self.on_change: self.on_change()
                self.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to revoke closure: {e}")
                
        PasswordDialog(self.winfo_toplevel(), on_success=proceed_revoke)

class LogCallWindow(ctk.CTkToplevel):
    def __init__(self, master, loan_id, customer_name, **kwargs):
        super().__init__(master, **kwargs)
        self.title(f"Log Call - {customer_name}")
        self.geometry("500x450")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        if master: self.transient(master)
        self.lift()
        self.loan_id = loan_id
        
        # UI
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text=f"Call Log: {customer_name}", font=s.Styles.FONT_H3, text_color=s.TEXT).pack(pady=(0, 20))
        
        # Date and Time (Pre-filled)
        now = datetime.now()
        self.date_var = ctk.StringVar(value=now.strftime("%d-%m-%Y"))
        self.time_var = ctk.StringVar(value=now.strftime("%I:%M %p"))
        
        row1 = ctk.CTkFrame(main, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row1, text="Date:", width=60, anchor="w").pack(side="left")
        ctk.CTkEntry(row1, textvariable=self.date_var, width=120, height=35, fg_color=s.CARD, border_color=s.BORDER, corner_radius=8).pack(side="left", padx=5)
        add_focus_hover_effect(list(row1.winfo_children())[-1])
        
        ctk.CTkLabel(row1, text="Time:", width=60, anchor="w").pack(side="left", padx=(20, 0))
        ctk.CTkEntry(row1, textvariable=self.time_var, width=120, height=35, fg_color=s.CARD, border_color=s.BORDER, corner_radius=8).pack(side="left", padx=5)
        add_focus_hover_effect(list(row1.winfo_children())[-1])
        
        # Response Text
        ctk.CTkLabel(main, text="Call Response / Remarks:", anchor="w").pack(fill="x", pady=(15, 5))
        self.text_response = ctk.CTkTextbox(main, width=s.Styles.FIELD_WIDTH, height=150, corner_radius=8, 
                                            border_width=1, border_color=s.BORDER, fg_color=s.CARD, text_color=s.TEXT)
        self.text_response.pack(pady=(0, 15), anchor="w")
        add_focus_hover_effect(self.text_response)
        
        # Status
        status_frame = ctk.CTkFrame(main, fg_color="transparent")
        status_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(status_frame, text="Call Status:", width=80, anchor="w").pack(side="left")
        self.status_var = ctk.StringVar(value="Responded")
        self.status_menu = ctk.CTkOptionMenu(status_frame, values=["Responded", "Busy / Not Picked", "Switch Off", "Promise to Pay"],
                                           variable=self.status_var, height=35, fg_color=s.CARD, button_color=s.NAVY_DARK,
                                           button_hover_color=s.BORDER, corner_radius=8)
        self.status_menu.pack(side="left", fill="x", expand=True)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="Save Log", fg_color=s.GREEN, hover_color="#059669", 
                      command=self.save_log).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color=s.RED, 
                      command=self.destroy).pack(side="left", expand=True, padx=5)

    def save_log(self):
        res = self.text_response.get("1.0", "end-1c").strip()
        if not res:
            messagebox.showwarning("Incomplete", "Please enter the response details!")
            return
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO call_logs (loan_id, call_date, call_time, response_text, status)
                VALUES (?, ?, ?, ?, ?)
            """, (self.loan_id, self.date_var.get(), self.time_var.get(), res, self.status_var.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Call response recorded successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save call log: {e}")

class CallHistoryWindow(ctk.CTkToplevel):
    def __init__(self, master, loan_id, customer_name, **kwargs):
        super().__init__(master, **kwargs)
        self.title(f"Call History - {customer_name}")
        self.geometry("600x500")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        if master: self.transient(master)
        self.lift()
        
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=25, pady=25)
        
        ctk.CTkLabel(main, text=f"Call History: {customer_name}", font=s.Styles.FONT_H3, text_color=s.TEXT).pack(pady=(0, 20))
        
        self.scroll = ctk.CTkScrollableFrame(main, fg_color=s.CARD, corner_radius=s.Styles.RADIUS, border_width=1, border_color=s.BORDER)
        self.scroll.pack(fill="both", expand=True)
        
        self.load_history(loan_id)
        
        ctk.CTkButton(main, text="Close", fg_color=s.GOLD, hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD, command=self.destroy).pack(pady=(20, 0))

    def load_history(self, lid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT call_date, call_time, response_text, status FROM call_logs WHERE loan_id=? ORDER BY created_at DESC", (lid,))
            logs = cursor.fetchall()
            conn.close()
            
            if not logs:
                ctk.CTkLabel(self.scroll, text="No history found.", font=s.Styles.FONT_DEFAULT, text_color=s.MUTED).pack(pady=50)
                return
                
            for i, (date, time, res, status) in enumerate(logs):
                row = ctk.CTkFrame(self.scroll, fg_color=s.CARD if i % 2 == 0 else s.BORDER, corner_radius=8)
                row.pack(fill="x", pady=5, padx=10)
                
                header = ctk.CTkFrame(row, fg_color="transparent")
                header.pack(fill="x", padx=15, pady=(10, 5))
                
                ctk.CTkLabel(header, text=f"📅 {date} | 🕒 {time}", font=s.Styles.FONT_TINY_BOLD, text_color=s.TEXT).pack(side="left")
                
                # Status tag with color
                color = "#d97706" if status == "Responded" else "#dc2626" if status == "Switch Off" else "#059669" if status == "Promise to Pay" else s.MUTED
                ctk.CTkLabel(header, text=status.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=color).pack(side="right")
                
                # Response text
                ctk.CTkLabel(row, text=res, font=s.Styles.FONT_SMALL, wraplength=500, justify="left", anchor="w").pack(fill="x", padx=15, pady=(0, 15))
        except Exception as e:
            print(f"Error loading call history: {e}")
            ctk.CTkLabel(self.scroll, text=f"Error: {e}").pack()

class ViewCustomerWindow(ctk.CTkToplevel):
    def __init__(self, master, data):
        super().__init__(master)
        self.title("Customer Details")
        self.geometry("600x700")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        self.focus()
        
        self.grid_columnconfigure(0, weight=1)
        self.configure(fg_color=s.BG)
        
        # Header
        header = ctk.CTkLabel(self, text="Customer Information", font=s.Styles.FONT_H2, text_color=s.TEXT)
        header.pack(pady=20)
        
        container = ctk.CTkScrollableFrame(self, fg_color=s.CARD, width=550, height=580, corner_radius=s.Styles.RADIUS, 
                                           border_width=1, border_color=s.BORDER)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Photo Preview
        photo_path = data[12]
        if photo_path and os.path.exists(photo_path):
            try:
                img = Image.open(photo_path)
                # Resize keeping aspect ratio
                w, h = img.size
                ratio = min(200/w, 200/h)
                img = img.resize((int(w*ratio), int(h*ratio)), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(int(w*ratio), int(h*ratio)))
                
                lbl_img = ctk.CTkLabel(container, image=ctk_img, text="")
                lbl_img.pack(pady=10)
            except:
                pass
        
        # Details Grid
        details = [
            ("Full Name", data[1]),
            ("Father Name", data[2]),
            ("Phone", data[3]),
            ("Aadhaar", data[7]),
            ("Street", data[4]),
            ("City", data[5]),
            ("Pincode", data[6]),
            ("Gender", data[8]),
            ("Business", data[9]),
            ("Rating", data[10]),
            ("Introducer", data[11]),
            ("Docs Path", data[13] or "None")
        ]
        
        for i, (label, value) in enumerate(details):
            row = ctk.CTkFrame(container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, corner_radius=8)
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=label, font=s.Styles.FONT_SMALL, text_color=s.MUTED, width=120, anchor="w").pack(side="left", padx=15, pady=8)
            ctk.CTkLabel(row, text=value or "-", font=s.Styles.FONT_DEFAULT, text_color=s.TEXT, anchor="w").pack(side="left", padx=10, pady=8, fill="x", expand=True)
        
        # Close Button
        ctk.CTkButton(self, text="Close", command=self.destroy, fg_color=s.GOLD, hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD).pack(pady=10)

class MasterDataTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, "Vehicle Master Data Management", **kwargs)
        self.edit_make_id = None
        self.edit_model_id = None
        
        # Two-column layout for Makes and Models
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=s.PAD_SM)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=2)
        
        # --- LEFT: Makes Section ---
        self.make_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.make_container.grid(row=0, column=0, sticky="nsew", padx=s.PAD_SM)
        
        self.make_card, self.make_form = self.create_card("Manage Vehicle Makes", master=self.make_container)
        self.make_card.pack(fill="x", pady=s.PAD_SM)


        self.field_make_name = self.create_input(self.make_form, "Make Name", 0, 0)
        self.btn_save_make = ctk.CTkButton(self.make_form, text="Save Make", command=self.save_make, fg_color=s.GOLD, font=s.Styles.FONT_TINY_BOLD)
        self.btn_save_make.grid(row=1, column=0, pady=10, sticky="ew")
        
        self.make_list_container = ctk.CTkFrame(self.make_container, fg_color="transparent")
        self.make_list_container.pack(fill="both", expand=True)
        
        # --- RIGHT: Models Section ---
        self.model_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.model_container.grid(row=0, column=1, sticky="nsew", padx=s.PAD_SM)
        
        self.model_card, self.model_form = self.create_card("Manage Vehicle Models", master=self.model_container)
        self.model_card.pack(fill="x", pady=s.PAD_SM)


        
        self.field_model_make, self.model_make_var = self.create_select(self.model_form, "Select Make", [], 0, 0)
        self.field_model_name = self.create_input(self.model_form, "Model Name", 0, 1)
        
        self.btn_save_model = ctk.CTkButton(self.model_form, text="Save Model", command=self.save_model, fg_color=s.GOLD, font=s.Styles.FONT_TINY_BOLD)
        self.btn_save_model.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        
        # List Headers
        self.model_header_card = ctk.CTkFrame(self.model_container, fg_color=s.NAVY, height=40, corner_radius=8)
        self.model_header_card.pack(fill="x", pady=(10, 5))
        
        ctk.CTkLabel(self.model_header_card, text="MAKE", text_color="white", font=s.Styles.FONT_TINY_BOLD).place(relx=0.05, rely=0.5, anchor="w")
        ctk.CTkLabel(self.model_header_card, text="MODEL NAME", text_color="white", font=s.Styles.FONT_TINY_BOLD).place(relx=0.35, rely=0.5, anchor="w")
        ctk.CTkLabel(self.model_header_card, text="ACTIONS", text_color="white", font=s.Styles.FONT_TINY_BOLD).place(relx=0.75, rely=0.5, anchor="w")

        self.model_list_container = ctk.CTkFrame(self.model_container, fg_color="transparent")
        self.model_list_container.pack(fill="both", expand=True)
        
        self.load_all_data()

    def load_all_data(self):
        self.load_makes()
        self.load_models()
        self.update_make_dropdown()

    def update_make_dropdown(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM makes ORDER BY name")
            makes = [r[0] for r in cursor.fetchall()]
            conn.close()
            self.field_model_make.configure(values=makes)
        except: pass

    def save_make(self):
        name = self.field_make_name.get().strip()
        if not name: return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            if self.edit_make_id:
                cursor.execute("UPDATE makes SET name=? WHERE id=?", (name, self.edit_make_id))
            else:
                cursor.execute("INSERT INTO makes (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()
            self.field_make_name.delete(0, 'end')
            self.edit_make_id = None
            self.btn_save_make.configure(text="Save Make")
            self.load_all_data()
        except Exception as e: messagebox.showerror("Error", str(e))

    def load_makes(self):
        for w in self.make_list_container.winfo_children(): w.destroy()
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM makes ORDER BY name")
            for mid, name in cursor.fetchall():
                row = ctk.CTkFrame(self.make_list_container, fg_color=s.CARD, height=40, corner_radius=8)
                row.pack(fill="x", pady=1)
                ctk.CTkLabel(row, text=name, font=s.Styles.FONT_SMALL).pack(side="left", padx=10)
                # Small Buttons
                act_f = ctk.CTkFrame(row, fg_color="transparent")
                act_f.pack(side="right", padx=5)
                ctk.CTkButton(act_f, text="✎", width=25, height=25, command=lambda m=mid, n=name: self.edit_make(m, n)).pack(side="left", padx=2)
                ctk.CTkButton(act_f, text="✕", width=25, height=25, fg_color=s.RED, command=lambda m=mid: self.delete_make(m)).pack(side="left", padx=2)
            conn.close()
        except: pass

    def edit_make(self, mid, name):
        self.edit_make_id = mid
        self.field_make_name.delete(0, 'end')
        self.field_make_name.insert(0, name)
        self.btn_save_make.configure(text="Update Make")
        self._parent_canvas.yview_moveto(0)

    def delete_make(self, mid):
        if messagebox.askyesno("Confirm", "Delete this Make?"):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM makes WHERE id=?", (mid,))
                conn.commit()
                conn.close()
                self.load_all_data()
            except Exception as e: messagebox.showerror("Error", str(e))

    def save_model(self):
        make_name = self.field_model_make.get()
        model_name = self.field_model_name.get().strip()
        if make_name == "Select Make..." or not model_name: 
            messagebox.showerror("Error", "Select a Make and enter Model Name")
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM makes WHERE name=?", (make_name,))
            res = cursor.fetchone()
            if not res: return
            make_id = res[0]
            if self.edit_model_id:
                cursor.execute("UPDATE models SET make_id=?, name=? WHERE id=?", (make_id, model_name, self.edit_model_id))
            else:
                cursor.execute("INSERT INTO models (make_id, name) VALUES (?, ?)", (make_id, model_name))
            conn.commit()
            conn.close()
            self.field_model_name.delete(0, 'end')
            self.edit_model_id = None
            self.btn_save_model.configure(text="Save Model")
            self.load_models()
        except Exception as e: messagebox.showerror("Error", str(e))

    def load_models(self):
        for w in self.model_list_container.winfo_children(): w.destroy()
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT m.id, makes.name, m.name FROM models m JOIN makes ON m.make_id = makes.id ORDER BY makes.name, m.name")
            for i, (mid, make_name, mod_name) in enumerate(cursor.fetchall()):
                row = ctk.CTkFrame(self.model_list_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=40)
                row.pack(fill="x")
                row.pack_propagate(False)
                
                ctk.CTkLabel(row, text=make_name, font=s.Styles.FONT_SMALL).place(relx=0.05, rely=0.5, anchor="w")
                ctk.CTkLabel(row, text=mod_name, font=s.Styles.FONT_SMALL).place(relx=0.35, rely=0.5, anchor="w")
                
                act_f = ctk.CTkFrame(row, fg_color="transparent")
                act_f.place(relx=0.75, rely=0.5, anchor="w")
                ctk.CTkButton(act_f, text="Edit", width=40, height=25, command=lambda m=mid, mk=make_name, n=mod_name: self.edit_model(m, mk, n)).pack(side="left", padx=2)
                ctk.CTkButton(act_f, text="Del", width=40, height=25, fg_color=s.RED, command=lambda m=mid: self.delete_model(m)).pack(side="left", padx=2)
            conn.close()
        except: pass

    def edit_model(self, mid, make_name, mod_name):
        self.edit_model_id = mid
        self.field_model_make.set(make_name)
        self.field_model_name.delete(0, 'end')
        self.field_model_name.insert(0, mod_name)
        self.btn_save_model.configure(text="Update Model")
        self._parent_canvas.yview_moveto(0)

    def delete_model(self, mid):
        if messagebox.askyesno("Confirm", "Delete this Model?"):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM models WHERE id=?", (mid,))
                conn.commit()
                conn.close()
                self.load_models()
            except: pass

class AccountCard(ctk.CTkFrame):
    def __init__(self, master, account_data, on_deposit, on_withdraw, on_transfer, on_delete, **kwargs):
        super().__init__(master, fg_color=s.CARD, corner_radius=12, border_width=1, border_color=s.BORDER, **kwargs)
        
        self.acc_id, self.name, self.acc_type, self.balance, self.bank, self.acc_num, self.branch, _ = account_data
        
        # Header with icon
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        
        icon = "🏦" if self.acc_type == "BANK" else "💵"
        icon_lbl = ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 24))
        icon_lbl.pack(side="left")
        
        name_lbl = ctk.CTkLabel(header, text=self.name, font=s.Styles.FONT_H3, text_color=s.TEXT)
        name_lbl.pack(side="left", padx=10)
        
        if self.name != "Shop Cash":
            del_btn = ctk.CTkButton(header, text="✕", width=25, height=25, fg_color="transparent", 
                                   text_color=s.MUTED, hover_color="#fee2e2", command=lambda: on_delete(self.acc_id, self.name))
            del_btn.pack(side="right")
        
        # Details
        details_str = f"{self.acc_type}"
        if self.acc_type == "BANK" and self.bank:
            details_str += f" | {self.bank}"
        
        ctk.CTkLabel(self, text=details_str, font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=15)
        
        # Balance
        bal_frame = ctk.CTkFrame(self, fg_color="#f8fafc", corner_radius=8)
        bal_frame.pack(fill="x", padx=15, pady=15)
        
        bal_lbl = ctk.CTkLabel(bal_frame, text=f"Rs. {self.balance:,.2f}", font=(s.Styles.FAMILY, 22, "bold"), text_color=s.NAVY)
        bal_lbl.pack(pady=10)
        
        # Actions
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=15, pady=(0, 15))
        
        actions.grid_columnconfigure((0, 1, 2), weight=1, uniform="buttons")
        
        ctk.CTkButton(actions, text="Deposit", height=32, fg_color=s.GREEN, hover_color="#059669", 
                      font=s.Styles.FONT_TINY_BOLD, command=lambda: on_deposit(self.acc_id, self.name)).grid(row=0, column=0, padx=(0, 2), sticky="ew")
        
        ctk.CTkButton(actions, text="Withdraw", height=32, fg_color=s.RED, hover_color="#e11d48", 
                      font=s.Styles.FONT_TINY_BOLD, command=lambda: on_withdraw(self.acc_id, self.name)).grid(row=0, column=1, padx=2, sticky="ew")
        
        ctk.CTkButton(actions, text="Transfer", height=32, fg_color=s.BLUE, hover_color="#2563eb", 
                      font=s.Styles.FONT_TINY_BOLD, command=lambda: on_transfer(self.acc_id, self.name)).grid(row=0, column=2, padx=(2, 0), sticky="ew")

class AccountDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save):
        super().__init__(master)
        self.title(t("add_account"))
        self.geometry("400x550")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        self.on_save = on_save
        
        self.configure(fg_color=s.BG)
        
        ctk.CTkLabel(self, text=t("add_account"), font=s.Styles.FONT_H2, text_color=s.NAVY).pack(pady=20)
        
        container = ctk.CTkFrame(self, fg_color=s.CARD, corner_radius=12, border_width=1, border_color=s.BORDER)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Type Selection
        ctk.CTkLabel(container, text=t("account_type"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(20, 0))
        self.type_var = ctk.StringVar(value="CASH")
        type_frame = ctk.CTkFrame(container, fg_color="transparent")
        type_frame.pack(fill="x", padx=20)
        ctk.CTkRadioButton(type_frame, text=t("cash"), variable=self.type_var, value="CASH", command=self.toggle_fields).pack(side="left", pady=5)
        ctk.CTkRadioButton(type_frame, text=t("bank"), variable=self.type_var, value="BANK", command=self.toggle_fields).pack(side="left", padx=20, pady=5)
        
        # Name
        ctk.CTkLabel(container, text=t("account_name"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_name = ctk.CTkEntry(container, height=40, placeholder_text=t("account_name"))
        self.entry_name.pack(fill="x", padx=20, pady=2)
        
        # Initial Balance
        ctk.CTkLabel(container, text=t("initial_balance") + " (₹)", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_balance = ctk.CTkEntry(container, height=40, placeholder_text="0.00")
        self.entry_balance.pack(fill="x", padx=20, pady=2)
        
        # Bank Details (Conditional) - Using t() for labels is enough, the code logic stays same
        self.bank_frame = ctk.CTkFrame(container, fg_color="transparent")
        
        ctk.CTkLabel(self.bank_frame, text=t("bank"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=0, pady=(10, 0))
        self.entry_bank = ctk.CTkEntry(self.bank_frame, height=35)
        self.entry_bank.pack(fill="x", pady=2)
        
        ctk.CTkLabel(self.bank_frame, text=t("registration_no"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=0, pady=(10, 0))
        self.entry_acc_num = ctk.CTkEntry(self.bank_frame, height=35)
        self.entry_acc_num.pack(fill="x", pady=2)
        
        ctk.CTkLabel(self.bank_frame, text=t("city"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=0, pady=(10, 0))
        self.entry_branch = ctk.CTkEntry(self.bank_frame, height=35)
        self.entry_branch.pack(fill="x", pady=2)
        
        # Actions
        btn_save = ctk.CTkButton(container, text=t("save"), height=45, fg_color=s.GOLD, hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD, command=self.handle_save)
        btn_save.pack(fill="x", padx=20, pady=30)

    def toggle_fields(self):
        if self.type_var.get() == "BANK":
            self.bank_frame.pack(fill="x", padx=20)
        else:
            self.bank_frame.pack_forget()

    def handle_save(self):
        try:
            name = self.entry_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Account name is required!")
                return
            
            data = {
                "name": name,
                "type": self.type_var.get(),
                "balance": float(self.entry_balance.get() or 0),
                "bank_name": self.entry_bank.get() if self.type_var.get() == "BANK" else None,
                "account_number": self.entry_acc_num.get() if self.type_var.get() == "BANK" else None,
                "branch_name": self.entry_branch.get() if self.type_var.get() == "BANK" else None
            }
            self.on_save(data)
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid balance!")

class TransactionDialog(ctk.CTkToplevel):
    def __init__(self, master, trans_type, source_acc_id, source_acc_name, on_save):
        super().__init__(master)
        # Translate types for title
        type_tr = t("deposit") if trans_type == "DEPOSIT" else t("withdraw") if trans_type == "WITHDRAW" else t("transfer")
        self.title(f"{type_tr} - {source_acc_name}")
        self.geometry("400x500")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        self.trans_type = trans_type
        self.source_acc_id = source_acc_id
        self.on_save = on_save
        self.targets = {}
        
        self.configure(fg_color=s.BG)
        
        ctk.CTkLabel(self, text=f"{type_tr} {t('from_account')} {source_acc_name}", font=s.Styles.FONT_H3, text_color=s.NAVY).pack(pady=20)
        
        container = ctk.CTkFrame(self, fg_color=s.CARD, corner_radius=12, border_width=1, border_color=s.BORDER)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Target Account (for transfers)
        if trans_type == "TRANSFER":
            ctk.CTkLabel(container, text=t("to_account"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(20, 0))
            self.target_acc_var = ctk.StringVar(value=t("select") + "...")
            self.target_dropdown = ctk.CTkOptionMenu(container, height=40, variable=self.target_acc_var,
                                                   fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT, 
                                                   button_color=s.COMBO_BG)
            self.target_dropdown.pack(fill="x", padx=20, pady=2)
            add_combo_hover_effect(self.target_dropdown)
        
        # Amount
        ctk.CTkLabel(container, text=t("amount") + " (₹)", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_amount = ctk.CTkEntry(container, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, placeholder_text="0.00")
        self.entry_amount.pack(padx=20, pady=2, anchor="w")
        
        # Description
        ctk.CTkLabel(container, text=t("description"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_desc = ctk.CTkEntry(container, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, placeholder_text="...")
        self.entry_desc.pack(padx=20, pady=2, anchor="w")
        
        # Actions
        btn_confirm = ctk.CTkButton(container, text=f"{t('confirm')} {type_tr}", height=45, 
                                   fg_color=s.GREEN if trans_type == "DEPOSIT" else s.RED if trans_type == "WITHDRAW" else s.BLUE,
                                   hover_color="#059669" if trans_type == "DEPOSIT" else "#e11d48" if trans_type == "WITHDRAW" else "#2563eb",
                                   font=s.Styles.FONT_BOLD, command=self.handle_confirm)
        btn_confirm.pack(fill="x", padx=20, pady=30)

    def load_target_accounts(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM accounts WHERE id != ?", (self.source_acc_id,))
            self.targets = {f"{r[1]}": r[0] for r in cursor.fetchall()}
            conn.close()
            self.target_dropdown.configure(values=list(self.targets.keys()))
        except: pass

    def handle_confirm(self):
        try:
            amount_str = self.entry_amount.get()
            if not amount_str:
                messagebox.showerror("Error", "Amount is required!")
                return
            amount = float(amount_str)
            if amount <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid amount!")
            return
            
        # Record lock check
        date_today = datetime.now().strftime("%d-%m-%Y")
        if cl.is_date_closed(date_today):
            messagebox.showerror("Error", f"Today's date ({date_today}) has already been closed. No new transactions can be recorded.")
            return

        data = {
            "type": self.trans_type,
            "source_id": self.source_acc_id,
            "amount": amount,
            "desc": self.entry_desc.get().strip(),
            "target_id": self.targets.get(self.target_acc_var.get()) if self.trans_type == "TRANSFER" else None
        }
        
        if self.trans_type == "TRANSFER" and not data["target_id"]:
            messagebox.showerror("Error", "Please select a target account!")
            return
            
        self.on_save(data)
        self.destroy()

class BorrowingDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save, edit_data=None):
        super().__init__(master)
        self.title(t("edit_borrowing") if edit_data else t("add_borrowed_fund"))
        self.geometry("450x600")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        self.on_save = on_save
        self.edit_data = edit_data
        self.accounts = {}
        
        self.configure(fg_color=s.BG)
        
        ctk.CTkLabel(self, text=t("borrowing_details"), font=s.Styles.FONT_H2, text_color=s.NAVY).pack(pady=20)
        
        container = ctk.CTkFrame(self, fg_color=s.CARD, corner_radius=12, border_width=1, border_color=s.BORDER)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Lender Name
        ctk.CTkLabel(container, text=t("lender_name"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(20, 0))
        self.entry_lender = ctk.CTkEntry(container, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, placeholder_text=t("name"), fg_color=s.CARD)
        self.entry_lender.pack(padx=20, pady=2, anchor="w")
        add_focus_hover_effect(self.entry_lender)
        
        # Amount
        ctk.CTkLabel(container, text=t("borrowed_amount") + " (₹)", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_amount = ctk.CTkEntry(container, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, placeholder_text="0.00", fg_color=s.CARD)
        self.entry_amount.pack(padx=20, pady=2, anchor="w")
        add_focus_hover_effect(self.entry_amount)
        
        # Interest Rate
        ctk.CTkLabel(container, text=t("interest_rate_pm"), font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_rate = ctk.CTkEntry(container, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, placeholder_text="e.g. 2.0", fg_color=s.CARD)
        self.entry_rate.pack(padx=20, pady=2, anchor="w")
        add_focus_hover_effect(self.entry_rate)
        
        # Borrow Date
        ctk.CTkLabel(container, text="Date", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        default_d = datetime.now()
        if edit_data:
            try:
                d_str = edit_data[4]
                if '-' in d_str:
                    parts = d_str.split('-')
                    if len(parts[0]) == 4: default_d = datetime.strptime(d_str, "%Y-%m-%d")
                    else: default_d = datetime.strptime(d_str, "%d-%m-%Y")
            except: pass
            
        self.field_date = DatePickerWidget(container, default_date=default_d)
        self.field_date.pack(fill="x", padx=20, pady=2)
        
        # Target Account
        ctk.CTkLabel(container, text="Credit To Account", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.acc_var = ctk.StringVar(value="Select Account...")
        self.acc_dropdown = ctk.CTkOptionMenu(container, height=40, 
                                              fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT, 
                                              button_color=s.COMBO_BG,
                                              variable=self.acc_var)
        self.acc_dropdown.pack(fill="x", padx=20, pady=2)
        add_combo_hover_effect(self.acc_dropdown)
        self.load_accounts()
        
        # Remarks
        ctk.CTkLabel(container, text="Remarks", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_remarks = ctk.CTkEntry(container, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, placeholder_text="Optional notes", fg_color=s.CARD)
        self.entry_remarks.pack(padx=20, pady=2, anchor="w")
        add_focus_hover_effect(self.entry_remarks)
        
        # Pre-fill data if editing
        if edit_data:
            self.entry_lender.insert(0, edit_data[1])
            self.entry_amount.insert(0, str(edit_data[2]))
            self.entry_rate.insert(0, str(edit_data[3]))
            self.entry_remarks.insert(0, edit_data[7] or "")
            
        # Actions
        btn_save = ctk.CTkButton(container, text="Update Borrowing" if edit_data else "Record Borrowing", 
                                height=45, fg_color=s.GOLD, hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD, 
                                command=self.handle_save)
        btn_save.pack(fill="x", padx=20, pady=30)

    def load_accounts(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM accounts")
            self.accounts = {r[1]: r[0] for r in cursor.fetchall()}
            conn.close()
            self.acc_dropdown.configure(values=list(self.accounts.keys()))
            
            # If editing, set the current account
            if self.edit_data:
                target_id = self.edit_data[5]
                for name, aid in self.accounts.items():
                    if aid == target_id:
                        self.acc_var.set(name)
                        break
        except: pass

    def handle_save(self):
        try:
            lender = self.entry_lender.get().strip()
            amount_str = self.entry_amount.get().strip()
            rate_str = self.entry_rate.get().strip()
            acc_name = self.acc_var.get()
            
            if not lender or not amount_str or not rate_str or acc_name == "Select Account...":
                messagebox.showerror("Error", "All fields are required!")
                return
            
            data = {
                "lender_name": lender,
                "amount": float(amount_str),
                "interest_rate": float(rate_str),
                "borrow_date": self.field_date.get(),
                "account_id": self.accounts.get(acc_name),
                "account_name": acc_name,
                "remarks": self.entry_remarks.get().strip()
            }
            
            if self.edit_data:
                self.on_save(data, self.edit_data)
            else:
                self.on_save(data)
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for amount and rate!")

class BorrowingCard(ctk.CTkFrame):
    def __init__(self, master, data, on_pay, on_edit, on_delete, **kwargs):
        super().__init__(master, fg_color=s.CARD, corner_radius=12, border_width=1, border_color=s.BORDER, **kwargs)
        
        bid, lender, amount, rate, date, acc_id, status, remarks, _ = data
        self.bid = bid
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(header, text="🤝", font=("Segoe UI Emoji", 20)).pack(side="left")
        ctk.CTkLabel(header, text=lender, font=s.Styles.FONT_BOLD, text_color=s.TEXT).pack(side="left", padx=10)
        
        del_btn = ctk.CTkButton(header, text="✕", width=25, height=25, fg_color="transparent", 
                               text_color=s.MUTED, hover_color="#fee2e2", command=lambda: on_delete(bid, lender))
        del_btn.pack(side="right")

        edit_btn = ctk.CTkButton(header, text="✎", width=25, height=25, fg_color="transparent", 
                               text_color=s.MUTED, hover_color=s.BORDER, command=lambda: on_edit(data))
        edit_btn.pack(side="right", padx=5)
        
        # Details
        ctk.CTkLabel(self, text=f"Rate: {rate}%/month | Date: {date}", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=15)
        
        # Principal Remaining
        bal_frame = ctk.CTkFrame(self, fg_color="#fff7ed", corner_radius=8)
        bal_frame.pack(fill="x", padx=15, pady=10)
        
        # Calculate stats (from borrowing_payments)
        remaining, interest_paid, payable_i = self.get_payment_stats(bid, amount, rate, date)
        
        ctk.CTkLabel(bal_frame, text=f"Capital: ₹{remaining:,.2f}", font=s.Styles.FONT_SMALL, text_color="#9a3412").pack(pady=(5, 0))
        ctk.CTkLabel(bal_frame, text=f"Interest Paid: ₹{interest_paid:,.2f}", font=s.Styles.FONT_TINY, text_color="#059669").pack(pady=0)
        ctk.CTkLabel(bal_frame, text=f"Payable Interest: ₹{payable_i:,.2f}", font=s.Styles.FONT_TINY_BOLD, text_color="#dc2626").pack(pady=(0, 5))
        
        # Actions
        btn_pay = ctk.CTkButton(self, text="Record Payment", height=32, fg_color=s.NAVY, hover_color=s.NAVY_DARK, 
                               font=s.Styles.FONT_TINY, command=lambda: on_pay(data, remaining))
        btn_pay.pack(fill="x", padx=15, pady=(0, 15))

    def get_payment_stats(self, bid, initial_p, rate, borrow_date_str):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT payment_date, amount, payment_type FROM borrowing_payments WHERE borrowing_id = ? ORDER BY payment_date ASC", (bid,))
            payments = cursor.fetchall()
            conn.close()
            
            # Helper for date parsing
            def parse_dt(d_str):
                try:
                    if '-' in d_str:
                        parts = d_str.split('-')
                        if len(parts[0]) == 4: return datetime.strptime(d_str, "%Y-%m-%d")
                        return datetime.strptime(d_str, "%d-%m-%Y")
                    return datetime.now()
                except: return datetime.now()

            last_dt = parse_dt(borrow_date_str)
            today = datetime.now()
            
            total_accrued = 0.0
            current_p = initial_p
            paid_p = 0.0
            paid_i = 0.0
            
            for p_date_str, p_amt, p_type in payments:
                if p_type == 'INTEREST':
                    paid_i += p_amt
                    continue
                
                # Principal payment change interest calculation period
                p_dt = parse_dt(p_date_str)
                diff_days = (p_dt - last_dt).days
                months = diff_days / 30.0
                total_accrued += current_p * (rate / 100.0) * months
                
                current_p -= p_amt
                paid_p += p_amt
                last_dt = p_dt
                
            # Period until today
            diff_days = (today - last_dt).days
            months = diff_days / 30.0
            total_accrued += current_p * (rate / 100.0) * months
            
            payable_i = max(0, total_accrued - paid_i)
            return max(0, initial_p - paid_p), paid_i, payable_i
        except: return initial_p, 0, 0

class BorrowingPaymentDialog(ctk.CTkToplevel):
    def __init__(self, master, borrowing_data, remaining_principal, on_save):
        super().__init__(master)
        bid, lender, amount, rate, date, acc_id, status, remarks, _ = borrowing_data
        self.title(f"Payment to {lender}")
        self.geometry("400x500")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        self.on_save = on_save
        self.bid = bid
        self.accounts = {}
        
        self.configure(fg_color=s.BG)
        
        ctk.CTkLabel(self, text=f"Record Payment: {lender}", font=s.Styles.FONT_H3, text_color=s.NAVY).pack(pady=20)
        
        container = ctk.CTkFrame(self, fg_color=s.CARD, corner_radius=12, border_width=1, border_color=s.BORDER)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Payment Type
        ctk.CTkLabel(container, text="Payment Type", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(20, 0))
        self.type_var = ctk.StringVar(value="INTEREST")
        type_frame = ctk.CTkFrame(container, fg_color="transparent")
        type_frame.pack(fill="x", padx=20)
        ctk.CTkRadioButton(type_frame, text="Interest", variable=self.type_var, value="INTEREST").pack(side="left", pady=5)
        ctk.CTkRadioButton(type_frame, text="Principal", variable=self.type_var, value="PRINCIPAL").pack(side="left", padx=20, pady=5)
        
        # Amount
        ctk.CTkLabel(container, text="Payment Amount (₹)", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.entry_amount = ctk.CTkEntry(container, height=40, placeholder_text="0.00", fg_color=s.CARD)
        self.entry_amount.pack(fill="x", padx=20, pady=2)
        add_focus_hover_effect(self.entry_amount)
        
        # Source Account
        ctk.CTkLabel(container, text="Paid From Account", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.acc_var = ctk.StringVar(value="Select Account...")
        self.acc_dropdown = ctk.CTkOptionMenu(container, height=40, 
                                              fg_color=s.COMBO_BG, text_color=s.COMBO_TEXT, 
                                              button_color=s.COMBO_BG,
                                              variable=self.acc_var)
        self.acc_dropdown.pack(fill="x", padx=20, pady=2)
        add_combo_hover_effect(self.acc_dropdown)
        self.load_accounts()
        
        # Date
        ctk.CTkLabel(container, text="Payment Date", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w", padx=20, pady=(15, 0))
        self.field_date = DatePickerWidget(container, default_date=datetime.now())
        self.field_date.pack(fill="x", padx=20, pady=2)
        
        # Actions
        btn_save = ctk.CTkButton(container, text="Confirm Payment", height=45, fg_color=s.RED, hover_color="#e11d48", font=s.Styles.FONT_BOLD, command=self.handle_save)
        btn_save.pack(fill="x", padx=20, pady=30)

    def load_accounts(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM accounts")
            self.accounts = {r[1]: r[0] for r in cursor.fetchall()}
            conn.close()
            self.acc_dropdown.configure(values=list(self.accounts.keys()))
        except: pass

    def handle_save(self):
        try:
            amount_str = self.entry_amount.get().strip()
            acc_name = self.acc_var.get()
            
            if not amount_str or acc_name == "Select Account...":
                messagebox.showerror("Error", "Amount and Account are required!")
                return
            
            data = {
                "borrowing_id": self.bid,
                "amount": float(amount_str),
                "payment_type": self.type_var.get(),
                "payment_date": self.field_date.get(),
                "account_id": self.accounts.get(acc_name),
                "account_name": acc_name
            }
            self.on_save(data)
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid numeric value for amount!")

class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, on_success, title=None):
        super().__init__(master)
        self.title(title or t("admin_password_required"))
        self.geometry("350x250")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        self.on_success = on_success
        
        self.configure(fg_color=s.BG)
        
        ctk.CTkLabel(self, text="🔒", font=("Segoe UI Emoji", 40)).pack(pady=(20, 10))
        ctk.CTkLabel(self, text=t("enter_admin_password"), font=s.Styles.FONT_BOLD, text_color=s.NAVY).pack()
        
        self.entry_pass = ctk.CTkEntry(self, width=s.Styles.FIELD_WIDTH, height=s.Styles.FIELD_HEIGHT, placeholder_text=t("password"), show="*")
        self.entry_pass.pack(pady=(5, 20))
        self.entry_pass.focus_set()
        
        btn_confirm = ctk.CTkButton(self, text=t("verify_proceed"), height=40, width=250, 
                                   fg_color=s.NAVY, hover_color=s.NAVY_DARK, font=s.Styles.FONT_BOLD,
                                   command=self.handle_verify)
        btn_confirm.pack()
        
        # Bind Enter key
        self.bind("<Return>", lambda e: self.handle_verify())

    def handle_verify(self):
        password = self.entry_pass.get()
        if not password: return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = 'admin'")
            res = cursor.fetchone()
            conn.close()
            
            if res and res[0] == password:
                self.on_success()
                self.destroy()
            else:
                messagebox.showerror("Access Denied", "Incorrect administrator password!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not verify password: {e}")

class CashBankTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("cash_bank_management"), **kwargs)
        
        # --- Stats/Overview Card ---
        self.stats_card, self.stats_f = self.create_card("Account Overview")
        self.acc_grid = ctk.CTkFrame(self.stats_f, fg_color="transparent")
        self.acc_grid.grid(row=1, column=0, sticky="ew", pady=10)
        self.stats_f.grid_columnconfigure(0, weight=1)
        
        self.add_acc_btn = ctk.CTkButton(self.stats_f, text="+ Add New Account", height=35, fg_color=s.NAVY, 
                                          hover_color=s.BORDER, font=s.Styles.FONT_BOLD, command=self.open_add_account)
        self.add_acc_btn.grid(row=2, column=0, sticky="w", pady=10)




        # --- Borrowing Section ---
        self.borrow_header = ctk.CTkLabel(self, text="Borrowings (Lenders)", font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.borrow_header.pack(pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG, anchor="w")
        
        self.borrow_card, self.borrow_inner = self.create_card("Active Borrowings")
        self.borrow_grid = ctk.CTkFrame(self.borrow_inner, fg_color="transparent")
        self.borrow_grid.grid(row=1, column=0, sticky="ew", pady=10)
        
        self.add_borrow_btn = ctk.CTkButton(self.borrow_inner, text="+ Record New Borrowing", height=35, fg_color=s.GOLD, 
                                             hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD, command=self.open_add_borrowing)
        self.add_borrow_btn.grid(row=2, column=0, sticky="w", pady=10)


        # Header Definition (do this early!)
        self.trans_cols = [
            ("DATE/TIME", 0.15),
            ("ACCOUNT", 0.20),
            ("TYPE", 0.15),
            ("DESCRIPTION", 0.35),
            ("AMOUNT", 0.15)
        ]

        # --- Recent Transactions Card ---
        self.trans_card, self.trans_f = self.create_card("Recent Transactions")
        self.trans_f.grid_columnconfigure(0, weight=1)
        
        # Add Export Button to card header area
        self.btn_export = ctk.CTkButton(self.trans_f, text="📄 View / Print All", width=120, height=28, 
                                        fg_color=s.NAVY, hover_color=s.BORDER, font=s.Styles.FONT_TINY_BOLD, 
                                        command=self.export_transactions)
        self.btn_export.place(relx=1.0, rely=0.0, anchor="ne", y=0, x=-5)
        
        # Table Header
        self.trans_header_card = ctk.CTkFrame(self.trans_f, fg_color=s.NAVY, height=35, corner_radius=6)
        self.trans_header_card.grid(row=1, column=0, sticky="ew", padx=s.PAD_SM, pady=(0, 5))
        self.trans_header_card.pack_propagate(False)
        
        curr_x = 0.0
        for text, weight in self.trans_cols:
            lbl = ctk.CTkLabel(self.trans_header_card, text=text, font=s.Styles.FONT_TINY_BOLD, text_color=s.WHITE)
            lbl.place(relx=curr_x, rely=0.5, anchor="w", x=15)
            curr_x += weight

        self.trans_container = ctk.CTkFrame(self.trans_f, fg_color="transparent")
        self.trans_container.grid(row=2, column=0, sticky="ew")

        self.refresh_ui()

    def refresh_ui(self):
        self.load_accounts()
        self.load_transactions()
        self.load_borrowings()

    def load_accounts(self):
        for w in self.acc_grid.winfo_children(): w.destroy()
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY type")
            accounts = cursor.fetchall()
            conn.close()
            
            # Use responsive grid: 3 per row
            for i, acc in enumerate(accounts):
                card = AccountCard(self.acc_grid, acc, 
                                  on_deposit=self.open_deposit, 
                                  on_withdraw=self.open_withdraw, 
                                  on_transfer=self.open_transfer,
                                  on_delete=self.delete_account)
                card.grid(row=i // 3, column=i % 3, padx=10, pady=10, sticky="nsew")
            
            # Ensure all 3 columns share space equally even if there are fewer than 3 accounts
            for i in range(3):
                self.acc_grid.grid_columnconfigure(i, weight=1)
        except Exception as e: print(f"Error loading accounts: {e}")

    def load_transactions(self):
        for w in self.trans_container.winfo_children(): w.destroy()
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.transaction_date, a.name, t.transaction_type, t.description, t.amount 
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                ORDER BY t.transaction_date DESC LIMIT 20
            """)
            transactions = cursor.fetchall()
            conn.close()
            
            for i, (date, acc_name, t_type, desc, amount) in enumerate(transactions):
                row = ctk.CTkFrame(self.trans_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=0)
                row.pack(fill="x")
                row.pack_propagate(False)
                
                # Format Date
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                    date_str = dt.strftime("%d/%m %I:%M%p")
                except:
                    date_str = str(date)
                
                # Color based on type
                color = s.GREEN if t_type in ("DEPOSIT", "TRANSFER_IN", "INCOME") else s.RED
                
                curr_x = 0.0
                row_data = [
                    (date_str, s.Styles.FONT_TINY, s.MUTED),
                    (acc_name, s.Styles.FONT_SMALL, s.TEXT),
                    (t_type, s.Styles.FONT_TINY_BOLD, color),
                    (desc or "-", s.Styles.FONT_TINY, s.MUTED),
                    (f"₹{amount:,.2f}", s.Styles.FONT_SMALL_BOLD, color)
                ]
                
                for j, (text, font, t_color) in enumerate(row_data):
                    w = self.trans_cols[j][1]
                    ctk.CTkLabel(row, text=text, font=font, text_color=t_color).place(relx=curr_x, rely=0.5, anchor="w", x=15)
                    curr_x += w

                
        except Exception as e: print(f"Error loading transactions: {e}")

    def export_transactions(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.transaction_date, a.name, t.transaction_type, t.description, t.amount 
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                ORDER BY t.transaction_date DESC LIMIT 100
            """)
            transactions = cursor.fetchall()
            conn.close()
            
            rows_html = ""
            for i, (date, acc_name, t_type, desc, amount) in enumerate(transactions):
                color = "green" if t_type in ("DEPOSIT", "TRANSFER_IN", "INCOME") else "red"
                rows_html += f"""
                <tr style="background-color: {'#ffffff' if i%2==0 else '#f8fafc'}">
                    <td>{date}</td>
                    <td>{acc_name}</td>
                    <td style="color: {color}; font-weight: bold;">{t_type}</td>
                    <td>{desc or '-'}</td>
                    <td style="color: {color}; font-weight: bold; text-align: right;">₹{amount:,.2f}</td>
                </tr>
                """
                
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #1e293b; }}
                    h1 {{ color: #4f46e5; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th {{ background-color: #1e293b; color: white; text-align: left; padding: 12px; font-size: 14px; }}
                    td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #64748b; text-align: center; }}
                </style>
            </head>
            <body>
                <h1>Recent Transaction History</h1>
                <p>Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}</p>
                <table>
                    <thead>
                        <tr>
                            <th>DATE / TIME</th>
                            <th>ACCOUNT</th>
                            <th>TYPE</th>
                            <th>DESCRIPTION</th>
                            <th style="text-align: right;">AMOUNT</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                <div class="footer">{get_company_name()} Management System</div>
            </body>
            </html>
            """
            
            import tempfile
            import webbrowser
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                webbrowser.open(f'file://{f.name}')
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export transactions: {e}")

    def open_add_account(self):
        AccountDialog(self.winfo_toplevel(), on_save=self.save_account)

    def save_account(self, data):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (name, type, balance, bank_name, account_number, branch_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data["name"], data["type"], data["balance"], data["bank_name"], data["account_number"], data["branch_name"]))
            
            # If initial balance > 0, create a transaction record
            if data["balance"] > 0:
                acc_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO transactions (account_id, transaction_type, amount, description)
                    VALUES (?, 'DEPOSIT', ?, 'Initial Balance')
                """, (acc_id, data["balance"]))
                
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Account '{data['name']}' created successfully!")
            self.refresh_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save account: {e}")

    def delete_account(self, acc_id, name):
        def proceed_delete():
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?\nThis will also delete its full transaction history."):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM transactions WHERE account_id = ?", (acc_id,))
                    cursor.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
                    conn.commit()
                    conn.close()
                    self.refresh_ui()
                except Exception as e: messagebox.showerror("Error", str(e))
        
        PasswordDialog(self.winfo_toplevel(), on_success=proceed_delete)

    # --- Borrowing Logic ---
    def load_borrowings(self):
        for w in self.borrow_grid.winfo_children(): w.destroy()
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM borrowings WHERE status = 'Active' ORDER BY borrow_date DESC")
            borrowings = cursor.fetchall()
            conn.close()
            
            for i, b in enumerate(borrowings):
                card = BorrowingCard(self.borrow_grid, b, 
                                    on_pay=self.open_borrowing_payment,
                                    on_edit=self.open_edit_borrowing,
                                    on_delete=self.delete_borrowing)
                card.grid(row=i // 3, column=i % 3, padx=10, pady=10, sticky="nsew")
                self.borrow_grid.grid_columnconfigure(i % 3, weight=1)
        except Exception as e: print(f"Error loading borrowings: {e}")

    def open_add_borrowing(self):
        BorrowingDialog(self.winfo_toplevel(), on_save=self.save_borrowing)

    def save_borrowing(self, data):
        if cl.is_date_closed(data["borrow_date"]):
            messagebox.showerror("Error", f"The date {data['borrow_date']} has already been closed. No new borrowings can be recorded for this date.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 1. Add Borrowing Record
            cursor.execute("""
                INSERT INTO borrowings (lender_name, amount, interest_rate, borrow_date, account_id, remarks)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data["lender_name"], data["amount"], data["interest_rate"], data["borrow_date"], data["account_id"], data["remarks"]))
            
            # 2. Update Account Balance
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (data["amount"], data["account_id"]))
            
            # 3. Record Transaction
            cursor.execute("""
                INSERT INTO transactions (account_id, transaction_type, amount, description)
                VALUES (?, 'DEPOSIT', ?, ?)
            """, (data["account_id"], data["amount"], f"Borrowing from {data['lender_name']}"))
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Borrowing of ₹{data['amount']:,.2f} recorded and credited to {data['account_name']}!")
            self.refresh_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record borrowing: {e}")

    def open_edit_borrowing(self, data):
        BorrowingDialog(self.winfo_toplevel(), on_save=self.save_edited_borrowing, edit_data=data)

    def save_edited_borrowing(self, data, old_data):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            bid = old_data[0]
            old_amount = old_data[2]
            old_acc_id = old_data[5]
            
            # 1. Update Borrowing Record
            cursor.execute("""
                UPDATE borrowings 
                SET lender_name = ?, amount = ?, interest_rate = ?, borrow_date = ?, account_id = ?, remarks = ?
                WHERE id = ?
            """, (data["lender_name"], data["amount"], data["interest_rate"], data["borrow_date"], data["account_id"], data["remarks"], bid))
            
            # 2. Handle Account Balance Changes if amount or account changed
            if old_acc_id == data["account_id"]:
                # Same account, just adjust by difference
                diff = data["amount"] - old_amount
                if diff > 0:
                    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (diff, old_acc_id))
                    cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, 'DEPOSIT', ?, ?)", 
                                 (old_acc_id, diff, f"Borrowing Edit: Adjustment (+) for {data['lender_name']}"))
                elif diff < 0:
                    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (abs(diff), old_acc_id))
                    cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, 'WITHDRAWAL', ?, ?)", 
                                 (old_acc_id, abs(diff), f"Borrowing Edit: Adjustment (-) for {data['lender_name']}"))
            else:
                # Different account: Revert old, Apply new
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (old_amount, old_acc_id))
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (data["amount"], data["account_id"]))
                # Log transactions
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, 'WITHDRAWAL', ?, ?)", 
                             (old_acc_id, old_amount, f"Borrowing Edit: Reverting old credit to {old_data[1]}"))
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, 'DEPOSIT', ?, ?)", 
                             (data["account_id"], data["amount"], f"Borrowing Edit: New credit for {data['lender_name']}"))
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Borrowing updated successfully!")
            self.refresh_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update borrowing: {e}")

    def open_borrowing_payment(self, b_data, remaining):
        BorrowingPaymentDialog(self.winfo_toplevel(), b_data, remaining, on_save=self.save_borrowing_payment)

    def save_borrowing_payment(self, data):
        if cl.is_date_closed(data["payment_date"]):
            messagebox.showerror("Error", f"The date {data['payment_date']} has already been closed. No new payments can be recorded for this date.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check availability
            cursor.execute("SELECT balance FROM accounts WHERE id = ?", (data["account_id"],))
            bal = cursor.fetchone()[0]
            if bal < data["amount"]:
                messagebox.showerror("Insufficient Funds", "Not enough balance in account!")
                conn.close()
                return

            # 1. Record Payment
            cursor.execute("""
                INSERT INTO borrowing_payments (borrowing_id, payment_date, amount, payment_type, account_id)
                VALUES (?, ?, ?, ?, ?)
            """, (data["borrowing_id"], data["payment_date"], data["amount"], data["payment_type"], data["account_id"]))
            
            # 2. Update Account
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (data["amount"], data["account_id"]))
            
            # 3. Record Transaction
            desc = f"Borrowing {data['payment_type'].title()} Payment"
            cursor.execute("""
                INSERT INTO transactions (account_id, transaction_type, amount, description)
                VALUES (?, 'WITHDRAWAL', ?, ?)
            """, (data["account_id"], data["amount"], desc))
            
            # 4. Check if borrowing is fully paid (Principal)
            if data["payment_type"] == "PRINCIPAL":
                cursor.execute("SELECT amount FROM borrowings WHERE id = ?", (data["borrowing_id"],))
                total_p = cursor.fetchone()[0]
                cursor.execute("SELECT SUM(amount) FROM borrowing_payments WHERE borrowing_id = ? AND payment_type = 'PRINCIPAL'", (data["borrowing_id"],))
                paid_p = cursor.fetchone()[0] or 0
                
                if paid_p >= total_p:
                    cursor.execute("UPDATE borrowings SET status = 'Paid' WHERE id = ?", (data["borrowing_id"],))
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Borrowing payment recorded successfully!")
            self.refresh_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record payment: {e}")

    def delete_borrowing(self, bid, name):
        def proceed_delete():
            if messagebox.askyesno("Confirm", f"Delete borrowing record from '{name}'?\nNote: This will NOT revert account balances. It only removes the record from this list."):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM borrowing_payments WHERE borrowing_id = ?", (bid,))
                    cursor.execute("DELETE FROM borrowings WHERE id = ?", (bid,))
                    conn.commit()
                    conn.close()
                    self.refresh_ui()
                except Exception as e: messagebox.showerror("Error", str(e))
        
        PasswordDialog(self.winfo_toplevel(), on_success=proceed_delete)

    # --- Transaction Logic ---
    def open_deposit(self, acc_id, name):
        TransactionDialog(self.winfo_toplevel(), "DEPOSIT", acc_id, name, on_save=self.process_transaction)
        
    def open_withdraw(self, acc_id, name):
        TransactionDialog(self.winfo_toplevel(), "WITHDRAW", acc_id, name, on_save=self.process_transaction)
        
    def open_transfer(self, acc_id, name):
        TransactionDialog(self.winfo_toplevel(), "TRANSFER", acc_id, name, on_save=self.process_transaction)

    def process_transaction(self, data):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check availability for withdraw/transfer
            if data["type"] in ("WITHDRAW", "TRANSFER"):
                cursor.execute("SELECT balance FROM accounts WHERE id = ?", (data["source_id"],))
                bal = cursor.fetchone()[0]
                if bal < data["amount"]:
                    messagebox.showerror("Insufficient Funds", "Not enough balance in source account!")
                    conn.close()
                    return

            if data["type"] == "DEPOSIT":
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (data["amount"], data["source_id"]))
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, 'DEPOSIT', ?, ?)", 
                             (data["source_id"], data["amount"], data["desc"]))
            
            elif data["type"] == "WITHDRAW":
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (data["amount"], data["source_id"]))
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, 'WITHDRAWAL', ?, ?)", 
                             (data["source_id"], data["amount"], data["desc"]))
                             
            elif data["type"] == "TRANSFER":
                # Out from source
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (data["amount"], data["source_id"]))
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description, related_account_id) VALUES (?, 'TRANSFER_OUT', ?, ?, ?)", 
                             (data["source_id"], data["amount"], data["desc"], data["target_id"]))
                # In to target
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (data["amount"], data["target_id"]))
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description, related_account_id) VALUES (?, 'TRANSFER_IN', ?, ?, ?)", 
                             (data["target_id"], data["amount"], data["desc"], data["source_id"]))

            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Transaction processed successfully!")
            self.refresh_ui()
            
        except Exception as e:
            messagebox.showerror("Error", f"Transaction failed: {e}")

class LoanTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("new_loan_entry"), **kwargs)
        self.edit_id = None
        self.customer_map = {}
        self.vehicle_map = {}
        self.loan_doc_path = tk.StringVar(value="")
        
        # Demo Status in Loan Tab
        if not ActivationManager.is_activated():
            self.demo_status = ctk.CTkLabel(self, text="", font=s.Styles.FONT_BOLD, text_color=s.GOLD)

            self.demo_status.pack(pady=2, padx=20, anchor="w")
            self.update_demo_loan_status()
        
        # --- Loan Form Card ---
        self.form_card, self.form = self.create_card(t("loan_application_details"))
        
        # Row 0: Loan Number (Custom ID)
        self.field_loan_number = self.create_input(self.form, "Loan ID (Editable)", 0, 0, columnspan=3)
        self.load_next_loan_number()
        
        # Row 1: Cascading Vehicle Selection
        self.field_make, self.make_var = self.create_select(self.form, t("make"), [], 1, 0)
        self.make_var.trace_add("write", self.on_make_selected)
        
        self.field_model, self.model_var = self.create_select(self.form, t("model"), [], 1, 1)
        self.model_var.trace_add("write", self.on_model_selected)
        
        self.field_vehicle, self.vehicle_var = self.create_select(self.form, t("registration_no"), [], 1, 2)
        self.vehicle_var.trace_add("write", self.update_from_vehicle)
        
        # Row 2: Customer, Loan Date, Sale Price
        self.field_customer, self.customer_var = self.create_searchable_select(self.form, t("customer_selection"), [], 2, 0)
        
        self.field_loan_date = self.create_date_picker(self.form, t("loan_date"), 2, 1, 
                                                      default_date=datetime.now(), on_change=self.on_loan_date_changed)
        
        self.field_sale_price = self.create_input(self.form, t("sale_price"), 2, 2)
        
        # Row 3: Down Payment, Loan Amount, Tenure
        self.part_amount_var = ctk.StringVar()
        self.part_amount_var.trace_add("write", self.update_loan_amount)
        self.field_part_amount = self.create_input(self.form, t("down_payment"), 3, 0, textvariable=self.part_amount_var)
        self.field_amount = self.create_input(self.form, t("loan_amount") + " *", 3, 1)
        self.field_tenure = self.create_input(self.form, t("loan_tenure") + " *", 3, 2)
        
        # Row 4: Interest Rate, Installment, Document Fee
        self.field_interest = self.create_input(self.form, t("interest_rate_pa") + " *", 4, 0)
        self.field_installment = self.create_input(self.form, t("installment"), 4, 1)
        self.field_installment.bind("<KeyRelease>", lambda e: self.calculate_interest_from_emi())
        self.field_doc_fee = self.create_input(self.form, t("document_fee"), 4, 2)
        
        # Row 5: Due Beginning Date, Photo, Calculate EMI
        self.field_due_date = self.create_date_picker(self.form, "DUE Beginning Date", 5, 0, 
                                                     default_date=add_months(datetime.now(), 1))
        
        # Row 5 Buttons
        self.btn_upload_loan = ctk.CTkButton(self.form, text="📄 " + t("photo"), height=32,
                                            fg_color="#475569", font=s.Styles.FONT_TINY_BOLD, command=self.upload_loan_doc)
        self.btn_upload_loan.grid(row=5, column=1, padx=10, pady=(22, 10), sticky="ew")
        
        self.calc_btn = ctk.CTkButton(self.form, text=t("calculate_emi"), height=32,
                                       fg_color=s.BLUE, hover_color="#2563eb", font=s.Styles.FONT_TINY_BOLD,
                                       command=self.calculate_emi)
        self.calc_btn.grid(row=5, column=2, padx=10, pady=(22, 10), sticky="ew")


        # Action Buttons
        self.save_btn, self.clear_btn = self.create_action_buttons(self.form, "SAVE LOAN", self.save_loan, self.clear_form)
        self.save_btn.configure(fg_color=s.GOLD, hover_color=s.GOLD_DARK)


        # --- Loan List Section with Search ---
        list_top = ctk.CTkFrame(self, fg_color="transparent")
        list_top.pack(fill="x", pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG)
        
        self.list_header = ctk.CTkLabel(list_top, text="Loans", font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.list_header.pack(side="left")
        
        self.l_search_entry = ctk.CTkEntry(list_top, placeholder_text="Filter Name/ID...", width=200, height=30)
        self.l_search_entry.pack(side="right", padx=(10, 0))
        self.l_search_entry.bind("<KeyRelease>", lambda e: self.load_loans())
        
        self.show_closed_var = tk.BooleanVar(value=False)
        self.closed_toggle = ctk.CTkCheckBox(list_top, text="Show Closed Loans", variable=self.show_closed_var, 
                                            command=self.load_loans, font=s.Styles.FONT_TINY_BOLD,
                                            fg_color=s.RED, hover_color="#e11d48")
        self.closed_toggle.pack(side="right")
        
        # Table Header
        self.list_header_card = ctk.CTkFrame(self, fg_color=s.NAVY, height=45, corner_radius=8)
        self.list_header_card.pack(fill="x", padx=s.PAD_LG)
        self.list_header_card.pack_propagate(False)
        
        lh_data = [("CUSTOMER", 0.02), ("AMOUNT/TENURE", 0.32), ("EMI", 0.62), ("ACTIONS", 0.82)]
        for text, rel_x in lh_data:
            lbl = ctk.CTkLabel(self.list_header_card, text=text, font=s.Styles.FONT_TINY_BOLD, text_color=s.WHITE)
            lbl.place(relx=rel_x, rely=0.5, anchor="w", x=15)

        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True, padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        # Lazy Loading State
        self.loan_offset = 0
        self.has_more = True
        self.loading_more = False
        
        # Bind scroll events
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind("<Configure>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<MouseWheel>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-4>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-5>", lambda e: self.check_scroll(), add="+")

        self.load_customers()
        self.load_vehicles()
        self.load_loans()

    def on_make_selected(self, *args):
        make_name = self.make_var.get()
        if not make_name or make_name == t("make"): return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT md.name 
                FROM vehicles v
                JOIN makes mk ON v.make_id = mk.id
                JOIN models md ON v.model_id = md.id
                WHERE mk.name = ? AND (v.status='Available' OR v.id IN (SELECT vehicle_id FROM loans WHERE id=?))
                ORDER BY md.name
            """, (make_name, self.edit_id or -1))
            models = [r[0] for r in cursor.fetchall()]
            conn.close()
            
            self.field_model.configure(values=models)
            if models:
                self.model_var.set(models[0])
            else:
                self.model_var.set("")
                self.field_vehicle.configure(values=[])
                self.vehicle_var.set("")
        except Exception as e:
            print(f"Error loading models for loan: {e}")

    def on_model_selected(self, *args):
        make_name = self.make_var.get()
        model_name = self.model_var.get()
        if not model_name: return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, v.reg_number, v.tentative_sale_price, v.purchase_price
                FROM vehicles v
                JOIN makes mk ON v.make_id = mk.id
                JOIN models md ON v.model_id = md.id
                WHERE mk.name = ? AND md.name = ? AND (v.status='Available' OR v.id IN (SELECT vehicle_id FROM loans WHERE id=?))
                ORDER BY v.reg_number
            """, (make_name, model_name, self.edit_id or -1))
            stock = cursor.fetchall()
            conn.close()
            
            self.vehicle_map = {reg: (vid, tentative, purchase) 
                                for vid, reg, tentative, purchase in stock}
            regs = list(self.vehicle_map.keys())
            self.field_vehicle.configure(values=regs)
            if regs:
                self.vehicle_var.set(regs[0])
            else:
                self.vehicle_var.set("")
        except Exception as e:
            print(f"Error loading regs for loan: {e}")

    def update_from_vehicle(self, *args):
        selected = self.vehicle_var.get()
        if selected in self.vehicle_map:
            vid, price, p_price = self.vehicle_map[selected]
            self.field_sale_price.delete(0, 'end')
            if price:
                self.field_sale_price.insert(0, str(price))
            else:
                self.field_sale_price.insert(0, "0.00")
            self.update_loan_amount()

    def update_loan_amount(self, *args):
        try:
            # Sale Price
            s_price_str = self.field_sale_price.get()
            s_price = float(s_price_str) if s_price_str else 0.0
            
            # Part Amount
            p_amount_str = self.part_amount_var.get()
            p_amount = float(p_amount_str) if p_amount_str else 0.0
            
            # Loan Amount
            loan_amount = max(0, s_price - p_amount)
            self.field_amount.delete(0, 'end')
            self.field_amount.insert(0, f"{loan_amount:.2f}")
        except:
            pass

    def calculate_emi(self):
        try:
            p = float(self.field_amount.get())
            r = float(self.field_interest.get())
            n = int(self.field_tenure.get())
            # Flat Interest Calculation: (Principal * Rate / 100) / Tenure
            if n > 0:
                interest_per_month = (p * (r / 100.0)) / n
                emi = (p / n) + interest_per_month
            else:
                emi = 0
            
            self.field_installment.delete(0, 'end')
            self.field_installment.insert(0, f"{emi:.2f}")
        except Exception as e:
            messagebox.showerror("Error", "Please enter valid numeric values for Amount, Tenure, and Interest.")

    def calculate_interest_from_emi(self):
        try:
            emi = float(self.field_installment.get())
            p = float(self.field_amount.get())
            n = int(self.field_tenure.get())
            
            if p > 0 and n > 0:
                # Rate = [((EMI * Tenure) / Principal) - 1] * 100
                rate = ((emi * n / p) - 1) * 100
                self.field_interest.delete(0, 'end')
                self.field_interest.insert(0, f"{rate:.2f}")
        except:
            pass # Silent failure to avoid popups while typing

    def load_customers(self):
        def fetch():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, phone FROM customers ORDER BY name ASC")
            res = cursor.fetchall()
            conn.close()
            return res

        def render(customers):
            if not self.winfo_exists(): return
            self.customer_map = {f"{name} ({phone})": cid for cid, name, phone in customers}
            self.field_customer.configure_values(list(self.customer_map.keys()))

        self.run_in_background(fetch, render)

    def load_vehicles(self):
        def fetch():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT name FROM makes ORDER BY name ASC")
            res = [r[0] for r in cursor.fetchall()]
            conn.close()
            return res

        def render(makes):
            if not self.winfo_exists(): return
            self.field_make.configure(values=[t("make")] + makes)
            self.make_var.set(t("make"))

        self.run_in_background(fetch, render)

    def upload_loan_doc(self):
        filename = filedialog.askopenfilename(title="Select Loan Document", 
                                              filetypes=[("PDF/Image Files", "*.pdf *.jpg *.jpeg *.png")])
        if filename:
            self.loan_doc_path.set(filename)
            self.btn_upload_loan.configure(fg_color=s.GREEN, text="📄 Doc Selected")

    def view_loan_doc(self, path):
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
        else:
            messagebox.showerror("Error", "File not found!")

    def check_scroll(self, event=None):
        if not self.has_more or self.loading_more:
            return
        try:
            if self._parent_canvas.yview()[1] > 0.8:
                self.load_loans(append=True)
        except: pass

    def load_loans(self, append=False):
        if self.loading_more or (append and not self.has_more):
            return
            
        self.loading_more = True
        
        if not append:
            self.loan_offset = 0
            self.has_more = True
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

        offset = self.loan_offset
        limit = 10
        
        show_closed = self.show_closed_var.get()
        query_text = self.l_search_entry.get().strip() if hasattr(self, 'l_search_entry') else ""
        
        def fetch():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                if show_closed:
                    status_query = "l.status IN ('Closed', 'Returned')"
                    params = []
                else:
                    status_query = "l.status = ?"
                    params = ["Active"]
                
                sql = f"""
                    SELECT l.id, l.loan_number, c.name, l.loan_amount, l.loan_tenure, l.installment_amount, l.status, v.reg_number
                    FROM loans l
                    LEFT JOIN customers c ON l.customer_id = c.id
                    LEFT JOIN vehicles v ON l.vehicle_id = v.id
                    WHERE {status_query}
                """
                
                if query_text:
                    sql += " AND (c.name LIKE ? OR l.loan_number LIKE ? OR v.reg_number LIKE ?)"
                    params.extend([f"%{query_text}%", f"%{query_text}%", f"%{query_text}%"])
                
                sql += " ORDER BY l.id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(sql, params)
                res = cursor.fetchall()
                conn.close()
                return res
            except Exception as e:
                print(f"Error fetching loans: {e}")
                return []

        def render(loans):
            if not self.winfo_exists():
                self.loading_more = False
                return
                
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

            if not loans:
                if not append:
                    for widget in self.list_container.winfo_children(): widget.destroy()
                    lbl = ctk.CTkLabel(self.list_container, text="No loans found.", font=s.Styles.FONT_TINY, text_color="gray")
                    lbl.pack(pady=20)
                self.has_more = False
                self.loading_more = False
                return

            if len(loans) < limit:
                self.has_more = False

            def render_loan_row(i, loan):
                lid, lnum, cname, amount, tenure, emi, status, reg = loan
                row = ctk.CTkFrame(self.list_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=55, corner_radius=0)
                row.pack(fill="x")
                row.pack_propagate(False)
                
                info_f = ctk.CTkFrame(row, fg_color="transparent")
                info_f.pack(side="left", padx=15, fill="y")
                
                ctk.CTkLabel(info_f, text=cname or "UNKNOWN CUSTOMER", font=s.Styles.FONT_BOLD, text_color=s.TEXT if cname else s.RED).pack(anchor="w", pady=(5,0))
                ctk.CTkLabel(info_f, text=f"{lnum} | {reg or '-'}", font=s.Styles.FONT_TINY, text_color=s.MUTED).pack(anchor="w")
                
                act_f = ctk.CTkFrame(row, fg_color="transparent")
                act_f.pack(side="right", padx=15, fill="y")
                
                ctk.CTkButton(act_f, text="🗑️ " + t("delete"), width=70, height=30, fg_color=s.RED, hover_color="#b91c1c", 
                             font=s.Styles.FONT_TINY, command=lambda l=lid: self.prompt_admin_auth_and_delete(l)).pack(side="right", padx=2, pady=12)

                ctk.CTkButton(act_f, text="✏️ " + t("edit"), width=60, height=30, fg_color=s.BLUE, hover_color="#2563eb", 
                             font=s.Styles.FONT_TINY, command=lambda l=lid: self.edit_loan(l)).pack(side="right", padx=2, pady=12)
                
                ctk.CTkButton(act_f, text="👁 " + t("view"), width=70, height=30, fg_color=s.GREEN, hover_color="#059669", 
                             font=s.Styles.FONT_TINY, command=lambda l=lid: self.view_loan(l)).pack(side="right", padx=2, pady=12)
                
                if status == 'Closed':
                    ctk.CTkLabel(act_f, text="CLOSED", font=s.Styles.FONT_TINY_BOLD, text_color=s.RED).pack(side="right", padx=10)
                
                ctk.CTkLabel(act_f, text=f"EMI: {format_indian_currency(emi)} ({tenure}M)", font=s.Styles.FONT_SMALL, text_color=s.NAVY, width=150, anchor="e").pack(side="right", padx=10)
                ctk.CTkLabel(act_f, text=f"Amt: {format_indian_currency(amount)}", font=s.Styles.FONT_SMALL, width=120, anchor="e").pack(side="right", padx=5)

            def on_complete(count):
                if not self.winfo_exists(): return
                if self.has_more:
                    self.load_more_btn = ctk.CTkButton(self.list_container, text="Click to Load More Loans...", 
                                                      fg_color="transparent", text_color=s.PRIMARY,
                                                      hover_color=s.BORDER, font=s.Styles.FONT_SMALL_BOLD,
                                                      command=lambda: self.load_loans(append=True))
                    self.load_more_btn.pack(pady=20, fill="x")
                self.loading_more = False

            self.render_list_chunked(self.list_container, loans, render_loan_row, 
                                   clear=not append, start_row_idx=offset, on_complete=on_complete)
            self.loan_offset += len(loans)
            self.list_header.configure(text="Closed Loans" if show_closed else "Active Loans")

        self.run_in_background(fetch, render)

    def on_loan_date_changed(self, new_date_str):
        try:
            d, m, y = map(int, new_date_str.split('-'))
            sourcedate = datetime(y, m, d)
            new_due_date = add_months(sourcedate, 1)
            self.field_due_date.set_date(new_due_date)
        except: pass

    def save_loan(self):
        c_selected = self.field_customer.get()
        amount = self.field_amount.get()
        tenure = self.field_tenure.get()
        interest = self.field_interest.get()
        emi = self.field_installment.get()
        doc_fee = self.field_doc_fee.get()
        due_date = self.field_due_date.get() or datetime.now().strftime('%d-%m-%Y')
        
        if not c_selected or "Select" in c_selected or not amount or not tenure or not interest:
            messagebox.showerror("Error", "All fields marked with * are required!")
            return
            
        # --- Demo Mode / Activation Check ---
        if not ActivationManager.is_activated():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'Active'")
                loan_count = cursor.fetchone()[0]
                conn.close()
                limit = ActivationManager.get_loan_limit()
                if loan_count >= limit:
                    messagebox.showerror("Demo Mode Limit", 
                                       f"You have reached the limit of {limit} loans for Demo Mode.\n\n"
                                       "Please activate the software to create more loans.\n"
                                       "Go to: Master Control -> System Setting -> Software Activation")
                    return
            except Exception as e:
                print(f"Activation check error: {e}")
            
        v_selected = self.vehicle_var.get()
        if v_selected == "" or v_selected == t("registration_no"):
            messagebox.showerror("Error", "Please select a vehicle registration number!")
            return
            
        cid = self.customer_map.get(c_selected)
        vehicle_info = self.vehicle_map.get(v_selected)
        vid = vehicle_info[0] if vehicle_info else None
        p_price = vehicle_info[2] if vehicle_info else 0.0
        
        loan_date = self.field_loan_date.get() or datetime.now().strftime('%d-%m-%Y')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check for duplicate active loan if vehicle is selected
            if vid:
                cursor.execute("SELECT id FROM loans WHERE vehicle_id = ? AND status = 'Active' AND id != ?", (vid, self.edit_id or -1))
                if cursor.fetchone():
                    messagebox.showerror("Error", "An active loan already exists for this vehicle!")
                    conn.close()
                    return

            f_amt = float(amount)
            f_emi = float(emi) if emi else 0.0
            f_sale_price = float(self.field_sale_price.get()) if self.field_sale_price.get() else 0.0
            f_down_payment = float(self.part_amount_var.get()) if self.part_amount_var.get() else 0.0
            f_doc_fee = float(doc_fee) if doc_fee else 0.0
            
            # Warning if sale price < purchase price
            if f_sale_price < p_price:
                if not messagebox.askyesno("Warning", f"Sale Price ({format_indian_currency(f_sale_price)}) is lower than Purchase Price ({format_indian_currency(p_price)}). Proceed anyway?"):
                    return
            
            # If editing, revert previous impact
            if self.edit_id:
                self._revert_loan_impact(cursor, self.edit_id)
                self.edit_id = None
                
            loan_number = self.field_loan_number.get()
            if not loan_number: loan_number = f"L-{int(datetime.now().timestamp())[-4:]}"
                
            # 1. Save Loan Record
            cursor.execute("""
                INSERT INTO loans (loan_number, customer_id, vehicle_id, loan_amount, loan_tenure, interest_rate, installment_amount, loan_date, down_payment, document_fee, loan_doc_path, due_beginning_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (loan_number, cid, vid, f_amt, tenure, interest, f_emi, loan_date, f_down_payment, f_doc_fee, self.loan_doc_path.get(), due_date))
            
            # 2. Update Customer Balance (Loan Amount + Down Payment)
            # IMPORTANT: Document Fee is NOT added to customer balance per requirement
            cursor.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (f_amt + f_down_payment, cid))
            
            # 3. Handle Document Fee for Shop (Income)
            if f_doc_fee > 0:
                # Find Shop Cash account
                cursor.execute("SELECT id FROM accounts WHERE name = 'Shop Cash'")
                shop_cash_res = cursor.fetchone()
                if shop_cash_res:
                    shop_cash_id = shop_cash_res[0]
                    # Deposit into Shop Cash
                    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (f_doc_fee, shop_cash_id))
                    # Record Transaction
                    veh_info = f" ({v_selected})" if v_selected != "Select Vehicle..." else ""
                    cursor.execute("""
                        INSERT INTO transactions (account_id, transaction_type, amount, description)
                        VALUES (?, 'DEPOSIT', ?, ?)
                    """, (shop_cash_id, f_doc_fee, f"Document Fee for Loan - {c_selected}{veh_info}"))
                else:
                    print("Warning: 'Shop Cash' account not found, document fee recorded in loan only.")
            
            conn.commit()
            conn.close()
            ActivationManager.invalidate_cache()
            messagebox.showinfo("Success", f"Loan of {format_indian_currency(f_amt)} sanctioned and credited to customer account!")
            self.clear_form()
            self.load_loans()
            self.mark_dirty()
            if hasattr(self, 'update_demo_loan_status'): self.update_demo_loan_status()
            # Update parent banner if it exists
            parent = self.winfo_toplevel()
            if hasattr(parent, 'dashboard_page'):
                parent.dashboard_page.update_demo_banner()
                parent.dashboard_page.mark_tab_dirty("Dashboard")
                parent.dashboard_page.mark_tab_dirty("Customers")
        except ValueError:
            messagebox.showerror("Error", "Loan Amount and EMI must be valid numbers!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save loan: {e}")

    def prompt_admin_auth_and_delete(self, lid):
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("admin_password_required"))
        dialog.geometry("350x220")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        dialog.update_idletasks()
        try:
            x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() - 350) // 2
            y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() - 220) // 2
            dialog.geometry(f"+{x}+{y}")
        except:
            pass
        
        ctk.CTkLabel(dialog, text=t("enter_admin_password"), font=s.Styles.FONT_BOLD).pack(pady=(25, 15))
        
        pw_entry = ctk.CTkEntry(dialog, placeholder_text=t("password"), show="*", width=250)
        pw_entry.pack(pady=10, padx=20)
        pw_entry.focus()
        
        def verify():
            pw = pw_entry.get()
            if not pw: return
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE (role='Administrator' OR role='admin') AND password=?", (pw,))
                res = cursor.fetchone()
                conn.close()
                if res:
                    dialog.destroy()
                    self.delete_loan(lid)
                else:
                    messagebox.showerror(t("error"), t("incorrect_password"), parent=dialog)
            except Exception as e:
                messagebox.showerror(t("error"), f"Auth failed: {e}", parent=dialog)
                
        btn = ctk.CTkButton(dialog, text=t("verify_proceed"), fg_color=s.RED, hover_color="#b91c1c", command=verify, width=200)
        btn.pack(pady=15)
        dialog.bind("<Return>", lambda e: verify())

    def delete_loan(self, lid):
        if messagebox.askyesno("Confirm", "Delete this loan record? This will also revert the customer's balance and document fees."):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Check for associated Sales
                cursor.execute("""
                    SELECT v.status, v.vehicle_name, v.reg_number, l.customer_id, l.loan_amount, l.down_payment
                    FROM loans l
                    LEFT JOIN vehicles v ON v.id = l.vehicle_id 
                    WHERE l.id = ?
                """, (lid,))
                res = cursor.fetchone()
                if res:
                    v_status, v_name, reg, cid, l_amt, d_amt = res
                    v_status = str(v_status).strip().lower() if v_status else ""
                    if v_status == 'sold':
                        messagebox.showerror("Error", f"Cannot delete Loan (Process) for {v_name} ({reg}).\n\nAssociated Sale exists. Please delete the Sale first.")
                        conn.close()
                        return
                    
                    # Additional check: If no specific vehicle link, check customer balance
                    total_to_deduct = (l_amt or 0) + (d_amt or 0)
                    cursor.execute("SELECT balance, name FROM customers WHERE id=?", (cid,))
                    cust = cursor.fetchone()
                    if cust and cust[0] < total_to_deduct:
                        if not messagebox.askyesno("Warning", f"Customer {cust[1]} has a balance of {format_indian_currency(cust[0])}, but deleting this loan will deduct {format_indian_currency(total_to_deduct)}.\n\nThis may be because the loan credit was already used for a sale.\n\nProceed anyway?"):
                            conn.close()
                            return
                
                self._revert_loan_impact(cursor, lid)
                conn.commit()
                conn.close()
                ActivationManager.invalidate_cache()
                self.load_loans()
                self.load_customers()
                self.load_vehicles()
                messagebox.showinfo("Success", "Loan record deleted and financial impact reverted.")
                if hasattr(self, 'update_demo_loan_status'): self.update_demo_loan_status()
                # Update parent banner
                parent = self.winfo_toplevel()
                if hasattr(parent, 'dashboard_page') and hasattr(parent.dashboard_page, 'update_demo_banner'):
                    parent.dashboard_page.update_demo_banner()
            except Exception as e: 
                messagebox.showerror("Error", f"Failed to delete loan: {e}")

    def _revert_loan_impact(self, cursor, lid):
        cursor.execute("SELECT customer_id, loan_amount, down_payment, document_fee FROM loans WHERE id=?", (lid,))
        loan = cursor.fetchone()
        if not loan: return
        cid, amount, down_payment, doc_fee = loan
        
        # 1. Revert Customer Balance
        cursor.execute("UPDATE customers SET balance = balance - ? WHERE id = ?", (amount + (down_payment or 0), cid))
        
        # 2. Revert Document Fee from Shop Cash
        if doc_fee and doc_fee > 0:
            cursor.execute("SELECT id FROM accounts WHERE name = 'Shop Cash'")
            shop_res = cursor.fetchone()
            if shop_res:
                shop_id = shop_res[0]
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (doc_fee, shop_id))
                cursor.execute("DELETE FROM transactions WHERE account_id=? AND description LIKE ? AND amount=?", (shop_id, "%Document Fee for Loan%", doc_fee))
        
        # 3. Delete Loan
        cursor.execute("DELETE FROM loans WHERE id=?", (lid,))

    def view_loan(self, lid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, 
                       l.loan_amount, l.loan_tenure, l.interest_rate, l.installment_amount, 
                       l.loan_date, l.down_payment, l.document_fee, l.loan_doc_path, l.due_beginning_date, l.status
                FROM loans l 
                LEFT JOIN customers c ON l.customer_id = c.id 
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone()
            conn.close()
            if loan:
                ViewLoanWindow(self.winfo_toplevel(), loan, on_change=self.load_loans)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load loan details: {e}")

    def edit_loan(self, lid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.customer_id, l.vehicle_id, l.loan_amount, l.loan_tenure, 
                       l.interest_rate, l.installment_amount, l.down_payment, l.document_fee, 
                       l.loan_doc_path, v.vehicle_name, v.reg_number, c.name, c.phone, l.due_beginning_date, l.loan_date, l.loan_number
                FROM loans l
                LEFT JOIN customers c ON l.customer_id = c.id
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone()
            
            if loan:
                cid, vid, amt, tenure, rate, emi, dp, fee, d_path, v_name, reg, c_name, c_phone, due_date, saved_loan_date, loan_number = loan
                self.edit_id = lid
                
                # Load into form
                self.field_loan_number.delete(0, 'end')
                self.field_loan_number.insert(0, loan_number if loan_number else f"L-{lid}")
                self.field_loan_date.set_date(saved_loan_date)
                
                # Cascading Vehicle pre-fill
                if vid:
                    cursor.execute("""
                        SELECT mk.name, md.name 
                        FROM vehicles v
                        JOIN makes mk ON v.make_id = mk.id
                        JOIN models md ON v.model_id = md.id
                        WHERE v.id=?
                    """, (vid,))
                    v_res = cursor.fetchone()
                    if v_res:
                        self.make_var.set(v_res[0])
                        self.on_make_selected()
                        self.model_var.set(v_res[1])
                        self.on_model_selected()
                        self.vehicle_var.set(reg)
                
                c_str = f"{c_name} (ID: {cid}, Mob: {c_phone or '-'})"
                if c_str not in self.field_customer.values:
                    self.field_customer.configure_values(list(self.field_customer.values) + [c_str])
                self.customer_var.set(c_str)
                
                self.field_amount.delete(0, 'end')
                self.field_amount.insert(0, str(amt))
                self.field_tenure.delete(0, 'end')
                self.field_tenure.insert(0, str(tenure))
                self.field_interest.delete(0, 'end')
                self.field_interest.insert(0, str(rate))
                self.field_installment.delete(0, 'end')
                self.field_installment.insert(0, str(emi))
                self.part_amount_var.set(str(dp))
                self.field_doc_fee.delete(0, 'end')
                self.field_doc_fee.insert(0, str(fee))
                self.field_due_date.set_date(due_date)
                
                if d_path:
                    self.loan_doc_path.set(d_path)
                    self.btn_upload_loan.configure(fg_color=s.GREEN, text="📄 Doc Selected")
                
                self.header.configure(text="Edit Loan")
                self.save_btn.configure(text="UPDATE LOAN")
                self._parent_canvas.yview_moveto(0)
                messagebox.showinfo("Edit Mode", "Loan data loaded. Financial impacts will be auto-corrected on update.")
            
            conn.close()
        except Exception as e:
            if 'conn' in locals(): conn.close()
            messagebox.showerror("Error", f"Failed to load loan: {e}")

    def clear_form(self):
        self.edit_id = None
        self.make_var.set("")
        self.model_var.set("")
        self.vehicle_var.set("")
        self.field_model.configure(values=[])
        self.field_vehicle.configure(values=[])
        self.field_customer.set("")
        self.field_amount.delete(0, 'end')
        self.field_tenure.delete(0, 'end')
        self.field_interest.delete(0, 'end')
        self.field_installment.delete(0, 'end') # Assuming field_emi is now field_installment
        self.part_amount_var.set("0.0") # This was field_down_payment in the diff, but part_amount_var in original
        self.field_doc_fee.delete(0, 'end')
        self.field_sale_price.delete(0, 'end')
        self.loan_doc_path.set("")
        self.btn_upload_loan.configure(fg_color="#475569", text="📄 Upload Loan Doc")
        self.header.configure(text="New Loan")
        self.save_btn.configure(text="SAVE LOAN")
        self.field_due_date.set_date(datetime.now())
        self.field_loan_date.set_date(datetime.now())
        self.load_next_loan_number()
        if hasattr(self, 'update_demo_loan_status'): self.update_demo_loan_status()

    def load_next_loan_number(self):
        try:
            conn = get_connection(); c = conn.cursor()
            c.execute("SELECT seq FROM sqlite_sequence WHERE name='loans'")
            res = c.fetchone()
            conn.close()
            next_id = int(res[0]) + 1 if res else 1
            self.field_loan_number.delete(0, 'end')
            self.field_loan_number.insert(0, f"L-{next_id}")
        except: pass

    def update_demo_loan_status(self):
        if not hasattr(self, 'demo_status'): return
        if ActivationManager.is_activated():
            self.demo_status.pack_forget()
        else:
            limit = ActivationManager.get_loan_limit()
            count = ActivationManager.get_current_loan_count()
            balance = max(0, limit - count)
            self.demo_status.configure(text=f"📌 Demo Entries: {count}/{limit} used. {balance} remaining.")



class RCPledgeTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("rc_pledge_loan"), **kwargs)
        self.edit_id = None
        self.customer_map = {}
        self.loan_doc_path = tk.StringVar(value="")
        self.signed_doc_path = tk.StringVar(value="")
        self.show_closed_var = tk.BooleanVar(value=False)
        
        # --- Form Container ---
        self.form_container = ctk.CTkFrame(self, fg_color="transparent")
        self.form_container.pack(fill="x", padx=s.PAD_SM)
        self.form_container.grid_columnconfigure(0, weight=1)
        self.form_container.grid_columnconfigure(1, weight=1)

        # LEFT: Vehicle & Customer Details
        self.v_card, self.v_form = self.create_card(t("pledge_details"), master=self.form_container)
        self.v_card.grid(row=0, column=0, sticky="nsew", padx=s.PAD_SM)
        
        # Row 1: Customer Selection
        self.field_customer, self.customer_var = self.create_searchable_select(self.v_form, t("select_customer"), [], 1, 0, columnspan=2)
        
        # Row 2: Make, Model
        self.field_make, self.make_var = self.create_select(self.v_form, t("make"), [], 2, 0, command=self.load_models_for_make)
        self.field_model, self.model_var = self.create_select(self.v_form, t("model"), [], 2, 1)
        
        # Row 3: Reg Number, Model Year
        self.reg_var = ctk.StringVar()
        self.reg_trace_id = self.reg_var.trace_add("write", self.format_reg_number)
        self.field_reg = self.create_input(self.v_form, t("registration_no"), 3, 0, textvariable=self.reg_var)
        
        cur_year = datetime.now().year
        years = [str(y) for y in range(cur_year, 1999, -1)]
        self.field_year, _ = self.create_select(self.v_form, t("model_year"), years, 3, 1)
        
        # Row 4: Vehicle Value, RC Possession
        self.field_val = self.create_input(self.v_form, t("vehicle_value"), 4, 0)
        self.rc_pos_var = self.create_radio_group(self.v_form, t("rc_possession"), [t("received"), t("not_received")], 4, 1, default_value="Received")

        # RIGHT: Loan Details
        self.l_card, self.l_form = self.create_card(t("loan_details"), master=self.form_container)
        self.l_card.grid(row=0, column=1, sticky="nsew", padx=(s.PAD_SM, 0))

        # Row 0: Editable Loan Number
        self.field_loan_number = self.create_input(self.l_form, "Loan ID (Editable)", 0, 0, columnspan=2)
        self.load_next_loan_number()

        # Row 1: Loan Amount, Tenure
        self.field_amount = self.create_input(self.l_form, t("loan_amount") + " *", 1, 0)
        self.field_tenure = self.create_input(self.l_form, t("loan_tenure") + " *", 1, 1)
        
        # Row 2: Interest Rate, EMI
        self.field_interest = self.create_input(self.l_form, t("interest_rate_pa") + " *", 2, 0)
        self.field_emi = self.create_input(self.l_form, t("installment"), 2, 1)
        self.field_emi.bind("<KeyRelease>", lambda e: self.calculate_interest_from_emi())
        
        # Row 3: Loan Date, Doc Fee
        self.field_loan_date = self.create_date_picker(self.l_form, t("date"), 3, 0, 
                                                      default_date=datetime.now(), on_change=self.on_loan_date_changed)
        self.field_doc_fee = self.create_input(self.l_form, t("document_fee"), 3, 1)
        
        # Row 4: Due Date, Disbursement From
        self.field_due_date = self.create_date_picker(self.l_form, "DUE Beginning Date", 4, 0, 
                                                     default_date=add_months(datetime.now(), 1))
        self.field_acc, self.acc_var = self.create_select(self.l_form, t("paid_from") + " *", [], 4, 1)

        # Row 5: Action Buttons & Uploads
        self.btn_cont = ctk.CTkFrame(self.l_form, fg_color="transparent")
        self.btn_cont.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.btn_calc = ctk.CTkButton(self.btn_cont, text=t("calculate_emi"), width=120, fg_color=s.BLUE, command=self.calculate_emi)
        self.btn_calc.pack(side="left", padx=5)
        
        self.btn_upload = ctk.CTkButton(self.btn_cont, text="📄 " + t("signed_docs"), width=120, fg_color=s.PRIMARY, command=self.upload_signed_doc)
        self.btn_upload.pack(side="left", padx=5)

        self.save_btn, self.clear_btn = self.create_action_buttons(self.l_form, t("save_pledge"), self.save_pledge_loan, self.clear_form)
        self.save_btn.configure(fg_color=s.GOLD, hover_color=s.GOLD_DARK)

        # --- List Section ---
        header_f = ctk.CTkFrame(self, fg_color="transparent")
        header_f.pack(pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG, fill="x")
        
        self.list_header = ctk.CTkLabel(header_f, text="Active Pledge Loans", font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.list_header.pack(side="left")
        
        ctk.CTkCheckBox(header_f, text=t("show_closed"), variable=self.show_closed_var, 
                        command=self.load_pledge_loans, font=s.Styles.FONT_TINY_BOLD,
                        fg_color=s.RED, hover_color="#e11d48").pack(side="right", padx=10)
        
        self.list_header_card = ctk.CTkFrame(self, fg_color=s.NAVY, height=45, corner_radius=8)
        self.list_header_card.pack(fill="x", padx=s.PAD_LG)
        self.list_header_card.pack_propagate(False)
        
        h_data = [("CUSTOMER", 0.02), ("VEHICLE", 0.25), ("LOAN", 0.48), ("STATUS", 0.68), ("ACTIONS", 0.78)]
        for text, rel_x in h_data:
            lbl = ctk.CTkLabel(self.list_header_card, text=text, font=s.Styles.FONT_TINY_BOLD, text_color=s.WHITE)
            lbl.place(relx=rel_x, rely=0.5, anchor="w", x=15)

        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True, padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        # Lazy Loading State
        self.pledge_offset = 0
        self.has_more = True
        self.loading_more = False
        
        # Bind scroll events
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind("<Configure>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<MouseWheel>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-4>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-5>", lambda e: self.check_scroll(), add="+")

        self.load_customers(); self.load_makes(); self.load_accounts(); self.load_pledge_loans()

    def calculate_emi(self):
        try:
            p = float(self.field_amount.get())
            r = float(self.field_interest.get())
            n = int(self.field_tenure.get())
            if n > 0:
                interest_per_month = (p * (r / 100.0)) / n
                emi = (p / n) + interest_per_month
            else:
                emi = 0
            self.field_emi.delete(0, 'end'); self.field_emi.insert(0, f"{emi:.2f}")
        except: messagebox.showerror("Error", "Enter valid numeric values for Amount, Tenure and Interest.")

    def calculate_interest_from_emi(self):
        try:
            emi = float(self.field_emi.get())
            p = float(self.field_amount.get())
            n = int(self.field_tenure.get())
            
            if p > 0 and n > 0:
                # Rate = [((EMI * Tenure) / Principal) - 1] * 100
                rate = ((emi * n / p) - 1) * 100
                self.field_interest.delete(0, 'end')
                self.field_interest.insert(0, f"{rate:.2f}")
        except:
            pass # Silent failure to avoid popups while typing

    def format_reg_number(self, *args):
        try:
            # Capture state: current value and cursor position
            raw = self.reg_var.get().upper()
            pos = self.field_reg._entry.index("insert")
            
            # Clean up: take only alphanumeric chars
            alnum_data = [(i, c) for i, c in enumerate(raw) if c.isalnum()]
            valid_list = []
            valid_orig_indices = []
            for i, (orig_idx, c) in enumerate(alnum_data[:10]):
                valid_list.append(c)
                valid_orig_indices.append(orig_idx)
            
            alnums_before = sum(1 for idx in valid_orig_indices if idx < pos)
            clean = "".join(valid_list)
            
            # Reconstruct formatted string based on pattern
            res = ""
            if len(clean) >= 2:
                res += clean[0:2]
                if len(clean) > 2:
                    res += " " + clean[2:4]
                    if len(clean) > 4:
                        res += " - " + clean[4:6]
                        if len(clean) > 6:
                            res += " " + clean[6:10]
            else:
                res += clean

            if res != raw:
                # Update variable without triggering recursion
                self.reg_var.trace_remove("write", self.reg_trace_id)
                self.reg_var.set(res)
                self.reg_trace_id = self.reg_var.trace_add("write", self.format_reg_number)
                
                # Calculate new cursor position relative to valid alnums counted
                new_pos = 0
                if alnums_before > 0:
                    count = 0
                    for i, char in enumerate(res):
                        if char.isalnum(): count += 1
                        new_pos = i + 1
                        if count == alnums_before: break
                
                # If the target position is a separator, move past it
                while new_pos < len(res) and not res[new_pos].isalnum():
                    new_pos += 1
                
                target_pos = new_pos
                if self.field_reg.winfo_exists():
                    self.field_reg.after_idle(lambda: self.field_reg._entry.icursor(target_pos) if self.field_reg.winfo_exists() else None)
        except:
            # Restore trace if something fails
            try:
                self.reg_var.trace_remove("write", self.reg_trace_id)
                self.reg_trace_id = self.reg_var.trace_add("write", self.format_reg_number)
            except: pass

    def load_customers(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id, name, phone FROM customers ORDER BY name")
            customers = cursor.fetchall(); conn.close()
            self.customer_map = {f"{name} (ID: {cid}, Mob: {phone or '-'})": cid for cid, name, phone in customers}
            v_list = list(self.customer_map.keys())
            self.field_customer.configure_values(v_list)
        except Exception as e: 
            print(f"Error loading customers for autocomplete: {e}")

    def load_makes(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT name FROM makes ORDER BY name")
            makes = [r[0] for r in cursor.fetchall()]; conn.close()
            self.field_make.configure(values=makes)
        except: pass

    def load_models_for_make(self, make_name):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id FROM makes WHERE name=?", (make_name,))
            res = cursor.fetchone()
            if res:
                cursor.execute("SELECT name FROM models WHERE make_id=? ORDER BY name", (res[0],))
                models = [r[0] for r in cursor.fetchall()]
                self.field_model.configure(values=models)
                if models: self.model_var.set(models[0])
            conn.close()
        except: pass

    def load_accounts(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = cursor.fetchall(); conn.close()
            self.account_map = {f"{name} (₹{bal:,.2f})": aid for aid, name, bal in accounts}
            self.field_acc.configure(values=list(self.account_map.keys()))
        except: pass

    def upload_signed_doc(self):
        path = filedialog.askopenfilename(title="Select Signed Document", filetypes=[("Image/PDF", "*.jpg *.jpeg *.png *.pdf")])
        if path:
            self.signed_doc_path.set(path)
            self.btn_upload.configure(fg_color=s.GREEN, text="✅ Document Selected")

    def on_loan_date_changed(self, new_date_str):
        try:
            d, m, y = map(int, new_date_str.split('-'))
            sourcedate = datetime(y, m, d)
            new_due_date = add_months(sourcedate, 1)
            self.field_due_date.set_date(new_due_date)
        except: pass

    def save_pledge_loan(self):
        try:
            # Validations
            cust = self.field_customer.get(); make = self.make_var.get(); reg = self.reg_var.get(); amt_str = self.field_amount.get()
            acc = self.acc_var.get(); emi_str = self.field_emi.get()
            if any(not x or "Select" in x for x in [cust, make, reg, acc]) or not amt_str:
                messagebox.showerror("Error", "Please fill required fields and select a customer/account."); return
            
            cid = self.customer_map[cust]; aid = self.account_map[acc]; amt = float(amt_str)
            emi = float(emi_str) if emi_str else 0.0; tenure = int(self.field_tenure.get() or 0)
            interest = float(self.field_interest.get() or 0); doc_fee = float(self.field_doc_fee.get() or 0)
            
            conn = get_connection(); cursor = conn.cursor()
            
            # --- REFINANCE & DUPLICATE VEHICLE CHECK START ---
            vid = None
            old_loan_id = None
            refinance_settlement_amt = 0
            
            if not self.edit_id:
                cursor.execute("SELECT id, status FROM vehicles WHERE reg_number = ?", (reg,))
                existing_vehicle = cursor.fetchone()
                
                if existing_vehicle:
                    vid = existing_vehicle[0]
                    v_status = existing_vehicle[1]
                    
                    # Check for active loan
                    cursor.execute("""
                        SELECT id, loan_amount, loan_number,
                               (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE loan_id = loans.id) as total_paid
                        FROM loans 
                        WHERE vehicle_id = ? AND status = 'Active'
                    """, (vid,))
                    active_loan = cursor.fetchone()
                    
                    if active_loan:
                        old_loan_id, old_loan_amount, old_loan_number, total_paid = active_loan
                        refinance_settlement_amt = max(0, old_loan_amount - total_paid)
                        
                        if amt < refinance_settlement_amt:
                            messagebox.showerror("Refinance Error", f"New loan amount (₹{amt:,.2f}) is less than the settlement amount (₹{refinance_settlement_amt:,.2f}) of the active loan ({old_loan_number}).")
                            conn.close()
                            return
                            
                        net_disbursement = amt - refinance_settlement_amt
                        msg = (f"An active loan ({old_loan_number}) exists for this vehicle.\n\n"
                               f"Old Loan Outstanding: ₹{refinance_settlement_amt:,.2f}\n"
                               f"New Loan Amount: ₹{amt:,.2f}\n"
                               f"Net Disbursement: ₹{net_disbursement:,.2f}\n\n"
                               "Proceed with Refinance? This will settle and close the old loan.")
                        if not messagebox.askyesno("Refinance Vehicle", msg):
                            conn.close()
                            return
            # --- REFINANCE CHECK END ---
            
            if self.edit_id:
                if hasattr(self, 'orig_aid') and self.orig_aid:
                    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (self.orig_amt, self.orig_aid))
                    cursor.execute("DELETE FROM transactions WHERE description LIKE ?", (f"Loan Disbursement: {self.orig_loan_number}%",))
                    if hasattr(self, 'orig_doc_fee') and self.orig_doc_fee > 0:
                        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (self.orig_doc_fee, self.orig_aid))
                        cursor.execute("DELETE FROM transactions WHERE description = ?", (f"Document Fee: {self.orig_loan_number}",))
                
                cursor.execute("""
                    UPDATE vehicles SET vehicle_name=?, make_id=(SELECT id FROM makes WHERE name=?), 
                                        model_id=(SELECT id FROM models WHERE name=?), model_year=?, 
                                        reg_number=?, purchase_price=?
                    WHERE id=?
                """, (f"{make} {self.model_var.get()}", make, self.model_var.get(), self.field_year.get(), reg, float(self.field_val.get() or 0), self.edit_vid))
                
            loan_number = self.field_loan_number.get()
            if not loan_number: loan_number = f"L-{int(datetime.now().timestamp())[-4:]}"

            if self.edit_id:
                cursor.execute("""
                    UPDATE loans SET customer_id=?, loan_amount=?, loan_tenure=?, interest_rate=?, 
                                     installment_amount=?, loan_date=?, due_beginning_date=?, 
                                     document_fee=?, loan_doc_path=?, loan_number=?
                    WHERE id=?
                """, (cid, amt, tenure, interest, emi, self.field_loan_date.get(), self.field_due_date.get(), doc_fee, self.signed_doc_path.get(), loan_number, self.edit_id))
                lid = self.edit_id
            else:
                # 1. Insert/Update Vehicle as 'Pledge'
                if vid:
                    cursor.execute("""
                        UPDATE vehicles SET vehicle_name=?, make_id=(SELECT id FROM makes WHERE name=?), 
                                            model_id=(SELECT id FROM models WHERE name=?), model_year=?, 
                                            status='Pledge', purchase_price=?
                        WHERE id=?
                    """, (f"{make} {self.model_var.get()}", make, self.model_var.get(), self.field_year.get(), float(self.field_val.get() or 0), vid))
                else:
                    cursor.execute("""
                        INSERT INTO vehicles (vehicle_name, make_id, model_id, model_year, reg_number, status, purchase_price)
                        VALUES (?, (SELECT id FROM makes WHERE name=?), (SELECT id FROM models WHERE name=?), ?, ?, ?, ?)
                    """, (f"{make} {self.model_var.get()}", make, self.model_var.get(), self.field_year.get(), reg, 'Pledge', float(self.field_val.get() or 0)))
                    vid = cursor.lastrowid
                
                # Close old loan if refinancing
                if old_loan_id:
                    if refinance_settlement_amt > 0:
                        cursor.execute("""
                            INSERT INTO payments (loan_id, amount, payment_date, account_id, remarks)
                            VALUES (?, ?, ?, ?, ?)
                        """, (old_loan_id, refinance_settlement_amt, self.field_loan_date.get(), aid, f"Refinance Settlement for new loan {loan_number}"))
                    cursor.execute("UPDATE loans SET status = 'Closed', closed_date = ? WHERE id = ?", (self.field_loan_date.get(), old_loan_id))

                # 2. Insert Loan
                cursor.execute("""
                    INSERT INTO loans (loan_number, customer_id, vehicle_id, loan_amount, loan_tenure, interest_rate, installment_amount, 
                                     loan_date, due_beginning_date, document_fee, loan_doc_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (loan_number, cid, vid, amt, tenure, interest, emi, self.field_loan_date.get(), self.field_due_date.get(), doc_fee, self.signed_doc_path.get()))
                lid = cursor.lastrowid
            
            # 3. Accounting Logic
            # Disbursement (Cr Account)
            actual_disbursement = amt
            if not self.edit_id and old_loan_id:
                actual_disbursement = amt - refinance_settlement_amt
                
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (actual_disbursement, aid))
            
            if not self.edit_id and old_loan_id:
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, ?, ?, ?)",
                             (aid, 'WITHDRAWAL', actual_disbursement, f"Refinance Net Disbursement: {loan_number} (Reg: {reg})"))
            else:
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, ?, ?, ?)",
                             (aid, 'WITHDRAWAL', actual_disbursement, f"Loan Disbursement: {loan_number} (Reg: {reg})"))
            
            # Document Fee (Dr Account / Income)
            if doc_fee > 0:
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (doc_fee, aid))
                cursor.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (?, ?, ?, ?)",
                             (aid, 'INCOME', doc_fee, f"Document Fee: {loan_number}"))
            
            conn.commit(); conn.close()
            ActivationManager.invalidate_cache()
            messagebox.showinfo("Success", "RC Pledge Loan saved successfully!")
            self.clear_form(); self.load_pledge_loans()
        except Exception as e: messagebox.showerror("Error", f"Failed to save pledge loan: {e}")

    def check_scroll(self, event=None):
        if not self.has_more or self.loading_more:
            return
        try:
            if self._parent_canvas.yview()[1] > 0.8:
                self.load_pledge_loans(append=True)
        except: pass

    def load_pledge_loans(self, append=False):
        if self.loading_more or (append and not self.has_more):
            return
            
        self.loading_more = True
        
        if not append:
            self.pledge_offset = 0
            self.has_more = True
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

        offset = self.pledge_offset
        limit = 10
        status_filter = 'Closed' if self.show_closed_var.get() else 'Active'
        
        def fetch():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT l.id, COALESCE(c.name, '[No Customer]'), v.vehicle_name, v.reg_number, l.loan_amount, l.loan_tenure, l.status
                    FROM loans l
                    LEFT JOIN customers c ON l.customer_id = c.id
                    LEFT JOIN vehicles v ON l.vehicle_id = v.id
                    WHERE l.status = ? AND (v.status = 'Pledge' OR l.vehicle_id IS NULL)
                    ORDER BY l.id DESC LIMIT ? OFFSET ?
                """, (status_filter, limit, offset))
                rows = cursor.fetchall()
                conn.close()
                return rows
            except Exception as e:
                print(f"Error fetching pledge loans: {e}")
                return []

        def render(rows):
            if not self.winfo_exists():
                self.loading_more = False
                return
                
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

            # Update title
            self.list_header.configure(text="Closed Pledge Loans" if status_filter == 'Closed' else "Active Pledge Loans")

            if not rows:
                if not append:
                    for w in self.list_container.winfo_children(): w.destroy()
                    lbl = ctk.CTkLabel(self.list_container, text="No pledge loans found.", font=s.Styles.FONT_TINY, text_color="gray")
                    lbl.pack(pady=20)
                self.has_more = False
                self.loading_more = False
                return

            if len(rows) < limit:
                self.has_more = False

            def render_pledge_row(i, row):
                f = ctk.CTkFrame(self.list_container, fg_color=s.CARD_ALT if i % 2 == 0 else "transparent", height=45)
                f.pack(fill="x", pady=1)
                f.pack_propagate(False)
                
                ctk.CTkLabel(f, text=row[1], font=s.Styles.FONT_DEFAULT).place(relx=0.02, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(f, text=f"{row[2]}\n{row[3]}", font=s.Styles.FONT_TINY).place(relx=0.25, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(f, text=f"₹{row[4]:,.2f} ({row[5]}m)", font=s.Styles.FONT_DEFAULT).place(relx=0.48, rely=0.5, anchor="w", x=15)
                
                status_color = s.GREEN if row[6] == 'Active' else s.MUTED
                ctk.CTkLabel(f, text=row[6].upper(), font=s.Styles.FONT_TINY_BOLD, text_color=status_color).place(relx=0.68, rely=0.5, anchor="w", x=15)
                
                btn_f = ctk.CTkFrame(f, fg_color="transparent")
                btn_f.place(relx=0.78, rely=0.5, anchor="w", x=15)
                ctk.CTkButton(btn_f, text="👁", width=35, height=28, fg_color=s.PRIMARY, font=s.Styles.FONT_TINY, command=lambda lid=row[0]: self.view_loan(lid)).pack(side="left", padx=2)
                ctk.CTkButton(btn_f, text=t("edit"), width=60, height=28, fg_color=s.GOLD, font=s.Styles.FONT_TINY, text_color=s.NAVY_DARK, command=lambda lid=row[0]: self.edit_pledge_loan(lid)).pack(side="left", padx=2)
                ctk.CTkButton(btn_f, text=t("delete"), width=70, height=28, fg_color=s.RED, font=s.Styles.FONT_TINY, command=lambda lid=row[0]: self.delete_pledge_loan(lid)).pack(side="left", padx=2)

            def on_complete(count):
                if not self.winfo_exists(): return
                if self.has_more:
                    self.load_more_btn = ctk.CTkButton(self.list_container, text="Click to Load More Pledge Loans...", 
                                                      fg_color="transparent", text_color=s.PRIMARY,
                                                      hover_color=s.BORDER, font=s.Styles.FONT_SMALL_BOLD,
                                                      command=lambda: self.load_pledge_loans(append=True))
                    self.load_more_btn.pack(pady=20, fill="x")
                self.loading_more = False

            self.render_list_chunked(self.list_container, rows, render_pledge_row, 
                                   clear=not append, start_row_idx=offset, on_complete=on_complete)
            self.pledge_offset += len(rows)

        self.run_in_background(fetch, render)

    def view_loan(self, lid):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, 
                       l.loan_amount, l.loan_tenure, l.interest_rate, l.installment_amount, 
                       l.loan_date, l.down_payment, l.document_fee, l.loan_doc_path, l.due_beginning_date, l.status
                FROM loans l 
                JOIN customers c ON l.customer_id = c.id 
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone(); conn.close()
            if loan: ViewLoanWindow(self.winfo_toplevel(), loan, on_change=self.load_pledge_loans)
        except Exception as e: messagebox.showerror("Error", f"Error opening loan details: {e}")

    def edit_pledge_loan(self, lid):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("""
                SELECT l.customer_id, l.vehicle_id, l.loan_amount, l.loan_tenure, 
                       l.interest_rate, l.installment_amount, l.document_fee, 
                       l.loan_doc_path, v.vehicle_name, v.reg_number, v.model_year, v.purchase_price,
                       c.name, c.phone, l.due_beginning_date, l.loan_date, l.loan_number,
                       (SELECT account_id FROM transactions WHERE description LIKE 'Loan Disbursement: ' || IFNULL(l.loan_number, 'L-' || l.id) || '%') as aid
                FROM loans l
                JOIN customers c ON l.customer_id = c.id
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone()
            
            if loan:
                cid, vid, amt, tenure, rate, emi, doc_fee, d_path, v_name, reg, year, val, c_name, c_phone, due_date, saved_loan_date, loan_number, aid = loan
                self.edit_id = lid
                self.edit_vid = vid
                self.orig_amt = amt
                self.orig_doc_fee = doc_fee or 0
                self.orig_aid = aid
                self.orig_loan_number = loan_number if loan_number else f"L-{lid}"
                
                self.field_loan_number.delete(0, 'end')
                self.field_loan_number.insert(0, self.orig_loan_number)
            
            c_str = f"{c_name} (ID: {cid}, Mob: {c_phone or '-'})"
            if c_str not in self.field_customer.values:
                self.field_customer.configure_values(list(self.field_customer.values) + [c_str])
            self.customer_var.set(c_str)
            
            if vid:
                cursor.execute("SELECT mk.name, md.name FROM vehicles v JOIN makes mk ON v.make_id=mk.id JOIN models md ON v.model_id=md.id WHERE v.id=?", (vid,))
                v_res = cursor.fetchone()
                if v_res:
                    self.make_var.set(v_res[0])
                    self.load_models_for_make(v_res[0])
                    self.model_var.set(v_res[1])
                    
            self.reg_var.set(reg)
            if year: self.field_year.set(str(year))
            self.field_val.delete(0, 'end'); self.field_val.insert(0, str(val))
            
            self.field_amount.delete(0, 'end'); self.field_amount.insert(0, str(amt))
            self.field_tenure.delete(0, 'end'); self.field_tenure.insert(0, str(tenure))
            self.field_interest.delete(0, 'end'); self.field_interest.insert(0, str(rate))
            self.field_emi.delete(0, 'end'); self.field_emi.insert(0, str(emi))
            if saved_loan_date: self.field_loan_date.set_date(saved_loan_date)
            self.field_doc_fee.delete(0, 'end'); self.field_doc_fee.insert(0, str(doc_fee or 0))
            if due_date: self.field_due_date.set_date(due_date)
            
            if aid:
                for acc_str, loop_aid in self.account_map.items():
                    if loop_aid == aid:
                        self.acc_var.set(acc_str)
                        break
                        
            if d_path:
                self.signed_doc_path.set(d_path)
                self.btn_upload.configure(fg_color=s.GREEN, text="✅ Document Selected")
            
            self.save_btn.configure(text="UPDATE PLEDGE")
            self.form_container.master.yview_moveto(0) if hasattr(self.form_container.master, 'yview_moveto') else None
            messagebox.showinfo("Edit Mode", "Loan data loaded. Financial impacts will be auto-corrected on update.")
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load pledge loan: {e}")

    def delete_pledge_loan(self, lid):
        def proceed_delete():
            if messagebox.askyesno("Confirm", "Delete this RC Pledge Loan record? This will revert financial transactions and delete the pledge vehicle record."):
                try:
                    conn = get_connection(); cursor = conn.cursor()
                    cursor.execute("SELECT vehicle_id, loan_amount, document_fee, loan_number FROM loans WHERE id=?", (lid,))
                    loan = cursor.fetchone()
                    if not loan: return
                    vid, amt, doc_fee, loan_number = loan
                    ln_str = loan_number if loan_number else f"L-{lid}"
                    
                    cursor.execute("SELECT account_id FROM transactions WHERE description LIKE ?", (f"Loan Disbursement: {ln_str}%",))
                    tx = cursor.fetchone()
                    if tx:
                        aid = tx[0]
                        cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amt, aid))
                        cursor.execute("DELETE FROM transactions WHERE description LIKE ?", (f"Loan Disbursement: {ln_str}%",))
                    
                    if doc_fee and doc_fee > 0:
                        cursor.execute("SELECT account_id FROM transactions WHERE description = ?", (f"Document Fee: {ln_str}",))
                        tx_doc = cursor.fetchone()
                        if tx_doc:
                            aid_doc = tx_doc[0]
                            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (doc_fee, aid_doc))
                            cursor.execute("DELETE FROM transactions WHERE description = ?", (f"Document Fee: L-{lid}",))
                    
                    cursor.execute("DELETE FROM loans WHERE id=?", (lid,))
                    if vid:
                        cursor.execute("DELETE FROM vehicles WHERE id=?", (vid,))
                    
                    conn.commit(); conn.close()
                    ActivationManager.invalidate_cache()
                    messagebox.showinfo("Success", "RC Pledge Loan deleted successfully.")
                    self.clear_form()
                    self.load_pledge_loans()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete loan: {e}")

        PasswordDialog(self.winfo_toplevel(), on_success=proceed_delete)

    def clear_form(self):
        self.edit_id = None
        self.field_customer.set(""); self.make_var.set(""); self.model_var.set(""); self.reg_var.set("")
        self.field_val.delete(0, 'end'); self.field_amount.delete(0, 'end'); self.field_tenure.delete(0, 'end')
        self.field_interest.delete(0, 'end'); self.field_emi.delete(0, 'end'); self.field_doc_fee.delete(0, 'end')
        self.acc_var.set("Select Account..."); self.signed_doc_path.set("")
        self.btn_upload.configure(fg_color=s.PRIMARY, text="📄 " + t("signed_docs"))
        self.save_btn.configure(text=t("save_pledge"))
        self.load_next_loan_number()

    def load_next_loan_number(self):
        try:
            conn = get_connection(); c = conn.cursor()
            c.execute("SELECT seq FROM sqlite_sequence WHERE name='loans'")
            res = c.fetchone()
            conn.close()
            next_id = int(res[0]) + 1 if res else 1
            self.field_loan_number.delete(0, 'end')
            self.field_loan_number.insert(0, f"L-{next_id}")
        except: pass

class ReportPrintWindow:
    def __init__(self, master, report_title, headers, data, **kwargs):
        self.generate_html_report(report_title, headers, data)
        
    def generate_html_report(self, title, headers, data):
        try:
            from datetime import datetime
            import tempfile
            import webbrowser
            import os

            # Generate Table Headers
            header_html = "".join([f"<th>{h}</th>" for h in headers])
            
            # Generate Table Rows
            rows_html = ""
            for row in data:
                rows_html += "<tr>"
                for cell in row:
                    val = str(cell) if cell is not None else "-"
                    rows_html += f"<td>{val}</td>"
                rows_html += "</tr>"

            current_time = datetime.now().strftime('%d-%m-%Y %I:%M %p')
            username = "System"
            # Try to get username from master app
            try:
                # master is usually the main app or a parent widget
                current_widget = tk._default_root if not hasattr(tk, '_default_root') else None
                # In this app structure, winfo_toplevel() usually has current_username
                # We'll try to find it
                import tkinter as tk
                # The master passed is usually the root window
                username = getattr(tk._default_root, 'current_username', 'System')
            except: pass

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Report - {title}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 40px; background-color: #f8fafc; color: #1e293b; }}
                    .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-top: 8px solid #0f172a; }}
                    .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #f1f5f9; padding-bottom: 20px; }}
                    .header h1 {{ margin: 0; color: #0f172a; font-size: 28px; letter-spacing: -0.025em; }}
                    .header p {{ margin: 5px 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; }}
                    .report-info {{ display: flex; justify-content: space-between; margin-bottom: 20px; font-size: 13px; color: #475569; font-weight: 600; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th {{ background-color: #0f172a; color: white; text-align: left; padding: 12px 15px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
                    td {{ padding: 12px 15px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
                    tr:nth-child(even) {{ background-color: #f8fafc; }}
                    .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #f1f5f9; text-align: center; font-size: 11px; color: #64748b; }}
                    @media print {{
                        body {{ background: white; padding: 0; }}
                        .container {{ box-shadow: none; max-width: 100%; width: 100%; padding: 20px; border: none; }}
                        .no-print {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{get_company_name()}</h1>
                        <p>{get_company_address()}</p>
                        <p>Contact: {get_company_contact()}</p>
                    </div>
                    
                    <div class="report-info">
                        <span>REPORT: {title.upper()}</span>
                        <span>GENERATED ON: {current_time}</span>
                    </div>
                    
                    <table>
                        <thead>
                            <tr>{header_html}</tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                    
                    <div class="footer">
                        <p>This is a system-generated report. Generated by: {username} | {get_company_name()} Software</p>
                    </div>
                </div>
                
                <div class="no-print" style="text-align:center; margin-top:30px;">
                    <button onclick="window.print()" style="padding:12px 24px; background:#0f172a; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        🖨️ Click to Print Report
                    </button>
                </div>
            </body>
            </html>
            """
            
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open('file://' + os.path.realpath(temp_path))
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to generate HTML report: {e}")

class ReportsTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("reports"), **kwargs)
        
        # --- Filter Card ---
        self.filter_card, self.filter_inner = self.create_card("Report Generation Filters")
        
        # 1. Row 1: Report Type, From Date, To Date, Fetch Button
        # We start from row 1 because row 0 is used by the section title in create_card
        
        self.report_type, self.report_type_var = self.create_select(self.filter_inner, "Select Report Type", 
                                                                    ["Vehicle Log", "In-house Stock", "Sales Report", "Collection Report", "Active Loans", "Closed Loans", "Transaction History", "Customer List", "Day End Closures"], 1, 0)
        
        self.date_from = self.create_date_picker(self.filter_inner, "From Date", 1, 1)
        self.date_to = self.create_date_picker(self.filter_inner, "To Date", 1, 2)
        
        self.btn_fetch = ctk.CTkButton(self.filter_inner, text="🔍 Generate Report", height=35, fg_color=s.GOLD, 
                                        hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD, command=self.generate_report)
        self.btn_fetch.grid(row=1, column=3, padx=10, pady=(22, 10), sticky="ew")
        
        # Configure columns to distribute space
        for i in range(4):
            self.filter_inner.grid_columnconfigure(i, weight=1)
            
        self.btn_print = ctk.CTkButton(self.filter_inner, text="🖨️ Shoot / Print", height=35, fg_color=s.NAVY, 
                                        hover_color=s.BORDER, font=s.Styles.FONT_BOLD, command=self.print_report)
        self.btn_print.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        
        # Results Section
        self.results_header = ctk.CTkLabel(self, text="Report Results", font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.results_header.pack(pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG, anchor="w")
        
        self.results_container = ctk.CTkFrame(self, fg_color="transparent")
        self.results_container.pack(fill="both", expand=True, padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        self.current_headers = []
        self.current_data = []
        self.current_loan_ids = []
        self.current_report_type = ""

        
    def generate_report(self):
        r_type = self.report_type.get()
        self.current_report_type = r_type
        self.current_loan_ids = []
        d_from = self.date_from.get()
        d_to = self.date_to.get()
        
        # Clear results
        for w in self.results_container.winfo_children(): w.destroy()
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            if r_type == "Vehicle Log":
                self.current_headers = ["VEHICLE NAME", "REG NO", "PURCHASE PRICE", "STATUS"]
                cursor.execute("""
                    SELECT 
                        COALESCE(mk.name || ' ' || md.name, v.vehicle_name) as display_name, 
                        v.reg_number, v.purchase_price, v.status 
                    FROM vehicles v
                    LEFT JOIN makes mk ON v.make_id = mk.id
                    LEFT JOIN models md ON v.model_id = md.id
                    ORDER BY v.created_at DESC
                """)
                self.current_data = cursor.fetchall()
                
            elif r_type == "In-house Stock":
                self.current_headers = ["VEHICLE MODEL", "STOCK COUNT", "TOTAL VALUE"]
                cursor.execute("""
                    SELECT 
                        COALESCE(mk.name || ' ' || md.name, v.vehicle_name) as display_name, 
                        COUNT(*) as count,
                        SUM(COALESCE(v.purchase_price, 0)) as total_val
                    FROM vehicles v
                    LEFT JOIN makes mk ON v.make_id = mk.id
                    LEFT JOIN models md ON v.model_id = md.id
                    WHERE v.status = 'Available' 
                    GROUP BY display_name
                    ORDER BY count DESC
                """)
                raw_data = cursor.fetchall()
                data = []
                for rd in raw_data:
                    display_name, count, t_val = rd
                    data.append((display_name, count, format_indian_currency(t_val)))
                
                total_count = sum(rd[1] for rd in raw_data)
                total_value = sum(rd[2] for rd in raw_data)
                
                if data:
                    data.append(("---", "---", "---"))
                    data.append(("TOTAL IN-HOUSE STOCK", total_count, format_indian_currency(total_value)))
                self.current_data = data

            elif r_type == "Active Loans":
                self.current_headers = ["CUSTOMER", "LOAN AMT", "TENURE", "EMI", "PAID AMT", "OUT. CAPITAL", "OUT. AMOUNT", "DATE"]
                
                def date_sql(col):
                    return f"substr({col}, 7, 4) || '-' || substr({col}, 4, 2) || '-' || substr({col}, 1, 2)"
                
                s_iso = f"{d_from[6:10]}-{d_from[3:5]}-{d_from[0:2]}" if d_from and len(d_from) == 10 else None
                e_iso = f"{d_to[6:10]}-{d_to[3:5]}-{d_to[0:2]}" if d_to and len(d_to) == 10 else None
                
                query = """
                    SELECT l.id, COALESCE(c.name, '[No Customer - Orphaned]'), l.loan_amount, l.loan_tenure, l.installment_amount, l.loan_date,
                    COALESCE((SELECT SUM(amount - penalty_amount) FROM payments WHERE loan_id = l.id), 0) as paid_amount
                    FROM loans l LEFT JOIN customers c ON l.customer_id = c.id 
                    WHERE l.status='Active'
                """
                params = []
                if s_iso and e_iso:
                    query += f" AND {date_sql('l.loan_date')} BETWEEN ? AND ?"
                    params = [s_iso, e_iso]
                    
                query += " ORDER BY l.created_at DESC"
                cursor.execute(query, params)
                raw_data = cursor.fetchall()
                loan_ids = []
                data = []
                total_paid = 0
                total_outstanding_capital = 0
                total_outstanding_amount = 0
                for rd in raw_data:
                    loan_amount = float(rd[2]) if rd[2] is not None else 0.0
                    tenure = int(rd[3]) if rd[3] is not None else 1
                    emi = float(rd[4]) if rd[4] is not None else 0.0
                    total_payable = emi * tenure
                    
                    rounded_emi = round(emi)
                    paid_amount = float(rd[6]) if rd[6] is not None else 0.0
                    outstanding_amount = max(0.0, total_payable - paid_amount)
                    
                    # Proportional unpaid principal (outstanding capital)
                    if total_payable > 0:
                        outstanding_capital = loan_amount * (outstanding_amount / total_payable)
                    else:
                        outstanding_capital = 0.0
                        
                    total_paid += paid_amount
                    total_outstanding_capital += outstanding_capital
                    total_outstanding_amount += outstanding_amount
                    
                    loan_ids.append(rd[0])  # store loan ID
                    data.append((
                        rd[1], 
                        format_indian_currency(loan_amount), 
                        rd[3], 
                        format_indian_currency(rounded_emi), 
                        format_indian_currency(paid_amount),
                        format_indian_currency(outstanding_capital), 
                        format_indian_currency(outstanding_amount), 
                        rd[5]
                    ))
                
                if data:
                    data.append(("---", "---", "---", "---", "---", "---", "---", "---"))
                    data.append((
                        "TOTAL ACTIVE LOANS", 
                        "", 
                        f"{len(data)-1} Cases", 
                        "", 
                        format_indian_currency(total_paid),
                        format_indian_currency(total_outstanding_capital), 
                        format_indian_currency(total_outstanding_amount), 
                        ""
                    ))
                
                self.current_data = data
                self.current_loan_ids = loan_ids

            elif r_type == "Closed Loans":
                self.current_headers = ["CUSTOMER", "LOAN AMT", "TENURE", "EMI", "LOAN DATE", "CLOSED ON"]
                cursor.execute("""
                    SELECT c.name, l.loan_amount, l.loan_tenure, l.installment_amount, l.loan_date, l.closed_date
                    FROM loans l JOIN customers c ON l.customer_id = c.id 
                    WHERE l.status='Closed' ORDER BY l.closed_date DESC
                """)
                raw_data = cursor.fetchall()
                data = []
                for rd in raw_data:
                    rounded_emi = round(float(rd[3])) if rd[3] is not None else 0
                    data.append((rd[0], format_indian_currency(rd[1]), rd[2], format_indian_currency(rounded_emi), rd[4] or "-", rd[5] or "-"))
                self.current_data = data
                
            elif r_type == "Transaction History":
                self.current_headers = ["DATE", "ACCOUNT", "TYPE", "DESC", "AMOUNT"]
                cursor.execute("""
                    SELECT t.transaction_date, a.name, t.transaction_type, t.description, t.amount 
                    FROM transactions t JOIN accounts a ON t.account_id = a.id 
                    ORDER BY t.transaction_date DESC
                """)
                self.current_data = cursor.fetchall()
                
            elif r_type == "Customer List":
                self.current_headers = ["NAME", "PHONE", "CITY", "BALANCE"]
                cursor.execute("SELECT name, phone, city, balance FROM customers ORDER BY name")
                self.current_data = cursor.fetchall()
                
            elif r_type == "Sales Report":
                self.current_headers = ["DATE", "VEHICLE", "REG NO", "CUSTOMER", "SALE PRICE"]
                
                # Date filtering helper
                def date_sql(col):
                    return f"substr({col}, 7, 4) || '-' || substr({col}, 4, 2) || '-' || substr({col}, 1, 2)"
                
                s_iso = f"{d_from[6:10]}-{d_from[3:5]}-{d_from[0:2]}" if d_from else None
                e_iso = f"{d_to[6:10]}-{d_to[3:5]}-{d_to[0:2]}" if d_to else None
                
                query = """
                    SELECT v.sale_date, COALESCE(mk.name || ' ' || md.name, v.vehicle_name), v.reg_number, COALESCE(c.name, 'N/A'), v.sale_price
                    FROM vehicles v
                    LEFT JOIN customers c ON v.customer_id = c.id
                    LEFT JOIN makes mk ON v.make_id = mk.id
                    LEFT JOIN models md ON v.model_id = md.id
                    WHERE v.status = 'Sold'
                """
                params = []
                if s_iso and e_iso:
                    query += f" AND {date_sql('v.sale_date')} BETWEEN ? AND ?"
                    params = [s_iso, e_iso]
                
                query += " ORDER BY " + date_sql('v.sale_date') + " DESC"
                cursor.execute(query, params)
                raw_data = cursor.fetchall()
                data = []
                for rd in raw_data:
                    data.append((rd[0], rd[1], rd[2], rd[3], format_indian_currency(rd[4] or 0)))
                self.current_data = data

            elif r_type == "Day End Closures":
                self.current_headers = ["REPORT NO", "DATE", "CASH", "ASSETS", "USER"]
                cursor.execute("SELECT report_number, closure_date, closing_cash, total_assets, closed_by FROM day_closures ORDER BY timestamp DESC")
                self.current_data = cursor.fetchall()

            elif r_type == "Collection Report":
                self.current_headers = ["DATE", "CUSTOMER", "LOAN NO", "TYPE", "EMI NOS", "AMOUNT"]
                
                def date_sql(col):
                    return f"substr({col}, 7, 4) || '-' || substr({col}, 4, 2) || '-' || substr({col}, 1, 2)"
                
                s_iso = f"{d_from[6:10]}-{d_from[3:5]}-{d_from[0:2]}" if d_from else None
                e_iso = f"{d_to[6:10]}-{d_to[3:5]}-{d_to[0:2]}" if d_to else None
                
                query = f"""
                    SELECT p.payment_date, COALESCE(c.name, 'N/A'), COALESCE(l.loan_number, 'L-' || l.id),
                           CASE WHEN v.status = 'Pledge' THEN 'RC Pledge' ELSE 'Loan' END as loan_type,
                           p.emi_numbers, p.amount
                    FROM payments p
                    JOIN loans l ON p.loan_id = l.id
                    JOIN customers c ON l.customer_id = c.id
                    LEFT JOIN vehicles v ON l.vehicle_id = v.id
                    WHERE 1=1
                """
                params = []
                if s_iso and e_iso:
                    query += f" AND {date_sql('p.payment_date')} BETWEEN ? AND ?"
                    params = [s_iso, e_iso]
                
                query += f" ORDER BY {date_sql('p.payment_date')} DESC, p.created_at DESC"
                cursor.execute(query, params)
                raw_data = cursor.fetchall()
                data = []
                total_collected = 0
                for rd in raw_data:
                    total_collected += rd[5] or 0
                    data.append((rd[0], rd[1], rd[2], rd[3], rd[4] or "-", format_indian_currency(rd[5] or 0)))
                
                if data:
                    data.append(("---", "---", "---", "---", "---", "---"))
                    data.append(("TOTAL COLLECTION", "", "", "", "", format_indian_currency(total_collected)))
                self.current_data = data
                
            conn.close()
            self.render_results()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")

    def render_results(self):
        is_active_loans = self.current_report_type == "Active Loans"
        
        if not self.current_data:
            ctk.CTkLabel(self.results_container, text="No data found for the selected criteria.", font=s.Styles.FONT_DEFAULT).pack(pady=40)
            return
            
        # Table Header
        t_head = ctk.CTkFrame(self.results_container, fg_color=s.NAVY_DARK, height=40, corner_radius=s.Styles.RADIUS)
        t_head.pack(fill="x", pady=(0, 5))
        t_head.pack_propagate(False)
        
        n_cols = len(self.current_headers)
        if n_cols == 4:
            col_widths = [0.35, 0.25, 0.2, 0.2]
        elif n_cols == 5:
            if self.current_report_type == "Sales Report":
                # Date, Vehicle, Reg, Customer, Amount
                col_widths = [0.15, 0.25, 0.15, 0.25, 0.2]
            else:
                # Date, Account, Type, Desc, Amount (Transaction History/Closures)
                col_widths = [0.15, 0.15, 0.1, 0.45, 0.15]
        elif n_cols == 8 and is_active_loans:
            col_widths = [0.15, 0.12, 0.06, 0.11, 0.13, 0.14, 0.14, 0.15]
        elif n_cols == 6 and is_active_loans:
            col_widths = [0.22, 0.18, 0.08, 0.15, 0.18, 0.19]
        elif n_cols == 6 and self.current_report_type == "Collection Report":
            # Date, Customer, Loan No, Type, EMI Nos, Amount
            col_widths = [0.12, 0.25, 0.13, 0.15, 0.2, 0.15]
        elif n_cols == 6:
            col_widths = [0.22, 0.18, 0.1, 0.15, 0.18, 0.17]
        else:
            col_widths = [1.0 / n_cols] * n_cols

        # Show column headers (hide ACTION header label — replaced by button)
        current_x = 0.0
        for i, h in enumerate(self.current_headers):
            if h == "ACTION":
                current_x += col_widths[i]
                continue
            ctk.CTkLabel(t_head, text=h, font=s.Styles.FONT_TINY_BOLD, text_color="white").place(relx=current_x, rely=0.5, anchor="w", x=15)
            current_x += col_widths[i]
            
        # Rows
        for i, row_data in enumerate(self.current_data):
            row_f = ctk.CTkFrame(self.results_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=0)
            row_f.pack(fill="x")
            row_f.pack_propagate(False)
            
            row_x = 0.0
            for j, val in enumerate(row_data):
                txt = str(val) if val is not None else "-"
                ctk.CTkLabel(row_f, text=txt, font=s.Styles.FONT_SMALL).place(relx=row_x, rely=0.5, anchor="w", x=15)
                row_x += col_widths[j]

    def close_loan(self, loan_id):
        if not messagebox.askyesno("Close Loan", 
            f"Are you sure you want to mark Loan #{loan_id} as CLOSED?\n\n"
            "This will change the loan status to 'Closed'. This action cannot be undone easily."):
            return
        try:
            from datetime import datetime as dt
            conn = get_connection()
            cursor = conn.cursor()
            today = dt.now().strftime("%d-%m-%Y")
            cursor.execute("""
                UPDATE loans SET status='Closed', closed_date=? WHERE id=?
            """, (today, loan_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Loan #{loan_id} has been marked as CLOSED.")
            self.generate_report()  # Refresh the report
        except Exception as e:
            messagebox.showerror("Error", f"Failed to close loan: {e}")

    def print_report(self):
        if not self.current_data:
            messagebox.showwarning("Warning", "Please generate a report first!")
            return
        ReportPrintWindow(self.winfo_toplevel(), self.report_type.get(), self.current_headers, self.current_data)

class PaymentsTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("emi_collection"), **kwargs)
        self.loan_map = {}
        self.account_map = {}
        self.selected_loan_id = None
        
        # --- Payment Form Card ---
        self.form_card, self.form = self.create_card(t("emi_payment_entry"))
        
        # Row 1: Loan Selection & Date
        self.field_loan, self.loan_var = self.create_searchable_select(self.form, t("loans_menu"), [], 1, 0, columnspan=2)
        self.loan_var.trace_add("write", self.update_loan_details_display)
        self.field_date = self.create_date_picker(self.form, t("date"), 1, 2, default_date=datetime.now())
        
        # Internal state for calculations
        self.overdue_count = 0
        self.total_penalty = 0
        
        # Row 2: Penalty Rate & Penalty Amount & Total Amount
        self.field_penalty_rate = self.create_input(self.form, "Penalty per EMI (₹)", 2, 0)
        self.field_penalty_rate.insert(0, "300")
        self.field_penalty_rate.configure(state="disabled")
        self.field_penalty_rate.bind("<KeyRelease>", self.update_penalty_calculation)

        self.field_penalty_total_input = self.create_input(self.form, "Penalty Amount (₹)", 2, 1)
        self.field_penalty_total_input.bind("<KeyRelease>", self.on_penalty_total_changed)
        
        self.field_amount = self.create_input(self.form, t("amount") + " (EMI)", 2, 2)
        
        # Row 3: Account, Use Credit, Remarks
        self.field_acc, self.acc_var = self.create_select(self.form, t("account"), [], 3, 0)
        
        self.use_credit_var = ctk.BooleanVar(value=False)
        self.cb_use_credit = ctk.CTkCheckBox(self.form, text="Use Customer Credit", variable=self.use_credit_var, 
                                            command=self.toggle_credit_usage, font=s.Styles.FONT_TINY_BOLD,
                                            text_color=s.PRIMARY)
        self.cb_use_credit.grid(row=3, column=1, padx=15, sticky="w")
        
        self.field_remarks = self.create_input(self.form, t("remarks"), 3, 2)
        
        # Internal state for installment selection
        self.due_vars = [] # List of (var, amount, is_overdue)
        self.selected_emi_count = 0
        self.selected_overdue_count = 0
        self.selected_penalty_total = 0
        self.current_customer_balance = 0
        self.current_customer_id = None
        
        self.form.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Summary Box

        self.summary_card = ctk.CTkFrame(self.form, fg_color="#f8fafc", corner_radius=8, border_width=1, border_color="#e2e8f0")
        self.summary_card.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        self.sum_label = ctk.CTkLabel(self.summary_card, text=t("loan_details"), font=s.Styles.FONT_SMALL, justify="left")
        self.sum_label.pack(padx=20, pady=15)
        
        # Dues Visualization Section
        self.dues_header = ctk.CTkLabel(self.form, text=t("overdue_dues"), font=s.Styles.FONT_BOLD, text_color=s.NAVY)
        self.dues_header.grid(row=5, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")
        
        self.dues_container = ctk.CTkScrollableFrame(self.form, height=130, fg_color="transparent", orientation="horizontal")
        self.dues_container.grid(row=6, column=0, columnspan=3, padx=0, pady=(0, 20), sticky="ew")

        
        # Action Buttons
        btn_row = ctk.CTkFrame(self.form, fg_color="transparent")
        btn_row.grid(row=7, column=0, columnspan=3, pady=(0, 10))

        self.pay_btn = ctk.CTkButton(btn_row, text="💳 " + t("record_payment"), height=45, width=180, 
                                      fg_color=s.GREEN, hover_color="#059669", font=s.Styles.FONT_BOLD,
                                      command=self.process_payment)
        self.pay_btn.pack(side="left", padx=10)

        self.preclose_btn = ctk.CTkButton(btn_row, text="🔒 " + "Pre-close Loan", height=45, width=180, 
                                          fg_color=s.RED, hover_color="#e11d48", font=s.Styles.FONT_BOLD,
                                          command=self.open_preclosure_dialog)
        self.preclose_btn.pack(side="left", padx=10)

        
        # --- History Section ---
        self.history_header = ctk.CTkLabel(self, text="Recent EMI Collections", font=s.Styles.FONT_H2, text_color=s.TEXT)
        self.history_header.pack(pady=(s.PAD_LG, s.PAD_SM), padx=s.PAD_LG, anchor="w")
        
        self.history_container = ctk.CTkFrame(self, fg_color="transparent")
        self.history_container.pack(fill="x", padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        # Lazy Loading State
        self.payment_offset = 0
        self.has_more = True
        self.loading_more = False
        
        # Bind scroll events
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind("<Configure>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<MouseWheel>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-4>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-5>", lambda e: self.check_scroll(), add="+")

        # State for editing
        self.edit_payment_id = None
        self.old_payment_amt = 0
        self.old_account_id = None
        self.old_description = ""
        self.old_date = ""
        self.editing_emi_indices = set()

        self.load_active_loans()
        self.load_accounts()
        self.load_recent_payments()

    # Redundant helper methods removed (using BaseTab versions)


    def load_active_loans(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, v.reg_number, l.installment_amount 
                FROM loans l 
                JOIN customers c ON l.customer_id = c.id
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.status = 'Active' ORDER BY l.created_at DESC
            """)
            loans = cursor.fetchall()
            conn.close()
            
            # Use fallback 0 if installment_amount is None to avoid formatting crash
            self.loan_map = {f"{r[1]} - {r[2] or 'N/A'} (EMI: ₹{(r[3] or 0):,.2f})": r[0] for r in loans}
            
            val_list = list(self.loan_map.keys())
            if not val_list:
                if hasattr(self.field_loan, 'configure_values'):
                    self.field_loan.configure_values(["No Active Loans Found"])
                else:
                    self.field_loan.configure(values=["No Active Loans Found"])
                self.loan_var.set("")
            else:
                if hasattr(self.field_loan, 'configure_values'):
                    self.field_loan.configure_values(val_list)
                else:
                    self.field_loan.configure(values=val_list)
                self.loan_var.set("")
        except Exception as e: 
            print(f"Error loading active loans: {e}")
            if hasattr(self.field_loan, 'configure_values'):
                self.field_loan.configure_values(["Error loading loans"])
            else:
                self.field_loan.configure(values=["Error loading loans"])

    def load_accounts(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = cursor.fetchall()
            conn.close()
            # Handle NULL balances with default 0
            self.account_map = {f"{r[1]} ({format_indian_currency(r[2] or 0)})": r[0] for r in accounts}
            acc_list = list(self.account_map.keys())
            self.field_acc.configure(values=acc_list)
            for name in acc_list:
                if "Shop Cash" in name: 
                    self.acc_var.set(name)
                    break
        except Exception as e:
            print(f"Error loading accounts: {e}")
            self.field_acc.configure(values=["Error loading accounts"])

    def on_loan_selected(self, val):
        lid = self.loan_map.get(val)
        if lid:
            # Re-triggering refresh of details (which handles emi field)
            self.update_loan_details_display()

    def update_loan_details_display(self, *args):
        val = self.loan_var.get()
        lid = self.loan_map.get(val)
        self.selected_loan_id = lid
        if lid:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT l.loan_amount, l.loan_tenure, l.installment_amount, l.due_beginning_date,
                           (SELECT SUM(amount) FROM payments WHERE loan_id = l.id),
                           c.balance, c.name, c.id
                    FROM loans l 
                    JOIN customers c ON l.customer_id = c.id
                    WHERE l.id = ?
                """, (lid,))
                loan = cursor.fetchone()
                
                # Fetch all payments to get emi_numbers
                cursor.execute("SELECT payment_date, amount, emi_numbers FROM payments WHERE loan_id = ? ORDER BY created_at", (lid,))
                payments_data = cursor.fetchall()
                
                conn.close()
                if loan:
                    amt, tenure, emi, due_start, paid_amt, cust_balance, cust_name, cust_id = loan
                    amt = amt or 0
                    tenure = tenure or 0
                    emi = emi or 0
                    paid_amt = paid_amt or 0
                    self.current_customer_balance = cust_balance or 0
                    self.current_customer_id = cust_id
                    
                    # Parse paid indices from emi_numbers
                    paid_indices = set()
                    emi_to_date = {}
                    for p_date, p_amt, p_emis in payments_data:
                        if p_emis:
                            parts = p_emis.split(",")
                            for part in parts:
                                try:
                                    idx_str = part.strip().replace("E", "")
                                    if idx_str:
                                        idx = int(idx_str) - 1
                                        paid_indices.add(idx)
                                        emi_to_date[idx] = p_date
                                except: pass
                    
                    # Fallback for old records without emi_numbers: assume they are sequential E1, E2...
                    if not paid_indices and payments_data:
                        for idx in range(len(payments_data)):
                            paid_indices.add(idx)
                            emi_to_date[idx] = payments_data[idx][0]
                            
                    count = len(paid_indices)
                    
                    # Reset dynamic selection state
                    self.due_vars = []
                    
                    # Calculate overdues
                    try:
                        start_dt = datetime.strptime(due_start, "%d-%m-%Y") if due_start else datetime.now()
                    except:
                        start_dt = datetime.now()
                    
                    self.overdue_count = 0
                    now = datetime.now().date()
                    for i in range(tenure):
                        month = (start_dt.month + i - 1) % 12 + 1
                        year = start_dt.year + (start_dt.month + i - 1) // 12
                        
                        try:
                            # Use same logic as the grid boxes below
                            due_date_obj = datetime(year, month, min(start_dt.day, 28)).date()
                            if start_dt.day > 28:
                                import calendar
                                last_day = calendar.monthrange(year, month)[1]
                                due_date_obj = datetime(year, month, min(start_dt.day, last_day)).date()
                        except:
                            due_date_obj = now
                            
                        if due_date_obj < now:
                            # This installment's due date has passed
                            if i not in paid_indices: # It hasn't been paid yet
                                self.overdue_count += 1
                                
                    # Update Penalty Calculation
                    self.update_penalty_calculation()
                    
                    # Disable penalty input if no overdues
                    if self.overdue_count == 0:
                        self.field_penalty_rate.configure(state="disabled")
                        self.field_penalty_total_input.delete(0, 'end')
                        self.field_penalty_total_input.insert(0, "0")
                        self.field_penalty_total_input.configure(state="disabled")
                    else:
                        self.field_penalty_rate.configure(state="normal")
                        self.field_penalty_total_input.configure(state="normal")
                    
                    self.sum_label.configure(text=(
                        f"📌 Loan Summary:\nTotal Amount: {format_indian_currency(amt)} | Tenure: {tenure} Months\n"
                        f"EMI: {format_indian_currency(emi)} | Installments Paid: {count}\n"
                        f"Total Paid: {format_indian_currency(paid_amt)} | Approx. Balance: {format_indian_currency(max(0, amt - paid_amt))}\n"
                        f"⚠️ Overdue EMIs: {self.overdue_count} | Total Penalty: {format_indian_currency(self.total_penalty)}\n"
                        f"💰 Customer Credit Balance: {format_indian_currency(self.current_customer_balance)}"
                    ))
                    
                    # We no longer automatically fill the field_amount here.
                    # This will be handled by the update_amount_from_selection() called later in the method.

                    
                    # Render Dues Boxes
                    for w in self.dues_container.winfo_children(): w.destroy()
                    
                    for i in range(tenure):
                        # Calculate installment date
                        month = (start_dt.month + i - 1) % 12 + 1
                        year = start_dt.year + (start_dt.month + i - 1) // 12
                        due_date_str = f"{start_dt.day:02d}-{month:02d}-{year}"
                        
                        # Calculate exactly for comparison
                        try:
                            due_date_obj = datetime(year, month, min(start_dt.day, 28)) 
                            if start_dt.day > 28:
                                import calendar
                                last_day = calendar.monthrange(year, month)[1]
                                due_date_obj = datetime(year, month, min(start_dt.day, last_day))
                        except:
                            due_date_obj = datetime.now()
                        
                        is_paid = i in paid_indices
                        pay_date = emi_to_date.get(i)
                        is_overdue = not is_paid and due_date_obj.date() < datetime.now().date()
                        
                        box_color = s.GREEN if is_paid else s.RED if is_overdue else "#f1f5f9"
                        text_color = "white" if (is_paid or is_overdue) else s.TEXT
                        
                        box = ctk.CTkFrame(self.dues_container, width=75, height=95, fg_color=box_color, corner_radius=6)
                        box.pack(side="left", padx=2, pady=5)
                        box.pack_propagate(False)
                        
                        # Add Checkbox if not paid or being edited
                        can_edit = (not is_paid) or (self.edit_payment_id is not None and i in self.editing_emi_indices)
                        if can_edit:
                            is_checked = (i in self.editing_emi_indices) if self.edit_payment_id else (i == count)
                            var = ctk.BooleanVar(value=is_checked)
                            cb = ctk.CTkCheckBox(box, text="", variable=var, width=20, height=20, 
                                                command=self.update_amount_from_selection,
                                                checkbox_width=18, checkbox_height=18, border_width=1)
                            cb.pack(pady=(2,0))
                            self.due_vars.append((var, emi, is_overdue, i+1))  # Add EMI number
                        else:
                            # Placeholder for alignment
                            ctk.CTkLabel(box, text="✅", font=("Poppins", 10), text_color="white").pack(pady=(2,0))

                        ctk.CTkLabel(box, text=f"E{i+1}", font=("Poppins", 9, "bold"), text_color=text_color).pack()
                        ctk.CTkLabel(box, text=due_date_str[:5], font=("Poppins", 8), text_color=text_color).pack()
                        
                        if is_paid:
                            ctk.CTkLabel(box, text="PAID", font=("Poppins", 8, "bold"), text_color="white").pack()
                            ctk.CTkLabel(box, text=pay_date[:5] if pay_date else "", font=("Poppins", 7), text_color="white").pack()
                        elif is_overdue:
                            ctk.CTkLabel(box, text="DUE", font=("Poppins", 8, "bold"), text_color="white").pack()
                            ctk.CTkLabel(box, text=format_indian_currency(emi), font=("Poppins", 8), text_color="white").pack()
                        else:
                            ctk.CTkLabel(box, text=format_indian_currency(emi), font=("Poppins", 8), text_color=s.MUTED).pack()
                            
                    # Initial calculation based on auto-ticked box
                    self.update_amount_from_selection()
                    
            except Exception as e: print(f"Error updating dues display: {e}")
        else:
            # No loan selected
            self.field_penalty_rate.configure(state="disabled")
            self.field_penalty_total_input.configure(state="disabled")
            self.sum_label.configure(text=t("select_loan_to_view_details"))
            for w in self.dues_container.winfo_children(): w.destroy()

    def update_amount_from_selection(self):
        try:
            # Get current penalty rate
            rate_str = self.field_penalty_rate.get().strip()
            rate = float(rate_str) if rate_str else 0
        except:
            rate = 0
            
        total_emi = 0
        total_pen = 0
        selected_count = 0
        selected_overdue_count = 0
        
        for var, emi_amt, is_overdue, emi_num in self.due_vars:
            if var.get():
                total_emi += emi_amt
                selected_count += 1
                if is_overdue:
                    total_pen += rate
                    selected_overdue_count += 1
                    
        self.selected_emi_count = selected_count
        self.selected_overdue_count = selected_overdue_count
        
        # Refresh Penalty Total field based on selection
        self.field_penalty_total_input.delete(0, 'end')
        self.field_penalty_total_input.insert(0, str(int(total_pen)))
        
        self.selected_penalty_total = total_pen
        total_payable = total_emi + total_pen
        
        # Apply Customer Credit if switched ON
        if self.use_credit_var.get():
            total_payable = max(0, total_payable - self.current_customer_balance)
            
        # Update Amount Field
        self.field_amount.delete(0, 'end')
        self.field_amount.insert(0, str(int(total_payable)))
        
        # Update the summary labels to show EXACT penalty for SELECTED boxes
        # Calculate overall overdues for labels
        # (This keeps the standard "⚠️ Overdue EMIs" label accurate but we can highlight SELECTION)
        if self.loan_var.get() != t("select") + "...":
            try:
                txt = self.sum_label.cget("text")
                if "Selected:" in txt:
                    # Remove previous Selection line to refresh
                    lines = txt.split("\n")
                    lines = [l for l in lines if "Selected:" not in l]
                    txt = "\n".join(lines)
                
                # Append Selection Summary
                summary_line = f"✅ Selected: {selected_count} Months | Total Payable: {format_indian_currency(total_payable)}"
                self.sum_label.configure(text=txt + "\n" + summary_line)
            except: pass
            
    def update_penalty_calculation(self, *args):
        try:
            rate_str = self.field_penalty_rate.get().strip()
            rate = float(rate_str) if rate_str else 0
        except ValueError:
            rate = 0
            
        self.total_penalty = self.overdue_count * rate
        
        # Update summary text
        if self.loan_var.get() != t("select") + "...":
            try:
                txt = self.sum_label.cget("text")
                if "Total Penalty:" in txt:
                    lines = txt.split("\n")
                    # Ensure we preserve formatting and only update the last line containing the penalty
                    for idx, line in enumerate(lines):
                        if "Total Penalty:" in line:
                            lines[idx] = f"⚠️ Overdue EMIs: {self.overdue_count} | Total Penalty: {format_indian_currency(self.total_penalty)}"
                            break
                    self.sum_label.configure(text="\n".join(lines))
            except: pass
            
        # Refresh the selection-based amount to reflect the new penalty rate
        self.update_amount_from_selection()

    def toggle_credit_usage(self):
        """Called when 'Use Customer Credit' checkbox is toggled"""
        self.update_amount_from_selection()

    def on_penalty_total_changed(self, *args):
        """Triggered when Penalty Amount is manually edited"""
        try:
            pen_str = self.field_penalty_total_input.get().strip()
            penalty = float(pen_str) if pen_str else 0
        except:
            penalty = 0
            
        self.selected_penalty_total = penalty
        
        # Calculate base EMI from selected boxes
        total_emi = 0
        for var, emi_amt, is_overdue, emi_num in self.due_vars:
            if var.get():
                total_emi += emi_amt
        
        total_payable = total_emi + penalty
        
        # Apply Customer Credit if switched ON
        if self.use_credit_var.get():
            total_payable = max(0, total_payable - self.current_customer_balance)
            
        # Update Amount Field
        self.field_amount.delete(0, 'end')
        self.field_amount.insert(0, str(int(total_payable)))
        
        # Update summary
        if self.loan_var.get() != t("select") + "...":
            try:
                txt = self.sum_label.cget("text")
                if "Selected:" in txt:
                    lines = txt.split("\n")
                    lines = [l for l in lines if "Selected:" not in l]
                    txt = "\n".join(lines)
                
                summary_line = f"✅ Selected: {self.selected_emi_count} Months | Total Payable: {format_indian_currency(total_payable)}"
                self.sum_label.configure(text=txt + "\n" + summary_line)
            except: pass
            
    def process_payment(self):
        loan_val = self.loan_var.get()
        loan_id = self.loan_map.get(loan_val)
        amount_str = self.field_amount.get()
        acc_val = self.acc_var.get()
        acc_id = self.account_map.get(acc_val)
        date = self.field_date.get() or datetime.now().strftime('%d-%m-%Y')
        remarks = self.field_remarks.get()
        
        if not loan_id or not amount_str or not acc_id:
            messagebox.showerror("Error", "Please select loan, enter amount and target account!")
            return
            
        if cl.is_date_closed(date):
            messagebox.showerror("Error", f"The date {date} has already been closed. No new payments can be recorded for this date.")
            return
            
        try:
            amount = float(amount_str)
            # Calculate total required for selected items
            total_emi_required = 0
            for var, emi_amt, is_overdue, emi_num in self.due_vars:
                if var.get():
                    total_emi_required += emi_amt
            
            total_required = total_emi_required + self.selected_penalty_total
            
            excess_to_credit = 0
            credit_to_use = 0
            
            if self.use_credit_var.get():
                # Manually requested to use credit
                if self.current_customer_balance > 0:
                    credit_to_use = min(total_required, self.current_customer_balance)
                    # The amount entered should be the remaining cash
                    # But if the user entered more than required - credit, we treat it as extra surplus?
                    # Let's see: total_required = 1200, credit = 500. amount_entered (remaining) = 700.
                    # total_to_pay_loan = 1200.
            
            if amount > (total_required - credit_to_use):
                excess_to_credit = amount - (total_required - credit_to_use)
            elif amount < (total_required - credit_to_use):
                shortfall = (total_required - credit_to_use) - amount
                if shortfall > 0 and not self.use_credit_var.get() and self.current_customer_balance >= shortfall:
                    if messagebox.askyesno("Use Credit", f"Total required is {format_indian_currency(total_required)} but you entered {format_indian_currency(amount)}.\n\nUse {format_indian_currency(shortfall)} from customer's credit balance (₹{self.current_customer_balance:,.2f})?"):
                        credit_to_use = shortfall
            
            # Final amount for the payment record (Applied to EMI)
            applied_amount = total_required 
            # Actual cash movement for account balance
            cash_received = amount 
            
            # Penalty per EMI Capture
            try:
                p_rate = float(self.field_penalty_rate.get() or 0)
            except:
                p_rate = 0

            # Calculate EMI numbers being paid
            emi_numbers = []
            for var, emi_amt, is_overdue, emi_num in self.due_vars:
                if var.get():
                    emi_numbers.append(f"E{emi_num}")
            emi_numbers_str = ",".join(emi_numbers)

            conn = get_connection()
            cursor = conn.cursor()
            
            if self.edit_payment_id:
                # REVERT OLD IMPACT FIRST
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (self.old_payment_amt, self.old_account_id))
                cursor.execute("DELETE FROM transactions WHERE description = ? AND amount = ? AND transaction_date = ?", 
                             (self.old_description, self.old_payment_amt, self.old_date))
                
                # Note: editing a payment with credit logic is complex (reverting old credit etc). 
                # For now we focus on new payments.
                
                # UPDATE EXISTING PAYMENT
                cursor.execute("""
                    UPDATE payments SET amount=?, payment_date=?, account_id=?, penalty_amount=?, 
                                      penalty_per_emi=?, overdue_count=?, remarks=?, emi_numbers=?
                    WHERE id = ?
                """, (applied_amount, date, acc_id, self.selected_penalty_total, p_rate, self.selected_overdue_count, remarks, emi_numbers_str, self.edit_payment_id))
                msg = f"EMI Payment of {format_indian_currency(applied_amount)} updated successfully."
            else:
                # SAVE NEW PAYMENT
                cursor.execute("""
                    INSERT INTO payments (loan_id, amount, payment_date, account_id, penalty_amount, penalty_per_emi, overdue_count, remarks, emi_numbers, credit_used, surplus_added)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (loan_id, applied_amount, date, acc_id, self.selected_penalty_total, p_rate, self.selected_overdue_count, remarks, emi_numbers_str, credit_to_use, excess_to_credit))
                
                penalty_msg_part = f" (Penalty: {format_indian_currency(self.selected_penalty_total)})" if self.selected_penalty_total > 0 else ""
                msg = f"EMI Payment of {format_indian_currency(applied_amount)} recorded successfully{penalty_msg_part}."
                
                if excess_to_credit > 0:
                    cursor.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (excess_to_credit, self.current_customer_id))
                    msg += f"\nExcess amount of {format_indian_currency(excess_to_credit)} added to customer credit."
                elif credit_to_use > 0:
                    cursor.execute("UPDATE customers SET balance = balance - ? WHERE id = ?", (credit_to_use, self.current_customer_id))
                    msg += f"\nUsed {format_indian_currency(credit_to_use)} from customer credit."
            
            # Financial Transaction (Applied for both)
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (cash_received, acc_id))
            
            # Record deposit transaction
            cursor.execute("""
                INSERT INTO transactions (account_id, transaction_type, amount, description, transaction_date)
                VALUES (?, 'DEPOSIT', ?, ?, ?)
            """, (acc_id, cash_received, f"EMI Received: {loan_val}", date))
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", msg)
            
            # Reset state
            self.edit_payment_id = None
            self.editing_emi_indices = set()
            self.pay_btn.configure(text="💳 " + t("record_payment"), fg_color=s.GREEN)
            
            self.field_amount.delete(0, 'end')
            self.field_remarks.delete(0, 'end')
            self.load_recent_payments()
            self.load_active_loans() # Refresh balances
            self.update_loan_details_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process payment: {e}")

    def check_scroll(self, event=None):
        if not self.has_more or self.loading_more:
            return
        try:
            if self._parent_canvas.yview()[1] > 0.8:
                self.load_recent_payments(append=True)
        except: pass

    def load_recent_payments(self, append=False):
        if self.loading_more or (append and not self.has_more):
            return
            
        self.loading_more = True
        
        if not append:
            self.payment_offset = 0
            self.has_more = True
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

        offset = self.payment_offset
        limit = 10
        
        def fetch():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.id, p.payment_date, c.name, v.reg_number, p.amount, a.name 
                    FROM payments p JOIN loans l ON p.loan_id = l.id
                    JOIN customers c ON l.customer_id = c.id
                    LEFT JOIN vehicles v ON l.vehicle_id = v.id
                    JOIN accounts a ON p.account_id = a.id
                    ORDER BY p.created_at DESC LIMIT ? OFFSET ?
                """, (limit, offset))
                payments = cursor.fetchall()
                conn.close()
                return payments
            except Exception as e:
                print(f"Error fetching recent payments: {e}")
                return []

        def render(payments):
            if not self.winfo_exists():
                self.loading_more = False
                return
                
            if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
                self.load_more_btn.destroy()

            if not payments:
                if not append:
                    for w in self.history_container.winfo_children(): w.destroy()
                    lbl = ctk.CTkLabel(self.history_container, text="No recent payments found.", font=s.Styles.FONT_TINY, text_color="gray")
                    lbl.pack(pady=20)
                self.has_more = False
                self.loading_more = False
                return

            if len(payments) < limit:
                self.has_more = False

            def render_payment_row(i, row_data):
                pid, date, name, reg, amt, acc = row_data
                row = ctk.CTkFrame(self.history_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=0)
                row.pack(fill="x")
                row.pack_propagate(False)
                ctk.CTkLabel(row, text=date, font=s.Styles.FONT_TINY).place(relx=0.0, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row, text=f"{name} ({reg or 'N/A'})", font=s.Styles.FONT_TINY, width=250, anchor="w").place(relx=0.2, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row, text=f"₹{amt:,.2f}", font=s.Styles.FONT_TINY, text_color=s.GREEN).place(relx=0.55, rely=0.5, anchor="w", x=15)
                
                # Action buttons frame
                btn_f = ctk.CTkFrame(row, fg_color="transparent")
                btn_f.place(relx=0.97, rely=0.5, anchor="e")
                
                # Print button
                ctk.CTkButton(btn_f, text="🖨️", width=28, height=28, fg_color=s.NAVY, font=s.Styles.FONT_TINY,
                               command=lambda p=pid: self.print_emi_receipt(p)).pack(side="left", padx=2)
                
                # Edit button
                ctk.CTkButton(btn_f, text="✏️", width=28, height=28, fg_color=s.PRIMARY, font=s.Styles.FONT_TINY,
                               command=lambda p=pid: self.edit_payment(p)).pack(side="left", padx=2)
                
                # Delete button
                ctk.CTkButton(btn_f, text="🗑", width=28, height=28, fg_color=s.RED, font=s.Styles.FONT_TINY,
                               command=lambda p=pid: self.delete_payment(p)).pack(side="left", padx=2)
                
                ctk.CTkLabel(row, text=f"To: {acc}", font=s.Styles.FONT_TINY, text_color=s.MUTED).place(relx=0.72, rely=0.5, anchor="w", x=15)

            def on_complete(count):
                if not self.winfo_exists(): return
                if self.has_more:
                    self.load_more_btn = ctk.CTkButton(self.history_container, text="Click to Load More Payments...", 
                                                      fg_color="transparent", text_color=s.PRIMARY,
                                                      hover_color=s.BORDER, font=s.Styles.FONT_SMALL_BOLD,
                                                      command=lambda: self.load_recent_payments(append=True))
                    self.load_more_btn.pack(pady=20, fill="x")
                self.loading_more = False

            self.render_list_chunked(self.history_container, payments, render_payment_row, 
                                   clear=not append, start_row_idx=offset, on_complete=on_complete)
            self.payment_offset += len(payments)

        self.run_in_background(fetch, render)
    def delete_payment(self, pid):
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this payment record? \nThis will revert the account balance and transaction history."):
            return

        def proceed_delete():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Fetch details for reversal
                cursor.execute("""
                    SELECT p.amount, p.account_id, p.payment_date, c.name, v.reg_number,
                           p.credit_used, p.surplus_added, c.id
                    FROM payments p JOIN loans l ON p.loan_id = l.id
                    JOIN customers c ON l.customer_id = c.id
                    LEFT JOIN vehicles v ON l.vehicle_id = v.id
                    WHERE p.id = ?
                """, (pid,))
                res = cursor.fetchone()
                if not res: return
                
                amt, aid, p_date, name, v_reg, cred_used, surp_added, cid = res
                
                # REVERSAL LOGIC:
                # Actual cash received originally was (applied_amount - credit_used + surplus_added)? 
                # Wait, applied_amount was total_required.
                # If surplus was added, cash_received = applied_amount + surplus_added.
                # If credit was used, cash_received = applied_amount - credit_used.
                # So cash_received = amt - cred_used + surp_added.
                cash_to_revert = amt - cred_used + surp_added
                
                # Revert Balance
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (cash_to_revert, aid))
                
                # Revert Customer Balance
                if cred_used > 0:
                    cursor.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (cred_used, cid))
                if surp_added > 0:
                    cursor.execute("UPDATE customers SET balance = balance - ? WHERE id = ?", (surp_added, cid))
                
                # Delete Transaction
                cursor.execute("DELETE FROM transactions WHERE description LIKE ? AND amount = ? AND transaction_date = ?", 
                             (f"EMI Received: {name}%", cash_to_revert, p_date))
                
                # Delete Payment
                cursor.execute("DELETE FROM payments WHERE id = ?", (pid,))
                
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Payment deleted successfully and balance reverted.")
                self.load_recent_payments()
                self.load_active_loans()
                self.update_loan_details_display()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete payment: {e}")

        PasswordDialog(self.winfo_toplevel(), on_success=proceed_delete)

    def edit_payment(self, pid):
        def proceed_edit():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.loan_id, p.amount, p.payment_date, p.account_id, p.remarks, p.emi_numbers,
                           c.name, v.reg_number, l.installment_amount
                    FROM payments p JOIN loans l ON p.loan_id = l.id
                    JOIN customers c ON l.customer_id = c.id
                    LEFT JOIN vehicles v ON l.vehicle_id = v.id
                    WHERE p.id = ?
                """, (pid,))
                res = cursor.fetchone()
                conn.close()
                
                if res:
                    loan_id, amt, p_date, aid, remarks, emis, c_name, v_reg, inst_amt = res
                    
                    # 1. Fill Loan
                    loan_key = f"{c_name} - {v_reg or 'N/A'} (EMI: ₹{inst_amt:,.2f})"
                    # Map might be slightly different depending on current formatting, try to find matching ID
                    for k, v in self.loan_map.items():
                        if v == loan_id:
                            self.loan_var.set(k)
                            break
                    
                    # 2. Fill Form
                    self.field_amount.delete(0, 'end')
                    self.field_amount.insert(0, str(amt))
                    self.field_date.set_date(p_date)
                    self.field_remarks.delete(0, 'end')
                    self.field_remarks.insert(0, remarks or "")
                    
                    # 3. Fill Account
                    for k, v in self.account_map.items():
                        if v == aid:
                            self.acc_var.set(k)
                            break
                    
                    # 4. Set state for Update
                    self.edit_payment_id = pid
                    self.old_payment_amt = amt
                    self.old_account_id = aid
                    self.old_date = p_date
                    self.old_description = f"EMI Received: {self.loan_var.get()}"
                    
                    self.editing_emi_indices = set()
                    if emis:
                        for part in emis.split(","):
                            try:
                                idx_str = part.strip().replace("E", "")
                                if idx_str: self.editing_emi_indices.add(int(idx_str) - 1)
                            except: pass
                    
                    self.pay_btn.configure(text="💾 Update Payment", fg_color=s.GOLD)
                    self.update_loan_details_display() # This redraws the grid with editable checkboxes
                    messagebox.showinfo("Edit Mode", "Payment details loaded. You can now modify EMIs as well. Click 'Update Payment' to save changes.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load payment for edit: {e}")

        PasswordDialog(self.winfo_toplevel(), on_success=proceed_edit)

    def print_emi_receipt(self, pid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.amount, p.penalty_amount, p.penalty_per_emi, p.overdue_count, p.payment_date,
                       c.name, c.phone, c.city, v.vehicle_name, v.reg_number, l.installment_amount, p.emi_numbers
                FROM payments p
                JOIN loans l ON p.loan_id = l.id
                JOIN customers c ON l.customer_id = c.id
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE p.id = ?
            """, (pid,))
            r = cursor.fetchone()
            conn.close()
            
            if not r: return
            
            amt, pen_tot, pen_rate, over_count, date, cname, cphone, ccity, vname, vreg, emi_base, emi_numbers = r
            
            # Formatting
            emi_base = emi_base or 0
            pen_tot = pen_tot or 0
            pen_rate = pen_rate or 0
            over_count = over_count or 0
            
            # Multi-EMI calculation
            # We derive the EMI count as (amt - pen_tot) / emi_base
            import math
            emi_paid_count = 0
            if emi_base > 0:
                emi_paid_count = round((amt - pen_tot) / emi_base)
            else:
                emi_paid_count = 1 # Fallback
            
            total_emi_paid = emi_paid_count * emi_base
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>EMI Receipt - {vreg}</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 20px; background: #f8fafc; }}
                    .receipt-card {{ background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 8px solid #3b82f6; position: relative; }}
                    .header {{ text-align: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 20px; margin-bottom: 30px; }}
                    .header h1 {{ margin: 0; color: #0f172a; font-size: 26px; font-weight: 800; }}
                    .section-title {{ font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; border-bottom: 1px solid #f1f5f9; padding-bottom: 5px; }}
                    .detail-item {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
                    .label {{ font-size: 12px; color: #64748b; font-weight: 600; }}
                    .value {{ font-size: 13px; color: #1e293b; font-weight: 700; }}
                    .breakdown {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin-top: 20px; }}
                    .total-box {{ background: #eff6ff; padding: 20px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #3b82f6; text-align: right; }}
                    .total-label {{ font-size: 13px; color: #1e40af; font-weight: 600; }}
                    .total-value {{ font-size: 28px; color: #1d4ed8; font-weight: 800; }}
                    .footer {{ margin-top: 40px; text-align: center; font-size: 10px; color: #94a3b8; }}
                    @media print {{
                        button.no-print {{ display: none !important; }}
                    }}
                </style>
            </head>
            <body>
                <div class="receipt-card">
                    <div class="header">
                        <h1>{get_company_name()}</h1>
                        <p style="font-size: 12px; color:#64748b;">{get_company_address()}</p>
                        <p style="font-size: 12px; color:#64748b;">Contact: {get_company_contact()}</p>
                        <p style="font-size: 14px; font-weight: 700; background: #ebf5ff; color: #1d4ed8; display: inline-block; padding: 5px 15px; border-radius: 10px; margin-top: 10px;">Date: {date}</p>
                    </div>

                    <div class="section-title">Customer Information</div>
                    <div class="detail-item"><div class="label">Customer Name</div><div class="value">{cname}</div></div>
                    <div class="detail-item"><div class="label">Vehicle / Reg No</div><div class="value">{vname or '-'} ({vreg or '-'})</div></div>
                    <div class="detail-item"><div class="label">EMI Numbers Paid</div><div class="value">{emi_numbers or 'N/A'}</div></div>
                    
                    <div class="section-title">Payment Breakdown</div>
                    <div class="breakdown">
                        <div class="detail-item">
                            <div class="label">Base Installment ({emi_paid_count} Months × ₹{emi_base:,.2f})</div>
                            <div class="value">₹{total_emi_paid:,.2f}</div>
                        </div>
                        <div class="detail-item">
                            <div class="label">Overdue Penalty ({over_count or 0} Months × ₹{pen_rate:,.2f})</div>
                            <div class="value">₹{pen_tot:,.2f}</div>
                        </div>
                    </div>

                    <div class="total-box">
                        <div class="total-label">Grand Total Paid</div>
                        <div class="total-value">₹{amt:,.2f}</div>
                    </div>

                    <div class="footer">
                        <p>This is a computer-generated receipt. Thank you for your payment!</p>
                    </div>
                </div>
                <div style="text-align:center; margin-top:20px;">
                    <button class="no-print" onclick="window.print()" style="padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">Print Receipt</button>
                </div>
            </body>
            </html>
            """
            import tempfile, webbrowser, os
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            webbrowser.open('file://' + os.path.realpath(temp_path))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate receipt: {e}")

    def open_preclosure_dialog(self):
        if not self.selected_loan_id:
            messagebox.showerror("Error", "Please select a loan first!")
            return
            
        try:
            total_payable = float(self.field_amount.get().replace(',', ''))
        except:
            total_payable = 0
            
        PreClosureDialog(self.winfo_toplevel(), self.selected_loan_id, self.loan_var.get(), on_success=self.on_preclosure_success, passed_outstanding=total_payable)
        
    def on_preclosure_success(self):
        self.load_recent_payments()
        self.load_active_loans()
        self.update_loan_details_display()

class PreClosureDialog(ctk.CTkToplevel):
    def __init__(self, master, loan_id, loan_display, on_success=None, passed_outstanding=None, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Loan Pre-closure Settlement")
        self.passed_outstanding = passed_outstanding
        self.geometry("500x700")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        if master: self.transient(master)
        
        self.loan_id = loan_id
        self.loan_display = loan_display
        self.on_success = on_success
        self.account_map = {}
        
        # Details from DB
        self.total_loan_amount = 0
        self.total_paid = 0
        self.outstanding = 0
        self.calculated_payable = 0
        
        self.setup_ui()
        self.load_data()
        self.load_accounts()

    def setup_ui(self):
        # Header (Fixed)
        ctk.CTkLabel(self, text="LOAN PRE-CLOSURE", font=s.Styles.FONT_H3, text_color=s.RED).pack(pady=(15, 10))
        
        # Scrollable Content Area
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=480)
        self.scroll_frame.pack(fill="both", expand=True, padx=20)
        
        # Loan Info Box
        info_card = ctk.CTkFrame(self.scroll_frame, fg_color=s.CARD, corner_radius=12, border_width=1, border_color=s.BORDER)
        info_card.pack(fill="x", pady=5)
        
        self.info_label = ctk.CTkLabel(info_card, text=f"Settlement for:\n{self.loan_display}", font=s.Styles.FONT_SMALL_BOLD, justify="center")
        self.info_label.pack(pady=10, padx=20)
        
        # Numbers Row
        num_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        num_frame.pack(fill="x", pady=5)
        
        self.outstanding_label = ctk.CTkLabel(num_frame, text="Outstanding Balance: ₹0.00", font=s.Styles.FONT_H3, text_color=s.NAVY)
        self.outstanding_label.pack()
        
        # Inputs
        input_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=10)
        
        # Discount
        ctk.CTkLabel(input_frame, text="Interest Waiver / Discount (₹):", font=s.Styles.FONT_TINY_BOLD).pack(anchor="w", padx=2)
        self.field_discount = ctk.CTkEntry(input_frame, height=35, width=400, placeholder_text="0")
        self.field_discount.pack(pady=(2, 8))
        self.field_discount.insert(0, "0")
        self.field_discount.bind("<KeyRelease>", lambda e: self.recalculate())
        
        # Charges
        ctk.CTkLabel(input_frame, text="Additional Closure Charges (₹):", font=s.Styles.FONT_TINY_BOLD).pack(anchor="w", padx=2)
        self.field_charges = ctk.CTkEntry(input_frame, height=35, width=400, placeholder_text="0")
        self.field_charges.pack(pady=(2, 8))
        self.field_charges.insert(0, "0")
        self.field_charges.bind("<KeyRelease>", lambda e: self.recalculate())
        
        # Total to Pay
        self.pay_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#fef2f2", corner_radius=8, height=50)
        self.pay_frame.pack(fill="x", pady=10)
        self.pay_frame.pack_propagate(False)
        self.total_pay_label = ctk.CTkLabel(self.pay_frame, text="FINAL PAYABLE: ₹0.00", font=s.Styles.FONT_BOLD, text_color=s.RED)
        self.total_pay_label.pack(expand=True)
        
        # Account Selection
        ctk.CTkLabel(self.scroll_frame, text="Deposit Account:", font=s.Styles.FONT_TINY_BOLD).pack(anchor="w", padx=2)
        self.field_acc = ctk.CTkOptionMenu(self.scroll_frame, values=[], height=35, width=400, fg_color=s.CARD, text_color=s.TEXT, button_color=s.NAVY)
        self.field_acc.pack(pady=(2, 10))
        
        # Date
        ctk.CTkLabel(self.scroll_frame, text="Settlement Date:", font=s.Styles.FONT_TINY_BOLD).pack(anchor="w", padx=2)
        from ui_components import DatePickerWidget
        self.field_date = DatePickerWidget(self.scroll_frame, default_date=datetime.now(), height=35)
        self.field_date.pack(pady=(2, 10), anchor="w")
        
        # Action Buttons (Fixed at bottom)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        self.confirm_btn = ctk.CTkButton(btn_frame, text="CONFIRM & CLOSE LOAN", height=45, fg_color=s.GREEN, hover_color="#059669", font=s.Styles.FONT_BOLD, command=self.confirm_closure)
        self.confirm_btn.pack(side="left", expand=True, padx=5)
        
        ctk.CTkButton(btn_frame, text="CANCEL", height=45, fg_color=s.RED, command=self.destroy).pack(side="left", expand=True, padx=5)

    def load_data(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.loan_amount, l.loan_tenure, l.installment_amount,
                       (SELECT SUM(amount) FROM payments WHERE loan_id = l.id) as total_paid
                FROM loans l 
                WHERE l.id = ?
            """, (self.loan_id,))
            res = cursor.fetchone()
            conn.close()
            
            if res:
                self.total_loan_amount = res[0] or 0
                loan_tenure = res[1] or 0
                installment_amount = res[2] or 0
                self.total_paid = res[3] or 0
                
                if getattr(self, 'passed_outstanding', 0) > 0:
                    self.outstanding = self.passed_outstanding
                else:
                    total_expected = loan_tenure * installment_amount
                    self.outstanding = max(0, total_expected - self.total_paid)
                    
                self.outstanding_label.configure(text=f"Outstanding Balance: {format_indian_currency(self.outstanding)}")
                self.recalculate()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")

    def load_accounts(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = cursor.fetchall()
            conn.close()
            self.account_map = {f"{r[1]} ({format_indian_currency(r[2] or 0)})": r[0] for r in accounts}
            acc_list = list(self.account_map.keys())
            self.field_acc.configure(values=acc_list)
            for name in acc_list:
                if "Shop Cash" in name: 
                    self.field_acc.set(name)
                    break
        except: pass

    def recalculate(self):
        try:
            disc = float(self.field_discount.get() or 0)
            char = float(self.field_charges.get() or 0)
            self.calculated_payable = max(0, self.outstanding - disc + char)
            self.total_pay_label.configure(text=f"FINAL SETTLEMENT AMOUNT: {format_indian_currency(self.calculated_payable)}")
        except:
            pass

    def confirm_closure(self):
        if not messagebox.askyesno("Confirm Pre-closure", "Are you sure you want to PERMANENTLY CLOSE this loan?\nThis action will record a final payment and update loan status."):
            return
            
        acc_val = self.field_acc.get()
        acc_id = self.account_map.get(acc_val)
        date = self.field_date.get()
        payable = self.calculated_payable
        
        if not acc_id:
            messagebox.showerror("Error", "Please select a deposit account!")
            return
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 1. Record Final Payment
            cursor.execute("""
                INSERT INTO payments (loan_id, amount, payment_date, account_id, remarks, emi_numbers)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.loan_id, payable, date, acc_id, f"PRE-CLOSURE SETTLEMENT (Discount: {self.field_discount.get()}, Charges: {self.field_charges.get()})", "SETTLED"))
            
            # 2. Update Account Balance
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (payable, acc_id))
            
            # 3. Add Transaction
            cursor.execute("""
                INSERT INTO transactions (account_id, transaction_type, amount, description, transaction_date)
                VALUES (?, 'DEPOSIT', ?, ?, ?)
            """, (acc_id, payable, f"Loan Pre-closure: {self.loan_display}", date))
            
            # 4. Close the Loan
            cursor.execute("UPDATE loans SET status = 'Closed', closed_date = ? WHERE id = ?", (date, self.loan_id))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", f"Loan settled for {format_indian_currency(payable)} and marked as CLOSED.")
            if self.on_success: self.on_success()
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to settle loan: {e}")

class OverdueLoansWindow(ctk.CTkToplevel):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Overdue Loan Details")
        self.geometry("1100x700")
        
        # Focus logic
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        
        # Header
        header = ctk.CTkFrame(self, fg_color=s.RED, height=60, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="⚠️ OVERDUE LOANS ATTENTION REQUIRED", font=s.Styles.FONT_BOLD, text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        
        container = ctk.CTkFrame(self, fg_color=s.BG)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Table Header
        t_head = ctk.CTkFrame(container, fg_color=s.NAVY_DARK, height=40, corner_radius=s.Styles.RADIUS)
        t_head.pack(fill="x", pady=(0, 10))
        t_head.pack_propagate(False)
        
        headers = [("CUSTOMER", 0.0), ("VEHICLE", 0.3), ("REG NO", 0.5), ("EMI", 0.7), ("ACTIONS", 0.85)]
        for text, rel_x in headers:
            ctk.CTkLabel(t_head, text=text, font=s.Styles.FONT_TINY, text_color="white").place(relx=rel_x, rely=0.5, anchor="w", x=15)
            
        self.list_container = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True)
        
        self.load_overdue_loans()

    def load_overdue_loans(self):
        # Clear container and show loading
        for widget in self.list_container.winfo_children():
            widget.destroy()
        
        loading_lbl = ctk.CTkLabel(self.list_container, text="Calculating overdue loans...", font=s.Styles.FONT_DEFAULT)
        loading_lbl.pack(pady=40)

        def fetch():
            overdue_list = []
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT l.id, c.name, v.vehicle_name, v.reg_number, l.installment_amount, l.due_beginning_date, l.loan_tenure,
                           (SELECT COUNT(*) FROM payments WHERE loan_id = l.id) as paid_count
                    FROM loans l
                    JOIN customers c ON l.customer_id = c.id
                    LEFT JOIN vehicles v ON l.vehicle_id = v.id
                    WHERE l.status = 'Active'
                """)
                loans = cursor.fetchall()
                
                now = datetime.now().date()
                for row in loans:
                    lid, cname, vname, reg, emi, due_start, tenure, paid_count = row
                    if not due_start: continue
                    try:
                        start_dt = datetime.strptime(due_start, "%d-%m-%Y")
                        if paid_count < tenure:
                            i = paid_count 
                            month = (start_dt.month + i - 1) % 12 + 1
                            year = start_dt.year + (start_dt.month + i - 1) // 12
                            import calendar
                            last_day = calendar.monthrange(year, month)[1]
                            due_date = datetime(year, month, min(start_dt.day, last_day)).date()
                            if due_date < now:
                                overdue_list.append(row)
                    except: continue
                conn.close()
            except Exception as e:
                print(f"Error fetching overdue loans: {e}")
            return overdue_list

        def render(overdue_list):
            if not self.winfo_exists(): return
            for widget in self.list_container.winfo_children():
                widget.destroy()
            
            if not overdue_list:
                ctk.CTkLabel(self.list_container, text="No overdue loans found!", font=s.Styles.FONT_DEFAULT).pack(pady=40)
                return
                
            for i, (lid, name, v_name, reg, emi, due_start, tenure, paid_count) in enumerate(overdue_list):
                row_f = ctk.CTkFrame(self.list_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, height=45, corner_radius=0)
                row_f.pack(fill="x")
                row_f.pack_propagate(False)
                
                ctk.CTkLabel(row_f, text=name, font=s.Styles.FONT_TINY).place(relx=0.0, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row_f, text=v_name or "-", font=s.Styles.FONT_TINY).place(relx=0.3, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row_f, text=reg or "-", font=s.Styles.FONT_TINY).place(relx=0.5, rely=0.5, anchor="w", x=15)
                ctk.CTkLabel(row_f, text=f"₹{emi:,.2f}", font=s.Styles.FONT_TINY, text_color=s.RED).place(relx=0.7, rely=0.5, anchor="w", x=15)
                
                btn_call = ctk.CTkButton(row_f, text="📞 " + t("call"), width=65, height=30, fg_color="#d97706", 
                                       hover_color="#b45309", font=s.Styles.FONT_TINY,
                                       command=lambda l=lid, c=name: self.open_call_log(l, c))
                btn_call.place(relx=0.76, rely=0.5, anchor="w", x=0)

                btn_h = ctk.CTkButton(row_f, text="📜 " + t("hist"), width=65, height=30, fg_color="#475569", 
                                      hover_color="#334155", font=s.Styles.FONT_TINY,
                                      command=lambda l=lid, c=name: self.open_call_history(l, c))
                btn_h.place(relx=0.84, rely=0.5, anchor="w", x=0)

                btn_v = ctk.CTkButton(row_f, text="👁 " + t("view"), width=65, height=30, fg_color=s.GREEN, hover_color="#059669", 
                                     font=s.Styles.FONT_TINY, command=lambda l=lid: self.view_loan(l))
                btn_v.place(relx=0.92, rely=0.5, anchor="w", x=0)

        def run():
            data = fetch()
            if self.winfo_exists():
                self.after(0, lambda: render(data))
        
        import threading
        threading.Thread(target=run, daemon=True).start()

    def open_call_log(self, lid, customer_name):
        LogCallWindow(self, lid, customer_name)

    def open_call_history(self, lid, customer_name):
        CallHistoryWindow(self, lid, customer_name)
    
    def view_loan(self, lid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, 
                       l.loan_amount, l.loan_tenure, l.interest_rate, l.installment_amount, 
                       l.loan_date, l.down_payment, l.document_fee, l.loan_doc_path, l.due_beginning_date, l.status
                FROM loans l 
                JOIN customers c ON l.customer_id = c.id 
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone()
            conn.close()
            if loan:
                ViewLoanWindow(self, loan)
        except: pass

class DunningRegisterTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("overdue_register"), **kwargs)
        
        # --- Header Section with Export ---
        self.header_card, self.header_f = self.create_card("Register Actions")
        self.btn_html = ctk.CTkButton(self.header_f, text="🖨️ " + t("reports"), 
                                      width=180, height=35, fg_color=s.GOLD, 
                                      hover_color=s.GOLD_DARK, font=s.Styles.FONT_BOLD,
                                      command=self.export_to_html)
        self.btn_html.grid(row=1, column=0, pady=10)


        # --- Stats Card ---
        self.stats_card, self.stats_f = self.create_card("Overdue Summary")
        self.total_overdue_lbl = ctk.CTkLabel(self.stats_f, text=t("total_receivable") + ": ₹0.00", 
                                             font=s.Styles.FONT_BOLD, text_color=s.RED)
        self.total_overdue_lbl.grid(row=1, column=0, padx=20, pady=15, sticky="w")
        
        self.count_lbl = ctk.CTkLabel(self.stats_f, text=t("active_loans") + ": 0", 
                                     font=s.Styles.FONT_BOLD, text_color=s.TEXT)
        self.count_lbl.grid(row=1, column=1, padx=20, pady=15, sticky="e")
        self.stats_f.grid_columnconfigure(1, weight=1)

        
        # --- Table Header ---
        self.list_header_card = ctk.CTkFrame(self, fg_color=s.NAVY, height=45, corner_radius=8)
        self.list_header_card.pack(fill="x", padx=s.PAD_LG, pady=(s.PAD_LG, s.PAD_SM))
        # self.list_header_card.pack_propagate(False) # Removed as it might cause issues with resizing
        
        cols = [
            (t("customer") + " / " + t("phone"), 0.02),
            (t("vehicle") + " / " + t("reg_no"), 0.22),
            (t("installment"), 0.42),
            (t("overdue_dues"), 0.55),
            (t("total_receivable"), 0.68),
            (t("actions"), 0.81)
        ]
        for text, rel_x in cols:
            lbl = ctk.CTkLabel(self.list_header_card, text=text, font=s.Styles.FONT_TINY_BOLD, text_color=s.WHITE)
            lbl.place(relx=rel_x, rely=0.5, anchor="w", x=15)
            
        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True, padx=s.PAD_LG, pady=(0, s.PAD_LG))
        
        # Lazy Loading State
        self.dunning_offset = 0
        self.has_more = True
        self.loading_more = False
        self.full_overdue_data = []
        
        # Bind scroll events
        if hasattr(self, "_parent_canvas"):
            self._parent_canvas.bind("<Configure>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<MouseWheel>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-4>", lambda e: self.check_scroll(), add="+")
            self._parent_canvas.bind("<Button-5>", lambda e: self.check_scroll(), add="+")

        self.load_dunning_data()

    def check_scroll(self, event=None):
        if not self.has_more or self.loading_more:
            return
        try:
            if self._parent_canvas.yview()[1] > 0.8:
                self.load_dunning_data(append=True)
        except: pass

    def view_loan(self, lid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, 
                       l.loan_amount, l.loan_tenure, l.interest_rate, l.installment_amount, 
                       l.loan_date, l.down_payment, l.document_fee, l.loan_doc_path, l.due_beginning_date, l.status
                FROM loans l 
                JOIN customers c ON l.customer_id = c.id 
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone()
            conn.close()
            if loan:
                ViewLoanWindow(self.winfo_toplevel(), loan)
        except Exception as e: 
            print(f"Error opening loan view: {e}")

    def open_call_log(self, lid, customer_name):
        LogCallWindow(self.winfo_toplevel(), lid, customer_name)

    def open_call_history(self, lid, customer_name):
        CallHistoryWindow(self.winfo_toplevel(), lid, customer_name)


    def load_dunning_data(self, append=False):
        if self.loading_more or (append and not self.has_more):
            return
            
        self.loading_more = True
        limit = 10
        
        if not append:
            self.dunning_offset = 0
            self.has_more = True
            self.full_overdue_data = []
            for w in self.list_container.winfo_children(): w.destroy()
            
            # Show a loading indicator
            self.loading_lbl = ctk.CTkLabel(self.list_container, text="Calculating overdue installments...", font=s.Styles.FONT_TINY, text_color=s.MUTED)
            self.loading_lbl.pack(pady=20)
            
            def fetch():
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, l.installment_amount, 
                               l.due_beginning_date, l.loan_tenure,
                               (SELECT COUNT(*) FROM payments WHERE loan_id = l.id) as paid_count
                        FROM loans l
                        JOIN customers c ON l.customer_id = c.id
                        LEFT JOIN vehicles v ON l.vehicle_id = v.id
                        WHERE l.status = 'Active'
                    """)
                    loans = cursor.fetchall()
                    conn.close()
                    
                    overdue_data = []
                    total_overdue_val = 0
                    now = datetime.now().date()
                    
                    for row in loans:
                        lid, cname, phone, vname, reg, emi, due_start, tenure, paid_count = row
                        if not due_start: continue
                        
                        try:
                            start_dt = datetime.strptime(due_start, "%d-%m-%Y")
                            missed_installments = 0
                            for i in range(paid_count, tenure):
                                month = (start_dt.month + i - 1) % 12 + 1
                                year = start_dt.year + (start_dt.month + i - 1) // 12
                                import calendar
                                last_day = calendar.monthrange(year, month)[1]
                                due_date = datetime(year, month, min(start_dt.day, last_day)).date()
                                
                                if due_date < now:
                                    missed_installments += 1
                                else:
                                    break
                                    
                            if missed_installments > 0:
                                overdue_amt = missed_installments * emi
                                overdue_data.append({
                                    "id": lid,
                                    "customer": cname,
                                    "phone": phone or "N/A",
                                    "vehicle": f"{vname or 'N/A'}\n{reg or 'N/A'}",
                                    "emi": emi,
                                    "count": missed_installments,
                                    "total": overdue_amt
                                })
                                total_overdue_val += overdue_amt
                        except: continue
                    return overdue_data, total_overdue_val
                except Exception as e:
                    print(f"Error in background dunning fetch: {e}")
                    return [], 0

            def render(result):
                if not self.winfo_exists(): return
                if hasattr(self, 'loading_lbl') and self.loading_lbl.winfo_exists():
                    self.loading_lbl.destroy()
                
                overdue_data, total_val = result
                self.full_overdue_data = overdue_data
                self.total_overdue_lbl.configure(text=f"{t('total_receivable')}: ₹{total_val:,.2f}")
                self.count_lbl.configure(text=f"{t('active_loans')}: {len(overdue_data)}")
                
                if not overdue_data:
                    ctk.CTkLabel(self.list_container, text="Excellent! No overdue installments detected.", 
                                 font=s.Styles.FONT_DEFAULT, text_color=s.GREEN).pack(pady=50)
                    self.has_more = False
                    self.loading_more = False
                    return
                
                self.render_next_chunk()

            self.run_in_background(fetch, render)
        else:
            self.render_next_chunk()

    def render_next_chunk(self):
        if not self.winfo_exists(): return
        
        limit = 10
        offset = self.dunning_offset
        chunk = self.full_overdue_data[offset : offset + limit]
        
        if not chunk:
            self.has_more = False
            self.loading_more = False
            return

        if offset + limit >= len(self.full_overdue_data):
            self.has_more = False

        # Remove existing load more button
        if hasattr(self, "load_more_btn") and self.load_more_btn.winfo_exists():
            self.load_more_btn.destroy()

        def render_row(i, data):
            row_f = ctk.CTkFrame(self.list_container, fg_color=s.CARD if i % 2 == 0 else s.BORDER, 
                                height=60, corner_radius=0)
            row_f.pack(fill="x")
            row_f.pack_propagate(False)
            
            # Customer / Phone
            c_lbl = ctk.CTkLabel(row_f, text=f"{data['customer']}\n{data['phone']}", 
                                font=s.Styles.FONT_TINY_BOLD, justify="left", anchor="w")
            c_lbl.place(relx=0.0, rely=0.5, anchor="w", x=15)
            
            # Vehicle / Reg
            v_lbl = ctk.CTkLabel(row_f, text=data['vehicle'], font=s.Styles.FONT_TINY, justify="left", anchor="w")
            v_lbl.place(relx=0.22, rely=0.5, anchor="w", x=15)
            
            # EMI
            ctk.CTkLabel(row_f, text=f"₹{data['emi']:,.2f}", font=s.Styles.FONT_TINY).place(relx=0.42, rely=0.5, anchor="w", x=15)
            
            # Count
            ctk.CTkLabel(row_f, text=f"{data['count']} Months", font=s.Styles.FONT_BOLD, 
                         text_color=s.RED).place(relx=0.55, rely=0.5, anchor="w", x=15)
            
            # Total
            ctk.CTkLabel(row_f, text=f"₹{data['total']:,.2f}", font=s.Styles.FONT_BOLD, 
                         text_color=s.RED).place(relx=0.68, rely=0.5, anchor="w", x=15)
            
            btn_call = ctk.CTkButton(row_f, text="📞 " + t("call"), width=75, height=35, fg_color="#d97706", 
                                   hover_color="#b45309", font=s.Styles.FONT_TINY_BOLD,
                                   command=lambda l=data['id'], c=data['customer']: self.open_call_log(l, c))
            btn_call.place(relx=0.81, rely=0.5, anchor="w", x=0)

            btn_h = ctk.CTkButton(row_f, text="📜 " + t("hist"), width=60, height=35, fg_color=s.MUTED, 
                                  hover_color="#475569", font=s.Styles.FONT_TINY_BOLD,
                                  command=lambda l=data['id'], c=data['customer']: self.open_call_history(l, c))
            btn_h.place(relx=0.875, rely=0.5, anchor="w", x=0)
            
            # Actions
            btn_v = ctk.CTkButton(row_f, text="👁 " + t("view"), width=75, height=35, fg_color=s.NAVY, 
                                 hover_color=s.NAVY_DARK, font=s.Styles.FONT_TINY_BOLD, 
                                 command=lambda l=data['id']: self.view_loan(l))
            btn_v.place(relx=0.93, rely=0.5, anchor="w", x=0)

        def on_complete(count):
            if not self.winfo_exists(): return
            if self.has_more:
                self.load_more_btn = ctk.CTkButton(self.list_container, text="Click to Load More Overdue Cases...", 
                                                  fg_color="transparent", text_color=s.PRIMARY,
                                                  hover_color=s.BORDER, font=s.Styles.FONT_SMALL_BOLD,
                                                  command=lambda: self.load_dunning_data(append=True))
                self.load_more_btn.pack(pady=20, fill="x")
            self.loading_more = False

        self.render_list_chunked(self.list_container, chunk, render_row, 
                               clear=False, start_row_idx=offset, on_complete=on_complete)
        
        self.dunning_offset += len(chunk)

    def export_to_html(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, l.installment_amount, 
                       l.due_beginning_date, l.loan_tenure,
                       (SELECT COUNT(*) FROM payments WHERE loan_id = l.id) as paid_count
                FROM loans l
                JOIN customers c ON l.customer_id = c.id
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.status = 'Active'
            """)
            loans = cursor.fetchall()
            conn.close()
            
            overdue_rows_html = ""
            total_overdue_val = 0
            case_count = 0
            now = datetime.now().date()
            
            for row in loans:
                lid, cname, phone, vname, reg, emi, due_start, tenure, paid_count = row
                if not due_start: continue
                
                try:
                    start_dt = datetime.strptime(due_start, "%d-%m-%Y")
                    missed_installments = 0
                    for i in range(paid_count, tenure):
                        month = (start_dt.month + i - 1) % 12 + 1
                        year = start_dt.year + (start_dt.month + i - 1) // 12
                        import calendar
                        last_day = calendar.monthrange(year, month)[1]
                        due_date = datetime(year, month, min(start_dt.day, last_day)).date()
                        
                        if due_date < now:
                            missed_installments += 1
                        else:
                            break
                            
                    if missed_installments > 0:
                        overdue_amt = missed_installments * emi
                        total_overdue_val += overdue_amt
                        case_count += 1
                        
                        overdue_rows_html += f"""
                        <tr>
                            <td><strong>{cname}</strong><br><small>{phone or 'N/A'}</small></td>
                            <td>{vname or 'N/A'}<br><small>{reg or 'N/A'}</small></td>
                            <td>₹{emi:,.2f}</td>
                            <td class="overdue-text">{missed_installments} Months</td>
                            <td class="overdue-text">₹{overdue_amt:,.2f}</td>
                        </tr>
                        """
                except: continue

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Dunning Register - {datetime.now().strftime('%d-%m-%Y')}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #334155; max-width: 1000px; margin: 0 auto; padding: 40px; background: #f3f4f6; }}
                    .container {{ background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-top: 8px solid #dc2626; }}
                    .header {{ text-align: center; border-bottom: 2px solid #d1d5db; padding-bottom: 20px; margin-bottom: 30px; }}
                    .header h1 {{ margin: 0; color: #0f172a; font-size: 28px; }}
                    .header p {{ margin: 5px 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
                    .stats {{ display: flex; justify-content: space-between; margin-bottom: 30px; padding: 20px; background: #fef2f2; border-radius: 8px; border: 1px solid #fee2e2; }}
                    .stat-item {{ text-align: center; }}
                    .stat-label {{ font-size: 12px; color: #991b1b; text-transform: uppercase; font-weight: 700; }}
                    .stat-value {{ font-size: 24px; color: #dc2626; font-weight: 800; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th {{ text-align: left; background: #1e293b; color: white; padding: 12px 15px; font-size: 12px; text-transform: uppercase; }}
                    td {{ padding: 12px 15px; border-bottom: 1px solid #d1d5db; font-size: 14px; }}
                    tr:nth-child(even) {{ background-color: #d1d5db; }}
                    .overdue-text {{ color: #dc2626; font-weight: 700; }}
                    .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #64748b; }}
                    @media print {{
                        body {{ background: white; padding: 0; }}
                        .container {{ box-shadow: none; border: 1px solid #d1d5db; }}
                        .no-print {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{get_company_name()}</h1>
                        <p>Dunning Register — Overdue Installment Cases</p>
                        <div style="margin-top:10px; font-size: 12px; color: #64748b;">Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}</div>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-label">Total Overdue cases</div>
                            <div class="stat-value">{case_count}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Total Outstanding Dues</div>
                            <div class="stat-value">₹{total_overdue_val:,.2f}</div>
                        </div>
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Customer / Phone</th>
                                <th>Vehicle / Reg</th>
                                <th>Monthly EMI</th>
                                <th>Overdue</th>
                                <th>Total Due</th>
                            </tr>
                        </thead>
                        <tbody>
                            {overdue_rows_html if overdue_rows_html else '<tr><td colspan="5" style="text-align:center;">No overdue cases found.</td></tr>'}
                        </tbody>
                    </table>
                    
                    <div class="footer">
                        <p>This report is for internal management use only.</p>
                        <p>&copy; {datetime.now().year} {get_company_name()} Software | User: {getattr(self.winfo_toplevel(), 'current_username', 'System')}</p>
                    </div>
                </div>
                
                <div class="no-print" style="text-align:center; margin-top:30px;">
                    <button onclick="window.print()" style="padding:12px 24px; background:#dc2626; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600;">🖨️ Print Report</button>
                </div>
            </body>
            </html>
            """
            
            import tempfile
            import webbrowser
            import os
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open('file://' + os.path.realpath(temp_path))
            
        except Exception as e:
            print(f"Error generating HTML dunning report: {e}")

    def view_loan(self, lid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, 
                       l.loan_amount, l.loan_tenure, l.interest_rate, l.installment_amount, 
                       l.loan_date, l.down_payment, l.document_fee, l.loan_doc_path, l.due_beginning_date, l.status
                FROM loans l 
                JOIN customers c ON l.customer_id = c.id 
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone()
            conn.close()
            if loan:
                ViewLoanWindow(self.winfo_toplevel(), loan)
        except: pass

class ProfitTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("profit_tracking"), **kwargs)
        
        # Filter Bar
        self.filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_frame.pack(fill="x", padx=s.PAD_LG, pady=(0, s.PAD_MD))
        
        from datetime import datetime
        now = datetime.now()
        first_day = now.replace(day=1)
        
        ctk.CTkLabel(self.filter_frame, text=t("date_range") + ":", font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED).pack(side="left", padx=5)
        
        self.date_from = DatePickerWidget(self.filter_frame)
        self.date_from.set_date(first_day.strftime("%d-%m-%Y"))
        self.date_from.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.filter_frame, text=t("to") if "to" in t("common") else "TO", font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED).pack(side="left", padx=5)
        
        self.date_to = DatePickerWidget(self.filter_frame)
        self.date_to.set_date(now.strftime("%d-%m-%Y"))
        self.date_to.pack(side="left", padx=5)
        
        self.filter_btn = ctk.CTkButton(self.filter_frame, text="🔍 " + t("filter_stats"), 
                                        width=120, height=32, command=self.apply_filter)
        self.filter_btn.pack(side="left", padx=15)
        
        self.refresh()

    def apply_filter(self):
        start = self.date_from.get()
        end = self.date_to.get()
        self.refresh(start, end)

    def refresh(self, start=None, end=None):
        for widget in self.winfo_children():
            if widget != self.header_frame and widget != self.filter_frame:
                widget.destroy()
        
        # Summary Cards
        stats = fl.get_profit_summary(start, end)
        
        cards_f = ctk.CTkFrame(self, fg_color="transparent")
        cards_f.pack(fill="x", padx=s.PAD_LG, pady=s.PAD_MD)
        
        self.create_stat_card(cards_f, t("total_income"), f"₹{(stats['income']['total'] or 0):,.2f}", s.GREEN, 0)
        self.create_stat_card(cards_f, t("total_expenses"), f"₹{(stats['expense']['total'] or 0):,.2f}", s.RED, 1)
        self.create_stat_card(cards_f, t("net_profit"), f"₹{(stats['profit'] or 0):,.2f}", s.GOLD, 2)
        
        # Breakdown Row
        breakdown_f = ctk.CTkFrame(self, fg_color="transparent")
        breakdown_f.pack(fill="x", padx=s.PAD_LG, pady=s.PAD_MD)
        
        # Income Breakdown
        inc_card, inc_inner = self.create_card(t("income_breakdown"), breakdown_f)
        inc_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        for i, (label, val) in enumerate(stats['income'].items()):
            if label == "total": continue
            self.create_breakdown_item(inc_inner, t(f"{label}_income") if f"{label}_income" in t("income_breakdown") else label, f"₹{(val or 0):,.2f}", i)
            
        # Expense Breakdown
        exp_card, exp_inner = self.create_card(t("expense_management"), breakdown_f)
        exp_card.pack(side="left", fill="both", expand=True, padx=(10, 0))
        for i, (label, val) in enumerate(stats['expense'].items()):
            if label == "total": continue
            self.create_breakdown_item(exp_inner, t(f"{label}_expense") if f"{label}_expense" in t("expense_management") else label, f"₹{(val or 0):,.2f}", i)

    def create_stat_card(self, master, label, value, color, col):
        card = ctk.CTkFrame(master, fg_color=s.CARD, corner_radius=15, border_width=1, border_color=s.BORDER)
        card.grid(row=0, column=col, sticky="nsew", padx=10)
        master.grid_columnconfigure(col, weight=1)
        
        ctk.CTkLabel(card, text=label.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED).pack(pady=(15, 5))
        ctk.CTkLabel(card, text=value, font=s.Styles.FONT_H2, text_color=color).pack(pady=(0, 15))

    def create_breakdown_item(self, master, label, value, row):
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.pack(fill="x", pady=5)
        ctk.CTkLabel(f, text=label, font=s.Styles.FONT_DEFAULT, text_color=s.TEXT).pack(side="left")
        ctk.CTkLabel(f, text=value, font=s.Styles.FONT_BOLD, text_color=s.NAVY).pack(side="right")

class ExpenseTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("expense_management"), **kwargs)
        self.btn_add = ctk.CTkButton(self.header_frame, text="+ " + t("add_new"), width=140, 
                                     fg_color=s.PRIMARY, hover_color=s.PRIMARY_HOVER, 
                                     font=s.Styles.FONT_BOLD, command=self.add_expense)
        self.btn_add.pack(side="right", padx=10)
        self.refresh()

    def refresh(self):
        for widget in self.winfo_children():
            if widget != self.header_frame:
                widget.destroy()
        
        card, inner = self.create_card(t("expense_management"))
        self.table_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.table_frame.pack(fill="both", expand=True)
        self.load_expenses()

    def load_expenses(self):
        for w in self.table_frame.winfo_children(): w.destroy()
        
        headers = [t("date"), t("category"), t("amount"), t("approved_by"), t("actions")]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED).grid(row=0, column=i, padx=10, pady=10, sticky="w")
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.expense_date, ec.name, e.amount, e.approved_by 
                FROM expenses e 
                JOIN expense_categories ec ON e.category_id = ec.id 
                ORDER BY e.expense_date DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            
            for i, row in enumerate(rows):
                for j, val in enumerate(row[1:]):
                    txt = f"₹{(val or 0):,.2f}" if j == 2 else val
                    ctk.CTkLabel(self.table_frame, text=txt, font=s.Styles.FONT_DEFAULT).grid(row=i+1, column=j, padx=10, pady=5, sticky="w")
                
                btn_f = ctk.CTkFrame(self.table_frame, fg_color="transparent")
                btn_f.grid(row=i+1, column=4, padx=10, pady=5)
                ctk.CTkButton(btn_f, text="🗑", width=30, fg_color=s.RED, command=lambda id=row[0]: self.delete_expense(id)).pack()
        except Exception as e:
            print(f"Error loading expenses: {e}")

    def add_expense(self):
        ExpenseWindow(self.winfo_toplevel(), self.refresh)

    def delete_expense(self, id):
        if messagebox.askyesno(t("confirm_delete"), t("are_you_sure_delete") + "?"):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM expenses WHERE id=?", (id,))
                conn.commit()
                conn.close()
                self.refresh()
            except: pass

class PayrollTab(BaseTab):
    def __init__(self, master, **kwargs):
        super().__init__(master, t("payroll_management"), **kwargs)
        
        self.seg_btn = ctk.CTkSegmentedButton(self.header_frame, values=[t("employee_mgmt"), t("generate_payroll")],
                                             command=self.toggle_view)
        self.seg_btn.pack(side="left", padx=50)
        self.seg_btn.set(t("employee_mgmt"))
        
        self.btn_add = ctk.CTkButton(self.header_frame, text="+ " + t("add_new"), width=140, 
                                     fg_color=s.PRIMARY, hover_color=s.PRIMARY_HOVER, 
                                     font=s.Styles.FONT_BOLD, command=self.add_employee)
        self.btn_add.pack(side="right", padx=10)
        
        self.content_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.content_wrap.pack(fill="both", expand=True)
        
        self.toggle_view(t("employee_mgmt"))

    def toggle_view(self, val):
        for w in self.content_wrap.winfo_children(): w.destroy()
        if val == t("employee_mgmt"):
            self.load_employees()
        else:
            self.load_payroll()

    def load_employees(self):
        card, inner = self.create_card(t("employee_mgmt"), self.content_wrap)
        # Simplified employee list
        headers = [t("employee_id"), t("name"), t("designation"), t("basic_salary"), t("status")]
        for i, h in enumerate(headers):
            ctk.CTkLabel(inner, text=h.upper(), font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED).grid(row=0, column=i, padx=10, pady=10, sticky="w")
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT employee_id, name, role, basic_salary, status FROM employees")
            rows = cursor.fetchall()
            conn.close()
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    txt = f"₹{(val or 0):,.2f}" if j == 3 else val
                    ctk.CTkLabel(inner, text=txt, font=s.Styles.FONT_DEFAULT).grid(row=i+1, column=j, padx=10, pady=5, sticky="w")
        except: pass

    def load_payroll(self):
        card, inner = self.create_card(t("generate_payroll"), self.content_wrap)
        ctk.CTkButton(inner, text="Generate Monthly Payroll", command=self.generate_payroll).pack(pady=20)

    def add_employee(self):
        EmployeeWindow(self.winfo_toplevel(), lambda: self.toggle_view(self.seg_btn.get()))

    def generate_payroll(self):
        # Implementation for generating payroll
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, basic_salary FROM employees WHERE status='Active'")
            employees = cursor.fetchall()
            
            if not employees:
                messagebox.showinfo("Payroll", "No active employees found.")
                conn.close()
                return
                
            # For simplicity, generate for current month
            now = datetime.now()
            month, year = now.month, now.year
            
            count = 0
            for eid, name, salary in employees:
                # Check if already generated
                cursor.execute("SELECT id FROM payroll WHERE employee_id=? AND month=? AND year=?", (eid, month, year))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO payroll (employee_id, month, year, basic_salary, net_salary, payment_date, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
                    """, (eid, month, year, salary, salary, now.strftime("%d-%m-%Y")))
                    count += 1
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Payroll", f"Generated {count} payroll records for {calendar.month_name[month]} {year}.")
            self.load_payroll()
        except Exception as e:
            messagebox.showerror("Error", str(e))

class ExpenseWindow(ctk.CTkToplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.title("Add Expense")
        self.geometry("500x700")
        self.callback = callback
        
        # Bring to foreground and focus
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        
        card = ctk.CTkFrame(self, fg_color=s.CARD)
        card.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(card, text="Category", font=s.Styles.FONT_TINY).pack(anchor="w", padx=20, pady=(20, 0))
        # Fetch categories
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM expense_categories")
        self.cats = cursor.fetchall()
        
        # Fetch accounts
        cursor.execute("SELECT id, name FROM accounts")
        self.accounts = cursor.fetchall()
        conn.close()
        
        self.cat_var = ctk.StringVar(value="Select Category")
        self.cat_menu = ctk.CTkOptionMenu(card, variable=self.cat_var, values=[c[1] for c in self.cats], width=400)
        self.cat_menu.pack(pady=5)
        
        ctk.CTkLabel(card, text="Account", font=s.Styles.FONT_TINY).pack(anchor="w", padx=20, pady=(10, 0))
        self.acc_var = ctk.StringVar(value="Select Account")
        self.acc_menu = ctk.CTkOptionMenu(card, variable=self.acc_var, values=[a[1] for a in self.accounts], width=400)
        self.acc_menu.pack(pady=5)
        
        ctk.CTkLabel(card, text="Amount", font=s.Styles.FONT_TINY).pack(anchor="w", padx=20, pady=(10, 0))
        self.amt_entry = ctk.CTkEntry(card, width=400)
        self.amt_entry.pack(pady=5)
        
        ctk.CTkLabel(card, text="Approved By", font=s.Styles.FONT_TINY).pack(anchor="w", padx=20, pady=(10, 0))
        self.app_entry = ctk.CTkEntry(card, width=400)
        self.app_entry.pack(pady=5)
        
        ctk.CTkLabel(card, text="Description", font=s.Styles.FONT_TINY).pack(anchor="w", padx=20, pady=(10, 0))
        self.desc_text = ctk.CTkTextbox(card, height=100, width=400)
        self.desc_text.pack(pady=5)
        
        ctk.CTkButton(card, text="SAVE EXPENSE", command=self.save, fg_color=s.PRIMARY).pack(pady=30)

    def save(self):
        cat_name = self.cat_var.get()
        acc_name = self.acc_var.get()
        amt = self.amt_entry.get()
        if cat_name == "Select Category" or acc_name == "Select Account" or not amt: return
        
        # Check if date is closed
        date_today = datetime.now().strftime("%d-%m-%Y")
        if cl.is_date_closed(date_today):
            messagebox.showerror("Error", f"Today's date ({date_today}) has already been closed. No new expenses can be recorded.")
            return

        try:
            amt_val = float(amt)
            cat_id = next(c[0] for c in self.cats if c[1] == cat_name)
            acc_id = next(a[0] for a in self.accounts if a[1] == acc_name)
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check balance
            cursor.execute("SELECT balance FROM accounts WHERE id=?", (acc_id,))
            bal = cursor.fetchone()[0]
            if bal < amt_val:
                messagebox.showerror("Insufficient Funds", f"Account balance is only ₹{bal:,.2f}")
                conn.close()
                return

            # Insert expense
            cursor.execute("""
                INSERT INTO expenses (expense_date, category_id, amount, account_id, approved_by, description) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now().strftime("%d-%m-%Y"), cat_id, amt_val, acc_id, self.app_entry.get(), self.desc_text.get("1.0", "end-1c")))
            
            # Update account
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amt_val, acc_id))
            
            # Insert transaction
            cursor.execute("""
                INSERT INTO transactions (account_id, transaction_type, amount, description) 
                VALUES (?, 'EXPENSE', ?, ?)
            """, (acc_id, amt_val, f"Expense: {cat_name} - {self.app_entry.get()}"))
            
            conn.commit()
            conn.close()
            self.callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

class EmployeeWindow(ctk.CTkToplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.title("New Employee")
        self.geometry("500x700")
        self.callback = callback
        
        # Bring to foreground and focus
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        
        card = ctk.CTkFrame(self, fg_color=s.CARD)
        card.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.name_entry = self.create_input(card, "Full Name")
        self.id_entry = self.create_input(card, "Employee ID")
        self.role_entry = self.create_input(card, "Designation")
        self.salary_entry = self.create_input(card, "Basic Salary")
        
        ctk.CTkButton(card, text="SAVE EMPLOYEE", command=self.save, fg_color=s.PRIMARY).pack(pady=30)

    def create_input(self, master, label):
        ctk.CTkLabel(master, text=label).pack(anchor="w", padx=20, pady=(10, 0))
        e = ctk.CTkEntry(master, width=400)
        e.pack(pady=5)
        return e

    def save(self):
        date_today = datetime.now().strftime("%d-%m-%Y")
        if cl.is_date_closed(date_today):
            messagebox.showerror("Error", f"The date {date_today} has already been closed. No new payroll records can be recorded for this date.")
            return
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO employees (employee_id, name, role, basic_salary, joining_date) VALUES (?, ?, ?, ?, ?)",
                           (self.id_entry.get(), self.name_entry.get(), self.role_entry.get(), float(self.salary_entry.get()), datetime.now().strftime("%d-%m-%Y")))
            conn.commit()
            conn.close()
            self.callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

class ClosureWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Day End Closure Preview")
        self.geometry("700x850")
        
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        
        self.summary = cl.get_daily_summary()
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        ctk.CTkLabel(scroll, text="DAY END CLOSURE SUMMARY", font=s.Styles.FONT_H2, text_color=s.PRIMARY).pack(pady=(0, 20))
        ctk.CTkLabel(scroll, text=f"For Date: {self.summary['date']}", font=s.Styles.FONT_BOLD).pack()
        
        # Cash Section
        self.create_section(scroll, "CASH SUMMARY", [
            ("Opening Cash", self.summary['cash']['opening']),
            ("Cash Sales (+)", self.summary['cash']['sales']),
            ("Cash Received (+)", self.summary['cash']['received']),
            ("Cash Expenses (-)", self.summary['cash']['expenses']),
            ("Bank Deposits (-)", self.summary['cash']['deposit']),
            ("CLOSING CASH", self.summary['cash']['closing'], True)
        ])
        
        # Bank Section
        bank_rows = [(b['name'], b['closing']) for b in self.summary['bank']]
        self.create_section(scroll, "BANK ACCOUNTS", bank_rows + [("TOTAL BANK", self.summary['totals']['bank'], True)])
        
        # Stock Section
        self.create_section(scroll, "STOCK SUMMARY", [
            ("Closing Stock Count", len(self.summary['stock'])),
            ("TOTAL STOCK VALUE", self.summary['totals']['stock'], True)
        ])
        
        # Total Assets
        asset_frame = ctk.CTkFrame(scroll, fg_color=s.NAVY, corner_radius=10)
        asset_frame.pack(fill="x", pady=20, padx=10)
        ctk.CTkLabel(asset_frame, text=f"TOTAL ASSETS: ₹ {self.summary['totals']['assets']:,}", 
                     font=s.Styles.FONT_H3, text_color="white").pack(pady=15)
        
        # Actions
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20, padx=20)
        
        # Preview Button
        ctk.CTkButton(btn_frame, text="👁 PREVIEW REPORT (HTML)", fg_color=s.NAVY, 
                     command=self.preview_report, width=200).pack(side="top", pady=(0, 15))
        
        ctk.CTkButton(btn_frame, text="CANCEL", fg_color="transparent", border_width=1, border_color=s.MUTED, 
                     text_color=s.TEXT, command=self.destroy, width=150).pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frame, text="CONFIRM & CLOSE DAY", fg_color=s.PRIMARY, 
                     command=self.confirm_closure, width=250).pack(side="right", padx=10)

    def preview_report(self):
        # Generate temporary HTML preview
        from reusable_master.db import MasterDatabase
        db = MasterDatabase()
        shop_info = {
            "name": db.get_setting("company_name", "NAGUDI AUTO FINANCE"),
            "address": db.get_setting("company_address", ""),
            "contact": db.get_setting("company_contact", "")
        }
        cl.generate_html_report(self.summary, "PREVIEW", shop_info)

    def create_section(self, master, title, rows):
        f = ctk.CTkFrame(master, fg_color=s.CARD, corner_radius=10, border_width=1, border_color=s.BORDER)
        f.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(f, text=title, font=s.Styles.FONT_TINY_BOLD, text_color=s.MUTED).pack(anchor="w", padx=15, pady=(10, 5))
        
        for name, val, *is_bold in rows:
            row_f = ctk.CTkFrame(f, fg_color="transparent")
            row_f.pack(fill="x", padx=15, pady=2)
            
            font = s.Styles.FONT_BOLD if is_bold else s.Styles.FONT_SMALL
            ctk.CTkLabel(row_f, text=name, font=font).pack(side="left")
            ctk.CTkLabel(row_f, text=f"₹ {val:,}" if isinstance(val, (int, float)) else str(val), font=font).pack(side="right")

    def confirm_closure(self):
        if messagebox.askyesno("Confirm Closure", "Are you sure you want to close the day? This will lock the records and generate the printable report."):
            report_num = cl.save_closure(self.summary)
            if report_num:
                # Get Shop Info
                from reusable_master.db import MasterDatabase
                db = MasterDatabase()
                shop_info = {
                    "name": db.get_setting("company_name", "NAGUDI AUTO FINANCE"),
                    "address": db.get_setting("company_address", ""),
                    "contact": db.get_setting("company_contact", "")
                }
                cl.generate_html_report(self.summary, report_num, shop_info)
                messagebox.showinfo("Success", f"Day closed successfully! Report No: {report_num}")
                self.destroy()
            else:
                messagebox.showerror("Error", "Could not save closure. Date might already be closed.")

class PastClosuresWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Past Day End Closures")
        self.geometry("900x600")
        
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        self.focus_force()
        self.grab_set()
        
        # Table of closures
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.load_closures()

    def load_closures(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT report_number, closure_date, closing_cash, total_assets, closed_by, timestamp FROM day_closures ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        
        # Headers
        header_f = ctk.CTkFrame(self.scroll, fg_color=s.NAVY)
        header_f.pack(fill="x", pady=(0, 10))
        cols = [("REPORT NO", 150), ("DATE", 120), ("CASH", 120), ("ASSETS", 120), ("USER", 120), ("ACTIONS", 100)]
        for text, w in cols:
            ctk.CTkLabel(header_f, text=text, text_color="white", font=s.Styles.FONT_TINY_BOLD, width=w).pack(side="left", padx=5)

        for rnum, date, cash, assets, user, ts in rows:
            row_f = ctk.CTkFrame(self.scroll, fg_color=s.CARD, height=45)
            row_f.pack(fill="x", pady=2)
            row_f.pack_propagate(False)
            
            ctk.CTkLabel(row_f, text=rnum, width=150).pack(side="left", padx=5)
            ctk.CTkLabel(row_f, text=date, width=120).pack(side="left", padx=5)
            ctk.CTkLabel(row_f, text=f"₹{cash:,}", width=120).pack(side="left", padx=5)
            ctk.CTkLabel(row_f, text=f"₹{assets:,}", width=120).pack(side="left", padx=5)
            ctk.CTkLabel(row_f, text=user, width=120).pack(side="left", padx=5)
            
            btn = ctk.CTkButton(row_f, text="📄 Reprint", width=80, height=28, 
                                command=lambda r=rnum: self.reprint(r))
            btn.pack(side="right", padx=10)

    def reprint(self, report_num):
        import json
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT summary_json FROM day_closures WHERE report_number = ?", (report_num,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                summary = json.loads(row[0])
                from reusable_master.db import MasterDatabase
                db = MasterDatabase()
                shop_info = {
                    "name": db.get_setting("company_name", t("company_name") if "t" in globals() else "NAGUDI AUTO FINANCE"),
                    "address": db.get_setting("company_address", ""),
                    "contact": db.get_setting("company_contact", "")
                }
                cl.generate_html_report(summary, report_num, shop_info)
            else:
                messagebox.showerror("Error", "No detailed data stored for this report.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reprint: {e}")

class CustomerHistoryWindow(ctk.CTkToplevel):
    def __init__(self, master, customer_id, initial_category="Sales"):
        super().__init__(master)
        self.customer_id = customer_id
        self.title("Customer 360 View - History")
        self.geometry("900x600")
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        
        self.configure(fg_color=s.BG)
        
        # Fetch customer name
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,))
        res = cursor.fetchone()
        name = res[0] if res else "Unknown Customer"
        conn.close()

        # Header
        header = ctk.CTkFrame(self, fg_color=s.NAVY, height=70, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=f"📂 {name.upper()}", font=s.Styles.FONT_H2, text_color="white").place(relx=0.05, rely=0.5, anchor="w")
        
        # Tabs Container
        self.tab_f = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_f.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tab_view = ctk.CTkTabview(self.tab_f, fg_color=s.CARD)
        self.tab_view.pack(fill="both", expand=True)
        
        self.tab_sales = self.tab_view.add("Sales Involvement")
        self.tab_purchases = self.tab_view.add("Purchase Involvement")
        self.tab_loans = self.tab_view.add("Loan Involvement")
        
        self.load_sales()
        self.load_purchases()
        self.load_loans()
        
        # Set initial tab
        if initial_category == "Sales": self.tab_view.set("Sales Involvement")
        elif initial_category == "Purchases": self.tab_view.set("Purchase Involvement")
        elif initial_category == "Loans": self.tab_view.set("Loan Involvement")

    def view_loan_history(self, lid):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.name, c.phone, v.vehicle_name, v.reg_number, 
                       l.loan_amount, l.loan_tenure, l.interest_rate, l.installment_amount, 
                       l.loan_date, l.down_payment, l.document_fee, l.loan_doc_path, l.due_beginning_date, l.status
                FROM loans l 
                JOIN customers c ON l.customer_id = c.id 
                LEFT JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.id = ?
            """, (lid,))
            loan = cursor.fetchone(); conn.close()
            if loan:
                ViewLoanWindow(self.tab_view, loan)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load loan details: {e}")

    def load_sales(self):
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("""
            SELECT vehicle_name, reg_number, sale_price, sale_date, status 
            FROM vehicles WHERE customer_id = ? ORDER BY sale_date DESC
        """, (self.customer_id,))
        rows = cursor.fetchall()
        conn.close()
        
        container = ctk.CTkScrollableFrame(self.tab_sales, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        if not rows:
            ctk.CTkLabel(container, text="No sales recorded for this customer.", font=s.Styles.FONT_DEFAULT, text_color=s.MUTED).pack(pady=50)
            return

        for name, reg, price, date, status in rows:
            f = ctk.CTkFrame(container, fg_color="#f8fafc", border_width=1, border_color="#e2e8f0")
            f.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(f, text=f"🚗 {name} ({reg})", font=s.Styles.FONT_BOLD).pack(side="left", padx=15, pady=10)
            ctk.CTkLabel(f, text=f"Date: {date or '-'}", font=s.Styles.FONT_TINY).pack(side="left", padx=15)
            ctk.CTkLabel(f, text=f"Price: {format_indian_currency(price or 0)}", font=s.Styles.FONT_TINY, text_color=s.GREEN).pack(side="right", padx=15)

    def load_purchases(self):
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("""
            SELECT vehicle_name, reg_number, purchase_price, purchase_date, status 
            FROM vehicles WHERE purchased_from_id = ? ORDER BY purchase_date DESC
        """, (self.customer_id,))
        rows = cursor.fetchall()
        conn.close()
        
        container = ctk.CTkScrollableFrame(self.tab_purchases, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        if not rows:
            ctk.CTkLabel(container, text="No purchases recorded from this customer.", font=s.Styles.FONT_DEFAULT, text_color=s.MUTED).pack(pady=50)
            return

        for name, reg, price, date, status in rows:
            f = ctk.CTkFrame(container, fg_color="#f8fafc", border_width=1, border_color="#e2e8f0")
            f.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(f, text=f"📥 {name} ({reg})", font=s.Styles.FONT_BOLD).pack(side="left", padx=15, pady=10)
            ctk.CTkLabel(f, text=f"Date: {date or '-'}", font=s.Styles.FONT_TINY).pack(side="left", padx=15)
            ctk.CTkLabel(f, text=f"Paid: {format_indian_currency(price or 0)}", font=s.Styles.FONT_TINY, text_color=s.RED).pack(side="right", padx=15)

    def load_loans(self):
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("""
            SELECT l.id, l.loan_amount, l.installment_amount, l.loan_date, l.status,
                   (SELECT SUM(amount) FROM payments WHERE loan_id = l.id) as paid_amt,
                   v.vehicle_name, v.reg_number
            FROM loans l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            WHERE l.customer_id = ? ORDER BY l.created_at DESC
        """, (self.customer_id,))
        rows = cursor.fetchall()
        conn.close()
        
        container = ctk.CTkScrollableFrame(self.tab_loans, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        if not rows:
            ctk.CTkLabel(container, text="No loans found for this customer.", font=s.Styles.FONT_DEFAULT, text_color=s.MUTED).pack(pady=50)
            return

        for lid, amt, emi, date, status, paid_amt, vname, vreg in rows:
            paid_amt = paid_amt or 0
            f = ctk.CTkFrame(container, fg_color="#f8fafc", border_width=1, border_color=s.GOLD if status=='Active' else "#e2e8f0")
            f.pack(fill="x", pady=5, padx=5)
            
            top = ctk.CTkFrame(f, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=(10, 5))
            ctk.CTkLabel(top, text=f"💳 LOAN #{lid} - {status.upper()}", font=s.Styles.FONT_BOLD, text_color=s.NAVY if status=='Active' else s.MUTED).pack(side="left")
            ctk.CTkLabel(top, text=f"Date: {date or '-'}", font=s.Styles.FONT_TINY).pack(side="right")
            
            mid = ctk.CTkFrame(f, fg_color="transparent")
            mid.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(mid, text=f"Vehicle: {vname or 'N/A'} ({vreg or '-'})", font=s.Styles.FONT_TINY).pack(side="left")
            
            bot = ctk.CTkFrame(f, fg_color="transparent")
            bot.pack(fill="x", padx=15, pady=(5, 10))
            ctk.CTkLabel(bot, text=f"Loan: {format_indian_currency(amt)}", font=s.Styles.FONT_TINY_BOLD).pack(side="left")
            ctk.CTkLabel(bot, text=f"Paid: {format_indian_currency(paid_amt)}", font=s.Styles.FONT_TINY_BOLD, text_color=s.GREEN).pack(side="left", padx=20)
            
            balance = max(0, amt - paid_amt)
            ctk.CTkLabel(bot, text=f"Balance: {format_indian_currency(balance)}", font=s.Styles.FONT_TINY_BOLD, text_color=s.RED).pack(side="right")
            
            # View Payments Button
            btn_view = ctk.CTkButton(bot, text="👁️ View Payments", width=120, height=28, 
                                     fg_color=s.GOLD, hover_color=s.GOLD_DARK, font=s.Styles.FONT_TINY_BOLD,
                                     text_color=s.NAVY, command=lambda l=lid: self.view_loan_history(l))
            btn_view.pack(side="right", padx=(0, 20))
