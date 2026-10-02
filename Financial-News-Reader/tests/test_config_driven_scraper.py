import pytest
from pathlib import Path
from playwright.async_api import async_playwright

from app.models.config_schema import (
    ArticleConfig,
    ArticleFieldsConfig,
    BrowserConfig,
    ContentExtractorConfig,
    FeedConfig,
    FeedFieldsConfig,
    SelectorConfig,
    SiteConfig,
)
from app.scraper.config_loader import ConfigLoader
from app.scraper.extractor import extract_content, extract_field
from app.scraper.playwright_engine import PlaywrightNewsScraper


def test_config_loader():
    """Verify loading and registering JSON configs from configs directory."""
    loader = ConfigLoader()
    sites = loader.list_sites()

    assert "zerodha_pulse" in sites
    assert "economic_times" in sites
    assert "moneycontrol" in sites
    assert "generic_article" in sites
    assert "financialexpress" in sites


def test_domain_routing():
    """Verify that URLs are automatically mapped to their respective site configs."""
    loader = ConfigLoader()

    # Zerodha Pulse
    cfg_pulse = loader.get_for_url("https://pulse.zerodha.com/news/12345")
    assert cfg_pulse.site_id == "zerodha_pulse"

    # Economic Times
    cfg_et = loader.get_for_url("https://economictimes.indiatimes.com/markets/stocks/news/tata-motors-q2/articleshow/123.cms")
    assert cfg_et.site_id == "economic_times"

    # Moneycontrol
    cfg_mc = loader.get_for_url("https://www.moneycontrol.com/news/business/markets/reliance-deal-123.html")
    assert cfg_mc.site_id == "moneycontrol"

    # Financial Express
    cfg_fe = loader.get_for_url("https://www.financialexpress.com/market/stock-insights/enviro-infra-growth/4350812/")
    assert cfg_fe.site_id == "financialexpress"

    # Generic Fallback
    cfg_generic = loader.get_for_url("https://www.reuters.com/markets/wealth/global-markets-2026-09-28/")
    assert cfg_generic.site_id == "generic_article"


@pytest.mark.asyncio
async def test_field_extraction_and_cleaning():
    """Test extractor logic on simulated HTML content with fallbacks and regex."""
    html = """
    <html>
      <head>
        <meta property="og:title" content="Meta Title Fallback" />
        <meta name="author" content="Jane Analyst" />
        <meta property="article:published_time" content="2026-09-28T10:00:00Z" />
      </head>
      <body>
        <div class="news-card">
          <h2 class="headline"><a href="/news/item-42" data-id="item-42">  RBI Keeps Repo Rate Unchanged at 6.5% - Livemint  </a></h2>
          <span class="source">— Livemint News</span>
          <span class="date" title="28 Sep 2026, 10:30 AM">2 hours ago</span>
          <div class="tags">
            <span class="tag">Economy</span>
            <span class="tag">Banking</span>
            <span class="tag">RBI</span>
          </div>
        </div>
      </body>
    </html>
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html)

        card = page.locator(".news-card")

        # 1. Title extraction with strip
        title_cfg = SelectorConfig(selector="h2.headline a", attribute="text")
        title = await extract_field(card, title_cfg)
        assert title == "RBI Keeps Repo Rate Unchanged at 6.5% - Livemint"

        # 2. URL extraction with base_url resolution
        url_cfg = SelectorConfig(selector="h2.headline a", attribute="href")
        url = await extract_field(card, url_cfg, base_url="https://pulse.zerodha.com")
        assert url == "https://pulse.zerodha.com/news/item-42"

        # 3. Source extraction with regex strip of "—"
        source_cfg = SelectorConfig(
            selector="span.source",
            attribute="text",
            clean_regex="^[—\\-\\s]+",
        )
        source = await extract_field(card, source_cfg)
        assert source == "Livemint News"

        # 4. Attribute fallback: span title attribute preferred over relative text
        date_cfg = SelectorConfig(
            selector="span.date",
            attribute="title",
            fallback_attribute="text",
        )
        date_val = await extract_field(card, date_cfg)
        assert date_val == "28 Sep 2026, 10:30 AM"

        # 5. List extraction for tags
        tags_cfg = SelectorConfig(selector=".tags .tag", attribute="text", is_list=True)
        tags = await extract_field(card, tags_cfg)
        assert tags == ["Economy", "Banking", "RBI"]

        # 6. Fallback selector test: primary missing, fallback to meta tag
        author_cfg = SelectorConfig(
            selector=".non-existent-author",
            fallbacks=["meta[name='author']"],
            attribute="text",
        )
        author = await extract_field(page, author_cfg)
        assert author == "Jane Analyst"

        await browser.close()


@pytest.mark.asyncio
async def test_content_extraction_and_sanitization():
    """Test extracting article body paragraphs while stripping ads and scripts."""
    html = """
    <html>
      <body>
        <article class="article-body">
          <p>The Reserve Bank of India on Monday kept the benchmark repo rate steady.</p>
          <div class="ad advertisement">Buy this stock now! Sponsored link.</div>
          <p>Governor noted that inflation has moderated within the target band of 4%.</p>
          <script>console.log("analytics code");</script>
          <div class="related-news">Related: 5 stocks to watch today</div>
          <p>The monetary policy committee voted unanimously to maintain status quo.</p>
        </article>
      </body>
    </html>
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html)

        content_cfg = ContentExtractorConfig(
            container_selector="article.article-body",
            paragraph_selector="p",
            exclude_selectors=[".ad", ".advertisement", ".related-news", "script"],
            join_delimiter="\n\n",
        )

        content = await extract_content(page, content_cfg)
        assert "The Reserve Bank of India on Monday kept the benchmark repo rate steady." in content
        assert "Governor noted that inflation has moderated within the target band of 4%." in content
        assert "The monetary policy committee voted unanimously to maintain status quo." in content

        # Ads and related items must be removed
        assert "Buy this stock now!" not in content
        assert "Sponsored link" not in content
        assert "analytics code" not in content
        assert "Related: 5 stocks to watch today" not in content

        await browser.close()


