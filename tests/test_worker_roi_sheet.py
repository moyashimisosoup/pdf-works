"""Spawned worker ROI contact sheet: A4 two-page result and safe no overwrite."""
import hashlib
import multiprocessing as mp
from pathlib import Path
import sys

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.workers.renderer import run_worker


def test_contact_sheet_through_spawned_worker(tmp_path):
    source = tmp_path / "original.pdf"
    with fitz.open() as doc:
        for number in range(9):
            page = doc.new_page(width=300, height=400)
            page.insert_text((35, 50), f"TEST ORIGINAL {number}")
        doc.save(source)
    original_digest = hashlib.sha256(source.read_bytes()).digest()
    cropped = []
    for number in range(9):
        with fitz.open() as doc:
            page = doc.new_page(width=120, height=80)
            page.insert_text((6, 26), f"ROI_{number}")
            image = tmp_path / f"roi_{number:02d}.png"
            page.get_pixmap().save(image)
            cropped.append(image)
    digests = [hashlib.sha256(p.read_bytes()).digest() for p in cropped]
    destination = tmp_path / "a4-sheet.pdf"
    ctx = mp.get_context("spawn")
    requests, replies = ctx.Queue(maxsize=24), ctx.Queue(maxsize=12)
    process = ctx.Process(target=run_worker, args=(requests, replies))
    process.start()
    try:
        requests.put({"id": 1, "op": "open", "generation": 8, "path": str(source)})
        assert replies.get(timeout=20)["status"] == "ok"
        request = {
            "id": 2, "op": "roi_sheet_export", "generation": 8,
            "files": [str(p) for p in cropped],
            "sources": list(reversed(range(9))),
            "destination": str(destination),
        }
        requests.put(request)
        response = replies.get(timeout=30)
        assert response["status"] == "ok", response
        assert response["count"] == 2
        with fitz.open(destination) as result:
            assert len(result) == 2
            assert "Original page 9" in result[0].get_text()
            assert "Original page 1" in result[1].get_text()
        requests.put({**request, "id": 3})
        collision = replies.get(timeout=20)
        assert collision["status"] == "error"
        assert "already exists" in collision["message"]
        assert hashlib.sha256(source.read_bytes()).digest() == original_digest
        assert digests == [hashlib.sha256(p.read_bytes()).digest() for p in cropped]
    finally:
        requests.put({"op": "stop"})
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)
        requests.close()
        replies.close()
    assert process.exitcode == 0
