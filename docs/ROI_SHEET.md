# ROI contact sheet (A4 2x4) / PDF Works
2026-10-20. Development branch: `feature/native-page-edit-20261017`.

## Workflow
1. Open PDF, select a normalized region with "範囲を選択".
2. Export PNGs to a chosen folder. Do not overwrite existing outputs.
3. The gallery opens. Press "PDF保存" and select a new PDF filename.
4. Generate an A4 portrait PDF with two columns and four rows.
5. Each tile preserves aspect ratio, numbered in gallery order with its original source page ID.
6. Nine or more images create additional sheets; 40 images create five A4 pages.

Implementation: `core/roi_sheet.py` (PyMuPDF, atomic no-overwrite), `workers/renderer.py` (`roi_sheet_export`), `ui/editor_window.py` and `ui/roi_gallery.py`.

Safety: no overwrite of source PDF, PNGs, or existing output. Files are checked before use, output is validated before exclusive final naming. The heavy PDF operation is run in an isolated PDF worker rather than the Qt main event loop.

Validation: local synthetic 1/8/9/40-page PDF tests passed. Backend CI #39351025065 and Windows Qt UI CI #39351025388 both succeeded using synthetic data. Real user Windows file dialog and print workflow still require manual verification.

Outstanding: user Windows E2E, filtering/reordering gallery tiles, print test, cancellation/progress UI, and embedded Japanese captions. Do not merge Draft PR #1 into main before desktop validation.
