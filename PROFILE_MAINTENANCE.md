# RockIn Profile Maintenance

This repository keeps the public profile presentation deterministic and locally verifiable.

## Sources of truth

- `profile/profile.json` controls public brand text, focus areas, stack, and asset paths.
- `profile/achievements.json` lists only GitHub achievements that were explicitly verified.
- `README.md` is generated from those sources.
- Trophy SVGs remain explicit visual evidence and must cover every verified achievement.

## Commands

Regenerate the README and run the complete local gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\profile-maintenance.ps1
```

Check without rewriting the README:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\profile-maintenance.ps1 -CheckOnly
```

After committing, require a clean worktree:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\profile-full-gate.ps1 -RequireClean
```

A new achievement is not accepted until its name, count, and visual representation are all verified.

## Automatic Pull Shark sync

`Pull Shark` is the only achievement currently synchronized automatically.

- Evidence source: GitHub Search API for PRs authored by `rockinai88` and merged.
- Levels: 2 merged PRs → x1, 16 → x2, 128 → x3, 1024 → x4.
- The sync is monotonic: a lower computed level never overwrites a previously verified level.
- Incomplete or invalid GitHub search results fail closed and produce no commit.
- The scheduled workflow uses only the repository `GITHUB_TOKEN`, a standard public `ubuntu-latest` runner, and `contents: write`.
- README and both achievement SVGs are updated only when the verified Pull Shark level increases.

Other GitHub achievement types remain explicit/manual because GitHub does not expose a stable achievements API for them.
