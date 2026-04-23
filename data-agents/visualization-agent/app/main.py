import logging

from fastapi import FastAPI
from pydantic import BaseModel

from app.visualize import create_visualizations
from app.tracing import instrument_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visualization-agent")

app = FastAPI(title="Visualization Sub-Agent")
instrument_app(app)


class VisualizeRequest(BaseModel):
    task: str
    context: str = ""


class ChartItem(BaseModel):
    title: str = ""
    description: str = ""
    image_base64: str = ""


class VisualizeResponse(BaseModel):
    charts: list[ChartItem] = []


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/visualize", response_model=VisualizeResponse)
async def visualize_endpoint(request: VisualizeRequest):
    logger.info("Received visualization task: %s", request.task[:200])
    charts = await create_visualizations(request.task, request.context)
    return VisualizeResponse(charts=[ChartItem(**c) for c in charts])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
