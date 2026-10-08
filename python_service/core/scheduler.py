import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from python_service.config import settings
from python_service.core.pipeline import InstaGeniePipeline

logger = logging.getLogger("insta-genie.scheduler")

# Try importing APScheduler, fallback to native asyncio timer loop
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False


class AutomationScheduler:
    """Automated scheduling agent for recurrent Instagram publishing."""

    def __init__(self, pipeline: Optional[InstaGeniePipeline] = None):
        self.pipeline = pipeline or InstaGeniePipeline()
        self.is_running = False
        self.history_logs: List[Dict[str, Any]] = []
        self._async_task: Optional[asyncio.Task] = None
        self._next_run_time: Optional[datetime] = None

        if HAS_APSCHEDULER:
            self.scheduler = AsyncIOScheduler()
        else:
            self.scheduler = None

    def start(self, interval_hours: Optional[int] = None):
        """Start the automated cron-like publishing schedule."""
        interval = interval_hours or settings.SCHEDULE_INTERVAL_HOURS
        if self.is_running:
            logger.warning("Scheduler is already running.")
            return

        self.is_running = True
        self._next_run_time = datetime.utcnow() + timedelta(hours=interval)

        if HAS_APSCHEDULER and self.scheduler:
            trigger = IntervalTrigger(hours=interval)
            self.scheduler.add_job(
                self.trigger_scheduled_post,
                trigger=trigger,
                id="insta_genie_auto_poster",
                name="Insta Genie Autonomous Publisher",
                replace_existing=True,
            )
            self.scheduler.start()
        else:
            # Fallback to pure asyncio background loop
            self._async_task = asyncio.create_task(self._run_async_loop(interval))

        logger.info(f"Automation Scheduler started. Posting every {interval} hours.")

    def stop(self):
        """Stop the automated publishing schedule."""
        if self.is_running:
            if HAS_APSCHEDULER and self.scheduler:
                self.scheduler.shutdown(wait=False)
            if self._async_task:
                self._async_task.cancel()
                self._async_task = None
            self.is_running = False
            self._next_run_time = None
            logger.info("Automation Scheduler stopped.")

    async def _run_async_loop(self, interval_hours: int):
        """Pure asyncio loop fallback when apscheduler is not installed."""
        while self.is_running:
            try:
                await asyncio.sleep(interval_hours * 3600)
                if not self.is_running:
                    break
                await self.trigger_scheduled_post()
                self._next_run_time = datetime.utcnow() + timedelta(hours=interval_hours)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler background loop: {e}")

    async def trigger_scheduled_post(self) -> Dict[str, Any]:
        """Runs an autonomous post cycle using a randomly selected topic from the pool."""
        topics = settings.topics_list or ["Artificial Intelligence Trends", "Digital Innovation"]
        selected_topic = random.choice(topics)

        logger.info(f"Scheduled job triggered for topic: '{selected_topic}'")
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "topic": selected_topic,
            "status": "PROCESSING"
        }
        self.history_logs.append(log_entry)

        try:
            result = await self.pipeline.execute_full_cycle(
                topic=selected_topic,
                tone="inspirational & engaging",
                auto_publish=True
            )
            log_entry["status"] = "SUCCESS"
            log_entry["result"] = result
            logger.info(f"Scheduled post completed successfully: {result.get('published', {}).get('permalink')}")
            return result
        except Exception as e:
            logger.error(f"Error during scheduled post cycle: {e}")
            log_entry["status"] = "FAILED"
            log_entry["error"] = str(e)
            return log_entry

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler health, next run time, and recent activity logs."""
        next_run = None
        if HAS_APSCHEDULER and self.scheduler and self.is_running:
            job = self.scheduler.get_job("insta_genie_auto_poster")
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
        elif self._next_run_time and self.is_running:
            next_run = self._next_run_time.isoformat()

        return {
            "is_running": self.is_running,
            "interval_hours": settings.SCHEDULE_INTERVAL_HOURS,
            "next_run_time": next_run,
            "topics_pool": settings.topics_list,
            "recent_runs": self.history_logs[-15:]
        }
