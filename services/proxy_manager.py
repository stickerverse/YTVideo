# services/proxy_manager.py should contain:
import requests
import random
from typing import List, Optional, Dict

class ProxyManager:
    """
    Service for managing and rotating proxy servers.
    """
    
    def __init__(self, proxies: Optional[List[str]] = None):
        """
        Initialize the proxy manager.
        
        Args:
            proxies: List of proxy URLs (optional)
        """
        self.proxies = proxies or []
        self.failed_proxies: Dict[str, int] = {}  # Track proxy failures
    
    def add_proxy(self, proxy_url: str) -> None:
        """
        Add a proxy to the list.
        
        Args:
            proxy_url: Proxy URL in the format "protocol://user:pass@host:port"
        """
        if proxy_url not in self.proxies:
            self.proxies.append(proxy_url)
    
    def add_proxies_from_file(self, file_path: str) -> int:
        """
        Add proxies from a text file, one proxy per line.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Number of proxies added
        """
        try:
            with open(file_path, 'r') as f:
                added = 0
                for line in f:
                    proxy = line.strip()
                    if proxy and not proxy.startswith('#'):
                        self.add_proxy(proxy)
                        added += 1
                return added
        except Exception as e:
            print(f"Error loading proxies from file: {e}")
            return 0
    
    def get_proxy(self) -> Optional[str]:
        """
        Get a working proxy.
        
        Returns:
            Proxy URL, or None if no working proxies available
        """
        # Filter out failed proxies
        working_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        
        if not working_proxies:
            # If all proxies have failed, try to reset some
            self._reset_failed_proxies()
            working_proxies = [p for p in self.proxies if p not in self.failed_proxies]
            
            if not working_proxies:
                return None
        
        # Return a random proxy
        return random.choice(working_proxies)
    
    def mark_proxy_failure(self, proxy_url: str) -> None:
        """
        Mark a proxy as failed.
        
        Args:
            proxy_url: Proxy URL
        """
        if proxy_url in self.proxies:
            self.failed_proxies[proxy_url] = self.failed_proxies.get(proxy_url, 0) + 1
    
    def _reset_failed_proxies(self) -> None:
        """Reset proxies that haven't failed too many times."""
        # Reset proxies with fewer than 5 failures
        for proxy, failures in list(self.failed_proxies.items()):
            if failures < 5:
                del self.failed_proxies[proxy]
    
    def test_proxy(self, proxy_url: str, test_url: str = "https://www.google.com") -> bool:
        """
        Test if a proxy is working.
        
        Args:
            proxy_url: Proxy URL to test
            test_url: URL to use for testing
            
        Returns:
            True if the proxy is working, False otherwise
        """
        try:
            response = requests.get(
                test_url,
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
