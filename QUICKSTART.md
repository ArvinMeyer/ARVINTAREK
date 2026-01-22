# 🚀 Quick Start Guide

Get the Email Extraction System running in 3 minutes!

## Option 1: Automated Setup (Recommended)

### Windows
```powershell
.\quickstart.bat
```

### Linux/macOS
```bash
chmod +x quickstart.sh
./quickstart.sh
```

The script will automatically:
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Create .env file
- ✅ Initialize database
- ✅ Start dashboard

## Option 2: Manual Setup

### Step 1: Create Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure
```powershell
copy .env.example .env
# Edit .env with your settings
```

### Step 4: Initialize Database
```powershell
python main.py init-db
```

### Step 5: Start Dashboard
```powershell
python main.py dashboard
```

### Step 6: Open Browser
```
http://127.0.0.1:5000
```

## First Scan

1. Click **"New Scan"**
2. Enter URLs (one per line):
   ```
   https://example.com
   https://example.com/contact
   ```
3. Click **"Create Scan Job"**
4. Click **"Start Scan"**
5. Watch emails being extracted!

## Validate Emails

1. Click **"Validate Pending"**
2. Wait for validation to complete
3. View results in **"Valid Emails"**

## Export Results

1. Navigate to **"Valid Emails"**
2. Click **"Export to CSV"**
3. Download your validated emails!

## Need Help?

- 📖 Full documentation: [README.md](README.md)
- 🔧 Installation guide: [INSTALLATION.md](INSTALLATION.md)
- 🚀 Deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- 📝 Implementation details: [walkthrough.md](walkthrough.md)

## Common Issues

### "Python not found"
Install Python 3.10+ from [python.org](https://www.python.org/downloads/)

### "Port 5000 already in use"
```powershell
python main.py dashboard --port 8080
```

### "ChromeDriver error"
Chrome will auto-download ChromeDriver. Ensure Chrome is installed.

---

**You're ready to go!** 🎉
