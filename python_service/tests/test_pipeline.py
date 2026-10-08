import pytest
from unittest.mock import AsyncMock, patch

from python_service.config import settings
from python_service.core.cloudflare_ai import CloudflareWorkersAI
from python_service.core.image_uploader import ImageUploader
from python_service.core.instagram_api import MetaInstagramGraphAPI
from python_service.core.pipeline import InstaGeniePipeline


@pytest.fixture(autouse=True)
def force_dry_run():
    original = settings.DRY_RUN
    settings.DRY_RUN = True
    yield
    settings.DRY_RUN = original


@pytest.mark.asyncio
async def test_cloudflare_ai_mock_post_content():
    ai = CloudflareWorkersAI(dry_run=True)
    content = await ai.generate_post_content("Quantum Computing Breakthroughs")

    assert "hook" in content
    assert "body" in content
    assert "hashtags" in content
    assert len(content["hashtags"]) > 0
    assert "image_prompt" in content
    assert "Quantum" in content["hook"] or "Quantum" in content["body"]


@pytest.mark.asyncio
async def test_cloudflare_ai_mock_image_generation():
    ai = CloudflareWorkersAI(dry_run=True)
    image_bytes, local_path = await ai.generate_image("Futuristic glowing cybernetic city")

    assert len(image_bytes) > 0
    assert local_path.endswith(".png")


@pytest.mark.asyncio
async def test_meta_instagram_api_mock_flow():
    api = MetaInstagramGraphAPI(dry_run=True)
    
    # 1. Profile check
    profile = await api.get_account_profile()
    assert "username" in profile
    assert profile["is_mock"] is True

    # 2. Container creation
    container_id = await api.create_media_container(
        image_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&q=80",
        caption="Test caption #test"
    )
    assert container_id.startswith("mock_container")

    # 3. Ready polling
    is_ready = await api.wait_for_container_ready(container_id)
    assert is_ready is True

    # 4. Publication
    pub_result = await api.publish_media(container_id)
    assert pub_result["status"] == "PUBLISHED_MOCK"
    assert "permalink" in pub_result


@pytest.mark.asyncio
async def test_full_pipeline_execution():
    pipeline = InstaGeniePipeline()
    result = await pipeline.execute_full_cycle(
        topic="Autonomous Coding Agents",
        tone="professional",
        auto_publish=True
    )

    assert result["status"] == "COMPLETED"
    assert result["topic"] == "Autonomous Coding Agents"
    assert "draft" in result
    assert "published" in result
    assert result["published"]["success"] is True
    assert result["published"]["permalink"].startswith("https://www.instagram.com")
