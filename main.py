#!/usr/bin/env python3
"""
Web Application Crawler - Command Line Interface
Usage: python3 main.py [OPTIONS]
"""

import argparse
import asyncio
import sys
import time
import json
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.services.dependencies import DependencyManager
from app.common.ansi_colors import ANSIColors


class WebCrawler:
    def __init__(self):
        self.ansi_colors = ANSIColors()
        self.dependency_manager = DependencyManager()
    
    def print_banner(self):
        """Print application banner"""
        banner = f"""
{self.ansi_colors.CYAN}
 ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗ 
██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗
██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝
██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗
╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
{self.ansi_colors.RESET}
{self.ansi_colors.BLUE}Web Application Crawler{self.ansi_colors.RESET}
{self.ansi_colors.GREEN}Command Line Interface{self.ansi_colors.RESET}
"""
        print(banner)

    def create_parser(self):
        """Create and configure argument parser"""
        parser = argparse.ArgumentParser(
            description="Web Application Crawler",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Crawl with authentication
  python3 main.py --auth --loginurl https://example.com/login \\
                  --username admin --password password123 --entrypoint https://example.com/dashboard

  # Crawl without authentication
  python3 main.py --entrypoint https://example.com

  # Crawl URLs from file with authentication
  python3 main.py --auth --loginurl https://example.com/login \\
                  --username admin --password password123 --filepath urls.txt

  # Crawl with output to specific directory
  python3 main.py --entrypoint https://example.com --output ./crawl_results
            """
        )

        # Authentication flag
        parser.add_argument(
            "--auth",
            action="store_true",
            help="Enable authentication mode"
        )

        # Authentication arguments (required when --auth is used)
        auth_group = parser.add_argument_group("Authentication (required when --auth is used)")
        auth_group.add_argument(
            "--loginurl",
            help="Login URL for authentication"
        )
        auth_group.add_argument(
            "--username",
            help="Username for authentication"
        )
        auth_group.add_argument(
            "--password",
            help="Password for authentication"
        )

        # Target specification (one required)
        target_group = parser.add_argument_group("Target specification (choose one)")
        target_group.add_argument(
            "--entrypoint",
            help="Single entry point URL to start crawling"
        )
        target_group.add_argument(
            "--filepath",
            help="Path to file containing URLs to crawl"
        )

        # Optional arguments
        parser.add_argument(
            "--output",
            help="Output directory for crawl results (default: current directory)"
        )

        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )

        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Suppress non-essential output"
        )

        parser.add_argument(
            "--format",
            choices=["json", "txt"],
            default="json",
            help="Output format for crawl results (default: json)"
        )

        return parser

    def validate_args(self, args):
        """Validate command line arguments"""
        errors = []

        # Validate authentication requirements
        if args.auth:
            if not all([args.loginurl, args.username, args.password]):
                errors.append("--loginurl, --username, and --password are required when --auth is used")
        
        # Must have either entrypoint or filepath
        if not args.entrypoint and not args.filepath:
            errors.append("Must specify either --entrypoint or --filepath")
        
        if args.entrypoint and args.filepath:
            errors.append("Cannot specify both --entrypoint and --filepath")

        # Validate file existence
        if args.filepath and not Path(args.filepath).exists():
            errors.append(f"File not found: {args.filepath}")

        # Validate URLs
        if args.entrypoint and not self._is_valid_url(args.entrypoint):
            errors.append(f"Invalid entrypoint URL: {args.entrypoint}")
        
        if args.auth and args.loginurl and not self._is_valid_url(args.loginurl):
            errors.append(f"Invalid login URL: {args.loginurl}")

        return errors

    def _is_valid_url(self, url):
        """Basic URL validation"""
        return url and (url.startswith('http://') or url.startswith('https://'))

    def prepare_config(self, args):
        """Convert command line arguments to crawler configuration"""
        config = {
            "use_auth": args.auth,
            "login_url": args.loginurl if args.auth else None,
            "username": args.username if args.auth else "anonymous",
            "password": args.password if args.auth else "anonymous",
            "entrypoint": args.entrypoint,
            "filepath": args.filepath,
            "output": args.output or ".",
            "verbose": args.verbose,
            "quiet": args.quiet,
            "format": args.format
        }

        # Determine base URL and starting points
        if args.entrypoint:
            from urllib.parse import urlparse
            parsed = urlparse(args.entrypoint)
            config["base_url"] = f"{parsed.scheme}://{parsed.netloc}"
            config["starting_point"] = [args.entrypoint]
        elif args.filepath:
            # Will be processed later to extract URLs
            config["base_url"] = None
            config["starting_point"] = []

        return config

    async def process_urls_from_file(self, filepath):
        """Process URLs from file"""
        urls = []
        try:
            with open(filepath, 'r') as file:
                for line in file:
                    url = line.strip()
                    if url and self._is_valid_url(url):
                        urls.append(url)
                    elif url:
                        print(f"{self.ansi_colors.YELLOW}Skipping invalid URL: {url}{self.ansi_colors.RESET}")
        except Exception as e:
            print(f"{self.ansi_colors.RED}Error reading file {filepath}: {e}{self.ansi_colors.RESET}")
            return []

        if urls:
            print(f"{self.ansi_colors.GREEN}Loaded {len(urls)} valid URLs from file{self.ansi_colors.RESET}")
        else:
            print(f"{self.ansi_colors.RED}No valid URLs found in file{self.ansi_colors.RESET}")

        return urls

    def save_results(self, results, config):
        """Save crawling results to file"""
        output_dir = Path(config["output"])
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename based on base URL or timestamp
        if config["base_url"]:
            base_name = config["base_url"].replace("http://", "").replace("https://", "").replace("/", "_")
        else:
            base_name = f"crawl_{int(time.time())}"
        
        if config["format"] == "json":
            output_file = output_dir / f"{base_name}_crawl_results.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        else:
            output_file = output_dir / f"{base_name}_crawl_results.txt"
            with open(output_file, 'w') as f:
                f.write("=== WEB CRAWLER RESULTS ===\n\n")
                f.write(f"Base URL: {config.get('base_url', 'N/A')}\n")
                f.write(f"Starting Points: {', '.join(config.get('starting_point', []))}\n")
                f.write(f"Crawl Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"Pages Discovered: {len(results.get('pages_to_test', []))}\n")
                for page in results.get('pages_to_test', []):
                    f.write(f"  - {page}\n")
                
                f.write(f"\nElements Detected: {len(results.get('detected_elements', []))}\n")
                f.write(f"Input Elements: {len(results.get('detected_input_elements', []))}\n")
                f.write(f"Requests Captured: {len(results.get('requests', []))}\n")
                f.write(f"Static Requests: {len(results.get('static_requests', []))}\n")

        return output_file

    async def run_crawl(self, config):
        """Execute the web crawling"""
        start_time = time.time()
        
        try:
            if not config["quiet"]:
                print(f"\n{self.ansi_colors.BLUE}Initializing crawler...{self.ansi_colors.RESET}")

            # Process file URLs if needed
            if config["filepath"]:
                urls = await self.process_urls_from_file(config["filepath"])
                if not urls:
                    return False
                
                # Set base URL from first URL
                from urllib.parse import urlparse
                parsed = urlparse(urls[0])
                config["base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                config["starting_point"] = urls

            # Get crawler instance
            crawler = await self.dependency_manager.get_crawler(config)
            if not crawler:
                print(f"{self.ansi_colors.RED}Failed to initialize crawler{self.ansi_colors.RESET}")
                return False

            if not config["quiet"]:
                print(f"{self.ansi_colors.GREEN}Crawler initialized successfully{self.ansi_colors.RESET}")
                print(f"\n{self.ansi_colors.BLUE}Starting crawl of: {config['base_url']}{self.ansi_colors.RESET}")
                print(f"{self.ansi_colors.BLUE}Entry points: {len(config['starting_point'])}{self.ansi_colors.RESET}")

            # Run the crawler
            crawling_results = await self.dependency_manager.common_helpers.run_crawler(crawler)
            
            if not crawling_results:
                print(f"{self.ansi_colors.RED}Crawling failed - no results obtained{self.ansi_colors.RESET}")
                return False

            # Calculate execution time
            total_time = time.time() - start_time
            minutes, seconds = divmod(total_time, 60)

            # Display results summary
            if not config["quiet"]:
                print(f"\n{self.ansi_colors.GREEN}Crawling completed successfully!{self.ansi_colors.RESET}")
                print(f"\n{self.ansi_colors.BLUE}=== CRAWL SUMMARY ==={self.ansi_colors.RESET}")
                print(f"  • Pages discovered: {self.ansi_colors.GREEN}{len(crawling_results.get('pages_to_test', []))}{self.ansi_colors.RESET}")
                print(f"  • Elements detected: {self.ansi_colors.GREEN}{len(crawling_results.get('detected_elements', []))}{self.ansi_colors.RESET}")
                print(f"  • Input elements: {self.ansi_colors.GREEN}{len(crawling_results.get('detected_input_elements', []))}{self.ansi_colors.RESET}")
                print(f"  • Requests captured: {self.ansi_colors.GREEN}{len(crawling_results.get('requests', []))}{self.ansi_colors.RESET}")
                print(f"  • Static requests: {self.ansi_colors.GREEN}{len(crawling_results.get('static_requests', []))}{self.ansi_colors.RESET}")
                print(f"  • Execution time: {self.ansi_colors.GREEN}{int(minutes)}m {int(seconds)}s{self.ansi_colors.RESET}")

            # Save results
            try:
                output_file = self.save_results(crawling_results, config)
                if not config["quiet"]:
                    print(f"\n{self.ansi_colors.BLUE}Results saved to: {self.ansi_colors.GREEN}{output_file}{self.ansi_colors.RESET}")
            except Exception as e:
                print(f"{self.ansi_colors.YELLOW}Warning: Could not save results to file: {e}{self.ansi_colors.RESET}")

            # Optionally show some discovered pages
            if config["verbose"] and crawling_results.get('pages_to_test'):
                print(f"\n{self.ansi_colors.BLUE}Discovered Pages:{self.ansi_colors.RESET}")
                for i, page in enumerate(crawling_results['pages_to_test'][:10]):  # Show first 10
                    print(f"  {i+1:2}. {page}")
                if len(crawling_results['pages_to_test']) > 10:
                    print(f"  ... and {len(crawling_results['pages_to_test']) - 10} more")

            return True

        except KeyboardInterrupt:
            print(f"\n{self.ansi_colors.YELLOW}Crawl interrupted by user{self.ansi_colors.RESET}")
            return False
        except Exception as e:
            print(f"\n{self.ansi_colors.RED}Crawl failed with error: {str(e)}{self.ansi_colors.RESET}")
            if config["verbose"]:
                import traceback
                print(f"{self.ansi_colors.YELLOW}Traceback:{self.ansi_colors.RESET}")
                traceback.print_exc()
            return False

    def run(self):
        """Main entry point"""
        # Print banner
        if not any(arg in sys.argv for arg in ['--quiet', '-q']):
            self.print_banner()

        # Parse arguments
        parser = self.create_parser()
        args = parser.parse_args()

        # Validate arguments
        errors = self.validate_args(args)
        if errors:
            print(f"{self.ansi_colors.RED}Validation errors:{self.ansi_colors.RESET}")
            for error in errors:
                print(f"  • {error}")
            print(f"\n{self.ansi_colors.BLUE}Use --help for usage information{self.ansi_colors.RESET}")
            sys.exit(1)

        # Prepare configuration
        config = self.prepare_config(args)

        # Run the crawl
        try:
            success = asyncio.run(self.run_crawl(config))
            sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            print(f"\n{self.ansi_colors.YELLOW}Interrupted by user{self.ansi_colors.RESET}")
            sys.exit(130)


def main():
    """Entry point for the application"""
    crawler = WebCrawler()
    crawler.run()


if __name__ == "__main__":
    main()