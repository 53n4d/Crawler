class Authentication:
    def __init__(self, authentication_helpers):
        self.authentication_helpers = authentication_helpers

        
    async def run(self, page):
        page.on("request", self.authentication_helpers.log_and_continue_request)
        headers = await self.authentication_helpers.authenticate(page)

        return headers

