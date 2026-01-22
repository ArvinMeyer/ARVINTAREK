"""
Validation pipeline orchestrator
"""
from datetime import datetime
from validator.validator import EmailValidator
from utils.db import get_db_session, EmailRaw, EmailValid, EmailInvalid
from utils.helpers import extract_domain
from utils.logger import get_logger

logger = get_logger(__name__)

class ValidationPipeline:
    """Orchestrates email validation process"""
    
    def __init__(self):
        """Initialize validation pipeline"""
        self.validator = EmailValidator()
    
    def validate_email(self, email_raw_id: int) -> bool:
        """
        Validate a single email from database
        
        Args:
            email_raw_id: ID of EmailRaw record
        
        Returns:
            True if valid, False if invalid
        """
        db = get_db_session()
        
        try:
            # Get raw email
            email_raw = db.query(EmailRaw).filter_by(id=email_raw_id).first()
            
            if not email_raw:
                logger.error(f"EmailRaw {email_raw_id} not found")
                return False
            
            if email_raw.validated:
                logger.debug(f"Email {email_raw.email} already validated")
                return False
            
            # Validate
            is_valid, reason, stage, metadata = self.validator.validate(email_raw.email)
            
            if is_valid:
                # Create valid email record
                email_valid = EmailValid(
                    raw_email_id=email_raw.id,
                    email=email_raw.email,
                    domain=extract_domain(email_raw.email),
                    has_mx_record=metadata.get('has_mx_record', False),
                    has_a_record=metadata.get('has_a_record', False),
                    smtp_valid=metadata.get('smtp_valid', False),
                    is_catch_all=metadata.get('is_catch_all', False),
                    domain_age_days=metadata.get('domain_age_days'),
                    has_ssl=metadata.get('has_ssl')
                )
                db.add(email_valid)
                logger.info(f"✓ Valid: {email_raw.email}")
            else:
                # Create invalid email record
                email_invalid = EmailInvalid(
                    raw_email_id=email_raw.id,
                    email=email_raw.email,
                    rejection_reason=reason,
                    rejection_stage=stage
                )
                db.add(email_invalid)
                logger.info(f"✗ Invalid: {email_raw.email} - {reason}")
            
            # Mark as validated
            email_raw.validated = True
            
            db.commit()
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating email {email_raw_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def validate_all_pending(self, limit: int = None) -> dict:
        """
        Validate all pending emails
        
        Args:
            limit: Maximum number to validate (None for all)
        
        Returns:
            Dictionary with validation statistics
        """
        db = get_db_session()
        stats = {'total': 0, 'valid': 0, 'invalid': 0}
        
        try:
            # Get pending emails
            query = db.query(EmailRaw).filter_by(validated=False)
            
            if limit:
                query = query.limit(limit)
            
            pending_emails = query.all()
            stats['total'] = len(pending_emails)
            
            logger.info(f"Validating {stats['total']} pending emails...")
            
            for email_raw in pending_emails:
                is_valid = self.validate_email(email_raw.id)
                
                if is_valid:
                    stats['valid'] += 1
                else:
                    stats['invalid'] += 1
            
            logger.info(f"Validation complete: {stats['valid']} valid, {stats['invalid']} invalid")
            
        except Exception as e:
            logger.error(f"Error in batch validation: {e}")
        finally:
            db.close()
        
        return stats
    
    def validate_by_scan_job(self, scan_job_id: int) -> dict:
        """
        Validate all emails from a specific scan job
        
        Args:
            scan_job_id: Scan job ID
        
        Returns:
            Dictionary with validation statistics
        """
        db = get_db_session()
        stats = {'total': 0, 'valid': 0, 'invalid': 0}
        
        try:
            # Get emails from scan job
            emails = db.query(EmailRaw).filter_by(
                scan_job_id=scan_job_id,
                validated=False
            ).all()
            
            stats['total'] = len(emails)
            
            logger.info(f"Validating {stats['total']} emails from scan job {scan_job_id}...")
            
            for email_raw in emails:
                is_valid = self.validate_email(email_raw.id)
                
                if is_valid:
                    stats['valid'] += 1
                else:
                    stats['invalid'] += 1
            
            logger.info(f"Validation complete: {stats['valid']} valid, {stats['invalid']} invalid")
            
        except Exception as e:
            logger.error(f"Error validating scan job emails: {e}")
        finally:
            db.close()
        
        return stats
