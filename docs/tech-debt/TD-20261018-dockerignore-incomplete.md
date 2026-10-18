---
name: td-20261018-dockerignore-incomplete
description: `.dockerignore` excludes only `.env`/`.secrets` literally and sends agent/tooling dirs (`.kronn/`, `.claude/`, `.mcp.json`, `docs/`) into the build context.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Verified in source
      reviewer: Docker audit 0.8.2
      note: first detection
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-dockerignore-incomplete

- **Area**: Infra
- **Category**: docker
- **Severity**: Low
- **Status**: Fixed
- **Effort**: S
- **Blast radius**: local (1-2 files)

## Problem (fact)
`.dockerignore` lists `.git/`, `.github/`, `workflows/`, `*.iso`, `out/`, `README.md`, `LICENSE`, `tmp/`, `.env`, `.secrets`. It has no `.env*` glob, and does not exclude `.kronn/`, `.claude/`, `.codex/`, `.gemini/`, `.copilot/`, `.mcp.json`, `docs/`, `todo/`, or `scripts/__pycache__/`. `.gitignore` already treats `.kronn/` and `.mcp.json` as local-only. No Containerfile does `COPY .`; all COPYs target `./src/*`, `./scripts/gen-recipe.py` or `Containerfile*`, so nothing from these dirs is baked into an image.

## Impact
Local or remote builds ship agent state, MCP config and any `.env.<suffix>` file to the build daemon/remote builder as part of the context. Context size and upload time grow with docs/agent churn.

## Where (pointers)
- `.dockerignore:1-10` — full exclusion list
- `.gitignore:13-17` — `.env`, `.secrets`, `.kronn/`, `.mcp.json` treated as local secrets/state
- `Containerfile:56`, `Containerfile:73`, `Containerfile:171` — only `./src/*` copied
- `Containerfile.iso:56-57` — `Containerfile*` and `scripts/gen-recipe.py` copied

## Suggested direction
Invert to an allow-list (`*` then `!src/`, `!scripts/gen-recipe.py`, `!Containerfile*`) or at least add `.env*`, `.secrets*`, `.kronn/`, `.claude/`, `.codex/`, `.gemini/`, `.copilot/`, `.mcp.json*`, `docs/`, `todo/`, `**/__pycache__/`.

## Resolution
Added `.env*`, `.secrets*`, agent state dirs, `.mcp.json*`, `docs/`, `todo/`, `tests/`, `.venv/`, cache dirs and `**/__pycache__/` to `.dockerignore`. The allow-list variant was not chosen: the shared CI may add files to the build context, which cannot be checked from this repo. `tests/integration/test_build_context.py` asserts that no `COPY` source is excluded.
