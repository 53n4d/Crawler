from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.v1.endpoints import router

app = FastAPI()

# Serve static files from the nested 'static/static' directory
app.mount("/static", StaticFiles(directory="static/static"), name="static")

@app.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse("static/index.html")

@app.get("/{path:path}", response_class=FileResponse)
async def catch_all(path: str):
    return FileResponse("static/index.html")

# Include the v1 API router
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
