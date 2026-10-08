import logging
import time
from typing import Dict, Any, Optional
from python_service.config import settings
from python_service.core.cloudflare_ai import CloudflareWorkersAI
from python_service.core.image_uploader import ImageUploader
from python_service.core.instagram_api import MetaInstagramGraphAPI

logger = logging.getLogger("insta-genie.pipeline")


class InstaGeniePipeline:
    """End-to-end agent pipeline for generating and publishing Instagram content."""

    def __init__(
        self,
        cf_ai: Optional[CloudflareWorkersAI] = None,
        uploader: Optional[ImageUploader] = None,
        ig_api: Optional[MetaInstagramGraphAPI] = None,
    ):
        self.cf_ai = cf_ai or CloudflareWorkersAI()
        self.uploader = uploader or ImageUploader()
        self.ig_api = ig_api or MetaInstagramGraphAPI()

    async def generate_draft(self, topic: str, tone: str = "engaging & informative") -> Dict[str, Any]:
        """
        Step A: Generate caption, hashtags, image prompt, and image binary.
        """
        start_time = time.time()
        logger.info(f"Starting post generation for topic: '{topic}'")

        # 1. Generate text content (caption, hooks, hashtags, image prompt)
        text_content = await self.cf_ai.generate_post_content(topic, tone=tone)

        # 2. Generate image based on engineered prompt
        image_bytes, local_path = await self.cf_ai.generate_image(
            prompt=text_content["image_prompt"],
            filename_prefix="post"
        )

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Post drafted successfully in {elapsed}s")

        return {
            "topic": topic,
            "hook": text_content["hook"],
            "body": text_content["body"],
            "hashtags": text_content["hashtags"],
            "full_caption": text_content["full_caption"],
            "image_prompt": text_content["image_prompt"],
            "local_image_path": local_path,
            "image_bytes": image_bytes,
            "elapsed_seconds": elapsed,
            "model_text": text_content.get("model_used", "Cloudflare Workers AI"),
            "model_image": self.cf_ai.image_model
        }

    async def publish_post(
        self,
        image_bytes: Optional[bytes] = None,
        public_image_url: Optional[str] = None,
        caption: str = "",
        filename: str = "insta_post.png"
    ) -> Dict[str, Any]:
        """
        Step B: Ensure public HTTPS URL, create IG container, poll status, and publish.
        """
        start_time = time.time()

        # 1. Obtain public URL for image if not already supplied
        if not public_image_url:
            if not image_bytes:
                raise ValueError("Either image_bytes or public_image_url must be provided.")
            logger.info("Uploading image to public host for Meta Graph API ingest...")
            public_image_url = await self.uploader.upload_image(image_bytes, filename=filename)

        logger.info(f"Target Public Image URL: {public_image_url}")

        # 2. Create Instagram container
        logger.info("Creating Meta Graph API Media Container...")
        container_id = await self.ig_api.create_media_container(
            image_url=public_image_url,
            caption=caption
        )

        # 3. Wait for Meta processing
        logger.info(f"Waiting for Container {container_id} to be ready...")
        is_ready = await self.ig_api.wait_for_container_ready(container_id)
        if not is_ready:
            raise RuntimeError(f"Instagram media container {container_id} failed readiness verification.")

        # 4. Publish to Instagram feed
        logger.info("Publishing media container...")
        publish_result = await self.ig_api.publish_media(container_id)

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Publishing completed in {elapsed}s! Permalink: {publish_result.get('permalink')}")

        return {
            "success": True,
            "container_id": container_id,
            "public_image_url": public_image_url,
            "published_media_id": publish_result.get("id"),
            "permalink": publish_result.get("permalink"),
            "status": publish_result.get("status"),
            "elapsed_seconds": elapsed
        }

    async def execute_full_cycle(
        self,
        topic: str,
        tone: str = "engaging & informative",
        auto_publish: bool = True
    ) -> Dict[str, Any]:
        """
        Executes complete autonomous loop: Idea -> Content & Image -> Host -> Post.
        """
        # Step 1: Draft
        draft = await self.generate_draft(topic=topic, tone=tone)

        if not auto_publish:
            return {
                "status": "DRAFT_READY",
                "draft": draft,
                "published": None
            }

        # Step 2: Publish
        publish_result = await self.publish_post(
            image_bytes=draft["image_bytes"],
            caption=draft["full_caption"],
            filename=f"post_{int(time.time())}.png"
        )

        return {
            "status": "COMPLETED",
            "topic": topic,
            "draft": {k: v for k, v in draft.items() if k != "image_bytes"},
            "published": publish_result
        }
