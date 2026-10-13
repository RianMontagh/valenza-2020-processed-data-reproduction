#!/usr/bin/env python3
"""Verify the frozen image/mask input identity and independent geographic data."""
import csv
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
def check(entry):
    path,expected=entry;h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    if h.hexdigest()!=expected:raise ValueError('Input hash mismatch: '+str(path))
    return str(path.relative_to(ROOT))
def main():
    inventory=list(csv.DictReader((ROOT/'data/inputs/archive_inventory.csv').open()))
    entries=[(ROOT/'data/inputs/extracted'/r['archive_path'],r['sha256']) for r in inventory if r['extracted']=='True']
    for r in json.loads((ROOT/'data/provenance/local_elevation.json').read_text()):entries.append((ROOT/r['path'],r['sha256']))
    land=json.loads((ROOT/'data/provenance/land.json').read_text());entries.append((ROOT/'data/geography/ne_110m_land.geojson',land['sha256']))
    with ThreadPoolExecutor(max_workers=4) as pool:verified=list(pool.map(check,entries))
    (ROOT/'data/results/input_verification.json').write_text(json.dumps({'verified_files':len(verified),'all_hashes_match':True},indent=2)+'\n')
    print('Verified',len(verified),'frozen inputs.')
if __name__=='__main__':main()
