"""
Migration script to add delay_seconds column to send_reports table
"""
import sqlite3
import os
from pathlib import Path
import config

# Get database path from config
DB_PATH = Path(config.DATABASE_PATH)

if not DB_PATH.exists():
    print(f"Database not found at {DB_PATH}")
    exit(1)

print(f"Connecting to database: {DB_PATH}")
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(send_reports)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'delay_seconds' in columns:
        print("Column 'delay_seconds' already exists. Skipping migration.")
    else:
        print("Adding 'delay_seconds' column to send_reports table...")
        cursor.execute("""
            ALTER TABLE send_reports 
            ADD COLUMN delay_seconds REAL DEFAULT 2.0
        """)
        conn.commit()
        print("✓ Successfully added 'delay_seconds' column with default value 2.0")
        
        # Update existing records to have default delay
        cursor.execute("UPDATE send_reports SET delay_seconds = 2.0 WHERE delay_seconds IS NULL")
        conn.commit()
        print("✓ Updated existing records with default delay value")
        
except Exception as e:
    conn.rollback()
    print(f"✗ Error: {e}")
    exit(1)
finally:
    conn.close()

print("Migration completed successfully!")

