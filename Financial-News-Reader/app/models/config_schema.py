from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SelectorConfig(BaseModel):
    """Configuration for extracting a single field using CSS/XPath selectors."""

    selector: str = Field(..., description="Primary CSS or XPath selector.")
    fallbacks: List[str] = Field(
        default_factory=list,
        description="Fallback selectors to try if the primary selector finds nothing.",
    )
    attribute: str = Field(
        default="text",
        description="Attribute to extract: 'text', 'inner_html', or an HTML attribute ('href', 'src', 'datetime', 'content', etc.).",
    )
    fallback_attribute: Optional[str] = Field(
        default=None,
        description="Fallback attribute if the primary attribute is null or empty.",
    )
    clean_regex: Optional[str] = Field(
        default=None,
        description="Optional regex to strip/replace unwanted text patterns.",
    )
    regex_extract: Optional[str] = Field(
        default=None,
        description="Optional regex with capture group to extract a specific substring.",
    )
    default: Optional[str] = Field(
        default=None,
        description="Default value if element is not found.",
    )
    is_list: bool = Field(
        default=False,
        description="If true, collects all matching elements as a list of strings (e.g. tags).",
    )
    strip: bool = Field(
        default=True,
        description="Whether to strip leading/trailing whitespace.",
    )

    @classmethod
    def from_any(cls, value: Union[str, Dict[str, Any], "SelectorConfig"]) -> "SelectorConfig":
        """Allows initializing a SelectorConfig from a plain selector string or dict."""
        if isinstance(value, SelectorConfig):
            return value
        if isinstance(value, str):
            return cls(selector=value)
        if isinstance(value, dict):
            return cls(**value)
        raise ValueError(f"Cannot convert {type(value)} to SelectorConfig")


class ContentExtractorConfig(BaseModel):
    """Configuration for extracting full article body text and paragraphs."""

    container_selector: str = Field(
        default="article",
        description="Container element holding the main article content.",
    )
    fallbacks: List[str] = Field(
        default_factory=list,
        description="Fallback container selectors.",
    )
    paragraph_selector: str = Field(
        default="p",
        description="Selector for paragraph/text elements inside container.",
    )
    exclude_selectors: List[str] = Field(
        default_factory=lambda: [
            ".ad",
            ".advertisement",
            ".social-share",
            ".related-news",
            ".related-stories",
            "script",
            "style",
            "figure",
            "iframe",
        ],
        description="Selectors for unwanted elements (ads, related links, scripts) to exclude.",
    )
    join_delimiter: str = Field(
        default="\n\n",
        description="Delimiter to join paragraphs with.",
    )
    min_paragraph_length: int = Field(
        default=1,
        description="Minimum character length for a paragraph to be retained.",
    )


class FeedPaginationConfig(BaseModel):
    """Configuration for handling listing pagination or infinite scroll."""

    type: Literal["none", "scroll", "click"] = Field(
        default="none",
        description="Pagination strategy: 'none', 'scroll' (infinite scroll), or 'click' (load more button).",
    )
    scroll_count: int = Field(
        default=2,
        description="Number of times to scroll down for infinite scroll.",
    )
    scroll_delay_seconds: float = Field(
        default=1.0,
        description="Delay in seconds between consecutive scrolls.",
    )
    load_more_selector: Optional[str] = Field(
        default=None,
        description="Button selector to click for loading more items.",
    )


