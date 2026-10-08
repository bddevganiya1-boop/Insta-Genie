import argparse
import asyncio
import io
import logging
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from python_service.config import settings
from python_service.core.pipeline import InstaGeniePipeline

# Rich formatting helper
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console(highlight=False, legacy_windows=False)
    HAS_RICH = True
except Exception:
    HAS_RICH = False
    console = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def print_banner():
    if HAS_RICH and console:
        try:
            banner = (
                "[bold magenta]✨ INSTA GENIE AGENT[/bold magenta]\n"
                "[cyan]Autonomous Instagram Creation & Direct Publishing Engine[/cyan]\n\n"
                f"• [bold green]Workers AI Model:[/bold green] {settings.CF_TEXT_MODEL}\n"
                f"• [bold green]Image Model:[/bold green] {settings.CF_IMAGE_MODEL}\n"
                f"• [bold green]Meta Graph API:[/bold green] {settings.META_GRAPH_API_VERSION}\n"
                f"• [bold yellow]Mode:[/bold yellow] {'DRY_RUN (Safe Mock)' if settings.DRY_RUN else 'LIVE PRODUCTION'}"
            )
            console.print(Panel(banner, border_style="magenta", expand=False))
            return
        except Exception:
            pass

    print("\n========================================================")
    print("✨ INSTA GENIE - Autonomous AI Instagram Agent")
    print(f"• Workers AI: {settings.CF_TEXT_MODEL}")
    print(f"• Image Model: {settings.CF_IMAGE_MODEL}")
    print(f"• Meta API: {settings.META_GRAPH_API_VERSION}")
    print(f"• Mode: {'DRY_RUN (Safe Mock)' if settings.DRY_RUN else 'LIVE PRODUCTION'}")
    print("========================================================\n")


async def execute_single_run(topic: str):
    print_banner()
    print(f"\n🚀 Executing Autonomous Pipeline for: '{topic}'\n")

    pipeline = InstaGeniePipeline()
    result = await pipeline.execute_full_cycle(topic=topic, auto_publish=True)

    draft = result.get("draft", {})
    published = result.get("published", {})

    if HAS_RICH and console:
        try:
            table = Table(title="✨ Pipeline Execution Summary", border_style="cyan")
            table.add_column("Property", style="bold yellow")
            table.add_column("Value", style="bold white")

            table.add_row("Topic", str(topic))
            table.add_row("Hook", str(draft.get("hook")))
            table.add_row("Hashtags", " ".join(draft.get("hashtags", [])))
            table.add_row("Image Prompt", str(draft.get("image_prompt")))
            table.add_row("Local Image", str(draft.get("local_image_path")))
            table.add_row("Instagram Post ID", str(published.get("published_media_id")))
            table.add_row("Instagram Permalink", str(published.get("permalink")))

            console.print(table)
            console.print("\n[bold green]✅ Success! Post generated and published.[/bold green]\n")
            return
        except Exception:
            pass

    print("--------------------------------------------------------")
    print(f"Topic: {topic}")
    print(f"Hook: {draft.get('hook')}")
    print(f"Hashtags: {' '.join(draft.get('hashtags', []))}")
    print(f"Local Image: {draft.get('local_image_path')}")
    print(f"Instagram Post ID: {published.get('published_media_id')}")
    print(f"Permalink: {published.get('permalink')}")
    print("--------------------------------------------------------")
    print("✅ Success! Post generated and published.\n")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    try:
        import uvicorn
        print(f"Starting Web UI on http://localhost:{port}")
        uvicorn.run("python_service.web.app:app", host=host, port=port, reload=False)
    except ImportError:
        print("Error: uvicorn is not installed. Please install dependencies via: pip install -r python_service/requirements.txt")


def cli():
    parser = argparse.ArgumentParser(description="Insta Genie - Autonomous AI Instagram Content & Publishing Engine")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI Web UI Dashboard and API server.")
    parser.add_argument("--run-now", action="store_true", help="Execute single generation & publish cycle immediately.")
    parser.add_argument("--topic", type=str, default="Autonomous AI Agents in 2026", help="Custom topic for the generation run.")
    parser.add_argument("--dry-run", action="store_true", help="Force mock dry-run mode.")
    parser.add_argument("--port", type=int, default=8000, help="Server port.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host.")

    args = parser.parse_args()

    if args.dry_run:
        settings.DRY_RUN = True

    if args.run_now:
        asyncio.run(execute_single_run(args.topic))
    elif args.serve:
        print_banner()
        run_server(host=args.host, port=args.port)
    else:
        print_banner()
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    cli()
