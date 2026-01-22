# SMTP Configuration Guide

## Common SMTP Settings

### Gmail
```
SENDER_SMTP_HOST=smtp.gmail.com
SENDER_SMTP_PORT=587
SENDER_SMTP_USER=your-email@gmail.com
SENDER_SMTP_PASSWORD=your-app-password
SENDER_SMTP_USE_TLS=True
SENDER_FROM_EMAIL=your-email@gmail.com
SENDER_FROM_NAME=Your Name
SENDER_SMTP_TIMEOUT=60
```

**Important for Gmail:**
- You MUST use an App Password (not your regular password)
- Enable 2-Factor Authentication first
- Generate App Password: https://myaccount.google.com/apppasswords

### Outlook/Hotmail
```
SENDER_SMTP_HOST=smtp-mail.outlook.com
SENDER_SMTP_PORT=587
SENDER_SMTP_USER=your-email@outlook.com
SENDER_SMTP_PASSWORD=your-password
SENDER_SMTP_USE_TLS=True
SENDER_FROM_EMAIL=your-email@outlook.com
SENDER_FROM_NAME=Your Name
```

### Yahoo
```
SENDER_SMTP_HOST=smtp.mail.yahoo.com
SENDER_SMTP_PORT=587
SENDER_SMTP_USER=your-email@yahoo.com
SENDER_SMTP_PASSWORD=your-app-password
SENDER_SMTP_USE_TLS=True
SENDER_FROM_EMAIL=your-email@yahoo.com
SENDER_FROM_NAME=Your Name
```

### Custom SMTP Server
```
SENDER_SMTP_HOST=mail.yourdomain.com
SENDER_SMTP_PORT=587
SENDER_SMTP_USER=your-username
SENDER_SMTP_PASSWORD=your-password
SENDER_SMTP_USE_TLS=True
SENDER_FROM_EMAIL=noreply@yourdomain.com
SENDER_FROM_NAME=Your Company
SENDER_SMTP_TIMEOUT=60
```

## Troubleshooting Timeout Errors

### 1. Check Your .env File
Make sure all SMTP settings are set correctly in your `.env` file:
- No typos in host/port
- Port is a number (587, 465, 25)
- TLS is True/False (not a string)

### 2. Test Network Connectivity
Try pinging the SMTP server:
```bash
ping smtp.gmail.com
# or
telnet smtp.gmail.com 587
```

### 3. Check Firewall
- Windows Firewall might be blocking outbound connections
- Antivirus software might block SMTP
- Corporate firewall might block port 587

### 4. Increase Timeout
If the server is slow, increase timeout:
```
SENDER_SMTP_TIMEOUT=60
```

### 5. Try Different Ports
- Port 587: TLS (most common)
- Port 465: SSL (older, less common)
- Port 25: No encryption (often blocked by ISPs)

### 6. Verify Credentials
- Double-check username and password
- For Gmail: Make sure you're using App Password, not regular password
- Check if account has 2FA enabled (required for App Passwords)

## Quick Test

After updating your `.env` file:
1. Restart your Flask server
2. Go to `/sender` page
3. Click "Test SMTP Connection"
4. Check the error message and current settings shown

## Common Errors

**"Connection timeout"**
- Server is unreachable
- Wrong host/port
- Firewall blocking
- Network issues

**"Authentication failed"**
- Wrong username/password
- For Gmail: Not using App Password
- Account locked/disabled

**"Connection refused"**
- Wrong port number
- Server not accepting connections on that port
- Try port 587 or 465

