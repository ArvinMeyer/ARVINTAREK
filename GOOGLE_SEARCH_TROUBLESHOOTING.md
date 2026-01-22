# Google Search Troubleshooting Guide

## WinError 10054: Connection Forcibly Closed

### What is this error?

The error `[WinError 10054] An existing connection was forcibly closed by the remote host` occurs when Google's servers forcibly close the connection during automated searches. This is typically a result of Google's anti-bot detection systems.

### Why does this happen?

1. **Rate Limiting**: Google detects too many requests from your IP address
2. **Bot Detection**: Google identifies automated browser behavior
3. **Network Issues**: Unstable internet connection or firewall interference
4. **CAPTCHA Challenges**: Google requires human verification

### Fixes Implemented

The following improvements have been made to handle this error:

#### 1. Retry Logic with Exponential Backoff
- Automatically retries failed requests up to 3 times
- Uses exponential backoff (3s, 6s, 12s) between retries
- Handles specific connection errors gracefully

#### 2. Longer Delays
- Increased delays between page loads (3-6 seconds instead of 2-4)
- Longer delays between multiple searches (8-15 seconds instead of 5-10)
- Additional delays after scrolling (1-2 seconds)

#### 3. Better Error Handling
- Catches `TimeoutException` and `WebDriverException` specifically
- Detects CAPTCHA and "unusual traffic" warnings
- Provides helpful error messages and suggestions

#### 4. Enhanced Anti-Detection
- Additional Chrome options for stability
- Better timeout management
- Connection state monitoring

### How to Use

The fixes are automatic - no code changes needed on your part. The system will now:

1. **Automatically retry** when connections fail
2. **Wait longer** between requests to avoid detection
3. **Provide better feedback** about what's happening

### If You Still Get Errors

If you continue to experience connection issues, try these solutions:

#### Solution 1: Increase Delays (Recommended)
Edit your `.env` file and add/modify:
```env
SELENIUM_PAGE_LOAD_TIMEOUT=90
SELENIUM_IMPLICIT_WAIT=15
```

#### Solution 2: Run in Non-Headless Mode
This allows you to see the browser and manually solve CAPTCHAs if needed:
```env
SELENIUM_HEADLESS=False
```

#### Solution 3: Use Fewer Queries
Instead of searching 10 queries at once, try 2-3 queries at a time.

#### Solution 4: Wait Between Sessions
If Google has flagged your IP:
- Wait 15-30 minutes before trying again
- Use a VPN or different network
- Switch to mobile hotspot temporarily

#### Solution 5: Manual URL Entry
Instead of using Google search, manually enter URLs:
1. Go to Dashboard → New Scan
2. Paste URLs directly (one per line)
3. Start the scan

### Understanding the Logs

When you see these messages, here's what they mean:

```
Connection forcibly closed by remote host (Attempt 1/3)
```
→ First attempt failed, automatically retrying...

```
Waiting 6s before retry...
```
→ System is waiting before the next attempt

```
Google detected unusual traffic
```
→ Google is showing a CAPTCHA or blocking page

```
Max retries reached. Last error: ...
```
→ All 3 attempts failed, manual intervention needed

### Best Practices

To minimize connection errors:

1. **Limit Search Volume**: Don't search too many queries in a short time
2. **Use Specific Queries**: More specific queries = fewer results = faster processing
3. **Schedule Searches**: Spread searches throughout the day
4. **Monitor Logs**: Watch for warning signs before errors occur
5. **Have Backup URLs**: Keep a list of URLs to scan manually if needed

### Technical Details

The retry logic works as follows:

```python
for attempt in range(3):  # Try up to 3 times
    try:
        # Attempt Google search
        driver.get(search_url)
        # ... extract URLs ...
        return urls  # Success!
    except WebDriverException as e:
        if "10054" in str(e):
            # Connection closed - wait and retry
            wait_time = (2 ** attempt) * 3  # 3s, 6s, 12s
            time.sleep(wait_time)
        else:
            raise  # Different error - don't retry
```

### Alternative: Use API-Based Search

For production use, consider using official search APIs:
- Google Custom Search API (100 free queries/day)
- Bing Search API
- DuckDuckGo API

These are more reliable and less likely to be blocked.

### Getting Help

If you continue to have issues:
1. Check the logs in `logs/app.log`
2. Look for specific error messages
3. Try the solutions above in order
4. Consider using manual URL entry as a fallback

---

**Last Updated**: 2026-01-06
**Related Files**: 
- `scraper/google_search.py` - Main search implementation
- `dashboard/app.py` - Web interface error handling
- `config.py` - Timeout and delay settings
