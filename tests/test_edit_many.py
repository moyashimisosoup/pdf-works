"""Batch page edits are one undo step and never mutate original PDFs."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.page_edit import EditSession


def test_noncontiguous_batch_rotation_single_undo():
    session = EditSession(8)
    session.rotate_many([6, 2, 0], 90)
    assert [p.rotation_delta for p in session.pages] == [90, 0, 90, 0, 0, 0, 90, 0]
    assert session.undo()
    assert all(p.rotation_delta == 0 for p in session.pages)
    assert not session.undo()


def test_batch_delete_preserves_order_and_is_atomic():
    session = EditSession(8)
    session.move(7, 0)
    assert [p.source_index for p in session.pages] == [7, 0, 1, 2, 3, 4, 5, 6]
    session.delete_many([1, 3, 5])
    assert [p.source_index for p in session.pages] == [7, 1, 3, 5, 6]
    assert session.undo()
    assert [p.source_index for p in session.pages] == [7, 0, 1, 2, 3, 4, 5, 6]
    assert session.undo()
    assert [p.source_index for p in session.pages] == list(range(8))


def test_reject_all_pages_and_duplicate_without_dirty_history():
    session = EditSession(3)
    before = session.snapshot()
    for selection in ([0, 1, 2], [0, 0], [0, 3], [-1], []):
        with pytest.raises((ValueError, IndexError)):
            session.delete_many(selection)
    assert session.snapshot() == before
    assert not session.can_undo


def test_invalid_rotate_selection_rejected_before_any_edit():
    session = EditSession(3)
    with pytest.raises(ValueError):
        session.rotate_many([0, 1], 15)
    with pytest.raises(IndexError):
        session.rotate_many([0, 9], 90)
    assert not session.can_undo
    session.rotate_many([0, 2], -90)
    assert session.snapshot() == [(0, 270), (1, 0), (2, 270)]
