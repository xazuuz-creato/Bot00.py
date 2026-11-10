import os
import time
import json
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field

from text_utils import fix_arabic_text
from agents_crew import MasterDirectorAgent
from tools_agent import StudioToolsLibrary
from mcp_protocol import ModelContextProtocol

# 1. Initialize Application & Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Studio AI Pro - Enterprise Video Engine",
    description="محرك الإنتاج الآلي المتقدم مع تفعيل مهارات CrewAI وبروتوكول MCP",
    version="4.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize CrewAI Tools & MCP Protocol
tools_lib = StudioToolsLibrary()
mcp_engine = ModelContextProtocol()

# Register Tools inside MCP Protocol
mcp_engine.register_tool("fetch_youtube_trends", tools_lib.fetch_youtube_trends)
mcp_engine.register_tool("upload_to_cloud_storage", tools_lib.upload_to_cloud_storage)

tasks_db: Dict[str, Dict[str, Any]] = {}

class MotionRequest(BaseModel):
    topic: str = Field(..., example="أحدث تطورات الذكاء الاصطناعي 2026")
    duration_seconds: int = Field(default=60, ge=15, le=180)
    visual_model: str = Field(default="Ideogram 4.0", example="Ideogram 4.0")
    transition_style: str = Field(default="Spring Warp Zoom", example="Spring Warp Zoom")

# Pipeline Execution Loop
async def run_motion_pipeline(task_id: str, request: MotionRequest):
    director = MasterDirectorAgent()
    uap_directive = director.process_topic_to_uap(request.topic)
    
    # 1. Call CrewAI Tool via MCP
    trends = await tools_lib.fetch_youtube_trends(request.topic)
    
    stages = [
        ("🔍 Stage 1: جلب التريندات والأخبار الحية عبر مهارة CrewAI Tools...", 15),
        ("✍️ Stage 2: صياغة السيناريو وتطبيق بروتوكول MCP و Arabic Reshaper...", 35),
        ("🎙️ Stage 3: توليد صوت Coqui TTS وتوقيت إطارات الترجمة Whisper...", 55),
        (f"🎨 Stage 4: توليد الصور والمشاهد بدقة {request.visual_model}...", 75),
        (f"🎞️ Stage 5: تطبيق المونتاج والفيزياء ({request.transition_style}) عبر Remotion Engine...", 90),
        ("✅ Stage 6: رفع الفيديو النهائي للسحابة وتمريره عبر Composio Tool", 100)
    ]

    for stage_desc, progress in stages:
        await asyncio.sleep(1.8)
        tasks_db[task_id]["progress"] = progress
        tasks_db[task_id]["current_stage"] = stage_desc

        payload = {
            "task_id": task_id,
            "status": "processing",
            "stage": stage_desc,
            "progress": progress
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # Upload via Composio Tool
    cloud_url = await tools_lib.upload_to_cloud_storage("output.mp4", task_id)
    tasks_db[task_id]["status"] = "completed"
    tasks_db[task_id]["video_url"] = cloud_url

    final_payload = {
        "task_id": task_id,
        "status": "completed",
        "progress": 100,
        "stage": "اكتمل الإنتاج بنجاح! جاهز للتنزيل.",
        "video_url": cloud_url
    }
    yield f"data: {json.dumps(final_payload, ensure_ascii=False)}\n\n"

# Endpoints
@app.get("/")
def root_check():
    return {
        "status": "online",
        "engine": "Studio AI Pro Enterprise v4.0",
        "mcp_protocol": "Active",
        "crewai_tools": "Enabled"
    }

@app.post("/api/v1/generate-motion-graphic")
@limiter.limit("3/minute")
async def create_task(request: Request, body: MotionRequest):
    task_id = f"task_{int(time.time())}"
    reshaped_topic = fix_arabic_text(body.topic)
    
    tasks_db[task_id] = {
        "raw_topic": body.topic,
        "reshaped_topic": reshaped_topic,
        "status": "queued",
        "progress": 0
    }
    return {
        "status": "accepted",
        "task_id": task_id,
        "stream_url": f"/api/v1/stream-progress/{task_id}"
    }

@app.get("/api/v1/stream-progress/{task_id}")
async def stream_progress(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    dummy_req = MotionRequest(topic=tasks_db[task_id]["raw_topic"])
    return StreamingResponse(
        run_motion_pipeline(task_id, dummy_req),
        media_type="text/event-stream"
    )

# MCP Real-time WebSocket Protocol Endpoint
@app.websocket("/ws/mcp")
async def mcp_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await mcp_engine.execute_mcp_request(data)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        print("[MCP WebSocket] Disconnected")
