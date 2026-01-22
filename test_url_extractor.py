"""
Simple Test URL Extractor
Tests URL and email extraction
"""
import sys
sys.path.insert(0, 'c:/tarekscrab')

from scraper.extractor import EmailExtractor
from scraper.parser import Parser
from utils.logger import get_logger
import requests

logger = get_logger(__name__)

def test_email_extraction():
    """Test email extraction from sample HTML"""
    print("=" * 60)
    print("Testing Email Extractor")
    print("=" * 60)
    
    # Sample HTML content with emails
    sample_html = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Contact Information</h1>
        <p>Contact us at info@example.com</p>
        <p>Sales: sales@example.com</p>
        <p>Support: support@example.com</p>
        <a href="mailto:contact@example.com">Email us</a>
    </body>
    </html>
    """
    
    print("\nExtracting emails from sample HTML...")
    
    try:
        extractor = EmailExtractor()
        result = extractor.extract_from_html(sample_html, "https://example.com")
        
        all_emails = result.get('all_emails', set())
        
        print(f"\n✓ Extraction completed!")
        print(f"✓ Found {len(all_emails)} unique emails:")
        print("-" * 60)
        
        for i, email in enumerate(sorted(all_emails), 1):
            print(f"{i}. {email}")
        
        print("-" * 60)
        print(f"\n✅ Test PASSED - Found {len(all_emails)} emails")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_url_extraction():
    """Test URL extraction from a real webpage"""
    print("\n" + "=" * 60)
    print("Testing URL Extractor")
    print("=" * 60)
    
    test_url = "https://example.com"
    
    print(f"\nTest URL: {test_url}")
    print("Fetching page...")
    
    try:
        # Fetch the page
        response = requests.get(test_url, timeout=10)
        html = response.text
        
        print("✓ Page fetched successfully")
        print("\nExtracting URLs from page...")
        
        # Parse HTML and extract links
        parser = Parser(html, test_url)
        urls = parser.get_links()
        
        print(f"\n✓ Extraction completed!")
        print(f"✓ Found {len(urls)} URLs:")
        print("-" * 60)
        
        for i, url in enumerate(sorted(urls)[:10], 1):  # Show first 10
            print(f"{i}. {url}")
        
        if len(urls) > 10:
            print(f"... and {len(urls) - 10} more")
        
        print("-" * 60)
        print(f"\n✅ Test PASSED - Extracted {len(urls)} URLs")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_email_with_context():
    """Test email extraction with context"""
    print("\n" + "=" * 60)
    print("Testing Email Extraction with Context")
    print("=" * 60)
    
    sample_html = """
    <html>
    <body>
        <div class="contact">
            <h2>Sales Department</h2>
            <p>For sales inquiries, please contact our sales team at sales@company.com</p>
        </div>
        <div class="support">
            <h2>Customer Support</h2>
            <p>Need help? Reach out to support@company.com for assistance</p>
        </div>
    </body>
    </html>
    """
    
    print("\nExtracting emails with context...")
    
    try:
        extractor = EmailExtractor()
        results = extractor.extract_with_context(sample_html, "https://company.com", context_chars=30)
        
        print(f"\n✓ Extraction completed!")
        print(f"✓ Found {len(results)} emails with context:")
        print("-" * 60)
        
        for i, item in enumerate(results, 1):
            print(f"\n{i}. Email: {item['email']}")
            print(f"   Context: ...{item['context']}...")
        
        print("-" * 60)
        print(f"\n✅ Test PASSED - Found {len(results)} emails with context")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n🔍 URL & Email Extractor Test Suite\n")
    
    # Run all tests
    test1 = test_email_extraction()
    test2 = test_url_extraction()
    test3 = test_email_with_context()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Email Extraction: {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"URL Extraction: {'✅ PASSED' if test2 else '❌ FAILED'}")
    print(f"Email with Context: {'✅ PASSED' if test3 else '❌ FAILED'}")
    print("=" * 60)
    
    if test1 and test2 and test3:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