@pytest.mark.asyncio
async def test_playwright_scraper_with_custom_config():
    """Test end-to-end PlaywrightNewsScraper execution on mock HTML."""
    feed_html = """
    <html>
      <body>
        <ul id="news">
          <li class="box item">
            <h2 class="title"><a href="/articles/1" data-id="art-1">HDFC Bank reports 15% credit growth</a></h2>
            <div class="desc">HDFC Bank released its quarterly loan book update.</div>
            <span class="date" title="28 Sep 2026, 12:00 PM">Just now</span>
            <span class="feed">— Reuters</span>
          </li>
          <li class="box item">
            <h2 class="title"><a href="/articles/2" data-id="art-2">TCS bags $500M European cloud deal</a></h2>
            <div class="desc">Deal expands multi-year enterprise transformation engagement.</div>
            <span class="date" title="28 Sep 2026, 11:30 AM">30 mins ago</span>
            <span class="feed">— Economic Times</span>
          </li>
        </ul>
      </body>
    </html>
    """

    config = SiteConfig(
        site_id="test_feed_site",
        site_name="Test Financial News",
        base_url="https://testnews.local",
        feed=FeedConfig(
            url="data:text/html;charset=utf-8," + feed_html,
            item_selector="ul#news li.box.item",
            fields=FeedFieldsConfig(
                title=SelectorConfig(selector="h2.title a", attribute="text"),
                url=SelectorConfig(selector="h2.title a", attribute="href"),
                article_id=SelectorConfig(selector="h2.title a", attribute="data-id"),
                description=SelectorConfig(selector="div.desc", attribute="text"),
                published_at=SelectorConfig(selector="span.date", attribute="title"),
                source=SelectorConfig(selector="span.feed", attribute="text", clean_regex="^[—\\-\\s]+"),
            ),
        ),
    )

    async with PlaywrightNewsScraper(config=config, headless=True) as scraper:
        articles = await scraper.fetch_feed()
        assert len(articles) == 2

        assert articles[0].article_id == "art-1"
        assert articles[0].title == "HDFC Bank reports 15% credit growth"
        assert articles[0].url == "https://testnews.local/articles/1"
        assert articles[0].source == "Reuters"
        assert articles[0].published_at == "28 Sep 2026, 12:00 PM"
        assert articles[0].description == "HDFC Bank released its quarterly loan book update."

        assert articles[1].article_id == "art-2"
        assert articles[1].title == "TCS bags $500M European cloud deal"
        assert articles[1].source == "Economic Times"


