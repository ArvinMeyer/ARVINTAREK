# ChromeDriver Manual Installation Guide

## The Problem

Your network is blocking the automatic download of ChromeDriver, causing this error:
```
Failed to start ChromeDriver: <urlopen error [WinError 10054]>
```

This happens **before** any Google search can even start. The solution is to install ChromeDriver manually.

---

## ✅ Quick Installation (5 minutes)

### Step 1: Check Your Chrome Version

1. Open Google Chrome browser
2. Click the three dots (⋮) in the top-right corner
3. Go to: **Help** → **About Google Chrome**
4. Note your version number (e.g., `131.0.6778.86`)

### Step 2: Download ChromeDriver

**Option A: Latest Stable (Recommended)**
1. Visit: https://googlechromelabs.github.io/chrome-for-testing/
2. Scroll down to "Stable" section
3. Find "chromedriver" for "win64"
4. Click the download link
5. Save the ZIP file

**Option B: Specific Version**
1. Visit: https://googlechromelabs.github.io/chrome-for-testing/
2. Use the JSON endpoints to find your exact Chrome version
3. Download the matching ChromeDriver

**Option C: Older Chrome Versions (< 115)**
1. Visit: https://chromedriver.chromium.org/downloads
2. Find the version matching your Chrome
3. Download for Windows

### Step 3: Extract ChromeDriver

1. Locate the downloaded ZIP file (usually in `Downloads` folder)
2. Right-click → **Extract All**
3. You should see `chromedriver.exe` inside

### Step 4: Install ChromeDriver

**Method 1: System-Wide (Recommended)**
1. Copy `chromedriver.exe`
2. Paste it into: `C:\Windows\System32\`
3. If prompted for admin permission, click **Yes**

**Method 2: Project Folder**
1. Copy `chromedriver.exe`
2. Paste it into: `c:\tarekscrab\`
3. No admin permission needed

**Method 3: Custom Location + PATH**
1. Create folder: `C:\chromedriver\`
2. Copy `chromedriver.exe` there
3. Add to system PATH:
   - Press `Win + R`
   - Type: `sysdm.cpl` → Enter
   - Click **Environment Variables**
   - Under "System variables", find **Path**
   - Click **Edit** → **New**
   - Add: `C:\chromedriver\`
   - Click **OK** on all dialogs

### Step 5: Verify Installation

Open Command Prompt and run:
```bash
chromedriver --version
```

You should see something like:
```
ChromeDriver 131.0.6778.86 (...)
```

If you see this, installation was successful! ✅

### Step 6: Restart Your Application

1. Go back to your terminal running the app
2. Press `Ctrl+C` to stop the server
3. Restart:
   ```bash
   python main.py
   ```

### Step 7: Test Google Search

1. Go to: http://127.0.0.1:5000
2. Click **Google Search**
3. Enter a search query
4. Click **Search**

**If you enabled live browser mode** (`SELENIUM_HEADLESS=False`), you should now see Chrome open! 🎉

---

## 🔧 Troubleshooting

### "chromedriver is not recognized"
- ChromeDriver is not in your PATH
- Try Method 1 (copy to System32) instead
- Or restart your terminal after adding to PATH

### "ChromeDriver version mismatch"
- Your ChromeDriver version doesn't match Chrome
- Download the correct version for your Chrome
- Check Chrome version: `chrome://settings/help`

### "Access denied" when copying to System32
- Right-click Command Prompt → **Run as Administrator**
- Or use Method 2 (project folder) instead

### Still getting WinError 10054
- This means ChromeDriver is still trying to auto-download
- Make sure you placed `chromedriver.exe` in the correct location
- Verify with: `chromedriver --version`
- Restart the application completely

### Browser opens but immediately closes
- ChromeDriver is working!
- The issue is now with Google search itself
- See `GOOGLE_SEARCH_TROUBLESHOOTING.md` for next steps

---

## 🚀 Alternative: Skip Google Search Entirely

If ChromeDriver installation is too complex, you can bypass it:

### Manual URL Entry Method

1. **Search Google manually** in your regular browser:
   ```
   "info@*.com" "HVAC Technician" "New York"
   ```

2. **Copy URLs** from search results (company websites)

3. **Go to Dashboard**: http://127.0.0.1:5000

4. **Click "New Scan"**

5. **Paste URLs** (one per line):
   ```
   https://example-hvac.com
   https://another-company.com
   https://third-company.com
   ```

6. **Click "Start Scan"**

The system will still extract emails from these URLs - you just skip the automated Google search part!

---

## 📊 What Changed

The code now has **two fallback strategies**:

1. **Strategy 1**: Try auto-download (default)
   - If this fails → try Strategy 2

2. **Strategy 2**: Use system ChromeDriver (bypass auto-download)
   - Looks for manually installed ChromeDriver
   - If this fails → show detailed error message

When you install ChromeDriver manually, **Strategy 2 will succeed** and you'll see:
```
✓ ChromeDriver started successfully (system ChromeDriver)
```

---

## 🎯 Summary

**The Issue**: Network blocking ChromeDriver auto-download  
**The Fix**: Install ChromeDriver manually  
**Time Required**: 5 minutes  
**Difficulty**: Easy (just download and copy a file)

**After installation**, you'll be able to:
- ✅ Use Google Search automation
- ✅ See the browser open (if `SELENIUM_HEADLESS=False`)
- ✅ Watch the entire scraping process
- ✅ Manually solve CAPTCHAs if needed

---

## 📞 Need Help?

If you're still stuck:
1. Check the error messages in the terminal
2. Verify ChromeDriver installation: `chromedriver --version`
3. Make sure Chrome browser is up to date
4. Try the manual URL entry method as a workaround

**Remember**: The manual URL entry method works perfectly and doesn't require ChromeDriver at all!
