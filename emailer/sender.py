"""
Bulk email sender module
"""
import smtplib
import socket
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Optional, Tuple
from jinja2 import Template
from utils.db import get_db_session, SendReport, DeliveryRecord, EmailValid
from utils.logger import get_logger
import config

logger = get_logger(__name__)

class EmailSender:
    """Bulk email sender with rate limiting"""
    
    def __init__(self, smtp_host: str = None, smtp_port: int = None,
                 smtp_user: str = None, smtp_password: str = None,
                 use_tls: bool = None, from_email: str = None, from_name: str = None):
        """
        Initialize email sender
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            use_tls: Use TLS encryption
            from_email: From email address (overrides config)
            from_name: From name (overrides config)
        """
        self.smtp_host = smtp_host or config.SENDER_SMTP_HOST
        self.smtp_port = smtp_port or config.SENDER_SMTP_PORT
        self.smtp_user = smtp_user or config.SENDER_SMTP_USER
        self.smtp_password = smtp_password or config.SENDER_SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else config.SENDER_SMTP_USE_TLS
        self.from_email = from_email or config.SENDER_FROM_EMAIL
        self.from_name = from_name or config.SENDER_FROM_NAME
    
    def send_email(self, to_email: str, subject: str, body_html: str,
                   body_text: str = None, attachments: List[str] = None) -> Tuple[bool, str]:
        """
        Send a single email
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body (optional)
            attachments: List of file paths to attach
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text part
            if body_text:
                msg.attach(MIMEText(body_text, 'plain'))
            
            # Add HTML part
            msg.attach(MIMEText(body_html, 'html'))
            
            # Add attachments
            if attachments:
                for filepath in attachments:
                    try:
                        with open(filepath, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition',
                                          f'attachment; filename={filepath.split("/")[-1]}')
                            msg.attach(part)
                    except Exception as e:
                        logger.warning(f"Failed to attach {filepath}: {e}")
            
            # Connect and send with retry logic
            max_retries = 2
            # Use SENDER_SMTP_TIMEOUT if available, otherwise default to 30 seconds
            smtp_timeout = getattr(config, 'SENDER_SMTP_TIMEOUT', 30)
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # Port 465 uses SSL (implicit), port 587 uses STARTTLS
                    if self.smtp_port == 465:
                        # Use SSL for port 465
                        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=smtp_timeout) as server:
                            server.login(self.smtp_user, self.smtp_password)
                            server.send_message(msg)
                    else:
                        # Use STARTTLS for port 587 and others
                        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=smtp_timeout) as server:
                            if self.use_tls:
                                server.starttls()
                            
                            server.login(self.smtp_user, self.smtp_password)
                            server.send_message(msg)
                    
                    logger.info(f"Email sent to {to_email}")
                    return True, ''
                    
                except (smtplib.SMTPServerDisconnected, ConnectionError, OSError, socket.timeout, socket.error) as e:
                    # Connection errors - retry
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2s, 4s
                        logger.warning(f"Connection error sending to {to_email} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"Connection error after {max_retries} attempts: {str(e)}"
                        logger.error(f"Failed to send to {to_email}: {error_msg}")
                        return False, error_msg
                        
                except smtplib.SMTPException as e:
                    # SMTP protocol errors - don't retry
                    error_msg = f"SMTP error: {str(e)}"
                    logger.error(f"Failed to send to {to_email}: {error_msg}")
                    return False, error_msg
                    
                except Exception as e:
                    # Other errors - retry once
                    last_error = e
                    if attempt < max_retries - 1 and ("timeout" in str(e).lower() or "timed out" in str(e).lower()):
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"Timeout error sending to {to_email} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"Error: {str(e)}"
                        logger.error(f"Failed to send to {to_email}: {error_msg}")
                        return False, error_msg
            
            # If we get here, all retries failed
            error_msg = f"Failed after {max_retries} attempts: {str(last_error)}"
            logger.error(f"Failed to send to {to_email}: {error_msg}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to send to {to_email}: {error_msg}")
            return False, error_msg
    
    def send_campaign(self, campaign_id: int, template_html: str,
                     template_text: str = None, attachments: List[str] = None) -> dict:
        """
        Send bulk email campaign
        
        Args:
            campaign_id: SendReport ID
            template_html: HTML email template (Jinja2)
            template_text: Plain text template (Jinja2)
            attachments: List of file paths to attach
        
        Returns:
            Dictionary with campaign statistics
        """
        db = get_db_session()
        stats = {'sent': 0, 'failed': 0, 'total': 0}
        
        try:
            # Get campaign
            campaign = db.query(SendReport).filter_by(id=campaign_id).first()
            
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return stats
            
            # Update campaign status
            campaign.status = 'running'
            campaign.started_at = datetime.utcnow()
            db.commit()
            
            # Get valid emails (you might want to filter by specific criteria)
            recipients = db.query(EmailValid).limit(campaign.total_recipients).all()
            stats['total'] = len(recipients)
            
            logger.info(f"Starting campaign '{campaign.campaign_name}' to {stats['total']} recipients")
            
            # Compile templates
            html_template = Template(template_html)
            text_template = Template(template_text) if template_text else None
            
            # Send emails with rate limiting
            for i, recipient in enumerate(recipients):
                try:
                    # Render templates with personalization
                    context = {
                        'email': recipient.email,
                        'domain': recipient.domain,
                        'unsubscribe_link': f'https://example.com/unsubscribe?email={recipient.email}'
                    }
                    
                    body_html = html_template.render(**context)
                    body_text = text_template.render(**context) if text_template else None
                    
                    # Send email
                    success, error_msg = self.send_email(
                        recipient.email,
                        campaign.subject,
                        body_html,
                        body_text,
                        attachments
                    )
                    
                    # Record delivery
                    delivery = DeliveryRecord(
                        send_report_id=campaign_id,
                        recipient_email=recipient.email,
                        status='sent' if success else 'failed',
                        error_message=error_msg if not success else None,
                        sent_at=datetime.utcnow() if success else None
                    )
                    db.add(delivery)
                    
                    if success:
                        stats['sent'] += 1
                        campaign.sent_count += 1
                    else:
                        stats['failed'] += 1
                        campaign.failed_count += 1
                    
                    db.commit()
                    
                    # Rate limiting
                    if (i + 1) % config.SENDER_BATCH_SIZE == 0:
                        logger.info(f"Batch complete ({i + 1}/{stats['total']}). Pausing...")
                        time.sleep(config.SENDER_BATCH_DELAY)
                    else:
                        delay = random.uniform(config.SENDER_MIN_DELAY, config.SENDER_MAX_DELAY)
                        time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error sending to {recipient.email}: {e}")
                    stats['failed'] += 1
                    campaign.failed_count += 1
                    db.commit()
            
            # Update campaign status
            campaign.status = 'completed'
            campaign.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Campaign complete: {stats['sent']} sent, {stats['failed']} failed")
            
        except Exception as e:
            logger.error(f"Campaign error: {e}")
            if campaign:
                campaign.status = 'failed'
                db.commit()
        finally:
            db.close()
        
        return stats
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test SMTP connection
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use configurable timeout
            smtp_timeout = getattr(config, 'SENDER_SMTP_TIMEOUT', 30)
            
            if not self.smtp_host or not self.smtp_port:
                return False, 'SMTP host and port are not configured'
            
            if not self.smtp_user or not self.smtp_password:
                return False, 'SMTP username and password are not configured'
            
            # Log connection attempt details
            connection_type = "SSL" if self.smtp_port == 465 else ("TLS" if self.use_tls else "Plain")
            logger.info(f"Testing SMTP connection to {self.smtp_host}:{self.smtp_port} (timeout: {smtp_timeout}s, Encryption: {connection_type})")
            
            # Try to connect with timeout
            # Port 465 uses SSL (implicit), port 587 uses STARTTLS
            try:
                if self.smtp_port == 465:
                    # Use SSL for port 465
                    logger.debug(f"Connecting to {self.smtp_host}:{self.smtp_port} using SSL...")
                    server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=smtp_timeout)
                else:
                    # Use STARTTLS for port 587 and others
                    logger.debug(f"Connecting to {self.smtp_host}:{self.smtp_port}...")
                    server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=smtp_timeout)
            except (socket.timeout, OSError, ConnectionError) as e:
                return False, f'Cannot connect to {self.smtp_host}:{self.smtp_port} - {str(e)}. Check host, port, and network.'
            
            try:
                # Test TLS if enabled (only for non-SSL ports)
                if self.use_tls and self.smtp_port != 465:
                    logger.debug("Starting TLS...")
                    server.starttls()
                    logger.debug("TLS started successfully")
                
                # Test authentication
                logger.debug("Attempting login...")
                server.login(self.smtp_user, self.smtp_password)
                logger.debug("Login successful")
                
                # Close connection
                server.quit()
                
                return True, f'Connection successful to {self.smtp_host}:{self.smtp_port}'
                
            except smtplib.SMTPAuthenticationError as e:
                server.quit()
                return False, f'Authentication failed: Check your username and password. For Gmail, use an App Password (not your regular password).'
            except smtplib.SMTPException as e:
                try:
                    server.quit()
                except:
                    pass
                return False, f'SMTP error: {str(e)}'
            except Exception as e:
                try:
                    server.quit()
                except:
                    pass
                raise
                
        except socket.timeout as e:
            return False, f'Connection timeout: Server {self.smtp_host}:{self.smtp_port} did not respond within {smtp_timeout} seconds. The server may be down or unreachable.'
        except (ConnectionError, OSError, socket.error) as e:
            error_str = str(e).lower()
            if 'refused' in error_str:
                return False, f'Connection refused: {self.smtp_host}:{self.smtp_port} is not accepting connections. Check if the port is correct.'
            elif 'timeout' in error_str or 'timed out' in error_str:
                return False, f'Connection timeout: Cannot reach {self.smtp_host}:{self.smtp_port}. Check network, firewall, and DNS.'
            else:
                return False, f'Connection error: {str(e)}. Check host ({self.smtp_host}), port ({self.smtp_port}), and network connection.'
        except Exception as e:
            logger.error(f"Unexpected error testing SMTP connection: {e}", exc_info=True)
            return False, f'Connection failed: {str(e)}'
