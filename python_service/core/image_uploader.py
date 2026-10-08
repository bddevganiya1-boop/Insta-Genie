import base64
import logging
from typing import Optional
import httpx

from python_service.config import settings

logger = logging.getLogger("insta-genie.image_uploader")


class ImageUploader:
    """Service to host generated images on a public URL accessible by Meta's Graph API."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.IMAGE_HOST_PROVIDER
        self.imgbb_key = settings.IMGBB_API_KEY
        self.cloudinary_cloud = settings.CLOUDINARY_CLOUD_NAME
        self.cloudinary_key = settings.CLOUDINARY_API_KEY
        self.cloudinary_secret = settings.CLOUDINARY_API_SECRET

    async def upload_image(self, image_bytes: bytes, filename: str = "insta_post.png") -> str:
        """
        Uploads image binary bytes to the selected cloud provider and returns a public HTTPS URL.
        """
        if settings.DRY_RUN:
            logger.info("DRY_RUN is active. Returning mock public image URL.")
            return "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&q=80"

        # 1. ImgBB Upload
        if self.imgbb_key:
            try:
                url = await self._upload_to_imgbb(image_bytes)
                if url:
                    return url
            except Exception as e:
                logger.error(f"ImgBB upload failed: {e}")

        # 2. Cloudinary Upload
        if self.cloudinary_cloud and self.cloudinary_key and self.cloudinary_secret:
            try:
                url = await self._upload_to_cloudinary(image_bytes)
                if url:
                    return url
            except Exception as e:
                logger.error(f"Cloudinary upload failed: {e}")

        # 3. S3 / R2 Upload
        if settings.S3_BUCKET_NAME and settings.S3_ACCESS_KEY_ID:
            try:
                url = await self._upload_to_s3(image_bytes, filename)
                if url:
                    return url
            except Exception as e:
                logger.error(f"S3/R2 upload failed: {e}")

        # Fallback placeholder if no credentials configured
        logger.warning(
            "No public image hosting credentials provided (IMGBB_API_KEY / CLOUDINARY / S3). "
            "Falling back to high-res aesthetic public placeholder."
        )
        return "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&q=80"

    async def _upload_to_imgbb(self, image_bytes: bytes) -> str:
        """Upload to ImgBB free image hosting service."""
        url = "https://api.imgbb.com/1/upload"
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        data = {
            "key": self.imgbb_key,
            "image": b64_image,
            "expiration": 2592000  # 30 days retention
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            res_json = response.json()
            public_url = res_json.get("data", {}).get("url") or res_json.get("data", {}).get("display_url")
            logger.info(f"Image uploaded to ImgBB: {public_url}")
            return public_url

    async def _upload_to_cloudinary(self, image_bytes: bytes) -> str:
        """Upload to Cloudinary CDN."""
        import hashlib
        import time

        timestamp = int(time.time())
        # Generate signature
        string_to_sign = f"timestamp={timestamp}{self.cloudinary_secret}"
        signature = hashlib.sha1(string_to_sign.encode("utf-8")).hexdigest()

        url = f"https://api.cloudinary.com/v1_1/{self.cloudinary_cloud}/image/upload"
        files = {"file": image_bytes}
        data = {
            "api_key": self.cloudinary_key,
            "timestamp": timestamp,
            "signature": signature
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            res_json = response.json()
            public_url = res_json.get("secure_url")
            logger.info(f"Image uploaded to Cloudinary: {public_url}")
            return public_url

    async def _upload_to_s3(self, image_bytes: bytes, filename: str) -> str:
        """Upload to S3 compatible storage / Cloudflare R2."""
        import boto3
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
        key = f"instagram_posts/{filename}"
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=image_bytes,
            ContentType="image/png"
        )
        base = settings.S3_PUBLIC_BASE_URL.rstrip("/") if settings.S3_PUBLIC_BASE_URL else f"https://{settings.S3_BUCKET_NAME}.s3.amazonaws.com"
        return f"{base}/{key}"
