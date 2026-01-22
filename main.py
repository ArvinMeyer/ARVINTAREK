"""
Main application entry point
"""
import sys
import argparse
from dashboard.app import run_dashboard
from utils.db import init_db
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Email Extraction & Verification System')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Start web dashboard')
    dashboard_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (0.0.0.0 for network access, 127.0.0.1 for local only)')
    dashboard_parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    dashboard_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Init DB command
    subparsers.add_parser('init-db', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'dashboard':
        logger.info("Starting Email Extraction System Dashboard")
        run_dashboard(host=args.host, port=args.port, debug=args.debug)
    
    elif args.command == 'init-db':
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    
    else:
        # Default: start dashboard on network (0.0.0.0)
        logger.info("Starting Email Extraction System Dashboard")
        logger.info("Use 'python main.py --help' for more options")
        logger.info("Starting on 0.0.0.0 for network access...")
        run_dashboard(host='0.0.0.0')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
