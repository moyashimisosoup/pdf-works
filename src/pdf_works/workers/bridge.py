"""Non-blocking Qt bridge to a spawned PDF rendering process."""
from __future__ import annotations
import multiprocessing as mp
import queue
from typing import Any
from PySide6.QtCore import QObject,QTimer,Signal
from .renderer import run_worker

class PdfBridge(QObject):
    result_ready=Signal(dict)
    worker_failed=Signal(str)

    def __init__(self,parent: QObject|None=None):
        super().__init__(parent)
        self._ctx=mp.get_context("spawn")
        self._requests:Any=self._ctx.Queue(maxsize=24)
        self._results:Any=self._ctx.Queue(maxsize=12)
        self._process:mp.Process|None=None
        self._counter=0
        self._timer=QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._poll)
        self._health_ticks=0

    def start(self):
        if self._process and self._process.is_alive(): return
        self._process=self._ctx.Process(target=run_worker,args=(self._requests,self._results),daemon=True)
        self._process.start()
        self._timer.start()

    def send(self,operation:str,**arguments:Any)->int|None:
        self._counter+=1
        try:
            self._requests.put_nowait({"id":self._counter,"op":operation,**arguments})
            return self._counter
        except queue.Full:
            return None

    def _poll(self):
        for _ in range(4):
            try: response=self._results.get_nowait()
            except queue.Empty: break
            self.result_ready.emit(response)
        self._health_ticks+=1
        if self._health_ticks%34==0 and self._process is not None and not self._process.is_alive():
            self._timer.stop()
            self.worker_failed.emit(f"PDF描画プロセスが終了しました（終了コード: {self._process.exitcode}）")

    def close(self):
        self._timer.stop()
        if self._process is not None:
            if self._process.is_alive():
                try: self._requests.put_nowait({"op":"stop"})
                except queue.Full: pass
                self._process.join(timeout=0.25)
                if self._process.is_alive():
                    self._process.terminate()
                    self._process.join(timeout=0.75)
            self._process=None
        self._requests.close()
        self._results.close()
