"""Normalized visual ROI, PNG export without modifying an input PDF.

Use only in a spawned PDF worker, never on the Qt GUI thread.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import tempfile
from typing import Iterable

MAX_OUTPUT_PIXELS = 16_000_000


@dataclass(frozen=True)
class NormalizedROI:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self):
        coords = (self.left, self.top, self.right, self.bottom)
        if any(type(n) not in (float, int) or not math.isfinite(n)
               or not 0 <= n <= 1 for n in coords):
            raise ValueError("ROI coordinates must be finite numbers from 0 to 1")
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("ROI must have positive width and height")

    def in_rect(self, displayed_rect):
        """Use the already-rotated visible page.rect; do not rotate twice."""
        import fitz
        r = displayed_rect
        return fitz.Rect(r.x0 + r.width * self.left,
                         r.y0 + r.height * self.top,
                         r.x0 + r.width * self.right,
                         r.y0 + r.height * self.bottom)


def export_region_pngs(
    source: str | Path, destination_dir: str | Path,
    roi: NormalizedROI, ordered_pages: Iterable[tuple[int, int]],
    *, dpi: int = 200, max_pixels: int = MAX_OUTPUT_PIXELS,
) -> list[Path]:
    """Extract a selected region in edited page order to new PNGs.

    Source rotations are preserved; only the local fitz document copy is
    mutated while rendering. Existing output filenames are never replaced.
    """
    import fitz

    if not isinstance(roi, NormalizedROI):
        raise TypeError("roi must be a NormalizedROI")
    if type(dpi) is not int or not 36 <= dpi <= 300:
        raise ValueError("DPI must be an integer in [36, 300]")
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("Invalid pixel budget")
    src = Path(source).resolve(strict=True)
    outdir = Path(destination_dir).resolve(strict=True)
    if src.suffix.lower() != ".pdf" or not src.is_file():
        raise ValueError("Source must be an existing PDF")
    if not outdir.is_dir():
        raise ValueError("Choose an existing output folder")
    items = list(ordered_pages)
    if not items:
        raise ValueError("Select at least one page")
    if any(not isinstance(p, (tuple, list)) or len(p) != 2
           or type(p[0]) is not int or type(p[1]) is not int
           or p[1] not in (0, 90, 180, 270) for p in items):
        raise ValueError("Invalid page or rotation")
    if len(set(p[0] for p in items)) != len(items):
        raise ValueError("Duplicate source page")

    outputs = [outdir / f"roi_{position + 1:03d}_source_{page + 1:03d}.png"
               for position, (page, _) in enumerate(items)]
    if any(path.exists() or path.is_symlink() for path in outputs):
        raise FileExistsError("An ROI output already exists in that folder")

    created: list[Path] = []
    try:
        with fitz.open(src) as document:
            if not document.is_pdf or document.needs_pass:
                raise ValueError("Invalid or password-protected PDF")
            if any(not 0 <= index < len(document) for index, _ in items):
                raise IndexError("Source page does not exist")
            for (index, delta), destination in zip(items, outputs):
                page = document[index]
                original_rotation = page.rotation
                page.set_rotation((original_rotation + delta) % 360)
                try:
                    clip = roi.in_rect(page.rect)
                    scale = dpi / 72.0
                    estimate = math.ceil(clip.width * scale + 1) * math.ceil(clip.height * scale + 1)
                    if estimate > max_pixels:
                        raise ValueError("Requested ROI exceeds pixel budget")
                    pix = page.get_pixmap(dpi=dpi, clip=clip, alpha=False, annots=True)
                    if pix.width * pix.height > max_pixels:
                        raise ValueError("Rendered ROI exceeds pixel budget")
                    temporary_name = None
                    try:
                        with tempfile.NamedTemporaryFile(
                            dir=outdir, prefix=".pdfworks-roi-", suffix=".png",
                            delete=False,
                        ) as tmp:
                            temporary_name = tmp.name
                        pix.save(temporary_name)
                        # NTFS / POSIX hard-link creation is exclusive. No overwrite.
                        os.link(temporary_name, destination)
                        created.append(destination)
                    finally:
                        if temporary_name:
                            Path(temporary_name).unlink(missing_ok=True)
                finally:
                    page.set_rotation(original_rotation)
        return created
    except Exception:
        # Delete only files created by this call. Source never changed.
        for created_path in created:
            created_path.unlink(missing_ok=True)
        raise
