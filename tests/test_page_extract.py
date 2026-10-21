"""Synthetic PDF tests for extraction selection, split safety and rollback."""
from pathlib import Path
import hashlib
import sys
import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.export import save_edited_pdf
from pdf_works.core.page_edit import EditSession
from pdf_works.core.page_extract import selected_page_specs, split_selected_pdf
import pdf_works.core.page_extract as module


def sample_pdf(tmp_path, count=8):
    src = tmp_path / "input.pdf"
    with fitz.open() as doc:
        for n in range(count):
            page = doc.new_page(width=280, height=400)
            page.insert_text((25, 75), f"SYNTHETIC_PAGE_{n+1}")
        doc.save(src)
    return src


def test_extract_uses_edited_order_and_rotation(tmp_path):
    src = sample_pdf(tmp_path)
    session = EditSession(8)
    session.move(7, 0)
    session.rotate(0, 90)
    chosen = selected_page_specs(session.snapshot(), [0, 2, 4])
    assert chosen == [(7, 90), (1, 0), (3, 0)]
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    target = tmp_path / "selected.pdf"
    assert save_edited_pdf(src, target, chosen) == 3
    with fitz.open(target) as doc:
        assert len(doc) == 3
        assert doc[0].rotation == 90
        assert ["SYNTHETIC_PAGE_8", "SYNTHETIC_PAGE_2", "SYNTHETIC_PAGE_4"] == [
            p.get_text().strip() for p in doc
        ]
    assert hashlib.sha256(src.read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        save_edited_pdf(src, target, chosen)


def test_split_preserves_edited_order_original_and_rotations(tmp_path):
    src = sample_pdf(tmp_path)
    before = hashlib.sha256(src.read_bytes()).digest()
    out = tmp_path / "parts"
    out.mkdir()
    result = split_selected_pdf(src, out, [(6, 180), (2, 0), (0, 90)], "segment")
    assert [x.name for x in result] == [
        "segment_001_source_007.pdf", "segment_002_source_003.pdf",
        "segment_003_source_001.pdf",
    ]
    for p, text, rotate in zip(result, (7, 3, 1), (180, 0, 90)):
        with fitz.open(p) as doc:
            assert len(doc) == 1
            assert doc[0].rotation == rotate
            assert f"SYNTHETIC_PAGE_{text}" in doc[0].get_text()
    assert hashlib.sha256(src.read_bytes()).digest() == before
    with pytest.raises(FileExistsError):
        split_selected_pdf(src, out, [(6,180),(2,0),(0,90)], "segment")
    assert len(list(out.glob("*.pdf"))) == 3


def test_preflight_collision_preserves_existing_and_no_partial(tmp_path):
    src = sample_pdf(tmp_path)
    target = tmp_path / "parts"
    target.mkdir()
    collision = target / "batch_002_source_002.pdf"
    collision.write_bytes(b"UNCHANGED")
    with pytest.raises(FileExistsError):
        split_selected_pdf(src, target, [(0,0),(1,0),(2,0)], "batch")
    assert list(target.iterdir()) == [collision]
    assert collision.read_bytes() == b"UNCHANGED"


def test_selected_page_specs_validation():
    specs = [(8, 0), (3, 90), (7, 0)]
    assert selected_page_specs(specs, [2, 0]) == [(8,0),(7,0)]
    for rows in ([], [-1], [3], [1, 1], [True]):
        with pytest.raises(ValueError):
            selected_page_specs(specs, rows)


def test_split_bad_prefix_and_rollback_on_midstream_failure(tmp_path, monkeypatch):
    src = sample_pdf(tmp_path)
    out = tmp_path / "parts"
    out.mkdir()
    for prefix in ("../bad", "CON/FILE", "bad?", " trailing "):
        with pytest.raises(ValueError):
            split_selected_pdf(src, out, [(0,0)], prefix)
    actual = module.save_edited_pdf
    calls = []
    def fail_second(source, destination, pages):
        calls.append(destination)
        if len(calls) == 2:
            raise RuntimeError("Synthetic simulated write failure")
        return actual(source, destination, pages)
    monkeypatch.setattr(module, "save_edited_pdf", fail_second)
    with pytest.raises(RuntimeError, match="simulated"):
        split_selected_pdf(src, out, [(0,0),(1,0),(2,0)], "batch")
    assert not list(out.glob("*.pdf"))
