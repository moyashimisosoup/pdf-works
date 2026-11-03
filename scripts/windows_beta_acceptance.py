"""Prepare and verify a local-only Windows beta acceptance run.

The helper never launches the app, modifies an existing PDF or uploads data.
Manual GUI responsiveness remains a separate acceptance condition.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

import fitz

from generate_test_pdf import build_pdf

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "output" / "beta-acceptance"
SOURCE = "source_40.pdf"
OUTPUT = "optimized.pdf"
REPORT = "verification.json"
POINTER = "latest-run.txt"
CHECKLIST = """# PDF Works beta: Windows hands-on checks

Only use the synthetic `source_40.pdf` in this run directory.
Do not upload private school or personal PDFs or this local report.

- [ ] Open source_40.pdf: 40 pages visible; move between pages and zoom to 300%.
- [ ] Use Ctrl/Shift selection, rotate several pages, Undo, move/delete and Undo.
- [ ] Save a changed copy with another filename and reopen it.
- [ ] Extract selected pages and split by page count / cut-after positions.
- [ ] Select ROI, export PNGs, open gallery, reorder/exclude and create A4 list PDF.
- [ ] Reopen the ORIGINAL source_40.pdf with no unsaved page edits.
- [ ] Click '容量を最適化' and save as optimized.pdf in this run directory.
- [ ] During saving, move the window / switch tasks; verify no freeze.
- [ ] Verify existing filenames cannot be overwritten.
- [ ] Change a page without saving; confirm Optimize is disabled.
- [ ] Check text visibility, font weight and usability at 100%, 125% and 150% DPI.
- [ ] Run: python scripts/windows_beta_acceptance.py verify
- [ ] Record observed errors or freezes in a separate local note (no sensitive data).

The verification.json file checks PDF contents and original SHA-256, NOT
manual GUI operation, responsiveness, or real-world document correctness.
"""


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, content: dict) -> None:
    # Only local metadata files created by this helper are replaced.
    temp = path.with_name(path.name + ".temporary")
    temp.write_text(
        json.dumps(content, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def prepare(runs: Path = RUNS) -> Path:
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = runs / f"run-{stamp}-{uuid.uuid4().hex[:8]}"
    directory.mkdir(exist_ok=False)
    source = directory / SOURCE
    build_pdf(source, 40)
    with fitz.open(source) as doc:
        count = len(doc)
    manifest = {
        "schema": 1,
        "created_utc": _utc(),
        "source_name": SOURCE,
        "source_sha256": _hash(source),
        "source_bytes": source.stat().st_size,
        "source_pages": count,
        "output_name": OUTPUT,
    }
    _write_json(directory / "manifest.json", manifest)
    (directory / "manual-checklist.md").write_text(CHECKLIST, encoding="utf-8")
    # The pointer is a basename, never an absolute user path.
    (runs / POINTER).write_text(directory.name + "\n", encoding="utf-8")
    return directory


def _latest_run(runs: Path) -> Path:
    name = (runs / POINTER).read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"run-\d{8}T\d{6}Z-[0-9a-f]{8}", name):
        raise ValueError("Invalid latest-run pointer")
    candidate = runs / name
    if not candidate.is_dir():
        raise FileNotFoundError("Acceptance run directory not found")
    return candidate


def _inspect(source: Path, output: Path) -> dict:
    with fitz.open(source) as original, fitz.open(output) as result:
        if original.needs_pass or result.needs_pass:
            return {"status": "fail", "reason": "password_protected"}
        if len(original) != len(result):
            return {"status": "fail", "reason": "page_count"}
        if original.get_toc() != result.get_toc():
            return {"status": "fail", "reason": "bookmarks"}
        # This synthetic PDF has only text, but compare ALL its page text.
        for i in range(len(original)):
            left, right = original[i], result[i]
            if (
                left.rect != right.rect
                or left.rotation != right.rotation
                or left.get_text("text") != right.get_text("text")
            ):
                return {"status": "fail", "reason": f"page_structure_{i + 1}"}
        # Pixel-fidelity spot checks complement full document text checks.
        for i in sorted({0, len(original) // 2, len(original) - 1}):
            a = original[i].get_pixmap(matrix=fitz.Matrix(0.6, 0.6), alpha=False)
            b = result[i].get_pixmap(matrix=fitz.Matrix(0.6, 0.6), alpha=False)
            if (a.width, a.height, a.samples) != (b.width, b.height, b.samples):
                return {"status": "fail", "reason": f"render_{i + 1}"}
        return {"status": "pass", "pages": len(original), "rendered_pages": [1, 21, 40]}


def verify(directory: Path) -> dict:
    """Verify only this helper's synthetic source and its separate result PDF."""
    directory = directory.resolve(strict=True)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or manifest.get("source_name") != SOURCE:
        raise ValueError("Invalid acceptance manifest")
    source = directory / SOURCE
    output = directory / OUTPUT
    report = {
        "schema": 1,
        "checked_utc": _utc(),
        "manual_gui_acceptance": "not_verified_by_script",
        "source_name": SOURCE,
        "output_name": OUTPUT,
    }
    if not source.is_file():
        report["source"] = {"status": "fail", "reason": "missing"}
        report["overall"] = "fail"
    elif _hash(source) != manifest["source_sha256"]:
        report["source"] = {"status": "fail", "reason": "sha256_changed"}
        report["overall"] = "fail"
    elif source.stat().st_size != manifest["source_bytes"]:
        report["source"] = {"status": "fail", "reason": "size_changed"}
        report["overall"] = "fail"
    else:
        report["source"] = {
            "status": "pass",
            "bytes": source.stat().st_size,
            "sha256": manifest["source_sha256"],
        }
        if not output.exists():
            report["optimized"] = {"status": "pending", "reason": "not_saved_yet"}
            report["overall"] = "incomplete"
        elif not output.is_file():
            report["optimized"] = {"status": "fail", "reason": "not_a_file"}
            report["overall"] = "fail"
        else:
            try:
                result = _inspect(source, output)
            except Exception as error:
                result = {"status": "fail", "reason": type(error).__name__}
            result["bytes"] = output.stat().st_size
            result["delta_bytes"] = output.stat().st_size - source.stat().st_size
            report["optimized"] = result
            report["overall"] = "pass" if result["status"] == "pass" else "fail"
    _write_json(directory / REPORT, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("--run-dir", type=Path, help="Use an existing run directory")
    args = parser.parse_args()
    if args.action == "prepare":
        if args.run_dir is not None:
            parser.error("--run-dir is only for verify")
        path = prepare()
        print(f"Prepared: {path}")
        print(f"Open in PDF Works: {path / SOURCE}")
        print(f"Save optimized result as: {path / OUTPUT}")
        print(f"Manual checklist: {path / 'manual-checklist.md'}")
        print("After completing GUI steps run: python scripts/windows_beta_acceptance.py verify")
        return 0
    try:
        folder = args.run_dir or _latest_run(RUNS)
        report = verify(folder)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Cannot verify acceptance run: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"Check: {report['overall']}")
    print(f"Details: {folder / REPORT}")
    print("Manual GUI acceptance is still required.")
    return 0 if report["overall"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
