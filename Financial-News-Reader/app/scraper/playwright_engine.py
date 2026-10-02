import asyncio
import logging
from typing import List, Optional
from urllib.parse import urlparse

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.models.config_schema import SelectorConfig, SiteConfig
from app.models.news import NewsArticle
from app.scraper.config_loader import ConfigLoader
from app.scraper.extractor import dismiss_overlays, extract_content, extract_field

logger = logging.getLogger(__name__)


class PlaywrightNewsScraper:
    """Config-driven scraper powered by Playwright and JSON site definitions."""

    def __init__(
        self,
        config: Optional[SiteConfig] = None,
        config_loader: Optional[ConfigLoader] = None,
        headless: Optional[bool] = None,
    ):
        self.config = config
        self.config_loader = config_loader or ConfigLoader()
        self._custom_headless = headless

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> "PlaywrightNewsScraper":
        """Initialize Playwright and launch the browser instance."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        headless = (
            self._custom_headless
            if self._custom_headless is not None
            else (self.config.browser.headless if self.config else True)
        )

        args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=args,
        )

        # Context settings
        user_agent = (
            self.config.browser.user_agent
            if self.config and self.config.browser.user_agent
            else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        viewport = (
            {
                "width": self.config.browser.viewport_width,
                "height": self.config.browser.viewport_height,
            }
            if self.config
            else {"width": 1280, "height": 800}
        )
        default_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Upgrade-Insecure-Requests": "1",
        }
        if self.config and self.config.browser.extra_headers:
            default_headers.update(self.config.browser.extra_headers)

        self._context = await self._browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            extra_http_headers=default_headers,
        )
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return self

    async def close(self) -> None:
        """Close browser context and stop Playwright."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self) -> "PlaywrightNewsScraper":
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _is_allowed_url(self, url: str) -> bool:
        """Checks if a URL belongs to the allowed domains for this site configuration."""
        if not self.config:
            return True

        feed_cfg = self.config.feed
        allowed = None
        if feed_cfg and getattr(feed_cfg, "allowed_domains", None):
            allowed = feed_cfg.allowed_domains
        elif self.config.domains:
            allowed = self.config.domains

        if not allowed or "*" in allowed:
            return True

        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if not netloc:
            return True

        allowed_normalized = {d.lower().strip() for d in allowed if d.strip()}

        # Direct match
        if netloc in allowed_normalized:
            return True

        # Check domain equivalence (with/without www.) or subdomains if allowed entry was a root domain
        for d in allowed_normalized:
            if not d.startswith("www."):
                if netloc == f"www.{d}" or netloc.endswith(f".{d}"):
                    return True
            else:
                if netloc == d[4:]:
                    return True

        return False

    def _resolve_config_for_url(self, url: str) -> SiteConfig:
        """Determines the appropriate SiteConfig for a given URL."""
        if self.config and self._is_allowed_url(url):
            return self.config
        return self.config_loader.get_for_url(url)

    async def fetch_feed(self, max_items: Optional[int] = None) -> List[NewsArticle]:
        """Scrape articles listed on the site's feed / latest news page."""
        if not self.config or not self.config.feed:
            raise ValueError(
                f"Config '{getattr(self.config, 'site_id', 'unknown')}' does not have a 'feed' configuration defined."
            )

        if not self._context:
            await self.start()

        feed_cfg = self.config.feed
        browser_cfg = self.config.browser
        page: Page = await self._context.new_page()

        articles: List[NewsArticle] = []

        try:
            logger.info(f"Navigating to feed URL: {feed_cfg.url}")
            await page.goto(
                feed_cfg.url,
                wait_until=browser_cfg.wait_until,
                timeout=browser_cfg.timeout_ms,
            )

            # Dismiss cookie banners or popups
            all_dismiss = browser_cfg.dismiss_selectors + self.config.article.dismiss_selectors
            if all_dismiss:
                await dismiss_overlays(page, all_dismiss)

            # Wait for container or items if specified
            if feed_cfg.wait_for_selector:
                try:
                    await page.wait_for_selector(
                        feed_cfg.wait_for_selector,
                        timeout=browser_cfg.timeout_ms,
                    )
                except PlaywrightTimeoutError:
                    logger.warning(
                        f"Timeout waiting for feed container selector: '{feed_cfg.wait_for_selector}'"
                    )

            # Handle pagination / infinite scroll
            if feed_cfg.pagination.type == "scroll":
                for _ in range(feed_cfg.pagination.scroll_count):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(feed_cfg.pagination.scroll_delay_seconds)
            elif feed_cfg.pagination.type == "click" and feed_cfg.pagination.load_more_selector:
                btn = page.locator(feed_cfg.pagination.load_more_selector)
                if await btn.count() > 0 and await btn.first.is_visible():
                    await btn.first.click()
                    await asyncio.sleep(feed_cfg.pagination.scroll_delay_seconds)

            # Locate article items
            items_locator = page.locator(feed_cfg.item_selector)
            items_count = await items_locator.count()
            logger.info(f"Found {items_count} items matching selector '{feed_cfg.item_selector}'")

            items = await items_locator.all()

            fields = feed_cfg.fields
            base_url = self.config.base_url
            seen_urls = set()

            for item in items:
                if max_items is not None and len(articles) >= max_items:
                    break

                try:
                    title = await extract_field(item, fields.title, base_url)
                    url = await extract_field(item, fields.url, base_url)

                    if not title or not url:
                        continue

                    # Filter out links outside of allowed domains
                    if not self._is_allowed_url(url):
                        logger.debug(f"Ignoring external link outside allowed domains: {url}")
                        continue

                    # Deduplicate feed URLs
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Optional fields
                    article_id = (
                        await extract_field(item, fields.article_id, base_url)
                        if fields.article_id
                        else None
                    )
                    published_at = (
                        await extract_field(item, fields.published_at, base_url)
                        if fields.published_at
                        else ""
                    )
                    description = (
                        await extract_field(item, fields.description, base_url)
                        if fields.description
                        else None
                    )

                    # Source
                    source = self.config.site_name
                    if fields.source:
                        extracted_source = await extract_field(item, fields.source, base_url)
                        if extracted_source:
                            source = extracted_source

                    articles.append(
                        NewsArticle(
                            article_id=article_id,
                            title=title,
                            url=url,
                            source=source,
                            published_at=published_at or "",
                            description=description,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error parsing feed item: {e}")
                    continue

        finally:
            await page.close()

        logger.info(f"Successfully scraped {len(articles)} articles from feed.")
        return articles

    async def fetch_article(
        self,
        url: str,
        site_config: Optional[SiteConfig] = None,
    ) -> NewsArticle:
        """Scrape full content and metadata for a single news article URL."""
        if not self._context:
            await self.start()

        cfg = site_config or self._resolve_config_for_url(url)
        art_cfg = cfg.article
        fields = art_cfg.fields
        browser_cfg = cfg.browser

        page: Page = await self._context.new_page()

        try:
            logger.info(f"Navigating to article: {url} (Config: {cfg.site_id})")
            await page.goto(
                url,
                wait_until=browser_cfg.wait_until,
                timeout=browser_cfg.timeout_ms,
            )

            # Dismiss popups / overlays
            all_dismiss = browser_cfg.dismiss_selectors + art_cfg.dismiss_selectors
            if all_dismiss:
                await dismiss_overlays(page, all_dismiss)

            # Wait for content
            if art_cfg.wait_for_selector:
                try:
                    await page.wait_for_selector(
                        art_cfg.wait_for_selector,
                        timeout=browser_cfg.timeout_ms,
                    )
                except PlaywrightTimeoutError:
                    logger.warning(
                        f"Timeout waiting for article selector: '{art_cfg.wait_for_selector}' on {url}"
                    )

            # Click expand/read-more if configured
            if art_cfg.click_to_expand_selector:
                try:
                    expand_btn = page.locator(art_cfg.click_to_expand_selector)
                    if await expand_btn.count() > 0 and await expand_btn.first.is_visible():
                        await expand_btn.first.click(timeout=2000)
                        await asyncio.sleep(0.5)
                except Exception:
                    pass

            # Scroll if needed
            if art_cfg.scroll_before_extract:
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)

            # Extract fields
            title = await extract_field(page, fields.title, cfg.base_url)
            published_at = (
                await extract_field(page, fields.published_at, cfg.base_url)
                if fields.published_at
                else ""
            )
            author = (
                await extract_field(page, fields.author, cfg.base_url)
                if fields.author
                else None
            )
            description = (
                await extract_field(page, fields.description, cfg.base_url)
                if fields.description
                else None
            )
            tags = (
                await extract_field(page, fields.tags, cfg.base_url)
                if fields.tags
                else []
            )
            image_url = (
                await extract_field(page, fields.image_url, cfg.base_url)
                if fields.image_url
                else None
            )

            # Article body text
            article_text = await extract_content(page, fields.content)

            # Determine source
            source = cfg.site_name
            if isinstance(fields.source, str):
                source = fields.source
            elif isinstance(fields.source, SelectorConfig):
                extracted_source = await extract_field(page, fields.source, cfg.base_url)
                if extracted_source:
                    source = extracted_source

            if not tags:
                tags = []
            elif isinstance(tags, str):
                tags = [tags]

            return NewsArticle(
                title=title or "Untitled",
                url=url,
                source=source,
                published_at=published_at or "",
                description=description,
                article_text=article_text,
                author=author,
                tags=tags,
                image_url=image_url,
            )

        finally:
            await page.close()

    async def fetch_feed_with_full_articles(
        self,
        max_items: Optional[int] = None,
    ) -> List[NewsArticle]:
        """Fetches the latest feed items and then visits each article URL to extract full text."""
        feed_articles = await self.fetch_feed(max_items=max_items)
        detailed_articles: List[NewsArticle] = []

        delay = self.config.browser.rate_limit_delay_seconds if self.config else 0.5

        for item in feed_articles:
            try:
                full_article = await self.fetch_article(item.url)
                # Preserve any feed-specific fields if detail page was sparse
                if not full_article.description and item.description:
                    full_article.description = item.description
                if not full_article.published_at and item.published_at:
                    full_article.published_at = item.published_at
                if item.article_id:
                    full_article.article_id = item.article_id

                detailed_articles.append(full_article)
            except Exception as e:
                logger.error(f"Failed to fetch article details for {item.url}: {e}")
                # Fallback to feed item so we don't lose the article completely
                detailed_articles.append(item)

            if delay > 0:
                await asyncio.sleep(delay)

        return detailed_articles

    @classmethod
    async def scrape_feed_site(
        cls,
        site_id: str,
        max_items: Optional[int] = None,
        fetch_full: bool = False,
        config_loader: Optional[ConfigLoader] = None,
        headless: bool = True,
    ) -> List[NewsArticle]:
        """One-shot helper to scrape feed articles for a site_id using its JSON config."""
        loader = config_loader or ConfigLoader()
        config = loader.get(site_id)
        if not config:
            raise ValueError(
                f"Unknown site_id '{site_id}'. Available: {loader.list_sites()}"
            )
        async with cls(config=config, config_loader=loader, headless=headless) as scraper:
            if fetch_full:
                return await scraper.fetch_feed_with_full_articles(max_items=max_items)
            return await scraper.fetch_feed(max_items=max_items)

    @classmethod
    async def scrape_article_url(
        cls,
        url: str,
        config_loader: Optional[ConfigLoader] = None,
        headless: bool = True,
    ) -> NewsArticle:
        """One-shot helper to scrape an article from any news URL using auto-matched JSON config."""
        loader = config_loader or ConfigLoader()
        config = loader.get_for_url(url)
        async with cls(config=config, config_loader=loader, headless=headless) as scraper:
            return await scraper.fetch_article(url)

