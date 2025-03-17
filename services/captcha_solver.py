import time
import requests
from typing import Optional, Dict, Any, Union
import base64
import os
import json
from io import BytesIO
from PIL import Image

from ..config import config


class CaptchaSolver:
    """
    Service for solving CAPTCHAs using external APIs.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the CAPTCHA solver.
        
        Args:
            api_key: API key for the CAPTCHA solving service (defaults to config value)
        """
        self.api_key = api_key or config.get('captcha_api_key')
        self.api_base_url = "https://2captcha.com/in.php"
        self.api_result_url = "https://2captcha.com/res.php"
        
        if not self.api_key:
            print("Warning: No CAPTCHA API key provided. CAPTCHA solving will not be available.")
    
    def solve_image_captcha(self, image_path_or_url: str, max_wait_time: int = 60) -> Optional[str]:
        """
        Solve an image-based CAPTCHA.
        
        Args:
            image_path_or_url: Path to an image file or URL of an image
            max_wait_time: Maximum time to wait for a solution (seconds)
            
        Returns:
            CAPTCHA solution string, or None if solving failed
        """
        if not self.api_key:
            raise ValueError("CAPTCHA API key not provided")
        
        # Get the image data
        if image_path_or_url.startswith(('http://', 'https://')):
            try:
                response = requests.get(image_path_or_url, timeout=10)
                response.raise_for_status()
                image_data = response.content
            except requests.RequestException as e:
                raise ValueError(f"Error downloading CAPTCHA image: {e}")
        elif os.path.exists(image_path_or_url):
            with open(image_path_or_url, 'rb') as f:
                image_data = f.read()
        else:
            raise ValueError(f"Image file not found: {image_path_or_url}")
        
        # Encode the image for API submission
        base64_image = base64.b64encode(image_data).decode('ascii')
        
        # Submit the CAPTCHA
        data = {
            'key': self.api_key,
            'method': 'base64',
            'body': base64_image,
            'json': 1,
        }
        
        try:
            response = requests.post(self.api_base_url, data=data)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') != 1:
                error = result.get('request', 'Unknown error')
                raise ValueError(f"CAPTCHA submission failed: {error}")
            
            captcha_id = result.get('request')
            
            # Wait for the solution
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                solution = self._get_solution(captcha_id)
                if solution:
                    return solution
                
                time.sleep(5)  # Wait before checking again
            
            # If we get here, the solution took too long
            return None
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error communicating with CAPTCHA service: {e}")
    
    def solve_recaptcha(self, site_key: str, site_url: str, max_wait_time: int = 120) -> Optional[str]:
        """
        Solve a Google reCAPTCHA.
        
        Args:
            site_key: reCAPTCHA site key
            site_url: URL of the page with the reCAPTCHA
            max_wait_time: Maximum time to wait for a solution (seconds)
            
        Returns:
            reCAPTCHA solution token, or None if solving failed
        """
        if not self.api_key:
            raise ValueError("CAPTCHA API key not provided")
        
        # Submit the reCAPTCHA
        data = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': site_url,
            'json': 1,
        }
        
        try:
            response = requests.post(self.api_base_url, data=data)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') != 1:
                error = result.get('request', 'Unknown error')
                raise ValueError(f"reCAPTCHA submission failed: {error}")
            
            captcha_id = result.get('request')
            
            # Wait for the solution
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                solution = self._get_solution(captcha_id)
                if solution:
                    return solution
                
                time.sleep(5)  # Wait before checking again
            
            # If we get here, the solution took too long
            return None
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error communicating with CAPTCHA service: {e}")
    
    def _get_solution(self, captcha_id: str) -> Optional[str]:
        """
        Check if a solution is ready for a submitted CAPTCHA.
        
        Args:
            captcha_id: ID of the submitted CAPTCHA
            
        Returns:
            CAPTCHA solution if available, None otherwise
        """
        params = {
            'key': self.api_key,
            'action': 'get',
            'id': captcha_id,
            'json': 1,
        }
        
        try:
            response = requests.get(self.api_result_url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') == 1:
                return result.get('request')
            
            # If status is not 1, check if it's still processing
            if result.get('request') == 'CAPCHA_NOT_READY':
                return None
            
            # If it's not processing and not ready, it's an error
            raise ValueError(f"CAPTCHA solving failed: {result.get('request', 'Unknown error')}")
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error checking CAPTCHA solution: {e}")
    
    def report_incorrect(self, captcha_id: str) -> bool:
        """
        Report an incorrect CAPTCHA solution.
        
        Args:
            captcha_id: ID of the incorrectly solved CAPTCHA
            
        Returns:
            True if the report was successful, False otherwise
        """
        if not self.api_key:
            return False
        
        params = {
            'key': self.api_key,
            'action': 'reportbad',
            'id': captcha_id,
            'json': 1,
        }
        
        try:
            response = requests.get(self.api_result_url, params=params)
            response.raise_for_status()
            result = response.json()
            
            return result.get('status') == 1
        
        except requests.RequestException:
            return False
    
    def get_balance(self) -> Optional[float]:
        """
        Get the current account balance.
        
        Returns:
            Account balance, or None if the request failed
        """
        if not self.api_key:
            return None
        
        params = {
            'key': self.api_key,
            'action': 'getbalance',
            'json': 1,
        }
        
        try:
            response = requests.get(self.api_result_url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') == 1:
                return float(result.get('request', '0'))
            
            return None
        
        except requests.RequestException:
            return None