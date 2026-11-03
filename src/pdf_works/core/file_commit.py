"""Confirm a fully written PDF without overwriting an existing destination.

On Windows, os.rename is a same-directory atomic move and refuses to replace
an existing destination. Unlike os.link, it works on FAT/exFAT and volumes
without hard-link support. POSIX uses exclusive hard-link creation.
"""
from __future__ import annotations

import os
from pathlib import Path


def publish_new_file(temporary: str | Path, destination: str | Path) -> None:
    source = Path(temporary)
    target = Path(destination)
    if source.parent.resolve() != target.parent.resolve():
        raise ValueError("Temporary and destination PDF must share a directory")
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Destination already exists: {target.name}")

    if os.name == "nt":
        # Windows os.rename raises FileExistsError if the destination exists,
        # including when another process creates it after the preflight.
        # No hard links required (e.g. E: exFAT, network or cloud drives).
        os.rename(source, target)
    else:
        # POSIX rename replaces existing files; exclusive link preserves the
        # existing no-overwrite guarantee instead.
        os.link(source, target)
