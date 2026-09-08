from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_profile import render_readme

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profile" / "profile.json"
ACHIEVEMENTS_PATH = ROOT / "profile" / "achievements.json"
README_PATH = ROOT / "README.md"

SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
]
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
NETWORK_REF_RE = re.compile(r"(?:src|href|xlink:href)\s*=\s*['\"]https?://|url\(\s*https?://", re.I)
LOCAL_PATH_RE = re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\|/home/[A-Za-z0-9._-]+/|/Users/[A-Za-z0-9._-]+/")


def fail(message: str) -> None:
    raise RuntimeError(message)

def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        fail(f"UNSUPPORTED_VERSION:{path.name}")
    return data


def public_files(profile: dict) -> list[Path]:
    for relative in profile["assets"].values():
        path = (ROOT / relative).resolve()
        if ROOT not in path.parents:
            fail(f"ASSET_OUTSIDE_REPO:{relative}")
    suffixes = {".md", ".json", ".py", ".ps1", ".svg", ".yml", ".yaml", ".toml", ".txt"}
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name == ".gitignore" or path.suffix.lower() in suffixes:
            files.append(path)
    return sorted(files)


def validate_profile_shape(profile: dict) -> None:
    required = {"brand", "tagline", "focus", "stack", "assets", "rights"}
    missing = sorted(required - profile.keys())
    if missing:
        fail(f"PROFILE_KEYS_MISSING:{','.join(missing)}")
    if not profile["brand"].strip() or not profile["tagline"].strip():
        fail("PROFILE_TEXT_EMPTY")
    if not profile["focus"] or not profile["stack"]:
        fail("PROFILE_LIST_EMPTY")
    expected_assets = {"hero_dark", "hero_light", "achievements_dark", "achievements_light"}
    if set(profile["assets"]) != expected_assets:
        fail("PROFILE_ASSET_KEYS_INVALID")

def validate_achievements(data: dict) -> None:
    items = data.get("achievements")
    if not isinstance(items, list) or not items:
        fail("ACHIEVEMENTS_EMPTY")
    ids: set[str] = set()
    names: set[str] = set()
    for item in items:
        achievement_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        count = item.get("count")
        if not achievement_id or not name:
            fail("ACHIEVEMENT_ID_OR_NAME_EMPTY")
        if achievement_id in ids or name in names:
            fail(f"ACHIEVEMENT_DUPLICATE:{achievement_id}")
        if not isinstance(count, int) or count < 1:
            fail(f"ACHIEVEMENT_COUNT_INVALID:{achievement_id}")
        if item.get("verified") is not True:
            fail(f"ACHIEVEMENT_NOT_VERIFIED:{achievement_id}")
        ids.add(achievement_id)
        names.add(name)


def validate_svg(path: Path) -> str:
    if not path.is_file():
        fail(f"ASSET_MISSING:{path.name}")
    text = path.read_text(encoding="utf-8")
    ET.fromstring(text)
    if NETWORK_REF_RE.search(text):
        fail(f"EXTERNAL_RESOURCE:{path.name}")
    if "@keyframes" in text and "prefers-reduced-motion" not in text:
        fail(f"REDUCED_MOTION_MISSING:{path.name}")
    return text

def validate_public_content(paths: list[Path]) -> None:
    for path in paths:
        if not path.is_file():
            fail(f"PUBLIC_FILE_MISSING:{path}")
        text = path.read_text(encoding="utf-8")
        if EMAIL_RE.search(text):
            fail(f"EMAIL_FOUND:{path.name}")
        if LOCAL_PATH_RE.search(text):
            fail(f"LOCAL_PATH_FOUND:{path.name}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                fail(f"SECRET_PATTERN_FOUND:{path.name}")


def validate_readme(profile: dict) -> None:
    current = README_PATH.read_text(encoding="utf-8")
    expected = render_readme()
    if current != expected:
        fail("README_NOT_GENERATED")
    if NETWORK_REF_RE.search(current):
        fail("README_EXTERNAL_RESOURCE")
    for relative in profile["assets"].values():
        if relative not in current:
            fail(f"README_ASSET_REFERENCE_MISSING:{relative}")
    if profile["rights"] not in current:
        fail("README_RIGHTS_REFERENCE_MISSING")


def validate_visual_coverage(profile: dict, achievements: dict) -> None:
    dark_path = (ROOT / profile["assets"]["achievements_dark"]).resolve()
    light_path = (ROOT / profile["assets"]["achievements_light"]).resolve()
    dark = dark_path.read_text(encoding="utf-8")
    light = light_path.read_text(encoding="utf-8")
    for item in achievements["achievements"]:
        name = str(item["name"])
        if name not in dark or name not in light:
            fail(f"ACHIEVEMENT_VISUAL_MISSING:{name}")
        if int(item["count"]) > 1:
            marker = f"x{int(item['count'])}"
            if marker not in dark or marker not in light:
                fail(f"ACHIEVEMENT_COUNT_VISUAL_MISSING:{name}")

def main() -> int:
    try:
        profile = load_json(PROFILE_PATH)
        achievements = load_json(ACHIEVEMENTS_PATH)
        validate_profile_shape(profile)
        validate_achievements(achievements)
        files = public_files(profile)
        validate_public_content(files)
        svg_files = [path for path in ROOT.rglob("*.svg") if ".git" not in path.parts]
        for svg in sorted(svg_files):
            validate_svg(svg)
        validate_readme(profile)
        validate_visual_coverage(profile, achievements)
    except Exception as exc:
        print(f"PROFILE_VALIDATE_FAIL:{exc}")
        return 1

    print("PROFILE_VALIDATE_PASS")
    print(f"ACHIEVEMENTS={len(achievements['achievements'])}")
    print(f"PUBLIC_FILES={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
