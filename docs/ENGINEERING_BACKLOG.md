# Engineering Backlog — Brookes Engineering Lab

Last revised 2026-11-23. See `PROJECT_INVENTORY.md` for repo context.

## Done

- **tunertoolpro-core: `main` brought from v0.1.1 to v0.4.4.** PR #5
  (`units/boost-gauge` → `feature/torque-extract-packs`) and PR #4
  (`feature/torque-extract-packs` → `main`) both merged with merge commits, so commit
  SHAs are preserved and all published tags remain reachable from `main`. Verified:
  722 tests OK (2 skipped) on `main` @ `80af4f9`; `v0.1.1`, `v0.4.1`–`v0.4.4` all
  confirmed as ancestors of `main`. Status: **PASS**.

## Open

1. **tunertoolpro-core: declare `pyjnius` as an optional dependency.**
   `jnius` is imported in `scanner/storage.py`, `link/devices.py` and `link/obd.py`.
   The imports are correctly lazy (inside functions, matching the `pyserial`/`pandas`
   pattern), so nothing breaks off-Android — but the dependency is undeclared, and the
   README states the core has no required dependencies. Add an
   `android = ["pyjnius"]` extra under `[project.optional-dependencies]` and note it in
   the README. Severity: low. Owner: CODEX, review SENTINEL.

2. **tunertoolpro-core: decide whether `pyproject.toml` version should track tags.**
   It currently reads `version = "0.1.0"` while published tags are at `v0.4.4`. Since
   apps pin by tag via `core.lock`, the metadata version may be deliberately unused —
   but the drift is misleading. Needs an owner decision, then either bump it per release
   or document that tags are authoritative. Severity: low.

3. **tunertoolpro-core: PR #3 (GM-LAN message table) needs a rebase.**
   Draft, 2 commits ahead of `main` and 18 behind. Before it leaves draft, TORQUE or
   VECTOR must confirm whether the GM-LAN table is validated against captured CAN
   traffic or still provisional — do not merge an unverified signal table.
   Severity: medium (correctness of CAN signal definitions).

4. **tunertoolpro-core: test suite leaks sockets.**
   Transport/session tests emit `ResourceWarning: unclosed socket` repeatedly. No test
   failures, but leaked descriptors can make CI flaky under load. Close sockets in
   `tearDown` or use context managers. Severity: low. Owner: SENTINEL.

5. **jarvis: decide fate of the 3 flagged `backup-local-master` commits.**
   Ollama/Gemma work that conflicts with the history already merged into
   `apps/desktop/`. Preserved read-only in the archived `jarvis-desktop-legacy` repo.
   Either explicitly discard as superseded or do a reviewed manual reconciliation — do
   not auto-merge. Severity: owner decision.

6. **jarvis: verify `apps/desktop` and `apps/android` build and test independently**
   inside the monorepo layout. CI workflows, packaging scripts and relative paths may
   assume repo-root context that no longer holds under `apps/<name>/`. Severity: medium.
   Owner: NEXUS.
