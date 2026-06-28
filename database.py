import sqlite3

conn = sqlite3.connect("data/staff.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS staff(
    user_id INTEGER PRIMARY KEY,
    username TEXT,

    current_pf INTEGER DEFAULT 0,
    lifetime_pf INTEGER DEFAULT 0,

    pf_type TEXT,
    last_active TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    completed_pf INTEGER,
    payment_date TEXT
)
""")

conn.commit()