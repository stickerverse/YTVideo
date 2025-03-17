import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration manager for the YouTube Downloader application."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration with values from environment variables and config file.
        
        Args:
            config_file: Path to a JSON configuration file (optional)
        """
        self.config_data: Dict[str, Any] = {}
        
        # Default configuration values
        self.config_data = {
            "download_dir": os.getenv("DOWNLOAD_DIR", str(Path.home() / "Downloads")),
            "default_proxy": os.getenv("DEFAULT_PROXY", None),
            "captcha_api_key": os.getenv("CAPTCHA_API_KEY", None),
            "aria2": {
                "path": os.getenv("ARIA2_PATH", "aria2c"),  # Default assumes aria2c is in PATH
                "max_connections": int(os.getenv("ARIA2_MAX_CONNECTIONS", "4")),
                "split": int(os.getenv("ARIA2_SPLIT", "4")),
                "enabled": os.getenv("ARIA2_ENABLED", "true").lower() == "true"
            },
            "ytdlp": {
                "format": os.getenv("YTDLP_FORMAT", "bestvideo+bestaudio/best"),
                "preferred_codec": os.getenv("YTDLP_PREFERRED_CODEC", "mp4"),
            },
            "batch": {
                "max_concurrent": int(os.getenv("BATCH_MAX_CONCURRENT", "3")),
            }
        }
        
        # Override with config file if provided
        if config_file and os.path.exists(config_file):
            self._load_config_file(config_file)
    
    def _load_config_file(self, config_file: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_file: Path to a JSON configuration file
        """
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                
            # Update configuration with values from file
            self._update_nested_dict(self.config_data, file_config)
        except Exception as e:
            print(f"Error loading configuration file: {e}")
    
    def _update_nested_dict(self, d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a nested dictionary with values from another dictionary.
        
        Args:
            d: Dictionary to update
            u: Dictionary with new values
            
        Returns:
            Updated dictionary
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                d[k] = self._update_nested_dict(d[k], v)
            else:
                d[k] = v
        return d
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key (can be nested using dots, e.g., "aria2.max_connections")
            default: Default value to return if key is not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (can be nested using dots, e.g., "aria2.max_connections")
            value: Value to set
        """
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
                
        config[keys[-1]] = value
    
    def save(self, config_file: str) -> None:
        """
        Save the current configuration to a JSON file.
        
        Args:
            config_file: Path to save the configuration
        """
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            print(f"Error saving configuration file: {e}")

# Global configuration instance
config = Config()