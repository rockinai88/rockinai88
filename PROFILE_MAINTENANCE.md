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
