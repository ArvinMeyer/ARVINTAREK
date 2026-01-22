# Network Access Guide

## Quick Fix for Windows Firewall

If you can't access the application from another PC, Windows Firewall is likely blocking it.

### Option 1: Allow through Firewall (Recommended)

Run this command in PowerShell as Administrator:

```powershell
New-NetFirewallRule -DisplayName "Flask Email System" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

Or manually:
1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → Next
5. Select "TCP" and enter port "5000" → Next
6. Select "Allow the connection" → Next
7. Check all profiles (Domain, Private, Public) → Next
8. Name it "Flask Email System" → Finish

### Option 2: Temporarily Disable Firewall (Not Recommended)

Only for testing:
1. Open Windows Defender Firewall
2. Turn off firewall for Private networks (temporarily)
3. Test access
4. Turn it back on and use Option 1

## Verify Server is Running

1. Check if server is listening on all interfaces:
   ```cmd
   netstat -an | findstr ":5000"
   ```
   
   You should see: `0.0.0.0:5000` (not `127.0.0.1:5000`)

2. Check your IP address:
   ```cmd
   ipconfig
   ```
   
   Look for "IPv4 Address" under your network adapter (usually `192.168.x.x`)

## Access from Another PC

1. Make sure both PCs are on the same network (same Wi-Fi/router)
2. From the other PC, open browser and go to:
   ```
   http://192.168.1.11:5000
   ```
   (Replace with your actual IP from ipconfig)

## Troubleshooting

### Can't connect from another PC:
- ✅ Check Windows Firewall (see above)
- ✅ Verify server shows "Network access: http://192.168.1.11:5000" in console
- ✅ Make sure both PCs are on same network
- ✅ Try pinging the server PC: `ping 192.168.1.11`
- ✅ Check if antivirus is blocking the connection

### Server not showing network access:
- Restart the server: `python main.py dashboard`
- Check `.env` file - make sure `FLASK_HOST=0.0.0.0` or remove it to use default
- Verify in console output it shows the network IP

### Connection timeout:
- Firewall is blocking - use Option 1 above
- Port 5000 might be in use - try different port: `python main.py dashboard --port 8080`

