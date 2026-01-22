# Google Search URL Extraction Feature

## Overview

The Google Search URL Extraction feature allows you to automatically extract URLs from Google search results using an undetectable ChromeDriver. This is useful for finding websites to scan based on specific search criteria.

## How It Works

1. **Undetectable Mode**: Uses `undetected-chromedriver` to bypass Google's bot detection
2. **Search Queries**: Enter multiple search queries (one per line)
3. **URL Extraction**: Automatically extracts URLs from search results
4. **Rate Limiting**: Includes delays between searches to avoid rate limiting

## Usage

### Access the Feature

Navigate to **Google Search** in the dashboard menu or visit:
```
http://127.0.0.1:5000/google/search
```

### Example Search Queries

```
"info@*.com" "HVAC Technician" "New York"
"contact@*.com" "Electrician" "California"
"sales@*.com" "Plumber" "Texas"
construction companies "New York" email
plumbing services California contact
```

### Parameters

- **Search Queries**: One query per line
- **Results Per Query**: Number of URLs to extract (1-100, default: 10)

### Search Tips

1. **Use Quotes**: For exact phrase matching
   - `"HVAC Technician"` - exact match
   - `HVAC Technician` - any order

2. **Site Operator**: Search within specific domains
   - `site:company.com email contact`

3. **Combine Keywords**: Industry + Location + Contact
   - `"construction" "New York" "contact us"`

4. **Email Patterns**: Use wildcards in quotes
   - `"info@*.com"` - finds pages with email patterns

## Technical Details

### Module: `scraper/google_search.py`

**Class: `GoogleSearchExtractor`**

```python
from scraper.google_search import extract_urls_from_google

# Extract URLs from Google
queries = [
    '"info@*.com" "HVAC Technician" "New York"',
    '"contact@*.com" "Electrician" "California"'
]

urls = extract_urls_from_google(queries, num_results=20)
print(f"Extracted {len(urls)} URLs")
```

### Features

- ✅ Undetectable ChromeDriver (bypasses bot detection)
- ✅ Random user-agent rotation
- ✅ Automatic page scrolling
- ✅ Delay between searches (5-10 seconds)
- ✅ Duplicate URL removal
- ✅ Google redirect URL parsing

### Anti-Detection Measures

1. **Undetected ChromeDriver**: Uses `undetected-chromedriver` library
2. **Random Delays**: 2-4 seconds per page, 5-10 seconds between queries
3. **Human-like Behavior**: Scrolls page gradually
4. **User-Agent Rotation**: Random selection from pool
5. **No Automation Flags**: Removes webdriver detection properties

## Workflow

### Step 1: Extract URLs from Google

1. Go to **Google Search** page
2. Enter search queries (one per line)
3. Set number of results (e.g., 10)
4. Click **Extract URLs from Google**
5. Wait for extraction to complete

### Step 2: Use URLs in Scan Job

1. Copy extracted URLs from logs
2. Go to **New Scan**
3. Paste URLs (one per line)
4. Start scan to extract emails

## Important Notes

### Legal Compliance

⚠️ **Warning**: Automated Google searches may violate Google's Terms of Service

- Use reasonable delays between searches
- Limit number of queries per session
- Don't perform excessive automated searches
- Only extract publicly available URLs
- Respect robots.txt and website policies

### Rate Limiting

- **Default Delay**: 5-10 seconds between queries
- **Recommended**: Start with 5-10 queries max
- **Avoid**: Running hundreds of queries in short time

### Best Practices

1. **Start Small**: Test with 2-3 queries first
2. **Use Specific Terms**: More specific = better results
3. **Combine with Manual**: Use for initial discovery, then manual review
4. **Monitor Logs**: Check `logs/app.log` for extraction status
5. **Respect Limits**: Don't abuse the feature

## Troubleshooting

### Issue: "ChromeDriver not found"
**Solution**: The system auto-downloads ChromeDriver. Ensure Chrome is installed.

### Issue: "No URLs extracted"
**Solution**: 
- Check if Google is accessible
- Try different search queries
- Increase number of results
- Check logs for errors

### Issue: "Bot detection / CAPTCHA"
**Solution**:
- Undetected mode should bypass this
- If it persists, reduce query frequency
- Try running in non-headless mode
- Clear browser cache

### Issue: "Rate limited by Google"
**Solution**:
- Increase delays between searches
- Reduce number of queries
- Wait before trying again
- Use different search terms

## Configuration

### Environment Variables

```env
# In .env file
SELENIUM_HEADLESS=True          # Run in headless mode
SELENIUM_TIMEOUT=30             # Page load timeout
SCRAPER_MIN_DELAY=1.0          # Min delay between requests
SCRAPER_MAX_DELAY=3.0          # Max delay between requests
```

### Customize Delays

Edit `scraper/google_search.py`:

```python
# Line ~95: Delay between searches
delay = random.uniform(5, 10)  # Change to (10, 20) for more delay
```

## API Usage

### Programmatic Access

```python
from scraper.google_search import GoogleSearchExtractor

# Initialize
with GoogleSearchExtractor(headless=True) as extractor:
    # Single query
    urls = extractor.search_google('"HVAC" "New York"', num_results=20)
    print(f"Found {len(urls)} URLs")
    
    # Multiple queries
    queries = [
        '"construction" "California"',
        '"plumbing" "Texas"'
    ]
    all_urls = extractor.search_multiple_queries(queries, num_results=10)
    print(f"Total: {len(all_urls)} unique URLs")
```

## Examples

### Example 1: Find Construction Companies

```
"construction companies" "New York" contact
"general contractor" "New York" email
"building contractor" "New York" "contact us"
```

### Example 2: Find HVAC Services

```
"HVAC services" "California" email
"air conditioning" "California" contact
"heating repair" "California" "info@"
```

### Example 3: Find Specific Email Patterns

```
"info@*.com" "plumber" "Texas"
"contact@*.com" "electrician" "Florida"
"sales@*.com" "carpenter" "Ohio"
```

## Performance

- **Speed**: ~10-15 URLs per minute (with delays)
- **Accuracy**: Depends on search query quality
- **Unique URLs**: Automatic deduplication
- **Success Rate**: ~80-90% (depends on Google availability)

## Future Enhancements

- [ ] Save extracted URLs to database
- [ ] URL preview before scanning
- [ ] Export URLs to CSV
- [ ] Search history tracking
- [ ] Proxy support for IP rotation
- [ ] Custom delay configuration in UI

---

**Remember**: Use this feature responsibly and in compliance with all applicable laws and terms of service.
