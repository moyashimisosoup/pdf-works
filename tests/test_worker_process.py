"""Spawned process test (works without an installed Qt package)."""
import multiprocessing as mp
from pathlib import Path
import sys
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pdf_works.workers.renderer import run_worker

def test_worker_open_render_thumbnail(tmp_path):
    path=tmp_path/"synthetic.pdf"
    doc=fitz.open()
    for i in range(40):
        page=doc.new_page(width=595,height=842)
        page.insert_text((40,40),f"Test {i+1}")
    doc.save(path)
    doc.close()
    ctx=mp.get_context("spawn")
    req=ctx.Queue(maxsize=24)
    res=ctx.Queue(maxsize=12)
    proc=ctx.Process(target=run_worker,args=(req,res))
    proc.start()
    try:
        req.put({"id":1,"op":"open","path":str(path),"generation":1})
        r=res.get(timeout=10)
        assert r["status"]=="ok" and r["count"]==40
        req.put({"id":2,"op":"render","page":0,"clip":(50,50,250,250),"scale":3.0,"generation":1})
        r=res.get(timeout=10)
        assert r["status"]=="ok" and r["op"]=="render"
        assert r["image"]["width"]>0 and r["image"]["height"]>0
        req.put({"id":3,"op":"thumb","page":39,"generation":1})
        r=res.get(timeout=10)
        assert r["status"]=="ok" and r["page"]==39
    finally:
        req.put({"op":"stop"})
        proc.join(timeout=6)
        if proc.is_alive(): proc.terminate()
        req.close()
        res.close()
    assert proc.exitcode==0
