# Deployment Guide

Production deployment guide for Email Extraction & Verification System on VPS servers.

## Deployment Options

1. **Hostinger VPS**
2. **Hetzner Cloud**
3. **DigitalOcean**
4. **AWS EC2**
5. **Any Linux VPS**

This guide focuses on Ubuntu 22.04 LTS deployment.

## Prerequisites

- VPS with Ubuntu 22.04 LTS
- Root or sudo access
- Domain name (optional, for SSL)
- SSH access

## Step 1: Server Setup

### Connect to Server
```bash
ssh root@your-server-ip
```

### Update System
```bash
apt update && apt upgrade -y
```

### Create Application User
```bash
adduser emailapp
usermod -aG sudo emailapp
su - emailapp
```

## Step 2: Install Dependencies

### Install Python 3.10+
```bash
sudo apt install python3.10 python3.10-venv python3-pip -y
python3.10 --version
```

### Install Chrome
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y
google-chrome --version
```

### Install Nginx
```bash
sudo apt install nginx -y
sudo systemctl enable nginx
```

## Step 3: Deploy Application

### Clone/Upload Project
```bash
cd /home/emailapp
# Upload your project files via SCP or Git
# For this example, assume files are in /home/emailapp/emailapp
```

### Create Virtual Environment
```bash
cd /home/emailapp/emailapp
python3.10 -m venv venv
source venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Environment
```bash
cp .env.example .env
nano .env
```

Update settings:
```env
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=False
SECRET_KEY=your-production-secret-key
SELENIUM_HEADLESS=True
```

### Initialize Database
```bash
python main.py init-db
```

## Step 4: Create Systemd Service

Create service file:
```bash
sudo nano /etc/systemd/system/emailapp.service
```

Add content:
```ini
[Unit]
Description=Email Extraction System
After=network.target

[Service]
Type=simple
User=emailapp
WorkingDirectory=/home/emailapp/emailapp
Environment="PATH=/home/emailapp/emailapp/venv/bin"
ExecStart=/home/emailapp/emailapp/venv/bin/python main.py dashboard --host 127.0.0.1 --port 5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable emailapp
sudo systemctl start emailapp
sudo systemctl status emailapp
```

## Step 5: Configure Nginx Reverse Proxy

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/emailapp
```

Add content:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # or server IP

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Increase timeouts for long-running scans
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;
}
```

### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/emailapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 6: Configure Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (for SSL)
sudo ufw enable
sudo ufw status
```

## Step 7: SSL Certificate (Optional but Recommended)

### Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Obtain Certificate
```bash
sudo certbot --nginx -d your-domain.com
```

Follow prompts to configure SSL.

### Auto-Renewal
```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

## Step 8: Monitoring and Logs

### View Application Logs
```bash
# Systemd logs
sudo journalctl -u emailapp -f

# Application logs
tail -f /home/emailapp/emailapp/logs/app.log
```

### Monitor System Resources
```bash
htop
```

### Check Service Status
```bash
sudo systemctl status emailapp
sudo systemctl status nginx
```

## Step 9: Backup Strategy

### Database Backup Script
Create `/home/emailapp/backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/home/emailapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp /home/emailapp/emailapp/data/emails.db $BACKUP_DIR/emails_$DATE.db
# Keep only last 7 days
find $BACKUP_DIR -name "emails_*.db" -mtime +7 -delete
```

Make executable:
```bash
chmod +x /home/emailapp/backup.sh
```

### Schedule with Cron
```bash
crontab -e
```

Add:
```
0 2 * * * /home/emailapp/backup.sh
```

## Step 10: Security Hardening

### Restrict Access
Update Nginx config to add basic auth:
```nginx
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:5000;
    # ... rest of config
}
```

Create password file:
```bash
sudo apt install apache2-utils -y
sudo htpasswd -c /etc/nginx/.htpasswd admin
sudo systemctl restart nginx
```

### Fail2Ban (Optional)
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Maintenance

### Update Application
```bash
cd /home/emailapp/emailapp
source venv/bin/activate
git pull  # if using git
pip install -r requirements.txt --upgrade
sudo systemctl restart emailapp
```

### Clear Database
```bash
# Backup first!
./backup.sh
# Then access dashboard and use "Purge Database" button
```

### Restart Services
```bash
sudo systemctl restart emailapp
sudo systemctl restart nginx
```

## Performance Optimization

### Increase Worker Threads
Edit `.env`:
```env
SCRAPER_THREADS=5  # Increase for more powerful servers
```

### Database Optimization
For large datasets, consider migrating to PostgreSQL:
```bash
sudo apt install postgresql postgresql-contrib -y
```

Update `config.py` to use PostgreSQL connection string.

## Troubleshooting

### Application Won't Start
```bash
# Check logs
sudo journalctl -u emailapp -n 50

# Check permissions
ls -la /home/emailapp/emailapp

# Verify Python path
which python
```

### Nginx 502 Bad Gateway
```bash
# Check if app is running
sudo systemctl status emailapp

# Check port binding
sudo netstat -tlnp | grep 5000
```

### ChromeDriver Issues
```bash
# Update Chrome
sudo apt update
sudo apt upgrade google-chrome-stable

# Clear cache
rm -rf ~/.cache/selenium
```

## Monitoring Tools (Optional)

### Install Prometheus + Grafana
For advanced monitoring, consider setting up:
- Prometheus for metrics collection
- Grafana for visualization
- Node Exporter for system metrics

## Cost Estimates

### Hostinger VPS
- **VPS 1:** $4.99/month (2GB RAM, 1 CPU)
- **VPS 2:** $8.99/month (4GB RAM, 2 CPU) ✅ Recommended
- **VPS 3:** $12.99/month (8GB RAM, 4 CPU)

### Hetzner Cloud
- **CX11:** €4.15/month (2GB RAM, 1 CPU)
- **CX21:** €5.83/month (4GB RAM, 2 CPU) ✅ Recommended
- **CX31:** €10.59/month (8GB RAM, 2 CPU)

### DigitalOcean
- **Basic:** $6/month (1GB RAM, 1 CPU)
- **Basic:** $12/month (2GB RAM, 1 CPU) ✅ Recommended
- **Basic:** $18/month (2GB RAM, 2 CPU)

## Conclusion

Your Email Extraction System is now deployed and running in production!

Access your dashboard at:
- HTTP: `http://your-domain.com`
- HTTPS: `https://your-domain.com`

For support, check logs and refer to [README.md](README.md).

---

**Deployment complete!** Monitor your application and enjoy automated email extraction.
