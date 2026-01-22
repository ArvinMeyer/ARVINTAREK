"""
Configuration management for Email Extraction System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'data' / 'emails.db'))
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# Flask Configuration
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')  # 0.0.0.0 allows access from network
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Get local IP address for BASE_URL if not explicitly set
def get_local_ip():
    """Get the local IP address for network access"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

# BASE_URL for unsubscribe links - use local IP if running on network
BASE_URL = os.getenv('BASE_URL', None)
if BASE_URL is None:
    # Auto-detect: use local IP if host is 0.0.0.0, otherwise use localhost
    if FLASK_HOST == '0.0.0.0':
        local_ip = get_local_ip()
        BASE_URL = f'http://{local_ip}:{FLASK_PORT}'
    else:
        BASE_URL = f'http://{FLASK_HOST}:{FLASK_PORT}'

# Selenium Configuration
SELENIUM_HEADLESS = os.getenv('SELENIUM_HEADLESS', 'True').lower() == 'true'
SELENIUM_TIMEOUT = int(os.getenv('SELENIUM_TIMEOUT', 30))
SELENIUM_PAGE_LOAD_TIMEOUT = int(os.getenv('SELENIUM_PAGE_LOAD_TIMEOUT', 60))
SELENIUM_IMPLICIT_WAIT = int(os.getenv('SELENIUM_IMPLICIT_WAIT', 10))

# User Agents Pool
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Scraper Configuration
SCRAPER_THREADS = int(os.getenv('SCRAPER_THREADS', 3))
SCRAPER_MIN_DELAY = float(os.getenv('SCRAPER_MIN_DELAY', 1.0))
SCRAPER_MAX_DELAY = float(os.getenv('SCRAPER_MAX_DELAY', 3.0))
SCRAPER_MAX_DEPTH = int(os.getenv('SCRAPER_MAX_DEPTH', 2))
SCRAPER_SCROLL_PAUSE = float(os.getenv('SCRAPER_SCROLL_PAUSE', 0.5))

# Email Validation Configuration
VALIDATION_ENABLE_REGEX = os.getenv('VALIDATION_ENABLE_REGEX', 'True').lower() == 'true'
VALIDATION_ENABLE_DISPOSABLE = os.getenv('VALIDATION_ENABLE_DISPOSABLE', 'True').lower() == 'true'
VALIDATION_ENABLE_DNS = os.getenv('VALIDATION_ENABLE_DNS', 'True').lower() == 'true'
VALIDATION_ENABLE_SMTP = os.getenv('VALIDATION_ENABLE_SMTP', 'True').lower() == 'true'
VALIDATION_ENABLE_WHOIS = os.getenv('VALIDATION_ENABLE_WHOIS', 'False').lower() == 'true'
VALIDATION_ENABLE_SSL = os.getenv('VALIDATION_ENABLE_SSL', 'False').lower() == 'true'
VALIDATION_THREADS = int(os.getenv('VALIDATION_THREADS', 10))  # Number of parallel validation threads

# SMTP Validation Settings
SMTP_TIMEOUT = int(os.getenv('SMTP_TIMEOUT', 10))
SMTP_VERIFY_DELAY = float(os.getenv('SMTP_VERIFY_DELAY', 0.5))
SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL', 'verify@example.com')

# Email Sender SMTP Settings
SENDER_SMTP_TIMEOUT = int(os.getenv('SENDER_SMTP_TIMEOUT', 30))  # Timeout for sending emails (seconds)

# Domain Age Settings (days)
MIN_DOMAIN_AGE_DAYS = int(os.getenv('MIN_DOMAIN_AGE_DAYS', 30))

# Disposable Email Domains (common ones)
DISPOSABLE_DOMAINS = {
    'tempmail.com', 'guerrillamail.com', '10minutemail.com', 'mailinator.com',
    'throwaway.email', 'temp-mail.org', 'getnada.com', 'maildrop.cc',
    'trashmail.com', 'yopmail.com', 'fakeinbox.com', 'sharklasers.com'
}

# Email Sender Configuration
SENDER_SMTP_HOST = os.getenv('SENDER_SMTP_HOST', '')
SENDER_SMTP_PORT = int(os.getenv('SENDER_SMTP_PORT', 587))
SENDER_SMTP_USER = os.getenv('SENDER_SMTP_USER', '')
SENDER_SMTP_PASSWORD = os.getenv('SENDER_SMTP_PASSWORD', '')
SENDER_SMTP_USE_TLS = os.getenv('SENDER_SMTP_USE_TLS', 'True').lower() == 'true'
SENDER_FROM_EMAIL = os.getenv('SENDER_FROM_EMAIL', '')
SENDER_FROM_NAME = os.getenv('SENDER_FROM_NAME', '')

# Rate Limiting for Email Sender
SENDER_EMAILS_PER_HOUR = int(os.getenv('SENDER_EMAILS_PER_HOUR', 100))
SENDER_MIN_DELAY = float(os.getenv('SENDER_MIN_DELAY', 2.0))
SENDER_MAX_DELAY = float(os.getenv('SENDER_MAX_DELAY', 5.0))
SENDER_BATCH_SIZE = int(os.getenv('SENDER_BATCH_SIZE', 10))
SENDER_BATCH_DELAY = float(os.getenv('SENDER_BATCH_DELAY', 60.0))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'app.log'
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))

# Export Configuration
EXPORT_DIR = BASE_DIR / 'exports'

# Ensure directories exist
os.makedirs(BASE_DIR / 'data', exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
