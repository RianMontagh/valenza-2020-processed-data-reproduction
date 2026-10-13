#!/usr/bin/env python3
"""Hash configuration, generated numerical data, plots and compiled report."""
import csv
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'data/results/artifact_manifest.csv';records=[]
    for folder in ['config','src','scripts','tests','figures','report','data/derived','data/results','data/provenance']:
        for p in sorted((ROOT/folder).rglob('*')):
            if not p.is_file() or p==out or p.suffix in ['.aux','.log','.out','.pyc'] or '__pycache__' in p.parts:continue
            h=hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
            records.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=h.hexdigest()))
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(records)
    print('Hashed',len(records),'artifacts.')
if __name__=='__main__':main()
