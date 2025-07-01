from fastapi import APIRouter, Depends, Body
from app.v1.dependencies import DependencyManager

router = APIRouter()

dependency_manager = DependencyManager()

@router.post("/config")
async def get_config(
    auth: int = Body(..., embed=True),
    scantype: str = Body(..., embed=True),
    loginurl: str = Body(None, embed=True),
    username: str = Body(None, embed=True),
    password: str = Body(None, embed=True),
    filepath: str = Body(None, embed=True),
    entrypoint: str = Body(None, embed=True),
    tests: list[int] = Body(..., embed=True),
):
    args = {
        "auth": auth,
        "scantype": scantype,
        "loginurl": loginurl,
        "username": username,
        "password": password,
        "filepath": filepath,
        "entrypoint": entrypoint,
        "tests": tests,
    }

    config = await dependency_manager.get_scan_config(args)
    return {"config": config}

@router.post("/crawler")
async def execute_crawler(config: dict = Body(...)):
    crawler = await dependency_manager.get_crawler(config)
    crawling_results = await dependency_manager.common_helpers.run_crawler(crawler)
    return {"crawling_results": crawling_results}
