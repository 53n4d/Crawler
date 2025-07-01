import json
import shutil
import asyncio
import aiohttp


class SubdomainEnumerationTest:
    test_name = "Subdomain Enumeration"
    counter = 0
    tested = []
    tasks = []
    expected_fields = ["__schema", "types", "queryType", "mutationType"]
    common_paths = [
        "/graphql",
        "/api/graphql",
        "/v1/graphql",
        "/v2/graphql",
        "/graph",
        "/gql",
        "/query",
    ]
    severity = "Medium"
