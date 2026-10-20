"""Artificial PDF tests for fixed-size and cut-position multi-page groups."""
from pathlib import Path
import hashlib
import sys

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pdf_works.core.page_partition as module
from pdf_works.core.page_partition import (
    export_partitioned_pdf, partition_page_specs, safe_output_prefix
)


def make_pdf(tmp_path, total=10):
    path = tmp_path / "original.pdf"
    with fitz.open() as doc:
        for i in range(total):
            page = doc.new_page(width=300, height=420)
            page.insert_text((20, 45), f"POSITION_{i+1}")
        doc.save(path)
    return path


def test_fixed_size_1_3_and_overfull():
    page_specs = [(i, 0) for i in range(10)]
    assert [len(p) for p in partition_page_specs(page_specs, "fixed", size=3)] == [3, 3, 3, 1]
    assert [len(p) for p in partition_page_specs(page_specs, "fixed", size=1)] == [1] * 10
    assert [len(p) for p in partition_page_specs(page_specs, "fixed", size=99)] == [10]


def test_boundaries_are_positions_not_original_page_numbers():
    pages = [(7, 90), (3, 0), (8, 180), (1, 0), (5, 0)]
    groups = partition_page_specs(pages, "boundaries", boundaries=[2, 4])
    assert groups == [pages[:2], pages[2:4], pages[4:]]


@pytest.mark.parametrize("mode,kwargs", [
    ("fixed", {"size": 0}), ("fixed", {"size": True}),
    ("fixed", {"size": -2}), ("fixed", {"size": 2.5}),
    ("fixed", {"size": 2, "boundaries": [3]}),
    ("boundaries", {"boundaries": []}),
    ("boundaries", {"boundaries": [0]}),
    ("boundaries", {"boundaries": [5]}),
    ("boundaries", {"boundaries": [2, 2]}),
    ("boundaries", {"boundaries": [4, 1]}),
    ("boundaries", {"boundaries": [True]}),
    ("wrong", {}),
])
def test_invalid_split_configuration(mode, kwargs):
    with pytest.raises(ValueError):
        partition_page_specs([(i, 0) for i in range(5)], mode, **kwargs)


def test_nontrivial_edit_order_output_and_no_overwrite(tmp_path):
    original = make_pdf(tmp_path)
    before = hashlib.sha256(original.read_bytes()).digest()
    output = tmp_path / "sections"
    output.mkdir()
    edited = [(9, 90), (2, 180), (4, 0), (1, 270), (8, 0), (0, 0)]
    parts = export_partitioned_pdf(
        original, output, edited, "lesson", "boundaries", boundaries=[2, 5]
    )
    assert [p.name for p in parts] == [
        "lesson_part_001_pages_001-002.pdf",
        "lesson_part_002_pages_003-005.pdf",
        "lesson_part_003_pages_006-006.pdf",
    ]
    texts = [["POSITION_10", "POSITION_3"], ["POSITION_5", "POSITION_2", "POSITION_9"], ["POSITION_1"]]
    for part, expected in zip(parts, texts):
        with fitz.open(part) as pdf:
            assert len(pdf) == len(expected)
            assert [p.get_text().strip() for p in pdf] == expected
    with fitz.open(parts[0]) as doc:
        assert [p.rotation for p in doc] == [90, 180]
    assert hashlib.sha256(original.read_bytes()).digest() == before
    with pytest.raises(FileExistsError):
        export_partitioned_pdf(original, output, edited, "lesson", "boundaries", boundaries=[2,5])


def test_existing_later_output_blocks_everything(tmp_path):
    original = make_pdf(tmp_path)
    dest = tmp_path / "parts"
    dest.mkdir()
    conflict = dest / "test_part_002_pages_003-004.pdf"
    conflict.write_bytes(b"PROTECTED")
    with pytest.raises(FileExistsError):
        export_partitioned_pdf(original, dest, [(i,0) for i in range(5)],
                               "test", "fixed", size=2)
    assert list(dest.iterdir()) == [conflict]
    assert conflict.read_bytes() == b"PROTECTED"


def test_partial_failure_removes_only_new_files(tmp_path, monkeypatch):
    original = make_pdf(tmp_path)
    dest = tmp_path / "parts"
    dest.mkdir()
    keep = dest / "keep.pdf"
    keep.write_bytes(b"NOT_FOR_DELETION")
    save = module.save_edited_pdf
    calls = []
    def broken(source, target, pages):
        calls.append(str(target))
        if len(calls) == 2:
            raise OSError("simulated disk error")
        return save(source, target, pages)
    monkeypatch.setattr(module, "save_edited_pdf", broken)
    with pytest.raises(OSError, match="simulated"):
        export_partitioned_pdf(original, dest, [(i,0) for i in range(6)],
                               "test", "fixed", size=2)
    assert list(dest.iterdir()) == [keep]
    assert keep.read_bytes() == b"NOT_FOR_DELETION"


def test_limits_and_safe_basename():
    assert safe_output_prefix("CON") == "pdf_CON"
    assert safe_output_prefix("report:2026?") == "report_2026_"
    assert safe_output_prefix("....") == "pdf"
    with pytest.raises(ValueError):
        partition_page_specs([(i, 0) for i in range(501)], "fixed", size=1)
