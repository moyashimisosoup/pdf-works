"""Spawned optimize IPC keeps the original PDF unchanged."""
from __future__ import annotations

import hashlib
import multiprocessing as mp
from pathlib import Path
import sys
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.workers.renderer import run_worker


def test_worker_optimizes_without_overwriting_source(tmp_path):
    source = tmp_path / "synthetic.pdf"
    with fitz.open() as doc:
        for page_no in range(8):
            page = doc.new_page(width=300, height=410)
            page.insert_text((24, 57), f"TEXT_{page_no+1}")
        doc.save(source)
    expected_sha = hashlib.sha256(source.read_bytes()).digest()
    out = tmp_path / "optimized.pdf"
    ctx = mp.get_context("spawn")
    requests, results = ctx.Queue(maxsize=24), ctx.Queue(maxsize=12)
    proc = ctx.Process(target=run_worker, args=(requests, results))
    proc.start()
    try:
        requests.put({"id":1,"op":"open","path":str(source),"generation":15})
        assert results.get(timeout=20)["status"] == "ok"
        request={"id":2,"op":"optimize_lossless",
                 "generation":15,"destination":str(out)}
        requests.put(request)
        reply=results.get(timeout=30)
        assert reply["status"]=="ok",reply
        assert reply["pages"]==8
        assert reply["before_bytes"]==source.stat().st_size
        assert reply["after_bytes"]==out.stat().st_size
        with fitz.open(out) as doc:
            assert len(doc)==8
            assert "TEXT_8" in doc[-1].get_text()
        requests.put({**request,"id":3})
        error=results.get(timeout=20)
        assert error["status"]=="error"
        assert "already exists" in error["message"]
        assert hashlib.sha256(source.read_bytes()).digest()==expected_sha
    finally:
        requests.put({"op":"stop"})
        proc.join(timeout=10)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=3)
        requests.close()
        results.close()
    assert proc.exitcode == 0
