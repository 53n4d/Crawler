class AuthenticationHelpers:
    def __init__(self, config):
        self.login_url = config["login_url"]
        self.username = config["username"]
        self.password = config["password"]
        self.headers_list = []


    async def log_and_continue_request(self, request):
        all_headers = request.headers
        headers_dict = {
            header: value
            for header, value in all_headers.items()
            if not header.startswith(":")
        }
        if headers_dict:  # Add to the headers list if the dictionary is not empty
            self.headers_list.append(headers_dict)    

        
    async def authenticate(self, page):
        try:
            await page.goto(self.login_url)
            await page.wait_for_load_state("load")
            parsed_content = await page.content()
            login_form = False
            if 'type="password"' in parsed_content:
                user_data = None
                for input_type in [
                    'name="j_username"',
                    'name="ctl00$ContentPlaceHolder1$txtUsername"',
                    'name="uid"',
                    'type="email"',
                    'name="email"',
                    'name="user"',
                    'name="uname"',
                    'name="login"',
                    'name="username"',
                    'id="basic_email"',
                ]:
                    if input_type in parsed_content:
                        user_data = input_type
                        login_form = True
                        break

                if login_form:
                    await page.fill(f"input[{user_data}]", self.username)
                    await page.fill('input[type="password"]', self.password)
                    await page.press('input[type="password"]', "Enter")
                    await page.wait_for_load_state("load")
                    await page.wait_for_timeout(1000)

                    current_url_after_bf = page.url
                    parsed_content_after_bf = await page.content()

                    if (
                        'type="password"' in parsed_content_after_bf
                        and user_data in parsed_content_after_bf
                        and current_url_after_bf == self.login_url
                    ):
                        pass
                    else:
                        for headers_dict in self.headers_list:
                            if "authorization" in headers_dict:
                                return headers_dict
                        for headers_dict in self.headers_list:
                            if "cookie" in headers_dict:
                                return headers_dict
                        if self.headers_list:
                            return self.headers_list[0]
                else:
                    print(f"There is no login form on {self.login_url}")

        except Exception as e:
            pass