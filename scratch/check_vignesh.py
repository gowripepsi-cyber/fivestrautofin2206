import sqlite3

def check_vignesh():
    conn = sqlite3.connect("nagudi_auto.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = 205")
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone()
    if row:
        print(dict(zip(columns, row)))
    else:
        print("Customer not found")
    conn.close()

if __name__ == "__main__":
    check_vignesh()
