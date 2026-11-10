"""Artificial PDF regression for one A/reference-B scale alignment."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.alignment import export_aligned, inspect_pair, placement


def make_pair(folder):
    a, b = folder / "a.pdf", folder / "b.pdf"
    with fitz.open() as doc:
        for index in range(2):
            page = doc.new_page(width=300, height=400)
            page.insert_text((35, 55), f"ANSWER_{index + 1}")
            page.draw_rect(fitz.Rect(20, 90, 275, 360))
        doc.save(a)
    with fitz.open() as doc:
        page = doc.new_page(width=310, height=430)
        page.insert_text((38, 60), "REFERENCE")
        doc.save(b)
    return a, b


def sha(path):
    return hashlib.sha256(path.read_bytes()).digest()


def test_one_pair_exports_only_a_pages_without_modifying_inputs(tmp_path):
    a, b = make_pair(tmp_path)
    dst = tmp_path / "a_aligned.pdf"
    old_a, old_b = sha(a), sha(b)
    meta = inspect_pair(a, b)
    assert meta["source_pages"] == 2
    assert meta["reference_pages"] == 1
    assert meta["reference_size"] == (310, 430)
    result = export_aligned(a, b, dst, percent=102.5, x_mm=2.0, y_mm=-1.5)
    assert result["pages"] == 2
    assert result["bytes"] == dst.stat().st_size
    assert sha(a) == old_a
    assert sha(b) == old_b
    with fitz.open(dst) as out:
        assert len(out) == 2
        for index in range(2):
            assert out[index].rect == fitz.Rect(0, 0, 310, 430)
            assert out[index].search_for(f"ANSWER_{index + 1}")
            assert "REFERENCE" not in out[index].get_text("text")


def test_placement_is_uniform_and_measured_in_pdf_millimeters():
    first = placement((300, 400), (310, 430))
    moved = placement((300, 400), (310, 430), percent=100, x_mm=10)
    assert moved[0] - first[0] == pytest.approx(10 * 72 / 25.4)
    bigger = placement((300, 400), (310, 430), percent=105)
    assert bigger[2] - bigger[0] == pytest.approx(
        (first[2] - first[0]) * 1.05
    )
    with pytest.raises(ValueError):
        placement((300, 400), (310, 430), percent=0)


def test_existing_and_annotated_pdfs_are_protected(tmp_path):
    a, b = make_pair(tmp_path)
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"DO NOT REPLACE")
    with pytest.raises(FileExistsError):
        export_aligned(a, b, output)
    assert output.read_bytes() == b"DO NOT REPLACE"
    with pytest.raises(ValueError, match="Cannot overwrite"):
        export_aligned(a, b, a)
    with fitz.open(a) as source:
        source[0].add_text_annot((70, 70), "Do not lose this")
        source.save(tmp_path / "annotated.pdf")
    with pytest.raises(ValueError, match="annotations or links"):
        export_aligned(tmp_path / "annotated.pdf", b, tmp_path / "unsafe.pdf")
    assert not (tmp_path / "unsafe.pdf").exists()
