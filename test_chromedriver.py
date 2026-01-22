"""
Test ChromeDriver Installation
Run this to verify ChromeDriver is working correctly
"""
import sys
import os

def test_chromedriver():
    """Test if ChromeDriver is installed and working"""
    
    print("=" * 70)
    print("CHROMEDRIVER INSTALLATION TEST")
    print("=" * 70)
    print()
    
    # Test 1: Check if chromedriver is in PATH
    print("Test 1: Checking if ChromeDriver is in system PATH...")
    import subprocess
    try:
        result = subprocess.run(
            ["chromedriver", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ PASS: {result.stdout.strip()}")
            chromedriver_found = True
        else:
            print("✗ FAIL: ChromeDriver not found in PATH")
            chromedriver_found = False
    except FileNotFoundError:
        print("✗ FAIL: ChromeDriver not found in PATH")
        chromedriver_found = False
    except Exception as e:
        print(f"✗ FAIL: Error running ChromeDriver: {e}")
        chromedriver_found = False
    
    print()
    
    # Test 2: Check if chromedriver.exe is in current directory
    print("Test 2: Checking for chromedriver.exe in project folder...")
    if os.path.exists("chromedriver.exe"):
        print("✓ PASS: Found chromedriver.exe in current directory")
        try:
            result = subprocess.run(
                ["./chromedriver.exe", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"  Version: {result.stdout.strip()}")
            chromedriver_found = True
        except Exception as e:
            print(f"✗ FAIL: Error running local ChromeDriver: {e}")
    else:
        print("✗ FAIL: chromedriver.exe not found in current directory")
    
    print()
    
    # Test 3: Try to initialize undetected-chromedriver
    if chromedriver_found:
        print("Test 3: Testing undetected-chromedriver initialization...")
        
        # Try with explicit driver path first
        chromedriver_path = None
        if os.path.exists("chromedriver.exe"):
            chromedriver_path = os.path.abspath("chromedriver.exe")
            print(f"  Using local ChromeDriver: {chromedriver_path}")
        
        try:
            import undetected_chromedriver as uc
            print("  Attempting to create ChromeDriver instance...")
            
            options = uc.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            
            # Try with explicit path first to bypass auto-download
            if chromedriver_path:
                try:
                    print("  Strategy 1: Using explicit driver path...")
                    driver = uc.Chrome(
                        options=options,
                        driver_executable_path=chromedriver_path,
                        use_subprocess=False
                    )
                    print("✓ PASS: ChromeDriver initialized with explicit path!")
                except Exception as e1:
                    print(f"  Strategy 1 failed: {e1}")
                    print("  Strategy 2: Trying default initialization...")
                    driver = uc.Chrome(options=options, version_main=None)
                    print("✓ PASS: ChromeDriver initialized with default method!")
            else:
                driver = uc.Chrome(options=options, version_main=None)
                print("✓ PASS: ChromeDriver initialized successfully!")
            
            # Try to navigate to a simple page
            print("  Testing navigation...")
            driver.get("https://www.google.com")
            print(f"✓ PASS: Successfully navigated to Google")
            print(f"  Page title: {driver.title}")
            
            driver.quit()
            print("✓ PASS: All tests passed! ChromeDriver is working correctly.")
            print()
            print("=" * 70)
            print("SUCCESS: You can now use Google Search in the dashboard!")
            print("=" * 70)
            return True
            
        except Exception as e:
            print(f"✗ FAIL: Error initializing ChromeDriver: {e}")
            print()
            print("DIAGNOSIS:")
            if "10054" in str(e) or "forcibly closed" in str(e).lower():
                print("  The WinError 10054 is still occurring.")
                print("  This means undetected-chromedriver is trying to download")
                print("  additional components and your network is blocking it.")
                print()
                print("WORKAROUND:")
                print("  Use manual URL entry instead of Google Search automation:")
                print("  1. Go to Dashboard → New Scan")
                print("  2. Paste URLs directly (one per line)")
                print("  3. Start the scan")
                print()
                print("  This bypasses ChromeDriver entirely and still extracts emails!")
            else:
                print("  This might be the auto-download issue.")
                print("  Make sure chromedriver.exe is in your PATH or current directory.")
    else:
        print("Test 3: SKIPPED (ChromeDriver not found)")
    
    print()
    print("=" * 70)
    print("INSTALLATION NEEDED")
    print("=" * 70)
    print()
    print("ChromeDriver is not properly installed. Here's what to do:")
    print()
    print("1. Download ChromeDriver:")
    print("   https://googlechromelabs.github.io/chrome-for-testing/")
    print()
    print("2. Extract chromedriver.exe from the ZIP file")
    print()
    print("3. Copy it to ONE of these locations:")
    print("   Option A (Recommended): C:\\Windows\\System32\\")
    print("   Option B (Easy): " + os.path.abspath("."))
    print()
    print("4. Run this test again:")
    print("   python test_chromedriver.py")
    print()
    print("=" * 70)
    
    return False

if __name__ == "__main__":
    success = test_chromedriver()
    sys.exit(0 if success else 1)
