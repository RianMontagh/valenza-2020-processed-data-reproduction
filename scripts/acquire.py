#!/usr/bin/env python3
"""Retrieve the public data archive and extract only allowed raster/mask data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import time
import urllib.parse
import zipfile
import requests
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
LANDING = 'https://datacore.iu.edu/concern/file_sets/9w032428c'
DOWNLOAD = 'https://datacore.iu.edu/downloads/9w032428c'

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()

def status():
    response = requests.get(LANDING, timeout=60)
    response.raise_for_status()
    text = response.text
    m = re.search(r'Archival file status:\s*([^<]+)', text)
    return (m.group(1).strip() if m else 'See download endpoint'), text

def download():
    path = ROOT / 'data/inputs/archive.zip'
    if path.exists() and zipfile.is_zipfile(path):
        return path
    provenance=ROOT/'data/inputs/archive_provenance.json'
    expected=json.loads(provenance.read_text())['sha256'] if provenance.exists() else None
    state, html = status()
    print(state, flush=True)
    if 'Available in archives' in state:
        action = re.search(r'<form action="([^"]*/sda/request/[^"]+)"', html)
        if not action:
            raise RuntimeError('Archive retrieval form missing')
        response = requests.get(urllib.parse.urljoin(LANDING, action.group(1)),
                                params={'file_set_id': '9w032428c'}, timeout=60)
        response.raise_for_status()
        raise RuntimeError('Archive restoration requested; retry later (provider estimates one hour).')
    if 'processing' in state.lower():
        raise RuntimeError('Archive restoration is still processing; no data have been substituted.')
    download_url=DOWNLOAD
    if 'Available for download' in state:
        action=re.search(r'<form action="([^"]*/sda/request/[^"]+)"',html)
        if not action:raise RuntimeError('Restored-file download form missing')
        download_url=urllib.parse.urljoin(LANDING,action.group(1))+'?'+urllib.parse.urlencode({
            'file_set_id':'9w032428c','request':'Download'})
    partial = path.with_suffix('.zip.part')
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {'Range': f'bytes={offset}-'} if offset else {}
    response = requests.get(download_url, headers=headers, stream=True, timeout=(30, 180))
    response.raise_for_status()
    if 'text/html' in response.headers.get('Content-Type', ''):
        raise RuntimeError('Provider returned an HTML status page, not the data archive.')
    if response.status_code != 206:
        offset = 0
    print('Archive response:',response.status_code,'content length',response.headers.get('Content-Length','unknown'),flush=True)
    count = offset
    last = time.monotonic()
    with partial.open('ab' if offset else 'wb') as f:
        for block in response.iter_content(8 * 1024**2):
            f.write(block); count += len(block)
            if time.monotonic() - last > 30:
                print(f'Downloaded {count / 1024**3:.2f} GiB', flush=True)
                last = time.monotonic()
    if not zipfile.is_zipfile(partial):
        raise RuntimeError('Downloaded object is not a readable ZIP archive')
    partial.rename(path)
    record = {'landing_url': LANDING, 'download_url': download_url,
              'bytes': path.stat().st_size, 'sha256': sha256(path)}
    if expected and record['sha256']!=expected:
        raise RuntimeError('Downloaded archive differs from the frozen input SHA-256; review before refreshing inputs.')
    (ROOT / 'data/inputs/archive_provenance.json').write_text(json.dumps(record, indent=2) + '\n')
    return path

def extract(path):
    target = ROOT / 'data/inputs/extracted'
    target.mkdir(parents=True, exist_ok=True)
    inventory = []
    inventory_path=ROOT/'data/inputs/archive_inventory.csv'
    frozen={r['archive_path']:r['sha256'] for r in csv.DictReader(inventory_path.open())} if inventory_path.exists() else {}
    with zipfile.ZipFile(path) as archive:
        def member(entry):
            p = PurePosixPath(entry.filename)
            allowed = ((p.suffix.lower() in {'.tif', '.tiff'} and
                        p.name.lower().startswith(('tc_', 'roi_'))) or
                       (p.suffix.lower() == '.mat' and p.name.lower().startswith('roi')))
            allowed = allowed and '__MACOSX' not in p.parts and not p.name.startswith('._')
            if entry.is_dir():
                return None
            record = {'archive_path': entry.filename, 'bytes': entry.file_size,
                      'crc32': f'{entry.CRC:08x}', 'extracted': allowed, 'sha256': ''}
            if allowed:
                if p.is_absolute() or '..' in p.parts:
                    raise RuntimeError('Unsafe archive path')
                out = target.joinpath(*p.parts)
                out.parent.mkdir(parents=True, exist_ok=True)
                if not out.exists() or out.stat().st_size != entry.file_size:
                    with archive.open(entry) as src, out.open('wb') as dst:
                        shutil.copyfileobj(src, dst, length=8 * 1024**2)
                record['sha256'] = sha256(out)
                if frozen.get(entry.filename) and record['sha256']!=frozen[entry.filename]:
                    raise RuntimeError('Extracted input hash mismatch: '+entry.filename)
                print('Data:', entry.filename, entry.file_size, flush=True)
            return record
        with ThreadPoolExecutor(max_workers=4) as workers:
            inventory=[r for r in workers.map(member,archive.infolist()) if r is not None]
    with (ROOT / 'data/inputs/archive_inventory.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['archive_path','bytes','crc32','extracted','sha256'])
        w.writeheader(); w.writerows(inventory)
    print('Extracted', sum(r['extracted'] for r in inventory), 'data files; code/output files excluded.')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--extract-only', action='store_true')
    args = ap.parse_args()
    if args.status:
        print(status()[0])
    else:
        extract(ROOT / 'data/inputs/archive.zip' if args.extract_only else download())