class FeedFieldsConfig(BaseModel):
    """Selector mappings for article items on feed/listing pages."""

    title: SelectorConfig = Field(..., description="Selector for article title.")
    url: SelectorConfig = Field(..., description="Selector for article link href.")
    article_id: Optional[SelectorConfig] = Field(
        default=None,
        description="Selector or attribute for article ID (e.g. data-id).",
    )
    published_at: Optional[SelectorConfig] = Field(
        default=None,
        description="Selector for publication timestamp or relative time.",
    )
    source: Optional[SelectorConfig] = Field(
        default=None,
        description="Selector for publication/source name.",
    )
    description: Optional[SelectorConfig] = Field(
        default=None,
        description="Selector for article snippet or description.",
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_selectors(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name in ["title", "url", "article_id", "published_at", "source", "description"]:
                if field_name in data and isinstance(data[field_name], (str, dict)):
                    data[field_name] = SelectorConfig.from_any(data[field_name])
        return data


class FeedConfig(BaseModel):
    """Configuration for scraping article feeds / listing pages."""

    url: str = Field(..., description="URL of the feed or listing page.")
    wait_for_selector: Optional[str] = Field(
        default=None,
        description="Selector to wait for before extracting feed items.",
    )
    item_selector: str = Field(
        ...,
        description="CSS selector identifying each individual article card/item.",
    )
    max_items: Optional[int] = Field(
        default=None,
        description="Maximum number of items to scrape from the feed.",
    )
    allowed_domains: Optional[List[str]] = Field(
        default=None,
        description="Optional list of allowed domains for feed items. If specified, any links outside these domains are ignored. Defaults to site domains.",
    )
    pagination: FeedPaginationConfig = Field(
        default_factory=FeedPaginationConfig,
        description="Pagination configuration.",
    )
    fields: FeedFieldsConfig = Field(
        ...,
        description="Field extraction mappings for each item.",
    )


class ArticleFieldsConfig(BaseModel):
    """Selector mappings for extracting article detail page content."""

    title: SelectorConfig = Field(
        default_factory=lambda: SelectorConfig(
            selector="h1",
            fallbacks=["meta[property='og:title']", "title"],
        ),
        description="Selector for article headline/title.",
    )
    published_at: Optional[SelectorConfig] = Field(
        default_factory=lambda: SelectorConfig(
            selector="time",
            fallbacks=[
                "meta[property='article:published_time']",
                ".published-date",
                ".date",
            ],
            attribute="datetime",
            fallback_attribute="text",
        ),
        description="Selector for publication date/time.",
    )
    author: Optional[SelectorConfig] = Field(
        default=None,
        description="Selector for article author/byline.",
    )
    description: Optional[SelectorConfig] = Field(
        default_factory=lambda: SelectorConfig(
            selector="meta[name='description']",
            fallbacks=["meta[property='og:description']"],
            attribute="content",
        ),
        description="Selector for article summary / lead / meta description.",
    )
    content: Optional[ContentExtractorConfig] = Field(
        default_factory=ContentExtractorConfig,
        description="Configuration for extracting full article body text.",
    )
    tags: Optional[SelectorConfig] = Field(
        default=None,
        description="Selector for tags, keywords, or categories.",
    )
    image_url: Optional[SelectorConfig] = Field(
        default_factory=lambda: SelectorConfig(
            selector="meta[property='og:image']",
            attribute="content",
        ),
        description="Selector for main article image URL.",
    )
    source: Optional[Union[SelectorConfig, str]] = Field(
        default=None,
        description="Static source name or selector to extract source.",
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_selectors(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name in ["title", "published_at", "author", "description", "tags", "image_url"]:
                if field_name in data and isinstance(data[field_name], (str, dict)):
                    data[field_name] = SelectorConfig.from_any(data[field_name])
            if "source" in data and isinstance(data["source"], dict):
                data["source"] = SelectorConfig.from_any(data["source"])
        return data


class ArticleConfig(BaseModel):
    """Configuration for extracting a single news article page."""

    wait_for_selector: Optional[str] = Field(
        default="h1, article",
        description="Selector to wait for to confirm article page is loaded.",
    )
    dismiss_selectors: List[str] = Field(
        default_factory=list,
        description="Selectors of cookie banners, popups, or overlays to dismiss before scraping.",
    )
    click_to_expand_selector: Optional[str] = Field(
        default=None,
        description="Selector of 'Read More' or 'Expand' button to click before extraction.",
    )
    scroll_before_extract: bool = Field(
        default=False,
        description="Whether to perform a brief scroll to trigger lazy loading of article content.",
    )
    fields: ArticleFieldsConfig = Field(
        default_factory=ArticleFieldsConfig,
        description="Article field extraction configuration.",
    )


class BrowserConfig(BaseModel):
    """Browser and network configuration for Playwright."""

    headless: bool = Field(
        default=True,
        description="Run browser in headless mode.",
    )
    timeout_ms: int = Field(
        default=30000,
        description="Navigation and selector timeout in milliseconds.",
    )
    wait_until: Literal["domcontentloaded", "load", "networkidle", "commit"] = Field(
        default="domcontentloaded",
        description="Playwright navigation wait condition.",
    )
    user_agent: Optional[str] = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        description="Custom user agent string.",
    )
    viewport_width: int = Field(default=1280, description="Browser viewport width.")
    viewport_height: int = Field(default=800, description="Browser viewport height.")
    rate_limit_delay_seconds: float = Field(
        default=0.5,
        description="Polite delay between consecutive requests.",
    )
    extra_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers sent with requests.",
    )
    dismiss_selectors: List[str] = Field(
        default_factory=list,
        description="Global selectors for overlays, consent banners to close.",
    )


class SiteConfig(BaseModel):
    """Complete configuration schema for a news site scraper."""

    schema_ref: Optional[str] = Field(
        default=None,
        alias="$schema",
        description="Reference to JSON Schema for IDE validation.",
    )
    site_id: str = Field(
        ...,
        description="Unique identifier for the site (e.g. 'zerodha_pulse', 'economic_times').",
    )
    site_name: str = Field(
        ...,
        description="Display name for the news site (e.g. 'Zerodha Pulse').",
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Domain names associated with this site (e.g. ['pulse.zerodha.com']).",
    )
    base_url: str = Field(
        ...,
        description="Base URL of the news site.",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this site scraper configuration is active.",
    )
    browser: BrowserConfig = Field(
        default_factory=BrowserConfig,
        description="Browser and Playwright execution settings.",
    )
    feed: Optional[FeedConfig] = Field(
        default=None,
        description="Configuration for scraping latest news feed or listing pages.",
    )
    article: ArticleConfig = Field(
        default_factory=ArticleConfig,
        description="Configuration for scraping single article detail pages.",
    )

    model_config = ConfigDict(populate_by_name=True)
