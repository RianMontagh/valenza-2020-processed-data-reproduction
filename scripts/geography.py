#!/usr/bin/env python3
"""Reacquire the small independent geographic inputs, checking their saved hashes."""
import gzip
import hashlib
import json
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
def main():
    records=json.loads((ROOT/'data/provenance/local_elevation.json').read_text())
    land=json.loads((ROOT/'data/provenance/land.json').read_text())
    records.append(dict(land,path='data/geography/ne_110m_land.geojson'))
    for r in records:
        path=ROOT/r['path']
        if not path.exists():
            response=requests.get(r['url'],timeout=120);response.raise_for_status()
            data=gzip.decompress(response.content) if r['url'].endswith('.gz') else response.content
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Provider input changed: '+r['path'])
        print('Verified',r['path'])
if __name__=='__main__':main()
