#!/usr/bin/env python3
"""Bind permitted metadata to data filenames; no author program is an input."""
import json
import re
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    with zipfile.ZipFile(ROOT/'data/inputs/archive.zip') as archive:
        names={Path(n).name:n for n in archive.namelist() if '__MACOSX' not in n}
    records=json.loads((ROOT/'config/interpretation_metadata.json').read_text())
    bindings=[]
    for r in records:
        if 'bands_text' not in r:continue
        part=r['part_id']
        # Distinct events share one deposited image stack in these three cases.
        image=re.sub(r'_[123]$','',part) if part.startswith(('V5_','V12_','G25_')) else part
        site=part.split('_')[0] if re.match(r'^B(?:1|9|10|12|14)_',part) else part
        stacks={s:'data/inputs/extracted/'+names[f'TC_{image}_{s}.tif'] for s in ['B','G','W']}
        masks={}
        for role,prefix,var in [('avulsion','av','BW'),('parent','p','BWc')]:
            match=[n for n in names if re.fullmatch(f'ROI_{prefix}_{re.escape(part)}_[BW]\\.mat',n)]
            if len(match)>1:raise ValueError('Ambiguous mask geometry: '+part)
            if match:
                # Both independently evaluated filters use the same supplied geometry.
                for sig in ['B','W']:
                    masks[role+'_'+sig]={'path':'data/inputs/extracted/'+names[match[0]],'variable':var}
        if not masks:raise ValueError('No masks for '+part)
        for index,onset in enumerate(re.findall(r'\d+',r['onset_index_text'])):
            bindings.append(dict(job_id=part+('_onset'+onset if index else ''),site_id=site,
                source_row=r['source_row'],onset_index=int(onset),stacks=stacks,masks=masks,
                scenario='onset28' if index else 'primary',
                notes='The same supplied ROI geometry is used for both spectral filters; the filename signature does not choose the result.'))
    (ROOT/'config/data_bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    used={Path(v).name for b in bindings for v in b['stacks'].values()}
    used|={Path(v['path']).name for b in bindings for v in b['masks'].values()}
    unused=[n for n in names if n.startswith(('TC_','ROI_')) and n.endswith(('.tif','.mat')) and n not in used]
    (ROOT/'data/results/unused_inputs.json').write_text(json.dumps({'unused_files':unused,
        'reason':'No corresponding permitted time-window metadata. No windows inferred from excluded results.'},indent=2)+'\n')
    print('Bound',len(bindings),'jobs;',len(unused),'unbound image/mask files.')
if __name__=='__main__':main()
