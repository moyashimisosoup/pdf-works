"""Small synthetic checks for vector-preserving page deskew."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.page_edit import EditSession
from pdf_works.core.export import save_edited_pdf


def make_source(path, count=3):
    with fitz.open() as document:
        for index in range(count):
            page = document.new_page(width=300, height=420)
            page.insert_text((40, 80), f"TILT_SEARCHABLE_PAGE_{index + 1}")
            page.draw_line((24, 120), (240, 120))
        document[1].set_rotation(90)
        document.save(path)


def test_fine_angle_input_arrow_ticks_and_undo():
    session = EditSession(3)
    session.set_fine_many([0, 2], 1)
    assert session.fine_snapshot() == [1, 0, 1]
    session.set_fine_many([0], 10)
    session.rotate(0, 90)
    assert session.pages[0].rotation_delta == 90
    assert session.pages[0].fine_tenths == 10
    assert session.undo()
    assert session.fine_snapshot() == [10, 0, 1]
    assert session.undo()
    assert session.fine_snapshot() == [1, 0, 1]
    assert session.undo()
    assert session.fine_snapshot() == [0, 0, 0]
    assert session.snapshot() == [(0, 0), (1, 0), (2, 0)]
    with pytest.raises(ValueError):
        session.set_fine_many([0], 101)


def test_tilt_save_keeps_searchable_text_and_original(tmp_path):
    src, dst = tmp_path / "source.pdf", tmp_path / "fine.pdf"
    make_source(src)
    original_sha = hashlib.sha256(src.read_bytes()).digest()
    result = save_edited_pdf(
        src, dst, [(0, 0), (1, 0), (2, 0)],
        fine_angles=[12, -4, 0],
    )
    assert result == 3
    assert original_sha == hashlib.sha256(src.read_bytes()).digest()
    with fitz.open(src) as before, fitz.open(dst) as after:
        assert [after[i].rotation for i in range(3)] == [0, 0, 0]
        for i in range(3):
            text = f"TILT_SEARCHABLE_PAGE_{i + 1}"
            assert text in after[i].get_text("text")
            assert after[i].search_for(text)
        assert after[1].rect == before[1].rect
        assert after[0].rect == before[0].rect
        # Rotation is visible but text is vector, never a raster image.
        assert not after[0].get_images(full=True)
        assert before[0].get_pixmap().samples != after[0].get_pixmap().samples


def test_mixed_90_degree_and_fine_angle_save(tmp_path):
    src, dst = tmp_path / "mixed.pdf", tmp_path / "saved.pdf"
    make_source(src)
    assert save_edited_pdf(
        src, dst, [(2, 90), (0, 0), (1, 0)],
        fine_angles=[0, -7, 0],
    ) == 3
    with fitz.open(dst) as doc:
        assert [p.get_text().strip() for p in doc] == [
            "TILT_SEARCHABLE_PAGE_3",
            "TILT_SEARCHABLE_PAGE_1",
            "TILT_SEARCHABLE_PAGE_2",
        ]
        assert [p.rotation for p in doc] == [90, 0, 90]


def test_tilt_refuses_annotation_without_any_output(tmp_path):
    src, dst = tmp_path / "annotated.pdf", tmp_path / "saved.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.add_text_annot((40, 70), "Keep this!")
        doc.save(src)
    before = src.read_bytes()
    with pytest.raises(ValueError, match="リンク・注釈・フォーム"):
        save_edited_pdf(src, dst, [(0, 0)], fine_angles=[5])
    assert not dst.exists()
    assert src.read_bytes() == before


def test_tilt_refuses_bad_input_and_preexisting_destination(tmp_path):
    src, dst = tmp_path / "source.pdf", tmp_path / "existing.pdf"
    make_source(src)
    with pytest.raises(ValueError, match="Invalid fine tilt"):
        save_edited_pdf(src, dst, [(0, 0)], fine_angles=[300])
    dst.write_bytes(b"KEEP")
    with pytest.raises(FileExistsError):
        save_edited_pdf(src, dst, [(0, 0)], fine_angles=[1])
    assert dst.read_bytes() == b"KEEP"
