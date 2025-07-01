import re
import os
from urllib.parse import urlparse

class ScanHelpers:
    def __init__(self, common_helpers, ansi_colors, report_generator):
        self.common_helpers = common_helpers
        self.patterns = self.common_helpers.get_json_data('patterns.json')
        self.ansi_colors = ansi_colors
        self.report_generator = report_generator

    def process_api_args(self, args):
        metadata = self.common_helpers.get_json_data(f'{args["scantype"]}_metadata.json')
        payloads = self.common_helpers.get_json_data(f'{args["scantype"]}_payloads.json')

        if args["auth"] == 1:
            use_auth = True
            scan_type = args["scantype"]
            entrypoint = args["entrypoint"]
            login_url = args["loginurl"]
            if not self.is_valid_url(login_url):
                print(f"{self.ansi_colors.RED}Entered value is not a valid URL.{self.ansi_colors.RESET}")
                return None
            username = args["username"]
            password = args["password"]
            filepath = args["filepath"]
            tests = args["tests"]
            self.print_selected_tests(scan_type, metadata, tests)

        elif args["auth"] == 2:
            if args["loginurl"] or args["username"] or args["password"]:
                print(f"{self.ansi_colors.RED}You cannot set auth to 2 (scan without authentication) and use loginurl, username, or password.{self.ansi_colors.RESET}")
                return None

            use_auth = False
            scan_type = args["scantype"]
            entrypoint = args["entrypoint"]
            if not self.is_valid_url(entrypoint):
                print(f"{self.ansi_colors.RED}Entered value is not a valid URL.{self.ansi_colors.RESET}")
                return None

            login_url = None
            username = str(self.common_helpers.random_token())
            password = str(self.common_helpers.random_token())
            filepath = None
            tests = args["tests"]
            self.print_selected_tests(scan_type, metadata, tests)

        else:
            print(f"{self.ansi_colors.RED}Invalid scan type. Please choose auth 1 or 2.{self.ansi_colors.RESET}")
            return None

        return (
            use_auth,
            scan_type,
            login_url,
            username,
            password,
            filepath,
            entrypoint,
            tests,
            metadata,
            payloads,
        )

    def print_selected_tests(self, scan_type, metadata, tests):
        scan_types = {"inspection": "INSPECTION SCAN", "exploitation": "EXPLOITATION SCAN"}

        print(f"\n{self.ansi_colors.BLUE}{scan_types[scan_type]}{self.ansi_colors.RESET}")
        selected_tests = self.get_selected_tests(tests, metadata)
        print(f"\n{self.ansi_colors.BLUE}   Selected Tests:{self.ansi_colors.RESET}\n")
        for test in selected_tests:
            print(f"    {self.ansi_colors.GREEN} - {test}{self.ansi_colors.RESET}")

    def is_valid_url(self, url):
        return re.match(self.patterns["url_validation_regex"], url, re.IGNORECASE) is not None

    def process_file(self, filepath, urls):
        if os.path.exists(filepath):
            with open(filepath, "r") as file:
                urls = [
                    line.strip() for line in file if self.is_valid_url(line.strip())
                ]
        else:
            print(f"{self.ansi_colors.RED}File not found: {filepath}{self.ansi_colors.RESET}")
        return urls

    def determine_base_url_and_starting_point(self, entrypoint, urls, login_url):
        if entrypoint:
            base_url = self.pull_base_url(entrypoint)
            starting_point = [entrypoint]
        elif urls:
            base_url = self.pull_base_url(
                urls[0]
            )
            starting_point = urls
        else:
            base_url = self.pull_base_url(login_url)
            starting_point = [base_url]
        return base_url, starting_point

    def pull_base_url(self, url):
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    def get_selected_tests(self, tests, metadata):
        test_mapping = {test_info["test_id"]: test_info["test_name"] for test_info in metadata.values()}
        return [test_mapping[test] for test in tests if test in test_mapping]

    def scan_results(self, tests_results, base_url, minutes, seconds):
        html_report, total_vulnerabilities = self.report_generator.generate_html_report(
            tests_results, base_url
        )

        report_file_name = (
            base_url.replace("http://", "").replace("https://", "").replace("/", "_")
            + ".html"
        )
        with open(report_file_name, "w") as file:
            file.write(html_report)

        print(self.common_helpers.decorate_string(f"Results for: ({base_url})"))

        print(
            f"{self.ansi_colors.BLUE}Total Vulnerabilities: {self.ansi_colors.RESET}{self.ansi_colors.RED}{total_vulnerabilities}{self.ansi_colors.RESET}\n"
        )

        total_time = int(minutes) * 60 + int(seconds)
        print(
            f"    {self.ansi_colors.BLUE}Tests Execution Time: {self.ansi_colors.RESET}{self.ansi_colors.RED}{total_time // 60} min, {total_time % 60} sec{self.ansi_colors.RESET}"
        )

        return report_file_name
