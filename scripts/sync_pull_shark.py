from __future__ import annotations

import argparse
import copy
import json
import os
import re
import urllib.parse
import urllib.request
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACHIEVEMENTS_PATH = ROOT / "profile" / "achievements.json"
DARK_SVG_PATH = ROOT / "assets" / "github-achievements-motion.svg"
LIGHT_SVG_PATH = ROOT / "assets" / "github-achievements-motion-light.svg"
API_VERSION = "2026-03-10"
TIER_THRESHOLDS = ((1024, 4), (128, 3), (16, 2), (2, 1))


def pull_shark_level(merged_prs: int) -> int:
    if not isinstance(merged_prs, int) or isinstance(merged_prs, bool) or merged_prs < 0:
        raise RuntimeError("MERGED_PR_COUNT_INVALID")
    for threshold, level in TIER_THRESHOLDS:
        if merged_prs >= threshold:
            return level
    return 0


def _pull_shark_item(data: dict) -> dict:
    items = [item for item in data.get("achievements", []) if item.get("id") == "pull-shark"]
    if len(items) != 1:
        raise RuntimeError("PULL_SHARK_SOURCE_INVALID")
    item = items[0]
    if item.get("name") != "Pull Shark" or item.get("verified") is not True:
        raise RuntimeError("PULL_SHARK_SOURCE_INVALID")
    return item


def apply_pull_shark_level(data: dict, new_level: int) -> bool:
    if new_level < 1 or new_level > 4:
        raise RuntimeError(f"PULL_SHARK_LEVEL_INVALID:{new_level}")
    item = _pull_shark_item(data)
    current = item.get("count")
    if not isinstance(current, int) or current < 1 or current > 4:
        raise RuntimeError("PULL_SHARK_CURRENT_LEVEL_INVALID")
    if new_level < current:
        raise RuntimeError(f"PULL_SHARK_DOWNGRADE_BLOCKED:{current}->{new_level}")
    if new_level == current:
        return False
    item["count"] = new_level
    item["verified"] = True
    return True


def render_pull_shark_svg(source: str, old_level: int, new_level: int) -> str:
    old_label = f"Pull Shark x{old_level}"
    new_label = f"Pull Shark x{new_level}"
    if source.count(old_label) != 1:
        raise RuntimeError("PULL_SHARK_SVG_LABEL_INVALID")
    updated = source.replace(old_label, new_label, 1)
    marker = re.compile(r'(<text x="151" y="35"[^>]*>)x' + re.escape(str(old_level)) + r'(</text>)')
    updated, replacements = marker.subn(rf"\1x{new_level}\2", updated, count=1)
    if replacements != 1:
        raise RuntimeError("PULL_SHARK_SVG_MARKER_INVALID")
    return updated


def parse_search_response(payload: bytes) -> int:
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("GITHUB_SEARCH_JSON_INVALID") from exc
    if not isinstance(data, dict) or data.get("incomplete_results") is not False:
        raise RuntimeError("GITHUB_SEARCH_INCOMPLETE")
    count = data.get("total_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise RuntimeError("GITHUB_SEARCH_COUNT_INVALID")
    return count


def build_search_url(username: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        raise RuntimeError("GITHUB_USERNAME_INVALID")
    query = urllib.parse.urlencode({"q": f"author:{username} is:pr is:merged", "per_page": "1"})
    return f"https://api.github.com/search/issues?{query}"


def resolve_search_token(environment: Mapping[str, str]) -> str:
    token = str(environment.get("ACHIEVEMENT_GITHUB_TOKEN", "")).strip()
    if not token:
        raise RuntimeError("ACHIEVEMENT_GITHUB_TOKEN_MISSING")
    return token

def fetch_merged_pr_count(username: str, token: str | None = None) -> int:
    request = urllib.request.Request(
        build_search_url(username),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "rockin-profile-achievement-sync/1",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"GITHUB_SEARCH_HTTP:{response.status}")
            return parse_search_response(response.read())
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"GITHUB_SEARCH_REQUEST_FAILED:{type(exc).__name__}") from exc


def _json_text(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def sync_repository(merged_prs: int, write: bool) -> tuple[int, bool]:
    level = pull_shark_level(merged_prs)
    current_data = json.loads(ACHIEVEMENTS_PATH.read_text(encoding="utf-8"))
    current_level = int(_pull_shark_item(current_data)["count"])
    if level < 1:
        raise RuntimeError(f"PULL_SHARK_EVIDENCE_BELOW_BASE:{merged_prs}")

    new_data = copy.deepcopy(current_data)
    changed = apply_pull_shark_level(new_data, level)
    if not changed:
        return level, False

    dark = render_pull_shark_svg(DARK_SVG_PATH.read_text(encoding="utf-8"), current_level, level)
    light = render_pull_shark_svg(LIGHT_SVG_PATH.read_text(encoding="utf-8"), current_level, level)
    if write:
        ACHIEVEMENTS_PATH.write_text(_json_text(new_data), encoding="utf-8", newline="\n")
        DARK_SVG_PATH.write_text(dark, encoding="utf-8", newline="\n")
        LIGHT_SVG_PATH.write_text(light, encoding="utf-8", newline="\n")
    return level, True


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize the verified Pull Shark level from GitHub merged PR evidence.")
    parser.add_argument("--merged-prs", type=int, help="Use an explicit merged-PR count instead of calling GitHub.")
    parser.add_argument("--username", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "rockinai88"))
    parser.add_argument("--write", action="store_true", help="Write verified level changes to repository sources.")
    args = parser.parse_args()

    try:
        merged_prs = args.merged_prs
        if merged_prs is None:
            merged_prs = fetch_merged_pr_count(args.username, resolve_search_token(os.environ))
        level, changed = sync_repository(merged_prs, args.write)
    except Exception as exc:
        print(f"PULL_SHARK_SYNC_FAIL:{exc}")
        return 1

    state = "CHANGED" if changed else "NO_CHANGE"
    mode = "WRITE" if args.write else "DRY_RUN"
    print(f"PULL_SHARK_SYNC_{state} merged_prs={merged_prs} level={level} mode={mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
