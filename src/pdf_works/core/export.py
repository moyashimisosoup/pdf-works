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
    fine_angles: Sequence[int] | None = None,
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
    fine = list(fine_angles) if fine_angles is not None else [0] * len(pages)
    if len(fine) != len(pages) or any(
        type(value) is not int or not -100 <= value <= 100 for value in fine
    ):
        raise ValueError("Invalid fine tilt: expected tenths of degrees (-100 to +100)")

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

            if any(fine):
                if (original.is_form_pdf or original.get_sigflags() > 0
                        or original.is_encrypted or original.embfile_count() > 0):
                    raise ValueError(
                        "微調整保存には署名・フォーム・暗号化・添付付きPDFを使用できません"
                    )
                for slot, ticks in enumerate(fine):
                    if ticks == 0:
                        continue
                    page = original[source_indices[slot]]
                    if page.get_links() or list(page.annots() or ()) or list(page.widgets() or ()):
                        raise ValueError(
                            f"元{source_indices[slot] + 1}ページにはリンク・注釈・フォームがあります。"
                            "微調整ではこれらを保持できないため保存を中止しました"
                        )

            with tempfile.NamedTemporaryFile(
                prefix=".pdf-works-", suffix=".pdf",
                dir=dst.parent, delete=False,
            ) as tmp:
                temp_name = tmp.name

            no_edits = len(source_indices) == len(original) and all(
                i == slot and pages[slot][1] == 0 and fine[slot] == 0
                for slot, i in enumerate(source_indices)
            )
            if no_edits:
                # An unchanged Save As is a straight byte copy.
                shutil.copyfile(src, temp_name)
            else:
                # Rotate residual tilt as vector content, not a raster image.
                # remove_rotation() normalizes existing 90° rotation into
                # page contents in this *in-memory* copy, never on disk.
                tilted = fitz.open(src) if any(fine) else None
                try:
                    if tilted is not None:
                        for source_index in {
                            source_indices[slot] for slot, ticks in enumerate(fine) if ticks
                        }:
                            tilted[source_index].remove_rotation()
                    with fitz.open() as output:
                        slot = 0
                        while slot < len(source_indices):
                            if fine[slot]:
                                src_page = original[source_indices[slot]]
                                width, height = src_page.rect.width, src_page.rect.height
                                if pages[slot][1] in (90, 270):
                                    width, height = height, width
                                page = output.new_page(width=width, height=height)
                                page.show_pdf_page(
                                    page.rect, tilted, source_indices[slot],
                                    # show_pdf_page positive angles are counterclockwise;
                                    # Qt and page.set_rotation positive are clockwise.
                                    rotate=-float(pages[slot][1] + fine[slot] / 10.0),
                                    keep_proportion=True,
                                )
                                # Any orientation is baked into the visible
                                # vector content; /Rotate remains zero.
                                expected_rotations[slot] = 0
                                slot += 1
                                continue
                            end = slot
                            while (
                                end + 1 < len(source_indices)
                                and fine[end + 1] == 0
                                and source_indices[end + 1] == source_indices[end] + 1
                            ):
                                end += 1
                            output.insert_pdf(
                                original,
                                from_page=source_indices[slot],
                                to_page=source_indices[end],
                                links=True, annots=True,
                            )
                            for page_slot in range(slot, end + 1):
                                output[page_slot].set_rotation(
                                    expected_rotations[page_slot]
                                )
                            slot = end + 1
                        # Compression is the separate Optimize action.
                        output.save(temp_name, garbage=1, deflate=False)
                finally:
                    if tilted is not None:
                        tilted.close()
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
