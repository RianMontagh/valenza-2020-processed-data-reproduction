#!/usr/bin/env python3
"""Translate explicit data bindings into portable C++ manifests and mask TIFFs."""
import csv
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import rasterio
from scipy.io import loadmat
from metadata import sequence

ROOT=Path(__file__).resolve().parents[1]
def main():
    metadata={r['source_row']:r for r in json.loads((ROOT/'config/interpretation_metadata.json').read_text())}
    bindings=json.loads((ROOT/'config/data_bindings.json').read_text())
    mask_dir=ROOT/'data/inputs/normalized_masks';mask_dir.mkdir(parents=True,exist_ok=True)
    manifest_dir=ROOT/'config/manifests';manifest_dir.mkdir(exist_ok=True)
    provenance=[];jobs=[];temporal=[]
    audit={int(r['source_row']):r for r in csv.DictReader((ROOT/'data/results/metadata_audit.csv').open())}
    for binding in bindings:
        jid=binding['job_id'];record=metadata[binding['source_row']]
        bands=sequence(record['bands_text'])
        entry=audit[binding['source_row']]
        years=entry['years'].split(';') if entry['years'] else ['unresolved']*len(bands)
        onset=binding['onset_index']
        if onset<1 or onset>=len(bands):raise ValueError('Invalid onset split for '+jid)
        embedded={}
        for component in ['B','G','W']:
            with rasterio.open(ROOT/binding['stacks'][component]) as ds:
                embedded[component]=[]
                for band in bands:
                    text=ds.descriptions[band-1] or ds.tags(band).get('DESCRIPTION','')
                    match=re.search(r'(?:19|20)\d{2}',text)
                    embedded[component].append(match.group() if match else '')
        rows=[]
        for i,(band,year) in enumerate(zip(bands,years)):
            labels={embedded[c][i] for c in ['B','G','W'] if embedded[c][i]}
            if len(labels)>1:raise ValueError('Component year labels disagree: '+jid)
            image_year=next(iter(labels)) if labels else 'unresolved'
            used_year=image_year if labels else year
            temporal.append({'job_id':jid,'native_band':band,'metadata_year':year,
                             'image_year':image_year,'used_label':used_year,
                             'role':'A' if i<onset else 'P',
                             'disagreement':year!='unresolved' and image_year!='unresolved' and year!=image_year})
            rows.append((band,used_year,'A' if i<onset else 'P'))
        if 'year_labels' in binding:
            rows=[(b,str(binding['year_labels'].get(str(b),y)),r) for b,y,r in rows]
        lp=manifest_dir/(jid+'_layers.csv')
        with lp.open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['band','year','role']);w.writerows(rows)
        stacks={k:str(ROOT/v) for k,v in binding['stacks'].items()}
        with rasterio.open(stacks['B']) as ds:
            profile=ds.profile.copy();shape=(ds.height,ds.width)
            if max(bands)>ds.count:raise ValueError('Band selection exceeds stack: '+jid)
            profile.update(driver='GTiff',count=1,dtype='uint8',nodata=None,compress='deflate')
        config={k:binding['stacks'][k] for k in ['B','G','W']}
        config['layers']=str(lp.relative_to(ROOT))
        for role in ['avulsion_B','parent_B','avulsion_W','parent_W']:
            source=binding.get('masks',{}).get(role)
            if source is None:
                config[role]='NONE';continue
            path=ROOT/source['path']
            if path.suffix.lower()=='.mat':
                variable=source['variable']
                data=loadmat(path,variable_names=[variable])[variable]
            else:
                with rasterio.open(path) as ds:data=ds.read(1)
            if source.get('transpose',False):data=data.T
            if data.shape!=shape:raise ValueError(f'Mask {path} shape {data.shape} != {shape}')
            if not np.all((data==0)|(data==1)):raise ValueError('Nonbinary mask: '+str(path))
            out=mask_dir/(jid+'_'+role+'.tif')
            with rasterio.open(out,'w',**profile) as ds:ds.write(data.astype('uint8'),1)
            config[role]=str(out.relative_to(ROOT))
            provenance.append({'job_id':jid,'role':role,**source,'shape':list(shape),
                               'mask_pixels':int(np.count_nonzero(data)),
                               'normalized_sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
        mp=manifest_dir/(jid+'.tsv')
        mp.write_text(''.join(k+'\t'+v+'\n' for k,v in config.items()))
        jobs.append({'job_id':jid,'site_id':binding['site_id'],'source_row':binding['source_row'],
                     'manifest':str(mp.relative_to(ROOT)),'output':'data/derived/'+jid,
                     'scenario':binding.get('scenario','primary'),'notes':binding.get('notes','')})
    (ROOT/'config/jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')
    (ROOT/'data/inputs/mask_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    with (ROOT/'data/results/temporal_labels.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(temporal[0]));w.writeheader();w.writerows(temporal)
    print('Prepared',len(jobs),'explicit jobs and',len(provenance),'binary masks.')
if __name__=='__main__':main()
