# JSON-Configured Playwright News Scraping Framework

A production-grade, declarative web scraping framework for the Autonomous Financial News Agent.

Instead of writing custom Python code for every news site, **each news source is defined purely as a JSON configuration file**. The generic Playwright engine parses the JSON rules to extract article listings and full article text with robust anti-bot handling, DOM sanitization, and fallback strategies.

---

## 📑 Architecture Overview

```text
               +----------------------------------------+
               | News Article URL or Target Source Name |
               +-------------------+--------------------+
                                   |
                                   v
                      +--------------------------+
                      |      ConfigLoader        |
                      |   (Domain / ID Routing)  |
                      +------------+-------------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
      zerodha_pulse.json   economic_times.json   generic_article.json
              |                    |                    |
              +--------------------+--------------------+
                                   |
                                   v
                     +----------------------------+
                     |    PlaywrightNewsScraper   |
                     |  • Anti-bot / Stealth      |
                     |  • Banner / Overlay Close  |
                     |  • Fallback Selectors      |
                     |  • DOM Sanitization (Ads)  |
                     +-------------+--------------+
                                   |
                                   v
                            NewsArticle Object
                      (Normalized Data Structure)
```

---

## 📁 Project Structure

```text
Financial-News-Reader/
│
├── configs/                          # JSON Scraper Configurations
│   ├── schema.json                   # Auto-generated JSON Schema for IDE validation
│   ├── zerodha_pulse.json            # Zerodha Pulse feed & article config
│   ├── economic_times.json           # Economic Times markets & article config
│   ├── moneycontrol.json             # Moneycontrol news & article config
│   ├── financialexpress.json         # Financial Express homepage feed & article config
│   └── generic_article.json          # Universal fallback using HTML5 & OpenGraph tags
│
├── app/
│   ├── models/
│   │   ├── news.py                   # Normalized NewsArticle dataclass
│   │   └── config_schema.py          # Pydantic v2 validation schema & model
│   │
│   ├── scraper/
│   │   ├── config_loader.py          # Config registry, loader, and URL domain matcher
│   │   ├── extractor.py              # In-browser DOM extraction, regex clean, ad stripping
│   │   └── playwright_engine.py      # Async Playwright scraping engine
│   │
│   └── main.py                       # CLI interface for testing and scraping
│
├── tests/
│   ├── conftest.py
│   └── test_config_driven_scraper.py # Pytest test suite
│
├── requirements.txt
└── README.md
```

---

## ⚙️ JSON Configuration Schema