@pytest.mark.asyncio
async def test_scrape_feed_site_helper_and_headless():
    """Verify scrape_feed_site classmethod accepts headless option and executes properly."""
    feed_html = """
    <html>
      <body>
        <ul id="news">
          <li class="box item">
            <h2 class="title"><a href="/item/1">Sample News Headline</a></h2>
          </li>
        </ul>
      </body>
    </html>
    """

    config = SiteConfig(
        site_id="mock_site_headless",
        site_name="Mock Site Headless",
        base_url="https://mocksite.local",
        feed=FeedConfig(
            url="data:text/html;charset=utf-8," + feed_html,
            item_selector="ul#news li.box.item",
            fields=FeedFieldsConfig(
                title=SelectorConfig(selector="h2.title a", attribute="text"),
                url=SelectorConfig(selector="h2.title a", attribute="href"),
            ),
        ),
    )

    loader = ConfigLoader()
    loader.register(config)

    # Test scrape_feed_site with headless=True
    articles_headless = await PlaywrightNewsScraper.scrape_feed_site(
        "mock_site_headless",
        config_loader=loader,
        headless=True,
    )
    assert len(articles_headless) == 1
    assert articles_headless[0].title == "Sample News Headline"

    # Test PlaywrightNewsScraper instance headless flag setting
    scraper_headless = PlaywrightNewsScraper(config=config, headless=True)
    assert scraper_headless._custom_headless is True

    scraper_headful = PlaywrightNewsScraper(config=config, headless=False)
    assert scraper_headful._custom_headless is False


@pytest.mark.asyncio
async def test_unlimited_feed_scraping_by_default():
    """Verify that when max_items is None, all available items on page are scraped."""
    feed_html = """
    <html>
      <body>
        <ul id="news">
          <li class="box item"><h2 class="title"><a href="/1">Headline 1</a></h2></li>
          <li class="box item"><h2 class="title"><a href="/2">Headline 2</a></h2></li>
          <li class="box item"><h2 class="title"><a href="/3">Headline 3</a></h2></li>
          <li class="box item"><h2 class="title"><a href="/4">Headline 4</a></h2></li>
          <li class="box item"><h2 class="title"><a href="/5">Headline 5</a></h2></li>
          <li class="box item"><h2 class="title"><a href="/6">Headline 6</a></h2></li>
        </ul>
      </body>
    </html>
    """

    config = SiteConfig(
        site_id="mock_site_unlimited",
        site_name="Mock Site Unlimited",
        base_url="https://mockunlimited.local",
        feed=FeedConfig(
            url="data:text/html;charset=utf-8," + feed_html,
            item_selector="ul#news li.box.item",
            fields=FeedFieldsConfig(
                title=SelectorConfig(selector="h2.title a", attribute="text"),
                url=SelectorConfig(selector="h2.title a", attribute="href"),
            ),
        ),
    )

    async with PlaywrightNewsScraper(config=config, headless=True) as scraper:
        # Unlimited by default (max_items=None)
        unlimited_articles = await scraper.fetch_feed(max_items=None)
        assert len(unlimited_articles) == 6

        # Capped when max_items is explicitly defined
        capped_articles = await scraper.fetch_feed(max_items=3)
        assert len(capped_articles) == 3


