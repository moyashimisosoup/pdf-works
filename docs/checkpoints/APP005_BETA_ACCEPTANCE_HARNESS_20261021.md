# APP-005 | Windows beta acceptance harness | CHECKPOINT | 2026-10-21 JST

## Canonical context
- APP-ID: APP-005 PDF Works
- Repo: https://github.com/moyashimisosoup/pdf-works
- Branch: `feature/native-page-edit-20261017`
- PR: https://github.com/moyashimisosoup/pdf-works/pull/1 (Draft, not merged)
- Baseline from previous checkpoint: `df69c6e31e365490e746185bcd4ec06790d410b5` (Windows synthetic raster/opacity/vector CI success)
- Last checked new working commit: `affa1a5736d72b4b8649c37ed94e2842aff78f76`
- Instructions: `AGENTS.md`, `docs/BETA_RUN.md`.

## Changes saved
1. `scripts/windows_beta_acceptance.py` creates a unique Git-ignored `output/beta-acceptance/run-.../` with 40-page **synthetic** PDF, source hash manifest, and manual checklist. It records a latest-run pointer without overwriting PDF files. A separate `verify` command checks the source SHA, actual byte counts, all 40 pages' text/rotation/geometry and sampled render pixels of pages 1, 21, 40 against a separately saved `optimized.pdf`.
2. `tests/test_windows_beta_acceptance.py`: four tests cover separate runs, pending output, successful optimize-and-verify, source mutation refusal, and corrupted result detection.
3. Windows workflow now tests the helper and triggers on its script changes. Existing backend test workflow discovers the four tests.
4. `docs/BETA_RUN.md` documents the hands-on sequence: prepare -> launch app -> save optimized.pdf -> verify. Automated verification reports `pass/fail/incomplete`, and always labels manual GUI acceptance unverified. No automatic collection or external upload.

## Verification status at this checkpoint
- Saved changes and GitHub file read-back verified.
- Previous known-good SHA `df69c6e`: [Linux backend #39613523519](https://github.com/moyashimisosoup/pdf-works/actions/runs/39613523519) SUCCESS; [Windows Qt #39613523329](https://github.com/moyashimisosoup/pdf-works/actions/runs/39613523329) SUCCESS.
- Latest code/test SHA `affa1a57`: [Linux backend #39616103392](https://github.com/moyashimisosoup/pdf-works/actions/runs/39616103392) and [Windows Qt #39616103247](https://github.com/moyashimisosoup/pdf-works/actions/runs/39616103247) were **QUEUED** at last check. **Do not claim these new tests passed** until conclusions are SUCCESS.
- User's Windows PC beta hands-on acceptance remains **NOT RUN/NOT VERIFIED**.

## Next operation
1. Re-fetch latest branch HEAD, PR and both workflow runs, diagnose any failing test and correct it without merging.
2. Only once CI passes, use `docs/BETA_RUN.md` on the user's Windows PC with synthetic data. Report both `verification.json` results and manual GUI observations (no private PDF uploads).
3. Keep `main`, release and EXE delivery untouched. Licensing check and realistic Japanese/scan-heavy sample coverage remain later gates.

CHECKPOINT documents test preparation; it does **not** certify desktop acceptance.
