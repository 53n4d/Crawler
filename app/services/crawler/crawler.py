from urllib.parse import urljoin, urlparse, parse_qs
import asyncio
import json
import base64
import re
import logging


class Crawler:
    pages_to_test = []
    requests = []
    static_requests = []
    responses = []
    static_responses = []
    detected_elements = []
    detected_input_elements = []
    encountered_urls = set()
    encountered_responses = set()
    filled_values = {}
    crawling_results = {}

    def __init__(self, authentication, config, crawler_helpers, common_helpers):
        self.authentication = authentication
        self.crawler_helpers = crawler_helpers
        self.common_helpers = common_helpers
        self.use_auth = config["use_auth"]
        self.username = config["username"]
        self.password = config["password"]
        self.base_url = config["base_url"]
        self.pages_to_visit = config["starting_point"]
        self.constants = self.common_helpers.get_json_data('constants.json')
        self.user_param_names = self.constants["user_param_names"]
        self.password_param_names = self.constants["password_param_names"]
        self.new_popup_page = None

        self.skip_extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".svg",
            ".ico",
            ".css",
            ".js",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".woff",
            ".woff2",
            ".json",
        )

        self.avoid_pages = [
            "phpinfo",
            "swagger",
            "security.php",
            "about",
            "setup.php",
            "start_over",
            "difficulty/hard",
            "socket",
        ]

    async def run(self, context):
        self.domain = urlparse(self.base_url).netloc
        page = await context.new_page()

        page.on("popup", self.capture_new_page)
        page.on(
            "response",
            lambda response: asyncio.create_task(
                self.log_and_continue_response(
                    response, self.domain, self.encountered_responses
                )
            ),
        )
        page.on(
            "request",
            lambda request: asyncio.create_task(
                self.log_and_continue_request(
                    page,
                    request,
                    self.domain,
                    self.encountered_urls,
                    self.user_param_names,
                    self.password_param_names,
                )
            ),
        )

        try:
            if self.use_auth:
                await self.authentication.run(page)

            for index, one_page in enumerate(self.pages_to_visit):
                if self.should_skip(one_page, self.skip_extensions):
                    logging.info(f"Skipping {one_page} due to its extension.")
                    continue

                if any(page_to_avoid in one_page for page_to_avoid in self.avoid_pages):
                    logging.info(f"Skipping {one_page} due to your requirement.")
                    continue

                try:
                    await page.goto(one_page, timeout=30000)
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    logging.error(f"Failed to navigate to {one_page}, skipping... Error: {e}")
                    continue

                current_url = page.url
                if current_url != one_page:
                    if self.use_auth:
                        if index > 1 and index == len(self.pages_to_visit) - 1:
                            self.pages_to_visit.append(self.base_url)
                        await self.authentication.run(page)
                        await page.goto(one_page, timeout=30000)
                        await page.wait_for_load_state("networkidle")

                if self.base_url not in current_url:
                    logging.info(f"Skipping {one_page} due to {self.base_url} check.")
                    continue

                self.pages_to_test.append(one_page)

                self.detected_elements, self.detected_input_elements = (
                    await self.crawler_helpers.detection_cl_elements(
                        page, self.detected_elements, self.detected_input_elements
                    )
                )
                logging.info(self.detected_elements)
                await self.start_clicking(
                    page, self.username, self.password, self.base_url
                )

                if self.new_popup_page:
                    await self.new_popup_page.wait_for_load_state("networkidle")
                    if self.new_popup_page.url not in self.pages_to_visit:
                        self.pages_to_visit.append(self.new_popup_page.url)
                    await self.new_popup_page.close()
                    self.new_popup_page = None

        except Exception as e:
            logging.error(f"Error during crawling: {e}\n")

        await page.close()
        crawling_results = {
            "pages_to_test": self.pages_to_test,
            "detected_elements": self.detected_elements,
            "detected_input_elements": self.detected_input_elements,
            "requests": self.requests,
            "static_requests": self.static_requests,
            "responses": self.responses,
            "static_responses": self.static_responses,
        }

        return crawling_results

    async def capture_new_page(self, popup):
        self.new_popup_page = popup
        if self.new_popup_page:
            await self.new_popup_page.wait_for_load_state("networkidle")
            if self.new_popup_page.url not in self.pages_to_visit:
                self.pages_to_visit.append(self.new_popup_page.url)
            await popup.close()
            self.new_popup_page = None

    async def log_and_continue_response(self, response, domain, encountered_responses):
        response_domain = urlparse(response.url).netloc
        if response_domain == domain:
            method = response.request.method
            if (response.url, response.status, method) not in encountered_responses:
                encountered_responses.add((response.url, response.status, method))
                all_headers = await response.all_headers()
                headers_dict = {
                    header: value
                    for header, value in all_headers.items()
                    if not header.startswith(":")
                }
                response_info = {
                    "request_method": method,
                    "url": response.url,
                    "status": response.status,
                    "headers": headers_dict,
                }
                if 300 <= response.status < 400:
                    response_info["body"] = "Redirect response"
                    logging.info(f"Redirect response for {response.url}")
                else:
                    try:
                        content_type = headers_dict.get("content-type", "")
                        if any(
                            substring in content_type
                            for substring in ["text", "json", "application"]
                        ):
                            response_info["body"] = await response.text()
                            logging.info(f"Retrieved text response for {response.url}")
                        elif (
                            "image" in content_type
                            or "audio" in content_type
                            or "video" in content_type
                        ):
                            binary_data = await response.body()
                            base64_encoded_data = base64.b64encode(binary_data).decode("utf-8")
                            response_info["body"] = base64_encoded_data
                            logging.info(f"Retrieved binary response for {response.url}")
                        else:
                            try:
                                response_info["body"] = await response.text()
                                logging.info(f"Retrieved other text response for {response.url}")
                            except UnicodeDecodeError:
                                binary_data = await response.body()
                                response_info["body"] = base64.b64encode(binary_data).decode("utf-8")
                                logging.info(f"Retrieved binary response for {response.url} after text decode failure")

                        f_pattern = re.compile(r"(/[\w/]*(?:bla\.txt|bla\.txt.jpg))")
                        match_file = f_pattern.findall(response_info["body"])
                        if match_file:
                            for f_match in match_file:
                                file_url = urljoin(self.base_url, f_match)
                                if file_url not in self.pages_to_visit:
                                    self.pages_to_visit.append(file_url)
                                    logging.info(f"Found and added file URL: {file_url}")
                    except Exception as e:
                        logging.error(f"Failed to retrieve response body for {response.url}: {e}")
                        response_info["body"] = "Failed to retrieve response body"

                (
                    self.static_responses.append(json.dumps(response_info))
                    if self.should_skip(response.url, self.skip_extensions)
                    else self.responses.append(json.dumps(response_info))
                )
                logging.info(f"Logged response for {response.url}")

    def check_for_password_keys(self, data, user_param_names, password_param_names):
        if len(data) > 5 or len(data) < 2:
            return False

        password_count = 0
        for key in data:
            if any(user_string in key for user_string in user_param_names):
                continue
            if any(password_string in key for password_string in password_param_names):
                password_count += 1

        return password_count == 1

    async def log_and_continue_request(
        self,
        page,
        request,
        domain,
        encountered_urls,
        user_param_names,
        password_param_names,
    ):
        inserted_values = []
        inserted_files = []
        inserted_file_value = ["test file crawler pointer"]

        try:
            request_domain = urlparse(request.url).netloc
            if request_domain == domain:
                parsed_url = urlparse(request.url)
                query_parameters = parsed_url.query
                parameter_names = [
                    param.split("=")[0] for param in query_parameters.split("&")
                ]
                post_data = request.post_data
                filled_values_list = list(self.filled_values.values())

                url_tuple = (
                    parsed_url.scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    request.method,
                    tuple(parameter_names),
                    post_data,
                )

                if url_tuple not in encountered_urls:
                    encountered_urls.add(url_tuple)

                    try:
                        all_headers = await request.all_headers()
                    except Exception as e:
                        logging.error(f"Error fetching headers for {request.url}: {e}")
                        return

                    headers_dict = {
                        header: value
                        for header, value in all_headers.items()
                        if not header.startswith(":")
                    }

                    has_password = False
                    if post_data is not None:
                        try:
                            json_data = json.loads(post_data)
                            has_password = self.check_for_password_keys(
                                json_data, user_param_names, password_param_names
                            )
                        except json.JSONDecodeError:
                            parsed_post_data = parse_qs(post_data)
                            has_password = self.check_for_password_keys(
                                parsed_post_data, user_param_names, password_param_names
                            )

                    url_query = parse_qs(urlparse(request.url).query)
                    has_password |= self.check_for_password_keys(
                        url_query, user_param_names, password_param_names
                    )

                    request_info = {
                        "url": request.url,
                        "page_url": page.url,
                        "method": request.method,
                        "headers": headers_dict,
                        "post_data": post_data,
                        "has_login": has_password,
                    }

                    for filled_v in filled_values_list:
                        if post_data:
                            if filled_v in post_data:
                                if filled_v.endswith(".txt") or filled_v.endswith(
                                    ".jpg"
                                ):
                                    inserted_files.append(filled_v)
                                else:
                                    inserted_values.append(filled_v)
                            elif filled_v in request.url:
                                if filled_v.endswith(".txt") or filled_v.endswith(
                                    ".jpg"
                                ):
                                    inserted_files.append(filled_v)
                                else:
                                    inserted_values.append(filled_v)
                        else:
                            if filled_v in request.url:
                                if filled_v.endswith(".txt") or filled_v.endswith(
                                    ".jpg"
                                ):
                                    inserted_files.append(filled_v)
                                else:
                                    inserted_values.append(filled_v)

                    if inserted_values:
                        request_info["inserted_values"] = inserted_values
                    elif inserted_files:
                        request_info["inserted_files"] = inserted_files
                        request_info["inserted_file_value"] = inserted_file_value
                    (
                        self.static_requests.append(json.dumps(request_info))
                        if self.should_skip(request.url, self.skip_extensions)
                        else self.requests.append(json.dumps(request_info))
                    )
                    self.filled_values.clear()
        except Exception as e:
            logging.error(f"Error in task: {e}")

    async def process_element(self, page, el, base_url, parent_sel_path=None):
        check_again = True
        viewport_size = page.viewport_size
        screen_width = viewport_size["width"]
        screen_height = viewport_size["height"]
        center_x = screen_width - 10  # Bottom-right corner
        center_y = screen_height - 10

        selector_path = el["selectorPath"]

        async def try_click(selector):
            try:
                test = page.locator(selector)
                await test.scroll_into_view_if_needed()
                await asyncio.sleep(0.1)
                await test.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(0.5)
                return True
            except Exception as e:
                logging.error(f"Error clicking {selector}: {e}")
                return False

        async def check_and_click(selector):
            elements = await page.query_selector_all(selector)
            if len(elements) > 1:
                if "innerHTML" in el and not any(char in el["innerHTML"] for char in ["<", ">"]):
                    selector += f":has-text('{el['innerHTML']}')"
            return await try_click(selector)

        try:
            if el["href"].strip() != "":
                el["clicked"] = "yes"
                if not el["href"].startswith("#") and el["href"] and not urlparse(el["href"]).scheme:
                    href = urljoin(el["currentUrl"], el["href"])
                    if href not in self.pages_to_visit:
                        self.pages_to_visit.append(href)
                elif el["href"].startswith(base_url):
                    if el["href"] not in self.pages_to_visit:
                        self.pages_to_visit.append(el["href"])
            elif el["clicked"] == "no" and el["currentUrl"] == page.url:
                is_visible = await page.is_visible(selector_path)
                if not is_visible:
                    if parent_sel_path is not None:
                        parent = page.locator(parent_sel_path)
                        await parent.scroll_into_view_if_needed()
                        await asyncio.sleep(0.1)
                        try:
                            await parent.click()
                            await page.wait_for_load_state("networkidle")
                            await asyncio.sleep(0.5)
                        except TimeoutError:
                            logging.error(f"Element {parent_sel_path} click timed out, moving on.")
                    await asyncio.sleep(0.1)
                    selector_path = el["selectorPath"]

                is_disabled = await page.eval_on_selector(
                    selector_path,
                    """
                        element => {
                            let parent = element.parentElement;
                            if (parent && parent.classList.contains('disabled')) {
                                parent.classList.remove('disabled');
                                return true;
                            }
                            return false;
                        }
                    """
                )

                is_visible = await page.is_visible(selector_path)
                if is_visible:
                    await asyncio.sleep(0.1)

                    if not is_disabled:
                        if not await check_and_click(selector_path):
                            if not await check_and_click(el["selectorPath"]):
                                logging.error(f"Failed to click element with selector: {selector_path}")
                                await page.mouse.click(center_x, center_y)
                                el["clicked"] = "yes"
                            else:
                                check_again = False
                        else:
                            check_again = False

                    if not check_again:
                        el["clicked"] = "yes"
                        await page.wait_for_load_state("networkidle")
                        while page.url != el["currentUrl"]:
                            if page.url not in self.pages_to_visit and "#" not in page.url:
                                self.pages_to_visit.append(page.url)
                            await page.goto(el["currentUrl"], timeout=30000)
                            await page.wait_for_load_state("networkidle")
                            if page.url == el["currentUrl"]:
                                self.detected_elements, self.detected_input_elements = await self.crawler_helpers.detection_cl_elements(
                                    page, self.detected_elements, self.detected_input_elements
                                )
                                logging.info(f"second: {self.detected_elements}")
                            elif page.url != el["currentUrl"]:
                                await self.authentication.run(page)
                                await page.goto(el["currentUrl"], timeout=30000)
                                await page.wait_for_load_state("networkidle")
                                self.detected_elements, self.detected_input_elements = await self.crawler_helpers.detection_cl_elements(
                                    page, self.detected_elements, self.detected_input_elements
                                )
                                logging.info(f"third: {self.detected_elements}")
                        await asyncio.sleep(0.1)
                        await page.wait_for_load_state("networkidle")
                        updated_elements = await page.evaluate("window.detected_elements")
                        updated_input_elements = await page.evaluate("window.detected_input_elements")

                        new_elements = [
                            el for el in updated_input_elements
                            if el["hash"] not in {el["hash"] for el in self.detected_input_elements}
                        ]

                        self.detected_input_elements.extend(new_elements)

                        different_elements_by_hash = []
                        for element in updated_elements:
                            if "parentElement" in element:
                                has_matching_elements = any(
                                    "hash" in e and "parentElement" in e
                                    for e in self.detected_elements
                                )
                                if has_matching_elements:
                                    detected_element_pairs = {
                                        (e.get("hash"), e.get("parentElement", {}).get("hash"))
                                        for e in self.detected_elements
                                    }
                                    if (
                                        element.get("hash"),
                                        element.get("parentElement", {}).get("hash")
                                    ) not in detected_element_pairs:
                                        different_elements_by_hash.append(element)
                                else:
                                    different_elements_by_hash.append(element)

                        self.detected_elements.extend(different_elements_by_hash)
                        await self.process_children(page, el)
                else:
                    logging.info(f"Element {el['className']} - {el['selectorPath']}: is not visible!")

        except Exception as e:
            logging.error(f"Simulate a click in the bottom-right corner of the screen because of error: {e}")
            await page.mouse.click(center_x, center_y)
            el["clicked"] = "yes"



    async def process_input_element(self, page, el, username, password):
        viewport_size = page.viewport_size
        screen_width = viewport_size["width"]
        screen_height = viewport_size["height"]
        center_x = screen_width // 2
        center_y = screen_height // 2
        form_clicked = False

        if (
            "type" in el
            and el["type"] == "inputSet"
            and el["isFilled"] == "no"
            and el["currentUrl"] == page.url
        ):

            async def find_element_by_inner_html(page, tag_name, inner_html):
                try:
                    elements = await page.query_selector_all(tag_name)
                    for element in elements:
                        if await element.inner_html() == inner_html:
                            return element
                except Exception as e:
                    logging.error(f"Error while searching for element: {e}")
                return None

            form_element = await find_element_by_inner_html(page, el["tagName"], el["innerHTML"])

            if form_element:
                is_hidden = await page.evaluate(
                    """
                    element => {
                        if (getComputedStyle(element).display === "none" || getComputedStyle(element).display === "none !important") {
                            element.style.display = "block";
                            return true;
                        }
                        return false;
                    }
                    """,
                    form_element,
                )
            else:
                is_hidden = False

            if is_hidden:
                pass

            try:
                for input_el in el["inputs"]:
                    selector_str = input_el.get("selectorPath")

                    is_visible = await page.is_visible(selector_str)
                    if not is_visible:
                        if el.get("parentHash") is not None:
                            for parent_el in self.detected_elements:
                                if parent_el.get("hash") == el.get("parentHash"):
                                    get_par_sel_path = parent_el.get("selectorPath")
                                    find_parent = page.locator(get_par_sel_path)
                                    await find_parent.scroll_into_view_if_needed()
                                    await asyncio.sleep(0.1)
                                    try:
                                        await find_parent.click()
                                        await page.wait_for_load_state("networkidle")
                                        await asyncio.sleep(0.5)
                                    except TimeoutError:
                                        logging.error(f"Element {get_par_sel_path} click timed out, moving on.")
                                    await asyncio.sleep(0.1)

                    input_type = input_el.get("type")
                    input_name = input_el.get("name") if input_el.get("name") is not None else "nema"
                    input_id = input_el.get("id") if input_el.get("id") is not None else "nema"
                    input_placeholder = input_el.get("placeholder") if input_el.get("placeholder") is not None else "nema"
                    input_accept = input_el.get("accept") if input_el.get("accept") is not None else "nema"
                    if input_type == "hidden":
                        continue
                    tag_name = input_el.get("tagName")
                    selector_str = input_el.get("selectorPath")
                    selector = page.locator(selector_str)
                    is_hidden = await page.eval_on_selector(
                        selector_str,
                        """
                        element => {
                            if (getComputedStyle(element).display === "none" || getComputedStyle(element).display === "none !important") {
                                element.style.display = "block";
                                return true;
                            }
                            return false;
                        }
                        """,
                    )
                    await page.eval_on_selector(
                        selector_str,
                        """
                        element => {
                            if (element) {
                                element.removeAttribute('hidden');
                                return true;
                            }
                            return false;
                        }
                        """,
                    )

                    if is_hidden:
                        pass
                    await selector.scroll_into_view_if_needed()
                    await asyncio.sleep(0.1)

                    if (
                        input_type == "text"
                        and input_name == "url"
                        or input_type == "url"
                    ):
                        if input_type not in ["submit", "button"]:
                            await page.fill(selector_str, "https://pastebin.com/raw/sBPFirne")
                        self.filled_values[selector_str] = "https://pastebin.com/raw/sBPFirne"
                        await asyncio.sleep(0.1)
                    elif (
                        "email" in input_type
                        or "email" in input_name
                        or "email" in input_id
                        or "email" in input_placeholder
                    ):
                        if "@" not in username:
                            random_text = self.common_helpers.random_string()
                            email = random_text + "@gmail.com"
                        else:
                            email = username
                        if input_type not in ["submit", "button"]:
                            await page.fill(selector_str, email)
                        else:
                            await selector.click()
                        self.filled_values[selector_str] = email
                        await asyncio.sleep(0.1)
                    elif (
                        "password" in input_type
                        or "password" in input_name
                        or "password" in input_id
                        or "password" in input_placeholder
                    ):
                        if input_type not in ["submit", "button"]:
                            await page.fill(selector_str, password)
                        self.filled_values[selector_str] = password
                        await asyncio.sleep(0.1)
                    elif (
                        "number" in input_type
                        or "number" in input_name
                        or "number" in input_id
                        or "number" in input_placeholder
                    ):
                        random_num = self.common_helpers.random_token(5)
                        if input_type not in ["submit", "button"]:
                            await page.fill(selector_str, random_num)
                        self.filled_values[selector_str] = random_num
                        await asyncio.sleep(0.1)
                    elif input_type == "text":
                        random_text = self.common_helpers.random_string()
                        if input_type not in ["submit", "button"]:
                            await page.fill(selector_str, random_text)
                        self.filled_values[selector_str] = random_text
                        await asyncio.sleep(0.1)
                    elif tag_name == "TEXTAREA":
                        random_text = self.common_helpers.random_string()
                        await page.fill(selector_str, random_text)
                        self.filled_values[selector_str] = random_text
                        await asyncio.sleep(0.1)
                    elif input_type == "file":
                        if "image" in input_accept:
                            try:
                                await selector.set_input_files("app/common/assets/images/bla.txt.jpg")
                                self.filled_values[selector] = "bla.txt.jpg"
                            except Exception as e:
                                logging.error(f"Failed to upload bla.txt.jpg due to: {e}. Trying bla.txt.jpg...")
                        else:
                            try:
                                await selector.set_input_files("app/common/assets/documents/bla.txt")
                                self.filled_values[selector] = "bla.txt"
                            except Exception as e:
                                logging.error(f"Failed to upload bla.txt due to: {e}. Trying bla.txt...")
                    elif input_type == "file":
                        if "video" in input_accept:
                            try:
                                await selector.set_input_files("app/common/assets/videos/hackU.mp4")
                                self.filled_values[selector] = "hackU.mp4"
                            except Exception as e:
                                logging.error(f"Failed to upload hackU.mp4 due to: {e}....")
                    elif input_type == "submit" or (tag_name == "BUTTON" and input_type == "submit"):
                        await asyncio.sleep(0.1)
                        try:
                            await selector.click()
                            await page.wait_for_load_state("networkidle")
                            await asyncio.sleep(0.5)
                            form_clicked = True
                        except TimeoutError:
                            logging.error(f"Element click timed out, moving on.")
                    else:
                        logging.info(f"Element not detected.")

                    if form_clicked:
                        await page.wait_for_load_state("networkidle")
                        await page.mouse.click(center_x, center_y)
                        while page.url != el["currentUrl"]:
                            if page.url not in self.pages_to_visit and "#" not in page.url:
                                self.pages_to_visit.append(page.url)
                                await page.goto(el["currentUrl"], timeout=30000)
                                await page.wait_for_load_state("networkidle")
                            if page.url == el["currentUrl"]:
                                self.detected_elements, self.detected_input_elements = await self.crawler_helpers.detection_cl_elements(
                                    page, self.detected_elements, self.detected_input_elements
                                )
                                logging.info(f"fourth: {self.detected_elements}")
                            elif page.url != el["currentUrl"]:
                                await self.authentication.run(page)
                                await page.goto(el["currentUrl"], timeout=30000)
                                await page.wait_for_load_state("networkidle")
                                self.detected_elements, self.detected_input_elements = await self.crawler_helpers.detection_cl_elements(
                                    page, self.detected_elements, self.detected_input_elements
                                )
                                logging.info(f"fifth: {self.detected_elements}")
                        await asyncio.sleep(0.1)
                        await page.wait_for_load_state("networkidle")
                        await page.goto(el["currentUrl"], timeout=30000)
                        self.detected_elements, self.detected_input_elements = await self.crawler_helpers.detection_cl_elements(
                            page, self.detected_elements, self.detected_input_elements,
                        )
                        logging.info(f"sixth: {self.detected_elements}")
                    else:
                        logging.info("Form is not submitted!")

                el["isFilled"] = "yes"
            except Exception as e:
                logging.error(f"Error while filling form on page: {page.url} with selector: {selector_str} --- {e}")

    async def process_children(self, page, parent_element):
        if len(self.detected_input_elements) > 0:
            for element in self.detected_elements:
                for el in self.detected_input_elements:
                    for input_el in el["inputs"]:
                        if element.get("selectorPath") == input_el["selectorPath"]:
                            element["clicked"] = "yes"
                        if element.get("forAttribute") and element.get("clicked") == "no":
                            if "#" + element.get("forAttribute") == input_el["selectorPath"]:
                                element["clicked"] = "yes"

        parent_level = parent_element.get("level")
        parent_hash_origin = parent_element.get("hash")
        if parent_level is not None:
            for child in self.detected_elements:
                child_level = child.get("level")
                parent_hash = child.get("parentElement", {}).get("hash")
                if parent_hash_origin == parent_hash:
                    parent_sel_path = parent_element.get("selectorPath")
                else:
                    parent_sel_path = None
                if child_level is not None and child_level > parent_level:
                    await self.process_element(page, child, self.base_url, parent_sel_path)

    async def start_clicking(self, page, username, password, base_url):
        if len(self.detected_input_elements) > 0:
            for element in self.detected_elements:
                for el in self.detected_input_elements:
                    for input_el in el["inputs"]:
                        if element.get("selectorPath") == input_el["selectorPath"]:
                            element["clicked"] = "yes"
                        if element.get("forAttribute") and element.get("clicked") == "no":
                            if "#" + element.get("forAttribute") == input_el["selectorPath"]:
                                element["clicked"] = "yes"

        for el in self.detected_elements:
            await self.process_element(page, el, base_url)

        for el in self.detected_input_elements:
            await self.process_input_element(page, el, username, password)

    def should_skip(self, url, skip_extensions):
        return any(re.search(f"{re.escape(ext)}$", url) for ext in skip_extensions)
