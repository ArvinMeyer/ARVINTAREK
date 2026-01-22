"""
Migration script to add SMTP configurations and Email accounts tables
Run this once to add the new tables to your database
"""
import sqlite3
import os
from pathlib import Path
import config

def migrate():
    """Add new tables for SMTP configs and email accounts"""
    db_path = Path(config.DATABASE_PATH)
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Create smtp_configs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smtp_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                host VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL,
                username VARCHAR(255) NOT NULL,
                password VARCHAR(500) NOT NULL,
                use_tls BOOLEAN DEFAULT 1,
                timeout INTEGER DEFAULT 30,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create email_accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                smtp_config_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                from_email VARCHAR(255) NOT NULL,
                from_name VARCHAR(200) NOT NULL,
                reply_to VARCHAR(255),
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (smtp_config_id) REFERENCES smtp_configs(id)
            )
        """)
        
        # Add new columns to send_reports table
        try:
            cursor.execute("ALTER TABLE send_reports ADD COLUMN smtp_config_id INTEGER")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Warning: Could not add smtp_config_id column: {e}")
        
        try:
            cursor.execute("ALTER TABLE send_reports ADD COLUMN email_account_id INTEGER")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Warning: Could not add email_account_id column: {e}")
        
        try:
            cursor.execute("ALTER TABLE send_reports ADD COLUMN body_html TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Warning: Could not add body_html column: {e}")
        
        try:
            cursor.execute("ALTER TABLE send_reports ADD COLUMN body_text TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Warning: Could not add body_text column: {e}")
        
        # Add foreign key constraints (SQLite doesn't enforce them, but good for documentation)
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_send_reports_smtp_config_id 
                ON send_reports(smtp_config_id)
            """)
        except:
            pass
        
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_send_reports_email_account_id 
                ON send_reports(email_account_id)
            """)
        except:
            pass
        
        conn.commit()
        print("✓ Migration completed successfully!")
        print("  - Created smtp_configs table")
        print("  - Created email_accounts table")
        print("  - Added smtp_config_id, email_account_id, body_html, body_text to send_reports table")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("Running migration to add SMTP and Email Account tables...")
    migrate()
    print("\nYou can now:")
    print("  1. Go to /smtp-configs to add SMTP configurations")
    print("  2. Go to /email-accounts to add email accounts")
    print("  3. Use them when creating campaigns")

