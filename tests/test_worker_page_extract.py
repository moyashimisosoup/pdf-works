"""Selected-page PDF extraction/splitting via spawned worker, no original edits."""
import hashlib
import multiprocessing as mp
from pathlib import Path
import sys

import fitz
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.workers.renderer import run_worker


def test_selected_export_and_split_spawned_worker(tmp_path):
    src = tmp_path / "original.pdf"
    with fitz.open() as doc:
        for number in range(8):
            p = doc.new_page(width=180, height=240)
            p.insert_text((15, 38), f"SYNTHETIC_PAGE_{number+1}")
        doc.save(src)
    before = hashlib.sha256(src.read_bytes()).digest()
    directory = tmp_path / "parts"
    directory.mkdir()
    ctx = mp.get_context("spawn")
    requests, replies = ctx.Queue(maxsize=24), ctx.Queue(maxsize=12)
    process = ctx.Process(target=run_worker, args=(requests, replies))
    process.start()
    try:
        requests.put({"op": "open", "generation": 7,
                      "id": 1, "path": str(src)})
        assert replies.get(timeout=20)["status"] == "ok"
        specs = [(7, 90), (2, 0), (5, 180)]
        output = tmp_path / "chosen.pdf"
        requests.put({"id": 2, "op": "extract_selected",
                      "generation": 7, "destination": str(output), "pages": specs})
        reply = replies.get(timeout=25)
        assert reply["status"] == "ok", reply
        assert reply["count"] == 3
        with fitz.open(output) as doc:
            assert len(doc) == 3
            assert [page.rotation for page in doc] == [90, 0, 180]
            assert ["SYNTHETIC_PAGE_8", "SYNTHETIC_PAGE_3", "SYNTHETIC_PAGE_6"] == [
                page.get_text().strip() for page in doc
            ]
        requests.put({"id": 3, "op": "split_selected",
                      "generation": 7, "destination_dir": str(directory),
                      "pages": specs, "prefix": "part"})
        response = replies.get(timeout=35)
        assert response["status"] == "ok", response
        assert response["count"] == 3
        assert [Path(n).name for n in response["files"]] == [
            "part_001_source_008.pdf", "part_002_source_003.pdf",
            "part_003_source_006.pdf",
        ]
        with fitz.open(response["files"][2]) as doc:
            assert len(doc) == 1
            assert doc[0].rotation == 180
            assert "SYNTHETIC_PAGE_6" in doc[0].get_text()
        requests.put({"id": 4, "op": "split_selected",
                      "generation": 7, "destination_dir": str(directory),
                      "pages": specs, "prefix": "part"})
        denied = replies.get(timeout=20)
        assert denied["status"] == "error"
        assert "already exists" in denied["message"]
        assert hashlib.sha256(src.read_bytes()).digest() == before
    finally:
        requests.put({"op": "stop"})
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)
        requests.close()
        replies.close()
    assert process.exitcode == 0
