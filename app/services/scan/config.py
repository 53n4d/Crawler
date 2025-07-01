class ScanConfig:
    def __init__(self, scan_helpers, ansi_colors):
        self.scan_helpers = scan_helpers
        self.ansi_colors = ansi_colors

    async def run(self, args):
        urls = []

        (
            use_auth,
            scan_type,
            login_url,
            username,
            password,
            filepath,
            entrypoint,
            tests,
            metadata,
            payloads
        ) = self.scan_helpers.process_api_args(args)

        if filepath:
            urls = self.scan_helpers.process_file(filepath, urls)
            print(f"\n{self.ansi_colors.BLUE}URLs from file:{self.ansi_colors.RESET}\n")
            if urls:
                for url in urls:
                    print(f"    {self.ansi_colors.GREEN} - {url}{self.ansi_colors.RESET}")
            else:
                print(f"{self.ansi_colors.RED}No valid URLs found in the file.{self.ansi_colors.RESET}")

        base_url, starting_point = (
            self.scan_helpers.determine_base_url_and_starting_point(
                entrypoint, urls, login_url
            )
        )

        return {
            "use_auth": use_auth,
            "scan_type": scan_type,
            "login_url": login_url,
            "username": username,
            "password": password,
            "filepath": filepath,
            "entrypoint": entrypoint,
            "base_url": base_url,
            "starting_point": starting_point,
            "tests": tests,
            "metadata": metadata,
            "payloads": payloads,
            "urls": urls,  # this should put in use
        }
