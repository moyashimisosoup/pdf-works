"""Export selected edited pages or split them into separate PDFs without overwriting.

The functions belong in a spawned worker process, not the Qt GUI thread.
"""
from __future__ import annotations
from pathlib import Path
from typing import Sequence

from .export import save_edited_pdf


def selected_page_specs(snapshot: Sequence[tuple[int, int]],
                        selected_rows: Sequence[int]) -> list[tuple[int, int]]:
    """Keep the current edited order, never sort by original PDF page number."""
    if not selected_rows or any(type(i) is not int or not 0 <= i < len(snapshot)
                                for i in selected_rows):
        raise ValueError("Select valid pages first")
    rows = sorted(selected_rows)
    if len(set(rows)) != len(rows):
        raise ValueError("Duplicate selected page")
    return [snapshot[i] for i in rows]


def split_selected_pdf(source: str | Path, output_dir: str | Path,
                       pages: Sequence[tuple[int, int]], prefix: str) -> list[Path]:
    """Create one new PDF per selected page; preflight, then roll back on errors.

    Naming embeds selection order and original source page number. Existing files
    are untouched, including a colliding existing part. The source remains intact.
    """
    src = Path(source).resolve(strict=True)
    folder = Path(output_dir).resolve(strict=True)
    if not src.is_file() or src.suffix.lower() != ".pdf":
        raise ValueError("Source must be an existing PDF")
    if not folder.is_dir():
        raise ValueError("Select an existing output folder")
    if (not isinstance(prefix, str) or not 1 <= len(prefix) <= 64
            or prefix.strip(" .") != prefix
            or any(char in prefix for char in '<>:"/\\|?*')):
        raise ValueError("Invalid output filename prefix")
    if not pages:
        raise ValueError("Select at least one page")
    if (any(not isinstance(p, (tuple, list)) or len(p) != 2
            or type(p[0]) is not int or type(p[1]) is not int
            or p[0] < 0 or p[1] not in (0, 90, 180, 270) for p in pages)
            or len({p[0] for p in pages}) != len(pages)):
        raise ValueError("Invalid or duplicate source pages")
    targets = [
        folder / f"{prefix}_{i+1:03d}_source_{index+1:03d}.pdf"
        for i, (index, _) in enumerate(pages)
    ]
    if any(p.exists() or p.is_symlink() or p.resolve() == src
           for p in targets):
        raise FileExistsError("A split output already exists, choose another folder")
    created: list[Path] = []
    try:
        for destination, spec in zip(targets, pages):
            save_edited_pdf(src, destination, [spec])
            created.append(destination)
        return created
    except Exception:
        for destination in created:
            destination.unlink(missing_ok=True)
        raise
