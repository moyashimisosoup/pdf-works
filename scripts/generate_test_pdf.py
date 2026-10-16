"""Generate a synthetic PDF without private data."""
import argparse
from pathlib import Path
import fitz

def build_pdf(path:Path,count:int=40):
    doc=fitz.open()
    for i in range(1,count+1):
        page=doc.new_page(width=595,height=842)
        page.insert_text((55,95),f"Sample PDF - page {i}",fontsize=22)
        for line in range(24):
            page.insert_text((55,155+line*22),f"Synthetic line {line+1:02d} / page {i:02d}",fontsize=11)
        page.insert_text((280,795),str(i),fontsize=18)
    path.parent.mkdir(parents=True,exist_ok=True)
    doc.save(path)
    doc.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    p.add_argument("--pages",type=int,default=40)
    a=p.parse_args()
    build_pdf(a.output,a.pages)
    print(f"Generated {a.pages} pages: {a.output}")
