"""Every text marked with _() (plus the place names/tips and backup reasons) needs an English entry in en.py,
and every {placeholder} must match. Run: python tests/i18n_check.py  (--missing prints the missing ones)
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aplauncher import en, places  # noqa: E402

# Stored in backup manifests in German and translated when shown.
BACKUP_REASONS = ["vor dem Spielstart", "vor dem Fortsetzen", "von Hand", "Stand vor dem Wiederherstellen"]


def marked() -> dict[str, str]:
    """German text -> file it comes from."""
    found = {}
    for f in sorted((ROOT / "aplauncher").rglob("*.py")):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_"
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                found.setdefault(node.args[0].value, f.name)
    for name, _prefixes, tips in places.OOT_DUNGEONS.values():
        for text in [name, *tips]:
            found.setdefault(text, "places.py")
    for name, _prefixes in places.OOT_AREAS.values():
        found.setdefault(name, "places.py")
    for tips in places.SM64_TIPS.values():
        for text in tips:
            found.setdefault(text, "places.py")
    for text in BACKUP_REASONS:
        found.setdefault(text, "backup.py")
    return found


def placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w*)\}", text))


def main():
    texts = marked()
    missing = [t for t in texts if t not in en.TEXT]
    wrong = [t for t in texts if t in en.TEXT and placeholders(t) != placeholders(en.TEXT[t])]
    unused = [t for t in en.TEXT if t not in texts]
    if "--missing" in sys.argv:
        for t in missing:
            print(f"{texts[t]}: {t!r}")
    print(f"{len(texts)} texts, {len(missing)} missing, {len(wrong)} placeholder mismatches, {len(unused)} unused")
    for t in wrong:
        print("  placeholders differ:", repr(t))
    for t in unused:
        print("  unused:", repr(t))
    sys.exit(1 if missing or wrong else 0)


if __name__ == "__main__":
    main()
