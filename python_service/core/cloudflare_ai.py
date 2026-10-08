import io
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import httpx
from PIL import Image, ImageDraw, ImageFont

from python_service.config import settings

logger = logging.getLogger("insta-genie.cloudflare_ai")


class CloudflareWorkersAI:
    """Client for Cloudflare Workers AI Text & Image Generation models."""

    def __init__(
        self,
        account_id: Optional[str] = None,
        api_token: Optional[str] = None,
        text_model: Optional[str] = None,
        image_model: Optional[str] = None,
        dry_run: Optional[bool] = None,
    ):
        self.account_id = account_id or settings.CLOUDFLARE_ACCOUNT_ID
        self.api_token = api_token or settings.CLOUDFLARE_API_TOKEN
        self.text_model = text_model or settings.CF_TEXT_MODEL
        self.image_model = image_model or settings.CF_IMAGE_MODEL
        self.dry_run = dry_run if dry_run is not None else settings.DRY_RUN
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run"

    async def generate_post_content(self, topic: str, tone: str = "engaging & professional") -> Dict[str, Any]:
        """
        Generate Instagram post caption, viral hook, and curated hashtags using Cloudflare Workers AI LLM.
        """
        if self.dry_run or not self.account_id or not self.api_token:
            logger.info("Running in DRY_RUN / Mock mode for text generation.")
            return self._mock_post_content(topic)

        system_prompt = (
            "You are an elite Instagram growth strategist and social media copywriter. "
            "Your job is to generate a high-converting Instagram post for a given topic. "
            "You MUST respond ONLY with valid JSON in this exact structure without markdown backticks:\n"
            "{\n"
            '  "hook": "Catchy first-line hook",\n'
            '  "caption": "Full body text formatted nicely with emojis, bullet points, and a strong CTA",\n'
            '  "hashtags": ["#tag1", "#tag2", "#tag3", ...],\n'
            '  "image_prompt": "A photorealistic, highly detailed, visually striking prompt for AI image generation (FLUX/SDXL style), 1:1 aspect ratio, cinematic lighting, 8k resolution, no text overlay."\n'
            "}"
        )

        user_prompt = f"Topic: {topic}\nTone: {tone}\nTarget Audience: Modern Instagram audience interested in innovation and lifestyle."

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.7
        }

        url = f"{self.base_url}/{self.text_model}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                raw_response = data.get("result", {}).get("response", "")
                parsed = self._extract_json(raw_response)
                
                # Sanitize and guarantee required fields
                caption = parsed.get("caption", f"✨ Exploring {topic}! What are your thoughts? Drop a comment below! 👇")
                hook = parsed.get("hook", f"Discover the magic of {topic}")
                hashtags = parsed.get("hashtags", [f"#{topic.replace(' ', '')}", "#InstaDaily", "#Innovation", "#ExplorePage"])
                image_prompt = parsed.get("image_prompt", f"High quality aesthetic photography representing {topic}, cinematic lighting, 8k resolution, photorealistic")

                # Ensure hashtags have # prefix and clean formatting
                formatted_hashtags = [
                    tag if tag.startswith("#") else f"#{tag}"
                    for tag in hashtags
                ]

                full_caption = f"{hook}\n\n{caption}\n\n.\n.\n{' '.join(formatted_hashtags)}"

                return {
                    "hook": hook,
                    "body": caption,
                    "hashtags": formatted_hashtags,
                    "full_caption": full_caption,
                    "image_prompt": image_prompt,
                    "model_used": self.text_model
                }

            except Exception as e:
                logger.error(f"Error calling Cloudflare Workers AI for text: {e}")
                logger.info("Falling back to local high-quality mock content generator.")
                return self._mock_post_content(topic)

    async def generate_image(self, prompt: str, filename_prefix: str = "insta_post") -> Tuple[bytes, str]:
        """
        Generate image using Cloudflare Workers AI (e.g. FLUX.1-schnell or SDXL Lightning).
        Returns (image_bytes, local_saved_path).
        """
        output_path = Path(settings.OUTPUT_DIR) / f"{filename_prefix}_{int(time.time())}.png"

        if self.dry_run or not self.account_id or not self.api_token:
            logger.info("Running in DRY_RUN / Mock mode for image generation.")
            mock_bytes = self._generate_mock_image(prompt)
            output_path.write_bytes(mock_bytes)
            return mock_bytes, str(output_path)

        url = f"{self.base_url}/{self.image_model}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        # Optimized payload for FLUX.1 or SDXL
        payload = {
            "prompt": prompt,
            "num_steps": 4 if "schnell" in self.image_model or "lightning" in self.image_model else 20
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                image_bytes = response.content

                # Verify image validity
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()

                output_path.write_bytes(image_bytes)
                logger.info(f"Image successfully generated and saved to {output_path}")
                return image_bytes, str(output_path)

            except Exception as e:
                logger.error(f"Error generating image via Cloudflare Workers AI: {e}")
                logger.info("Generating fallback aesthetic mock graphic.")
                mock_bytes = self._generate_mock_image(prompt)
                output_path.write_bytes(mock_bytes)
                return mock_bytes, str(output_path)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON object from model text response."""
        try:
            # First try direct parse
            return json.loads(text)
        except Exception:
            # Strip markdown codeblocks
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            # Try finding outer braces
            brace_match = re.search(r"\{.*\}", text, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except Exception:
                    pass
        return {}

    def _mock_post_content(self, topic: str) -> Dict[str, Any]:
        """High-grade mock response for local testing and dry-run demos."""
        clean_tag = re.sub(r'[^a-zA-Z0-9]', '', topic)
        hook = f"🚀 The Future of {topic} is Happening Right Now!"
        body = (
            f"Are you ready to level up your knowledge in {topic}?\n\n"
            f"Here are 3 key takeaways you need to know today:\n"
            f"1️⃣ Game-changing innovation is reshaping how we create and think.\n"
            f"2️⃣ Efficiency and consistency are the secrets to long-term success.\n"
            f"3️⃣ Staying ahead of the curve gives you an unfair advantage.\n\n"
            f"👉 Save this post for later & share your thoughts in the comments!"
        )
        hashtags = [
            f"#{clean_tag}",
            f"#{clean_tag}Tips",
            "#InstaGenie",
            "#Automation",
            "#ArtificialIntelligence",
            "#ContentCreation",
            "#ExplorePage",
            "#TechTrends",
            "#ViralPost",
            "#DigitalGrowth"
        ]
        image_prompt = (
            f"A futuristic, ultra-detailed 3D render representing {topic}, glowing neon elements, "
            f"sleek modern aesthetic, cinematic studio lighting, photorealistic, 8k resolution"
        )
        full_caption = f"{hook}\n\n{body}\n\n.\n.\n{' '.join(hashtags)}"

        return {
            "hook": hook,
            "body": body,
            "hashtags": hashtags,
            "full_caption": full_caption,
            "image_prompt": image_prompt,
            "model_used": "mock-workers-ai"
        }

    def _generate_mock_image(self, prompt: str) -> bytes:
        """Create a stylish fallback banner graphic when in offline/dry-run mode."""
        width, height = 1080, 1080
        img = Image.new("RGB", (width, height), color="#0F172A")
        draw = ImageDraw.Draw(img)

        # Draw decorative gradient-like accents
        for i in range(12):
            radius = 500 - (i * 35)
            alpha_color = (99 + i * 10, 102 + i * 8, 241 - i * 5)
            draw.ellipse(
                [(width // 2 - radius, height // 2 - radius),
                 (width // 2 + radius, height // 2 + radius)],
                outline=alpha_color,
                width=3
            )

        # Draw card in center
        card_bounds = [140, 300, 940, 780]
        draw.rounded_rectangle(card_bounds, radius=30, fill="#1E293B", outline="#6366F1", width=4)

        # Text on image
        title = "INSTA GENIE AI"
        subtitle = "Autonomous Instagram Agent"
        clean_prompt = prompt[:75] + "..." if len(prompt) > 75 else prompt

        # We use default font to avoid external font file dependencies
        draw.text((width // 2, 400), title, fill="#F8FAFC", anchor="mm")
        draw.text((width // 2, 480), subtitle, fill="#94A3B8", anchor="mm")
        draw.text((width // 2, 580), "Prompt Visual Preview:", fill="#38BDF8", anchor="mm")
        draw.text((width // 2, 640), f'"{clean_prompt}"', fill="#E2E8F0", anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
