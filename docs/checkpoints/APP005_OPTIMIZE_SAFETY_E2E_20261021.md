# APP-005 | CHECKPOINT | Compression safety and Windows Qt E2E | 2026-10-21 JST

## Source of truth
- Repo: https://github.com/moyashimisosoup/pdf-works
- Branch: `feature/native-page-edit-20261017`, Draft PR #1 OPEN. No merge to `main`, no release/EXE.
- Verified implementation/workflow commit: `33367b3ad8b4fd51edd624546d28626707305d0c`.
- Subsequent docs-only commits: `e28bb9310caf169b9f06d8e66ab381d96bfa12f8` and `f0ed1a65638b291f9701b8b513ca478ade4f34a4`.
- Development rules: `AGENTS.md`; compression design: `docs/COMPRESSION_PLAN.md`.

## New changes
1. `f22c03f`: `tests/test_optimize.py` adds 3 structural signature field refusals (SigFlags=1, synthetic signed-like dictionary, missing optional SigFlags) plus AES-256 encrypted input refusal. Rejected attempts must create no output and preserve source SHA-256.
2. `61a4c85`: `tests/test_optimize_e2e_ui.py` exercises Qt `EditWindow` -> actual spawned `PdfBridge` worker -> output on a 40-page artificial PDF, checking completion feedback, search text, bookmarks, original hash, and edit state.
3. `33367b3`: Windows Qt CI adds the real-worker Qt end-to-end test after the existing optimize UI and backend tests.
4. Documentation updated after tests, including README status correcting older alpha-only wording.

## Verification on the tested code SHA
- [Linux backend run #39562384297](https://github.com/moyashimisosoup/pdf-works/actions/runs/39562384297): SUCCESS, **84 passed, 8 skipped, 1 warning**; Qt E2E is skipped there due to no PySide6.
- [Windows Qt run #39562384279](https://github.com/moyashimisosoup/pdf-works/actions/runs/39562384279): SUCCESS, optimization core+real worker **13 passed**, complete Qt->spawn->save **1 passed**.
- The signed-like fixture contains dummy `/ByteRange` and `/Contents`, **not** a valid PKCS#7 signature. Therefore real-world cryptographic signature validation was **not** performed.
- The above tests are CI/artificial. Not evidence of hands-on use on the user's Windows PC.

## Unverified and next operation
- Run `docs/BETA_RUN.md` on the user's Windows PC with a 40-page artificial PDF: use actual dialog, select/rotate/undo, ROI to PNG/gallery/contact sheet, extraction/splits, optimize, re-open, compare bytes/appearance/searchability, responsiveness and source SHA-256.
- After hands-on acceptance, profile scan/image-heavy and font/vector-heavy PDF performance and verify visual fidelity. Real signed, form and encrypted documents should remain excluded; no private files in Git.
- `fitz` emits a deprecation warning; migrate compatibility carefully in a separate reviewed change, not a rushed bulk rewrite.
- Do not merge to main, publish, or distribute EXE until acceptance and licensing are reviewed.
