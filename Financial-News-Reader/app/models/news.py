from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class NewsArticle:
    """Represents a normalized news item extracted from any news source."""

    title: str
    url: str
    source: str
    published_at: str = ""
    description: Optional[str] = None
    article_text: Optional[str] = None
    author: Optional[str] = None
    article_id: Optional[str] = None
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tags: List[str] = field(default_factory=list)
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary representation."""
        return {
            "article_id": self.article_id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
            "description": self.description,
            "article_text": self.article_text,
            "author": self.author,
            "scraped_at": self.scraped_at,
            "tags": self.tags,
            "image_url": self.image_url,
            "metadata": self.metadata,
        }
