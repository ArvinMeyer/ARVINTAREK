"""
Multi-stage email validation pipeline
"""
import re
import socket
import smtplib
import ssl
import dns.resolver
import whois
from datetime import datetime, timedelta
from typing import Tuple, Optional
from utils.logger import get_logger
from utils.helpers import extract_domain, retry
import config

logger = get_logger(__name__)

class EmailValidator:
    """Multi-stage email validation"""
    
    def __init__(self):
        """Initialize validator"""
        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.timeout = 5
        self.dns_resolver.lifetime = 5
    
    def validate(self, email: str) -> Tuple[bool, str, str, dict]:
        """
        Validate email through all stages
        
        Args:
            email: Email address to validate
        
        Returns:
            Tuple of (is_valid, rejection_reason, rejection_stage, metadata)
        """
        metadata = {}
        
        # Stage 1: Regex validation
        if config.VALIDATION_ENABLE_REGEX:
            is_valid, reason = self.validate_regex(email)
            if not is_valid:
                return False, reason, 'regex', metadata
        
        # Stage 2: Disposable domain check
        if config.VALIDATION_ENABLE_DISPOSABLE:
            is_valid, reason = self.check_disposable(email)
            if not is_valid:
                return False, reason, 'disposable', metadata
        
        # Stage 3: DNS validation
        if config.VALIDATION_ENABLE_DNS:
            is_valid, reason, dns_meta = self.validate_dns(email)
            metadata.update(dns_meta)
            if not is_valid:
                return False, reason, 'dns', metadata
        
        # Stage 4: SMTP validation
        if config.VALIDATION_ENABLE_SMTP:
            is_valid, reason, smtp_meta = self.validate_smtp(email)
            metadata.update(smtp_meta)
            if not is_valid:
                return False, reason, 'smtp', metadata
        
        # Stage 5: Domain age check
        if config.VALIDATION_ENABLE_WHOIS:
            is_valid, reason, whois_meta = self.check_domain_age(email)
            metadata.update(whois_meta)
            if not is_valid:
                return False, reason, 'whois', metadata
        
        # Stage 6: SSL check
        if config.VALIDATION_ENABLE_SSL:
            is_valid, reason, ssl_meta = self.check_ssl(email)
            metadata.update(ssl_meta)
            # Note: SSL check is informational, doesn't reject
        
        return True, '', '', metadata
    
    def validate_regex(self, email: str) -> Tuple[bool, str]:
        """
        Validate email format using regex
        
        Args:
            email: Email address
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        # RFC 5322 compliant regex (simplified)
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False, 'Invalid email format'
        
        # Check length
        if len(email) > 254:
            return False, 'Email too long'
        
        # Check local part length
        local_part = email.split('@')[0]
        if len(local_part) > 64:
            return False, 'Local part too long'
        
        return True, ''
    
    def check_disposable(self, email: str) -> Tuple[bool, str]:
        """
        Check if email is from disposable domain
        
        Args:
            email: Email address
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        domain = extract_domain(email)
        
        if domain in config.DISPOSABLE_DOMAINS:
            return False, f'Disposable domain: {domain}'
        
        return True, ''
    
    @retry(max_attempts=2, delay=0.5)
    def validate_dns(self, email: str) -> Tuple[bool, str, dict]:
        """
        Validate domain DNS records
        
        Args:
            email: Email address
        
        Returns:
            Tuple of (is_valid, rejection_reason, metadata)
        """
        domain = extract_domain(email)
        metadata = {'has_a_record': False, 'has_mx_record': False}
        
        has_nxdomain = False
        
        try:
            # Check A record
            try:
                self.dns_resolver.resolve(domain, 'A')
                metadata['has_a_record'] = True
            except dns.resolver.NXDOMAIN:
                # Domain doesn't exist - this is a definitive failure
                has_nxdomain = True
            except dns.resolver.NoAnswer:
                # No A record, but domain exists - that's OK
                pass
            except Exception as e:
                # Check if it's a timeout/lifetime error
                error_str = str(e).lower()
                if 'timeout' in error_str or 'lifetime' in error_str or 'expired' in error_str:
                    # Timeout - don't reject, could be temporary network issue
                    logger.debug(f"DNS A record lookup timeout for {domain}: {e}")
                else:
                    # Other errors (network issues, etc.) - don't reject
                    logger.debug(f"DNS A record lookup error for {domain}: {e}")
                pass
            
            # Check MX record
            try:
                mx_records = self.dns_resolver.resolve(domain, 'MX')
                if mx_records:
                    metadata['has_mx_record'] = True
            except dns.resolver.NXDOMAIN:
                # Domain doesn't exist - this is a definitive failure
                has_nxdomain = True
            except dns.resolver.NoAnswer:
                # No MX record, but domain exists - that's OK
                pass
            except Exception as e:
                # Check if it's a timeout/lifetime error
                error_str = str(e).lower()
                if 'timeout' in error_str or 'lifetime' in error_str or 'expired' in error_str:
                    # Timeout - don't reject, could be temporary network issue
                    logger.debug(f"DNS MX record lookup timeout for {domain}: {e}")
                else:
                    # Other errors (network issues, etc.) - don't reject
                    logger.debug(f"DNS MX record lookup error for {domain}: {e}")
                pass
            
            # Only reject if domain definitively doesn't exist (NXDOMAIN)
            if has_nxdomain:
                return False, 'Domain does not exist (NXDOMAIN)', metadata
            
            # If we found records, definitely valid
            if metadata['has_mx_record'] or metadata['has_a_record']:
                return True, '', metadata
            
            # If no records found but no NXDOMAIN, could be temporary issue
            # Be lenient - allow it to pass (regex and format validation already passed)
            # Many valid domains might have DNS issues temporarily
            logger.debug(f"No DNS records found for {domain}, but allowing (could be temporary)")
            return True, '', metadata
            
        except dns.resolver.NXDOMAIN:
            # Domain definitively doesn't exist
            return False, 'Domain does not exist (NXDOMAIN)', metadata
        except Exception as e:
            # Check if it's a timeout/lifetime error
            error_str = str(e).lower()
            if 'timeout' in error_str or 'lifetime' in error_str or 'expired' in error_str:
                # Timeout/lifetime expired - don't reject, could be temporary network issue
                logger.debug(f"DNS validation timeout for {domain}: {e}")
                return True, '', metadata
            elif 'nxdomain' in error_str:
                # Domain doesn't exist
                return False, 'Domain does not exist (NXDOMAIN)', metadata
            else:
                # Other errors (network issues, resolver errors, etc.) - don't reject
                # Temporary DNS issues shouldn't invalidate emails
                logger.debug(f"DNS validation error for {domain}: {e}")
                return True, '', metadata
    
    @retry(max_attempts=2, delay=1.0)
    def validate_smtp(self, email: str) -> Tuple[bool, str, dict]:
        """
        Validate email via SMTP handshake
        
        Args:
            email: Email address
        
        Returns:
            Tuple of (is_valid, rejection_reason, metadata)
        """
        domain = extract_domain(email)
        metadata = {'smtp_valid': False, 'is_catch_all': False}
        
        try:
            # Try to get MX records first
            mx_host = None
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                if mx_records:
                    mx_host = str(mx_records[0].exchange).rstrip('.')
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                # No MX records, try A record as fallback
                try:
                    a_records = dns.resolver.resolve(domain, 'A')
                    if a_records:
                        mx_host = str(a_records[0]).rstrip('.')
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                    # No MX or A records - but don't reject here, DNS validation already checked this
                    logger.debug(f"No MX or A records for {domain}, skipping SMTP")
                    return True, '', metadata
            
            if not mx_host:
                # Can't determine mail server, but DNS validation already passed
                # So we'll allow it (DNS validation is more reliable)
                return True, '', metadata
            
            # Connect to SMTP server
            try:
                with smtplib.SMTP(timeout=config.SMTP_TIMEOUT) as smtp:
                    smtp.connect(mx_host)
                    smtp.helo(socket.getfqdn())
                    smtp.mail(config.SMTP_FROM_EMAIL)
                    
                    # Test actual email
                    code, message = smtp.rcpt(email)
                    
                    if code == 250:
                        metadata['smtp_valid'] = True
                        
                        # Test catch-all with random email (informational only, don't reject)
                        try:
                            random_email = f'random{datetime.now().timestamp()}@{domain}'
                            code_random, _ = smtp.rcpt(random_email)
                            
                            if code_random == 250:
                                metadata['is_catch_all'] = True
                                # Don't reject catch-all domains - many legitimate domains use catch-all
                                logger.debug(f"Catch-all domain detected for {domain}")
                        except Exception:
                            pass  # Ignore catch-all test errors
                        
                        return True, '', metadata
                    else:
                        # SMTP rejected, but this is often unreliable (anti-harvesting measures)
                        # If DNS validation passed, we'll still allow it
                        logger.debug(f"SMTP rejected {email}: {message.decode() if isinstance(message, bytes) else message}")
                        # Don't reject - SMTP verification is unreliable
                        return True, '', metadata
            except (socket.timeout, smtplib.SMTPServerDisconnected, ConnectionRefusedError):
                # Timeout or connection issues are not necessarily invalid
                logger.debug(f"SMTP connection issue for {email}")
                return True, '', metadata
            except Exception as smtp_error:
                logger.debug(f"SMTP validation error for {email}: {smtp_error}")
                # Don't reject on SMTP errors, they're often false positives
                return True, '', metadata
            
        except Exception as e:
            logger.debug(f"SMTP validation error for {email}: {e}")
            # Don't reject on SMTP errors, they're often false positives
            # If DNS validation passed, we trust that more than SMTP
            return True, '', metadata
    
    def check_domain_age(self, email: str) -> Tuple[bool, str, dict]:
        """
        Check domain age via WHOIS
        
        Args:
            email: Email address
        
        Returns:
            Tuple of (is_valid, rejection_reason, metadata)
        """
        domain = extract_domain(email)
        metadata = {'domain_age_days': None}
        
        try:
            w = whois.whois(domain)
            
            # Get creation date
            creation_date = w.creation_date
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            
            if creation_date:
                age = datetime.now() - creation_date
                metadata['domain_age_days'] = age.days
                
                if age.days < config.MIN_DOMAIN_AGE_DAYS:
                    return False, f'Domain too new: {age.days} days', metadata
            
            return True, '', metadata
            
        except Exception as e:
            logger.debug(f"WHOIS lookup error for {domain}: {e}")
            # Don't reject on WHOIS errors
            return True, '', metadata
    
    def check_ssl(self, email: str) -> Tuple[bool, str, dict]:
        """
        Check if domain has valid SSL certificate
        
        Args:
            email: Email address
        
        Returns:
            Tuple of (is_valid, rejection_reason, metadata)
        """
        domain = extract_domain(email)
        metadata = {'has_ssl': False}
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    if cert:
                        metadata['has_ssl'] = True
            
            return True, '', metadata
            
        except Exception as e:
            logger.debug(f"SSL check error for {domain}: {e}")
            # SSL is informational only
            return True, '', metadata
