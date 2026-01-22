"""
Browser automation using Undetected ChromeDriver
"""
import os
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException, NoSuchWindowException
import config
from utils.logger import get_logger

logger = get_logger(__name__)

class Browser:
    """Undetected ChromeDriver automation wrapper"""
    
    def __init__(self, headless: bool = None, user_agent: str = None):
        """
        Initialize browser
        
        Args:
            headless: Run in headless mode (default from config)
            user_agent: Custom user agent (random from pool if None)
        """
        self.headless = headless if headless is not None else config.SELENIUM_HEADLESS
        self.user_agent = user_agent or random.choice(config.USER_AGENTS)
        self.driver = None
        
    def start(self):
        """Start the browser using undetected-chromedriver"""
        try:
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless=new')
            
            # Performance and security options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument(f'user-agent={self.user_agent}')
            
            # Strategy 1: Try with explicit driver path (if chromedriver.exe exists locally)
            chromedriver_path = None
            if os.path.exists("chromedriver.exe"):
                chromedriver_path = os.path.abspath("chromedriver.exe")
                logger.info(f"Found local chromedriver.exe: {chromedriver_path}")
            
            if chromedriver_path:
                try:
                    logger.info("Initializing ChromeDriver with explicit path...")
                    self.driver = uc.Chrome(
                        options=options,
                        driver_executable_path=chromedriver_path,
                        use_subprocess=False
                    )
                    logger.info("✓ ChromeDriver started successfully (explicit path)")
                except Exception as e:
                    logger.warning(f"Explicit path initialization failed: {e}")
                    logger.info("Trying fallback strategy...")
                    # Fallback to auto-download
                    self.driver = uc.Chrome(options=options, version_main=None)
                    logger.info("✓ ChromeDriver started successfully (auto-download)")
            else:
                # No local chromedriver.exe, try auto-download
                logger.info("Attempting ChromeDriver auto-download...")
                self.driver = uc.Chrome(options=options, version_main=None)
                logger.info("✓ ChromeDriver started successfully (auto-download)")
            
            # Set timeouts
            self.driver.set_page_load_timeout(config.SELENIUM_PAGE_LOAD_TIMEOUT)
            self.driver.implicitly_wait(config.SELENIUM_IMPLICIT_WAIT)
            
            # Verify browser is actually working
            try:
                _ = self.driver.window_handles
                logger.info(f"Browser started successfully (headless={self.headless})")
            except Exception as e:
                logger.error(f"Browser started but session invalid: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            self.driver = None
            raise
    
    def navigate(self, url: str) -> bool:
        """
        Navigate to URL
        
        Args:
            url: URL to navigate to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if browser session is still valid
            if not self.driver:
                logger.error("Browser driver is None, cannot navigate")
                return False
                
            if not self.is_valid():
                logger.warning("Browser session invalid, cannot navigate")
                return False
            
            logger.info(f"Navigating to: {url}")
            logger.info(f"Current browser window handles: {len(self.driver.window_handles)}")
            
            # Navigate to URL
            self.driver.get(url)
            
            # Verify we actually navigated
            current_url = self.driver.current_url
            logger.info(f"Successfully navigated. Current URL: {current_url}")
            
            # Random delay to mimic human behavior
            time.sleep(random.uniform(config.SCRAPER_MIN_DELAY, config.SCRAPER_MAX_DELAY))
            
            return True
            
        except (InvalidSessionIdException, NoSuchWindowException) as e:
            logger.error(f"Browser session invalid for {url}: {e}")
            self.driver = None  # Mark as invalid
            return False
        except TimeoutException as e:
            logger.warning(f"Timeout loading {url}: {e}")
            return False
        except WebDriverException as e:
            logger.error(f"WebDriver error navigating to {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error navigating to {url}: {e}", exc_info=True)
            return False
    
    def scroll_page(self, pause_time: float = None):
        """
        Scroll page to load dynamic content
        
        Args:
            pause_time: Pause between scrolls (default from config)
        """
        pause = pause_time or config.SCRAPER_SCROLL_PAUSE
        
        try:
            # Check if browser session is still valid
            if not self.driver or not self.is_valid():
                logger.warning("Browser session invalid, cannot scroll")
                return
            
            # Get initial scroll height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while True:
                # Scroll down to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for page to load
                time.sleep(pause)
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # Break if no more content
                if new_height == last_height:
                    break
                    
                last_height = new_height
            
            logger.debug("Page scrolling completed")
            
        except (InvalidSessionIdException, NoSuchWindowException) as e:
            logger.warning(f"Browser session invalid during scroll: {e}")
            self.driver = None  # Mark as invalid
        except Exception as e:
            logger.warning(f"Error during page scroll: {e}")
    
    def get_page_source(self) -> str:
        """
        Get current page HTML source
        
        Returns:
            Page HTML source
        """
        try:
            if not self.driver or not self.is_valid():
                logger.warning("Browser session invalid, cannot get page source")
                return ""
            return self.driver.page_source
        except (InvalidSessionIdException, NoSuchWindowException) as e:
            logger.error(f"Browser session invalid: {e}")
            self.driver = None  # Mark as invalid
            return ""
        except Exception as e:
            logger.error(f"Failed to get page source: {e}")
            return ""
    
    def is_valid(self) -> bool:
        """
        Check if browser session is still valid
        
        Returns:
            True if valid, False otherwise
        """
        if not self.driver:
            logger.debug("Browser driver is None")
            return False
        try:
            # Try to get window handles - this will fail if session is invalid
            _ = self.driver.window_handles
            return True
        except (InvalidSessionIdException, NoSuchWindowException, WebDriverException) as e:
            logger.debug(f"Browser session invalid check: {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error checking browser validity: {e}")
            return False
    
    def wait_for_element(self, by: By, value: str, timeout: int = None) -> bool:
        """
        Wait for element to be present
        
        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Wait timeout (default from config)
        
        Returns:
            True if element found, False otherwise
        """
        timeout = timeout or config.SELENIUM_TIMEOUT
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            logger.debug(f"Element not found: {by}={value}")
            return False
    
    def screenshot(self, filepath: str):
        """
        Take screenshot
        
        Args:
            filepath: Output file path
        """
        try:
            self.driver.save_screenshot(filepath)
            logger.info(f"Screenshot saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                # Check if session is still valid before trying to quit
                try:
                    self.driver.window_handles
                    self.driver.quit()
                except (InvalidSessionIdException, NoSuchWindowException, WebDriverException):
                    # Session already invalid, just mark as closed
                    pass
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
