# APP-005 | HANDOFF_READY | 2026-10-21 JST

**Status: PAUSED — awaiting next development session and Windows hands-on acceptance.**
This is a checkpoint, not an instruction to publish or merge.

## 1. Scope / canonical references
- APP-ID: APP-005 / PDF Works native Windows Qt editor.
- Work ID: not verified in this session; do not invent or register a new one.
- Canonical repository: https://github.com/moyashimisosoup/pdf-works
- Draft PR #1: https://github.com/moyashimisosoup/pdf-works/pull/1
- Branch: `feature/native-page-edit-20261017`
- Verified source HEAD before writing this checkpoint: `c7c9f617a59ef0132534f1e11e9a750b6f581d6f`
- main observed unchanged: `3501df8e966aed5c8975181bf6fa005ca7c8275b`
- APP portfolio canonical ledger: https://github.com/moyashimisosoup/session-deck/blob/main/docs/APP_PORTFOLIO.md
- Repo instructions: `AGENTS.md`. Architecture: `docs/SPEC_V5.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/COMPRESSION_PLAN.md`.

## 2. Saved / checked
- Page editing: Ctrl/Shift multi-selection, batch rotation/delete, undo, rearrange by up/down, safe save-as.
- ROI: normalized region drag, per-page PNG export, lazy gallery, exclude/reorder, A4 2x4 contact sheet.
- Extraction: selected pages to a new PDF, per-page split, by-N split and cut-after-page positions.
- Real source PDF byte size displayed.
- Quality-preserving optimization added in this work sequence: `src/pdf_works/core/optimize.py`, `workers/renderer.py` `optimize_lossless`, `ui/editor_window.py` save dialog/status, tests and documentation.
- This optimization works on the opened **source PDF**, not unsaved EditSession changes. Unsaved edits block the operation. It does not promise file-size reduction.
- Safeguards: no source/existing-output overwrite, preflight refusal of encrypted/signed/form/embedded-file PDFs, re-open after save and compare dimensions, rotations, extracted text, annotations, links and outline; no downsampling or flattening.
- CI for source HEAD `c7c9f617...`: [backend #39414382469](https://github.com/moyashimisosoup/pdf-works/actions/runs/39414382469) SUCCESS; [Windows Qt #39414382611](https://github.com/moyashimisosoup/pdf-works/actions/runs/39414382611) SUCCESS.
- Draft PR #1 remains OPEN and DRAFT; branch was mergeable (clean) when checked. Neither main nor publishing were changed.

## 3. Not verified / unimplemented
- **User's Windows hardware**: end-to-end opening a real PDF, Ctrl/Shift multi-selection, rotation/undo, ROI PNG -> gallery -> contact PDF, extraction, splitting and quality-preserving optimization with real files. CI offscreen Qt tests are not equivalent.
- Optimization on complex documents: actual Japanese embedded fonts, layered/vector art, transparent backgrounds, large scans, links/annotations/structure preservation, performance, memory and visual differences under real workloads.
- Electronic signatures, AcroForm, encryption and embedded files are intentionally rejected; support is NOT implemented. No guarantee for unsupported document classes.
- Quality presets with image recompression, ROI resize handles, GUI drag ordering, Redo and distributable EXE remain outside the current confirmed implementation.
- Some earlier roadmap items may be stale. Reconcile with code, commits, CI and current PR before marking anything complete.
- A further commit adding THIS checkpoint is documentation only and has not itself passed CI unless its run is checked separately.

## 4. First operation in the next session
1. Read this exact handoff and `AGENTS.md`; fetch latest GitHub branch HEAD, PR #1 and CI results **before** any editing. Do not assume the `c7c9f617` baseline is still the latest.
2. Inspect and execute the current Windows desktop acceptance checklist in repo docs (do not upload sensitive documents). Capture factual pass/fail and performance (rough elapsed time, original/output byte count) for a 40-page synthetic PDF.
3. Only after that decide on focused fixes for size-growth/quality preservation and consider further compression modes. Keep the PR DRAFT and main untouched pending acceptance.

## 5. Session boundary
- User asked to stop at a clean point and hand off because the work was taking too long.
- Stop feature work now. This document is the durable handoff artifact; next session must verify current HEAD and avoid repeated implementations.
