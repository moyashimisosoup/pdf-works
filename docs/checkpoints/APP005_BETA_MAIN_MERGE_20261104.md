# APP-005 | Windows PDF Works beta merged into main | 2026-11-04 JST

## Confirmed integration
- Repository: https://github.com/moyashimisosoup/pdf-works
- PR: https://github.com/moyashimisosoup/pdf-works/pull/1
- PR #1 was marked ready for review and merged (merge method: merge).
- Merge commit `57fd51bdb1315ad27337aa4b9e6b9716118e5eaa` verified as current `main` HEAD on GitHub.
- Tested PR head: `c06c9f61b51d1cef0ea1bdd5b9457b5380c48a6f`.
- [Linux backend CI](https://github.com/moyashimisosoup/pdf-works/actions/runs/41687160692): SUCCESS.
- [Windows Qt CI](https://github.com/moyashimisosoup/pdf-works/actions/runs/41687160697): SUCCESS, including `start-pdf-works.cmd --check` smoke test using installed CI Python.
- Read-back from `main`: `README.md` and `start-pdf-works.cmd` exist.

## User-operable Windows beta
- Download or clone `main`; `start-pdf-works.cmd` installs required Python packages into a local virtual environment on first run then launches the native Qt editor.
- `setup-pdf-works.cmd` is available for installation / repair.
- Requires user-installed Python 3.11+ and initial internet access. No EXE, Windows installer, or auto-deployment to user hardware has been created.
- Optional Zen Maru Gothic fonts: run `.venv\Scripts\python.exe scripts/install_fonts.py`; without fonts, a fallback font is used.
- Features: PDF viewing, pages editing (rotate/delete/move/Undo), save as new file, ROI to PNG/gallery/A4 sheet, extract/split, quality-preserving PDF optimization.
- Existing files / original PDFs are not intended to be overwritten; encrypted, forms, signature fields and attachments are not supported for optimization.

## Honest acceptance boundary
- GitHub-hosted Windows Qt tests passed with artificial PDFs; the user's actual Windows desktop was **not remotely installed or manually tested**.
- Human GUI usability, DPI, performance, private real-world PDF layouts and long-session stability are still unverified.
- Font/Qt/PyMuPDF EXE redistribution licensing remains unresolved. Do not claim a distributable standalone EXE.
- The repo is public. Never commit school, personal or nonpublic PDFs.

## Next single step
- On Windows with Python 3.11+ installed: obtain the repository `main`, run `start-pdf-works.cmd` and open an artificial PDF. Record any failure message if it does not start. The detailed hands-on checklist is at `docs/BETA_RUN.md`.
