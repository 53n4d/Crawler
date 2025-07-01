import os
import asyncio

from ..services.scan.config import ScanConfig
from ..services.authentication.authentication import Authentication
from ..services.crawler.crawler import Crawler
from ..services.crawler.helpers import CrawlerHelpers
from ..common.helpers import CommonHelpers
from ..services.scan.helpers import ScanHelpers 
from ..services.scan.report import ReportGenerator
from ..services.authentication.helpers import AuthenticationHelpers
from ..common.ansi_colors import ANSIColors


class DependencyManager:
    def __init__(self):
        self.ansi_colors = ANSIColors
        self.common_helpers = CommonHelpers(self.ansi_colors)
        self.common_helpers.load_json_files("/home/xseverity/Desktop/dynex/app/common/metadata")
        self.common_helpers.load_json_files("/home/xseverity/Desktop/dynex/app/common/patterns")
        self.common_helpers.load_json_files("/home/xseverity/Desktop/dynex/app/common/constants")
        self.report_generator = ReportGenerator
        self.crawler_helpers = CrawlerHelpers
        self.scan_helpers = ScanHelpers(self.common_helpers, self.ansi_colors, self.report_generator)
        self.scan_config = ScanConfig(self.scan_helpers, self.ansi_colors)

    async def get_scan_config(self, args): 
        if args:
            config = await self.scan_config.run(args)
            return config
    
    async def get_crawler(self, config):
        authentication_helpers = AuthenticationHelpers(config)
        authentication = Authentication(authentication_helpers)
        crawler = Crawler(authentication, config, self.crawler_helpers, self.common_helpers)
        return crawler
    
    async def get_results():
        print('results')
        
