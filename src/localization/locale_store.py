from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True, init=False)
class LocalizedText(str):
    """Localized string value with metadata about formatting.

    The string behaves like a regular ``str`` but carries flags that tell
    consumers whether it originated from a multi-line array in the locale file.
    """

    is_multiline: bool = False
    key: Optional[str] = None
    locale: Optional[str] = None

    def __new__(cls, value: str, *, is_multiline: bool = False, key: Optional[str] = None,
                locale: Optional[str] = None):  # type: ignore[override]
        obj = super().__new__(cls, value)
        object.__setattr__(obj, "is_multiline", is_multiline)
        object.__setattr__(obj, "key", key)
        object.__setattr__(obj, "locale", locale)
        return obj

    def format(self, *args: Any, **kwargs: Any) -> "LocalizedText":  # type: ignore[override]
        formatted_value = super().format(*args, **kwargs)
        return LocalizedText(
            formatted_value,
            is_multiline=self.is_multiline,
            key=self.key,
            locale=self.locale,
        )


class LocaleStore:
    """Loads and serves localized strings from JSON files."""

    def __init__(self, locale_directory: Path, default_locale: str = "en"):
        self.locale_directory = locale_directory
        self.default_locale = default_locale
        self._translations: Dict[str, Dict[str, LocalizedText]] = {}
        self._load_locale(default_locale)

    def has_key(self, key: str) -> bool:
        default_catalog = self._translations.get(self.default_locale, {})
        return key in default_catalog

    def translate(self, key: str, *, locale: Optional[str] = None, **kwargs: Any) -> LocalizedText:
        """Return a translated string, falling back to the default locale."""

        target_locale = locale or self.default_locale
        catalog = self._get_catalog(target_locale)
        entry = catalog.get(key)

        if entry is None and target_locale != self.default_locale:
            entry = self._translations[self.default_locale].get(key)

        if entry is None:
            raise KeyError(f"Translation key '{key}' not found for locale '{target_locale}'")

        if kwargs:
            return entry.format(**kwargs)

        return entry

    def is_multiline(self, key: str, *, locale: Optional[str] = None) -> bool:
        target_locale = locale or self.default_locale
        catalog = self._get_catalog(target_locale)
        entry = catalog.get(key)
        if entry:
            return entry.is_multiline
        return False

    def _get_catalog(self, locale: str) -> Dict[str, LocalizedText]:
        if locale not in self._translations:
            self._load_locale(locale)
        return self._translations.get(locale, self._translations[self.default_locale])

    def _load_locale(self, locale: str) -> None:
        locale_file = self.locale_directory / f"{locale}.json"
        if not locale_file.exists():
            logger.warning("Locale file for '%s' not found at %s", locale, locale_file)
            return

        with locale_file.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

        flattened = self._flatten_keys(raw_data)
        catalog: Dict[str, LocalizedText] = {}

        for key, raw_value in flattened.items():
            localized_text = self._normalize_value(raw_value, key=key, locale=locale)
            catalog[key] = localized_text

        self._translations[locale] = catalog

    def _normalize_value(self, value: Any, *, key: Optional[str], locale: str) -> LocalizedText:
        if isinstance(value, list):
            joined_value = "\n".join(str(line) for line in value)
            return LocalizedText(joined_value, is_multiline=True, key=key, locale=locale)
        return LocalizedText(str(value), is_multiline=False, key=key, locale=locale)

    def _flatten_keys(self, data: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        items: Dict[str, Any] = {}
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                items.update(self._flatten_keys(value, new_key))
            else:
                items[new_key] = value
        return items


class LocaleKeyAccessor:
    """Provides attribute access to translation keys."""

    def __init__(self, store: LocaleStore, locale: Optional[str] = None, prefix: str = ""):
        self._store = store
        self._locale = locale
        self._prefix = prefix

    def for_locale(self, locale: str) -> "LocaleKeyAccessor":
        return LocaleKeyAccessor(self._store, locale=locale, prefix=self._prefix)

    def __getattr__(self, item: str) -> LocalizedText:
        candidate_key = f"{self._prefix}.{item}" if self._prefix else item

        if self._store.has_key(candidate_key):
            return self._store.translate(candidate_key, locale=self._locale)

        return LocaleKeyAccessor(self._store, locale=self._locale, prefix=candidate_key)

    def __call__(self, **kwargs: Any) -> LocalizedText:
        if not self._prefix:
            raise ValueError("Cannot format a key without a prefix; select a key first.")
        return self._store.translate(self._prefix, locale=self._locale, **kwargs)
