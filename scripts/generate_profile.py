from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profile" / "profile.json"
ACHIEVEMENTS_PATH = ROOT / "profile" / "achievements.json"
README_PATH = ROOT / "README.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def achievement_label(item: dict, ascii_count: bool = False) -> str:
    count = int(item["count"])
    if count <= 1:
        return str(item["name"])
    marker = "x" if ascii_count else "×"
    return f"{item['name']} {marker}{count}"


def natural_join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]

def render_readme() -> str:
    profile = load_json(PROFILE_PATH)
    achievement_data = load_json(ACHIEVEMENTS_PATH)
    achievements = achievement_data["achievements"]
    assets = profile["assets"]
    focus = " · ".join(profile["focus"])
    stack = " · ".join(f"`{item}`" for item in profile["stack"])
    trophy_text = " · ".join(achievement_label(item) for item in achievements)
    alt_items = [achievement_label(item, ascii_count=True) for item in achievements]
    alt_text = natural_join(alt_items)

    return f'''<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="{assets['hero_dark']}">
  <source media="(prefers-color-scheme: light)" srcset="{assets['hero_light']}">
  <img alt="{profile['brand']} — AI systems, agents and automation" src="{assets['hero_dark']}" width="100%">
</picture>

**{profile['tagline']}**

{focus}

{stack}

### GitHub Achievements

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="{assets['achievements_dark']}">
  <source media="(prefers-color-scheme: light)" srcset="{assets['achievements_light']}">
  <img alt="Animated GitHub achievement trophies: {alt_text}" src="{assets['achievements_dark']}" width="100%">
</picture>

<sub>{trophy_text}</sub>

[Rights & usage]({profile['rights']})

</div>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the RockIn profile README.")
    parser.add_argument("--check", action="store_true", help="Fail if README is not generated from the current source of truth.")
    args = parser.parse_args()
    expected = render_readme()

    if args.check:
        current = README_PATH.read_text(encoding="utf-8")
        if current != expected:
            print("README_GENERATOR_MISMATCH")
            return 1
        print("README_GENERATOR_PASS")
        return 0

    README_PATH.write_text(expected, encoding="utf-8", newline="\n")
    print("README_GENERATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
