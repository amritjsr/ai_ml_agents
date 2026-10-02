import logging
import re
from typing import Any, List, Optional, Union
from urllib.parse import urljoin

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from app.models.config_schema import ContentExtractorConfig, SelectorConfig

logger = logging.getLogger(__name__)


async def find_element(
    context: Union[Page, Locator],
    primary_selector: str,
    fallbacks: Optional[List[str]] = None,
) -> Optional[Locator]:
    """Finds the first matching locator by checking primary selector then fallbacks."""
    selectors = [primary_selector] + (fallbacks or [])
    for sel in selectors:
        if not sel:
            continue
        try:
            loc = context.locator(sel)
            if await loc.count() > 0:
                return loc
        except Exception as e:
            logger.debug(f"Selector '{sel}' query error: {e}")
            continue
    return None


async def extract_field(
    context: Union[Page, Locator],
    config: Optional[SelectorConfig],
    base_url: str = "",
) -> Any:
    """Extract a field value from a Page or Locator according to SelectorConfig."""
    if not config:
        return None

    locator = await find_element(context, config.selector, config.fallbacks)
    if locator is None:
        return config.default

    if config.is_list:
        items = await locator.all()
        results = []
        for item in items:
            val = await _extract_value_from_single_locator(item, config, base_url)
            if val:
                results.append(val)
        return results if results else (config.default or [])

    val = await _extract_value_from_single_locator(locator.first, config, base_url)
    if val is None or val == "":
        return config.default
    return val


async def _extract_value_from_single_locator(
    loc: Locator,
    config: SelectorConfig,
    base_url: str = "",
) -> Optional[str]:
    """Extracts and cleans value from a single Locator element."""
    attr = config.attribute.lower()
    value: Optional[str] = None

    try:
        # Check if element is a meta tag or if attribute is text
        tag_name = ""
        try:
            tag_name = await loc.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            pass

        if tag_name == "meta" and attr == "text":
            # For meta tags, text content is stored in the 'content' attribute
            value = await loc.get_attribute("content")
        elif attr in ("text", "innertext"):
            # Try inner_text first, fallback to text_content (e.g. for non-visible elements like title)
            value = await loc.inner_text()
            if not value or not value.strip():
                value = await loc.text_content()
                if value and not value.strip():
                    value = None
        elif attr == "inner_html":
            value = await loc.inner_html()
        else:
            value = await loc.get_attribute(config.attribute)

        # Fallback attribute if primary returned empty
        if (not value or (isinstance(value, str) and not value.strip())) and config.fallback_attribute:
            fb_attr = config.fallback_attribute.lower()
            if fb_attr in ("text", "innertext"):
                value = await loc.inner_text() or await loc.text_content()
            else:
                value = await loc.get_attribute(config.fallback_attribute)

    except Exception as e:
        logger.debug(f"Failed extracting attribute '{config.attribute}' from locator: {e}")
        return None

    if value is None:
        return None

    if config.strip:
        value = value.strip()

    # Apply regex cleaning
    if config.clean_regex:
        value = re.sub(config.clean_regex, "", value).strip()

    # Apply regex extraction
    if config.regex_extract:
        match = re.search(config.regex_extract, value)
        if match:
            value = match.group(1).strip()

    # Resolve relative URLs
    if config.attribute.lower() in ("href", "src") and base_url and value:
        value = urljoin(base_url, value)

    return value


async def extract_content(
    context: Union[Page, Locator],
    config: Optional[ContentExtractorConfig],
) -> Optional[str]:
    """Extracts article body content and paragraphs while stripping ads, scripts, and clutter."""
    if not config:
        return None

    container = await find_element(context, config.container_selector, config.fallbacks)
    if container is None:
        return None

    try:
        # Fast, clean in-browser DOM extraction and sanitization
        text = await container.first.evaluate(
            """(container, opts) => {
                const clone = container.cloneNode(true);
                // Strip unwanted elements
                (opts.excludeSelectors || []).forEach(sel => {
                    try {
                        clone.querySelectorAll(sel).forEach(el => el.remove());
                    } catch (e) {}
                });

                // Find paragraph elements
                const paras = Array.from(clone.querySelectorAll(opts.paragraphSelector || 'p'))
                    .map(p => (p.innerText || '').trim())
                    .filter(t => t.length >= (opts.minParagraphLength || 1));

                if (paras.length > 0) {
                    return paras.join(opts.joinDelimiter || '\\n\\n');
                }

                // If no paragraphs matched, fallback to clone innerText
                return (clone.innerText || '').trim();
            }""",
            {
                "excludeSelectors": config.exclude_selectors,
                "paragraphSelector": config.paragraph_selector,
                "joinDelimiter": config.join_delimiter,
                "minParagraphLength": config.min_paragraph_length,
            },
        )
        return text if text else None
    except Exception as e:
        logger.warning(f"Error extracting content via container evaluate: {e}")
        try:
            return await container.first.inner_text()
        except Exception:
            return None


async def dismiss_overlays(
    page: Page,
    selectors: List[str],
    timeout_ms: int = 1500,
) -> None:
    """Attempts to dismiss cookie banners, newsletters, or paywall popups."""
    for sel in selectors:
        if not sel:
            continue
        try:
            loc = page.locator(sel)
            if await loc.count() > 0 and await loc.first.is_visible():
                await loc.first.click(timeout=timeout_ms)
                logger.debug(f"Dismissed overlay using selector: {sel}")
        except PlaywrightTimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Could not dismiss overlay '{sel}': {e}")
