import asyncio
import logging
from typing import Dict, Any, Optional
import httpx

from python_service.config import settings

logger = logging.getLogger("insta-genie.instagram_api")


class MetaInstagramGraphAPI:
    """Meta Graph API Client for Instagram Content Publishing and Account Verification."""

    def __init__(
        self,
        account_id: Optional[str] = None,
        access_token: Optional[str] = None,
        api_version: Optional[str] = None,
        dry_run: Optional[bool] = None,
    ):
        self.account_id = account_id or settings.INSTAGRAM_ACCOUNT_ID
        self.access_token = access_token or settings.INSTAGRAM_ACCESS_TOKEN
        self.api_version = api_version or settings.META_GRAPH_API_VERSION
        self.dry_run = dry_run if dry_run is not None else settings.DRY_RUN
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    async def get_account_profile(self) -> Dict[str, Any]:
        """Fetch linked Instagram Account details (Username, Followers, Media count)."""
        if self.dry_run or not self.account_id or not self.access_token:
            return {
                "id": self.account_id or "17841400000000000",
                "username": "instagenie_demo",
                "name": "Insta Genie AI Agent",
                "biography": "Autonomous AI Social Media Assistant powered by Meta Graph API & Cloudflare Workers AI",
                "profile_picture_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=200&q=80",
                "followers_count": 14200,
                "media_count": 86,
                "is_mock": True
            }

        url = f"{self.base_url}/{self.account_id}"
        params = {
            "fields": "id,username,name,biography,profile_picture_url,followers_count,follows_count,media_count",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def create_media_container(self, image_url: str, caption: str) -> str:
        """
        Step 1: Create an Instagram media container object.
        Returns the container `creation_id`.
        """
        if self.dry_run or not self.account_id or not self.access_token:
            logger.info("DRY_RUN mode active: returning mock container ID.")
            return "mock_container_1798324792183921"

        url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, data=payload)
            if response.status_code != 200:
                logger.error(f"Meta Graph API error on container creation: {response.text}")
                response.raise_for_status()
            
            data = response.json()
            creation_id = data.get("id")
            logger.info(f"Instagram media container created with ID: {creation_id}")
            return creation_id

    async def wait_for_container_ready(self, creation_id: str, max_retries: int = 10, delay: float = 3.0) -> bool:
        """
        Step 2: Poll container status until it transitions to 'FINISHED'.
        """
        if self.dry_run or creation_id.startswith("mock_"):
            return True

        url = f"{self.base_url}/{creation_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        status_data = response.json()
                        status_code = status_data.get("status_code")
                        logger.info(f"Container {creation_id} status (Attempt {attempt+1}/{max_retries}): {status_code}")

                        if status_code == "FINISHED":
                            return True
                        elif status_code in ["ERROR", "EXPIRED"]:
                            logger.error(f"Container failed with status: {status_code} - {status_data}")
                            return False
                except Exception as e:
                    logger.warning(f"Error checking container status: {e}")

                await asyncio.sleep(delay)

        return True  # Proceed to publish attempt even if status is not explicitly finished

    async def publish_media(self, creation_id: str) -> Dict[str, Any]:
        """
        Step 3: Publish the ready container to the Instagram feed.
        Returns published media payload with permalink.
        """
        if self.dry_run or creation_id.startswith("mock_"):
            logger.info("DRY_RUN mode active: simulating successful publication.")
            return {
                "id": "18029384729182391",
                "permalink": "https://www.instagram.com/p/C_mockPostInstaGenie/",
                "timestamp": "2026-10-08T07:15:00+0000",
                "status": "PUBLISHED_MOCK"
            }

        url = f"{self.base_url}/{self.account_id}/media_publish"
        payload = {
            "creation_id": creation_id,
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, data=payload)
            if response.status_code != 200:
                logger.error(f"Meta Graph API error on media_publish: {response.text}")
                response.raise_for_status()

            data = response.json()
            published_id = data.get("id")
            logger.info(f"Successfully published Instagram Post ID: {published_id}")

            # Fetch permalink
            permalink = await self.get_media_permalink(published_id)
            return {
                "id": published_id,
                "permalink": permalink or f"https://www.instagram.com/p/{published_id}/",
                "status": "PUBLISHED"
            }

    async def get_media_permalink(self, media_id: str) -> Optional[str]:
        """Fetch post permalink for user preview and tracking."""
        if self.dry_run or media_id.startswith("18029384"):
            return "https://www.instagram.com/p/C_mockPostInstaGenie/"

        url = f"{self.base_url}/{media_id}"
        params = {
            "fields": "id,permalink,timestamp,media_type",
            "access_token": self.access_token
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.json().get("permalink")
        except Exception as e:
            logger.warning(f"Could not retrieve permalink for media {media_id}: {e}")

        return None
