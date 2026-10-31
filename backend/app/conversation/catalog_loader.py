"""Multilingual Catalog Loader for SurakshaVani."""

import json
from pathlib import Path
from typing import Any, Dict

CATALOG_DIR = Path(__file__).parent / "catalog"

_CATALOGS: Dict[str, Dict[str, str]] = {}


def load_catalogs() -> None:
    global _CATALOGS
    for lang in ["en", "hi", "mr"]:
        cat_file = CATALOG_DIR / f"{lang}.json"
        if cat_file.exists():
            with open(cat_file, "r", encoding="utf-8") as f:
                _CATALOGS[lang] = json.load(f)


def get_text(key: str, lang: str = "mr", **kwargs: Any) -> str:
    """Retrieves localized text with interpolated format arguments."""
    if not _CATALOGS:
        load_catalogs()

    catalog = _CATALOGS.get(lang, _CATALOGS.get("en", {}))
    template = catalog.get(key, _CATALOGS.get("en", {}).get(key, f"[{key}]"))
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


# Initial load
load_catalogs()

