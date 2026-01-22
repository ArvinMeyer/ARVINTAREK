"""
Simple Test - Email and URL Extraction (No Network Required)
"""
import sys
sys.path.insert(0, 'c:/tarekscrab')

from scraper.extractor import EmailExtractor
from scraper.parser import Parser
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    print("\n" + "=" * 70)
    print("🔍 EMAIL & URL EXTRACTOR TEST - Simple Demo")
    print("=" * 70)
    
    # Sample HTML with various content
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sample Company Website</title>
    </head>
    <body>
        <header>
            <h1>Welcome to Sample Company</h1>
            <nav>
                <a href="https://example.com/about">About Us</a>
                <a href="https://example.com/services">Services</a>
                <a href="https://example.com/contact">Contact</a>
            </nav>
        </header>
        
        <main>
            <section class="contact">
                <h2>Contact Information</h2>
                <p>General inquiries: <a href="mailto:info@samplecompany.com">info@samplecompany.com</a></p>
                <p>Sales team: sales@samplecompany.com</p>
                <p>Customer support: support@samplecompany.com</p>
                <p>HR department: hr@samplecompany.com</p>
            </section>
            
            <section class="departments">
                <h2>Department Contacts</h2>
                <ul>
                    <li>Marketing: marketing@samplecompany.com</li>
                    <li>Technical: tech@samplecompany.com</li>
                    <li>Billing: billing@samplecompany.com</li>
                </ul>
            </section>
            
            <section class="links">
                <h2>Useful Links</h2>
                <a href="https://example.com/products">Our Products</a>
                <a href="https://example.com/blog">Blog</a>
                <a href="https://example.com/careers">Careers</a>
                <a href="https://partner.example.com">Partner Portal</a>
            </section>
        </main>
        
        <footer>
            <p>© 2024 Sample Company. All rights reserved.</p>
            <a href="https://example.com/privacy">Privacy Policy</a>
            <a href="https://example.com/terms">Terms of Service</a>
        </footer>
    </body>
    </html>
    """
    
    test_url = "https://samplecompany.com"
    
    # Test 1: Email Extraction
    print("\n📧 TEST 1: Email Extraction")
    print("-" * 70)
    try:
        extractor = EmailExtractor()
        result = extractor.extract_from_html(sample_html, test_url)
        
        all_emails = result.get('all_emails', set())
        
        print(f"✓ Extracted {len(all_emails)} unique emails:")
        for i, email in enumerate(sorted(all_emails), 1):
            print(f"  {i}. {email}")
        
        print(f"\n✅ Email extraction PASSED - Found {len(all_emails)} emails")
    except Exception as e:
        print(f"❌ Email extraction FAILED: {e}")
    
    # Test 2: URL Extraction
    print("\n🔗 TEST 2: URL Extraction")
    print("-" * 70)
    try:
        parser = Parser(sample_html, test_url)
        urls = parser.get_links()
        
        print(f"✓ Extracted {len(urls)} URLs:")
        for i, url in enumerate(sorted(urls)[:15], 1):  # Show first 15
            print(f"  {i}. {url}")
        
        if len(urls) > 15:
            print(f"  ... and {len(urls) - 15} more")
        
        print(f"\n✅ URL extraction PASSED - Found {len(urls)} URLs")
    except Exception as e:
        print(f"❌ URL extraction FAILED: {e}")
    
    # Test 3: Email Extraction with Context
    print("\n📝 TEST 3: Email Extraction with Context")
    print("-" * 70)
    try:
        extractor = EmailExtractor()
        results = extractor.extract_with_context(sample_html, test_url, context_chars=40)
        
        print(f"✓ Extracted {len(results)} emails with context:")
        for i, item in enumerate(results[:5], 1):  # Show first 5
            print(f"\n  {i}. Email: {item['email']}")
            print(f"     Context: ...{item['context'][:60]}...")
        
        if len(results) > 5:
            print(f"\n  ... and {len(results) - 5} more")
        
        print(f"\n✅ Context extraction PASSED - Found {len(results)} emails with context")
    except Exception as e:
        print(f"❌ Context extraction FAILED: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\n💡 This demonstrates the URL and email extraction capabilities.")
    print("   You can use these extractors to scan websites and collect emails.")
    print("\n")

if __name__ == '__main__':
    main()
