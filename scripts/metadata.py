#!/usr/bin/env python3
"""Retain only the user-authorized interpretation columns, never outcomes."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://datacore.iu.edu/downloads/p5547s576'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
ALLOWED = {'A': 'part_id', 'B': 'latitude_deg', 'C': 'longitude_deg',
           'G': 'years_text', 'H': 'bands_text', 'I': 'onset_index_text'}

def sequence(text):
    values = []
    for term in str(text).strip().split(','):
        term = term.strip()
        if not term:
            continue
        ends = [int(v.strip()) for v in term.split(':')]
        if len(ends) == 1:
            values += ends
        elif len(ends) == 2:
            a, b = ends
            if abs(a - b) > 100:
                raise ValueError('Implausible range: ' + term)
            values += list(range(a, b + (1 if b >= a else -1), 1 if b >= a else -1))
        else:
            raise ValueError('Invalid range: ' + term)
    return values

def main():
    raw = urllib.request.urlopen(URL, timeout=120).read()
    records = []
    with zipfile.ZipFile(io.BytesIO(raw)) as book:
        shared = ET.fromstring(book.read('xl/sharedStrings.xml'))
        root = ET.fromstring(book.read('xl/worksheets/sheet1.xml'))
        for row in root.findall('.//s:row', NS):
            if int(row.attrib['r']) == 1:
                continue
            rec = {'source_row': int(row.attrib['r'])}
            for cell in row.findall('s:c', NS):
                col = re.sub(r'\d+', '', cell.attrib['r'])
                if col not in ALLOWED:
                    continue
                value = cell.find('s:v', NS)
                if value is None:
                    continue
                val = value.text
                if cell.attrib.get('t') == 's':
                    val = ''.join(shared[int(val)].itertext())
                rec[ALLOWED[col]] = val.strip()
            if re.fullmatch(r'[VBHG]\d+(?:_[\da-z]+)*', rec.get('part_id', '')):
                records.append(rec)
    target = ROOT / 'config/interpretation_metadata.json'
    target.write_text(json.dumps(records, indent=2) + '\n')
    sites = [r for r in records if 'latitude_deg' in r and 'longitude_deg' in r]
    if len(sites) != 63:
        raise ValueError(f'Expected 63 site records, found {len(sites)}')
    with (ROOT / 'config/sites.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['site_id', 'latitude_deg', 'longitude_deg'])
        w.writerows((r['part_id'], r['latitude_deg'], r['longitude_deg']) for r in sites)
    (ROOT / 'config/metadata_provenance.json').write_text(json.dumps({
        'url': URL, 'workbook_sha256': hashlib.sha256(raw).hexdigest(),
        'retained_columns': ALLOWED,
        'excluded_columns': ['D', 'E', 'F', 'J', 'K', 'L', 'M', 'N', 'O'],
        'workbook_retained': False,
    }, indent=2) + '\n')
    print(f'Retained {len(records)} interpretation records and {len(sites)} sites.')

if __name__ == '__main__':
    main()
