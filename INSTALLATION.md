# Installation Guide

Complete step-by-step installation instructions for the Email Extraction & Verification System.

## System Requirements

### Operating System
- Windows 10/11
- Ubuntu 20.04+ (Linux)
- macOS 11+ (Big Sur or later)

### Software Requirements
- **Python 3.10 or higher** (required)
- **Google Chrome** (latest version)
- **Internet connection** (for ChromeDriver download and email verification)

### Hardware Requirements
- **RAM:** Minimum 4GB (8GB recommended)
- **Storage:** 500MB free space
- **CPU:** Multi-core processor recommended for multi-threading

## Installation Steps

### 1. Install Python

#### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run installer and **check "Add Python to PATH"**
3. Verify installation:
```powershell
python --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip
python3.10 --version
```

#### macOS
```bash
brew install python@3.10
python3.10 --version
```

### 2. Install Google Chrome

Download and install from [google.com/chrome](https://www.google.com/chrome/)

ChromeDriver will be automatically downloaded by the application.

### 3. Download Project

Navigate to your project directory:
```powershell
cd c:\tarekscrab
```

### 4. Create Virtual Environment

#### Windows
```powershell
python -m venv venv
venv\Scripts\activate
```

#### Linux/macOS
```bash
python3.10 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### 5. Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install:
- selenium (browser automation)
- flask (web framework)
- sqlalchemy (database ORM)
- dnspython (DNS lookups)
- python-whois (domain age checking)
- beautifulsoup4 (HTML parsing)
- And more...

### 6. Configure Environment

```powershell
copy .env.example .env
```

Edit `.env` file with your settings:

```env
# Database
DATABASE_PATH=data/emails.db

# Flask
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
SECRET_KEY=your-random-secret-key-here

# Selenium
SELENIUM_HEADLESS=True

# Email Sender (Optional)
SENDER_SMTP_HOST=smtp.gmail.com
SENDER_SMTP_PORT=587
SENDER_SMTP_USER=your-email@gmail.com
SENDER_SMTP_PASSWORD=your-app-password
```

**For Gmail:**
1. Enable 2-factor authentication
2. Generate app-specific password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Use app password in `.env`

### 7. Initialize Database

```powershell
python main.py init-db
```

Expected output:
```
INFO - Initializing database...
INFO - Database initialized successfully
```

### 8. Start Application

```powershell
python main.py dashboard
```

Expected output:
```
INFO - Starting dashboard on http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

### 9. Access Dashboard

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

You should see the Email Extraction System dashboard!

## Verification

### Test Installation

1. **Check Dashboard:** Navigate to `http://127.0.0.1:5000`
2. **Create Test Scan:** Go to "New Scan" and add a test URL
3. **Check Logs:** Verify `logs/app.log` is being created
4. **Check Database:** Verify `data/emails.db` exists

### Common Issues

#### Issue: "Python not found"
**Solution:** Ensure Python is in PATH. Restart terminal after installation.

#### Issue: "pip not found"
**Solution:**
```powershell
python -m ensurepip --upgrade
```

#### Issue: "ChromeDriver download failed"
**Solution:** 
- Check internet connection
- Manually download from [chromedriver.chromium.org](https://chromedriver.chromium.org/)
- Place in project root

#### Issue: "Port 5000 already in use"
**Solution:**
```powershell
python main.py dashboard --port 8080
```

#### Issue: "Module not found"
**Solution:**
```powershell
# Ensure virtual environment is activated
venv\Scripts\activate
# Reinstall dependencies
pip install -r requirements.txt
```

## Updating

To update the application:

```powershell
# Activate virtual environment
venv\Scripts\activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart application
python main.py dashboard
```

## Uninstallation

1. Deactivate virtual environment:
```powershell
deactivate
```

2. Delete project directory:
```powershell
cd ..
rmdir /s tarekscrab
```

## Next Steps

- Read [README.md](README.md) for usage instructions
- Configure settings in `.env`
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment

## Support

If you encounter issues:
1. Check `logs/app.log` for errors
2. Verify all dependencies are installed
3. Ensure Chrome and Python versions are compatible
4. Check firewall/antivirus settings

---

**Installation complete!** You're ready to start extracting and validating emails.
