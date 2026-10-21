"""Non-Qt integration test for saving through the spawned worker."""
import multiprocessing as mp
from pathlib import Path
import sys
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pdf_works.workers.renderer import run_worker


def test_worker_export(tmp_path):
    src=tmp_path/'sample.pdf'
    doc=fitz.open()
    for n in range(3):
        p=doc.new_page(width=250,height=350)
        p.insert_text((35,45),f'P{n}')
    doc.save(src)
    doc.close()
    dest=tmp_path/'saved.pdf'
    context=mp.get_context('spawn')
    requests=context.Queue(maxsize=24)
    results=context.Queue(maxsize=12)
    process=context.Process(target=run_worker,args=(requests,results))
    process.start()
    try:
        requests.put({'id':1,'generation':1,'op':'open','path':str(src)})
        assert results.get(timeout=10)['status']=='ok'
        requests.put({'id':2,'generation':1,'op':'export','path':str(src),
                      'destination':str(dest),'pages':[(2,90),(0,0)]})
        result=results.get(timeout=15)
        assert result['status']=='ok', result
        assert result['count']==2
        with fitz.open(dest) as saved:
            assert saved[0].rotation == 90
            assert saved[0].get_text().strip()=='P2'
            assert saved[1].get_text().strip()=='P0'
        requests.put({'id':3,'generation':1,'op':'export','path':str(src),
                      'destination':str(src),'pages':[(0,0)]})
        assert results.get(timeout=15)['status']=='error'
    finally:
        requests.put({'op':'stop'})
        process.join(timeout=8)
        if process.is_alive(): process.terminate()
        requests.close()
        results.close()
    assert process.exitcode==0
