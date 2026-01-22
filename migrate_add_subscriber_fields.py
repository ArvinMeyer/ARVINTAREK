"""
Migration script to add subscriber fields to emails_valid table
"""
import sys
from sqlalchemy import text
from utils.db import get_db_session, engine
from utils.logger import get_logger

logger = get_logger(__name__)

def migrate():
    """Add subscriber fields to emails_valid table"""
    db = get_db_session()
    
    try:
        logger.info("Starting migration: Adding subscriber fields to emails_valid table")
        
        # Check if columns already exist
        inspector = __import__('sqlalchemy').inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('emails_valid')]
        
        if 'subscribed' not in columns:
            logger.info("Adding 'subscribed' column...")
            db.execute(text("ALTER TABLE emails_valid ADD COLUMN subscribed BOOLEAN DEFAULT 1"))
            db.commit()
            logger.info("✓ Added 'subscribed' column")
        else:
            logger.info("'subscribed' column already exists")
        
        if 'unsubscribed_at' not in columns:
            logger.info("Adding 'unsubscribed_at' column...")
            db.execute(text("ALTER TABLE emails_valid ADD COLUMN unsubscribed_at DATETIME"))
            db.commit()
            logger.info("✓ Added 'unsubscribed_at' column")
        else:
            logger.info("'unsubscribed_at' column already exists")
        
        if 'unsubscribe_token' not in columns:
            logger.info("Adding 'unsubscribe_token' column...")
            db.execute(text("ALTER TABLE emails_valid ADD COLUMN unsubscribe_token VARCHAR(100)"))
            db.commit()
            logger.info("✓ Added 'unsubscribe_token' column")
            
            # Create index on unsubscribe_token
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_unsubscribe_token ON emails_valid(unsubscribe_token)"))
                db.commit()
                logger.info("✓ Created index on 'unsubscribe_token'")
            except Exception as e:
                logger.warning(f"Could not create index (may already exist): {e}")
        else:
            logger.info("'unsubscribe_token' column already exists")
        
        # Set default subscribed=True for existing records
        try:
            result = db.execute(text("UPDATE emails_valid SET subscribed = 1 WHERE subscribed IS NULL"))
            db.commit()
            logger.info(f"✓ Updated {result.rowcount} existing records to subscribed=True")
        except Exception as e:
            logger.warning(f"Could not update existing records: {e}")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == '__main__':
    migrate()

