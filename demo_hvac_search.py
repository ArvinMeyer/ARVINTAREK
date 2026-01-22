"""
Demo: How to use the Google Search Query for HVAC Technicians
This demonstrates the workflow without requiring ChromeDriver
"""
import sys
sys.path.insert(0, 'c:/tarekscrab')

def main():
    print("\n" + "=" * 70)
    print("🔍 HVAC Technician Email Extraction - Workflow Demo")
    print("=" * 70)
    
    # The search query you want to use
    search_query = '"info@*.com" "HVAC Technician" "New York"'
    
    print("\n📝 SEARCH QUERY:")
    print(f"   {search_query}")
    
    print("\n" + "=" * 70)
    print("WORKFLOW OPTIONS")
    print("=" * 70)
    
    print("\n🌐 OPTION 1: Use the Dashboard (RECOMMENDED)")
    print("-" * 70)
    print("1. The dashboard is already running at: http://127.0.0.1:5000")
    print("2. Open your browser and navigate to the dashboard")
    print("3. Click 'New Scan' or 'Start Scan'")
    print("4. You can either:")
    print("   a) Use Google Search integration (if configured)")
    print("   b) Manually enter URLs of HVAC companies in New York")
    print("5. The system will:")
    print("   - Scan each URL")
    print("   - Extract email addresses")
    print("   - Validate emails")
    print("   - Store results in the database")
    
    print("\n🔧 OPTION 2: Manual URL List")
    print("-" * 70)
    print("Since ChromeDriver has compatibility issues, you can:")
    print("1. Manually search Google for: " + search_query)
    print("2. Copy the URLs of HVAC company websites")
    print("3. Create a file with URLs (one per line)")
    print("4. Use the dashboard to import and scan these URLs")
    
    print("\n💻 OPTION 3: Fix ChromeDriver (Advanced)")
    print("-" * 70)
    print("To fix the ChromeDriver SSL issue:")
    print("1. Download ChromeDriver manually from:")
    print("   https://chromedriver.chromium.org/downloads")
    print("2. Match your Chrome browser version")
    print("3. Place chromedriver.exe in your PATH")
    print("4. Then run: python test_google_hvac.py")
    
    print("\n📋 SAMPLE URLS TO TEST WITH:")
    print("-" * 70)
    sample_urls = [
        "https://www.example-hvac-ny.com",
        "https://www.nyc-heating-cooling.com",
        "https://www.manhattan-hvac-services.com",
    ]
    
    print("You can test the system with these sample URLs:")
    for i, url in enumerate(sample_urls, 1):
        print(f"{i}. {url}")
    
    print("\n" + "=" * 70)
    print("QUICK TEST: Email Extraction")
    print("=" * 70)
    
    # Demonstrate email extraction from sample HTML
    from scraper.extractor import EmailExtractor
    
    sample_html = """
    <html>
    <body>
        <h1>NYC HVAC Services</h1>
        <p>Contact us for all your heating and cooling needs!</p>
        <p>Email: info@nychvac.com</p>
        <p>Sales: sales@nychvac.com</p>
        <p>Emergency: emergency@nychvac.com</p>
    </body>
    </html>
    """
    
    print("\nExtracting emails from sample HVAC company page...")
    extractor = EmailExtractor()
    result = extractor.extract_from_html(sample_html, "https://nychvac.com")
    emails = result.get('all_emails', set())
    
    print(f"\n✅ Found {len(emails)} emails:")
    for email in sorted(emails):
        print(f"   • {email}")
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print("\n💡 Next Steps:")
    print("   1. Open the dashboard at http://127.0.0.1:5000")
    print("   2. Start a new scan with your target URLs")
    print("   3. Review and export the extracted emails")
    print("\n")

if __name__ == '__main__':
    main()
