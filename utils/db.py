"""
Database models and setup for Email Extraction System
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import config

Base = declarative_base()

class ScanJob(Base):
    """Represents a scanning job"""
    __tablename__ = 'scan_jobs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    status = Column(String(50), default='pending')  # pending, running, paused, completed, failed
    urls = Column(Text)  # JSON array of URLs
    search_patterns = Column(Text)  # JSON array of search patterns
    threads = Column(Integer, default=3)
    max_depth = Column(Integer, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_pages = Column(Integer, default=0)
    total_emails = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    scan_results = relationship('ScanResult', back_populates='scan_job', cascade='all, delete-orphan')
    emails_raw = relationship('EmailRaw', back_populates='scan_job', cascade='all, delete-orphan')

class ScanResult(Base):
    """Represents the result of scanning a single URL"""
    __tablename__ = 'scan_results'
    
    id = Column(Integer, primary_key=True)
    scan_job_id = Column(Integer, ForeignKey('scan_jobs.id'), nullable=False)
    url = Column(String(500), nullable=False)
    status = Column(String(50))  # success, failed, skipped
    emails_found = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scan_job = relationship('ScanJob', back_populates='scan_results')

class EmailRaw(Base):
    """Stores raw extracted emails before validation"""
    __tablename__ = 'emails_raw'
    
    id = Column(Integer, primary_key=True)
    scan_job_id = Column(Integer, ForeignKey('scan_jobs.id'), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    source_url = Column(String(500))
    context = Column(Text)  # Surrounding text where email was found
    extracted_at = Column(DateTime, default=datetime.utcnow)
    validated = Column(Boolean, default=False)
    
    # Relationships
    scan_job = relationship('ScanJob', back_populates='emails_raw')
    valid_email = relationship('EmailValid', back_populates='raw_email', uselist=False)
    invalid_email = relationship('EmailInvalid', back_populates='raw_email', uselist=False)

class EmailValid(Base):
    """Stores validated emails"""
    __tablename__ = 'emails_valid'
    
    id = Column(Integer, primary_key=True)
    raw_email_id = Column(Integer, ForeignKey('emails_raw.id'), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    domain = Column(String(255), index=True)
    
    # Validation metadata
    has_mx_record = Column(Boolean, default=False)
    has_a_record = Column(Boolean, default=False)
    smtp_valid = Column(Boolean, default=False)
    is_catch_all = Column(Boolean, default=False)
    domain_age_days = Column(Integer, nullable=True)
    has_ssl = Column(Boolean, nullable=True)
    
    validated_at = Column(DateTime, default=datetime.utcnow)
    last_verified_at = Column(DateTime, default=datetime.utcnow)
    
    # Subscriber management
    subscribed = Column(Boolean, default=True)  # Default to subscribed
    unsubscribed_at = Column(DateTime, nullable=True)
    unsubscribe_token = Column(String(100), nullable=True, unique=True, index=True)
    
    # Relationships
    raw_email = relationship('EmailRaw', back_populates='valid_email')

class EmailInvalid(Base):
    """Stores invalid/rejected emails"""
    __tablename__ = 'emails_invalid'
    
    id = Column(Integer, primary_key=True)
    raw_email_id = Column(Integer, ForeignKey('emails_raw.id'), nullable=False, unique=True)
    email = Column(String(255), nullable=False, index=True)
    rejection_reason = Column(String(200))
    rejection_stage = Column(String(50))  # regex, disposable, dns, smtp, whois, ssl
    validated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    raw_email = relationship('EmailRaw', back_populates='invalid_email')

class SMTPConfig(Base):
    """Stores SMTP server configurations"""
    __tablename__ = 'smtp_configs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)  # Friendly name for this SMTP config
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(500), nullable=False)  # Encrypted in production
    use_tls = Column(Boolean, default=True)
    timeout = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email_accounts = relationship('EmailAccount', back_populates='smtp_config', cascade='all, delete-orphan')
    send_reports = relationship('SendReport', back_populates='smtp_config')

class EmailAccount(Base):
    """Stores email account configurations"""
    __tablename__ = 'email_accounts'
    
    id = Column(Integer, primary_key=True)
    smtp_config_id = Column(Integer, ForeignKey('smtp_configs.id'), nullable=False)
    name = Column(String(200), nullable=False)  # Friendly name for this email account
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(200), nullable=False)
    reply_to = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    smtp_config = relationship('SMTPConfig', back_populates='email_accounts')
    send_reports = relationship('SendReport', back_populates='email_account')

class SendReport(Base):
    """Tracks email sending campaigns"""
    __tablename__ = 'send_reports'
    
    id = Column(Integer, primary_key=True)
    campaign_name = Column(String(200), nullable=False)
    subject = Column(String(500))
    body_html = Column(Text)  # Email body HTML
    body_text = Column(Text)  # Email body plain text
    template_name = Column(String(200))
    status = Column(String(50), default='pending')  # pending, running, paused, completed, failed
    
    # Link to SMTP and Email account
    smtp_config_id = Column(Integer, ForeignKey('smtp_configs.id'), nullable=True)
    email_account_id = Column(Integer, ForeignKey('email_accounts.id'), nullable=True)
    
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    delay_seconds = Column(Float, default=20.0)  # Delay between emails in seconds
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    delivery_records = relationship('DeliveryRecord', back_populates='send_report', cascade='all, delete-orphan')
    smtp_config = relationship('SMTPConfig', back_populates='send_reports')
    email_account = relationship('EmailAccount', back_populates='send_reports')

class DeliveryRecord(Base):
    """Individual email delivery record"""
    __tablename__ = 'delivery_records'
    
    id = Column(Integer, primary_key=True)
    send_report_id = Column(Integer, ForeignKey('send_reports.id'), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    status = Column(String(50))  # sent, delivered, failed, bounced
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    send_report = relationship('SendReport', back_populates='delivery_records')

class GoogleSearchHistory(Base):
    """Tracks Google search URL extractions"""
    __tablename__ = 'google_search_history'
    
    id = Column(Integer, primary_key=True)
    queries = Column(Text, nullable=False)  # JSON array of search queries
    num_results_per_query = Column(Integer, default=10)
    total_urls_found = Column(Integer, default=0)
    urls = Column(Text)  # JSON array of extracted URLs
    scan_job_id = Column(Integer, ForeignKey('scan_jobs.id'), nullable=True)
    status = Column(String(50), default='completed')  # running, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    scan_job = relationship('ScanJob', foreign_keys=[scan_job_id])

# Database engine and session
engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """Get database session (for non-generator usage)"""
    return SessionLocal()
