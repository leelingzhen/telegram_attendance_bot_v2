from pathlib import Path

from .locale_store import LocaleStore, LocaleKeyAccessor

_locale_directory = Path(__file__).parent / "locales"
_default_locale = "en"

store = LocaleStore(locale_directory=_locale_directory, default_locale=_default_locale)

# Default accessor for convenience
Key = LocaleKeyAccessor(store)

__all__ = [
    "Key",
    "store",
    "LocaleStore",
    "LocaleKeyAccessor",
]
