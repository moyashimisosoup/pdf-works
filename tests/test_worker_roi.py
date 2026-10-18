"""Spawn-process ROI export IPC: actual worker, artificial PDF only."""
from __future__ import annotations

import hashlib
import multiprocessing as mp
from pathlib import Path
import sys

import fitz
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.workers.renderer import run_worker


def test_worker_roi_export_in_edited_page_order(tmp_path):
    source = tmp_path / "input.pdf"
    out = tmp_path / "out"
    out.mkdir()
    with fitz.open() as document:
        for i in range(3):
            p = document.new_page(width=300, height=400)
            p.insert_text((10, 30), f"ONLY_TEST_{i}")
            p.draw_rect(fitz.Rect(0, 0, 100, 100), fill=(i / 3, .6, .2))
        document.save(source)
    before = hashlib.sha256(source.read_bytes()).digest()
    ctx = mp.get_context("spawn")
    requests = ctx.Queue(maxsize=24)
    replies = ctx.Queue(maxsize=12)
    process = ctx.Process(target=run_worker, args=(requests, replies))
    process.start()
    try:
        requests.put({"id":1, "op":"open", "path":str(source), "generation":42})
        assert replies.get(timeout=15)["status"] == "ok"
        command = {
            "id":2, "op":"roi_export", "generation":42,
            "destination_dir":str(out),
            "roi":(.05,.05,.4,.3), "pages":[(2,90),(0,0)], "dpi":96,
        }
        requests.put(command)
        reply = replies.get(timeout=30)
        assert reply["status"] == "ok", reply
        assert reply["count"] == 2
        assert [Path(f).name for f in reply["files"]] == [
            "roi_001_source_003.png", "roi_002_source_001.png",
        ]
        assert all(Path(f).is_file() for f in reply["files"])
        assert hashlib.sha256(source.read_bytes()).digest() == before
        requests.put({**command, "id":3})
        denied = replies.get(timeout=15)
        assert denied["status"] == "error"
        assert "already exists" in denied["message"]
        assert hashlib.sha256(source.read_bytes()).digest() == before
    finally:
        requests.put({"op":"stop"})
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)
        requests.close()
        replies.close()
    assert process.exitcode == 0
