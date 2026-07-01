import customtkinter as ctk

# --- Layout Variables ---
SIDEBAR_W = 260
HEADER_H = 70

# --- Professional Slate/Indigo Palette ---
# Neutral Grays (Slate)
BG = "#f8fafc"         # Slate 50
CARD = "#ffffff"       # White
CARD_ALT = "#f1f5f9"   # Slate 100
BORDER = "#e2e8f0"     # Slate 200
BORDER_ACTIVE = "#cbd5e1" # Slate 300

# Primary Action (Indigo)
PRIMARY = "#4f46e5"    # Indigo 600
PRIMARY_HOVER = "#4338ca" # Indigo 700

# Utility Colors
NAVY = "#1e293b"       # Slate 800 (Professional Blue-Gray)
NAVY_DARK = "#0f172a"  # Slate 900
GOLD = "#f59e0b"       # Amber 500
GOLD_LIGHT = "#fbbf24" # Amber 400
GOLD_DARK = "#d97706"  # Amber 600
GREEN = "#10b981"      # Emerald 500
RED = "#ef4444"        # Red 500
PURPLE = "#8b5cf6"     # Violet 500
BLUE = "#3b82f6"       # Blue 500

# Text Tokens
TEXT = "#1e293b"       # Slate 800
MUTED = "#64748b"      # Slate 500
WHITE = "#ffffff"

# Component Specific Defaults
ENTRY_BG_ACTIVE = "#f1f5f9"
ENTRY_TEXT_ACTIVE = "#1e293b"
COMBO_BG = "#ffffff"
COMBO_TEXT = "#1e293b"
COMBO_BG_HOVER = "#f8fafc"
COMBO_BORDER_ACTIVE = PRIMARY

# Spacing Tokens
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24

# Helper to configure appearance
def setup_theme():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

class Styles:
    RADIUS = 12
    FIELD_WIDTH = 300
    FIELD_HEIGHT = 40
    FAMILY = "Inter"
    
    # Typography System
    FONT_DEFAULT = (FAMILY, 14)
    FONT_BOLD = (FAMILY, 14, "bold")
    FONT_H1 = (FAMILY, 30, "bold")
    FONT_H2 = (FAMILY, 24, "bold")
    FONT_H3 = (FAMILY, 20, "bold")
    FONT_SMALL = (FAMILY, 14)
    FONT_SMALL_BOLD = (FAMILY, 14, "bold")
    FONT_TINY = (FAMILY, 12)
    FONT_TINY_BOLD = (FAMILY, 12, "bold")
