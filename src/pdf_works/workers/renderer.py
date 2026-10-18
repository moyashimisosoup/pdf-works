"""PyMuPDF operations run exclusively in a separate spawned process."""
from __future__ import annotations
import math
import queue
from collections import deque
from typing import Any

MAX_PIXELS = 6_000_000
MAX_SCALE = 3.0

def page_metadata(document: Any) -> list[tuple[float,float]]:
    return [(float(p.rect.width),float(p.rect.height)) for p in document]

def render_region(document: Any, page_no: int, clip: tuple[float,float,float,float], scale: float) -> dict:
    import fitz
    if not 0 <= page_no < len(document):
        raise ValueError("Page index out of range")
    if not math.isfinite(scale) or not 0 < scale <= MAX_SCALE:
        raise ValueError("Invalid image scale")
    page = document[page_no]
    box = fitz.Rect(*clip) & page.rect
    if box.is_empty or box.width < 0.5 or box.height < 0.5:
        raise ValueError("Empty visible region")
    if math.ceil(box.width*scale)*math.ceil(box.height*scale) > MAX_PIXELS:
        raise ValueError("Visible region exceeds image budget")
    pix = page.get_pixmap(matrix=fitz.Matrix(scale,scale),clip=box,alpha=False,colorspace=fitz.csRGB)
    if pix.n != 3 or pix.alpha:
        raise RuntimeError("Unexpected pixmap format")
    return {"width":pix.width,"height":pix.height,"stride":pix.stride,
            "samples":bytes(pix.samples),"x":pix.x/scale,"y":pix.y/scale,"scale":scale}

def render_thumbnail(document: Any, page_no: int, target_width: int=104) -> dict:
    if not 0 <= page_no < len(document):
        raise ValueError("Page index out of range")
    if not 40 <= target_width <= 200:
        raise ValueError("Thumbnail width out of range")
    page = document[page_no]
    scale=min(MAX_SCALE,target_width/max(page.rect.width,1.0))
    return render_region(document,page_no,tuple(page.rect),scale)

def run_worker(requests: Any, results: Any) -> None:
    """Communicate via dictionaries and bounded image bytes; no Qt objects."""
    import fitz
    document=None
    generation=-1
    original_rotations=[]
    deferred=deque()
    while True:
        try:
            req=deferred.popleft() if deferred else requests.get()
        except (EOFError,OSError):
            break
        op=req.get("op")
        if op=="render":
            # Drop obsolete viewport requests, never leapfrog open/stop commands.
            while True:
                try: later=requests.get_nowait()
                except queue.Empty: break
                if later.get("op") in ("open","stop"):
                    deferred.append(later)
                    break
                if later.get("op")=="render" and later.get("generation")==req.get("generation"):
                    req=later
                else:
                    deferred.append(later)
        op=req.get("op")
        if op=="stop":
            break
        response={"id":req.get("id"),"op":op,"generation":req.get("generation"),
                  "slot":req.get("slot"),"epoch":req.get("epoch")}
        try:
            if op=="open":
                if document is not None:
                    document.close()
                    document=None
                generation=req["generation"]
                document=fitz.open(req["path"])
                if document.needs_pass:
                    document.close()
                    document=None
                    raise ValueError("パスワード保護されたPDFはalpha版では未対応です")
                if not document.is_pdf:
                    raise ValueError("PDFを選択してください")
                original_rotations=[p.rotation for p in document]
                response.update(status="ok",sizes=page_metadata(document),count=len(document))
            elif op in ("render","thumb"):
                if document is None or req.get("generation")!=generation:
                    continue
                page_no=req["page"]
                delta=req.get("rotation",0)
                if delta not in (0,90,180,270):
                    raise ValueError("Invalid page rotation")
                document[page_no].set_rotation((original_rotations[page_no]+delta)%360)
                image=(render_region(document,page_no,tuple(req["clip"]),float(req["scale"]))
                       if op=="render" else render_thumbnail(document,page_no))
                response.update(status="ok",page=page_no,image=image)
            elif op=="export":
                if document is None or req.get("generation")!=generation:
                    raise RuntimeError("PDF document is not open")
                from ..core.export import save_edited_pdf
                count=save_edited_pdf(req["path"],req["destination"],req["pages"])
                response.update(status="ok",count=count,destination=req["destination"])
            elif op=="roi_export":
                if document is None or req.get("generation")!=generation:
                    raise RuntimeError("PDF document is not open")
                from ..core.crop import NormalizedROI, export_region_pngs
                # Read only the already-opened source file, never an untrusted
                # path supplied by the exporting caller.
                source_path = document.name
                roi=NormalizedROI(*req["roi"])
                paths=export_region_pngs(source_path,req["destination_dir"],
                                          roi,req["pages"],dpi=req.get("dpi",200))
                response.update(status="ok",count=len(paths),
                                files=[str(path) for path in paths])
            else:
                raise ValueError(f"Unknown operation {op!r}")
        except Exception as exc:
            response.update(status="error",message=str(exc))
        try: results.put(response,timeout=1.0)
        except (queue.Full,ValueError,OSError): pass
    if document is not None:
        document.close()
