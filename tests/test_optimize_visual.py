"""Synthetic visual-fidelity and workload checks for quality-preserving PDF saves.

No private samples or third-party images. Timings are observational only.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import random
import struct
import sys
import time
import zlib

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.optimize import optimize_pdf_lossless


def _chunk(name: bytes, payload: bytes) -> bytes:
    data = name + payload
    return struct.pack(">I", len(payload)) + data + struct.pack(
        ">I", zlib.crc32(data) & 0xFFFFFFFF
    )


def synthetic_png(seed: int, width: int = 400, height: int = 520) -> bytes:
    """Make a deterministic raster image using only standard-library modules."""
    rng = random.Random(seed)
    raw = b"".join(b"\x00" + rng.randbytes(width * 3) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b"")
    )


def make_pdf(path: Path, kind: str, count: int) -> None:
    images = [synthetic_png(i + 103) for i in range(4)] if kind != "vector" else []
    image_xrefs: dict[int, int] = {}
    with fitz.open() as document:
        for i in range(count):
            page = document.new_page(width=430, height=580)
            if images:
                slot = i % len(images)
                rect = fitz.Rect(12, 12, 418, 568)
                if slot in image_xrefs:
                    page.insert_image(rect, xref=image_xrefs[slot])
                else:
                    image_xrefs[slot] = page.insert_image(rect, stream=images[slot])
            if kind in ("mixed", "vector"):
                page.draw_rect(
                    fitz.Rect(45, 125, 280, 240),
                    fill=(0.08, 0.35, 0.8),
                    fill_opacity=0.37,
                    overlay=True,
                )
                for line in range(12):
                    y = 272 + 20 * line
                    page.insert_text(
                        (30, y), f"SEARCHABLE_{kind.upper()}_{i + 1}_{line}",
                        fontsize=10,
                    )
                page.draw_line((24, 415), (399, 470), color=(0.85, 0.1, 0.1))
            if i % 5 == 0:
                page.set_rotation((i // 5 % 4) * 90)
        document.set_toc([[1, "Start", 1], [1, "End", count]])
        document.save(path)


@pytest.mark.parametrize(
    ("kind", "count", "render_every_page"),
    [
        ("scan", 40, False),
        ("mixed", 20, True),
        ("vector", 100, False),
    ],
)
def test_visual_fidelity_and_size_report(tmp_path, kind, count, render_every_page):
    source = tmp_path / f"{kind}_{count}.pdf"
    destination = tmp_path / f"{kind}_{count}_optimized.pdf"
    make_pdf(source, kind, count)
    original_hash = hashlib.sha256(source.read_bytes()).digest()
    start = time.perf_counter()
    report = optimize_pdf_lossless(source, destination)
    elapsed = time.perf_counter() - start
    assert original_hash == hashlib.sha256(source.read_bytes()).digest()
    assert report["pages"] == count
    assert report["before_bytes"] == source.stat().st_size
    assert report["after_bytes"] == destination.stat().st_size
    assert not list(tmp_path.glob(".pdfworks-opt-*.pdf"))

    with fitz.open(source) as before, fitz.open(destination) as after:
        assert before.get_toc() == after.get_toc()
        indices = (
            range(count) if render_every_page
            else sorted(set([0, count // 2, count - 1]))
        )
        for index in indices:
            old_page, new_page = before[index], after[index]
            assert old_page.rect == new_page.rect
            assert old_page.rotation == new_page.rotation
            assert old_page.get_text("text") == new_page.get_text("text")
            assert len(old_page.get_images(full=True)) == len(
                new_page.get_images(full=True)
            )
            old_render = old_page.get_pixmap(
                matrix=fitz.Matrix(0.8, 0.8), colorspace=fitz.csRGB, alpha=False
            )
            new_render = new_page.get_pixmap(
                matrix=fitz.Matrix(0.8, 0.8), colorspace=fitz.csRGB, alpha=False
            )
            assert (old_render.width, old_render.height) == (
                new_render.width, new_render.height
            )
            assert hashlib.sha256(old_render.samples).digest() == hashlib.sha256(
                new_render.samples
            ).digest(), f"rendered pixels differ: {kind} page {index + 1}"

    delta = report["after_bytes"] - report["before_bytes"]
    print(
        f"QUALITY_WORKLOAD kind={kind} pages={count} "
        f"before_bytes={report['before_bytes']} "
        f"after_bytes={report['after_bytes']} delta_bytes={delta} "
        f"elapsed_seconds={elapsed:.3f}",
        flush=True,
    )
