# Project Inventory — Brookes Engineering Lab

Scope: repos actively owned by the crew. Last audited 2026-11-23.

## tunertoolpro-core

GUI-free core of TunerToolPro: GM 4L60E/6L80E transmission calibration math, BCT and
EFILive file formats, vehicle/engine data, and the CAN bus sniffer (frames, sniffer
model, ELM327 receive-only monitor, transports).

- **Stack:** Python ≥3.10, zero required deps; `pyserial` (serial adapters) and
  `pandas` (log import) are optional, lazily imported.
- **Distribution model:** vendored core. Consumer apps keep their own copy of
  `tunertoolpro/`, pinned to a release tag in `core.lock`. Releases are immutable git
  tags (`v0.1.0`, ...). Apps update via `tools/update_core.py <tag>`.
- **Default branch:** `main`, at **v0.4.4** as of 2026-11-23 (PRs #5 and #4 merged).
- **Release tags** (immutable; all now ancestors of `main`):
  `v0.1.0`, `v0.1.1`, `v0.4.1`, `v0.4.2`, `v0.4.3`, `v0.4.4`. Note these releases were
  cut from feature branches *before* those branches reached `main`, so tag existence is
  not evidence that a change is on `main` — check with
  `git merge-base --is-ancestor <tag> origin/main`.
- **Tag style is inconsistent:** `v0.4.1` and `v0.4.2` are lightweight; the rest are
  annotated. Immutable, so left as-is.
- **Open branches:**
  - `feature/gmlan-message-table` — GM-LAN message table for high-speed CAN, linked to
    car profile by ECM/TCM labels. Draft PR #3, 2 commits ahead of `main` and 18 behind;
    needs a rebase onto the current `main` before review.
- **Tests:** `python3 -m unittest discover -s tests -t .` — **722 tests, OK (2 skipped)**
  on `main` @ `80af4f9` (verified 2026-11-23). Baseline before the merges was 187 tests
  on `main` @ `4e6fb6c`.

### Pull requests are stacked

PRs in this repo target each other, not always `main`. The v0.4.x series was
`units/boost-gauge` → `feature/torque-extract-packs` → `main`. **Always read a PR's base
branch** (`gh pr view <n> --json baseRefName`) before claiming what a merge will do; a
PR whose head branch contains the newest work is not necessarily the one that lands it
on `main`.

## Jarvis (consolidated)

Former `Jarvis` (desktop/CLI) and `Jarvis-Android` repos merged into one monorepo,
`nbrookes80-spec/jarvis`, with git history preserved via `git subtree`:

- `apps/desktop/` — CLI + desktop voice assistant (Linux/macOS/Windows). Source:
  former `Jarvis` repo, `master` branch. CI configured, 10 merged PRs, actively
  maintained (Venice AI/Gemma/Dolphin model backends, audio-bridge fixes).
- `apps/android/` — Android app, local (NeoHorse via llama.cpp JNI) and cloud (Venice)
  model backends, Room storage for chats/notes, SAF export. Source: former
  `Jarvis-Android` repo, `docs/model-import-readme` branch (one commit ahead of
  `master`, no conflicts) — the most complete line; the repo's default `main` branch
  was nearly empty and is not represented.

**Flagged, not merged:** `Jarvis`'s `backup-local-master` branch had 3 commits
(Ollama/Gemma work) that conflict with equivalent work later merged into `master` via
PRs #5-#9. These were left out of the consolidation rather than auto-resolved — pending
explicit review if still wanted.

The original `Jarvis` and `Jarvis-Android` repos are renamed to `jarvis-desktop-legacy`
and `jarvis-android-legacy` and archived as read-only historical reference.

## Out of scope (flagged, not under active crew work)

- `ncat-poa-context-plugin` (legal/Power-of-Attorney plugin) — legal domain, not
  engineering.
- `stremio-adult-site-directory` — unrelated.
- `t43-6l80e-reference`, `Ender3V2S1-20260106`, `ai-skills-hub`, `noddy` — owned by the
  user but not yet confirmed in scope for crew work.
- ~27 forked repos (OSINT tools, Torque Pro docs, Printrun, LS_Based_Engine_Repository,
  Holden-Commodore, etc.) — treated as read-only reference material, not crew-owned
  projects, unless the owner says otherwise.