@pytest.mark.asyncio
async def test_feed_filters_external_domains():
    """Verify that any link outside configured allowed domains is ignored during feed scraping."""
    feed_html = """
    <html>
      <body>
        <ul id="news">
          <li class="item">
            <h2 class="title"><a href="https://www.financialexpress.com/market/nifty-record-high/101/">FE Market Story 1</a></h2>
          </li>
          <li class="item">
            <h2 class="title"><a href="https://indianexpress.com/article/entertainment/movie-review/202/">External Group Story</a></h2>
          </li>
          <li class="item">
            <h2 class="title"><a href="https://twitter.com/financialexpress/status/303">Twitter Social Link</a></h2>
          </li>
          <li class="item">
            <h2 class="title"><a href="https://www.financialexpress.com/business/auto-sales-september/102/">FE Auto Story 2</a></h2>
          </li>
          <li class="item">
            <h2 class="title"><a href="https://play.google.com/store/apps/details?id=com.fe">PlayStore App</a></h2>
          </li>
        </ul>
      </body>
    </html>
    """

    config = SiteConfig(
        site_id="financialexpress_test",
        site_name="Financial Express Test",
        base_url="https://www.financialexpress.com",
        domains=["financialexpress.com", "www.financialexpress.com"],
        feed=FeedConfig(
            url="data:text/html;charset=utf-8," + feed_html,
            allowed_domains=["www.financialexpress.com"],
            item_selector="ul#news li.item",
            fields=FeedFieldsConfig(
                title=SelectorConfig(selector="h2.title a", attribute="text"),
                url=SelectorConfig(selector="h2.title a", attribute="href"),
            ),
        ),
    )

    async with PlaywrightNewsScraper(config=config, headless=True) as scraper:
        articles = await scraper.fetch_feed()
        # Only the 2 financialexpress.com links should be extracted, the 3 external ones ignored
        assert len(articles) == 2
        assert articles[0].title == "FE Market Story 1"
        assert articles[0].url == "https://www.financialexpress.com/market/nifty-record-high/101/"
        assert articles[1].title == "FE Auto Story 2"
        assert articles[1].url == "https://www.financialexpress.com/business/auto-sales-september/102/"


@pytest.mark.asyncio
async def test_financialexpress_article_extraction_with_real_config():
    """Verify article parsing against simulated Financial Express DOM structure."""
    article_html = """
    <html>
      <head>
        <meta property="og:image" content="https://images.financialexpressdigital.com/2026/10/fe-story.jpg" />
      </head>
      <body>
        <h1 class="heading-three mb-2">Sebi tightens F&O entry rules for stock derivatives</h1>
        <h2 class="heading-four font-medium mb-2">Capital markets regulator Sebi introduces stricter eligibility criteria for stocks entering the F&O segment.</h2>
        <div class="written_box font-sm font-medium one-line-author-meta">
          <div class="author-link multiple_author_link">
            <a href="https://www.financialexpress.com/author/rohit-sharma/">Rohit Sharma</a>
          </div>
          <div class="updated flex capitalize">
            <time datetime="2026-10-01T11:00:00+05:30">October 1, 2026 11:00 IST</time>
          </div>
        </div>
        <div class="post-content wp-block-post-content mb-4">
          <p>The Securities and Exchange Board of India on Thursday unveiled tighter criteria for stocks in the futures and options segment.</p>
          <div class="adcode300x250">Ad banner to be excluded</div>
          <div class="ie-network-also-read">Also Read: 5 top performing stocks today</div>
          <p>Under the revised guidelines, the median quarter sigma order size has been increased to Rs 75 lakh from the current Rs 25 lakh.</p>
          <div class="stories_fe_widget">Related widget content</div>
          <p>Market analysts believe the new framework will weed out highly volatile and illiquid counters from derivative trading.</p>
        </div>
        <div class="wp-block-post-terms">
          <a href="https://www.financialexpress.com/about/sebi/">SEBI</a>
          <a href="https://www.financialexpress.com/about/derivatives/">Derivatives</a>
        </div>
      </body>
    </html>
    """

    loader = ConfigLoader()
    fe_cfg = loader.get("financialexpress")
    assert fe_cfg is not None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(article_html)

        # Title
        title = await extract_field(page, fe_cfg.article.fields.title)
        assert title == "Sebi tightens F&O entry rules for stock derivatives"

        # Author
        author = await extract_field(page, fe_cfg.article.fields.author)
        assert author == "Rohit Sharma"

        # Published date
        published_at = await extract_field(page, fe_cfg.article.fields.published_at)
        assert published_at == "2026-10-01T11:00:00+05:30"

        # Description
        desc = await extract_field(page, fe_cfg.article.fields.description)
        assert "Capital markets regulator Sebi introduces stricter eligibility criteria" in desc

        # Content extraction & exclusions
        content = await extract_content(page, fe_cfg.article.fields.content)
        assert "The Securities and Exchange Board of India on Thursday unveiled" in content
        assert "Under the revised guidelines, the median quarter sigma order size" in content
        assert "Market analysts believe the new framework will weed out" in content
        assert "Ad banner to be excluded" not in content
        assert "Also Read" not in content
        assert "Related widget content" not in content

        # Tags
        tags = await extract_field(page, fe_cfg.article.fields.tags)
        assert tags == ["SEBI", "Derivatives"]

        await browser.close()



