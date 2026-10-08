import os
from pathlib import Path
from typing import List

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env" if (PROJECT_ROOT / ".env").exists() else CURRENT_DIR / ".env"

# Load .env manually if python-dotenv is available or by simple parser
if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))


class Settings:
    def __init__(self):
        self.DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        self.OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", str(PROJECT_ROOT / "generated_media"))

        # Cloudflare Workers AI
        self.CLOUDFLARE_ACCOUNT_ID: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.CLOUDFLARE_API_TOKEN: str = os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.CF_TEXT_MODEL: str = os.getenv("CF_TEXT_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
        self.CF_IMAGE_MODEL: str = os.getenv("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

        # Meta Instagram Graph API
        self.INSTAGRAM_ACCOUNT_ID: str = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
        self.INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        self.META_GRAPH_API_VERSION: str = os.getenv("META_GRAPH_API_VERSION", "v20.0")

        # Image Hosting
        self.IMAGE_HOST_PROVIDER: str = os.getenv("IMAGE_HOST_PROVIDER", "imgbb")
        self.IMGBB_API_KEY: str = os.getenv("IMGBB_API_KEY", "")
        self.CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
        self.CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
        self.CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

        # S3 / R2
        self.S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
        self.S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
        self.S3_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY_ID", "")
        self.S3_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_ACCESS_KEY", "")
        self.S3_PUBLIC_BASE_URL: str = os.getenv("S3_PUBLIC_BASE_URL", "")

        # Scheduler
        self.SCHEDULE_INTERVAL_HOURS: int = int(os.getenv("SCHEDULE_INTERVAL_HOURS", "6"))
        self.DEFAULT_TOPICS: str = os.getenv(
            "DEFAULT_TOPICS",
            "AI Innovation & Robotics,Modern Minimalist Architecture,Healthy High-Protein Recipes,Future Tech & Cyberpunk Aesthetics,Daily Mindful Motivation"
        )

    @property
    def topics_list(self) -> List[str]:
        return [t.strip() for t in self.DEFAULT_TOPICS.split(",") if t.strip()]

    @property
    def is_cloudflare_configured(self) -> bool:
        return bool(self.CLOUDFLARE_ACCOUNT_ID and self.CLOUDFLARE_API_TOKEN)

    @property
    def is_instagram_configured(self) -> bool:
        return bool(self.INSTAGRAM_ACCOUNT_ID and self.INSTAGRAM_ACCESS_TOKEN)


settings = Settings()

# Ensure local media directory exists
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
