"""Acceptance helper tests use only fresh artificial files."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from windows_beta_acceptance import prepare, verify
from pdf_works.core.optimize import optimize_pdf_lossless


def test_prepare_creates_isolated_ignored_run(tmp_path):
    runs = tmp_path / "beta-acceptance"
    first = prepare(runs)
    second = prepare(runs)
    assert first != second
    assert first.joinpath("source_40.pdf").is_file()
    assert first.joinpath("manual-checklist.md").is_file()
    assert (runs / "latest-run.txt").read_text(encoding="utf-8").strip() == second.name
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_pages"] == 40
    assert manifest["source_bytes"] > 0
    assert manifest["output_name"] == "optimized.pdf"
    assert not (first / "optimized.pdf").exists()


def test_verify_reports_incomplete_then_true_optimized_result(tmp_path):
    run = prepare(tmp_path / "beta-acceptance")
    pre = verify(run)
    assert pre["overall"] == "incomplete"
    assert pre["manual_gui_acceptance"] == "not_verified_by_script"
    assert pre["optimized"]["status"] == "pending"
    assert (run / "verification.json").is_file()

    optimize_pdf_lossless(run / "source_40.pdf", run / "optimized.pdf")
    post = verify(run)
    assert post["overall"] == "pass"
    assert post["optimized"]["status"] == "pass"
    assert post["optimized"]["pages"] == 40
    assert post["optimized"]["rendered_pages"] == [1, 21, 40]
    assert post["source"]["status"] == "pass"
    assert post["manual_gui_acceptance"] == "not_verified_by_script"
    # Verification never deletes or rewrites the result PDF.
    assert (run / "optimized.pdf").is_file()


def test_verify_detects_original_tampering(tmp_path):
    run = prepare(tmp_path / "beta-acceptance")
    source = run / "source_40.pdf"
    source.write_bytes(b"REPLACED")
    result = verify(run)
    assert result["overall"] == "fail"
    assert result["source"]["reason"] == "sha256_changed"
    assert "optimized" not in result


def test_verify_rejects_corrupt_output_without_deleting(tmp_path):
    run = prepare(tmp_path / "beta-acceptance")
    output = run / "optimized.pdf"
    output.write_bytes(b"not a PDF")
    result = verify(run)
    assert result["overall"] == "fail"
    assert result["optimized"]["status"] == "fail"
    assert output.read_bytes() == b"not a PDF"
