from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(
    title="Hello World",
    version="0.1.0",
    root_path="/apps/hello",
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/hello")
async def hello():
    return {"message": "Hello from Squareberg!"}


@app.get("/api/hello/{name}")
async def hello_name(name: str):
    return {"message": f"Hello, {name}!"}


@app.get("/api/time")
async def time():
    return {"time": datetime.now(timezone.utc).isoformat()}
