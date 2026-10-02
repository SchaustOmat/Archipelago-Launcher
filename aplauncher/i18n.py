"""Interface language. The German text is the source; _() looks up the English version in en.py.

The language is fixed at start (settings "lang", or the Windows display language when unset), so a
change takes effect after a restart.
"""
import ctypes

from . import en

LANGS = {"de": "Deutsch", "en": "English"}
_lang = "de"


def system_lang() -> str:
    try:
        primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
    except (AttributeError, OSError):
        return "en"
    return "de" if primary == 0x07 else "en"  # LANG_GERMAN


def set_lang(lang: str | None):
    global _lang
    _lang = lang if lang in LANGS else system_lang()


def lang() -> str:
    return _lang


def date(dt, with_time=True) -> str:
    fmt = "%d.%m.%Y" if _lang == "de" else "%Y-%m-%d"
    return dt.strftime(fmt + ("  %H:%M" if with_time else ""))


def exact(dt) -> str:
    """Date with the time to the second, e.g. '02.10.2026, 14:32:05 Uhr'."""
    if _lang == "de":
        return dt.strftime("%d.%m.%Y, %H:%M:%S Uhr")
    return dt.strftime("%Y-%m-%d, %H:%M:%S")


def _(text: str) -> str:
    if _lang == "de":
        return text
    return en.TEXT.get(text, text)
