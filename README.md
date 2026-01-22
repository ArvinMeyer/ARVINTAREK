# Email Extraction & Verification System

A complete production-ready Python application for automated email extraction, multi-stage validation, and permission-based bulk email sending with a modern web dashboard.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ⚠️ Legal Notice

**IMPORTANT:** This tool is designed ONLY for scanning websites where you have explicit permission. 

- ❌ Do NOT bypass CAPTCHAs or security controls
- ❌ Do NOT scrape Google or other protected search engines  
- ❌ Do NOT violate terms of service of any platform
- ✅ ONLY use for permission-based, opt-in email campaigns
- ✅ Ensure compliance with GDPR, CAN-SPAM, and applicable regulations

## 🚀 Features

### 📊 Web Dashboard
- Real-time statistics and analytics
- Live scan progress monitoring
- Interactive data tables with pagination
- CSV export functionality
- Database management tools

### 🌐 Intelligent Web Scraper
- Selenium ChromeDriver automation
- Multi-threaded concurrent scanning
- User-agent rotation
- Auto page scrolling for dynamic content
- Configurable delays and rate limiting

### ✅ Multi-Stage Email Validation
1. **Regex Validation** - RFC 5322 compliant format checking
2. **Disposable Domain Filter** - Block temporary email services
3. **DNS Validation** - A and MX record verification
4. **SMTP Handshake** - Real mailbox verification
5. **WHOIS Domain Age** - Filter newly created domains
6. **SSL Certificate** - Domain security validation

### 📧 Bulk Email Sender
- SMTP integration with TLS support
- Rate limiting and throttling
- Jinja2 template engine
- Attachment support
- Delivery tracking and reporting
- Campaign management

### 💾 Database
- SQLite with SQLAlchemy ORM
- 7 tables with full relationships
- Automatic schema creation
- Data export capabilities

## 📁 Project Structure

```
project/
│── dashboard/          # Flask web application
│   ├── app.py
│   ├── templates/      # HTML templates
│   └── static/         # CSS/JS assets
│── scraper/            # Web scraping module
│   ├── browser.py      # Selenium automation
│   ├── parser.py       # HTML parsing
│   ├── extractor.py    # Email extraction
│   └── scanner.py      # Multi-threaded orchestrator
│── validator/          # Email validation module
│   ├── validator.py    # Validation stages
│   └── pipeline.py     # Batch processing
│── emailer/            # Bulk email sender
│   └── sender.py       # SMTP integration
│── utils/              # Utilities
│   ├── db.py          # Database models
│   ├── logger.py      # Logging system
│   └── helpers.py     # Helper functions
│── main.py            # Application entry point
│── config.py          # Configuration management
│── requirements.txt   # Python dependencies
└── .env.example       # Environment variables template
```

## 🛠️ Installation

### Prerequisites
- Python 3.10 or higher
- Google Chrome browser
- Internet connection

### Quick Start

1. **Clone or download the project**
```bash
cd c:\tarekscrab
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
copy .env.example .env
# Edit .env with your settings
```

5. **Initialize database**
```bash
python main.py init-db
```

6. **Start dashboard**
```bash
python main.py dashboard
```

7. **Open browser**
```
http://127.0.0.1:5000
```

## ⚙️ Configuration

Edit `.env` file to customize settings:

### Scraper Settings
```env
SCRAPER_THREADS=3              # Number of concurrent threads
SCRAPER_MIN_DELAY=1.0          # Minimum delay between requests (seconds)
SCRAPER_MAX_DELAY=3.0          # Maximum delay between requests (seconds)
SELENIUM_HEADLESS=True         # Run browser in headless mode
```

### Validation Settings
```env
VALIDATION_ENABLE_REGEX=True        # Enable regex validation
VALIDATION_ENABLE_DNS=True          # Enable DNS checks
VALIDATION_ENABLE_SMTP=True         # Enable SMTP verification
VALIDATION_ENABLE_WHOIS=False       # Enable WHOIS domain age check
MIN_DOMAIN_AGE_DAYS=30             # Minimum domain age (days)
```

