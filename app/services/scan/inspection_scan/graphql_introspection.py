import json
import asyncio
import aiohttp
from functools import partial


class GraphQlIntrospectionTest:
    test_selector = "graphql_introspection"
    counter = 0
    tested = []
    tasks = []
    issue = {}
    expected_fields = ["__schema", "types", "queryType", "mutationType"]
    common_paths = [
        "/graphql",
        "/api/graphql",
        "/v1/graphql",
        "/v2/graphql",
        "/graph",
        "/gql",
        "/query",
        "/graphiql",
    ]

    def __init__(
        self,
        base_url,
        requests,
        parse_data,
        new_headers,
        modify_request,
        send_request,
        inspection_payloads,
        inspection_metadata,
    ):
        self.base_url = base_url
        self.requests = requests
        self.parse_data = parse_data
        self.new_headers = new_headers
        self.modify_request = modify_request
        self.send_request = send_request
        self.inspection_payloads = inspection_payloads
        self.inspection_metadata = inspection_metadata
        
    @classmethod
    def get_test_selector(cls):
        return cls.test_selector

    async def run(self):
        payload = self.inspection_payloads["payloads"]["graphql_intro"]
        metadata = self.inspection_metadata["inspection"]["graphqlIntrospection"]

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=800)
            ) as session:
                for request in self.requests:
                    full_url, _, _, headers, _, _, _, _ = self.parse_data(request)
                    if (
                        any(path in full_url for path in self.common_paths)
                        and full_url not in self.tested
                    ):
                        self.tested.append(full_url)
                        modified_url, modified_body, modified_method, headers = (
                            await self.prepare_graphql_introspection_request_elements(
                                headers, payload
                            )
                        )

                        request, headers = self.modify_request(
                            request,
                            headers,
                            self.new_headers,
                            modified_url,
                            modified_method,
                            modified_body,
                        )

                        config = {
                            "session": session,
                            "modified_url": modified_url,
                            "method": modified_method,
                            "headers": headers,
                            "modified_body": modified_body,
                        }

                        task = asyncio.create_task(self.send_request(**config))
                        task.add_done_callback(
                            partial(
                                self.issue_validation,
                                request=request,
                                payload=payload,
                                metadata=metadata,
                            )
                        )
                        self.tasks.append(task)
                        self.counter += 1

                await asyncio.gather(*self.tasks, return_exceptions=True)

        except asyncio.exceptions.CancelledError:
            print("Task was cancelled, cleaning up...")
        finally:
            pass
        
        self.issue['counter'] = self.counter
        print(self.issue)
        return self.issue

    def issue_validation(self, task, request, payload, metadata):
        try:
            response = task.result()
            if isinstance(response, Exception):
                print(f"Task error: {response}")
            else:
                test_name = metadata["test_name"]
                raw_response, status_code = response
                rate_limit = status_code.get("429")
                if all(
                    field in raw_response.get("body", "")
                    for field in self.expected_fields
                ):
                    self.issue.setdefault(test_name, []).append({
                            "request": request,
                            "payload": payload,
                            "response": raw_response,
                            "rate_limit": rate_limit,
                            "metadata": metadata,
                    })
                    # Cancel all pending tasks
                    for pending_task in self.tasks:
                        if not pending_task.done():
                            pending_task.cancel()

        except Exception as e:
            print(f"Error processing task result: {e}")

    async def prepare_graphql_introspection_request_elements(self, headers, payload):
        modified_url = f"{self.base_url}/graphql"
        headers["Content-Type"] = "application/json"
        modified_body = json.dumps(payload)
        modified_method = "POST"
        return modified_url, modified_body, modified_method, headers
