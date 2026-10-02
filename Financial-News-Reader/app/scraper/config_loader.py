import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.models.config_schema import SiteConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Manages loading, registry, and lookup of news site JSON scraper configurations."""

    def __init__(self, config_dir: Optional[Path | str] = None):
        if config_dir is None:
            # Default to 'configs' directory in project root
            self.config_dir = Path(__file__).resolve().parent.parent.parent / "configs"
        else:
            self.config_dir = Path(config_dir)

        self._configs: Dict[str, SiteConfig] = {}
        self._domain_map: Dict[str, str] = {}
        self._generic_fallback_id: Optional[str] = "generic_article"

        self.load_all()

    def load_file(self, file_path: Path | str) -> SiteConfig:
        """Load and validate a single JSON configuration file."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = SiteConfig.model_validate(data)
        self.register(config)
        return config

    def register(self, config: SiteConfig) -> None:
        """Register a SiteConfig instance in the memory registry."""
        self._configs[config.site_id] = config
        for domain in config.domains:
            self._domain_map[domain.lower()] = config.site_id
            if domain.startswith("www."):
                self._domain_map[domain[4:].lower()] = config.site_id
            else:
                self._domain_map[f"www.{domain}".lower()] = config.site_id

        if config.site_id == "generic_article" or "*" in config.domains:
            self._generic_fallback_id = config.site_id

        logger.debug(f"Registered config '{config.site_id}' ({config.site_name})")

    def load_all(self) -> Dict[str, SiteConfig]:
        """Scan config directory and load all .json config files (skipping schema.json)."""
        if not self.config_dir.exists():
            logger.warning(f"Config directory does not exist: {self.config_dir}")
            return self._configs

        for json_file in sorted(self.config_dir.glob("*.json")):
            if json_file.name == "schema.json":
                continue
            try:
                self.load_file(json_file)
            except Exception as e:
                logger.error(f"Failed to load config {json_file}: {e}")

        logger.info(f"Loaded {len(self._configs)} scraper configs from {self.config_dir}")
        return self._configs

    def get(self, site_id: str) -> Optional[SiteConfig]:
        """Retrieve config by site_id."""
        return self._configs.get(site_id)

    def get_for_url(self, url: str) -> SiteConfig:
        """Automatically find the matching SiteConfig for a given URL by domain.

        Falls back to generic_article if no domain-specific config is found.
        """
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()

        # Check exact host match
        if netloc in self._domain_map:
            site_id = self._domain_map[netloc]
            return self._configs[site_id]

        # Check host with/without www
        if netloc.startswith("www.") and netloc[4:] in self._domain_map:
            return self._configs[self._domain_map[netloc[4:]]]

        # Subdomain match (e.g. news.economictimes.indiatimes.com -> economictimes.indiatimes.com)
        for domain, site_id in self._domain_map.items():
            if domain != "*" and (netloc == domain or netloc.endswith(f".{domain}")):
                return self._configs[site_id]

        # Fallback to generic parser
        if self._generic_fallback_id and self._generic_fallback_id in self._configs:
            return self._configs[self._generic_fallback_id]

        raise KeyError(f"No configuration found for URL '{url}' and no generic fallback available.")

    def list_sites(self) -> List[str]:
        """Return list of all registered site IDs."""
        return list(self._configs.keys())
