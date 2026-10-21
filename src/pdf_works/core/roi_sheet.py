"""Create a no-overwrite A4 contact sheet from previously exported ROI PNGs.

Only call from the spawned PDF worker; never run image/PDF IO in Qt's event loop.
"""
from __future__ import annotations

import os
import struct
from pathlib import Path
import tempfile
from typing import Sequence

ROWS, COLUMNS = 4, 2
PER_SHEET = ROWS * COLUMNS
MAX_ITEMS = 1000
MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGE_BYTES = 64 * 1024 * 1024


def save_roi_contact_sheet(
    image_files: Sequence[str | Path],
    source_ids: Sequence[int],
    destination: str | Path,
) -> int:
    """Save a new A4 PDF, eight ROI images per sheet, and return its page count."""
    import fitz

    if not image_files or len(image_files) != len(source_ids):
        raise ValueError("The sheet requires aligned nonempty image and page lists")
    if len(image_files) > MAX_ITEMS:
        raise ValueError(f"Too many ROI images (limit {MAX_ITEMS})")
    if any(type(source) is not int or source < 0 for source in source_ids):
        raise ValueError("Invalid original page index")

    target = Path(destination).resolve(strict=False)
    if target.suffix.lower() != ".pdf":
        raise ValueError("Output must have a .pdf extension")
    if not target.parent.is_dir():
        raise FileNotFoundError("Destination folder not found")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Output PDF already exists")

    paths = []
    for raw in image_files:
        source = Path(raw).resolve(strict=True)
        if source.suffix.lower() != ".png" or not source.is_file():
            raise ValueError("All ROI inputs must be PNG files")
        if source.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError("An image exceeds the allowed file size")
        with source.open("rb") as reader:
            header = reader.read(24)
        if (len(header) != 24 or header[:8] != bytes.fromhex("89504e470d0a1a0a")
                or header[12:16] != b"IHDR"):
            raise ValueError("Input is not a PNG image")
        pixel_width, pixel_height = struct.unpack(">II", header[16:24])
        if (pixel_width == 0 or pixel_height == 0
                or pixel_width * pixel_height > MAX_IMAGE_PIXELS):
            raise ValueError("An image exceeds the pixel budget")
        paths.append(source)

    temp_name = None
    width, height = fitz.paper_size("a4")
    left_margin, right_margin = 28.0, 28.0
    top_y, bottom_y = 64.0, height - 33.0
    horizontal_gap, vertical_gap = 13.0, 11.0
    tile_width = (width - left_margin - right_margin - horizontal_gap) / COLUMNS
    tile_height = (bottom_y - top_y - (ROWS - 1) * vertical_gap) / ROWS
    label_height = 23.0
    sheet_count = (len(paths) + PER_SHEET - 1) // PER_SHEET
    try:
        with fitz.open() as output:
            for idx, (image_path, source_id) in enumerate(zip(paths, source_ids)):
                slot = idx % PER_SHEET
                if slot == 0:
                    page = output.new_page(width=width, height=height)
                    sheet_no = len(output)
                    page.insert_text(
                        (left_margin, 29), "PDF WORKS / ROI CONTACT SHEET",
                        fontsize=12, fontname="helv", color=(.19, .14, .22),
                    )
                    page.insert_text(
                        (left_margin, 46),
                        f"Items {idx+1}-{min(idx+PER_SHEET, len(paths))} of {len(paths)}",
                        fontsize=9, fontname="helv", color=(.46, .42, .52),
                    )
                    page.insert_text(
                        (width-right_margin-50, height-17),
                        f"{sheet_no} / {sheet_count}", fontsize=9,
                        fontname="helv", color=(.46, .42, .52),
                    )
                row, col = divmod(slot, COLUMNS)
                x0 = left_margin + col * (tile_width + horizontal_gap)
                y0 = top_y + row * (tile_height + vertical_gap)
                box = fitz.Rect(x0, y0, x0 + tile_width, y0 + tile_height)
                page.draw_rect(box, color=(.82, .79, .86), fill=(1, 1, 1), width=.6)
                inset = 8.0
                image_rect = fitz.Rect(
                    x0+inset, y0+inset, x0+tile_width-inset,
                    y0+tile_height-label_height-inset,
                )
                page.insert_image(image_rect, filename=str(image_path),
                                  keep_proportion=True, overlay=True)
                separator_y = y0+tile_height-label_height-3
                page.draw_line((x0+inset, separator_y),
                               (x0+tile_width-inset, separator_y),
                               color=(.90, .88, .92), width=.6)
                caption = f"{idx+1:03d}  /  Original page {source_id+1}"
                page.insert_text((x0+10, y0+tile_height-9), caption, fontsize=9,
                                 fontname="helv", color=(.22, .16, .27))
            with tempfile.NamedTemporaryFile(
                prefix=".pdfworks-contact-", suffix=".pdf",
                dir=target.parent, delete=False,
            ) as tmp:
                temp_name = tmp.name
            output.save(temp_name, garbage=3, deflate=True)
        with fitz.open(temp_name) as check:
            if len(check) != sheet_count:
                raise RuntimeError("Contact sheet PDF page count mismatch")
        os.link(temp_name, target)  # atomic create-if-absent
        return sheet_count
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
