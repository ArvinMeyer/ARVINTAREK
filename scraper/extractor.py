"""
Email extraction from web pages
"""
from typing import Set, Dict
from utils.helpers import extract_emails_from_text, normalize_email
from utils.logger import get_logger
from scraper.parser import Parser

logger = get_logger(__name__)

class EmailExtractor:
    """Extract and process emails from web pages"""
    
    def __init__(self):
        """Initialize email extractor"""
        self.extracted_emails = set()
    
    def extract_from_html(self, html: str, url: str) -> Dict[str, Set[str]]:
        """
        Extract emails from HTML content
        
        Args:
            html: HTML content
            url: Source URL
        
        Returns:
            Dictionary with 'text_emails' and 'meta_emails' sets
        """
        result = {
            'text_emails': set(),
            'meta_emails': set(),
            'all_emails': set()
        }
        
        try:
            # Parse HTML
            parser = Parser(html, url)
            
            # Extract from text content
            text = parser.get_text()
            text_emails = extract_emails_from_text(text)
            result['text_emails'] = text_emails
            
            # Extract from meta tags and mailto links
            meta_emails = parser.get_meta_emails()
            result['meta_emails'] = meta_emails
            
            # Combine all
            all_emails = text_emails | meta_emails
            result['all_emails'] = all_emails
            
            # Add to global set
            self.extracted_emails.update(all_emails)
            
            logger.info(f"Extracted {len(all_emails)} emails from {url}")
            
        except Exception as e:
            logger.error(f"Error extracting emails from {url}: {e}")
        
        return result
    
    def extract_with_context(self, html: str, url: str, context_chars: int = 50) -> list:
        """
        Extract emails with surrounding context
        
        Args:
            html: HTML content
            url: Source URL
            context_chars: Number of characters to capture before/after email
        
        Returns:
            List of dicts with 'email' and 'context'
        """
        results = []
        
        try:
            parser = Parser(html, url)
            text = parser.get_text()
            
            # Find emails with context
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            
            for match in re.finditer(email_pattern, text):
                email = normalize_email(match.group())
                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                context = text[start:end].strip()
                
                results.append({
                    'email': email,
                    'context': context,
                    'url': url
                })
            
            logger.debug(f"Extracted {len(results)} emails with context from {url}")
            
        except Exception as e:
            logger.error(f"Error extracting emails with context: {e}")
        
        return results
    
    def filter_duplicates(self, emails: Set[str]) -> Set[str]:
        """
        Filter out already extracted emails
        
        Args:
            emails: Set of emails to filter
        
        Returns:
            Set of new (not previously extracted) emails
        """
        new_emails = emails - self.extracted_emails
        logger.debug(f"Filtered {len(emails) - len(new_emails)} duplicate emails")
        return new_emails
    
    def get_all_extracted(self) -> Set[str]:
        """
        Get all extracted emails
        
        Returns:
            Set of all extracted emails
        """
        return self.extracted_emails.copy()
    
    def clear(self):
        """Clear all extracted emails"""
        self.extracted_emails.clear()
        logger.info("Cleared all extracted emails")
