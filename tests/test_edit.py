from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import fitz
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pdf_works.core.page_edit import EditSession
from pdf_works.core.export import save_edited_pdf


def fixture_pdf(tmp_path, count=4):
    src=tmp_path/"source.pdf"
    with fitz.open() as doc:
        for n in range(count):
            page=doc.new_page(width=300,height=400)
            page.insert_text((30,50),f"MARKER_{n:02d}")
        doc[2].set_rotation(90)
        doc.save(src)
    return src


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reorder_rotate_delete_undo(tmp_path):
    model=EditSession(4)
    model.move(3,0)
    model.rotate(0,90)
    model.delete(2)
    assert model.snapshot()==[(3,90),(0,0),(2,0)]
    assert model.undo()
    assert model.snapshot()==[(3,90),(0,0),(1,0),(2,0)]
    assert model.undo()
    assert model.undo()
    assert model.snapshot()==[(0,0),(1,0),(2,0),(3,0)]
    assert not model.undo()


def test_save_preserves_source_and_text(tmp_path):
    src=fixture_pdf(tmp_path)
    before=checksum(src)
    model=EditSession(4)
    model.move(2,0)
    model.rotate(0,90)
    model.delete(2)
    dst=tmp_path/"edited.pdf"
    assert save_edited_pdf(src,dst,model.snapshot())==3
    assert checksum(src)==before
    with fitz.open(dst) as doc:
        assert len(doc)==3
        assert [doc[i].get_text().strip() for i in range(3)]==[
            "MARKER_02", "MARKER_00", "MARKER_03"]
        assert doc[0].rotation == 180


def test_reject_source_overwrite_and_existing_target(tmp_path):
    src=fixture_pdf(tmp_path)
    original=checksum(src)
    with pytest.raises(ValueError,match="source PDF"):
        save_edited_pdf(src,src,[(0,0)])
    dst=tmp_path/"output.pdf"
    dst.write_bytes(b"KEEP ME")
    with pytest.raises(FileExistsError):
        save_edited_pdf(src,dst,[(0,0)])
    assert dst.read_bytes()==b"KEEP ME"
    assert checksum(src)==original


def test_reject_invalid_page_and_empty_document(tmp_path):
    src=fixture_pdf(tmp_path)
    with pytest.raises(ValueError): EditSession(0)
    with pytest.raises(ValueError): EditSession(1).delete(0)
    with pytest.raises(ValueError): save_edited_pdf(src,tmp_path/"x.pdf",[])
    with pytest.raises(ValueError): save_edited_pdf(src,tmp_path/"x.pdf",[(999,0)])
    with pytest.raises(ValueError): save_edited_pdf(src,tmp_path/"x.pdf",[(0,10)])
    with pytest.raises(ValueError): save_edited_pdf(src,tmp_path/"x.pdf",[(0,0),(0,0)])
