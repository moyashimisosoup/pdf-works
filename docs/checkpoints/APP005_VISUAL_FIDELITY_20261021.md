# APP-005 | CHECKPOINT | Artificial visual fidelity and performance | 2026-10-21 JST

## Canonical state
- Repo: https://github.com/moyashimisosoup/pdf-works
- APP-ID: APP-005. work_id: not verified; do not create another.
- Branch: `feature/native-page-edit-20261017`, [Draft PR #1](https://github.com/moyashimisosoup/pdf-works/pull/1). Keep `main` unchanged.
- Functional/test changes: `c81f716c3428f8e93e77467b2113d3b22130a1bc` (new synthetic test) and `9eab625a1765ae2380a03d597c5be26f7d1c64cc` (Windows workflow).
- Documentation: `75a9d0246534bee038a95ca8af223caedabce502` (`COMPRESSION_PLAN.md`).

## Verification
- [Linux Backend CI #39612856545](https://github.com/moyashimisosoup/pdf-works/actions/runs/39612856545): SUCCESS, 87 passed, 8 skipped, 1 warning.
- [Windows Qt CI #39612856560](https://github.com/moyashimisosoup/pdf-works/actions/runs/39612856560): SUCCESS, raster/vector tests 3 passed; existing real Qt->spawn worker 40-page optimize E2E still passed.
- `tests/test_optimize_visual.py`: deterministic synthetic PNG rasters (not actual scanned text), transparent vector overlays, searchable ASCII text, rotation, bookmarks. Checks input hash untouched, bytes and page count, and exact sampled RGB render hashes (80% scale) before/after. Mixed 20p all pages sampled; raster 40p and vector 100p 3 pages each.
- Windows runner measurements (single sample; seconds exclude startup and visual checking):

| Case | Before bytes | After bytes | Delta bytes | Optimize call seconds |
| --- | ---: | ---: | ---: | ---: |
| Artificial raster 40p | 2512986 | 2512054 | -932 | 0.091 |
| Mixed raster/text/opacity 20p | 2554066 | 2557984 | +3918 | 0.105 |
| Vector/text 100p | 268629 | 273208 | +4579 | 0.136 |

These are NOT compression guarantees, end-user speed metrics, or evidence that every PDF is pixel-preserved. The `fitz` deprecation warning is still present. No JPEG downsampling or lossy conversion was introduced.

## Next gate
1. Perform a *hands-on* acceptance test of beta on user's Windows PC using `docs/BETA_RUN.md`. Start with the repo-generated artificial 40-page PDF, not private school PDFs.
2. Verify page edit/undo, ROI->PNG gallery->A4 sheet, split/extract, real optimize button, copy-free source preservation, normal / 125% / 150% DPI controls and GUI responsiveness. Record actual source/output byte count and source SHA-256 before and after.
3. Review complex Japanese fonts, scan PDFs, links/annotations and memory/long-running usage separately. Signed/forms/password/attached files must remain excluded.
4. Keep PR Draft. No main merge, public release, or EXE distribution until hands-on acceptance and licensing checks.
