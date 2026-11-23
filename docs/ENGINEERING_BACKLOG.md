# Engineering Backlog — Brookes Engineering Lab

Prioritized 2026-11-23. See `PROJECT_INVENTORY.md` for full repo context.

1. **tunertoolpro-core: merge the three open PRs onto `main`.**
   `main` is 13-15 commits behind already-reviewed work (#3 GMLAN message table —
   draft, #4 torque-extract-packs, #5 boost-gauge). Highest-value, lowest-risk cleanup
   in the crew's current scope. Run the full test suite on each branch before merge
   (SENTINEL).

2. **tunertoolpro-core: confirm `feature/gmlan-message-table` (PR #3, draft) is ready
   to leave draft.** Needs a decision from TORQUE/VECTOR on whether the GM-LAN table
   is validated against real CAN traffic or still provisional.

3. **jarvis (consolidated): decide fate of the 3 flagged `backup-local-master`
   commits** (Ollama/Gemma work that conflicts with `apps/desktop`'s merged history).
   Either explicitly discard as superseded or do a reviewed manual reconciliation —
   do not auto-merge.

4. **jarvis (consolidated): verify `apps/desktop` and `apps/android` build/test
   independently** inside the new monorepo layout (paths, CI workflows, packaging
   scripts may assume repo-root context that no longer holds under `apps/<name>/`).

5. **tunertoolpro-core: no automated test run has been performed yet** as part of this
   audit. Baseline `python -m unittest discover -s tests -t .` on `main` and each open
   branch before the Step 6/7 merge-and-test cycle in the development process.

Lowest priority: `jarvis`/`apps/desktop` on its own is the healthiest of the three
projects (CI green, PRs cleanly merged) — no urgent backlog items beyond #3 and #4
above.
