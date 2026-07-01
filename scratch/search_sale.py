import sqlite3

DB_NAME = "nagudi_auto.db"

def search_sale():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    amount = 65000.0
    print(f"Searching for transactions with amount: {amount}")
    
    cursor.execute("SELECT * FROM transactions WHERE amount = ?", (amount,))
    transactions = cursor.fetchall()
    for t in transactions:
        # Avoid printing rupee symbol to prevent encoding error
        t_list = list(t)
        if isinstance(t_list[3], str):
            t_list[3] = t_list[3].replace("\u20b9", "Rs.")
        print(f"Transaction: {t_list}")
        
    conn.close()

if __name__ == "__main__":
    search_sale()
