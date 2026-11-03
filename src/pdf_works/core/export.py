"""Fast, exclusive, non-destructive PDF Save As in the spawned worker."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from typing import Sequence

from .file_commit import publish_new_file


def save_edited_pdf(
    source: str | Path,
    destination: str | Path,
    pages: Sequence[tuple[int, int]],
) -> int:
    import fitz

    src = Path(source).resolve(strict=True)
    dst = Path(destination).resolve(strict=False)
    if not src.is_file() or src.suffix.lower() != ".pdf":
        raise ValueError("Source must be a PDF file")
    if dst.suffix.lower() != ".pdf":
        raise ValueError("Output filename must end in .pdf")
    if os.path.normcase(str(src)) == os.path.normcase(str(dst)):
        raise ValueError("Cannot overwrite the source PDF")
    if dst.exists() or dst.is_symlink():
        raise FileExistsError(f"Destination already exists: {dst.name}")
    if not dst.parent.is_dir():
        raise FileNotFoundError("Destination folder does not exist")
    if not pages:
        raise ValueError("At least one page must remain")

    temp_name: str | None = None
    try:
        with fitz.open(src) as original:
            if original.needs_pass or not original.is_pdf:
                raise ValueError("Password-protected or non-PDF source")
            seen: set[int] = set()
            source_indices: list[int] = []
            expected_rotations: list[int] = []
            for source_index, delta in pages:
                if type(source_index) is not int:
                    raise ValueError("Invalid source index")
                if source_index in seen or not 0 <= source_index < len(original):
                    raise ValueError("Invalid or duplicate source page")
                if type(delta) is not int or delta not in (0, 90, 180, 270):
                    raise ValueError("Invalid page rotation")
                seen.add(source_index)
                source_indices.append(source_index)
                expected_rotations.append(
                    (original[source_index].rotation + delta) % 360
                )

            with tempfile.NamedTemporaryFile(
                prefix=".pdf-works-", suffix=".pdf",
                dir=dst.parent, delete=False,
            ) as tmp:
                temp_name = tmp.name

            no_edits = len(source_indices) == len(original) and all(
                i == slot and pages[slot][1] == 0
                for slot, i in enumerate(source_indices)
            )
            if no_edits:
                # An unchanged Save As is a straight byte copy.
                shutil.copyfile(src, temp_name)
            else:
                with fitz.open() as output:
                    # Batch adjacent source pages to avoid repeated PDF resource
                    # transfer on every page, especially with large scans.
                    start = 0
                    while start < len(source_indices):
                        end = start
                        while (
                            end + 1 < len(source_indices)
                            and source_indices[end + 1] == source_indices[end] + 1
                        ):
                            end += 1
                        output.insert_pdf(
                            original,
                            from_page=source_indices[start],
                            to_page=source_indices[end],
                            links=True, annots=True,
                        )
                        start = end + 1
                    for slot, rotation in enumerate(expected_rotations):
                        output[slot].set_rotation(rotation)
                    # Compression belongs to the separate Optimize command.
                    output.save(temp_name, garbage=1, deflate=False)

        with fitz.open(temp_name) as check:
            if len(check) != len(source_indices):
                raise RuntimeError("Saved PDF page count mismatch")
            for idx, expected in enumerate(expected_rotations):
                if check[idx].rotation != expected:
                    raise RuntimeError(f"Unexpected rotation on page {idx + 1}")
        publish_new_file(temp_name, dst)
        return len(source_indices)
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
