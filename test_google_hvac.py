"""
Test Google Search for HVAC Technicians in New York
"""
import sys
sys.path.insert(0, 'c:/tarekscrab')

from scraper.google_search import GoogleSearchExtractor
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    print("\n" + "=" * 70)
    print("🔍 Google Search Test: HVAC Technicians in New York")
    print("=" * 70)
    
    # Search query
    query = '"info@*.com" "HVAC Technician" "New York"'
    num_results = 10
    
    print(f"\n📝 Search Query: {query}")
    print(f"📊 Requested Results: {num_results}")
    print("\n⏳ Starting ChromeDriver (this may take a moment)...")
    
    try:
        # Use headless=False to see the browser in action
        with GoogleSearchExtractor(headless=False) as extractor:
            print("✅ ChromeDriver started successfully!")
            print("\n🔎 Searching Google...")
            
            # Perform search
            urls = extractor.search_google(query, num_results=num_results)
            
            print(f"\n✅ Search completed!")
            print(f"📌 Found {len(urls)} URLs:")
            print("-" * 70)
            
            for i, url in enumerate(urls, 1):
                print(f"{i}. {url}")
            
            print("-" * 70)
            
            if len(urls) > 0:
                print(f"\n✅ SUCCESS - Extracted {len(urls)} URLs from Google search")
                print("\n💡 Next steps:")
                print("   - These URLs can be scanned for email addresses")
                print("   - Use the dashboard to start a scan with these URLs")
                print("   - Or use the Scanner class to automate extraction")
            else:
                print("\n⚠️  No URLs found - Google may have blocked the request")
                print("   Try running with headless=True or adjust search query")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
