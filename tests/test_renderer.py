"""Render tests use synthetic pages, not private PDF files."""
from pathlib import Path
import sys
import fitz
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pdf_works.workers.renderer import page_metadata,render_region,render_thumbnail

@pytest.fixture
def sample_pdf(tmp_path):
    path=tmp_path/"synthetic.pdf"
    doc=fitz.open()
    for n in range(40):
        page=doc.new_page(width=595,height=842)
        page.insert_text((100,100),str(n+1),fontsize=24)
    doc.save(path)
    doc.close()
    return path

def test_metadata_40_pages(sample_pdf):
    with fitz.open(sample_pdf) as doc: sizes=page_metadata(doc)
    assert len(sizes)==40 and sizes[0]==(595.0,842.0)

def test_clip_at_300_percent(sample_pdf):
    with fitz.open(sample_pdf) as doc:
        result=render_region(doc,0,(80,70,240,150),3.0)
    assert result["width"]<=482
    assert result["height"]<=242
    assert len(result["samples"])==result["stride"]*result["height"]

def test_thumbnail_small(sample_pdf):
    with fitz.open(sample_pdf) as doc: thumb=render_thumbnail(doc,39)
    assert 70<=thumb["width"]<=110 and thumb["height"]<=200

def test_invalid_clip_scale_and_page(sample_pdf):
    with fitz.open(sample_pdf) as doc:
        with pytest.raises(ValueError):
            render_region(doc,0,(10,10,10,10),1.0)
        with pytest.raises(ValueError):
            render_region(doc,0,(0,0,595,842),5.0)
        with pytest.raises(ValueError):
            render_region(doc,40,(0,0,10,10),1.0)
