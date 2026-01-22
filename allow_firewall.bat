@echo off
echo ========================================
echo Adding Windows Firewall Rule
echo ========================================
echo.
echo This will allow port 5000 through Windows Firewall
echo You need to run this as Administrator!
echo.
pause

powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0fix_firewall.ps1\"' -Verb RunAs"

echo.
echo If the rule was added successfully, you should now be able to
echo access the application from other devices on your network.
echo.
pause

