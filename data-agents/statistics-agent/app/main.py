import logging

from fastapi import FastAPI
from pydantic import BaseModel

from app.statistics import analyze
from app.tracing import instrument_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("statistics-agent")

app = FastAPI(title="Statistics Sub-Agent")
instrument_app(app)


class AnalyzeRequest(BaseModel):
    task: str
    context: str = ""


class AnalyzeResponse(BaseModel):
    summary: str = ""
    statistics: dict = {}
    tables: list = []


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(request: AnalyzeRequest):
    logger.info("Received analysis task: %s", request.task[:200])
    result = await analyze(request.task, request.context)
    return AnalyzeResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
