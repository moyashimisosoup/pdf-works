"""Align one source PDF (A) against one fixed reference PDF (B).

The output is a NEW PDF containing only A's pages, each placed on a canvas
the same physical dimensions as B's first page. No rasterization or network.
The first pages determine one uniform scale for every source page.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import tempfile

from .file_commit import publish_new_file

POINTS_PER_MM = 72.0 / 25.4
MAX_PAGES = 500


def placement(
    source_size: tuple[float, float],
    reference_size: tuple[float, float],
    percent: float = 100.0,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    *,
    base_source_size: tuple[float, float] | None = None,
) -> tuple[float, float, float, float]:
    """Return the rectangle on B's PDF page where A's content is positioned.

    A is initially fit to B (aspect ratio preserved). The same physical
    scale calculated for A page 1 is reused for every page in a file.
    Offsets are in real-world mm, never screen pixels.
    """
    dimensions = (*source_size, *reference_size, percent, x_mm, y_mm)
    if not all(math.isfinite(float(value)) for value in dimensions):
        raise ValueError("Non-finite alignment value")
    sw, sh = (float(v) for v in source_size)
    rw, rh = (float(v) for v in reference_size)
    bw, bh = (float(v) for v in (base_source_size or source_size))
    if min(sw, sh, rw, rh, bw, bh) <= 0:
        raise ValueError("PDF page dimensions must be positive")
    if not 30.0 <= percent <= 300.0:
        raise ValueError("Scale must be between 30% and 300%")
    if not -100.0 <= x_mm <= 100.0 or not -100.0 <= y_mm <= 100.0:
        raise ValueError("Offset must be between -100 and +100 mm")
    base = min(rw / bw, rh / bh)
    factor = base * float(percent) / 100.0
    width, height = sw * factor, sh * factor
    left = (rw - width) / 2.0 + x_mm * POINTS_PER_MM
    top = (rh - height) / 2.0 + y_mm * POINTS_PER_MM
    return (left, top, left + width, top + height)


def _check_pdf(document, *, source: bool):
    if document.needs_pass or document.is_encrypted or not document.is_pdf:
        raise ValueError("Password-protected or non-PDF document cannot be aligned")
    if not 1 <= len(document) <= MAX_PAGES:
        raise ValueError(f"PDF must contain 1 to {MAX_PAGES} pages")
    if source:
        if (document.is_form_pdf or document.get_sigflags() > 0
                or document.embfile_count() > 0):
            raise ValueError(
                "A contains forms, signatures or attachments which cannot "
                "be preserved by alignment. Export was cancelled."
            )
        for i, page in enumerate(document):
            if page.get_links() or list(page.annots() or ()) or list(page.widgets() or ()):
                raise ValueError(
                    f"A page {i + 1} contains annotations or links; "
                    "alignment was cancelled to avoid deleting them."
                )


def inspect_pair(a_path: str | Path, b_path: str | Path) -> dict:
    """Metadata only; called from the PDF worker, never the GUI thread."""
    import fitz

    a = Path(a_path).resolve(strict=True)
    b = Path(b_path).resolve(strict=True)
    if not a.is_file() or not b.is_file():
        raise ValueError("Choose two PDF files")
    with fitz.open(a) as da, fitz.open(b) as db:
        _check_pdf(da, source=True)
        _check_pdf(db, source=False)
        return {
            "source_pages": len(da),
            "reference_pages": len(db),
            "source_size": tuple(da[0].rect)[2:],
            "reference_size": tuple(db[0].rect)[2:],
        }


def render_pair(a_path: str | Path, b_path: str | Path, width: int = 600) -> dict:
    """Bounded low-resolution first-page previews for both documents."""
    import fitz

    if type(width) is not int or not 100 <= width <= 800:
        raise ValueError("Invalid preview width")
    details = inspect_pair(a_path, b_path)
    images = {}
    for key, filename in (("a", a_path), ("b", b_path)):
        with fitz.open(filename) as document:
            page = document[0]
            factor = min(width / max(page.rect.width, 1.0), 900 / max(page.rect.height, 1.0))
            pix = page.get_pixmap(
                matrix=fitz.Matrix(factor, factor),
                colorspace=fitz.csRGB,
                alpha=False,
            )
            images[key] = {
                "width": pix.width, "height": pix.height,
                "stride": pix.stride, "samples": bytes(pix.samples),
            }
    return {**details, "images": images}


def export_aligned(
    a_path: str | Path,
    b_path: str | Path,
    destination: str | Path,
    percent: float = 100.0,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
) -> dict:
    """Place all pages of A on B-sized pages without touching either input."""
    import fitz

    a = Path(a_path).resolve(strict=True)
    b = Path(b_path).resolve(strict=True)
    target = Path(destination).resolve(strict=False)
    if a.suffix.lower() != ".pdf" or b.suffix.lower() != ".pdf":
        raise ValueError("A and B must be PDFs")
    if target.suffix.lower() != ".pdf":
        raise ValueError("Output must have .pdf extension")
    if os.path.normcase(str(target)) in (os.path.normcase(str(a)), os.path.normcase(str(b))):
        raise ValueError("Cannot overwrite A or B")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Output already exists; choose a new name")
    if not target.parent.is_dir():
        raise FileNotFoundError("Output directory does not exist")

    temp_name: str | None = None
    try:
        with fitz.open(a) as source, fitz.open(b) as reference:
            _check_pdf(source, source=True)
            _check_pdf(reference, source=False)
            ref_size = (reference[0].rect.width, reference[0].rect.height)
            first_size = (source[0].rect.width, source[0].rect.height)
            # Reject invalid inputs before creating a file.
            placement(first_size, ref_size, percent, x_mm, y_mm)
            with fitz.open() as result:
                for index, page in enumerate(source):
                    rect = placement(
                        (page.rect.width, page.rect.height),
                        ref_size, percent, x_mm, y_mm,
                        base_source_size=first_size,
                    )
                    out = result.new_page(width=ref_size[0], height=ref_size[1])
                    out.show_pdf_page(
                        fitz.Rect(*rect), source, index,
                        keep_proportion=False, overlay=True,
                    )
                with tempfile.NamedTemporaryFile(
                    prefix=".pdfworks-align-", suffix=".pdf",
                    dir=target.parent, delete=False,
                ) as tmp:
                    temp_name = tmp.name
                result.save(temp_name, garbage=1, deflate=False)
        with fitz.open(temp_name) as check:
            if len(check) != len(source):
                raise RuntimeError("Aligned PDF page count mismatch")
            if any(
                abs(page.rect.width - ref_size[0]) > 0.1
                or abs(page.rect.height - ref_size[1]) > 0.1
                for page in check
            ):
                raise RuntimeError("Output page size mismatch")
        publish_new_file(temp_name, target)
        return {"pages": len(source), "bytes": target.stat().st_size}
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
