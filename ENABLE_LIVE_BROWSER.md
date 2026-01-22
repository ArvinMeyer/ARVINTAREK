# Enable Live Browser Mode (Non-Headless)

## What is Live Browser Mode?

When you enable live browser mode, you will **see the Chrome browser window open** and watch the entire Google search process happen in real-time. This is useful for:

1. **Debugging** - See exactly what's happening
2. **CAPTCHA Solving** - Manually solve CAPTCHAs if Google challenges you
3. **Less Detection** - Visible browsers are less likely to be flagged as bots
4. **Transparency** - Watch the automation work

## How to Enable

### Step 1: Edit Your `.env` File

1. Open the file `c:\tarekscrab\.env` in a text editor
2. Find the line that says:
   ```
   SELENIUM_HEADLESS=True
   ```
3. Change it to:
   ```
   SELENIUM_HEADLESS=False
   ```
4. Save the file

### Step 2: Restart Your Application

1. Stop the running server (press `Ctrl+C` in the terminal)
2. Start it again:
   ```bash
   python main.py
   ```

### Step 3: Try Google Search Again

1. Go to the dashboard: http://127.0.0.1:5000
2. Click "Google Search"
3. Enter your search query
4. Click "Search"

**You should now see a Chrome browser window open!** 🎉

## What You'll See

When the browser opens, you'll see:
1. Chrome window appears
2. Google homepage loads
3. Your search query is entered
4. Results page loads
5. The page scrolls automatically
6. URLs are extracted
7. Browser closes

## If You See a CAPTCHA

If Google shows a CAPTCHA challenge:
1. **Don't panic!** This is normal
2. **Solve the CAPTCHA manually** in the browser window
3. The script will continue automatically after you solve it
4. The browser will stay open until the process completes

## Troubleshooting

### Browser Opens But Immediately Closes
- The ChromeDriver download might have failed
- Check the logs for errors
- See the "Manual ChromeDriver Installation" section below

### Browser Doesn't Open At All
- Make sure you saved the `.env` file
- Restart the application
- Check that `SELENIUM_HEADLESS=False` (no quotes, capital F)

### Browser Opens But Shows Errors
- Your Chrome browser might be outdated
- Update Chrome to the latest version
- Restart and try again

## Manual ChromeDriver Installation (If Auto-Download Fails)

The error you're seeing suggests ChromeDriver auto-download is failing. Here's how to install it manually:

### Option 1: Quick Fix (Recommended)

1. **Download ChromeDriver manually**:
   - Go to: https://googlechromelabs.github.io/chrome-for-testing/
   - Download the version matching your Chrome browser
   - For Windows: Download `chromedriver-win64.zip`

2. **Extract and place ChromeDriver**:
   - Extract the ZIP file
   - Copy `chromedriver.exe` to: `C:\Windows\System32\`
   - OR place it in your project folder: `c:\tarekscrab\`

3. **Restart the application**

### Option 2: Use Pre-Installed ChromeDriver

If you already have ChromeDriver installed:

1. Find where it's located (e.g., `C:\chromedriver\chromedriver.exe`)
2. Add it to your system PATH
3. Restart your terminal and application

### Option 3: Disable Auto-Download

Modify `scraper/google_search.py` to use a specific ChromeDriver path:

```python
# Instead of:
self.driver = uc.Chrome(options=options, version_main=None)

# Use:
self.driver = uc.Chrome(
    options=options, 
    driver_executable_path=r'C:\path\to\chromedriver.exe'
)
```

## Current Issue: ChromeDriver Download Failing

The error you're seeing:
```
Failed to start ChromeDriver: <urlopen error [WinError 10054]>
```

This means the **automatic download of ChromeDriver is being blocked**. This is the same network issue as the Google search problem.

### Solutions (in order of recommendation):

1. **Install ChromeDriver manually** (see above) - **BEST SOLUTION**
2. **Use a VPN** to download ChromeDriver
3. **Download on a different network** (mobile hotspot)
4. **Wait and try again later** (network might be temporarily blocking)

## Benefits of Live Browser Mode

✅ **See what's happening** - Full transparency  
✅ **Solve CAPTCHAs** - Manual intervention when needed  
✅ **Less bot detection** - Visible browsers are more "human"  
✅ **Better debugging** - Watch errors happen in real-time  
✅ **Learn the process** - Understand how the scraper works  

## Drawbacks

❌ **Slower** - Browser rendering takes time  
❌ **Resource intensive** - Uses more CPU/RAM  
❌ **Requires display** - Can't run on headless servers  
❌ **Less parallel** - Harder to run multiple instances  

## Recommended Settings for Live Mode

Edit your `.env` file:

```env
# Enable live browser
SELENIUM_HEADLESS=False

# Increase timeouts for manual interaction
SELENIUM_PAGE_LOAD_TIMEOUT=120
SELENIUM_IMPLICIT_WAIT=20

# Slower scraping (more human-like)
SCRAPER_MIN_DELAY=2.0
SCRAPER_MAX_DELAY=5.0
```

## Going Back to Headless Mode

To switch back to headless mode (no browser window):

1. Edit `.env`
2. Change `SELENIUM_HEADLESS=False` back to `SELENIUM_HEADLESS=True`
3. Restart the application

---

**Quick Start Command:**

```bash
# Stop current server (Ctrl+C)
# Edit .env and set SELENIUM_HEADLESS=False
# Then restart:
python main.py
```

**Next Steps:**
1. Enable live browser mode (set `SELENIUM_HEADLESS=False`)
2. Install ChromeDriver manually (if auto-download keeps failing)
3. Try Google search again and watch it work!
