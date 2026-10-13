#!/usr/bin/env python3
"""Audit band/year metadata without replacing inconsistent labels by guesses."""
import csv
import json
from pathlib import Path
import re
from metadata import sequence

ROOT=Path(__file__).resolve().parents[1]

def audit():
    records=json.loads((ROOT/'config/interpretation_metadata.json').read_text())
    rows=[]
    for r in records:
        if 'bands_text' not in r:
            continue
        bands=sequence(r['bands_text'])
        notes=[]
        try:
            years=sequence(r['years_text'])
            if any(y<1986 or y>2017 for y in years):
                notes.append('Year label outside 1986–2017; label not used to change band selection.')
        except ValueError:
            years=[]
            notes.append('Invalid year range; preserve raw text and use supplied band indices.')
        if len(years)!=len(bands):
            notes.append('Year count differs from band count; calendar labels unresolved.')
        indices=[int(v) for v in re.findall(r'\d+',r['onset_index_text'])]
        if len(indices)>1:
            notes.append('Multiple onset indices; evaluate both as separate timing scenarios.')
        if any(k<1 or k>=len(bands) for k in indices):
            notes.append('Onset split does not leave both parent and avulsion observations.')
        rows.append({'part_id':r['part_id'],'source_row':r['source_row'],
                     'bands':';'.join(map(str,bands)),
                     'years':';'.join(map(str,years)) if len(years)==len(bands) and all(1986<=y<=2017 for y in years) else '',
                     'onset_indices':';'.join(map(str,indices)),
                     'notes':' '.join(notes)})
    with (ROOT/'data/results/metadata_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(f'Audited {len(rows)} image-part records; {sum(bool(r["notes"]) for r in rows)} require notes.')
    return rows

if __name__=='__main__':audit()
