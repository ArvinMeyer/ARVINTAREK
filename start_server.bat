@echo off
echo ========================================
echo Starting Email Extraction System
echo ========================================
echo.
echo This will start the server accessible from your network.
echo Your IP address: 
ipconfig | findstr /i "IPv4" | findstr /v "Autoconfiguration"
echo.
echo After starting, access from another PC using:
echo http://YOUR_IP:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python main.py dashboard --host 0.0.0.0

pause

