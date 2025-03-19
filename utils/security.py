import os
import re
import hashlib
import secrets
import time
from typing import Dict, Any, Optional, List, Tuple
from functools import wraps
import ipaddress

from flask import request, jsonify, current_app
from urllib.parse import urlparse

from ..config import config
from .logger import app_logger

# Load allowed hosts from config
ALLOWED_HOSTS = config.get('allowed_hosts', '*').split(',')
SECRET_KEY = config.get('secret_key', secrets.token_hex(32))
RATE_LIMIT_ENABLED = config.get('rate_limit_enabled', True)
ENVIRONMENT = config.get('environment', 'development')

# In-memory rate limiting storage (for simple deployments)
# For production, consider using Redis or another distributed cache
rate_limits: Dict[str, Dict[str, float]] = {}


class SecurityMiddleware:
    """Security middleware for Flask applications"""
    
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with a Flask app"""
        
        # Add security headers to all responses
        @app.after_request
        def add_security_headers(response):
            # Common security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Only set strict HSTS in production
            if ENVIRONMENT == 'production':
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            return response
        
        # Check host header to prevent host header attacks
        @app.before_request
        def validate_host():
            if '*' in ALLOWED_HOSTS:
                return
                
            host = request.host.split(':')[0]
            if host not in ALLOWED_HOSTS:
                app_logger.warning(f"Invalid host header: {host}")
                return jsonify({'error': 'Invalid host header'}), 400


def generate_token(data: Dict[str, Any], expiry: int = 3600) -> str:
    """
    Generate a secure token with the given data
    
    Args:
        data: Data to encode in the token
        expiry: Token expiry time in seconds (default: 1 hour)
        
    Returns:
        Secure token string
    """
    # Add timestamp for expiry check
    timestamp = int(time.time()) + expiry
    data['exp'] = timestamp
    
    # Create a string representation of the data
    data_str = '&'.join([f"{k}={v}" for k, v in sorted(data.items())])
    
    # Create signature using HMAC
    signature = hmac_sign(data_str)
    
    # Encode data and signature
    import base64
    import json
    
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    
    return f"{payload}.{signature}"


def verify_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify a token and return the data if valid
    
    Args:
        token: Token to verify
        
    Returns:
        Tuple of (is_valid, data)
    """
    try:
        # Split token into payload and signature
        payload, signature = token.split('.')
        
        # Decode payload
        import base64
        import json
        
        decoded_payload = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        
        # Check expiry
        if 'exp' in decoded_payload:
            if int(time.time()) > decoded_payload['exp']:
                return False, None
        
        # Recreate data string for signature verification
        data_str = '&'.join([f"{k}={v}" for k, v in sorted(decoded_payload.items())])
        
        # Verify signature
        expected_signature = hmac_sign(data_str)
        if signature != expected_signature:
            return False, None
        
        return True, decoded_payload
    except Exception as e:
        app_logger.error(f"Token verification error: {str(e)}")
        return False, None


def hmac_sign(data: str) -> str:
    """
    Create an HMAC signature for data
    
    Args:
        data: Data to sign
        
    Returns:
        HMAC signature
    """
    import hmac
    import hashlib
    import base64
    
    signature = hmac.new(
        SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).digest()
    
    return base64.urlsafe_b64encode(signature).decode()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other issues
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path traversal characters
    basename = os.path.basename(filename)
    
    # Remove or replace potentially dangerous characters
    basename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', basename)
    
    # Limit length
    if len(basename) > 255:
        name, ext = os.path.splitext(basename)
        basename = name[:255-len(ext)] + ext
    
    return basename


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid and properly formatted
    
    Args:
        url: URL to check
        
    Returns:
        True if the URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except:
        return False


def rate_limit(limit: int, period: int = 60):
    """
    Rate limiting decorator
    
    Args:
        limit: Number of requests allowed
        period: Time period in seconds
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not RATE_LIMIT_ENABLED:
                return f(*args, **kwargs)
                
            # Get client IP
            ip = request.remote_addr
            
            # Create endpoint key
            endpoint = request.path
            key = f"{ip}:{endpoint}"
            
            # Initialize rate limit data if not exists
            if key not in rate_limits:
                rate_limits[key] = {
                    'count': 0,
                    'reset_time': time.time() + period
                }
            
            # Reset count if period has passed
            if time.time() > rate_limits[key]['reset_time']:
                rate_limits[key] = {
                    'count': 0,
                    'reset_time': time.time() + period
                }
            
            # Increment count
            rate_limits[key]['count'] += 1
            
            # Check if limit exceeded
            if rate_limits[key]['count'] > limit:
                app_logger.warning(f"Rate limit exceeded for {ip} on {endpoint}")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': int(rate_limits[key]['reset_time'] - time.time())
                }), 429
            
            # Set rate limit headers
            response
