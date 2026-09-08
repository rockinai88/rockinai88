from __future__ import annotations

import json
import sys
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sync_pull_shark as sync


class PullSharkTierTests(unittest.TestCase):
    def test_thresholds_are_exact(self) -> None:
        cases = {0: 0, 1: 0, 2: 1, 15: 1, 16: 2, 127: 2, 128: 3, 1023: 3, 1024: 4, 9999: 4}
        for merged_prs, expected in cases.items():
            with self.subTest(merged_prs=merged_prs):
                self.assertEqual(sync.pull_shark_level(merged_prs), expected)

    def test_updates_only_pull_shark_to_higher_level(self) -> None:
        data = {"version": 1, "achievements": [
            {"id": "pull-shark", "name": "Pull Shark", "count": 2, "verified": True},
            {"id": "yolo", "name": "YOLO", "count": 1, "verified": True},
        ]}
        changed = sync.apply_pull_shark_level(data, 3)
        self.assertTrue(changed)
        self.assertEqual(data["achievements"][0]["count"], 3)
        self.assertEqual(data["achievements"][1]["count"], 1)

    def test_blocks_automatic_downgrade(self) -> None:
        data = {"version": 1, "achievements": [
            {"id": "pull-shark", "name": "Pull Shark", "count": 3, "verified": True},
        ]}
        with self.assertRaisesRegex(RuntimeError, "PULL_SHARK_DOWNGRADE_BLOCKED"):
            sync.apply_pull_shark_level(data, 2)
        self.assertEqual(data["achievements"][0]["count"], 3)

    def test_svg_update_is_targeted_and_fail_closed(self) -> None:
        source = (
            '<svg aria-label="Achievements: Pull Shark x2 and YOLO">'
            '<text x="151" y="35" font-weight="900">x2</text>'
            '<text>YOLO</text></svg>'
        )
        updated = sync.render_pull_shark_svg(source, 2, 3)
        self.assertIn("Pull Shark x3", updated)
        self.assertIn(">x3</text>", updated)
        self.assertNotIn("Pull Shark x2", updated)
        with self.assertRaisesRegex(RuntimeError, "PULL_SHARK_SVG_MARKER_INVALID"):
            sync.render_pull_shark_svg('<svg aria-label="Pull Shark x2"><text>YOLO</text></svg>', 2, 3)


class GitHubEvidenceTests(unittest.TestCase):
    def test_rejects_incomplete_search_evidence(self) -> None:
        payload = json.dumps({"total_count": 150, "incomplete_results": True}).encode()
        with self.assertRaisesRegex(RuntimeError, "GITHUB_SEARCH_INCOMPLETE"):
            sync.parse_search_response(payload)

    def test_accepts_complete_search_evidence(self) -> None:
        payload = json.dumps({"total_count": 150, "incomplete_results": False}).encode()
        self.assertEqual(sync.parse_search_response(payload), 150)


class AutomationContractTests(unittest.TestCase):
    def test_search_url_targets_authored_merged_pull_requests(self) -> None:
        url = sync.build_search_url("rockinai88")
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["q"][0]
        self.assertEqual(query, "author:rockinai88 is:pr is:merged")

    def test_workflow_is_free_least_privilege_and_pinned(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "sync-achievements.yml").read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertIn("contents: write", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertIn("actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803", workflow)
        self.assertIn("python3 scripts/sync_pull_shark.py --write", workflow)


class CredentialContractTests(unittest.TestCase):
    def test_requires_dedicated_achievement_token(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "ACHIEVEMENT_GITHUB_TOKEN_MISSING"):
            sync.resolve_search_token({"GITHUB_TOKEN": "repo-scoped-token"})
        self.assertEqual(
            sync.resolve_search_token({"ACHIEVEMENT_GITHUB_TOKEN": "dedicated-user-token"}),
            "dedicated-user-token",
        )

    def test_workflow_uses_only_dedicated_search_secret(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "sync-achievements.yml").read_text(encoding="utf-8")
        self.assertIn("ACHIEVEMENT_GITHUB_TOKEN: ${{ secrets.ACHIEVEMENT_GITHUB_TOKEN }}", workflow)
        sync_block = workflow.split("- name: Sync verified Pull Shark level", 1)[1].split("- name: Regenerate profile README", 1)[0]
        self.assertNotIn("GITHUB_TOKEN: ${{ github.token }}", sync_block)

class SourceGuardTests(unittest.TestCase):
    def test_rejects_unverified_pull_shark_source(self) -> None:
        data = {"version": 1, "achievements": [
            {"id": "pull-shark", "name": "Pull Shark", "count": 2, "verified": False},
        ]}
        with self.assertRaisesRegex(RuntimeError, "PULL_SHARK_SOURCE_INVALID"):
            sync.apply_pull_shark_level(data, 3)


if __name__ == "__main__":
    unittest.main()


class FollowButtonTests(unittest.TestCase):
    def test_generated_readme_uses_exact_profile_follow_link_and_local_asset(self) -> None:
        import generate_profile

        readme = generate_profile.render_readme()
        self.assertIn('href="https://github.com/rockinai88"', readme)
        self.assertIn('src="./assets/follow-rockinai88.svg"', readme)
        self.assertIn('alt="Follow @rockinai88"', readme)
        self.assertNotIn("shields.io", readme.lower())

    def test_follow_button_asset_is_local_svg(self) -> None:
        asset = ROOT / "assets" / "follow-rockinai88.svg"
        self.assertTrue(asset.is_file())
        text = asset.read_text(encoding="utf-8")
        self.assertIn("Follow @rockinai88", text)
        self.assertNotRegex(text, r'(?:href|src)=["\']https?://')
        self.assertNotRegex(text, r'url\(\s*https?://')


class FollowGateTests(unittest.TestCase):
    def test_full_gate_renders_follow_asset(self) -> None:
        gate = (ROOT / "scripts" / "profile-full-gate.ps1").read_text(encoding="utf-8")
        self.assertIn("$Config.follow.asset", gate)
