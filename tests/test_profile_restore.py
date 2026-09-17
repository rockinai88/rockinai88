from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class ProfileRestoreTests(unittest.TestCase):
    def test_readme_keeps_current_brand_and_restores_follow_and_trophies(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("./assets/rockin-showcase-dark.svg", readme)
        self.assertIn('href="https://github.com/rockinai88"', readme)
        self.assertIn('./assets/follow-rockinai88.svg', readme)
        self.assertIn('./assets/github-achievements-motion.svg', readme)
        self.assertIn('./assets/github-achievements-motion-light.svg', readme)
        self.assertNotIn("rockin-logo-dark.svg", readme)

    def test_follow_asset_is_local_and_safe(self):
        asset = ROOT / "assets" / "follow-rockinai88.svg"
        self.assertTrue(asset.is_file())
        text = asset.read_text(encoding="utf-8")
        self.assertIn("Follow @rockinai88", text)
        self.assertNotIn('href="http', text)
        self.assertNotIn('src="http', text)
        self.assertNotIn('url(http', text)


class PullSharkRestoreTests(unittest.TestCase):
    def setUp(self):
        import sync_pull_shark as sync
        self.sync = sync

    def test_thresholds_match_pull_shark_tiers(self):
        cases = {0: 0, 2: 1, 16: 2, 128: 3, 1024: 4}
        for merged_prs, level in cases.items():
            with self.subTest(merged_prs=merged_prs):
                self.assertEqual(self.sync.pull_shark_level(merged_prs), level)

    def test_source_level_is_verified_and_consistent_with_both_svgs(self):
        data = json.loads((ROOT / "profile" / "achievements.json").read_text(encoding="utf-8"))
        pull = [x for x in data["achievements"] if x["id"] == "pull-shark"]
        self.assertEqual(len(pull), 1)
        level = pull[0]["count"]
        self.assertIn(level, (1, 2, 3, 4))
        self.assertTrue(pull[0]["verified"])
        for name in ("github-achievements-motion.svg", "github-achievements-motion-light.svg"):
            svg = (ROOT / "assets" / name).read_text(encoding="utf-8")
            self.assertIn(f"Pull Shark x{level}", svg)
            self.assertIn(f">x{level}</text>", svg)

    def test_workflow_only_syncs_achievement_files(self):
        workflow = (ROOT / ".github" / "workflows" / "sync-achievements.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "17 6 * * *"', workflow)
        self.assertIn("ACHIEVEMENT_GITHUB_TOKEN", workflow)
        self.assertIn("python3 scripts/sync_pull_shark.py --write", workflow)
        self.assertNotIn("generate_profile.py", workflow)
        staged = workflow.split("git add", 1)[1]
        self.assertIn("profile/achievements.json", staged)
        self.assertNotIn("README.md", staged)

    def test_sync_blocks_downgrades(self):
        data = {"version": 1, "achievements": [
            {"id": "pull-shark", "name": "Pull Shark", "count": 3, "verified": True}
        ]}
        with self.assertRaisesRegex(RuntimeError, "PULL_SHARK_DOWNGRADE_BLOCKED"):
            self.sync.apply_pull_shark_level(data, 2)


if __name__ == "__main__":
    unittest.main()
