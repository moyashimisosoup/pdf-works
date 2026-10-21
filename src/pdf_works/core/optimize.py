"""Conservative, non-rasterizing PDF optimization with semantic pre/post checks.

Run only in the spawned PDF worker. Never overwrite the source or a prior output.
This operation optimizes the *source* PDF, not unsaved EditSession changes.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile


def _pdf_signature(document) -> tuple:
    """A bounded semantic check for selected page and document features."""
    def rect_tuple(rect):
        return tuple(round(float(v), 3) for v in rect)

    pages = []
    for page in document:
        annotations = []
        for annotation in page.annots() or ():
            info = annotation.info
            annotations.append((
                annotation.type[0], rect_tuple(annotation.rect),
                info.get("content", ""), info.get("title", ""),
                info.get("subject", ""),
            ))
        links = []
        for link in page.get_links():
            links.append((
                link.get("kind"), link.get("uri"), link.get("page"),
                link.get("nameddest"),
            ))
        pages.append((
            rect_tuple(page.rect), page.rotation, page.get_text("text"),
            tuple(annotations), tuple(links),
        ))
    return (tuple(pages), tuple(tuple(x) for x in document.get_toc(simple=True)))


def optimize_pdf_lossless(
    source: str | Path, destination: str | Path,
) -> dict[str, int]:
    """Write a fresh quality-preserving PDF and return actual byte counts.

    No image recompression to JPEG, page rasterization, resizing, or text flattening.
    Full rewrite can invalidate signatures and interactive forms, so these PDFs
    (plus embedded files) are deliberately refused in this beta mode.
    """
    import fitz

    src = Path(source).resolve(strict=True)
    dst = Path(destination).resolve(strict=False)
    if not src.is_file() or src.suffix.lower() != ".pdf":
        raise ValueError("Source must be an existing PDF")
    if dst.suffix.lower() != ".pdf":
        raise ValueError("Destination must end with .pdf")
    if os.path.normcase(str(src)) == os.path.normcase(str(dst)):
        raise ValueError("The source PDF cannot be overwritten")
    if dst.exists() or dst.is_symlink():
        raise FileExistsError("Output PDF already exists")
    if not dst.parent.is_dir():
        raise FileNotFoundError("Destination folder does not exist")

    temp_name = None
    try:
        with fitz.open(src) as original:
            if not original.is_pdf or original.needs_pass or original.is_encrypted:
                raise ValueError("Encrypted or protected PDF is not supported")
            if original.is_form_pdf or original.get_sigflags() > 0:
                raise ValueError(
                    "Form or signed PDFs are excluded to protect interactive content"
                )
            if original.embfile_count() > 0:
                raise ValueError(
                    "PDFs containing embedded files are excluded in this beta"
                )
            before = _pdf_signature(original)
            source_size = src.stat().st_size
            with tempfile.NamedTemporaryFile(
                dir=dst.parent, prefix=".pdfworks-opt-", suffix=".pdf",
                delete=False,
            ) as temp:
                temp_name = temp.name
            original.save(
                temp_name, garbage=3, deflate=True,
                deflate_images=True, deflate_fonts=True,
                clean=False, use_objstms=0,
            )
        with fitz.open(temp_name) as candidate:
            if candidate.needs_pass or _pdf_signature(candidate) != before:
                raise RuntimeError(
                    "PDF content validation failed; nothing was saved"
                )
            page_count = len(candidate)
        # Hard-link creation is exclusive even if another process created a file
        # after our initial preflight.
        os.link(temp_name, dst)
        return {
            "before_bytes": source_size,
            "after_bytes": dst.stat().st_size,
            "pages": page_count,
        }
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
