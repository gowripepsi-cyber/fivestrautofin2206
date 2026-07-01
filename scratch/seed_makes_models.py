import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'nagudi_auto.db')

MAKES_MODELS = {
    # Two-Wheelers
    "Hero": [
        "Splendor Plus", "Splendor Pro", "HF Deluxe", "HF 100",
        "Passion Pro", "Passion Plus", "Glamour", "Xtreme 160R",
        "Xtreme 200R", "Maestro Edge", "Destini 125", "Xpulse 200"
    ],
    "Honda": [
        "Activa 3G", "Activa 4G", "Activa 5G", "Activa 6G",
        "CB Shine", "CB Unicorn", "CB Hornet 160R", "SP 125",
        "Dio", "Grazia", "CB200X", "Livo", "Dream Yuga"
    ],
    "Bajaj": [
        "Pulsar 150", "Pulsar 180", "Pulsar 220F", "Pulsar NS200",
        "Pulsar RS200", "CT 100", "CT 110", "Platina 100",
        "Platina 110", "Avenger Street 160", "Avenger Cruise 220",
        "Dominar 400", "Chetak"
    ],
    "TVS": [
        "Apache RTR 160", "Apache RTR 180", "Apache RTR 200 4V",
        "Apache RR 310", "Jupiter", "Jupiter Classic", "Jupiter ZX",
        "Star City Plus", "Radeon", "Sport", "NTORQ 125", "iQube",
        "XL 100", "Ronin"
    ],
    "Yamaha": [
        "FZ S FI", "FZ 25", "FZS FI", "MT 15",
        "R15 V4", "R15 S", "Fascino 125", "Ray ZR 125",
        "Ray ZR Street Rally", "Saluto 125", "Aerox 155"
    ],
    "Suzuki": [
        "Access 125", "Burgman Street", "Gixxer 150", "Gixxer SF",
        "Gixxer 250", "Gixxer SF 250", "V-Strom SX", "Intruder"
    ],
    "Royal Enfield": [
        "Bullet 350", "Classic 350", "Meteor 350", "Thunderbird 350",
        "Himalayan", "Interceptor 650", "Continental GT 650",
        "Hunter 350", "Super Meteor 650", "Shotgun 650"
    ],
    "KTM": [
        "Duke 125", "Duke 200", "Duke 250", "Duke 390",
        "RC 125", "RC 200", "RC 390", "Adventure 390"
    ],
    "Kawasaki": [
        "Ninja 300", "Ninja 400", "Ninja 650", "Ninja ZX-6R",
        "Versys 650", "Z650", "Z900", "Vulcan S"
    ],
    # Four-Wheelers
    "Maruti Suzuki": [
        "Alto 800", "Alto K10", "Swift", "Swift Dzire",
        "Wagon R", "Celerio", "Baleno", "Ertiga",
        "Brezza", "Grand Vitara", "Fronx", "Jimny", "S-Presso"
    ],
    "Hyundai": [
        "i10", "Grand i10 Nios", "i20", "Aura",
        "Verna", "Creta", "Venue", "Tucson",
        "Alcazar", "Ioniq 5", "Exter"
    ],
    "Tata": [
        "Nano", "Tiago", "Tigor", "Altroz",
        "Nexon", "Harrier", "Safari", "Punch", "Curvv"
    ],
    "Mahindra": [
        "Bolero", "Bolero Neo", "Scorpio", "Scorpio N",
        "XUV 300", "XUV 400", "XUV 700", "Thar",
        "KUV100", "Marazzo", "Pickup"
    ],
    "Toyota": [
        "Innova", "Innova Crysta", "Innova Hycross", "Fortuner",
        "Urban Cruiser", "Urban Cruiser Hyryder", "Glanza",
        "Camry", "Vellfire", "Hilux"
    ],
    "Honda Cars": [
        "Amaze", "City", "City e:HEV", "WR-V",
        "Jazz", "HR-V", "Elevate", "CR-V"
    ],
    "Kia": [
        "Seltos", "Sonet", "Carens", "EV6"
    ],
    "MG": [
        "Hector", "Hector Plus", "Astor", "Gloster",
        "ZS EV", "Comet EV"
    ],
    # Commercial
    "Ashok Leyland": [
        "Dost", "Dost Strong", "Bada Dost", "Partner",
        "Stile", "Sunshine"
    ],
    "Eicher": [
        "Pro 2049", "Pro 2059", "Pro 3015", "Pro 3019"
    ],
    "Force": [
        "Trax", "Gurkha", "Traveller", "Cruiser"
    ],
    "Piaggio": [
        "Ape City", "Ape Xtra", "Ape E-City"
    ],
}

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = OFF")
cur = conn.cursor()

print("Seeding makes and models...")
total_makes = 0
total_models = 0

for make_name, models in MAKES_MODELS.items():
    # Insert make (ignore if exists)
    cur.execute("INSERT OR IGNORE INTO makes (name) VALUES (?)", (make_name,))
    cur.execute("SELECT id FROM makes WHERE name=?", (make_name,))
    make_id = cur.fetchone()[0]
    total_makes += 1

    for model_name in models:
        cur.execute("INSERT OR IGNORE INTO models (make_id, name) VALUES (?, ?)", (make_id, model_name))
        total_models += 1

conn.commit()
conn.close()

print(f"  [OK] {total_makes} makes seeded")
print(f"  [OK] {total_models} models seeded")
print("\nDone! Make and Model dropdowns should now load correctly.")
