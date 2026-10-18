"""Synthetic PDF regression: visual rotations, cropbox, no overwrite."""
from pathlib import Path
import hashlib
import sys
import fitz
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.crop import NormalizedROI, export_region_pngs


def synthetic_pdf(path, rotations=(0, 90, 180, 270), crop=False):
    with fitz.open() as doc:
        for angle in rotations:
            p = doc.new_page(width=200, height=300)
            regions = [
                (fitz.Rect(0, 0, 100, 150), (1, 0, 0)),
                (fitz.Rect(100, 0, 200, 150), (0, 1, 0)),
                (fitz.Rect(0, 150, 100, 300), (0, 0, 1)),
                (fitz.Rect(100, 150, 200, 300), (1, 1, 0)),
            ]
            for rect, color in regions:
                p.draw_rect(rect, fill=color, color=color)
            if crop:
                p.set_cropbox(fitz.Rect(20, 40, 180, 260))
            p.set_rotation(angle)
        doc.save(path)


def midpoint(png):
    with fitz.open(png) as image:
        pix = image[0].get_pixmap(alpha=False, colorspace=fitz.csRGB)
    at = (pix.height // 2) * pix.stride + (pix.width // 2) * 3
    return bytes(pix.samples[at:at + 3])


@pytest.mark.parametrize("crop", [False, True])
def test_visual_roi_matches_full_render(tmp_path, crop):
    source = tmp_path / "quad.pdf"
    synthetic_pdf(source, crop=crop)
    roi = NormalizedROI(0, 0, .5, .5)
    digest = hashlib.sha256(source.read_bytes()).digest()
    exports = export_region_pngs(source, tmp_path, roi, [(i, 0) for i in range(4)], dpi=72)
    with fitz.open(source) as doc:
        for i, output in enumerate(exports):
            pix = doc[i].get_pixmap(alpha=False, colorspace=fitz.csRGB)
            x, y = pix.width // 4, pix.height // 4
            at = y * pix.stride + x * 3
            assert midpoint(output) == bytes(pix.samples[at:at + 3])
    assert hashlib.sha256(source.read_bytes()).digest() == digest


def test_rotated_page_delta_matches_blue_quadrant(tmp_path):
    source = tmp_path / "quad.pdf"
    synthetic_pdf(source, rotations=(0,))
    result = export_region_pngs(source, tmp_path, NormalizedROI(0, 0, .5, .5),
                                [(0, 90)], dpi=72)
    assert midpoint(result[0]) == bytes([0, 0, 255])


def test_bad_roi_and_file_collision(tmp_path):
    source = tmp_path / "quad.pdf"
    synthetic_pdf(source, rotations=(0,))
    with pytest.raises(ValueError): NormalizedROI(0, 0, 0, 1)
    with pytest.raises(ValueError): NormalizedROI(0, 0, float("nan"), 1)
    dest = tmp_path / "roi_001_source_001.png"
    dest.write_bytes(b"ORIGINAL")
    with pytest.raises(FileExistsError):
        export_region_pngs(source, tmp_path, NormalizedROI(0, 0, 1, 1), [(0, 0)])
    assert dest.read_bytes() == b"ORIGINAL"


def test_pixel_budget_and_invalid_page(tmp_path):
    source = tmp_path / "quad.pdf"
    synthetic_pdf(source, rotations=(0,))
    with pytest.raises(ValueError):
        export_region_pngs(source, tmp_path, NormalizedROI(0, 0, .8, .8),
                           [(0, 0)], dpi=300, max_pixels=10)
    with pytest.raises(IndexError):
        export_region_pngs(source, tmp_path, NormalizedROI(0, 0, .5, .5), [(8, 0)])
    assert not list(tmp_path.glob("roi_*png"))


def test_forty_pages(tmp_path):
    source = tmp_path / "forty.pdf"
    with fitz.open() as doc:
        for index in range(40):
            p = doc.new_page(width=595, height=842)
            p.insert_text((30, 50), f"DEMO_{index}")
            p.set_rotation((index % 4) * 90)
        doc.save(source)
    before = hashlib.sha256(source.read_bytes()).digest()
    output = export_region_pngs(source, tmp_path, NormalizedROI(.05,.04,.45,.25),
                                [(i,0) for i in range(40)], dpi=144)
    assert len(output) == 40
    assert len({p.name for p in output}) == 40
    assert all(p.stat().st_size > 50 for p in output)
    assert hashlib.sha256(source.read_bytes()).digest() == before
