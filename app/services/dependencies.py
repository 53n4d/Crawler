import os
import asyncio
from pathlib import Path

from .authentication.authentication import Authentication
from .crawler.crawler import Crawler
from .crawler.helpers import CrawlerHelpers
from ..common.helpers import CommonHelpers
from .authentication.helpers import AuthenticationHelpers
from ..common.ansi_colors import ANSIColors


class DependencyManager:
    def __init__(self):
        self.ansi_colors = ANSIColors()
        self.common_helpers = CommonHelpers(self.ansi_colors)
        
        # Get the absolute path to the app directory
        app_dir = Path(__file__).parent.parent
        patterns_dir = app_dir / "common" / "patterns"
        constants_dir = app_dir / "common" / "constants"
        
        # Load JSON configuration files
        if patterns_dir.exists():
            self.common_helpers.load_json_files(str(patterns_dir))
        else:
            print(f"{self.ansi_colors.YELLOW}Warning: Patterns directory not found at {patterns_dir}{self.ansi_colors.RESET}")
            
        if constants_dir.exists():
            self.common_helpers.load_json_files(str(constants_dir))
        else:
            print(f"{self.ansi_colors.YELLOW}Warning: Constants directory not found at {constants_dir}{self.ansi_colors.RESET}")
        
        # Initialize helpers
        self.crawler_helpers = CrawlerHelpers()

    async def get_crawler(self, config):
        """Create crawler instance with the given configuration"""
        try:
            authentication_helpers = AuthenticationHelpers(config)
            authentication = Authentication(authentication_helpers)
            crawler = Crawler(authentication, config, self.crawler_helpers, self.common_helpers)
            return crawler
        except Exception as e:
            print(f"{self.ansi_colors.RED}Error creating crawler: {e}{self.ansi_colors.RESET}")
            return None

    def get_loaded_data_info(self):
        """Get information about loaded JSON data"""
        loaded_files = list(self.common_helpers.json_data.keys())
        if loaded_files:
            print(f"{self.ansi_colors.GREEN}Loaded configuration files:{self.ansi_colors.RESET}")
            for filename in loaded_files:
                print(f"  - {filename}")
        else:
            print(f"{self.ansi_colors.YELLOW}No configuration files loaded{self.ansi_colors.RESET}")
        return loaded_files