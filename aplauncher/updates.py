"""Update check against the GitHub releases of the launcher (config.UPDATE_REPO)."""
import json
import re
import urllib.request
from pathlib import Path

from . import config

API = "https://api.github.com/repos/{repo}/releases/latest"
UA = {"User-Agent": "APLauncher-update-check", "Accept": "application/vnd.github+json"}


def _version(text: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


def notes_for(body: str, lang: str) -> str:
    """Release notes are written as "## English" and "## Deutsch" sections; pick the one for the UI language."""
    sections = re.split(r"^##\s+(English|Deutsch)\s*$", body, flags=re.M)
    by_lang = {sections[i].lower()[:2]: sections[i + 1].strip() for i in range(1, len(sections) - 1, 2)}
    want = "de" if lang == "de" else "en"
    text = by_lang.get(want) or by_lang.get("en") or body.strip()
    return text.replace("**", "").replace("`", "")  # shown in a plain message box


def latest() -> dict | None:
    """{"version", "url", "notes", "setup_url", "setup_name"} if a newer release exists, else None."""
    if not config.UPDATE_REPO:
        return None
    try:
        req = urllib.request.Request(API.format(repo=config.UPDATE_REPO), headers=UA)
        rel = json.loads(urllib.request.urlopen(req, timeout=10).read())
    except (OSError, ValueError):
        return None
    tag = rel.get("tag_name", "")
    if rel.get("draft") or rel.get("prerelease") or _version(tag) <= _version(config.APP_VERSION):
        return None
    # The small setup (downloads the games itself), not the Full one.
    setup = next((a for a in rel.get("assets", [])
                  if re.fullmatch(r"ArchipelagoLauncher-Setup_[\d.]+\.exe", a.get("name", ""))), None)
    return {"version": tag.lstrip("v"), "url": rel.get("html_url", ""), "notes": (rel.get("body") or "").strip(),
            "setup_url": setup["browser_download_url"] if setup else None,
            "setup_name": setup["name"] if setup else None}


def download(url: str, dest: Path, progress=None) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        total = int(r.headers.get("Content-Length") or 0)
        tmp = dest.with_suffix(".part")
        done = 0
        with open(tmp, "wb") as f:
            while chunk := r.read(1 << 16):
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total)
    tmp.replace(dest)
    return dest
