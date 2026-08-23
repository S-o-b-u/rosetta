import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bankmanagementsystem.db")

def setup_db():
    # Remove existing DB to start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. login table
    # Schema inferred from: insert into login values('"+formno+"','"+cardno+"','"+pin+"')
    cursor.execute('''
        CREATE TABLE login (
            formno TEXT,
            cardno TEXT,
            pin TEXT
        )
    ''')
    
    # Seed data
    cursor.execute("INSERT INTO login (formno, cardno, pin) VALUES ('1001', '1234567890123456', '1234')")
    
    # 2. bank table (for deposit/withdrawl later)
    # Schema inferred from: insert into bank values('"+pin+"', '"+date+"', 'Deposit', '"+amount+"')
    cursor.execute('''
        CREATE TABLE bank (
            pin TEXT,
            date TEXT,
            type TEXT,
            amount TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[+] Test DB created and seeded at {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    setup_db()
