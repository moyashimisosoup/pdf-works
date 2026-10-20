"""Position-based and fixed-size splitting of the currently edited PDF order.

These functions are called by the spawned PDF worker, never by the Qt GUI thread.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from .export import save_edited_pdf

MAX_PARTS = 500


def safe_output_prefix(stem: str) -> str:
    """Sanitize a document basename for Windows / POSIX output paths."""
    if not isinstance(stem, str):
        raise TypeError("Filename stem must be text")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem)[:48].strip(" .")
    if not name:
        name = "pdf"
    if name.split(".")[0].upper() in (
        {"CON", "PRN", "AUX", "NUL"} |
        {f"COM{i}" for i in range(1, 10)} |
        {f"LPT{i}" for i in range(1, 10)}
    ):
        name = "pdf_" + name
    return name


def partition_page_specs(
    pages: Sequence[tuple[int, int]], mode: str,
    *, size: int | None = None, boundaries: Sequence[int] | None = None,
) -> list[list[tuple[int, int]]]:
    """Return contiguous groups using 1-based *edited* page positions.

    'size' means N pages per file. 'boundaries' means cuts *after* page K,
    e.g. [3, 7] -> 1-3 / 4-7 / 8-end.
    """
    if not pages:
        raise ValueError("There must be at least one edited page")
    snapshot = list(pages)
    if (any(not isinstance(p, (tuple, list)) or len(p) != 2 or
            type(p[0]) is not int or type(p[1]) is not int or
            p[0] < 0 or p[1] not in (0, 90, 180, 270)
            for p in snapshot)
            or len({p[0] for p in snapshot}) != len(snapshot)):
        raise ValueError("Invalid edited pages")
    count = len(snapshot)
    if mode == "fixed":
        if type(size) is not int or size <= 0 or boundaries is not None:
            raise ValueError("Enter a positive number of pages per file")
        cuts = list(range(size, count, size))
    elif mode == "boundaries":
        if size is not None or boundaries is None:
            raise ValueError("Specify the pages to cut after")
        cuts = list(boundaries)
        if (not cuts or any(type(x) is not int or not 1 <= x < count for x in cuts)
                or cuts != sorted(set(cuts))):
            raise ValueError("Cut points must be unique, increasing, and before the last page")
    else:
        raise ValueError("Unknown split mode")
    if len(cuts) + 1 > MAX_PARTS:
        raise ValueError(f"Too many output files (limit {MAX_PARTS})")
    marks = [0] + cuts + [count]
    return [snapshot[a:b] for a, b in zip(marks, marks[1:])]


def export_partitioned_pdf(
    source: str | Path, folder: str | Path,
    pages: Sequence[tuple[int, int]], prefix: str,
    mode: str, *, size: int | None = None,
    boundaries: Sequence[int] | None = None,
) -> list[Path]:
    """Preflight every destination and roll back only files created by this run."""
    src = Path(source).resolve(strict=True)
    directory = Path(folder).resolve(strict=True)
    if not src.is_file() or src.suffix.lower() != ".pdf":
        raise ValueError("Source must be a PDF")
    if not directory.is_dir():
        raise ValueError("Output folder does not exist")
    groups = partition_page_specs(pages, mode, size=size, boundaries=boundaries)
    if type(prefix) is not str or prefix != safe_output_prefix(prefix):
        raise ValueError("Invalid file prefix")
    starts = []
    position = 1
    for group in groups:
        starts.append((position, position + len(group) - 1))
        position += len(group)
    destinations = [
        directory / f"{prefix}_part_{i+1:03d}_pages_{start:03d}-{end:03d}.pdf"
        for i, (start, end) in enumerate(starts)
    ]
    if any(path.exists() or path.is_symlink() or path.resolve() == src
           for path in destinations):
        raise FileExistsError("A split output already exists; choose another folder")
    created: list[Path] = []
    try:
        for target, group in zip(destinations, groups):
            save_edited_pdf(src, target, group)
            created.append(target)
        return created
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
