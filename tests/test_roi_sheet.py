"""A4 ROI contact sheet: boundary pagination and safety checks."""
from pathlib import Path
import hashlib
import sys
import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.roi_sheet import save_roi_contact_sheet


def fake_images(tmp_path, number):
    paths = []
    for i in range(number):
        with fitz.open() as document:
            page = document.new_page(width=50+(i % 4)*12, height=40+(i % 3)*20)
            page.draw_rect(page.rect, fill=(i % 3 / 3, .15, .4))
            path = tmp_path / f"roi_{i}.png"
            page.get_pixmap().save(path)
            paths.append(path)
    return paths


@pytest.mark.parametrize("count,pages", [(1, 1), (8, 1), (9, 2), (40, 5)])
def test_a4_pagination_and_inputs_unchanged(tmp_path, count, pages):
    files = fake_images(tmp_path, count)
    digests = [hashlib.sha256(p.read_bytes()).digest() for p in files]
    target = tmp_path / "result.pdf"
    assert save_roi_contact_sheet(files, list(reversed(range(count))), target) == pages
    with fitz.open(target) as document:
        assert len(document) == pages
        assert all(abs(p.rect.width-595) < 1 and abs(p.rect.height-842) < 1
                   for p in document)
        assert all(1 <= len(p.get_images()) <= 8 for p in document)
        assert len(document[0].get_images()) == min(count, 8)
        assert "Original page" in document[0].get_text()
    assert digests == [hashlib.sha256(p.read_bytes()).digest() for p in files]
    with pytest.raises(FileExistsError):
        save_roi_contact_sheet(files, list(range(count)), target)


def test_reject_missing_invalid_and_corrupt_files(tmp_path):
    files = fake_images(tmp_path, 1)
    for ids in ([], [-1], [True]):
        with pytest.raises(ValueError):
            save_roi_contact_sheet(files, ids, tmp_path / "out.pdf")
    with pytest.raises(ValueError):
        save_roi_contact_sheet([], [], tmp_path / "out.pdf")
    with pytest.raises(ValueError):
        save_roi_contact_sheet(files, [0], tmp_path / "out.txt")
    corrupt = tmp_path / "invalid.png"
    corrupt.write_text("broken PNG")
    with pytest.raises(ValueError):
        save_roi_contact_sheet([corrupt], [0], tmp_path / "out.pdf")
    assert not (tmp_path / "out.pdf").exists()
