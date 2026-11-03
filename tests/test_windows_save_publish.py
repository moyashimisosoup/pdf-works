"""Minimal regression for saving to volumes without hard links."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from types import SimpleNamespace

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core import file_commit
from pdf_works.core.export import save_edited_pdf


def test_windows_rename_path_without_hard_link(monkeypatch, tmp_path):
    temporary = tmp_path / ".temporary.pdf"
    output = tmp_path / "saved.pdf"
    temporary.write_bytes(b"PDF SAVE")
    # Emulate Windows branch on Linux and prove the function never uses os.link.
    monkeypatch.setattr(
        file_commit, "os",
        SimpleNamespace(
            name="nt",
            rename=os.rename,
            link=lambda *args: pytest.fail("hard link should not be used"),
        ),
    )
    file_commit.publish_new_file(temporary, output)
    assert output.read_bytes() == b"PDF SAVE"
    assert not temporary.exists()


def test_windows_destination_not_overwritten(monkeypatch, tmp_path):
    temporary = tmp_path / ".temporary.pdf"
    output = tmp_path / "saved.pdf"
    temporary.write_bytes(b"NEW")
    output.write_bytes(b"ORIGINAL")
    monkeypatch.setattr(
        file_commit, "os",
        SimpleNamespace(name="nt", rename=os.rename, link=os.link),
    )
    with pytest.raises(FileExistsError):
        file_commit.publish_new_file(temporary, output)
    assert output.read_bytes() == b"ORIGINAL"
    assert temporary.read_bytes() == b"NEW"


def test_unedited_save_as_preserves_pdf_bytes(tmp_path):
    source = tmp_path / "original.pdf"
    dest = tmp_path / "new.pdf"
    with fitz.open() as pdf:
        for i in range(3):
            pdf.new_page().insert_text((40, 70), f"Page {i+1}")
        pdf.save(source)
    original = source.read_bytes()
    assert save_edited_pdf(source, dest, [(0, 0), (1, 0), (2, 0)]) == 3
    assert dest.read_bytes() == original
    assert source.read_bytes() == original
