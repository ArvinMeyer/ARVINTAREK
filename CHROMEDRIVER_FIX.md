# ChromeDriver Fix Guide

## Problem
The Google Search feature is encountering an SSL error when trying to download ChromeDriver automatically.

## Quick Solution: Manual URL Entry (RECOMMENDED)

Instead of using Google Search automation, you can:

1. **Manually search Google** for your query:
   ```
   "info@*.com" "HVAC Technician" "New York"
   ```

2. **Copy the URLs** of HVAC company websites from the search results

3. **Go to the dashboard** at http://127.0.0.1:5000

4. **Click "New Scan"** and paste the URLs (one per line)

5. **Start the scan** - the system will extract emails automatically

## Alternative: Fix ChromeDriver (Advanced)

If you want to use automated Google Search:

### Option 1: Download ChromeDriver Manually

1. Check your Chrome browser version:
   - Open Chrome
   - Go to `chrome://settings/help`
   - Note the version number (e.g., 120.0.6099.109)

2. Download matching ChromeDriver:
   - Visit: https://chromedriver.chromium.org/downloads
   - Download the version matching your Chrome
   - For Chrome 115+, use: https://googlechromelabs.github.io/chrome-for-testing/

3. Install ChromeDriver:
   - Extract `chromedriver.exe`
   - Place it in: `C:\Windows\System32\` or add to PATH
   - Or place in project folder: `c:\tarekscrab\`

4. Restart the dashboard and try Google Search again

### Option 2: Use Alternative Browser Automation

The project includes `undetected-chromedriver` which should work better, but needs proper ChromeDriver installation first.

## Testing

After fixing, test with:
```bash
python test_google_hvac.py
```

This will verify ChromeDriver is working correctly.
