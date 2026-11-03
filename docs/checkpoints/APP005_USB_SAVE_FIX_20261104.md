# APP-005 CHECKPOINT | Windows USB Save As repair | 2026-11-04 JST

## User-visible evidence
- User encountered WinError 1 when saving to an E: USB drive.
- The **same unsaved edit session succeeded when saving to the Windows Desktop**. User confirmed that outcome.
- Therefore the edited PDF can be preserved without discarding the in-memory edits; inspect the Desktop PDF and copy it to USB using File Explorer before closing the old running process.
- USB filesystem type has **not** been verified. OS hard-link incompatibility is the leading cause supported by code and behavior, not a directly confirmed device diagnosis.

## Implemented and merged
- [PR #2](https://github.com/moyashimisosoup/pdf-works/pull/2) merged into `main`.
- Merge commit: `7238a9a8362b1757483889f296e186a13462e517`.
- Windows: new-file commit uses same-directory `os.rename` instead of `os.link`, avoiding hard-link requirements for exFAT/FAT USB volumes. POSIX retains exclusive hard-link behavior.
- `export.py`: no-edit Save As uses direct byte copy, and actual edits batch contiguous page copies to reduce repeated PDF resource work. Original and existing destinations remain protected.
- Shared fix applied to quality-preserving optimization and A4 ROI contact sheet export.
- Three focused regressions in `tests/test_windows_save_publish.py`, including explicit no-hard-link Windows branch and no-overwrite test.
- [Linux CI #41692088442](https://github.com/moyashimisosoup/pdf-works/actions/runs/41692088442): SUCCESS.
- [Windows Qt CI #41692088481](https://github.com/moyashimisosoup/pdf-works/actions/runs/41692088481): SUCCESS, including real Windows Save As tests.
- GitHub main read-back confirms commit and new helper.

## Remaining boundary and next action
- The **old running PDF Works process is not hot-patched**. After confirming a safe Desktop PDF, close and reopen the updated main code.
- Git clone: `git fetch origin; git switch main; git pull --ff-only origin main`. ZIP install: download current main ZIP and extract fresh.
- Actual save to the user's USB has not been re-tested after the fix.
- Existing left sidebar has lazily loaded thumbnails. A separate larger / grid thumbnail overview request remains a UX improvement, not part of this bugfix.
- Next operation: confirm saved Desktop PDF opens, then update main and test a new file save to USB.
