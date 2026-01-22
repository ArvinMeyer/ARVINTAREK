"""
Google Search URL Extractor using Undetected ChromeDriver
"""
import os
import time
import random
from typing import List, Set
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, WebDriverException
from utils.logger import get_logger
import config

logger = get_logger(__name__)

class GoogleSearchExtractor:
    """Extract URLs from Google search results using Undetected ChromeDriver"""
    
    def __init__(self, headless: bool = False, max_retries: int = 3):
        """
        Initialize Google search extractor
        
        Args:
            headless: Run in headless mode
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.headless = headless
        self.driver = None
        self.extracted_urls = set()
        self.max_retries = max_retries
    
    def start(self):
        """Start ChromeDriver with anti-detection measures and fallback strategies"""
        last_error = None
        
        # Configure undetected-chromedriver options
        options = uc.ChromeOptions()
        
        # Anti-detection settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        
        # Additional stability options
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Random user agent
        user_agent = random.choice(config.USER_AGENTS)
        options.add_argument(f'user-agent={user_agent}')
        
        # Strategy 1: Try with explicit driver path (if chromedriver.exe exists locally)
        chromedriver_path = None
        if os.path.exists("chromedriver.exe"):
            chromedriver_path = os.path.abspath("chromedriver.exe")
            logger.info(f"Found local chromedriver.exe: {chromedriver_path}")
        
        if chromedriver_path:
            try:
                logger.info("Attempting to initialize ChromeDriver with explicit path...")
                self.driver = uc.Chrome(
                    options=options,
                    driver_executable_path=chromedriver_path,
                    use_subprocess=False
                )
                
                # Set timeouts with more conservative values
                self.driver.set_page_load_timeout(config.SELENIUM_PAGE_LOAD_TIMEOUT)
                self.driver.implicitly_wait(config.SELENIUM_IMPLICIT_WAIT)
                
                logger.info("✓ ChromeDriver started successfully (explicit path)")
                return
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(f"Explicit path initialization failed: {error_msg}")
                logger.info("Trying fallback strategy...")
        
        # Strategy 2: Try auto-download (default behavior)
        try:
            logger.info("Attempting to initialize ChromeDriver (auto-download)...")
            self.driver = uc.Chrome(options=options, version_main=None)
            
            # Set timeouts with more conservative values
            self.driver.set_page_load_timeout(config.SELENIUM_PAGE_LOAD_TIMEOUT)
            self.driver.implicitly_wait(config.SELENIUM_IMPLICIT_WAIT)
            
            logger.info("✓ ChromeDriver started successfully (auto-download)")
            return
            
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            if '10054' in error_msg or 'forcibly closed' in error_msg.lower():
                logger.warning("ChromeDriver auto-download failed (connection blocked)")
                logger.info("Trying fallback strategy: use system ChromeDriver...")
            elif 'SSL' in error_msg or 'UNEXPECTED_EOF' in error_msg:
                logger.warning("ChromeDriver auto-download failed (SSL error)")
                logger.info("Trying fallback strategy: use system ChromeDriver...")
            else:
                logger.warning(f"ChromeDriver initialization failed: {error_msg}")
                logger.info("Trying fallback strategy...")
        
        
        # All strategies failed - provide helpful error message
        logger.error("=" * 70)
        logger.error("CHROMEDRIVER INITIALIZATION FAILED")
        logger.error("=" * 70)
        logger.error("")
        logger.error("ChromeDriver could not be initialized.")
        logger.error("")
        if not chromedriver_path:
            logger.error("ISSUE: chromedriver.exe not found in project folder")
            logger.error("")
            logger.error("SOLUTION: Place chromedriver.exe in the project folder")
            logger.error("")
            logger.error("Step 1: Make sure you downloaded ChromeDriver")
            logger.error("  → Visit: https://googlechromelabs.github.io/chrome-for-testing/")
            logger.error("  → Download: chromedriver-win64.zip")
            logger.error("")
            logger.error("Step 2: Extract and place in project folder")
            logger.error("  → Extract chromedriver.exe from the ZIP")
            logger.error(f"  → Copy to: {os.path.abspath('.')}")
            logger.error("  → The file should be: chromedriver.exe (not in a subfolder)")
            logger.error("")
        else:
            logger.error("ISSUE: ChromeDriver found but failed to initialize")
            logger.error(f"  Path: {chromedriver_path}")
            logger.error("")
            logger.error("POSSIBLE CAUSES:")
            logger.error("  1. ChromeDriver version doesn't match your Chrome browser")
            logger.error("  2. ChromeDriver file is corrupted")
            logger.error("  3. Antivirus blocking execution")
            logger.error("")
            logger.error("SOLUTION: Re-download ChromeDriver")
            logger.error("  → Delete current chromedriver.exe")
            logger.error("  → Download fresh copy from:")
            logger.error("    https://googlechromelabs.github.io/chrome-for-testing/")
            logger.error("")
        
        logger.error("Step 3: Restart the application")
        logger.error("  → Press Ctrl+C to stop")
        logger.error("  → Run: python main.py")
        logger.error("")
        logger.error("ALTERNATIVE: Use manual URL entry instead")
        logger.error("  → Dashboard → New Scan → Paste URLs directly")
        logger.error("  → This bypasses Google search entirely")
        logger.error("")
        logger.error("=" * 70)
        logger.error(f"Last error: {last_error}")
        logger.error("=" * 70)
        
        raise Exception(
            "ChromeDriver initialization failed. "
            "Please check error messages above for instructions."
        )
    
    def search_google(self, query: str, num_pages: int = 1) -> List[str]:
        """
        Search Google and extract result URLs from multiple pages
        
        Args:
            query: Search query
            num_pages: Number of Google result pages to fetch (each page has ~10 results)
        
        Returns:
            List of URLs from search results
        """
        all_urls = []
        last_error = None
        
        # Fetch multiple pages
        for page_num in range(num_pages):
            start_index = page_num * 10  # Google uses start parameter for pagination
            page_urls = []
            
            for attempt in range(self.max_retries):
                try:
                    # Build Google search URL with pagination
                    if page_num == 0:
                        search_url = f"https://www.google.com/search?q={query}&num=10"
                    else:
                        search_url = f"https://www.google.com/search?q={query}&num=10&start={start_index}"
                    
                    logger.info(f"Searching Google for: {query} (Page {page_num + 1}/{num_pages}, Attempt {attempt + 1}/{self.max_retries})")
                    
                    # Navigate to Google with timeout handling
                    try:
                        self.driver.get(search_url)
                    except TimeoutException:
                        logger.warning(f"Page load timeout on attempt {attempt + 1}, continuing anyway...")
                    except WebDriverException as e:
                        if "ERR_CONNECTION_CLOSED" in str(e) or "10054" in str(e):
                            logger.warning(f"Connection closed by remote host on attempt {attempt + 1}")
                            raise  # Re-raise to trigger retry
                        else:
                            logger.error(f"WebDriver error: {e}")
                            raise
                    
                    # Random delay to mimic human behavior (longer delays)
                    delay = random.uniform(3, 6)
                    logger.debug(f"Waiting {delay:.1f}s to mimic human behavior...")
                    time.sleep(delay)
                    
                    # Scroll page
                    self._scroll_page()
                    
                    # Additional delay after scrolling
                    time.sleep(random.uniform(1, 2))
                    
                    # Get page source
                    html = self.driver.page_source
                    
                    # Check if we got blocked
                    if "unusual traffic" in html.lower() or "captcha" in html.lower():
                        logger.warning("Google detected unusual traffic. You may need to:")
                        logger.warning("1. Increase delays between searches")
                        logger.warning("2. Use a VPN or different IP address")
                        logger.warning("3. Run in non-headless mode and solve CAPTCHA manually")
                        if attempt < self.max_retries - 1:
                            wait_time = (attempt + 1) * 10  # Exponential backoff
                            logger.info(f"Waiting {wait_time}s before retry...")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error("Max retries reached. Google is blocking requests.")
                            break  # Break from retry loop, move to next page
                    
                    # Parse HTML
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Extract search result links using multiple methods
                    # Google's HTML structure changes frequently, so we try multiple approaches
                    
                    # Method 1: Look for links with specific data attributes (modern Google)
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        # Skip internal Google links
                        if href.startswith('/search') or href.startswith('#') or 'google.com' in href:
                            continue
                        # Direct HTTP/HTTPS links
                        if href.startswith('http'):
                            page_urls.append(href)
                    
                    # Method 2: Extract from /url?q= redirects (classic Google)
                    if len(page_urls) < 3:  # If we didn't get many results, try this method too
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if '/url?q=' in href or '/url?url=' in href:
                                try:
                                    parsed = parse_qs(urlparse(href).query)
                                    if 'q' in parsed:
                                        actual_url = parsed['q'][0]
                                        if actual_url.startswith('http') and 'google.com' not in actual_url:
                                            page_urls.append(actual_url)
                                    elif 'url' in parsed:
                                        actual_url = parsed['url'][0]
                                        if actual_url.startswith('http') and 'google.com' not in actual_url:
                                            page_urls.append(actual_url)
                                except Exception as e:
                                    logger.debug(f"Error parsing redirect URL: {e}")
                                    continue
                    
                    # Method 3: Use Selenium to get links directly from the page
                    if len(page_urls) < 3:
                        try:
                            # Find all links using Selenium
                            link_elements = self.driver.find_elements('tag name', 'a')
                            for elem in link_elements:
                                try:
                                    href = elem.get_attribute('href')
                                    if href and href.startswith('http') and 'google.com' not in href:
                                        # Skip common non-result links
                                        if any(skip in href for skip in ['youtube.com/results', 'maps.google', 'accounts.google']):
                                            continue
                                        page_urls.append(href)
                                except:
                                    continue
                        except Exception as e:
                            logger.debug(f"Error using Selenium to extract links: {e}")
                    
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_urls = []
                    for url in page_urls:
                        if url not in seen:
                            seen.add(url)
                            unique_urls.append(url)
                    page_urls = unique_urls
                    
                    logger.info(f"Extracted {len(page_urls)} URLs from Google search page {page_num + 1}")
                    if len(page_urls) == 0:
                        logger.warning(f"No URLs extracted from page {page_num + 1}. Google may have blocked the request or HTML structure changed.")
                        if attempt < self.max_retries - 1:
                            wait_time = (attempt + 1) * 5
                            logger.info(f"Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                    
                    # Add to global set
                    self.extracted_urls.update(page_urls)
                    
                    # Add page URLs to all URLs
                    all_urls.extend(page_urls)
                    
                    # Success - break out of retry loop for this page
                    break
            
                except (TimeoutException, WebDriverException) as e:
                    last_error = e
                    error_msg = str(e)
                    
                    if "10054" in error_msg or "forcibly closed" in error_msg.lower():
                        logger.warning(f"Connection forcibly closed by remote host (Page {page_num + 1}, Attempt {attempt + 1}/{self.max_retries})")
                    elif "timeout" in error_msg.lower():
                        logger.warning(f"Request timeout (Page {page_num + 1}, Attempt {attempt + 1}/{self.max_retries})")
                    else:
                        logger.warning(f"WebDriver error: {error_msg} (Page {page_num + 1}, Attempt {attempt + 1}/{self.max_retries})")
                    
                    if attempt < self.max_retries - 1:
                        # Exponential backoff
                        wait_time = (2 ** attempt) * 3  # 3s, 6s, 12s
                        logger.info(f"Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Max retries reached for page {page_num + 1}. Last error: {error_msg}")
                        
                except Exception as e:
                    last_error = e
                    logger.error(f"Unexpected error searching Google page {page_num + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        logger.info(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Max retries reached for page {page_num + 1} after unexpected error")
            
            # Delay between pages to avoid rate limiting
            if page_num < num_pages - 1 and len(page_urls) > 0:
                delay = random.uniform(5, 10)
                logger.info(f"Waiting {delay:.1f}s before fetching next page...")
                time.sleep(delay)
        
        # Remove duplicates from all pages
        seen = set()
        unique_all_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_all_urls.append(url)
        
        logger.info(f"Extracted total of {len(unique_all_urls)} unique URLs from {num_pages} page(s)")
        return unique_all_urls
    
    def search_multiple_queries(self, queries: List[str], num_pages: int = 1) -> Set[str]:
        """
        Search multiple queries and combine results
        
        Args:
            queries: List of search queries
            num_pages: Number of Google result pages to fetch per query
        
        Returns:
            Set of unique URLs
        """
        all_urls = set()
        
        for i, query in enumerate(queries):
            try:
                urls = self.search_google(query, num_pages)
                all_urls.update(urls)
                
                # Longer delay between searches to avoid rate limiting
                if i < len(queries) - 1:
                    delay = random.uniform(8, 15)  # Increased from 5-10
                    logger.info(f"Waiting {delay:.1f}s before next search...")
                    time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error searching query '{query}': {e}")
                continue
        
        logger.info(f"Total unique URLs extracted: {len(all_urls)}")
        return all_urls
    
    def _scroll_page(self):
        """Scroll page to load dynamic content"""
        try:
            # Scroll down slowly
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(random.uniform(0.3, 0.7))
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error during page scroll: {e}")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("ChromeDriver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def extract_urls_from_google(search_queries: List[str], num_pages: int = 1) -> List[str]:
    """
    Convenience function to extract URLs from Google search
    
    Args:
        search_queries: List of search queries
        num_pages: Number of Google result pages to fetch per query
    
    Returns:
        List of unique URLs
    
    Example:
        queries = [
            '"info@*.com" "HVAC Technician" "New York"',
            '"contact@*.com" "Electrician" "California"'
        ]
        urls = extract_urls_from_google(queries, num_pages=3)
    """
    with GoogleSearchExtractor(headless=config.SELENIUM_HEADLESS) as extractor:
        urls = extractor.search_multiple_queries(search_queries, num_pages)
        return list(urls)
