import sqlite3

def test_update():
    conn = sqlite3.connect("nagudi_auto.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM customers WHERE id = 205")
    print("Before:", cursor.fetchone())
    cursor.execute("UPDATE customers SET balance = balance + 10 WHERE id = 205")
    conn.commit()
    cursor.execute("SELECT balance FROM customers WHERE id = 205")
    print("After:", cursor.fetchone())
    # revert
    cursor.execute("UPDATE customers SET balance = balance - 10 WHERE id = 205")
    conn.commit()

if __name__ == "__main__":
    test_update()
