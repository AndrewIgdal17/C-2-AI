import asyncio
import json
import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
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
    stream: bool = False


class ChartItem(BaseModel):
    title: str = ""
    description: str = ""
    image_base64: str = ""


class VisualizeResponse(BaseModel):
    charts: list[ChartItem] = []


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/visualize")
async def visualize_endpoint(request: VisualizeRequest):
    logger.info("Received task: %s (stream=%s)", request.task[:100], request.stream)

    if request.stream:
        log_queue = asyncio.Queue()

        async def log_callback(msg):
            await log_queue.put(msg)

        async def run_and_signal():
            try:
                result = await create_visualizations(request.task, request.context, log_callback=log_callback)
                await log_queue.put(("__RESULT__", result))
            except Exception as e:
                await log_queue.put(("__ERROR__", str(e)))

        async def event_stream():
            task = asyncio.create_task(run_and_signal())
            while True:
                try:
                    item = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {{}}\n\n"
                    continue

                if isinstance(item, tuple):
                    if item[0] == "__RESULT__":
                        result_data = {"charts": item[1]}
                        yield f"event: result\ndata: {json.dumps(result_data)}\n\n"
                        break
                    elif item[0] == "__ERROR__":
                        err_data = {"error": item[1]}
                        yield f"event: error\ndata: {json.dumps(err_data)}\n\n"
                        break
                else:
                    yield f"event: log\ndata: {json.dumps({'message': item})}\n\n"
            await task

        return StreamingResponse(event_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    else:
        charts = await create_visualizations(request.task, request.context)
        return VisualizeResponse(charts=[ChartItem(**c) for c in charts])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