### Email Sender Settings
```env
SENDER_SMTP_HOST=smtp.gmail.com
SENDER_SMTP_PORT=587
SENDER_SMTP_USER=your-email@gmail.com
SENDER_SMTP_PASSWORD=your-app-password
SENDER_EMAILS_PER_HOUR=100         # Rate limit
```

## 📖 Usage

### 1. Create Scan Job

Navigate to **New Scan** and enter:
- URLs to scan (one per line)
- Number of threads
- Maximum crawl depth

Example URLs:
```
https://example.com
https://example.com/contact
https://example.com/about
```

### 2. Start Scanning

Click **Start Scan** to begin extraction. Monitor progress in real-time.

### 3. Validate Emails

Click **Validate Pending** to run the validation pipeline on extracted emails.

### 4. Export Results

Navigate to **Valid Emails** and click **Export to CSV** to download results.

### 5. Send Campaigns (Optional)

Configure SMTP settings and create email campaigns from the **Email Sender** page.

## 🎯 Input Patterns

The system supports flexible input patterns for targeted extraction:

```
"info@?*?.com" "HVACTechnician" "New York"
"contact@?*?.com" "Electrician" "California"
"sales@?*?.com" "Plumber" "Texas"
```

**Note:** These patterns should only be used on websites you have permission to scan, NOT on search engines.

## 📊 Dashboard Features

### Statistics Cards
- Total pages scanned
- Total emails found
- Valid emails count
- Invalid emails count
- Validation success rate

### Scan Management
- Create new scan jobs
- Monitor active scans
- View scan results
- Pause/resume/stop scans

### Email Management
- View valid emails with metadata
- View invalid emails with rejection reasons
- Export to CSV
- Pagination support

### Database Admin
- Purge all data
- View logs
- Export reports

## 🔧 Advanced Usage

### Command Line Interface

```bash
# Start dashboard
python main.py dashboard

# Start on custom host/port
python main.py dashboard --host 0.0.0.0 --port 8080

# Enable debug mode
python main.py dashboard --debug

# Initialize database
python main.py init-db
```

### Programmatic Usage

```python
from scraper.scanner import Scanner
from validator.pipeline import ValidationPipeline

# Create scan job
scanner = Scanner(scan_job_id=1)
scanner.start(['https://example.com'], num_threads=3)
scanner.wait()

# Validate emails
pipeline = ValidationPipeline()
stats = pipeline.validate_all_pending()
print(f"Valid: {stats['valid']}, Invalid: {stats['invalid']}")
```

## 🐛 Troubleshooting

### ChromeDriver Issues
```bash
# The system auto-downloads ChromeDriver via webdriver-manager
# If issues persist, manually download from:
# https://chromedriver.chromium.org/
```

### SMTP Authentication Errors
- Use app-specific passwords for Gmail
- Enable "Less secure app access" if required
- Check firewall/antivirus settings

### Database Locked Errors
- Close all connections before purging
- Restart the application
- Check file permissions

## 📝 License

MIT License - Use responsibly and legally.

## 🤝 Contributing

This is a complete, production-ready system. Contributions welcome for:
- Additional validation stages
- New export formats
- UI improvements
- Performance optimizations

## ⚡ Performance

- **Scanning:** 3-10 pages/minute (depending on threads)
- **Validation:** 100-500 emails/minute
- **Sending:** Configurable rate limiting (default: 100/hour)

## 🔒 Security

- All data stored locally in SQLite
- No external API calls (except DNS/WHOIS)
- SMTP credentials stored in .env (never committed)
- Rate limiting prevents blacklisting

## 📞 Support

For issues or questions:
1. Check the logs in `logs/app.log`
2. Review configuration in `.env`
3. Ensure all dependencies are installed
4. Verify Chrome and ChromeDriver compatibility

---

**Remember:** Always use this tool ethically and legally. Respect website terms of service and privacy regulations.
