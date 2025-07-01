import asyncio
from aiohttp.client_exceptions import ClientOSError, ServerDisconnectedError

status_code_counts = {}
raw_response = {}


async def send_request(session, modified_url, method, headers, modified_body):
    semaphore = asyncio.Semaphore(10)
    async with semaphore:
        try:
            async with session.request(
                method,
                modified_url,
                headers=headers,
                data=modified_body,
                allow_redirects=True,
            ) as response:
                response_status = str(response.status)
                body = await response.text()

                status_code_counts[response_status] = (
                    status_code_counts.get(response_status, 0) + 1
                )

                raw_response = {
                    "status": response.status,
                    "response_url": str(response.url),
                    "headers": dict(response.headers),
                    "body": body,
                }

                return raw_response, status_code_counts

        except ServerDisconnectedError:
            status_code_counts["SERVER_DISCONNECTED"] = (
                status_code_counts.get("SERVER_DISCONNECTED", 0) + 1
            )
            print("ServerDisconnectedError encountered")
            raise

        except ClientOSError as e:
            if e.errno == 104:  # Connection reset by peer
                status_code_counts["CONN_RESET"] = (
                    status_code_counts.get("CONN_RESET", 0) + 1
                )
                print("ClientOSError (Connection reset by peer) encountered")
                raise

        except asyncio.TimeoutError:
            status_code_counts["TIMEOUT"] = status_code_counts.get("TIMEOUT", 0) + 1
            print("TimeoutError encountered")
            raise

        except Exception as e:
            status_code_counts["ERROR"] = status_code_counts.get("ERROR", 0) + 1
            print(f"Exception encountered: {e}")
            raise
