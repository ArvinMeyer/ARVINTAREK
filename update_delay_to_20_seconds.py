"""
Update existing campaigns to use 20 seconds delay instead of 2 seconds
"""
import sqlite3
import config
from pathlib import Path

# Get database path from config
DB_PATH = Path(config.DATABASE_PATH)

if not DB_PATH.exists():
    print(f"Database not found at {DB_PATH}")
    exit(1)

print(f"Connecting to database: {DB_PATH}")
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

try:
    # Update all campaigns that have delay_seconds = 2.0 or NULL to 20.0
    cursor.execute("""
        UPDATE send_reports 
        SET delay_seconds = 20.0 
        WHERE delay_seconds IS NULL OR delay_seconds = 2.0
    """)
    updated_count = cursor.rowcount
    conn.commit()
    print(f"✓ Updated {updated_count} campaign(s) to use 20 seconds delay")
    
except Exception as e:
    conn.rollback()
    print(f"✗ Error: {e}")
    exit(1)
finally:
    conn.close()

print("Update completed successfully!")

