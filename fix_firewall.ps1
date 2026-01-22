# PowerShell script to add Windows Firewall rule for Flask Email System
# Run this as Administrator

Write-Host "Adding Windows Firewall rule for Flask Email System..." -ForegroundColor Green

try {
    # Remove existing rule if it exists
    Remove-NetFirewallRule -DisplayName "Flask Email System" -ErrorAction SilentlyContinue
    
    # Add new rule
    New-NetFirewallRule -DisplayName "Flask Email System" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow -Profile Any
    
    Write-Host "✓ Firewall rule added successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The application should now be accessible from other devices on your network." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To verify, check if the rule exists:" -ForegroundColor Cyan
    Write-Host "  Get-NetFirewallRule -DisplayName 'Flask Email System'" -ForegroundColor White
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you're running PowerShell as Administrator!" -ForegroundColor Yellow
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
}

