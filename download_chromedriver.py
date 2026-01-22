"""
Quick ChromeDriver Download Helper
This script helps you download the correct ChromeDriver version
"""
import urllib.request
import zipfile
import os
import shutil

def download_chromedriver():
    """Download ChromeDriver for Chrome 143"""
    
    print("=" * 70)
    print("ChromeDriver Download Helper")
    print("=" * 70)
    print()
    print("Your Chrome version: 143.0.7499.170")
    print()
    
    # ChromeDriver download URL for Chrome 143
    # Note: You may need to check https://googlechromelabs.github.io/chrome-for-testing/
    # for the exact URL for version 143
    
    print("MANUAL DOWNLOAD REQUIRED:")
    print()
    print("1. Open your browser and go to:")
    print("   https://googlechromelabs.github.io/chrome-for-testing/")
    print()
    print("2. Look for 'Stable' channel")
    print("3. Find 'chromedriver' for 'win64'")
    print("4. Download the ZIP file")
    print()
    print("5. Extract chromedriver.exe from the ZIP")
    print()
    print("6. Copy chromedriver.exe to one of these locations:")
    print("   Option A: C:\\Windows\\System32\\")
    print("   Option B: " + os.path.abspath("."))
    print()
    print("7. After copying, run this test again:")
    print("   python test_chromedriver.py")
    print()
    print("=" * 70)
    
    # Check if chromedriver.exe is in current directory
    if os.path.exists("chromedriver.exe"):
        print()
        print("✓ Found chromedriver.exe in current directory!")
        print()
        
        # Test it
        import subprocess
        try:
            result = subprocess.run(
                ["chromedriver.exe", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print("ChromeDriver version:", result.stdout.strip())
            print()
            print("✓ ChromeDriver is working!")
            print()
            print("You can now use Google Search in the dashboard.")
            return True
        except Exception as e:
            print(f"✗ Error testing ChromeDriver: {e}")
            return False
    else:
        print()
        print("✗ chromedriver.exe not found in current directory")
        print("  Please download and place it here first.")
        return False

if __name__ == "__main__":
    download_chromedriver()
