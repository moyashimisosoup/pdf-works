"""Atomic, no-overwrite PDF export. Intended for a worker process only."""
from __future__ import annotations
import os
from pathlib import Path
import tempfile
from typing import Sequence


def save_edited_pdf(source: str | Path, destination: str | Path,
                    pages: Sequence[tuple[int, int]]) -> int:
    import fitz

    src = Path(source).resolve(strict=True)
    dst = Path(destination).resolve(strict=False)
    if not src.is_file() or src.suffix.lower() != ".pdf":
        raise ValueError("Source must be a PDF file")
    if dst.suffix.lower() != ".pdf":
        raise ValueError("Output filename must end in .pdf")
    if os.path.normcase(str(src)) == os.path.normcase(str(dst)):
        raise ValueError("Cannot overwrite the source PDF")
    if dst.exists():
        raise FileExistsError(f"Destination already exists: {dst.name}")
    if not dst.parent.is_dir():
        raise FileNotFoundError("Destination folder does not exist")
    if not pages:
        raise ValueError("At least one page must remain")

    temp_name: str | None = None
    try:
        with fitz.open(src) as original, fitz.open() as output:
            if original.needs_pass or not original.is_pdf:
                raise ValueError("Password-protected or non-PDF source")
            seen: set[int] = set()
            expected_rotations: list[int] = []
            for source_index, delta in pages:
                if not isinstance(source_index, int) or isinstance(source_index, bool):
                    raise ValueError("Invalid source index")
                if source_index in seen or not 0 <= source_index < len(original):
                    raise ValueError("Invalid or duplicate source page")
                seen.add(source_index)
                if delta not in (0, 90, 180, 270):
                    raise ValueError("Invalid page rotation")
                output.insert_pdf(original, from_page=source_index, to_page=source_index,
                                  links=True, annots=True)
                copied = output[-1]
                expected_rotation = (original[source_index].rotation + delta) % 360
                copied.set_rotation(expected_rotation)
                expected_rotations.append(expected_rotation)
            with tempfile.NamedTemporaryFile(prefix=".pdf-works-", suffix=".pdf",
                                             dir=dst.parent, delete=False) as tmp:
                temp_name = tmp.name
            output.save(temp_name, garbage=3, deflate=True)
        with fitz.open(temp_name) as check:
            if len(check) != len(pages):
                raise RuntimeError("Saved PDF page count mismatch")
            for idx, expected in enumerate(expected_rotations):
                if check[idx].rotation != expected:
                    raise RuntimeError(f"Unexpected rotation on page {idx+1}")
        # Atomic create-if-absent on NTFS and POSIX: never overwrite a concurrent file.
        os.link(temp_name, dst)
        return len(pages)
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
