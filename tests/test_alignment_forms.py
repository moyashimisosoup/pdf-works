"""A/B comparison must display valid form PDFs before export safety checks."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.alignment import inspect_pair, render_pair, export_aligned


def _reference(path):
    with fitz.open() as doc:
        doc.new_page(width=310, height=430).insert_text((20, 35), "REFERENCE")
        doc.save(path)


def _answer_with_widget(path):
    with fitz.open() as doc:
        page = doc.new_page(width=300, height=420)
        page.insert_text((35, 55), "SCANNED ANSWER")
        field = fitz.Widget()
        field.field_name = "answer"
        field.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        field.field_value = "VISIBLE ANSWER"
        field.rect = fitz.Rect(40, 100, 230, 130)
        page.add_widget(field)
        doc.save(path)


def test_form_source_can_be_previewed_and_exported_with_explicit_consent(tmp_path):
    answer, reference, output = (
        tmp_path / "answer.pdf", tmp_path / "reference.pdf",
        tmp_path / "aligned.pdf",
    )
    _answer_with_widget(answer)
    _reference(reference)
    with fitz.open(answer) as original:
        assert original.is_form_pdf
        assert list(original[0].widgets() or ())
    hash_before = hashlib.sha256(answer.read_bytes()).hexdigest()
    details = render_pair(answer, reference)
    assert "widgets" in details["source_issues"]
    assert details["images"]["a"]["width"] > 0
    assert details["images"]["b"]["height"] > 0
    with pytest.raises(ValueError, match="表示内容だけ"):
        export_aligned(answer, reference, output)
    assert not output.exists()

    assert export_aligned(
        answer, reference, output, allow_visual_only=True
    )["pages"] == 1
    with fitz.open(output) as result:
        assert result[0].rect == fitz.Rect(0, 0, 310, 430)
        assert "SCANNED ANSWER" in result[0].get_text("text")
        assert "VISIBLE ANSWER" in result[0].get_text("text")
        assert not list(result[0].widgets() or ())
    assert hashlib.sha256(answer.read_bytes()).hexdigest() == hash_before


def test_attachment_does_not_block_preview_but_requires_consent(tmp_path):
    answer, reference, output = (
        tmp_path / "attachment.pdf", tmp_path / "reference.pdf",
        tmp_path / "aligned.pdf",
    )
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 60), "VISIBLE PAGE")
        doc.embfile_add("note.txt", b"private attachment not for PDF output")
        doc.save(answer)
    _reference(reference)
    details = inspect_pair(answer, reference)
    assert "attachments" in details["source_issues"]
    with pytest.raises(ValueError):
        export_aligned(answer, reference, output)
    assert export_aligned(
        answer, reference, output, allow_visual_only=True
    )["pages"] == 1
    with fitz.open(answer) as original, fitz.open(output) as new:
        assert original.embfile_count() == 1
        assert new.embfile_count() == 0


def test_signature_preview_is_allowed_but_never_exported(tmp_path):
    answer, reference, output = (
        tmp_path / "signed.pdf", tmp_path / "reference.pdf",
        tmp_path / "aligned.pdf",
    )
    with fitz.open() as doc:
        doc.new_page().insert_text((30, 55), "SIGNED")
        doc.xref_set_key(
            doc.pdf_catalog(), "AcroForm",
            "<< /Fields [] /SigFlags 3 >>",
        )
        doc.save(answer)
    _reference(reference)
    assert "signature" in inspect_pair(answer, reference)["source_issues"]
    assert render_pair(answer, reference)["images"]["a"]["width"] > 0
    with pytest.raises(ValueError, match="電子署名"):
        export_aligned(answer, reference, output, allow_visual_only=True)
    assert not output.exists()
