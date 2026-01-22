"""
Flask web dashboard for Email Extraction System
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
import csv
import io
from datetime import datetime
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.db import init_db, get_db_session, ScanJob, ScanResult, EmailRaw, EmailValid, EmailInvalid, SendReport, GoogleSearchHistory, SMTPConfig, EmailAccount, DeliveryRecord
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from utils.helpers import export_to_csv, calculate_percentage, format_datetime
from scraper.scanner import Scanner
from scraper.google_search import extract_urls_from_google
from validator.pipeline import ValidationPipeline
from validator.validator import EmailValidator
from emailer.sender import EmailSender
from utils.logger import get_logger
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
logger = get_logger(__name__)

# Context processor to make SMTP configs and email accounts available in all templates
@app.context_processor
def inject_smtp_settings():
    """Make SMTP configurations and email accounts available in all templates"""
    try:
        db = get_db_session()
        try:
            smtp_configs = db.query(SMTPConfig).filter_by(is_active=True).order_by(SMTPConfig.name).all()
            email_accounts = db.query(EmailAccount).filter_by(is_active=True).order_by(EmailAccount.name).all()
            return {
                'smtp_configs': smtp_configs,
                'email_accounts': email_accounts,
                'smtp_configs_count': len(smtp_configs),
                'email_accounts_count': len(email_accounts)
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in context processor: {e}")
        return {
            'smtp_configs': [],
            'email_accounts': [],
            'smtp_configs_count': 0,
            'email_accounts_count': 0
        }

# Global scanner instances
active_scanners = {}

# Validation job tracking
validation_jobs = {}
validation_lock = threading.Lock()  # Lock for thread-safe job updates

def validate_email_parallel(email_data, job_id):
    """
    Validate a single email in parallel (called by ThreadPoolExecutor)
    
    Args:
        email_data: Tuple of (email_raw_id, email_address) or (email_invalid_id, email_address, raw_email_id)
        job_id: Job ID for status updates
    
    Returns:
        Tuple of (success, result_dict)
    """
    from utils.helpers import extract_domain
    from sqlalchemy import func
    
    try:
        # Get job (with lock for thread safety)
        with validation_lock:
            if job_id not in validation_jobs:
                return False, {'error': 'Job not found'}
            job = validation_jobs[job_id]
        
        # Create validator and database session for this thread
        validator = EmailValidator()
        db = get_db_session()
        
        try:
            # Determine if this is a revalidation or new validation
            if len(email_data) == 3:
                # Revalidation: (email_invalid_id, email_address, raw_email_id)
                email_invalid_id, email_addr, raw_email_id = email_data
                
                # Delete old invalid record
                email_invalid = db.query(EmailInvalid).filter_by(id=email_invalid_id).first()
                if email_invalid:
                    db.delete(email_invalid)
                
                # Get raw email
                raw_email = db.query(EmailRaw).filter_by(id=raw_email_id).first()
                if not raw_email:
                    return False, {'error': 'Raw email not found', 'email': email_addr}
                
                # Reset validation status
                raw_email.validated = False
                db.commit()
                
                # Validate
                is_valid, reason, stage, metadata = validator.validate(email_addr)
                
                if is_valid:
                    email_valid = EmailValid(
                        raw_email_id=raw_email.id,
                        email=email_addr,
                        domain=extract_domain(email_addr),
                        has_mx_record=metadata.get('has_mx_record', False),
                        has_a_record=metadata.get('has_a_record', False),
                        smtp_valid=metadata.get('smtp_valid', False),
                        is_catch_all=metadata.get('is_catch_all', False),
                        domain_age_days=metadata.get('domain_age_days'),
                        has_ssl=metadata.get('has_ssl')
                    )
                    db.add(email_valid)
                    result = {'valid': True, 'email': email_addr}
                else:
                    email_invalid_new = EmailInvalid(
                        raw_email_id=raw_email.id,
                        email=email_addr,
                        rejection_reason=reason,
                        rejection_stage=stage
                    )
                    db.add(email_invalid_new)
                    result = {'valid': False, 'email': email_addr, 'reason': reason}
                
                raw_email.validated = True
                db.commit()
                
            else:
                # New validation: (email_raw_id, email_address)
                email_raw_id, email_addr = email_data
                
                # Check if already validated
                already_valid = db.query(EmailValid).filter(
                    func.lower(EmailValid.email) == email_addr.lower()
                ).first()
                already_invalid = db.query(EmailInvalid).filter(
                    func.lower(EmailInvalid.email) == email_addr.lower()
                ).first()
                
                if already_valid or already_invalid:
                    # Mark as validated
                    email_raw = db.query(EmailRaw).filter_by(id=email_raw_id).first()
                    if email_raw:
                        email_raw.validated = True
                        db.commit()
                    return True, {'already_validated': True, 'email': email_addr}
                
                # Get raw email
                email_raw = db.query(EmailRaw).filter_by(id=email_raw_id).first()
                if not email_raw:
                    return False, {'error': 'EmailRaw not found', 'email': email_addr}
                
                if email_raw.validated:
                    return True, {'already_validated': True, 'email': email_addr}
                
                # Validate
                is_valid, reason, stage, metadata = validator.validate(email_addr)
                
                if is_valid:
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
                    result = {'valid': True, 'email': email_addr}
                else:
                    email_invalid = EmailInvalid(
                        raw_email_id=email_raw.id,
                        email=email_raw.email,
                        rejection_reason=reason,
                        rejection_stage=stage
                    )
                    db.add(email_invalid)
                    result = {'valid': False, 'email': email_addr, 'reason': reason}
                
                email_raw.validated = True
                db.commit()
            
            return True, result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error validating email {email_data}: {e}")
        return False, {'error': str(e), 'email': email_data[1] if len(email_data) > 1 else 'unknown'}

@app.route('/')
def index():
    """Dashboard home page"""
    db = get_db_session()
    
    try:
        # Get statistics
        total_pages = db.query(ScanResult).filter_by(status='success').count()
        total_emails_raw = db.query(EmailRaw).count()
        total_valid = db.query(EmailValid).count()
        total_invalid = db.query(EmailInvalid).count()
        
        # Get recent scan jobs
        recent_jobs = db.query(ScanJob).order_by(ScanJob.created_at.desc()).limit(5).all()
        
        # Get recent validations
        recent_valid = db.query(EmailValid).order_by(EmailValid.validated_at.desc()).limit(10).all()
        
        stats = {
            'total_pages': total_pages,
            'total_emails': total_emails_raw,
            'valid_emails': total_valid,
            'invalid_emails': total_invalid,
            'success_rate': calculate_percentage(total_valid, total_emails_raw) if total_emails_raw > 0 else 0
        }
        
        return render_template('dashboard.html', stats=stats, recent_jobs=recent_jobs, recent_valid=recent_valid)
        
    finally:
        db.close()

@app.route('/scan/new', methods=['GET', 'POST'])
def new_scan():
    """Create new scan job"""
    if request.method == 'POST':
        db = get_db_session()
        
        try:
            # Get form data
            name = request.form.get('name')
            urls_text = request.form.get('urls', '')
            threads = int(request.form.get('threads', config.SCRAPER_THREADS))
            max_depth = int(request.form.get('max_depth', config.SCRAPER_MAX_DEPTH))
            
            # Parse URLs
            urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
            
            if not urls:
                flash('Please provide at least one URL', 'error')
                return redirect(url_for('new_scan'))
            
            # Create scan job
            scan_job = ScanJob(
                name=name or f'Scan {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                urls=json.dumps(urls),
                threads=threads,
                max_depth=max_depth,
                status='pending'
            )
            db.add(scan_job)
            db.commit()
            
            flash(f'Scan job created: {scan_job.name}', 'success')
            return redirect(url_for('scan_detail', scan_id=scan_job.id))
            
        finally:
            db.close()
    
    return render_template('scan_new.html')

@app.route('/scan/<int:scan_id>')
def scan_detail(scan_id):
    """View scan job details"""
    db = get_db_session()
    
    try:
        scan_job = db.query(ScanJob).filter_by(id=scan_id).first()
        
        if not scan_job:
            flash('Scan job not found', 'error')
            return redirect(url_for('index'))
        
        # Get scan results
        results = db.query(ScanResult).filter_by(scan_job_id=scan_id).all()
        
        # Parse URLs for total count with error handling
        try:
            urls = json.loads(scan_job.urls) if scan_job.urls else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing URLs JSON for scan {scan_id}: {e}")
            urls = []
        
        return render_template('scan_detail.html', scan_job=scan_job, results=results, urls=urls)
        
    finally:
        db.close()

@app.route('/api/scan/<int:scan_id>/status')
def scan_status_api(scan_id):
    """API endpoint for live scan status updates"""
    db = get_db_session()
    
    try:
        scan_job = db.query(ScanJob).filter_by(id=scan_id).first()
        
        if not scan_job:
            return jsonify({'error': 'Scan job not found'}), 404
        
        # Get result count
        result_count = db.query(ScanResult).filter_by(scan_job_id=scan_id).count()
        
        # Parse URLs for total count with error handling
        try:
            urls = json.loads(scan_job.urls) if scan_job.urls else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing URLs JSON for scan {scan_id}: {e}")
            urls = []
        
        return jsonify({
            'status': scan_job.status,
            'total_pages': scan_job.total_pages or 0,
            'total_emails': scan_job.total_emails or 0,
            'total_urls': len(urls),
            'result_count': result_count
        })
        
    except Exception as e:
        logger.error(f"Error in scan_status_api for scan {scan_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/scan/<int:scan_id>/start', methods=['GET', 'POST'])
def start_scan(scan_id):
    """Start scanning"""
    # If GET request, redirect to scan detail page
    if request.method == 'GET':
        return redirect(url_for('scan_detail', scan_id=scan_id))
    
    db = get_db_session()
    
    try:
        scan_job = db.query(ScanJob).filter_by(id=scan_id).first()
        
        if not scan_job:
            if request.is_json:
                return jsonify({'error': 'Scan job not found'}), 404
            flash('Scan job not found', 'error')
            return redirect(url_for('index'))
        
        if scan_job.status == 'running':
            if request.is_json:
                return jsonify({'error': 'Scan already running'}), 400
            flash('Scan is already running', 'info')
            return redirect(url_for('scan_detail', scan_id=scan_id))
        
        # Parse URLs with error handling
        try:
            urls = json.loads(scan_job.urls) if scan_job.urls else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing URLs JSON for scan {scan_id}: {e}")
            if request.is_json:
                return jsonify({'error': f'Invalid URLs data: {str(e)}'}), 400
            flash(f'Invalid URLs data: {str(e)}', 'error')
            return redirect(url_for('scan_detail', scan_id=scan_id))
        
        if not urls:
            if request.is_json:
                return jsonify({'error': 'No URLs to scan'}), 400
            flash('No URLs to scan', 'error')
            return redirect(url_for('scan_detail', scan_id=scan_id))
        
        # Store threads value before creating thread (to avoid scope issues)
        num_threads = scan_job.threads
        
        # Create and start scanner in background thread
        scanner = Scanner(scan_id)
        active_scanners[scan_id] = scanner
        
        def run_scanner():
            db_session = get_db_session()
            try:
                scanner.start(urls, num_threads)
                scanner.wait()
            except Exception as e:
                logger.error(f"Error in scanner thread for scan {scan_id}: {e}", exc_info=True)
                # Update scan job status to failed
                try:
                    failed_scan_job = db_session.query(ScanJob).filter_by(id=scan_id).first()
                    if failed_scan_job:
                        failed_scan_job.status = 'failed'
                        failed_scan_job.error_message = str(e)
                        db_session.commit()
                except Exception as db_error:
                    logger.error(f"Error updating scan status: {db_error}")
            finally:
                if scan_id in active_scanners:
                    del active_scanners[scan_id]
                db_session.close()
        
        thread = threading.Thread(target=run_scanner, daemon=True)
        thread.start()
        
        # If request is JSON (AJAX), return JSON response
        if request.is_json:
            return jsonify({'message': 'Scan started', 'status': 'running'})
        
        # Otherwise redirect to scan detail page (form submission)
        flash('Scan started successfully!', 'success')
        return redirect(url_for('scan_detail', scan_id=scan_id))
        
    finally:
        db.close()

@app.route('/scan/<int:scan_id>/stop', methods=['POST'])
def stop_scan(scan_id):
    """Stop scanning"""
    if scan_id in active_scanners:
        active_scanners[scan_id].stop()
        del active_scanners[scan_id]
        return jsonify({'message': 'Scan stopped', 'status': 'stopped'})
    
    return jsonify({'error': 'No active scan found'}), 404

@app.route('/emails/valid')
def valid_emails():
    """View valid emails"""
    db = get_db_session()
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Get all valid emails, ordered by most recently validated
        query = db.query(EmailValid).order_by(EmailValid.validated_at.desc())
        total = query.count()
        emails = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Get statistics
        total_valid = db.query(EmailValid).count()
        with_mx = db.query(EmailValid).filter_by(has_mx_record=True).count()
        with_smtp = db.query(EmailValid).filter_by(smtp_valid=True).count()
        
        stats = {
            'total': total_valid,
            'with_mx': with_mx,
            'with_smtp': with_smtp,
            'mx_rate': calculate_percentage(with_mx, total_valid) if total_valid > 0 else 0,
            'smtp_rate': calculate_percentage(with_smtp, total_valid) if total_valid > 0 else 0
        }
        
        # Get SMTP configs and Email accounts for selection
        smtp_configs = db.query(SMTPConfig).filter_by(is_active=True).all()
        email_accounts = db.query(EmailAccount).filter_by(is_active=True).all()
        
        # Check if coming from campaign creation
        return_to = request.args.get('return_to')
        select_mode = request.args.get('select_mode') == 'true'
        
        return render_template('emails_valid.html', emails=emails, page=page, 
                             total=total, per_page=per_page, stats=stats,
                             smtp_configs=smtp_configs, email_accounts=email_accounts,
                             return_to=return_to, select_mode=select_mode)
        
    except Exception as e:
        logger.error(f"Error loading valid emails: {e}", exc_info=True)
        flash(f'Error loading valid emails: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        db.close()

@app.route('/emails/valid/resubscribe', methods=['POST'])
def resubscribe_emails():
    """Re-subscribe unsubscribed emails"""
    db = get_db_session()
    
    try:
        data = request.get_json()
        emails = data.get('emails', [])
        email_ids = data.get('email_ids', [])
        
        if not emails and not email_ids:
            return jsonify({'success': False, 'error': 'No emails provided'}), 400
        
        from sqlalchemy import func
        
        count = 0
        for email_addr in emails:
            # Find email by address (case-insensitive)
            email_valid = db.query(EmailValid).filter(
                func.lower(EmailValid.email) == email_addr.lower()
            ).first()
            
            if email_valid and not email_valid.subscribed:
                email_valid.subscribed = True
                email_valid.unsubscribed_at = None
                count += 1
                logger.info(f"Re-subscribed: {email_addr}")
        
        # Also handle by IDs if provided
        if email_ids:
            for email_id in email_ids:
                email_valid = db.query(EmailValid).filter_by(id=email_id).first()
                if email_valid and not email_valid.subscribed:
                    email_valid.subscribed = True
                    email_valid.unsubscribed_at = None
                    if email_valid.email not in emails:  # Don't double count
                        count += 1
                    logger.info(f"Re-subscribed by ID: {email_valid.email}")
        
        db.commit()
        
        return jsonify({
            'success': True,
            'count': count,
            'message': f'Successfully re-subscribed {count} email(s)'
        })
        
    except Exception as e:
        logger.error(f"Error re-subscribing emails: {e}", exc_info=True)
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/emails/invalid')
def invalid_emails():
    """View invalid emails"""
    db = get_db_session()
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        query = db.query(EmailInvalid).order_by(EmailInvalid.validated_at.desc())
        total = query.count()
        emails = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return render_template('emails_invalid.html', emails=emails, page=page,
                             total=total, per_page=per_page)
        
    finally:
        db.close()

@app.route('/emails/export')
def export_emails():
    """Export emails to CSV"""
    db = get_db_session()
    export_type = request.args.get('type', 'valid')  # valid, all, invalid
    
    try:
        data = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_type == 'valid':
            emails = db.query(EmailValid).all()
            for email in emails:
                data.append({
                    'email': email.email,
                    'domain': email.domain,
                    'has_mx_record': email.has_mx_record,
                    'has_a_record': email.has_a_record,
                    'smtp_valid': email.smtp_valid,
                    'is_catch_all': email.is_catch_all,
                    'domain_age_days': email.domain_age_days,
                    'subscribed': email.subscribed,
                    'validated_at': format_datetime(email.validated_at)
                })
            filename = f'valid_emails_{timestamp}.csv'
            
        elif export_type == 'invalid':
            emails = db.query(EmailInvalid).all()
            for email in emails:
                data.append({
                    'email': email.email,
                    'domain': email.domain,
                    'rejection_stage': email.rejection_stage,
                    'rejection_reason': email.rejection_reason,
                    'validated_at': format_datetime(email.validated_at)
                })
            filename = f'invalid_emails_{timestamp}.csv'
            
        else:  # all
            # Get all emails from EmailRaw
            emails = db.query(EmailRaw).all()
            seen_emails = set()
            for email in emails:
                email_lower = email.email.lower()
                if email_lower not in seen_emails:
                    seen_emails.add(email_lower)
                    # Check validation status
                    valid_email = db.query(EmailValid).filter_by(email=email_lower).first()
                    invalid_email = db.query(EmailInvalid).filter_by(email=email_lower).first()
                    
                    status = 'unvalidated'
                    if valid_email:
                        status = 'valid'
                    elif invalid_email:
                        status = 'invalid'
                    
                    data.append({
                        'email': email.email,
                        'source_url': email.source_url,
                        'context': email.context,
                        'status': status,
                        'extracted_at': format_datetime(email.extracted_at)
                    })
            filename = f'all_emails_{timestamp}.csv'
        
        if not data:
            flash('No emails to export', 'warning')
            return redirect(url_for('emails_manage'))
        
        # Export to CSV
        filepath = config.EXPORT_DIR / filename
        export_to_csv(data, str(filepath))
        
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    finally:
        db.close()

@app.route('/emails/manage')
def emails_manage():
    """Manage emails page - manual entry and import"""
    return render_template('emails_manage.html')

@app.route('/emails/manual/add', methods=['POST'])
def add_emails_manual():
    """Add emails manually"""
    db = get_db_session()
    
    try:
        emails_text = request.form.get('emails', '').strip()
        source_url = request.form.get('source_url', '').strip() or None
        validate_immediately = request.form.get('validate_immediately') == 'on'
        
        if not emails_text:
            flash('Please enter at least one email address', 'error')
            return redirect(url_for('emails_manage'))
        
        # Parse emails (support both newline and comma separated)
        from utils.helpers import extract_emails_from_text
        emails_set = extract_emails_from_text(emails_text)
        
        if not emails_set:
            flash('No valid email addresses found', 'error')
            return redirect(url_for('emails_manage'))
        
        # Create a dummy scan job for manually added emails
        scan_job = db.query(ScanJob).filter_by(name='Manual Entry').first()
        if not scan_job:
            scan_job = ScanJob(
                name='Manual Entry',
                status='completed',
                urls=json.dumps([source_url] if source_url else []),
                threads=1,
                max_depth=0
            )
            db.add(scan_job)
            db.commit()
        
        added_count = 0
        skipped_count = 0
        
        for email in emails_set:
            email_lower = email.lower()
            # Check if email already exists
            existing = db.query(EmailRaw).filter(func.lower(EmailRaw.email) == email_lower).first()
            if existing:
                skipped_count += 1
                continue
            
            # Add to EmailRaw
            email_raw = EmailRaw(
                scan_job_id=scan_job.id,
                email=email,
                source_url=source_url,
                context='Manually added',
                validated=False
            )
            db.add(email_raw)
            added_count += 1
        
        db.commit()
        
        flash(f'Successfully added {added_count} email(s). {skipped_count} duplicate(s) skipped.', 'success')
        
        # Validate if requested
        if validate_immediately and added_count > 0:
            flash('Starting validation...', 'info')
            # Trigger validation in background
            from validator.validator import EmailValidator
            validator = EmailValidator()
            
            def validate_emails():
                db_session = get_db_session()
                try:
                    # Get newly added emails
                    new_emails = db_session.query(EmailRaw).filter_by(
                        scan_job_id=scan_job.id,
                        validated=False
                    ).all()
                    
                    for email_raw in new_emails:
                        try:
                            result = validator.validate(email_raw.email)
                            if result['valid']:
                                # Create EmailValid
                                valid_email = EmailValid(
                                    email=email_raw.email.lower(),
                                    domain=result.get('domain', ''),
                                    has_mx_record=result.get('has_mx_record', False),
                                    has_a_record=result.get('has_a_record', False),
                                    smtp_valid=result.get('smtp_valid', False),
                                    is_catch_all=result.get('is_catch_all', False),
                                    domain_age_days=result.get('domain_age_days'),
                                    validated_at=datetime.utcnow(),
                                    subscribed=True
                                )
                                db_session.add(valid_email)
                            else:
                                # Create EmailInvalid
                                invalid_email = EmailInvalid(
                                    email=email_raw.email.lower(),
                                    domain=result.get('domain', ''),
                                    rejection_stage=result.get('rejection_stage', 'unknown'),
                                    rejection_reason=result.get('rejection_reason', 'Validation failed'),
                                    validated_at=datetime.utcnow()
                                )
                                db_session.add(invalid_email)
                            
                            email_raw.validated = True
                            db_session.commit()
                        except Exception as e:
                            logger.error(f"Error validating {email_raw.email}: {e}")
                            db_session.rollback()
                finally:
                    db_session.close()
            
            thread = threading.Thread(target=validate_emails, daemon=True)
            thread.start()
        
        return redirect(url_for('emails_manage'))
        
    except Exception as e:
        logger.error(f"Error adding emails manually: {e}", exc_info=True)
        flash(f'Error adding emails: {str(e)}', 'error')
        db.rollback()
        return redirect(url_for('emails_manage'))
    finally:
        db.close()

@app.route('/emails/import', methods=['POST'])
def import_emails_csv():
    """Import emails from CSV file"""
    db = get_db_session()
    
    try:
        if 'csv_file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('emails_manage'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('emails_manage'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file', 'error')
            return redirect(url_for('emails_manage'))
        
        source_url = request.form.get('source_url', '').strip() or None
        validate_immediately = request.form.get('validate_immediately') == 'on'
        
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        # Find email column (case-insensitive)
        email_column = None
        for col in csv_reader.fieldnames:
            if col.lower() == 'email':
                email_column = col
                break
        
        if not email_column:
            flash('CSV file must contain an "email" column', 'error')
            return redirect(url_for('emails_manage'))
        
        # Create a dummy scan job for imported emails
        scan_job = db.query(ScanJob).filter_by(name='CSV Import').first()
        if not scan_job:
            scan_job = ScanJob(
                name='CSV Import',
                status='completed',
                urls=json.dumps([source_url] if source_url else []),
                threads=1,
                max_depth=0
            )
            db.add(scan_job)
            db.commit()
        
        added_count = 0
        skipped_count = 0
        invalid_count = 0
        
        # Validate email format
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        for row in csv_reader:
            email = row[email_column].strip()
            if not email:
                continue
            
            # Basic email validation
            if not email_pattern.match(email):
                invalid_count += 1
                continue
            
            email_lower = email.lower()
            # Check if email already exists
            existing = db.query(EmailRaw).filter(func.lower(EmailRaw.email) == email_lower).first()
            if existing:
                skipped_count += 1
                continue
            
            # Get source URL from CSV if available, otherwise use form value
            csv_source_url = row.get('source_url', row.get('source', source_url))
            
            # Add to EmailRaw
            email_raw = EmailRaw(
                scan_job_id=scan_job.id,
                email=email,
                source_url=csv_source_url,
                context='Imported from CSV',
                validated=False
            )
            db.add(email_raw)
            added_count += 1
        
        db.commit()
        
        message = f'Successfully imported {added_count} email(s).'
        if skipped_count > 0:
            message += f' {skipped_count} duplicate(s) skipped.'
        if invalid_count > 0:
            message += f' {invalid_count} invalid email(s) skipped.'
        
        flash(message, 'success')
        
        # Validate if requested
        if validate_immediately and added_count > 0:
            flash('Starting validation...', 'info')
            # Trigger validation in background (same as manual entry)
            from validator.validator import EmailValidator
            validator = EmailValidator()
            
            def validate_emails():
                db_session = get_db_session()
                try:
                    new_emails = db_session.query(EmailRaw).filter_by(
                        scan_job_id=scan_job.id,
                        validated=False
                    ).all()
                    
                    for email_raw in new_emails:
                        try:
                            result = validator.validate(email_raw.email)
                            if result['valid']:
                                valid_email = EmailValid(
                                    email=email_raw.email.lower(),
                                    domain=result.get('domain', ''),
                                    has_mx_record=result.get('has_mx_record', False),
                                    has_a_record=result.get('has_a_record', False),
                                    smtp_valid=result.get('smtp_valid', False),
                                    is_catch_all=result.get('is_catch_all', False),
                                    domain_age_days=result.get('domain_age_days'),
                                    validated_at=datetime.utcnow(),
                                    subscribed=True
                                )
                                db_session.add(valid_email)
                            else:
                                invalid_email = EmailInvalid(
                                    email=email_raw.email.lower(),
                                    domain=result.get('domain', ''),
                                    rejection_stage=result.get('rejection_stage', 'unknown'),
                                    rejection_reason=result.get('rejection_reason', 'Validation failed'),
                                    validated_at=datetime.utcnow()
                                )
                                db_session.add(invalid_email)
                            
                            email_raw.validated = True
                            db_session.commit()
                        except Exception as e:
                            logger.error(f"Error validating {email_raw.email}: {e}")
                            db_session.rollback()
                finally:
                    db_session.close()
            
            thread = threading.Thread(target=validate_emails, daemon=True)
            thread.start()
        
        return redirect(url_for('emails_manage'))
        
    except Exception as e:
        logger.error(f"Error importing emails: {e}", exc_info=True)
        flash(f'Error importing emails: {str(e)}', 'error')
        db.rollback()
        return redirect(url_for('emails_manage'))
    finally:
        db.close()


@app.route('/emails/raw')
def emails_raw():
    """View all raw (unvalidated) emails"""
    db = get_db_session()
    
    try:
        # Get all raw emails that haven't been validated yet
        raw_emails = db.query(EmailRaw).filter_by(validated=False).order_by(EmailRaw.extracted_at.desc()).all()
        
        total_raw = len(raw_emails)
        
        return render_template('emails_raw.html', emails=raw_emails, total=total_raw)
        
    finally:
        db.close()

@app.route('/emails/all')
def emails_all():
    """View all extracted emails with validation status (unique emails only)"""
    db = get_db_session()
    
    try:
        # Handle potential errors gracefully
        page = request.args.get('page', 1, type=int)
        scan_id = request.args.get('scan_id', type=int)
        # Default to False (show all emails) - only filter if explicitly requested
        show_only_unvalidated = False
        if request.args.get('unvalidated_only'):
            show_only_unvalidated = request.args.get('unvalidated_only', 'false').lower() == 'true'
        per_page = 50
        
        # Get unique emails by grouping by email address (case-insensitive)
        from sqlalchemy import func, distinct
        
        # Base query for unique emails
        if scan_id:
            # Get distinct email addresses for this scan
            distinct_emails_query = db.query(
                func.lower(EmailRaw.email).label('email_lower'),
                func.max(EmailRaw.extracted_at).label('latest_extracted_at')
            ).filter_by(scan_job_id=scan_id).group_by(func.lower(EmailRaw.email))
        else:
            # Get distinct email addresses across all scans
            distinct_emails_query = db.query(
                func.lower(EmailRaw.email).label('email_lower'),
                func.max(EmailRaw.extracted_at).label('latest_extracted_at')
            ).group_by(func.lower(EmailRaw.email))
        
        # Get total count of unique emails
        total = distinct_emails_query.count()
        
        # Get all distinct emails and sort by latest extraction date in Python
        all_distinct_emails = distinct_emails_query.all()
        all_distinct_emails.sort(key=lambda x: x.latest_extracted_at, reverse=True)
        
        # Apply pagination
        distinct_emails = all_distinct_emails[(page - 1) * per_page:page * per_page]
        
        # If no results, return empty (show all emails - which is none)
        if not distinct_emails:
            emails_data = []
            stats = {
                'total': 0,
                'validated': 0,
                'not_validated': 0,
                'valid': 0,
                'invalid': 0
            }
            scan_job_name = None
            if scan_id:
                scan_job = db.query(ScanJob).filter_by(id=scan_id).first()
                if scan_job:
                    scan_job_name = scan_job.name
            return render_template('emails_all.html', 
                                 emails=emails_data, 
                                 page=page, 
                                 total=0, 
                                 per_page=per_page,
                                 stats=stats,
                                 scan_id=scan_id,
                                 scan_job_name=scan_job_name)
        
        # Get validation status for each unique email
        emails_data = []
        seen_emails = set()
        
        for distinct_item in distinct_emails:
            email_lower = distinct_item.email_lower
            latest_extracted_at = distinct_item.latest_extracted_at
            
            # Skip if we've already processed this email (case-insensitive)
            if email_lower in seen_emails:
                continue
            seen_emails.add(email_lower)
            
            # Get the most recent raw email record for this email address
            raw_email_query = db.query(EmailRaw).filter(
                func.lower(EmailRaw.email) == email_lower
            )
            if scan_id:
                raw_email_query = raw_email_query.filter_by(scan_job_id=scan_id)
            
            raw_email = raw_email_query.order_by(EmailRaw.extracted_at.desc()).first()
            
            if not raw_email:
                continue
            
            # Get all source URLs where this email was found
            all_raw_emails = db.query(EmailRaw).filter(
                func.lower(EmailRaw.email) == email_lower
            )
            if scan_id:
                all_raw_emails = all_raw_emails.filter_by(scan_job_id=scan_id)
            
            source_urls = [e.source_url for e in all_raw_emails.all() if e.source_url]
            source_urls = list(set(source_urls))  # Remove duplicate URLs
            
            # Check if email is validated and if it's valid or invalid
            # Check by email address (case-insensitive) since validation might be on any instance
            valid_email = db.query(EmailValid).filter(
                func.lower(EmailValid.email) == email_lower
            ).order_by(EmailValid.validated_at.desc()).first()
            
            invalid_email = db.query(EmailInvalid).filter(
                func.lower(EmailInvalid.email) == email_lower
            ).order_by(EmailInvalid.validated_at.desc()).first()
            
            validation_status = 'not_validated'
            validation_details = None
            
            if valid_email:
                validation_status = 'valid'
                validation_details = {
                    'has_mx_record': valid_email.has_mx_record or False,
                    'has_a_record': valid_email.has_a_record or False,
                    'smtp_valid': valid_email.smtp_valid or False,
                    'is_catch_all': valid_email.is_catch_all or False,
                    'validated_at': valid_email.validated_at
                }
            elif invalid_email:
                validation_status = 'invalid'
                validation_details = {
                    'rejection_stage': invalid_email.rejection_stage or 'unknown',
                    'rejection_reason': invalid_email.rejection_reason or 'No reason provided',
                    'validated_at': invalid_email.validated_at
                }
            
            # Filter out validated emails if requested
            if show_only_unvalidated and validation_status != 'not_validated':
                continue
            
            emails_data.append({
                'email': raw_email.email,  # Use original case from most recent extraction
                'source_urls': source_urls,
                'source_url': source_urls[0] if source_urls else None,  # Primary source URL
                'context': raw_email.context,
                'extracted_at': latest_extracted_at,
                'validation_status': validation_status,
                'validation_details': validation_details,
                'occurrence_count': all_raw_emails.count()  # How many times this email was found
            })
        
        # Get statistics (filtered by scan_id if provided)
        # Count unique emails
        if scan_id:
            unique_emails_query = db.query(func.lower(EmailRaw.email)).filter_by(scan_job_id=scan_id).distinct()
            total_emails = unique_emails_query.count()
            
            # Get unique email addresses
            unique_email_addresses = [e[0] for e in unique_emails_query.all()]
            
            # Count validated unique emails
            validated_unique = db.query(func.lower(EmailValid.email)).distinct().filter(
                func.lower(EmailValid.email).in_([e.lower() for e in unique_email_addresses])
            ).count() if unique_email_addresses else 0
            
            not_validated_count = total_emails - validated_unique
            
            # Count valid/invalid unique emails
            valid_count = db.query(func.lower(EmailValid.email)).distinct().filter(
                func.lower(EmailValid.email).in_([e.lower() for e in unique_email_addresses])
            ).count() if unique_email_addresses else 0
            
            invalid_count = db.query(func.lower(EmailInvalid.email)).distinct().filter(
                func.lower(EmailInvalid.email).in_([e.lower() for e in unique_email_addresses])
            ).count() if unique_email_addresses else 0
        else:
            # Count all unique emails
            total_emails = db.query(func.lower(EmailRaw.email)).distinct().count()
            
            # Count validated unique emails
            validated_unique = db.query(func.lower(EmailValid.email)).distinct().count()
            not_validated_count = total_emails - validated_unique
            
            # Count valid/invalid unique emails
            valid_count = db.query(func.lower(EmailValid.email)).distinct().count()
            invalid_count = db.query(func.lower(EmailInvalid.email)).distinct().count()
        
        stats = {
            'total': total_emails,
            'validated': validated_unique,
            'not_validated': not_validated_count,
            'valid': valid_count,
            'invalid': invalid_count
        }
        
        # Get scan job name if filtering by scan_id
        scan_job_name = None
        if scan_id:
            scan_job = db.query(ScanJob).filter_by(id=scan_id).first()
            if scan_job:
                scan_job_name = scan_job.name
        
        return render_template('emails_all.html', 
                             emails=emails_data, 
                             page=page, 
                             total=total, 
                             per_page=per_page,
                             stats=stats,
                             scan_id=scan_id,
                             scan_job_name=scan_job_name)
        
    except Exception as e:
        logger.error(f"Error in emails_all route: {e}", exc_info=True)
        flash(f'Error loading emails: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        db.close()

@app.route('/validate/pending', methods=['POST'])
def validate_pending():
    """Validate all pending emails with real-time progress"""
    limit = request.form.get('limit', type=int)
    
    # Create a unique job ID
    import uuid
    import time
    from datetime import datetime
    
    job_id = str(uuid.uuid4())
    
    # Initialize job state
    validation_jobs[job_id] = {
        'status': 'running',
        'progress': 0,
        'message': 'Initializing validation...',
        'current_email': None,
        'total': 0,
        'processed': 0,
        'valid': 0,
        'invalid': 0,
        'already_validated': 0,
        'start_time': time.time(),
        'activity': [],
        'error': None
    }
    
    # Run validation in background
    def run_validation():
        if job_id not in validation_jobs:
            logger.error(f"Job {job_id} not found when starting validation")
            return
        
        job = validation_jobs[job_id]
        db = get_db_session()
        pipeline = ValidationPipeline()
        
        try:
            # Get pending emails
            query = db.query(EmailRaw).filter_by(validated=False)
            
            if limit:
                query = query.limit(limit)
            
            pending_emails = query.all()
            total = len(pending_emails)
            job['total'] = total
            
            if total == 0:
                job['status'] = 'completed'
                job['progress'] = 100
                job['message'] = 'No pending emails to validate'
                job['activity'].append({'message': 'No pending emails found', 'type': 'info'})
                db.close()
                return
            
            job['activity'].append({'message': f'Found {total} pending emails to validate', 'type': 'info'})
            job['message'] = f'Validating {total} emails...'
            
            start_time = time.time()
            times = []  # Track validation times for ETA calculation
            
            # Prepare email data for parallel processing
            email_list = [(email_raw.id, email_raw.email) for email_raw in pending_emails]
            
            # Use ThreadPoolExecutor for parallel validation
            num_threads = config.VALIDATION_THREADS
            with validation_lock:
                job['message'] = f'Validating {total} emails using {num_threads} threads...'
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Submit all validation tasks
                future_to_email = {
                    executor.submit(validate_email_parallel, email_data, job_id): email_data 
                    for email_data in email_list
                }
                
                # Process completed validations
                completed = 0
                for future in as_completed(future_to_email):
                    completed += 1
                    email_data = future_to_email[future]
                    email_addr = email_data[1]
                    
                    # Update progress
                    with validation_lock:
                        job['current_email'] = email_addr
                        job['processed'] = completed
                        job['progress'] = int((completed / total) * 100)
                        job['message'] = f'Validating {completed}/{total} emails...'
                    
                    try:
                        success, result = future.result()
                        
                        if success:
                            if result.get('already_validated'):
                                with validation_lock:
                                    job['already_validated'] += 1
                                    job['activity'].append({
                                        'message': f'✓ {email_addr} (already validated)',
                                        'type': 'info'
                                    })
                            elif result.get('valid'):
                                with validation_lock:
                                    job['valid'] += 1
                                    job['activity'].append({
                                        'message': f'✓ Valid: {email_addr}',
                                        'type': 'success'
                                    })
                            else:
                                with validation_lock:
                                    job['invalid'] += 1
                                    reason = result.get('reason', 'Unknown')
                                    job['activity'].append({
                                        'message': f'✗ Invalid: {email_addr} - {reason[:50]}',
                                        'type': 'error'
                                    })
                        else:
                            with validation_lock:
                                job['invalid'] += 1
                                error = result.get('error', 'Validation failed')
                                job['activity'].append({
                                    'message': f'✗ Error: {email_addr} - {error}',
                                    'type': 'error'
                                })
                    except Exception as e:
                        logger.error(f"Error processing validation result: {e}")
                        with validation_lock:
                            job['invalid'] += 1
                            job['activity'].append({
                                'message': f'✗ Error: {email_addr} - {str(e)[:50]}',
                                'type': 'error'
                            })
                    
                    # Calculate ETA
                    elapsed = time.time() - start_time
                    if completed > 0:
                        avg_time = elapsed / completed
                        remaining = total - completed
                        eta_seconds = avg_time * remaining
                        eta_minutes = int(eta_seconds / 60)
                        eta_seconds = int(eta_seconds % 60)
                        
                        with validation_lock:
                            if eta_minutes > 0:
                                job['message'] = f'Validating {completed}/{total} (~{eta_minutes}m {eta_seconds}s remaining)'
                            else:
                                job['message'] = f'Validating {completed}/{total} (~{eta_seconds}s remaining)'
            
            # Mark as completed
            elapsed_time = time.time() - start_time
            job['status'] = 'completed'
            job['progress'] = 100
            job['current_email'] = None
            job['message'] = f'Validation complete! {job["valid"]} valid, {job["invalid"]} invalid in {int(elapsed_time)}s'
            job['activity'].append({
                'message': f'✓ Validation complete: {job["valid"]} valid, {job["invalid"]} invalid, {job["already_validated"]} already validated',
                'type': 'success'
            })
            
        except Exception as e:
            error_msg = str(e)
            job['status'] = 'failed'
            job['error'] = error_msg
            job['message'] = f'Error: {error_msg}'
            job['activity'].append({
                'message': f'✗ Fatal error: {error_msg}',
                'type': 'error'
            })
            logger.error(f"Validation job error: {e}", exc_info=True)
        finally:
            db.close()
    
    thread = threading.Thread(target=run_validation, daemon=True)
    thread.start()
    
    return jsonify({'job_id': job_id, 'message': 'Validation started'})

@app.route('/validate/invalid', methods=['POST'])
def validate_invalid_emails():
    """Re-validate all invalid emails with real-time progress"""
    limit = request.form.get('limit', type=int)
    
    # Create a unique job ID
    import uuid
    import time
    from datetime import datetime
    
    job_id = str(uuid.uuid4())
    
    # Initialize job state
    validation_jobs[job_id] = {
        'status': 'running',
        'progress': 0,
        'message': 'Initializing re-validation...',
        'current_email': None,
        'total': 0,
        'processed': 0,
        'valid': 0,
        'invalid': 0,
        'start_time': time.time(),
        'activity': [],
        'error': None
    }
    
    # Run validation in background
    def run_revalidation():
        if job_id not in validation_jobs:
            logger.error(f"Job {job_id} not found when starting revalidation")
            return
        
        job = validation_jobs[job_id]
        db = get_db_session()
        
        try:
            from validator.validator import EmailValidator
            from utils.helpers import extract_domain
            from sqlalchemy import func
            
            validator = EmailValidator()
            # Get invalid emails
            query = db.query(EmailInvalid)
            
            if limit:
                query = query.limit(limit)
            
            invalid_emails = query.all()
            total = len(invalid_emails)
            job['total'] = total
            
            if total == 0:
                job['status'] = 'completed'
                job['progress'] = 100
                job['message'] = 'No invalid emails to re-validate'
                job['activity'].append({'message': 'No invalid emails found', 'type': 'info'})
                db.close()
                return
            
            job['activity'].append({'message': f'Found {total} invalid emails to re-validate', 'type': 'info'})
            job['message'] = f'Re-validating {total} emails...'
            
            start_time = time.time()
            
            # Prepare email data for parallel processing
            email_list = [(email_invalid.id, email_invalid.email, email_invalid.raw_email_id) 
                         for email_invalid in invalid_emails]
            
            # Use ThreadPoolExecutor for parallel validation
            num_threads = config.VALIDATION_THREADS
            with validation_lock:
                job['message'] = f'Re-validating {total} emails using {num_threads} threads...'
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Submit all validation tasks
                future_to_email = {
                    executor.submit(validate_email_parallel, email_data, job_id): email_data 
                    for email_data in email_list
                }
                
                # Process completed validations
                completed = 0
                for future in as_completed(future_to_email):
                    completed += 1
                    email_data = future_to_email[future]
                    email_addr = email_data[1]
                    
                    # Update progress
                    with validation_lock:
                        job['current_email'] = email_addr
                        job['processed'] = completed
                        job['progress'] = int((completed / total) * 100)
                        job['message'] = f'Re-validating {completed}/{total} emails...'
                    
                    try:
                        success, result = future.result()
                        
                        if success:
                            if result.get('valid'):
                                with validation_lock:
                                    job['valid'] += 1
                                    job['activity'].append({
                                        'message': f'✓ Now Valid: {email_addr}',
                                        'type': 'success'
                                    })
                            else:
                                with validation_lock:
                                    job['invalid'] += 1
                                    reason = result.get('reason', 'Unknown')
                                    job['activity'].append({
                                        'message': f'✗ Still Invalid: {email_addr} - {reason[:50]}',
                                        'type': 'error'
                                    })
                        else:
                            with validation_lock:
                                job['invalid'] += 1
                                error = result.get('error', 'Validation failed')
                                if 'not found' in error.lower():
                                    job['activity'].append({
                                        'message': f'⚠ {email_addr} (raw email not found)',
                                        'type': 'error'
                                    })
                                else:
                                    job['activity'].append({
                                        'message': f'✗ Error: {email_addr} - {error}',
                                        'type': 'error'
                                    })
                    except Exception as e:
                        logger.error(f"Error processing revalidation result: {e}")
                        with validation_lock:
                            job['invalid'] += 1
                            job['activity'].append({
                                'message': f'✗ Error: {email_addr} - {str(e)[:50]}',
                                'type': 'error'
                            })
                    
                    # Calculate ETA
                    elapsed = time.time() - start_time
                    if completed > 0:
                        avg_time = elapsed / completed
                        remaining = total - completed
                        eta_seconds = avg_time * remaining
                        eta_minutes = int(eta_seconds / 60)
                        eta_seconds = int(eta_seconds % 60)
                        
                        with validation_lock:
                            if eta_minutes > 0:
                                job['message'] = f'Re-validating {completed}/{total} (~{eta_minutes}m {eta_seconds}s remaining)'
                            else:
                                job['message'] = f'Re-validating {completed}/{total} (~{eta_seconds}s remaining)'
            
            # Mark as completed
            elapsed_time = time.time() - start_time
            job['status'] = 'completed'
            job['progress'] = 100
            job['current_email'] = None
            job['message'] = f'Re-validation complete! {job["valid"]} now valid, {job["invalid"]} still invalid in {int(elapsed_time)}s'
            job['activity'].append({
                'message': f'✓ Re-validation complete: {job["valid"]} now valid, {job["invalid"]} still invalid',
                'type': 'success'
            })
            
        except Exception as e:
            error_msg = str(e)
            job['status'] = 'failed'
            job['error'] = error_msg
            job['message'] = f'Error: {error_msg}'
            job['activity'].append({
                'message': f'✗ Fatal error: {error_msg}',
                'type': 'error'
            })
            logger.error(f"Re-validation job error: {e}", exc_info=True)
        finally:
            db.close()
    
    thread = threading.Thread(target=run_revalidation, daemon=True)
    thread.start()
    
    return jsonify({'job_id': job_id, 'message': 'Re-validation started'})

@app.route('/validate/status/<job_id>')
def validate_status(job_id):
    """Get status of a validation job"""
    if job_id not in validation_jobs:
        # Job might have been cleared or server restarted
        logger.warning(f"Validation job {job_id} not found in validation_jobs")
        return jsonify({
            'error': 'Job not found. The server may have restarted or the job was cleared.',
            'status': 'not_found'
        }), 404
    
    job = validation_jobs[job_id]
    
    # Calculate elapsed time
    elapsed_time = 0
    if 'start_time' in job:
        import time
        elapsed_time = int(time.time() - job['start_time'])
    
    # Return only the last 20 activity items to avoid sending too much data
    activity = job['activity'][-20:] if len(job['activity']) > 20 else job['activity']
    
    return jsonify({
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'current_email': job.get('current_email'),
        'total': job['total'],
        'processed': job['processed'],
        'valid': job['valid'],
        'invalid': job['invalid'],
        'already_validated': job.get('already_validated', 0),
        'activity': activity,
        'error': job.get('error'),
        'elapsed_time': elapsed_time
    })

@app.route('/emails/all/validate-selected', methods=['POST'])
def validate_selected_emails():
    """Validate selected emails by email address"""
    db = get_db_session()
    
    try:
        data = request.get_json()
        emails = data.get('emails', [])
        
        if not emails:
            return jsonify({'success': False, 'error': 'No emails provided'}), 400
        
        from sqlalchemy import func
        from validator.pipeline import ValidationPipeline
        from validator.validator import EmailValidator
        from utils.helpers import extract_domain
        
        pipeline = ValidationPipeline()
        validator = EmailValidator()
        stats = {'valid': 0, 'invalid': 0, 'already_validated': 0, 'not_found': 0}
        
        # Process each email
        for email_addr in emails:
            email_lower = email_addr.lower()
            
            # Check if already validated (check both valid and invalid tables)
            already_valid = db.query(EmailValid).filter(
                func.lower(EmailValid.email) == email_lower
            ).first()
            
            already_invalid = db.query(EmailInvalid).filter(
                func.lower(EmailInvalid.email) == email_lower
            ).first()
            
            if already_valid or already_invalid:
                stats['already_validated'] += 1
                # Mark all raw emails as validated
                raw_emails = db.query(EmailRaw).filter(
                    func.lower(EmailRaw.email) == email_lower
                ).all()
                for raw_email in raw_emails:
                    if not raw_email.validated:
                        raw_email.validated = True
                db.commit()
                continue
            
            # Find all raw email records for this email (case-insensitive)
            raw_emails = db.query(EmailRaw).filter(
                func.lower(EmailRaw.email) == email_lower
            ).all()
            
            if not raw_emails:
                stats['not_found'] += 1
                continue
            
            # Find the first unvalidated raw email record
            unvalidated_raw = None
            for raw_email in raw_emails:
                if not raw_email.validated:
                    unvalidated_raw = raw_email
                    break
            
            if not unvalidated_raw:
                stats['already_validated'] += 1
                continue
            
            # Validate the email using the validator directly
            is_valid, reason, stage, metadata = validator.validate(unvalidated_raw.email)
            
            if is_valid:
                # Check if EmailValid already exists (shouldn't, but just in case)
                existing_valid = db.query(EmailValid).filter(
                    func.lower(EmailValid.email) == email_lower
                ).first()
                
                if not existing_valid:
                    # Create valid email record
                    email_valid = EmailValid(
                        raw_email_id=unvalidated_raw.id,
                        email=unvalidated_raw.email,  # Use original case
                        domain=extract_domain(unvalidated_raw.email),
                        has_mx_record=metadata.get('has_mx_record', False),
                        has_a_record=metadata.get('has_a_record', False),
                        smtp_valid=metadata.get('smtp_valid', False),
                        is_catch_all=metadata.get('is_catch_all', False),
                        domain_age_days=metadata.get('domain_age_days'),
                        has_ssl=metadata.get('has_ssl')
                    )
                    db.add(email_valid)
                    logger.info(f"✓ Valid: {unvalidated_raw.email}")
                
                stats['valid'] += 1
            else:
                # Check if EmailInvalid already exists
                existing_invalid = db.query(EmailInvalid).filter(
                    func.lower(EmailInvalid.email) == email_lower
                ).first()
                
                if not existing_invalid:
                    # Create invalid email record
                    email_invalid = EmailInvalid(
                        raw_email_id=unvalidated_raw.id,
                        email=unvalidated_raw.email,  # Use original case
                        rejection_reason=reason,
                        rejection_stage=stage
                    )
                    db.add(email_invalid)
                    logger.info(f"✗ Invalid: {unvalidated_raw.email} - {reason}")
                
                stats['invalid'] += 1
            
            # Mark all raw email instances as validated
            for raw_email in raw_emails:
                if not raw_email.validated:
                    raw_email.validated = True
            
            db.commit()
        
        return jsonify({
            'success': True,
            'valid': stats['valid'],
            'invalid': stats['invalid'],
            'already_validated': stats['already_validated'],
            'not_found': stats['not_found']
        })
        
    except Exception as e:
        logger.error(f"Error validating selected emails: {e}", exc_info=True)
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/campaigns')
def campaigns_page():
    """Professional campaign management page"""
    db = get_db_session()
    
    try:
        # Get all campaigns with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Use joinedload to eagerly load relationships
        query = db.query(SendReport).options(
            joinedload(SendReport.smtp_config),
            joinedload(SendReport.email_account)
        ).order_by(SendReport.created_at.desc())
        total = query.count()
        campaigns = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Get statistics
        total_campaigns = db.query(SendReport).count()
        completed_campaigns = db.query(SendReport).filter_by(status='completed').count()
        running_campaigns = db.query(SendReport).filter_by(status='running').count()
        total_sent = db.query(func.sum(SendReport.sent_count)).scalar() or 0
        
        # Get SMTP configs and Email accounts
        smtp_configs = db.query(SMTPConfig).filter_by(is_active=True).all()
        email_accounts = db.query(EmailAccount).filter_by(is_active=True).all()
        
        # Get count of valid emails (subscribed only)
        valid_count = db.query(EmailValid).filter_by(subscribed=True).count()
        
        stats = {
            'total_campaigns': total_campaigns,
            'completed': completed_campaigns,
            'running': running_campaigns,
            'total_sent': total_sent,
            'valid_recipients': valid_count
        }
        
        return render_template('campaigns.html', campaigns=campaigns, page=page, 
                             total=total, per_page=per_page, stats=stats,
                             smtp_configs=smtp_configs, email_accounts=email_accounts)
        
    except Exception as e:
        logger.error(f"Error loading campaigns page: {e}", exc_info=True)
        flash(f'Error loading campaigns: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        db.close()

@app.route('/api/campaigns/<int:campaign_id>/status')
def campaign_status_api(campaign_id):
    """API endpoint for real-time campaign status"""
    db = get_db_session()
    
    try:
        campaign = db.query(SendReport).filter_by(id=campaign_id).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get delivery records for accurate counting
        total_deliveries = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id).count()
        sent_deliveries = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id, status='sent').count()
        failed_deliveries = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id, status='failed').count()
        delivered_deliveries = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id, status='delivered').count()
        
        # Get latest delivery record (most recently sent or in progress)
        latest_delivery = db.query(DeliveryRecord).filter_by(
            send_report_id=campaign_id
        ).order_by(DeliveryRecord.id.desc()).first()
        
        current_email = None
        if latest_delivery:
            current_email = latest_delivery.recipient_email
        
        # Use campaign counts as fallback, but prefer delivery records
        total = campaign.total_recipients
        sent = campaign.sent_count if campaign.sent_count else sent_deliveries
        failed = campaign.failed_count if campaign.failed_count else failed_deliveries
        delivered = campaign.delivered_count if campaign.delivered_count else delivered_deliveries
        
        # Calculate remaining emails
        remaining = max(0, total - sent - failed)
        
        # Calculate progress percentage (based on sent + failed)
        progress = ((sent + failed) / total * 100) if total > 0 else 0
        
        return jsonify({
            'status': campaign.status,
            'total': total,
            'sent': sent,
            'failed': failed,
            'delivered': delivered,
            'remaining': remaining,
            'progress': round(progress, 1),
            'current_email': current_email,
            'started_at': campaign.started_at.isoformat() if campaign.started_at else None,
            'completed_at': campaign.completed_at.isoformat() if campaign.completed_at else None
        })
        
    except Exception as e:
        logger.error(f"Error in campaign_status_api for campaign {campaign_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/campaigns/<int:campaign_id>')
def campaign_detail(campaign_id):
    """View individual campaign details"""
    db = get_db_session()
    
    try:
        # Get campaign with relationships
        campaign = db.query(SendReport).options(
            joinedload(SendReport.smtp_config),
            joinedload(SendReport.email_account),
            joinedload(SendReport.delivery_records)
        ).filter_by(id=campaign_id).first()
        
        if not campaign:
            flash('Campaign not found', 'error')
            return redirect(url_for('campaigns_page'))
        
        # Get delivery records with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        delivery_query = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id).order_by(DeliveryRecord.sent_at.desc())
        total_deliveries = delivery_query.count()
        deliveries = delivery_query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Calculate statistics
        sent_count = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id, status='sent').count()
        failed_count = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id, status='failed').count()
        delivered_count = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id, status='delivered').count()
        bounced_count = db.query(DeliveryRecord).filter_by(send_report_id=campaign_id, status='bounced').count()
        
        stats = {
            'total': total_deliveries,
            'sent': sent_count,
            'failed': failed_count,
            'delivered': delivered_count,
            'bounced': bounced_count
        }
        
        # Get SMTP configs and Email accounts for resend modal
        smtp_configs = db.query(SMTPConfig).filter_by(is_active=True).all()
        email_accounts = db.query(EmailAccount).filter_by(is_active=True).all()
        
        return render_template('campaign_detail.html', campaign=campaign, 
                             deliveries=deliveries, page=page, per_page=per_page,
                             total_deliveries=total_deliveries, stats=stats,
                             smtp_configs=smtp_configs, email_accounts=email_accounts)
        
    except Exception as e:
        logger.error(f"Error loading campaign detail: {e}", exc_info=True)
        flash(f'Error loading campaign: {str(e)}', 'error')
        return redirect(url_for('campaigns_page'))
    finally:
        db.close()

@app.route('/campaigns/<int:campaign_id>/resend', methods=['POST'])
def resend_campaign(campaign_id):
    """Resend a campaign to the same recipients"""
    db = get_db_session()
    
    try:
        # Get original campaign
        original_campaign = db.query(SendReport).filter_by(id=campaign_id).first()
        
        if not original_campaign:
            flash('Campaign not found', 'error')
            return redirect(url_for('campaigns_page'))
        
        # Get SMTP config and Email account from form (or use original if not provided)
        smtp_config_id = request.form.get('smtp_config_id', type=int) or original_campaign.smtp_config_id
        email_account_id = request.form.get('email_account_id', type=int) or original_campaign.email_account_id
        delay_seconds = float(request.form.get('delay_seconds', original_campaign.delay_seconds or 20.0))
        
        # Validate SMTP config and Email account exist
        if not smtp_config_id:
            flash('SMTP configuration is required', 'error')
            return redirect(url_for('campaign_detail', campaign_id=campaign_id))
        
        smtp_config = db.query(SMTPConfig).filter_by(id=smtp_config_id).first()
        if not smtp_config:
            flash('SMTP configuration not found', 'error')
            return redirect(url_for('campaign_detail', campaign_id=campaign_id))
        
        if not email_account_id:
            flash('Email account is required', 'error')
            return redirect(url_for('campaign_detail', campaign_id=campaign_id))
        
        email_account = db.query(EmailAccount).filter_by(id=email_account_id).first()
        if not email_account:
            flash('Email account not found', 'error')
            return redirect(url_for('campaign_detail', campaign_id=campaign_id))
        
        # Validate that email account matches SMTP config
        if email_account.smtp_config_id != smtp_config_id:
            flash('Selected email account does not match the selected SMTP configuration', 'error')
            return redirect(url_for('campaign_detail', campaign_id=campaign_id))
        
        # Get all recipient emails from delivery records
        delivery_records = db.query(DeliveryRecord).filter_by(
            send_report_id=campaign_id
        ).all()
        
        if not delivery_records:
            # If no delivery records, we can't resend (shouldn't happen)
            flash('No recipients found for this campaign', 'error')
            return redirect(url_for('campaign_detail', campaign_id=campaign_id))
        
        # Get unique recipient emails from delivery records
        recipient_emails = list(set([record.recipient_email for record in delivery_records]))
        
        # Create new campaign with selected settings
        new_campaign_name = f"{original_campaign.campaign_name} (Resent)"
        new_campaign = SendReport(
            campaign_name=new_campaign_name,
            subject=original_campaign.subject,
            body_html=original_campaign.body_html,
            body_text=original_campaign.body_text,
            smtp_config_id=smtp_config_id,
            email_account_id=email_account_id,
            status='pending',
            total_recipients=len(recipient_emails),
            delay_seconds=delay_seconds
        )
        db.add(new_campaign)
        db.commit()
        
        new_campaign_id = new_campaign.id
        
        # Start sending in background (same logic as /sender/batch)
        def send_batch_emails():
            from emailer.sender import EmailSender
            from sqlalchemy import func
            from utils.db import DeliveryRecord, SendReport, SMTPConfig, EmailAccount
            import time
            
            db_session = get_db_session()
            
            try:
                # Get campaign from database
                campaign = db_session.query(SendReport).filter_by(id=new_campaign_id).first()
                if not campaign:
                    logger.error(f"Campaign {new_campaign_id} not found")
                    return
                
                # Get SMTP config and Email account
                smtp_config = None
                email_account = None
                
                if campaign.smtp_config_id:
                    smtp_config = db_session.query(SMTPConfig).filter_by(id=campaign.smtp_config_id).first()
                if campaign.email_account_id:
                    email_account = db_session.query(EmailAccount).filter_by(id=campaign.email_account_id).first()
                
                # Initialize EmailSender with campaign-specific settings
                if smtp_config:
                    sender = EmailSender(
                        smtp_host=smtp_config.host,
                        smtp_port=smtp_config.port,
                        smtp_user=smtp_config.username,
                        smtp_password=smtp_config.password,
                        use_tls=smtp_config.use_tls
                    )
                    if email_account:
                        sender.from_email = email_account.from_email
                        sender.from_name = email_account.from_name
                else:
                    sender = EmailSender()
                    if email_account:
                        sender.from_email = email_account.from_email
                        sender.from_name = email_account.from_name
                
                # Update campaign status
                campaign.status = 'running'
                campaign.started_at = datetime.utcnow()
                db_session.commit()
                
                total_emails = len(recipient_emails)
                logger.info(f"Resending campaign {new_campaign_id} to {total_emails} recipients")
                
                for i, email_addr in enumerate(recipient_emails):
                    try:
                        # Get email valid record to check subscription status
                        email_valid = db_session.query(EmailValid).filter(
                            func.lower(EmailValid.email) == email_addr.lower()
                        ).first()
                        
                        # Skip if unsubscribed
                        if email_valid and not email_valid.subscribed:
                            logger.info(f"Skipping unsubscribed email: {email_addr}")
                            continue
                        
                        # Prepare email body with unsubscribe link
                        final_body = campaign.body_html
                        
                        # Add unsubscribe link (always included for compliance)
                        if email_valid:
                            # Generate unsubscribe token if not exists
                            if not email_valid.unsubscribe_token:
                                token = generate_unsubscribe_token(email_addr)
                                email_valid.unsubscribe_token = token
                                db_session.commit()
                            
                            # Create unsubscribe link
                            unsubscribe_url = f"{config.BASE_URL.rstrip('/')}/unsubscribe?token={email_valid.unsubscribe_token}"
                            
                            # Add unsubscribe link to body
                            final_body = campaign.body_html + f'''
                            <hr style="margin-top: 20px; border: none; border-top: 1px solid #eee;">
                            <p style="font-size: 12px; color: #999; text-align: center; margin-top: 20px;">
                                <a href="{unsubscribe_url}" style="color: #999; text-decoration: underline;">Unsubscribe</a>
                            </p>
                            '''
                        
                        # Send email
                        success, error = sender.send_email(
                            to_email=email_addr,
                            subject=campaign.subject,
                            body_html=final_body,
                            body_text=campaign.body_text
                        )
                        
                        # Create delivery record
                        delivery = DeliveryRecord(
                            send_report_id=campaign.id,
                            recipient_email=email_addr,
                            status='sent' if success else 'failed',
                            error_message=error if not success else None,
                            sent_at=datetime.utcnow() if success else None
                        )
                        db_session.add(delivery)
                        
                        if success:
                            campaign.sent_count += 1
                            logger.info(f"✓ Resent to {email_addr} ({campaign.sent_count}/{total_emails})")
                        else:
                            campaign.failed_count += 1
                            logger.warning(f"✗ Failed to resend to {email_addr}: {error}")
                        
                        db_session.commit()
                        
                        # Rate limiting - use campaign-specific delay
                        delay = campaign.delay_seconds if campaign.delay_seconds else 20.0
                        time.sleep(delay)
                        
                    except Exception as e:
                        logger.error(f"Error resending to {email_addr}: {e}", exc_info=True)
                        campaign.failed_count += 1
                        
                        try:
                            delivery = DeliveryRecord(
                                send_report_id=campaign.id,
                                recipient_email=email_addr,
                                status='failed',
                                error_message=f"Unexpected error: {str(e)}",
                                sent_at=None
                            )
                            db_session.add(delivery)
                            db_session.commit()
                        except:
                            pass
                
                campaign.status = 'completed'
                campaign.completed_at = datetime.utcnow()
                db_session.commit()
                
            except Exception as e:
                logger.error(f"Error in resend campaign: {e}", exc_info=True)
                try:
                    campaign = db_session.query(SendReport).filter_by(id=new_campaign_id).first()
                    if campaign:
                        campaign.status = 'failed'
                        db_session.commit()
                except:
                    pass
            finally:
                db_session.close()
        
        thread = threading.Thread(target=send_batch_emails, daemon=True)
        thread.start()
        
        flash(f'Campaign resent! New campaign created with {len(recipient_emails)} recipients.', 'success')
        return redirect(url_for('campaign_detail', campaign_id=new_campaign_id))
        
    except Exception as e:
        logger.error(f"Error resending campaign: {e}", exc_info=True)
        flash(f'Error resending campaign: {str(e)}', 'error')
        db.rollback()
        return redirect(url_for('campaign_detail', campaign_id=campaign_id))
    finally:
        db.close()

@app.route('/campaigns/new')
def new_campaign_page():
    """Professional campaign creation page"""
    db = get_db_session()
    
    try:
        # Get SMTP configs and Email accounts
        smtp_configs = db.query(SMTPConfig).filter_by(is_active=True).all()
        email_accounts = db.query(EmailAccount).filter_by(is_active=True).all()
        
        # Get count of valid emails (subscribed only)
        valid_count = db.query(EmailValid).filter_by(subscribed=True).count()
        total_count = db.query(EmailValid).count()
        
        return render_template('campaign_new.html', smtp_configs=smtp_configs, 
                             email_accounts=email_accounts, valid_count=valid_count,
                             total_count=total_count)
        
    finally:
        db.close()

@app.route('/sender')
def sender_page():
    """Email sender page"""
    db = get_db_session()
    
    try:
        # Get recent campaigns
        campaigns = db.query(SendReport).order_by(SendReport.created_at.desc()).limit(10).all()
        
        # Get count of valid emails (subscribed only)
        valid_count = db.query(EmailValid).filter_by(subscribed=True).count()
        total_count = db.query(EmailValid).count()
        
        # Get SMTP configurations and Email accounts
        smtp_configs = db.query(SMTPConfig).filter_by(is_active=True).all()
        email_accounts = db.query(EmailAccount).filter_by(is_active=True).all()
        
        # Get legacy SMTP configuration for display (fallback)
        smtp_config = {
            'host': config.SENDER_SMTP_HOST or 'Not configured',
            'port': config.SENDER_SMTP_PORT or 'Not configured',
            'from_email': config.SENDER_FROM_EMAIL or 'Not configured',
            'use_tls': 'Yes' if config.SENDER_SMTP_USE_TLS else 'No',
            'user': config.SENDER_SMTP_USER or 'Not configured'
        }
        
        return render_template('sender.html', campaigns=campaigns, valid_count=valid_count, 
                             total_count=total_count, smtp_config=smtp_config,
                             smtp_configs=smtp_configs, email_accounts=email_accounts)
        
    finally:
        db.close()

@app.route('/sender/test-smtp', methods=['POST'])
def test_smtp_connection():
    """Test SMTP connection"""
    try:
        from emailer.sender import EmailSender
        
        sender = EmailSender()
        success, message = sender.test_connection()
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'details': {
                    'host': config.SENDER_SMTP_HOST,
                    'port': config.SENDER_SMTP_PORT,
                    'user': config.SENDER_SMTP_USER,
                    'from_email': config.SENDER_FROM_EMAIL,
                    'use_tls': config.SENDER_SMTP_USE_TLS,
                    'timeout': getattr(config, 'SENDER_SMTP_TIMEOUT', 30)
                }
            })
        else:
            # Include current settings in error response
            return jsonify({
                'success': False,
                'message': message,
                'current_settings': {
                    'host': config.SENDER_SMTP_HOST or 'Not set',
                    'port': config.SENDER_SMTP_PORT or 'Not set',
                    'user': config.SENDER_SMTP_USER or 'Not set',
                    'from_email': config.SENDER_FROM_EMAIL or 'Not set',
                    'use_tls': config.SENDER_SMTP_USE_TLS,
                    'timeout': getattr(config, 'SENDER_SMTP_TIMEOUT', 30)
                },
                'suggestions': get_smtp_suggestions(message)
            }), 400
            
    except Exception as e:
        logger.error(f"Error testing SMTP connection: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error testing connection: {str(e)}'
        }), 500

def get_smtp_suggestions(error_message):
    """Get helpful suggestions based on error message"""
    error_lower = error_message.lower()
    suggestions = []
    
    if 'timeout' in error_lower or 'timed out' in error_lower:
        suggestions.append("Check your internet connection")
        suggestions.append("Verify the SMTP host and port are correct")
        suggestions.append("Check if your firewall is blocking the connection")
        suggestions.append("Try increasing SENDER_SMTP_TIMEOUT in .env (default: 30 seconds)")
    elif 'authentication' in error_lower or 'login' in error_lower or 'password' in error_lower:
        suggestions.append("Verify your SMTP username and password are correct")
        suggestions.append("For Gmail, use an 'App Password' instead of your regular password")
        suggestions.append("Check if 2-factor authentication is enabled (Gmail requires App Password)")
        suggestions.append("Verify SENDER_SMTP_USER and SENDER_SMTP_PASSWORD in .env")
    elif 'connection' in error_lower or 'refused' in error_lower:
        suggestions.append("Verify the SMTP host address is correct")
        suggestions.append("Check if the SMTP port is correct (587 for TLS, 465 for SSL, 25 for non-encrypted)")
        suggestions.append("Check if your ISP is blocking SMTP ports")
    elif 'tls' in error_lower or 'ssl' in error_lower:
        suggestions.append("Try changing SENDER_SMTP_USE_TLS in .env")
        suggestions.append("Some servers require TLS, others don't - check your email provider's documentation")
    
    if not suggestions:
        suggestions.append("Check your .env file configuration")
        suggestions.append("Verify all SMTP settings are correct")
        suggestions.append("Check the application logs for more details")
    
    return suggestions

def generate_unsubscribe_token(email):
    """Generate unique unsubscribe token"""
    import hashlib
    import base64
    timestamp = str(datetime.utcnow().timestamp())
    data = f"{email}{timestamp}{config.SECRET_KEY}"
    token = base64.urlsafe_b64encode(hashlib.sha256(data.encode()).digest()).decode()[:32]
    return token

@app.route('/sender/get-subscribed', methods=['GET'])
def get_subscribed_emails():
    """Get all subscribed email addresses"""
    db = get_db_session()
    
    try:
        subscribed_emails = db.query(EmailValid).filter_by(subscribed=True).all()
        emails = [email.email for email in subscribed_emails]
        return jsonify({'success': True, 'emails': emails, 'count': len(emails)})
    finally:
        db.close()

@app.route('/sender/batch', methods=['GET', 'POST'])
def sender_batch():
    """Batch email sender page with selection"""
    db = get_db_session()
    
    try:
        if request.method == 'POST':
            data = request.get_json()
            emails = data.get('emails', [])
            subject = data.get('subject', '')
            body_html = data.get('body_html', '')
            body_text = data.get('body_text', '')
            include_unsubscribe = data.get('include_unsubscribe', True)
            
            if not emails or not subject or not body_html:
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
            # Get SMTP config and Email account IDs
            smtp_config_id = data.get('smtp_config_id')
            email_account_id = data.get('email_account_id')
            
            # Validate SMTP config and Email account exist
            if smtp_config_id:
                smtp_config = db.query(SMTPConfig).filter_by(id=smtp_config_id).first()
                if not smtp_config:
                    return jsonify({'success': False, 'error': 'SMTP configuration not found'}), 404
            
            if email_account_id:
                email_account = db.query(EmailAccount).filter_by(id=email_account_id).first()
                if not email_account:
                    return jsonify({'success': False, 'error': 'Email account not found'}), 404
            
            # Get custom campaign name if provided
            campaign_name = data.get('campaign_name') or f"Batch Campaign - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            
            # Get delay_seconds (default to 20.0 if not provided)
            delay_seconds = float(data.get('delay_seconds', 20.0))
            if delay_seconds < 0:
                delay_seconds = 20.0  # Ensure non-negative
            
            # Create campaign
            campaign = SendReport(
                campaign_name=campaign_name,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                smtp_config_id=smtp_config_id,
                email_account_id=email_account_id,
                status='pending',
                total_recipients=len(emails),
                delay_seconds=delay_seconds
            )
            db.add(campaign)
            db.commit()
            
            # Store campaign_id for background thread
            campaign_id = campaign.id
            
            # Start sending in background
            def send_batch_emails():
                from emailer.sender import EmailSender
                from sqlalchemy import func
                from utils.db import DeliveryRecord, SendReport, SMTPConfig, EmailAccount
                import time
                import random
                
                db_session = get_db_session()
                
                try:
                    # Get campaign from database
                    campaign = db_session.query(SendReport).filter_by(id=campaign_id).first()
                    if not campaign:
                        logger.error(f"Campaign {campaign_id} not found")
                        return
                    
                    # Get SMTP config and Email account
                    smtp_config = None
                    email_account = None
                    
                    if campaign.smtp_config_id:
                        smtp_config = db_session.query(SMTPConfig).filter_by(id=campaign.smtp_config_id).first()
                    if campaign.email_account_id:
                        email_account = db_session.query(EmailAccount).filter_by(id=campaign.email_account_id).first()
                    
                    # Initialize EmailSender with campaign-specific settings
                    if smtp_config:
                        sender = EmailSender(
                            smtp_host=smtp_config.host,
                            smtp_port=smtp_config.port,
                            smtp_user=smtp_config.username,
                            smtp_password=smtp_config.password,
                            use_tls=smtp_config.use_tls
                        )
                        # Override from_email and from_name if email_account is set
                        if email_account:
                            sender.from_email = email_account.from_email
                            sender.from_name = email_account.from_name
                    else:
                        # Fallback to config.py settings
                        sender = EmailSender()
                        if email_account:
                            sender.from_email = email_account.from_email
                            sender.from_name = email_account.from_name
                    
                    total_emails = len(emails)
                    logger.info(f"Starting to send {total_emails} emails for campaign {campaign_id} using SMTP: {smtp_config.name if smtp_config else 'default'}, Email: {email_account.from_email if email_account else 'default'}")
                    
                    for i, email_addr in enumerate(emails):
                        try:
                            # Get email valid record
                            email_valid = db_session.query(EmailValid).filter(
                                func.lower(EmailValid.email) == email_addr.lower()
                            ).first()
                            
                            if not email_valid or not email_valid.subscribed:
                                logger.debug(f"Skipping {email_addr} (not subscribed or not found)")
                                continue
                            
                            # Log progress
                            logger.info(f"Sending email {i+1}/{total_emails}: {email_addr}")
                            
                            # Prepare email body
                            final_body = campaign.body_html
                            
                            # Add unsubscribe link (always included for compliance)
                            if email_valid:
                                # Generate unsubscribe token if not exists
                                if not email_valid.unsubscribe_token:
                                    token = generate_unsubscribe_token(email_addr)
                                    email_valid.unsubscribe_token = token
                                    db_session.commit()
                                
                                # Create unsubscribe link
                                unsubscribe_url = f"{config.BASE_URL.rstrip('/')}/unsubscribe?token={email_valid.unsubscribe_token}"
                                
                                # Add unsubscribe link to body
                                final_body = campaign.body_html + f'''
                                <hr style="margin-top: 20px; border: none; border-top: 1px solid #eee;">
                                <p style="font-size: 12px; color: #999; text-align: center; margin-top: 20px;">
                                    <a href="{unsubscribe_url}" style="color: #999; text-decoration: underline;">Unsubscribe</a>
                                </p>
                                '''
                            
                            # Send email one by one
                            success, error = sender.send_email(
                                email_addr,
                                campaign.subject,
                                final_body,
                                campaign.body_text
                            )
                            
                            # Record delivery
                            delivery = DeliveryRecord(
                                send_report_id=campaign.id,
                                recipient_email=email_addr,
                                status='sent' if success else 'failed',
                                error_message=error if not success else None,
                                sent_at=datetime.utcnow() if success else None
                            )
                            db_session.add(delivery)
                            
                            if success:
                                campaign.sent_count += 1
                                logger.info(f"✓ Successfully sent to {email_addr} ({campaign.sent_count} sent, {campaign.failed_count} failed)")
                            else:
                                campaign.failed_count += 1
                                logger.warning(f"✗ Failed to send to {email_addr}: {error} ({campaign.sent_count} sent, {campaign.failed_count} failed)")
                            
                            db_session.commit()
                            
                        except Exception as e:
                            # Catch any unexpected errors and continue
                            logger.error(f"Unexpected error processing {email_addr}: {e}", exc_info=True)
                            campaign.failed_count += 1
                            
                            # Still record the failure
                            try:
                                delivery = DeliveryRecord(
                                    send_report_id=campaign.id,
                                    recipient_email=email_addr,
                                    status='failed',
                                    error_message=f"Unexpected error: {str(e)}",
                                    sent_at=None
                                )
                                db_session.add(delivery)
                                db_session.commit()
                            except:
                                pass
                        
                        # Rate limiting - use campaign-specific delay
                        delay = campaign.delay_seconds if campaign.delay_seconds else 20.0
                        time.sleep(delay)
                    
                    campaign.status = 'completed'
                    campaign.completed_at = datetime.utcnow()
                    db_session.commit()
                except Exception as e:
                    logger.error(f"Error in batch email sending: {e}")
                    campaign.status = 'failed'
                    db_session.commit()
                finally:
                    db_session.close()
            
            thread = threading.Thread(target=send_batch_emails, daemon=True)
            thread.start()
            
            return jsonify({
                'success': True, 
                'campaign_id': campaign.id, 
                'count': len(emails), 
                'message': 'Emails queued for sending',
                'campaign_name': campaign.campaign_name
            })
        
        # GET request - show page (optional, can redirect to valid emails page)
        return redirect(url_for('emails_valid'))
    finally:
        db.close()

# ==================== SMTP Configuration Management ====================

@app.route('/smtp-configs')
def smtp_configs_page():
    """SMTP configurations management page"""
    db = get_db_session()
    try:
        configs = db.query(SMTPConfig).order_by(SMTPConfig.created_at.desc()).all()
        return render_template('smtp_configs.html', smtp_configs=configs)
    finally:
        db.close()

@app.route('/smtp-configs/add', methods=['GET', 'POST'])
def add_smtp_config():
    """Add new SMTP configuration"""
    if request.method == 'POST':
        db = get_db_session()
        try:
            data = request.get_json()
            config_obj = SMTPConfig(
                name=data.get('name'),
                host=data.get('host'),
                port=int(data.get('port', 587)),
                username=data.get('username'),
                password=data.get('password'),
                use_tls=data.get('use_tls', True),
                timeout=int(data.get('timeout', 30)),
                is_active=data.get('is_active', True)
            )
            db.add(config_obj)
            db.commit()
            return jsonify({'success': True, 'id': config_obj.id, 'message': 'SMTP configuration added'})
        except Exception as e:
            logger.error(f"Error adding SMTP config: {e}", exc_info=True)
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    return jsonify({'success': False, 'error': 'Invalid method'}), 405

@app.route('/smtp-configs/<int:config_id>/edit', methods=['GET', 'POST'])
def edit_smtp_config(config_id):
    """Edit SMTP configuration"""
    db = get_db_session()
    try:
        config_obj = db.query(SMTPConfig).filter_by(id=config_id).first()
        if not config_obj:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
        
        if request.method == 'GET':
            # Return config data for editing
            return jsonify({
                'success': True,
                'config': {
                    'name': config_obj.name,
                    'host': config_obj.host,
                    'port': config_obj.port,
                    'username': config_obj.username,
                    'use_tls': config_obj.use_tls,
                    'timeout': config_obj.timeout,
                    'is_active': config_obj.is_active
                }
            })
        
        # POST - Update config
        data = request.get_json()
        config_obj.name = data.get('name', config_obj.name)
        config_obj.host = data.get('host', config_obj.host)
        config_obj.port = int(data.get('port', config_obj.port))
        config_obj.username = data.get('username', config_obj.username)
        if data.get('password'):  # Only update if provided
            config_obj.password = data.get('password')
        config_obj.use_tls = data.get('use_tls', config_obj.use_tls)
        config_obj.timeout = int(data.get('timeout', config_obj.timeout))
        config_obj.is_active = data.get('is_active', config_obj.is_active)
        config_obj.updated_at = datetime.utcnow()
        
        db.commit()
        return jsonify({'success': True, 'message': 'SMTP configuration updated'})
    except Exception as e:
        logger.error(f"Error editing SMTP config: {e}", exc_info=True)
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/smtp-configs/<int:config_id>/delete', methods=['POST'])
def delete_smtp_config(config_id):
    """Delete SMTP configuration"""
    db = get_db_session()
    try:
        config_obj = db.query(SMTPConfig).filter_by(id=config_id).first()
        if not config_obj:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
        
        # Check if used in campaigns
        campaigns = db.query(SendReport).filter_by(smtp_config_id=config_id).count()
        if campaigns > 0:
            return jsonify({'success': False, 'error': f'Cannot delete: used in {campaigns} campaign(s)'}), 400
        
        db.delete(config_obj)
        db.commit()
        return jsonify({'success': True, 'message': 'SMTP configuration deleted'})
    except Exception as e:
        logger.error(f"Error deleting SMTP config: {e}", exc_info=True)
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/smtp-configs/<int:config_id>/test', methods=['POST'])
def test_smtp_config(config_id):
    """Test SMTP configuration"""
    db = get_db_session()
    try:
        config_obj = db.query(SMTPConfig).filter_by(id=config_id).first()
        if not config_obj:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
        
        from emailer.sender import EmailSender
        sender = EmailSender(
            smtp_host=config_obj.host,
            smtp_port=config_obj.port,
            smtp_user=config_obj.username,
            smtp_password=config_obj.password,
            use_tls=config_obj.use_tls
        )
        success, message = sender.test_connection()
        
        return jsonify({
            'success': success,
            'message': message,
            'details': {
                'host': config_obj.host,
                'port': config_obj.port,
                'username': config_obj.username,
                'use_tls': config_obj.use_tls,
                'timeout': config_obj.timeout
            }
        })
    except Exception as e:
        logger.error(f"Error testing SMTP config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

# ==================== Email Account Management ====================

@app.route('/email-accounts')
def email_accounts_page():
    """Email accounts management page"""
    db = get_db_session()
    try:
        # Use joinedload to eagerly load smtp_config relationship
        accounts = db.query(EmailAccount).options(
            joinedload(EmailAccount.smtp_config)
        ).order_by(EmailAccount.created_at.desc()).all()
        smtp_configs = db.query(SMTPConfig).filter_by(is_active=True).all()
        return render_template('email_accounts.html', email_accounts=accounts, smtp_configs=smtp_configs)
    except Exception as e:
        logger.error(f"Error loading email accounts page: {e}", exc_info=True)
        flash(f'Error loading email accounts: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        db.close()

@app.route('/email-accounts/add', methods=['POST'])
def add_email_account():
    """Add new email account"""
    db = get_db_session()
    try:
        data = request.get_json()
        
        # Verify SMTP config exists
        smtp_config = db.query(SMTPConfig).filter_by(id=data.get('smtp_config_id')).first()
        if not smtp_config:
            return jsonify({'success': False, 'error': 'SMTP configuration not found'}), 404
        
        account = EmailAccount(
            smtp_config_id=data.get('smtp_config_id'),
            name=data.get('name'),
            from_email=data.get('from_email'),
            from_name=data.get('from_name'),
            reply_to=data.get('reply_to'),
            is_active=data.get('is_active', True)
        )
        db.add(account)
        db.commit()
        return jsonify({'success': True, 'id': account.id, 'message': 'Email account added'})
    except Exception as e:
        logger.error(f"Error adding email account: {e}", exc_info=True)
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/email-accounts/<int:account_id>/edit', methods=['GET', 'POST'])
def edit_email_account(account_id):
    """Edit email account"""
    db = get_db_session()
    try:
        account = db.query(EmailAccount).filter_by(id=account_id).first()
        if not account:
            return jsonify({'success': False, 'error': 'Account not found'}), 404
        
        if request.method == 'GET':
            # Return account data for editing
            return jsonify({
                'success': True,
                'account': {
                    'name': account.name,
                    'smtp_config_id': account.smtp_config_id,
                    'from_email': account.from_email,
                    'from_name': account.from_name,
                    'reply_to': account.reply_to,
                    'is_active': account.is_active
                }
            })
        
        # POST - Update account
        data = request.get_json()
        account.name = data.get('name', account.name)
        account.from_email = data.get('from_email', account.from_email)
        account.from_name = data.get('from_name', account.from_name)
        account.reply_to = data.get('reply_to', account.reply_to)
        account.is_active = data.get('is_active', account.is_active)
        if data.get('smtp_config_id'):
            # Verify SMTP config exists
            smtp_config = db.query(SMTPConfig).filter_by(id=data.get('smtp_config_id')).first()
            if not smtp_config:
                return jsonify({'success': False, 'error': 'SMTP configuration not found'}), 404
            account.smtp_config_id = data.get('smtp_config_id')
        account.updated_at = datetime.utcnow()
        
        db.commit()
        return jsonify({'success': True, 'message': 'Email account updated'})
    except Exception as e:
        logger.error(f"Error editing email account: {e}", exc_info=True)
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/email-accounts/<int:account_id>/delete', methods=['POST'])
def delete_email_account(account_id):
    """Delete email account"""
    db = get_db_session()
    try:
        account = db.query(EmailAccount).filter_by(id=account_id).first()
        if not account:
            return jsonify({'success': False, 'error': 'Account not found'}), 404
        
        # Check if used in campaigns
        campaigns = db.query(SendReport).filter_by(email_account_id=account_id).count()
        if campaigns > 0:
            return jsonify({'success': False, 'error': f'Cannot delete: used in {campaigns} campaign(s)'}), 400
        
        db.delete(account)
        db.commit()
        return jsonify({'success': True, 'message': 'Email account deleted'})
    except Exception as e:
        logger.error(f"Error deleting email account: {e}", exc_info=True)
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@app.route('/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
    """Handle unsubscribe requests"""
    db = get_db_session()
    
    try:
        token = request.args.get('token') or request.form.get('token')
        
        if not token:
            return render_template('unsubscribe.html', error='Invalid unsubscribe link')
        
        # Find email by token
        email_valid = db.query(EmailValid).filter_by(unsubscribe_token=token).first()
        
        if not email_valid:
            return render_template('unsubscribe.html', error='Invalid unsubscribe link')
        
        if request.method == 'POST' or request.args.get('confirm'):
            # Unsubscribe
            email_valid.subscribed = False
            email_valid.unsubscribed_at = datetime.utcnow()
            db.commit()
            
            return render_template('unsubscribe.html', 
                                 success=True, 
                                 email=email_valid.email)
        
        # Show confirmation page
        return render_template('unsubscribe.html', 
                             email=email_valid.email, 
                             token=token)
    finally:
        db.close()

@app.route('/test-network')
def test_network():
    """Test endpoint to verify network access"""
    import socket
    hostname = socket.gethostname()
    local_ip = '127.0.0.1'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    
    return jsonify({
        'status': 'success',
        'message': 'Network test endpoint is accessible',
        'hostname': hostname,
        'local_ip': local_ip,
        'server_host': request.host,
        'remote_addr': request.remote_addr,
        'access_from': 'This endpoint confirms network access is working'
    })

@app.route('/api/stats')
def api_stats():
    """API endpoint for live statistics"""
    db = get_db_session()
    
    try:
        stats = {
            'total_pages': db.query(ScanResult).filter_by(status='success').count(),
            'total_emails': db.query(EmailRaw).count(),
            'valid_emails': db.query(EmailValid).count(),
            'invalid_emails': db.query(EmailInvalid).count(),
            'pending_validation': db.query(EmailRaw).filter_by(validated=False).count()
        }
        
        return jsonify(stats)
        
    finally:
        db.close()


# Global storage for Google search jobs
google_search_jobs = {}

@app.route('/google/search', methods=['GET', 'POST'])
def google_search():
    """Google search URL extraction with live progress"""
    if request.method == 'POST':
        queries_text = request.form.get('queries', '')
        num_results = int(request.form.get('num_results', 10))
        
        # Parse queries
        queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
        
        if not queries:
            return jsonify({'error': 'Please provide at least one search query'}), 400
        
        # Create a unique job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Initialize job state
        google_search_jobs[job_id] = {
            'status': 'running',
            'progress': 0,
            'message': 'Initializing ChromeDriver...',
            'urls': [],
            'activity': [],
            'queries': queries,
            'num_results': num_results,
            'error': None
        }
        
        # Extract URLs from Google in background
        def extract_and_save():
            job = google_search_jobs[job_id]
            scan_job_id = None
            
            try:
                job['activity'].append({'message': f'Starting search for {len(queries)} queries', 'type': 'info'})
                job['message'] = 'Starting Google search...'
                
                # Import here to use the updated extractor
                from scraper.google_search import GoogleSearchExtractor
                
                with GoogleSearchExtractor(headless=config.SELENIUM_HEADLESS) as extractor:
                    job['activity'].append({'message': 'ChromeDriver initialized successfully', 'type': 'success'})
                    job['message'] = 'ChromeDriver ready'
                    job['progress'] = 10
                    
                    all_urls = set()
                    total_queries = len(queries)
                    
                    for i, query in enumerate(queries):
                        job['activity'].append({'message': f'Searching: {query}', 'type': 'info'})
                        job['message'] = f'Searching query {i+1}/{total_queries}: {query[:50]}...'
                        
                        try:
                            urls = extractor.search_google(query, num_results)
                            new_urls = [url for url in urls if url not in all_urls]
                            all_urls.update(new_urls)
                            
                            # Update job with new URLs
                            job['urls'] = list(all_urls)
                            job['activity'].append({'message': f'Found {len(new_urls)} new URLs ({len(all_urls)} total)', 'type': 'success'})
                            
                            # Update progress
                            job['progress'] = 10 + int((i + 1) / total_queries * 70)
                            
                        except Exception as e:
                            job['activity'].append({'message': f'Error searching "{query}": {str(e)}', 'type': 'error'})
                            logger.error(f'Error searching query "{query}": {e}')
                    
                    job['message'] = f'Extraction complete! Found {len(all_urls)} URLs'
                    job['progress'] = 80
                    job['activity'].append({'message': f'Total URLs extracted: {len(all_urls)}', 'type': 'success'})
                
                if not all_urls:
                    job['status'] = 'completed'
                    job['progress'] = 100
                    job['message'] = 'No URLs found'
                    job['activity'].append({'message': 'No URLs extracted. Try different queries.', 'type': 'warning'})
                    return
                
                # Create a scan job with the extracted URLs
                job['message'] = 'Creating scan job...'
                job['progress'] = 85
                
                db = get_db_session()
                try:
                    scan_job = ScanJob(
                        name=f'Google Search: {queries[0][:50]}...' if queries else 'Google Search',
                        urls=json.dumps(list(all_urls)),
                        threads=config.SCRAPER_THREADS,
                        max_depth=1,
                        status='pending'
                    )
                    db.add(scan_job)
                    db.commit()
                    scan_job_id = scan_job.id
                    job['scan_job_id'] = scan_job_id
                    job['activity'].append({'message': f'Scan job created (ID: {scan_job_id})', 'type': 'success'})
                    logger.info(f"Created scan job {scan_job_id} with {len(all_urls)} URLs from Google")
                finally:
                    db.close()
                
                # Mark as completed
                job['status'] = 'completed'
                job['progress'] = 100
                job['message'] = f'Complete! {len(all_urls)} URLs ready for scanning'
                job['activity'].append({'message': 'Extraction completed successfully!', 'type': 'success'})
                
                # Save to search history
                db = get_db_session()
                try:
                    history_entry = GoogleSearchHistory(
                        queries=json.dumps(queries),
                        num_results_per_query=num_results,
                        total_urls_found=len(all_urls),
                        urls=json.dumps(list(all_urls)),
                        scan_job_id=scan_job_id,
                        status='completed',
                        completed_at=datetime.utcnow()
                    )
                    db.add(history_entry)
                    db.commit()
                    logger.info(f"Saved search history entry with {len(all_urls)} URLs")
                except Exception as e:
                    logger.error(f"Failed to save search history: {e}")
                finally:
                    db.close()
                
                
            except Exception as e:
                error_msg = str(e)
                job['status'] = 'failed'
                job['error'] = error_msg
                job['message'] = f'Error: {error_msg}'
                job['activity'].append({'message': f'Fatal error: {error_msg}', 'type': 'error'})
                
                logger.error(f"Google search error: {e}")
                
                # Handle specific error types
                if 'SSL' in error_msg or 'UNEXPECTED_EOF' in error_msg:
                    job['activity'].append({'message': 'ChromeDriver SSL error. Try manual installation.', 'type': 'error'})
                elif '10054' in error_msg or 'forcibly closed' in error_msg.lower():
                    job['activity'].append({'message': 'Connection blocked. Google may be rate limiting.', 'type': 'error'})
        
        thread = threading.Thread(target=extract_and_save, daemon=True)
        thread.start()
        
        
        return jsonify({'job_id': job_id, 'message': 'Search started'})
    
    return render_template('google_search.html')

@app.route('/google/search/status/<job_id>')
def google_search_status(job_id):
    """Get status of a Google search job"""
    if job_id not in google_search_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = google_search_jobs[job_id]
    
    # Return only the last 10 activity items to avoid sending too much data
    activity = job['activity'][-10:] if len(job['activity']) > 10 else job['activity']
    
    return jsonify({
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'urls': job['urls'],
        'activity': activity,
        'error': job['error'],
        'scan_job_id': job.get('scan_job_id')
    })


@app.route('/google/search/history')
def google_search_history():
    """Get Google search history"""
    db = get_db_session()
    
    try:
        # Get last 10 search history entries
        history = db.query(GoogleSearchHistory).order_by(
            GoogleSearchHistory.created_at.desc()
        ).limit(10).all()
        
        history_data = []
        for entry in history:
            try:
                queries = json.loads(entry.queries) if entry.queries else []
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error parsing queries JSON for history entry {entry.id}: {e}")
                queries = []
            
            history_data.append({
                'id': entry.id,
                'queries': queries,
                'num_results_per_query': entry.num_results_per_query,
                'total_urls_found': entry.total_urls_found,
                'scan_job_id': entry.scan_job_id,
                'created_at': entry.created_at.isoformat(),
                'status': entry.status
            })
        
        return jsonify({'history': history_data})
        
    finally:
        db.close()


@app.route('/google/search/history/<int:history_id>/scan', methods=['POST'])
def create_scan_from_history(history_id):
    """Create a scan job from a search history entry"""
    db = get_db_session()
    
    try:
        # Get the history entry
        history_entry = db.query(GoogleSearchHistory).filter_by(id=history_id).first()
        
        if not history_entry:
            return jsonify({'error': 'History entry not found'}), 404
        
        # Parse URLs from history with error handling
        try:
            urls = json.loads(history_entry.urls) if history_entry.urls else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing URLs JSON for history entry {history_id}: {e}")
            return jsonify({'error': f'Invalid URLs data: {str(e)}'}), 400
        
        if not urls:
            return jsonify({'error': 'No URLs found in history'}), 400
        
        # Get queries for the scan name with error handling
        try:
            queries = json.loads(history_entry.queries) if history_entry.queries else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing queries JSON for history entry {history_id}: {e}")
            queries = []
        scan_name = f'History: {queries[0][:50]}...' if queries else f'History Scan #{history_id}'
        
        # Create scan job
        scan_job = ScanJob(
            name=scan_name,
            urls=json.dumps(urls),
            threads=config.SCRAPER_THREADS,
            max_depth=1,
            status='pending'
        )
        db.add(scan_job)
        db.commit()
        scan_job_id = scan_job.id
        
        logger.info(f"Created scan job {scan_job_id} from history entry {history_id} with {len(urls)} URLs")
        
        return jsonify({
            'scan_job_id': scan_job_id,
            'message': f'Scan job created with {len(urls)} URLs',
            'url_count': len(urls)
        })
        
    except Exception as e:
        logger.error(f"Error creating scan from history: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        db.close()


@app.route('/admin/purge', methods=['POST'])
def purge_database():
    """Purge all data from database"""
    db = get_db_session()
    
    try:
        db.query(DeliveryRecord).delete()
        db.query(SendReport).delete()
        db.query(EmailInvalid).delete()
        db.query(EmailValid).delete()
        db.query(EmailRaw).delete()
        db.query(ScanResult).delete()
        db.query(ScanJob).delete()
        db.commit()
        
        flash('Database purged successfully', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.rollback()
        flash(f'Error purging database: {e}', 'error')
        return redirect(url_for('index'))
    finally:
        db.close()

def run_dashboard(host=None, port=None, debug=None):
    """Run the Flask dashboard"""
    host = host or config.FLASK_HOST
    port = port or config.FLASK_PORT
    debug = debug if debug is not None else config.FLASK_DEBUG
    
    # Initialize database
    init_db()
    
    # Get local IP address for network access info
    import socket
    local_ip = '127.0.0.1'
    try:
        # Get the local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    
    logger.info("=" * 60)
    logger.info("Email Extraction System Dashboard Starting")
    logger.info("=" * 60)
    logger.info(f"Host binding: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Local access:  http://127.0.0.1:{port}")
    if host == '0.0.0.0':
        logger.info(f"Network access: http://{local_ip}:{port}")
        logger.info(f"Access from other devices on your network using: http://{local_ip}:{port}")
        logger.info("")
        logger.info("⚠️  If you can't access from another PC:")
        logger.info("   1. Check Windows Firewall - allow port 5000")
        logger.info("   2. Run: New-NetFirewallRule -DisplayName 'Flask Email System' -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow")
        logger.info("   3. Make sure both PCs are on the same network")
    logger.info("=" * 60)
    logger.info("")
    if host == '0.0.0.0':
        logger.info("🔧 FIREWALL FIX REQUIRED:")
        logger.info("   Run this PowerShell command as Administrator:")
        logger.info("   .\\fix_firewall.ps1")
        logger.info("   OR manually allow port 5000 in Windows Firewall")
        logger.info("")
    
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)

if __name__ == '__main__':
    run_dashboard()
