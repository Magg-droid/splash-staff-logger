import sqlite3
import os

# Create data folder if it doesn't exist
os.makedirs(
    "data",
    exist_ok=True
)

conn = sqlite3.connect(
    "data/staff.db"
)

cursor = conn.cursor()


# Staff table
cursor.execute("""
CREATE TABLE IF NOT EXISTS staff(

    user_id INTEGER PRIMARY KEY,
    username TEXT,
    current_pf INTEGER,
    lifetime_pf INTEGER,
    pf_type TEXT,
    last_active TEXT

)
""")


# Payment history table
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
