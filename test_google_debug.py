"""
Debug script to test Google search and save HTML for inspection
"""
import time
import random
from scraper.google_search import GoogleSearchExtractor
from utils.logger import get_logger

logger = get_logger(__name__)

def test_google_search():
    """Test Google search and save HTML"""
    query = "HVAC companies New York"
    
    print(f"Testing Google search for: {query}")
    print("=" * 60)
    
    try:
        extractor = GoogleSearchExtractor(headless=False)  # Run with visible browser
        extractor.start()
        
        # Navigate to Google
        search_url = f"https://www.google.com/search?q={query}&num=10"
        print(f"Navigating to: {search_url}")
        extractor.driver.get(search_url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Save screenshot
        screenshot_path = "google_search_debug.png"
        extractor.driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")
        
        # Save HTML
        html = extractor.driver.page_source
        html_path = "google_search_debug.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML saved to: {html_path}")
        
        # Try to extract URLs
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        # Count all links
        all_links = soup.find_all('a', href=True)
        print(f"\nTotal links found: {len(all_links)}")
        
        # Show first 10 links
        print("\nFirst 10 links:")
        for i, link in enumerate(all_links[:10]):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            print(f"{i+1}. {href[:80]} | Text: {text}")
        
        # Try extraction methods
        print("\n" + "=" * 60)
        print("Testing extraction methods:")
        print("=" * 60)
        
        # Method 1: Direct HTTP links
        method1_urls = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and 'google.com' not in href:
                method1_urls.append(href)
        print(f"\nMethod 1 (Direct HTTP): {len(method1_urls)} URLs")
        for url in method1_urls[:5]:
            print(f"  - {url}")
        
        # Method 2: Selenium direct
        method2_urls = []
        link_elements = extractor.driver.find_elements('tag name', 'a')
        for elem in link_elements:
            try:
                href = elem.get_attribute('href')
                if href and href.startswith('http') and 'google.com' not in href:
                    method2_urls.append(href)
            except:
                continue
        print(f"\nMethod 2 (Selenium): {len(method2_urls)} URLs")
        for url in method2_urls[:5]:
            print(f"  - {url}")
        
        # Keep browser open for manual inspection
        print("\n" + "=" * 60)
        print("Browser will stay open for 30 seconds for manual inspection...")
        print("=" * 60)
        time.sleep(30)
        
        extractor.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_google_search()
