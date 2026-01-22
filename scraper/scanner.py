"""
Multi-threaded scanning orchestrator
"""
import threading
import queue
from typing import List, Set
from datetime import datetime
from scraper.browser import Browser
from scraper.extractor import EmailExtractor
from scraper.parser import Parser
from utils.db import get_db_session, ScanJob, ScanResult, EmailRaw
from utils.logger import get_logger
from utils.helpers import is_valid_url
import config

logger = get_logger(__name__)

class Scanner:
    """Multi-threaded web scanner"""
    
    def __init__(self, scan_job_id: int):
        """
        Initialize scanner
        
        Args:
            scan_job_id: Database ID of scan job
        """
        self.scan_job_id = scan_job_id
        self.url_queue = queue.Queue()
        self.visited_urls = set()
        self.lock = threading.Lock()
        self.running = False
        self.threads = []
        self.extractor = EmailExtractor()
    
    def add_urls(self, urls: List[str]):
        """
        Add URLs to scan queue
        
        Args:
            urls: List of URLs to scan
        """
        added_count = 0
        for url in urls:
            # Clean URL (strip whitespace)
            url = url.strip() if url else ""
            if not url:
                continue
                
            if is_valid_url(url) and url not in self.visited_urls:
                self.url_queue.put(url)
                added_count += 1
                logger.info(f"Added URL to queue: {url}")
            else:
                logger.debug(f"Skipped URL (invalid or already visited): {url}")
        
        logger.info(f"Added {added_count} URLs to scan queue (total: {len(urls)} provided)")
    
    def worker(self, thread_id: int):
        """
        Worker thread for scanning URLs
        
        Args:
            thread_id: Thread identifier
        """
        logger.info(f"Worker {thread_id} started")
        
        browser = None
        try:
            logger.info(f"Worker {thread_id}: Initializing browser...")
            browser = Browser()
            browser.start()
            # Give browser a moment to fully initialize
            import time
            time.sleep(1)
            logger.info(f"Worker {thread_id}: Browser started successfully, driver valid: {browser.is_valid()}")
            
            while self.running:
                try:
                    # Get URL from queue (with timeout to allow checking running flag)
                    try:
                        url = self.url_queue.get(timeout=1)
                        logger.info(f"Worker {thread_id}: Got URL from queue: {url}")
                    except queue.Empty:
                        continue
                    
                    # Check if already visited
                    with self.lock:
                        if url in self.visited_urls:
                            logger.debug(f"Worker {thread_id}: URL already visited: {url}")
                            self.url_queue.task_done()
                            continue
                        self.visited_urls.add(url)
                    
                    # Check if browser is still valid, recreate if needed
                    if not browser or not browser.is_valid():
                        logger.warning(f"Worker {thread_id}: Browser session invalid, recreating...")
                        try:
                            if browser:
                                browser.close()
                        except:
                            pass
                        browser = Browser()
                        browser.start()
                        logger.info(f"Worker {thread_id}: Browser recreated successfully")
                    
                    # Scan the URL
                    logger.info(f"Worker {thread_id}: About to scan URL: {url}")
                    self._scan_url(browser, url, thread_id)
                    
                    self.url_queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Worker {thread_id} error: {e}")
                    # If browser error, try to recreate
                    if browser and not browser.is_valid():
                        try:
                            browser.close()
                        except:
                            pass
                        try:
                            browser = Browser()
                            browser.start()
                            logger.info(f"Worker {thread_id}: Browser recreated after error")
                        except Exception as browser_error:
                            logger.error(f"Worker {thread_id}: Failed to recreate browser: {browser_error}")
                            break  # Exit worker if can't recreate browser
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass
        
        logger.info(f"Worker {thread_id} stopped")
    
    def _scan_url(self, browser: Browser, url: str, thread_id: int):
        """
        Scan a single URL
        
        Args:
            browser: Browser instance
            url: URL to scan
            thread_id: Thread identifier
        """
        db = get_db_session()
        scan_result = ScanResult(
            scan_job_id=self.scan_job_id,
            url=url,
            status='processing'
        )
        
        try:
            logger.info(f"[Thread {thread_id}] Starting to scan: {url}")
            
            # Ensure browser is valid before navigating
            if not browser or not browser.is_valid():
                logger.error(f"[Thread {thread_id}] Browser is invalid, cannot scan {url}")
                scan_result.status = 'failed'
                scan_result.error_message = 'Browser session invalid'
                db.add(scan_result)
                db.commit()
                return
            
            logger.info(f"[Thread {thread_id}] Browser is valid, navigating to: {url}")
            
            # Navigate to URL
            navigate_success = browser.navigate(url)
            logger.info(f"[Thread {thread_id}] Navigate result for {url}: {navigate_success}")
            
            if not navigate_success:
                logger.warning(f"[Thread {thread_id}] Failed to navigate to {url}")
                scan_result.status = 'failed'
                scan_result.error_message = 'Failed to load page'
                db.add(scan_result)
                db.commit()
                return
            
            # Scroll to load dynamic content (including footer)
            browser.scroll_page()
            
            # Get page source
            html = browser.get_page_source()
            
            if not html:
                scan_result.status = 'failed'
                scan_result.error_message = 'Empty page source'
                db.add(scan_result)
                db.commit()
                return
            
            # Extract emails from main page with context
            email_data = self.extractor.extract_with_context(html, url)
            
            # Also extract footer-specific content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # Look for footer content
            footer_text = ""
            footer_elements = soup.find_all(['footer', 'div'], class_=lambda x: x and ('footer' in x.lower() if isinstance(x, str) else False))
            if not footer_elements:
                footer_elements = soup.find_all(['footer'])
            
            for footer in footer_elements:
                footer_text += footer.get_text(separator=' ', strip=True) + " "
            
            # Extract emails from footer
            if footer_text:
                from utils.helpers import extract_emails_from_text
                footer_emails = extract_emails_from_text(footer_text)
                logger.info(f"[Thread {thread_id}] Found {len(footer_emails)} emails in footer")
                
                # Add footer emails to results
                for email in footer_emails:
                    # Check if not already in email_data
                    if not any(item['email'] == email for item in email_data):
                        email_data.append({
                            'email': email,
                            'context': footer_text[:100],  # First 100 chars of footer
                            'url': url
                        })
            
            # Find and visit Contact/About pages
            parser = Parser(html, url)
            contact_links = parser.get_contact_links()
            
            if contact_links:
                logger.info(f"[Thread {thread_id}] Found {len(contact_links)} contact-related links")
                
                # Visit the first contact link (to avoid too many requests)
                for contact_url in list(contact_links)[:1]:  # Only visit first contact page
                    try:
                        logger.info(f"[Thread {thread_id}] Visiting contact page: {contact_url}")
                        
                        if browser.navigate(contact_url):
                            browser.scroll_page()
                            contact_html = browser.get_page_source()
                            
                            if contact_html:
                                # Extract emails from contact page
                                contact_emails = self.extractor.extract_with_context(contact_html, contact_url)
                                logger.info(f"[Thread {thread_id}] Found {len(contact_emails)} emails on contact page")
                                
                                # Add contact page emails
                                email_data.extend(contact_emails)
                    except Exception as e:
                        logger.warning(f"[Thread {thread_id}] Error visiting contact page {contact_url}: {e}")
            
            # Save emails to database
            for item in email_data:
                email_raw = EmailRaw(
                    scan_job_id=self.scan_job_id,
                    email=item['email'],
                    source_url=url,
                    context=item['context']
                )
                db.add(email_raw)
            
            # Update scan result
            scan_result.status = 'success'
            scan_result.emails_found = len(email_data)
            db.add(scan_result)
            
            # Update scan job totals
            scan_job = db.query(ScanJob).filter_by(id=self.scan_job_id).first()
            if scan_job:
                scan_job.total_pages += 1
                scan_job.total_emails += len(email_data)
            
            db.commit()
            
            logger.info(f"[Thread {thread_id}] Found {len(email_data)} total emails on {url}")
            
        except Exception as e:
            logger.error(f"Error scanning {url}: {e}")
            scan_result.status = 'failed'
            scan_result.error_message = str(e)
            db.add(scan_result)
            db.commit()
        
        finally:
            db.close()
    
    def start(self, urls: List[str], num_threads: int = None):
        """
        Start scanning
        
        Args:
            urls: Initial URLs to scan
            num_threads: Number of worker threads (default from config)
        """
        if self.running:
            logger.warning("Scanner already running")
            return
        
        num_threads = num_threads or config.SCRAPER_THREADS
        
        # Update scan job status
        db = get_db_session()
        scan_job = db.query(ScanJob).filter_by(id=self.scan_job_id).first()
        if scan_job:
            scan_job.status = 'running'
            scan_job.started_at = datetime.utcnow()
            db.commit()
        db.close()
        
        # Add initial URLs
        self.add_urls(urls)
        
        # Start worker threads
        self.running = True
        for i in range(num_threads):
            thread = threading.Thread(target=self.worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        logger.info(f"Scanner started with {num_threads} threads")
    
    def stop(self):
        """Stop scanning"""
        if not self.running:
            return
        
        logger.info("Stopping scanner...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=5)
        
        # Update scan job status
        db = get_db_session()
        scan_job = db.query(ScanJob).filter_by(id=self.scan_job_id).first()
        if scan_job:
            scan_job.status = 'completed'
            scan_job.completed_at = datetime.utcnow()
            db.commit()
        db.close()
        
        logger.info("Scanner stopped")
    
    def wait(self):
        """Wait for all URLs to be processed"""
        self.url_queue.join()
        self.stop()
