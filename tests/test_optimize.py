"""Synthetic PDF quality-preserving optimization and safety tests."""
import hashlib
from pathlib import Path
import sys

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.optimize import optimize_pdf_lossless


def synthetic(tmp_path, count=8, *, annotate=False):
    src = tmp_path / "synthetic.pdf"
    with fitz.open() as doc:
        for i in range(count):
            page = doc.new_page(width=300, height=420)
            page.insert_text((25, 54), f"SEARCHABLE_WORD_{i+1} alpha beta")
            page.draw_rect(fitz.Rect(30, 80, 200, 150), fill=(.3,.5,.8))
            if annotate and i == 0:
                note=page.add_text_annot((70,180), "COMMENT 1")
                note.set_info(title="Tester")
                page.insert_link({"kind":fitz.LINK_URI,
                                  "from":fitz.Rect(30,250,110,280),
                                  "uri":"https://example.org/"})
        doc.set_toc([[1, "First", 1]])
        doc.save(src)
    return src


@pytest.mark.parametrize("count", [1, 8, 40])
def test_optimization_keeps_text_geometry_and_source(tmp_path, count):
    src=synthetic(tmp_path,count)
    original_sha=hashlib.sha256(src.read_bytes()).digest()
    out=tmp_path/"optimized.pdf"
    report=optimize_pdf_lossless(src,out)
    assert report["pages"]==count
    assert report["before_bytes"]==src.stat().st_size
    assert report["after_bytes"]==out.stat().st_size
    assert out.is_file()
    assert hashlib.sha256(src.read_bytes()).digest()==original_sha
    with fitz.open(src) as a, fitz.open(out) as b:
        assert a.get_toc()==b.get_toc()
        for pa,pb in zip(a,b):
            assert pa.get_text()==pb.get_text()
            assert pa.rect==pb.rect
            assert pa.rotation==pb.rotation
            assert pa.get_pixmap(matrix=fitz.Matrix(.6,.6)).samples == (
                pb.get_pixmap(matrix=fitz.Matrix(.6,.6)).samples
            )


def test_annotations_links_and_toc_preserved(tmp_path):
    src=synthetic(tmp_path,2,annotate=True)
    out=tmp_path/"optimized.pdf"
    optimize_pdf_lossless(src,out)
    with fitz.open(src) as a, fitz.open(out) as b:
        assert a.get_toc()==b.get_toc()
        assert len(list(a[0].annots()))==len(list(b[0].annots()))==1
        assert next(a[0].annots()).info["content"]=="COMMENT 1"
        assert next(b[0].annots()).info["content"]=="COMMENT 1"
        assert [x["uri"] for x in a[0].get_links()]==[
            x["uri"] for x in b[0].get_links()
        ]


def test_no_overwrite_of_output_or_original(tmp_path):
    src=synthetic(tmp_path,1)
    old=src.read_bytes()
    with pytest.raises((ValueError,FileExistsError)):
        optimize_pdf_lossless(src,src)
    dest=tmp_path/"keep.pdf"
    dest.write_bytes(b"PROTECTED")
    with pytest.raises(FileExistsError):
        optimize_pdf_lossless(src,dest)
    assert dest.read_bytes()==b"PROTECTED"
    assert src.read_bytes()==old


def test_reject_interactive_form(tmp_path):
    src=tmp_path/"form.pdf"
    with fitz.open() as doc:
        p=doc.new_page()
        widget=fitz.Widget()
        widget.field_name="answer"
        widget.field_value="YES"
        widget.field_type=fitz.PDF_WIDGET_TYPE_TEXT
        widget.rect=fitz.Rect(30,50,180,80)
        p.add_widget(widget)
        doc.save(src)
    with pytest.raises(ValueError, match="Form or signed"):
        optimize_pdf_lossless(src,tmp_path/"new.pdf")
    assert not (tmp_path/"new.pdf").exists()


def test_reject_embedded_files(tmp_path):
    src=tmp_path/"embedded.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.embfile_add("payload.txt", b"ARTIFICIAL DATA")
        doc.save(src)
    with pytest.raises(ValueError,match="embedded files"):
        optimize_pdf_lossless(src,tmp_path/"new.pdf")
    assert not (tmp_path/"new.pdf").exists()


def test_no_smaller_file_guarantee(tmp_path):
    src=synthetic(tmp_path,1)
    report=optimize_pdf_lossless(src,tmp_path/"out.pdf")
    assert isinstance(report["after_bytes"]-report["before_bytes"],int)
    # No assertion about a decrease: a lossless save may increase the file size.
