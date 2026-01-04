from pathlib import Path
import json
from typing import Dict, Any

# Package defaults (bundled with code)
PACKAGE_CONFIG_DIR = Path(__file__).parent / "defaults"

# User configs (in project root, gitignored)
PROJECT_ROOT = Path(__file__).parent.parent.parent
USER_CONFIG_DIR = PROJECT_ROOT / "config"

class ConfigLoader:
    """Load configuration with user overrides"""

    @staticmethod
    def load_config(config_name: str) -> Dict[str, Any]:
        """
        Load config with fallback: user config -> default config

        Args:
            config_name: Name of the config file (e.g., 'parsers.json')

        Raises:
            FileNotFoundError: If no config file was found

        Returns:
            Parsed JSON configuration
        """
        user_config_path = USER_CONFIG_DIR / config_name
        if user_config_path.exists():
            with open(user_config_path) as f:
                return json.load(f)
            
        default_config_path = PACKAGE_CONFIG_DIR / config_name
        if default_config_path.exists():
            with open(default_config_path) as f:
                return json.load(f)
            
        raise FileNotFoundError(
            f"Config file '{config_name} not found in:\n"
            f" - {user_config_path}\n"
            f" - {default_config_path}"
        )


    @staticmethod
    def load_parsers_config():
        """Load parsers registry configuration"""
        return ConfigLoader.load_config('parsers.json')
    
    @staticmethod
    def load_rules_config():
        """Load rules registry configuration"""
        return ConfigLoader.load_config('rules.json')