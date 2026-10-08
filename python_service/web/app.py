import base64
import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from python_service.config import settings
from python_service.core.cloudflare_ai import CloudflareWorkersAI
from python_service.core.instagram_api import MetaInstagramGraphAPI
from python_service.core.image_uploader import ImageUploader
from python_service.core.pipeline import InstaGeniePipeline
from python_service.core.scheduler import AutomationScheduler

app = FastAPI(
    title="Insta Genie API",
    description="Autonomous Instagram Content & Publishing Engine powered by Meta Graph API and Cloudflare Workers AI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Instances
pipeline = InstaGeniePipeline()
scheduler = AutomationScheduler(pipeline=pipeline)

# Request Models
class GenerateRequest(BaseModel):
    topic: str = Field(..., example="Autonomous AI Agents in Healthcare")
    tone: Optional[str] = Field("engaging, visionary & professional", example="engaging & professional")

class PublishRequest(BaseModel):
    caption: str = Field(..., example="✨ The future of AI is here! #AI #Innovation")
    image_base64: Optional[str] = Field(None, description="Base64 data of image")
    image_url: Optional[str] = Field(None, description="Direct public URL if already hosted")

class PipelineRequest(BaseModel):
    topic: str = Field(..., example="Cyberpunk Futuristic Architecture")
    tone: Optional[str] = Field("inspiring & aesthetic", example="inspiring & aesthetic")
    auto_publish: bool = Field(True, description="Immediately publish or only generate draft")

class SchedulerToggleRequest(BaseModel):
    enabled: bool
    interval_hours: Optional[int] = 6


# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/status")
async def get_system_status():
    """Returns overall configuration and connectivity health."""
    return {
        "status": "online",
        "dry_run": settings.DRY_RUN,
        "cloudflare": {
            "configured": settings.is_cloudflare_configured,
            "text_model": settings.CF_TEXT_MODEL,
            "image_model": settings.CF_IMAGE_MODEL
        },
        "instagram": {
            "configured": settings.is_instagram_configured,
            "account_id": settings.INSTAGRAM_ACCOUNT_ID[:6] + "..." if settings.INSTAGRAM_ACCOUNT_ID else "NOT_SET",
            "api_version": settings.META_GRAPH_API_VERSION
        },
        "image_hosting": {
            "provider": settings.IMAGE_HOST_PROVIDER,
            "configured": bool(settings.IMGBB_API_KEY or settings.CLOUDINARY_API_KEY or settings.S3_BUCKET_NAME)
        }
    }


@app.get("/api/account")
async def get_account_details():
    """Fetch Instagram profile metadata."""
    try:
        profile = await pipeline.ig_api.get_account_profile()
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate")
async def generate_content(req: GenerateRequest):
    """Generates post caption, hashtags, and image without publishing."""
    try:
        draft = await pipeline.generate_draft(topic=req.topic, tone=req.tone)
        # Convert image bytes to Base64 for instant frontend preview
        b64_image = base64.b64encode(draft["image_bytes"]).decode("utf-8")
        
        return {
            "success": True,
            "topic": draft["topic"],
            "hook": draft["hook"],
            "body": draft["body"],
            "hashtags": draft["hashtags"],
            "full_caption": draft["full_caption"],
            "image_prompt": draft["image_prompt"],
            "image_base64": f"data:image/png;base64,{b64_image}",
            "elapsed_seconds": draft["elapsed_seconds"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/api/publish")
async def publish_content(req: PublishRequest):
    """Publishes a drafted image & caption to Instagram."""
    try:
        image_bytes = None
        if req.image_base64:
            clean_b64 = req.image_base64.split(",")[-1]
            image_bytes = base64.b64decode(clean_b64)

        result = await pipeline.publish_post(
            image_bytes=image_bytes,
            public_image_url=req.image_url,
            caption=req.caption
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")


@app.post("/api/run-pipeline")
async def run_full_pipeline(req: PipelineRequest):
    """Executes full autonomous cycle: Generate -> Upload -> Publish."""
    try:
        result = await pipeline.execute_full_cycle(
            topic=req.topic,
            tone=req.tone,
            auto_publish=req.auto_publish
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/api/scheduler")
async def get_scheduler_status():
    """Get automation schedule status and recent run history."""
    return scheduler.get_status()


@app.post("/api/scheduler/toggle")
async def toggle_scheduler(req: SchedulerToggleRequest):
    """Enable or disable background recurrent posting."""
    if req.enabled:
        scheduler.start(interval_hours=req.interval_hours)
    else:
        scheduler.stop()
    return scheduler.get_status()


# Static file serving for UI Dashboard
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(STATIC_DIR / "index.html"))