Every news site configuration adheres to the Pydantic schema defined in [`app/models/config_schema.py`](file:///home/amrit/ai_ml_agents/Financial-News-Reader/app/models/config_schema.py).

### Complete Configuration Reference

```json
{
  "$schema": "./schema.json",
  "site_id": "example_news",
  "site_name": "Example Financial News",
  "domains": [
    "example.com",
    "news.example.com"
  ],
  "base_url": "https://example.com",
  "enabled": true,

  "browser": {
    "headless": true,
    "timeout_ms": 30000,
    "wait_until": "domcontentloaded",
    "rate_limit_delay_seconds": 1.0,
    "dismiss_selectors": [
      "#onetrust-accept-btn-handler",
      ".cookie-consent-close",
      ".btn-close"
    ],
    "extra_headers": {}
  },

  "feed": {
    "url": "https://example.com/markets/news",
    "wait_for_selector": "ul.news-list",
    "item_selector": "ul.news-list > li.article-card",
    "max_items": 50,
    "pagination": {
      "type": "none",
      "scroll_count": 2,
      "scroll_delay_seconds": 1.0,
      "load_more_selector": null
    },
    "fields": {
      "title": {
        "selector": "h2.headline a",
        "fallbacks": ["h2 a", "h3 a"],
        "attribute": "text"
      },
      "url": {
        "selector": "h2.headline a",
        "attribute": "href"
      },
      "article_id": {
        "selector": "h2.headline a",
        "attribute": "data-id"
      },
      "description": {
        "selector": "p.snippet",
        "attribute": "text"
      },
      "published_at": {
        "selector": "time.post-date",
        "attribute": "datetime",
        "fallback_attribute": "text"
      },
      "source": {
        "selector": "span.publisher",
        "attribute": "text",
        "clean_regex": "^[—\\-\\s]+"
      }
    }
  },

  "article": {
    "wait_for_selector": "h1, article",
    "dismiss_selectors": [
      ".subscribe-modal-close"
    ],
    "click_to_expand_selector": "button.read-more",
    "scroll_before_extract": false,
    "fields": {
      "title": {
        "selector": "h1.article-title",
        "fallbacks": ["h1", "meta[property='og:title']"],
        "attribute": "text"
      },
      "published_at": {
        "selector": "time",
        "fallbacks": ["meta[property='article:published_time']", ".date"],
        "attribute": "datetime",
        "fallback_attribute": "text"
      },
      "author": {
        "selector": ".byline-author, .author-name",
        "fallbacks": ["meta[name='author']"],
        "attribute": "text"
      },
      "description": {
        "selector": "h2.summary",
        "fallbacks": ["meta[name='description']", "meta[property='og:description']"],
        "attribute": "text",
        "fallback_attribute": "content"
      },
      "content": {
        "container_selector": "div.article-body, article",
        "fallbacks": [".story-content", "main"],
        "paragraph_selector": "p",
        "exclude_selectors": [
          ".ad",
          ".advertisement",
          ".related-stories",
          ".social-share",
          "script",
          "style"
        ],
        "join_delimiter": "\n\n",
        "min_paragraph_length": 10
      },
      "tags": {
        "selector": ".article-tags a",
        "attribute": "text",
        "is_list": true
      },
      "image_url": {
        "selector": "meta[property='og:image']",
        "attribute": "content"
      },
      "source": "Example Financial News"
    }
  }
}
```

---

## 🚀 How to Add a New News Site

To support a new financial website (e.g. Business Standard, Financial Times, Livemint):

1. **Create a new JSON file** inside [`configs/`](file:///home/amrit/ai_ml_agents/Financial-News-Reader/configs/):
   ```bash
   cp configs/generic_article.json configs/livemint.json
   ```
2. **Fill in the site details**:
   - `site_id`: `"livemint"`
   - `site_name`: `"Livemint"`
   - `domains`: `["livemint.com", "www.livemint.com"]`
   - `base_url`: `"https://www.livemint.com"`
   - `feed` (optional): feed URL and card selectors
   - `article`: CSS selectors for title, published date, author, and article body container.
3. **No Python code changes needed!** The framework automatically discovers all JSON files in [`configs/`](file:///home/amrit/ai_ml_agents/Financial-News-Reader/configs/) and routes requests by domain.

---

## 🛠️ CLI Usage Examples

### 1. List All Registered Configurations
```bash
python3 app/main.py list
```

### 2. Scrape News Feed
Scrape the latest headlines from Zerodha Pulse in headless mode (default: true):
```bash
python3 app/main.py feed --site zerodha_pulse --limit 5
# Or explicitly:
python3 app/main.py feed --site zerodha_pulse --limit 5 --headless true
```

Run visibly (non-headless):
```bash
python3 app/main.py feed --site zerodha_pulse --limit 5 --headless false
```

Scrape feed and automatically visit each article to retrieve full text:
```bash
python3 app/main.py feed --site zerodha_pulse --limit 3 --full
# Or Financial Express:
python3 app/main.py feed --site financialexpress --limit 5 --full
```

### 3. Scrape Any News Article URL
Provide any article link; the scraper matches the domain against registered JSON configs or falls back to [`generic_article.json`](file:///home/amrit/ai_ml_agents/Financial-News-Reader/configs/generic_article.json):
```bash
python3 app/main.py article "https://pulse.zerodha.com/news/12345" --headless true
```

Run visibly:
```bash
python3 app/main.py article "https://pulse.zerodha.com/news/12345" --headless false
```

---

## 🐍 Python API Usage

### Scrape Feed in Async Python (One-Shot Helper with Headless Option)
```python
import asyncio
from app.scraper.playwright_engine import PlaywrightNewsScraper

async def main():
    # Scrape feed headlines using site_id and specified headless mode
    articles = await PlaywrightNewsScraper.scrape_feed_site("zerodha_pulse", max_items=10, headless=True)
    for article in articles:
        print(f"[{article.source}] {article.title}")
        print(f"  URL: {article.url}")

asyncio.run(main())
```

### Scrape a Single Article by URL (Automatic Config Detection)
```python
import asyncio
from app.scraper.playwright_engine import PlaywrightNewsScraper

async def main():
    url = "https://economictimes.indiatimes.com/markets/stocks/news/sample-story/articleshow/123.cms"
    
    # Automatically resolves matching JSON config by domain (headless=True by default)
    article = await PlaywrightNewsScraper.scrape_article_url(url, headless=True)
    
    print("Headline:", article.title)
    print("Source:  ", article.source)
    print("Body:    ", article.article_text[:300])

asyncio.run(main())
```

---

## 🧪 Running Tests

Run the test suite using `pytest`:
```bash
pytest tests/test_config_driven_scraper.py -v
```
