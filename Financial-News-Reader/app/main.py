import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import Optional

from app.scraper.config_loader import ConfigLoader
from app.scraper.playwright_engine import PlaywrightNewsScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("financial-news-scraper")


async def scrape_feed(
    site_id: str,
    limit: Optional[int] = None,
    fetch_full: bool = False,
    headless: bool = True,
):
    """Scrape latest news feed for a configured site."""
    loader = ConfigLoader()
    config = loader.get(site_id)
    if not config:
        print(f"Error: Unknown site_id '{site_id}'. Available: {loader.list_sites()}")
        sys.exit(1)

    limit_desc = f"max {limit} items" if limit is not None else "unlimited items"
    print(f"\n--- Scraping feed: {config.site_name} ({limit_desc}) ---")
    async with PlaywrightNewsScraper(config=config, config_loader=loader, headless=headless) as scraper:
        if fetch_full:
            print("Fetching feed items AND full article contents...")
            articles = await scraper.fetch_feed_with_full_articles(max_items=limit)
        else:
            articles = await scraper.fetch_feed(max_items=limit)

        print(f"\nExtracted {len(articles)} articles:")
        for idx, art in enumerate(articles, 1):
            print(f"\n[{idx}] {art.title}")
            print(f"    Source:    {art.source}")
            print(f"    Published: {art.published_at}")
            print(f"    URL:       {art.url}")
            if art.description:
                print(f"    Desc:      {art.description[:120]}...")
            if art.article_text:
                print(f"    Body Text: {art.article_text[:160]}... ({len(art.article_text)} chars)")


async def scrape_article(url: str, headless: bool = True):
    """Scrape a single news article URL using domain-matched or generic JSON config."""
    loader = ConfigLoader()
    config = loader.get_for_url(url)
    print(f"\n--- Scraping Article: {url} ---")
    print(f"Matched Config: {config.site_name} (ID: {config.site_id})")

    async with PlaywrightNewsScraper(config=config, config_loader=loader, headless=headless) as scraper:
        article = await scraper.fetch_article(url)

        print("\n--- Extracted Article Details ---")
        print(f"Title:        {article.title}")
        print(f"Source:       {article.source}")
        print(f"Author:       {article.author or 'N/A'}")
        print(f"Published At: {article.published_at or 'N/A'}")
        print(f"Image URL:    {article.image_url or 'N/A'}")
        print(f"Tags:         {', '.join(article.tags) if article.tags else 'N/A'}")
        print(f"Description:  {article.description or 'N/A'}")
        print(f"Body Length:  {len(article.article_text) if article.article_text else 0} characters")
        if article.article_text:
            print("\nArticle Text Preview:")
            print("-" * 50)
            print(article.article_text[:600] + ("..." if len(article.article_text) > 600 else ""))
            print("-" * 50)


def str2bool(v: str | bool) -> bool:
    if isinstance(v, bool):
        return v
    if str(v).lower() in ("true", "1", "yes", "y", "t"):
        return True
    elif str(v).lower() in ("false", "0", "no", "n", "f"):
        return False
    raise argparse.ArgumentTypeError(f"Boolean value expected (true/false), got '{v}'.")


def add_headless_arguments(parser: argparse.ArgumentParser) -> None:
    """Helper to add consistent --headless option to CLI commands."""
    parser.add_argument(
        "--headless",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Run browser in headless mode (true/false, default: true)",
    )


def main():
    parser = argparse.ArgumentParser(
        description="JSON Config-Driven Playwright News Scraper Framework"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Feed command
    feed_parser = subparsers.add_parser("feed", help="Scrape latest news feed from a configured site")
    feed_parser.add_argument(
        "--site",
        "-s",
        type=str,
        default="zerodha_pulse",
        help="Site ID to scrape (e.g. zerodha_pulse, economic_times, moneycontrol)",
    )
    feed_parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Max number of items to scrape (default: unlimited)",
    )
    feed_parser.add_argument(
        "--full",
        action="store_true",
        help="Also fetch full article content for each feed item",
    )
    add_headless_arguments(feed_parser)

    # Article command
    art_parser = subparsers.add_parser("article", help="Scrape a single news article from a URL")
    art_parser.add_argument("url", type=str, help="URL of the news article to scrape")
    add_headless_arguments(art_parser)

    # List command
    subparsers.add_parser("list", help="List all registered JSON site configs")

    args = parser.parse_args()

    if args.command == "feed":
        asyncio.run(scrape_feed(args.site, args.limit, args.full, headless=args.headless))
    elif args.command == "article":
        asyncio.run(scrape_article(args.url, headless=args.headless))
    elif args.command == "list":
        loader = ConfigLoader()
        print("\nRegistered News Site Scraper Configurations:")
        for sid in sorted(loader.list_sites()):
            cfg = loader.get(sid)
            print(f"  • {cfg.site_id:20} -> {cfg.site_name} (Domains: {', '.join(cfg.domains)})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
