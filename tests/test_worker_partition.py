"""Spawned PDF worker, edited-order grouped splitting and file size reporting."""
from __future__ import annotations

import hashlib
import multiprocessing as mp
from pathlib import Path
import sys

import fitz
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.workers.renderer import run_worker


def test_worker_split_boundaries_and_size(tmp_path):
    src = tmp_path / "original.pdf"
    with fitz.open() as doc:
        for i in range(10):
            page = doc.new_page(width=300, height=400)
            page.insert_text((25, 80), f"PART_TEST_{i+1}")
        doc.save(src)
    original = hashlib.sha256(src.read_bytes()).digest()
    directory = tmp_path / "out"
    directory.mkdir()
    ctx = mp.get_context("spawn")
    incoming, outgoing = ctx.Queue(maxsize=24), ctx.Queue(maxsize=12)
    worker = ctx.Process(target=run_worker, args=(incoming, outgoing))
    worker.start()
    try:
        incoming.put({"id":1,"op":"open","generation":14,"path":str(src)})
        opened = outgoing.get(timeout=20)
        assert opened["status"] == "ok"
        assert opened["file_bytes"] == src.stat().st_size
        edited=[(9,90),(1,0),(8,180),(0,0),(4,0),(2,0)]
        request={
            "id":2, "op":"split_groups", "generation":14,
            "destination_dir":str(directory), "pages":edited,
            "prefix":"demo", "mode":"boundaries","boundaries":[2,5],
        }
        incoming.put(request)
        reply=outgoing.get(timeout=30)
        assert reply["status"]=="ok", reply
        assert reply["count"]==3
        assert [Path(f).name for f in reply["files"]] == [
            "demo_part_001_pages_001-002.pdf",
            "demo_part_002_pages_003-005.pdf",
            "demo_part_003_pages_006-006.pdf",
        ]
        with fitz.open(reply["files"][0]) as result:
            assert [page.get_text().strip() for page in result] == [
                "PART_TEST_10", "PART_TEST_2",
            ]
            assert result[0].rotation == 90
        incoming.put({**request, "id":3})
        error = outgoing.get(timeout=20)
        assert error["status"]=="error"
        assert "already exists" in error["message"]
        another=tmp_path/"fixed"
        another.mkdir()
        incoming.put({
            "id":4,"op":"split_groups","generation":14,
            "destination_dir":str(another),"pages":edited,
            "prefix":"lesson","mode":"fixed","size":2,
        })
        by_size=outgoing.get(timeout=30)
        assert by_size["status"] == "ok", by_size
        assert by_size["count"] == 3
        assert hashlib.sha256(src.read_bytes()).digest() == original
    finally:
        incoming.put({"op":"stop"})
        worker.join(timeout=10)
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=3)
        incoming.close()
        outgoing.close()
    assert worker.exitcode == 0
