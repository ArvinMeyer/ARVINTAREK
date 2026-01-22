"""
HTML parsing and link extraction
"""
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set
from utils.logger import get_logger

logger = get_logger(__name__)

class Parser:
    """HTML parser for extracting content and links"""
    
    def __init__(self, html: str, base_url: str):
        """
        Initialize parser
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
        """
        self.html = html
        self.base_url = base_url
        self.soup = BeautifulSoup(html, 'lxml')
    
    def get_text(self) -> str:
        """
        Get all text content from page
        
        Returns:
            Extracted text
        """
        try:
            # Remove script and style elements
            for script in self.soup(['script', 'style', 'noscript']):
                script.decompose()
            
            # Get text
            text = self.soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def get_links(self, same_domain_only: bool = True) -> Set[str]:
        """
        Extract all links from page
        
        Args:
            same_domain_only: Only return links from same domain
        
        Returns:
            Set of absolute URLs
        """
        links = set()
        base_domain = urlparse(self.base_url).netloc
        
        try:
            for anchor in self.soup.find_all('a', href=True):
                href = anchor['href']
                
                # Convert to absolute URL
                absolute_url = urljoin(self.base_url, href)
                
                # Parse URL
                parsed = urlparse(absolute_url)
                
                # Skip non-http(s) links
                if parsed.scheme not in ['http', 'https']:
                    continue
                
                # Filter by domain if requested
                if same_domain_only and parsed.netloc != base_domain:
                    continue
                
                # Remove fragment
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    clean_url += f"?{parsed.query}"
                
                links.add(clean_url)
            
            logger.debug(f"Extracted {len(links)} links from {self.base_url}")
            return links
            
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return set()
    
    def get_contact_links(self) -> Set[str]:
        """
        Extract contact/about page links
        
        Returns:
            Set of contact-related URLs
        """
        contact_keywords = [
            'contact', 'about', 'team', 'staff', 'directory',
            'people', 'employees', 'leadership', 'management'
        ]
        
        contact_links = set()
        
        try:
            for anchor in self.soup.find_all('a', href=True):
                href = anchor['href'].lower()
                text = anchor.get_text().lower()
                
                # Check if link or text contains contact keywords
                if any(keyword in href or keyword in text for keyword in contact_keywords):
                    absolute_url = urljoin(self.base_url, anchor['href'])
                    contact_links.add(absolute_url)
            
            logger.debug(f"Found {len(contact_links)} contact-related links")
            return contact_links
            
        except Exception as e:
            logger.error(f"Error extracting contact links: {e}")
            return set()
    
    def get_meta_emails(self) -> Set[str]:
        """
        Extract emails from meta tags and structured data
        
        Returns:
            Set of email addresses
        """
        emails = set()
        
        try:
            # Check meta tags
            for meta in self.soup.find_all('meta'):
                content = meta.get('content', '')
                if '@' in content and '.' in content:
                    # Simple check for email-like content
                    from utils.helpers import extract_emails_from_text
                    emails.update(extract_emails_from_text(content))
            
            # Check mailto links
            for anchor in self.soup.find_all('a', href=True):
                href = anchor['href']
                if href.startswith('mailto:'):
                    email = href.replace('mailto:', '').split('?')[0]
                    from utils.helpers import normalize_email
                    emails.add(normalize_email(email))
            
            logger.debug(f"Extracted {len(emails)} emails from meta/mailto")
            return emails
            
        except Exception as e:
            logger.error(f"Error extracting meta emails: {e}")
            return set()
    
    def has_pagination(self) -> bool:
        """
        Check if page has pagination
        
        Returns:
            True if pagination detected
        """
        pagination_indicators = [
            'pagination', 'pager', 'page-numbers', 'next-page',
            'prev-page', 'page-nav'
        ]
        
        try:
            # Check for common pagination classes/IDs
            for indicator in pagination_indicators:
                if self.soup.find(class_=indicator) or self.soup.find(id=indicator):
                    return True
            
            # Check for "next" links
            for anchor in self.soup.find_all('a'):
                text = anchor.get_text().lower()
                if 'next' in text or '»' in text or '›' in text:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking pagination: {e}")
            return False
