import json
import logging
import os
import random
import shutil
import string
import sys
import time
import asyncio
from alive_progress import alive_bar
from playwright.async_api import async_playwright


class CommonHelpers:
    def __init__(self, ansi_colors):
        self.json_data = {}
        self.ansi_colors = ansi_colors

    @staticmethod
    async def display_elapsed_time(start_time):
        while True:
            elapsed_time = time.time() - start_time
            minutes, seconds = divmod(elapsed_time, 60)
            print(f"\rElapsed time: {int(minutes)} minutes, {int(seconds)} seconds", end="")
            await asyncio.sleep(1)

    def decorate_string(self, title):
        term_width, _ = shutil.get_terminal_size()
        title_line = f"\033[1m\033[37m{title.center(term_width-4)}\033[0m"
        border_line = f"\n{self.ansi_colors.CYAN}{'=' * term_width}{self.ansi_colors.RESET}\n{title_line}\n{self.ansi_colors.CYAN}{'=' * term_width}{self.ansi_colors.RESET}\n"
        return border_line

    @staticmethod
    def remove_pycache():
        for dirpath, dirnames, _ in os.walk(os.getcwd()):
            for dirname in dirnames:
                if dirname == "__pycache__":
                    pycache_dir = os.path.join(dirpath, dirname)
                    shutil.rmtree(pycache_dir)

    @staticmethod
    def get_burp_data(file_path):
        with open(file_path, "r") as file:
            requests = json.loads(file.read())

        urls = set()
        page_urls = set()
        methods = set()
        headers = set()
        post_data = set()
        has_login = set()
        attack_types = set()

        for request in requests:
            urls.add(request.get("url", ""))
            page_urls.add(request.get("page_url", ""))
            methods.add(request.get("method", ""))
            headers.update(request.get("headers", {}).items())
            post_data.add(request.get("post_data", ""))
            has_login.add(request.get("has_login", False))
            attack_types.update(request.get("attack_types", []))

        return {
            "urls": urls,
            "page_urls": page_urls,
            "methods": methods,
            "headers": headers,
            "post_data": post_data,
            "has_login": has_login,
            "attack_types": attack_types,
        }

    @staticmethod
    def log_message(level, message):
        logging.basicConfig(
            filename="error_log.log",
            level=logging.DEBUG,  # Change this to DEBUG to capture all log levels
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        # Adding StreamHandler to print logs to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(console_handler)
        logger = logging.getLogger()

        if level == "debug":
            logger.debug(message)
        elif level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        elif level == "critical":
            logger.critical(message)
        else:
            logger.info(message) 



    @staticmethod
    def random_string(length=10):
        return "".join(random.choices(string.ascii_letters, k=length))

    @staticmethod
    def random_token(length=10):
        return str(random.randint(10 ** (length - 1), 10**length - 1))

    @staticmethod
    async def replace_with_payload(data, payload_template, single_inserted_value):
        modified = False
        key_payload_data = []
        tokens = []
        if isinstance(data, dict):
            for key in data.keys():
                if isinstance(data[key], (dict, list)):
                    data[key], was_modified, nested_key_payload, nested_tokens = (
                        await CommonHelpers.replace_with_payload(
                            data[key], payload_template, single_inserted_value
                        )
                    )
                    if was_modified:
                        modified = True
                        key_payload_data.extend(nested_key_payload)
                        tokens.extend(nested_tokens)
                elif (
                    data[key] == single_inserted_value
                ):  # Instead of using 'in', we're checking for direct equality
                    token = str(CommonHelpers.random_token())
                    payload = payload_template.replace("TOKEN", token)
                    data[key] = payload
                    key_payload_data.append({key: payload})
                    tokens.append({key: token})
                    modified = True
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                if item == single_inserted_value:
                    token = str(CommonHelpers.random_token())
                    payload = payload_template.replace("TOKEN", token)
                    data[idx] = payload
                    key_payload_data.append({idx: payload})
                    tokens.append({idx: token})
                    modified = True
                else:
                    data[idx], was_modified, nested_key_payload, nested_tokens = (
                        await CommonHelpers.replace_with_payload(
                            item, payload_template, single_inserted_value
                        )
                    )
                    if was_modified:
                        modified = True
                        key_payload_data.extend(nested_key_payload)
                        tokens.extend(nested_tokens)

        return data, modified, key_payload_data, tokens

    @staticmethod
    async def replace_substring_in_value(
        value, single_inserted_value, payload_template
    ):
        token = None
        if single_inserted_value in value:
            token = str(CommonHelpers.random_token())
            payload = payload_template.replace("TOKEN", token)
            value = value.replace(single_inserted_value, payload)

        return value, token

    @staticmethod
    async def initialize_playwright(browser_type="chromium"):
        print("Starting Playwright")
        try:
            playwright = await async_playwright().start()
            print("Playwright started")

            if browser_type == "chromium":
                print("Creating Chromium Browser")
                browser = await playwright.chromium.launch(headless=False)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
                    viewport={"width": 1920, "height": 1080},
                )
            elif browser_type == "firefox":
                print("Creating Firefox Browser")
                browser = await playwright.firefox.launch(headless=False)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
                    viewport={"width": 1920, "height": 1080},
                )
            else:
                raise ValueError(
                    "Invalid browser type. Choose 'chromium' or 'firefox'."
                )

            print("Browser and context created")
            return playwright, context, browser
        except Exception as e:
            print(f"Error in initialize_playwright: {e}")
            raise

    async def run_crawler(self, crawler_instance):
        print("Starting Crawler")
        playwright, context, browser = await CommonHelpers.initialize_playwright(
            browser_type="firefox"
        )

        print(f"\n{self.ansi_colors.color_text('Crawling:', self.ansi_colors.BLUE)} {self.ansi_colors.color_text('In progress...', self.ansi_colors.GREEN)}\n")
        crawler_task = asyncio.create_task(crawler_instance.run(context))

        with alive_bar() as bar:
            while not crawler_task.done():
                bar()
                await asyncio.sleep(0.1)
            crawling_results = await crawler_task
            bar()  # Update the progress bar one last time to ensure it's complete

        print(f"\n{self.ansi_colors.color_text('Crawling:', self.ansi_colors.BLUE)} {self.ansi_colors.color_text('Done!', self.ansi_colors.GREEN)}\n")
        await context.close()
        await browser.close()
        await playwright.stop()

        return crawling_results

    async def get_new_headers(self, context, use_auth, auth_obj, login_url, username, password):
        if use_auth:
            page = await context.new_page()
            new_headers = await auth_obj(
                page,
                login_url,
                username,
                password,
            )
            await page.close()
            return new_headers

    async def run_tests(self, tests_instance):
        starts_tests_time = time.time()
        print(f"\n{self.ansi_colors.color_text('Testing:', self.ansi_colors.BLUE)} {self.ansi_colors.color_text('In progress...', self.ansi_colors.GREEN)}\n")

        tests_task = asyncio.create_task(tests_instance.run())

        with alive_bar() as bar:
            while not tests_task.done():
                bar()
                await asyncio.sleep(0.1)
            tests_results = await tests_task
            bar()  # Update the progress bar one last time to ensure it's complete

        print(f"\n{self.ansi_colors.color_text('Testing:', self.ansi_colors.BLUE)} {self.ansi_colors.color_text('Done!', self.ansi_colors.GREEN)}\n")
        total_time = time.time() - starts_tests_time
        minutes, seconds = divmod(total_time, 60)

        return tests_results, minutes, seconds

    def load_json_files(self, base_path):
        for filename in os.listdir(base_path):
            if filename.endswith('.json'):
                path = os.path.join(base_path, filename)
                try:
                    with open(path, 'r') as file:
                        self.json_data[filename] = json.load(file)
                    print(f"Data loaded successfully from {path}.")
                except Exception as e:
                    print(f"Failed to load data from {path}: {e}")
    
    def get_json_data(self, filename):
        return self.json_data.get(filename, {})