"""
Test script for Google Search URL extraction
"""
import sys
sys.path.insert(0, 'c:/tarekscrab')

from scraper.google_search import GoogleSearchExtractor
from utils.logger import get_logger

logger = get_logger(__name__)

def test_google_search():
    """Test Google search URL extraction"""
    print("=" * 60)
    print("Testing Google Search URL Extraction")
    print("=" * 60)
    
    # Test query
    test_query = '"construction companies" "New York"'
    
    print(f"\nTest Query: {test_query}")
    print(f"Number of Results: 5")
    print("\nStarting ChromeDriver...")
    
    try:
        # Initialize extractor (non-headless for testing)
        with GoogleSearchExtractor(headless=False) as extractor:
            print("✓ ChromeDriver started successfully")
            
            # Search Google
            print(f"\nSearching Google...")
            urls = extractor.search_google(test_query, num_results=5)
            
            print(f"\n✓ Search completed!")
            print(f"✓ Extracted {len(urls)} URLs:")
            print("-" * 60)
            
            for i, url in enumerate(urls, 1):
                print(f"{i}. {url}")
            
            print("-" * 60)
            print(f"\n✅ Test PASSED - Extracted {len(urls)} URLs")
            
    except Exception as e:
        print(f"\n❌ Test FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("\n🔍 Google Search URL Extractor Test\n")
    success = test_google_search()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ TESTS FAILED - Check error messages above")
        print("=" * 60)
        sys.exit(1)
