# APP-005 PDF Works | Windows optimize gate | 2026-10-21 JST

## Scope and baseline
- Repository: https://github.com/moyashimisosoup/pdf-works
- Branch: `feature/native-page-edit-20261017`; PR #1 stays open and draft.
- Verified code/workflow commit: `fa3bc6fef4de51a3510495df49b2320685db83b6`.
- `main` remained `3501df8e966aed5c8975181bf6fa005ca7c8275b` when checked.
- Follow `AGENTS.md` and `docs/COMPRESSION_PLAN.md`.

## Verified
- Quality-preserving optimization core, spawned worker `optimize_lossless`, and Qt save/status UI already existed and were inspected. Avoid duplicate implementation.
- Windows UI workflow now runs `tests/test_optimize.py` and `tests/test_optimize_worker.py` **on Windows**, in addition to the existing mocked Qt optimization tests; optimize core/worker/test changes trigger the workflow.
- [Linux backend #39557115805](https://github.com/moyashimisosoup/pdf-works/actions/runs/39557115805): success.
- [Windows Qt #39557116008](https://github.com/moyashimisosoup/pdf-works/actions/runs/39557116008): success, including **9 passed** Windows PDF optimization + real spawned worker tests.
- Existing optimize tests cover 1/8/40 page synthetic text/geometry, annotations, links, outline, source non-overwrite, output collision, forms, embedded files and IPC. Never claim these tests guarantee preservation for every real-world PDF.

## Remaining acceptance gates
1. Run `docs/BETA_RUN.md` on user's Windows PC with synthetic 40-page PDF; record response/freezing, source/output bytes and source SHA-256 before/after.
2. Confirm real Qt click flow and output re-open, searchability, bookmark/link/annotation behavior, images/visual differences and refusal of existing output names.
3. Add a dedicated signed-PDF rejection regression fixture; current core checks `is_form_pdf`/`get_sigflags()`, but no signed fixture is present in `tests/test_optimize.py`. Also evaluate encrypted PDFs and difficult real layouts without uploading private documents.
4. Measure size and latency on representative artificial scan-heavy and vector/font-heavy PDFs before considering lossy presets.

Do not merge to main, publish, or distribute an EXE without user acceptance and licensing review. This checkpoint is docs-only and follows the tested `fa3bc6f` commit; there are no new functional code changes.
