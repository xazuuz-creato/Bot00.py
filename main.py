import asyncio
import json
import shutil
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import StudioConfig
from mcp_protocol import ModelContextProtocol
from pipeline import produce_video
from styles import STYLES_LIST
from tools_agent import StudioToolsLibrary

app = FastAPI(title="Studio AI Pro - Real Engine", version="9.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

StudioConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(StudioConfig.OUTPUT_DIR)), name="videos")

tools_lib = StudioToolsLibrary()
mcp_engine = ModelContextProtocol()
mcp_engine.register_tool("upload_to_cloud", tools_lib.upload_to_cloud_storage)
job_slots = asyncio.Semaphore(StudioConfig.MAX_CONCURRENT_JOBS)
tasks_db: Dict[str, Dict[str, Any]] = {}


async def _finish(result: dict) -> dict:
    out = {"video_url": f"/videos/{result['video_file']}", "srt_url": f"/videos/{result['srt_file']}",
           **{k: result[k] for k in ("title", "scenes", "duration", "fps", "ai_images", "voiced_scenes", "warnings")}}
    try:
        cloud = await tools_lib.upload_to_cloud_storage(result["video_path"], result["video_file"].rsplit(".", 1)[0])
        if cloud:
            out["cloud_url"] = cloud
    except Exception as e:
        out["warnings"] = out["warnings"] + [f"فشل الرفع السحابي: {e}"]
    return out


@app.get("/", response_class=HTMLResponse)
def serve_index():
    p = StudioConfig.BASE_DIR / "index.html"
    return p.read_text(encoding="utf-8") if p.exists() else "<h1>Studio AI Pro Active</h1>"


@app.get("/api/health")
def health():
    return {"ffmpeg": bool(shutil.which("ffmpeg")), **StudioConfig.status()}


@app.get("/api/styles")
def styles():
    return [s["name"] for s in STYLES_LIST]


@app.websocket("/ws/studio-director")
async def studio_director_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def send(msg: dict):
        await websocket.send_text(json.dumps(msg, ensure_ascii=False))

    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            idea = (payload.get("video_idea") or "").strip()[:2000] or "فيديو موشن جرافيك"
            style = payload.get("design_style", "")
            prop = payload.get("property_setting", "سينمائي")
            duration = max(10, min(StudioConfig.MAX_DURATION, int(payload.get("duration", 30))))

            async def progress(pct, message):
                await send({"status": "processing", "progress": pct, "message": message})

            try:
                async with job_slots:
                    result = await produce_video(idea, style, prop, duration, progress)
                done = await _finish(result)
                await send({"status": "completed", "progress": 100, "message": "✅ اكتمل الفيديو الحقيقي", **done})
            except Exception as e:
                await send({"status": "error", "progress": 0, "message": f"❌ فشل الإنتاج: {e}"})
    except WebSocketDisconnect:
        pass


class RealMotionRequest(BaseModel):
    topic: str = Field(..., example="أحدث تطورات الذكاء الاصطناعي")
    duration_seconds: int = Field(default=30)
    main_style: str = Field(default=STYLES_LIST[0]["name"])
    property_setting: str = Field(default="سينمائي")


@app.post("/api/v1/generate-motion-graphic")
async def create_motion_task(body: RealMotionRequest):
    task_id = f"task_{int(time.time() * 1000)}"
    tasks_db[task_id] = {**body.model_dump(), "status": "queued"}
    tasks_db[task_id]["duration_seconds"] = max(10, min(StudioConfig.MAX_DURATION, body.duration_seconds))
    return {"status": "accepted", "task_id": task_id, "stream_url": f"/api/v1/stream-progress/{task_id}"}


@app.get("/api/v1/stream-progress/{task_id}")
async def stream_task_progress(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    q: asyncio.Queue = asyncio.Queue()

    async def worker():
        async def progress(pct, message):
            await q.put({"status": "processing", "progress": pct, "stage": message})
        try:
            async with job_slots:
                result = await produce_video(task["topic"], task["main_style"], task["property_setting"],
                                             task["duration_seconds"], progress, job_id=task_id)
            task["status"] = "completed"
            await q.put({"status": "completed", "progress": 100, **(await _finish(result))})
        except Exception as e:
            await q.put({"status": "error", "message": str(e)})
        await q.put(None)

    asyncio.create_task(worker())

    async def gen():
        while (item := await q.get()) is not None:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
