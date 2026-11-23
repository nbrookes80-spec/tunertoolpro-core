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
- **Default branch:** `main` (2 commits — lagging well behind open feature branches).
- **Active branches:**
  - `feature/torque-extract-packs` — 13 commits ahead of `main` (PID packs, 2.7 bar MAP
    scaling, GM engineering-report pack). Open PR #4.
  - `units/boost-gauge` — 15 commits ahead (includes torque-extract-packs' commits plus
    MAP boost gauge reading, Bluetooth close-race fix). Open PR #5.
  - `feature/gmlan-message-table` — 1 commit ahead (GM-LAN message table for high-speed
    CAN, linked to car profile by ECM/TCM labels). Draft PR #3.
- **Tests:** `python -m unittest discover -s tests -t .` (not yet run against the open
  branches as part of this audit).

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
