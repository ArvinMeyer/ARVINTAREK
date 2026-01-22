# How to See Browser in Live Mode During Scans

## ✅ Changes Made

1. **Switched to Undetected ChromeDriver** - Both `browser.py` and `google_search.py` now use `undetected-chromedriver` instead of `webdriver-manager`
2. **Enabled Visible Browser Mode** - Changed `SELENIUM_HEADLESS=False` in `.env` file
3. **Fixed ChromeDriver Issues** - No more WinError 193 or SSL download errors

## 🎬 What You'll See Now

When you start a scan, you will see:
- ✅ Chrome browser window opens automatically
- ✅ Watch the browser navigate to each URL
- ✅ See the page loading and scrolling in real-time
- ✅ Observe the email extraction process live

## 📋 How to Test

### Option 1: Quick Test with Sample URLs

1. **Restart the server** (already done)
2. **Open dashboard**: http://127.0.0.1:5000
3. **Click "New Scan"**
4. **Paste these test URLs**:
   ```
   https://example.com
   https://www.iana.org
   ```
5. **Click "Create Scan"** then **"Start Scan"**
6. **Watch the browser window open** and navigate to each URL!

### Option 2: Test with HVAC Companies

1. Manually search Google for: `"HVAC Technician" "New York" contact`
2. Copy 3-5 company website URLs
3. Create a new scan with those URLs
4. Watch the browser extract emails in real-time!

## ⚠️ Important Notes

- **First Run**: undetected-chromedriver will download ChromeDriver on first use (may take a moment)
- **Browser Window**: Don't close the browser window manually - let the scanner control it
- **Multiple Threads**: If you set threads > 1, multiple browser windows will open simultaneously
- **Headless Mode**: To go back to background mode, change `SELENIUM_HEADLESS=True` in `.env`

## 🔧 Troubleshooting

If you still see errors:
1. Make sure Chrome browser is installed
2. Check that no antivirus is blocking ChromeDriver
3. Try with `threads=1` for single browser window
4. Check logs for detailed error messages

## 🎯 Next Steps

The server is restarting now with these changes. Once it's running:
1. Go to http://127.0.0.1:5000
2. Create a new scan
3. Watch the magic happen! 🚀
