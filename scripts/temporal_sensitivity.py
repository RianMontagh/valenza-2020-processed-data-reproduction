#!/usr/bin/env python3
"""Test alternative parent-channel windows without changing spectral thresholds."""
import csv
import json
from pathlib import Path
import subprocess
import numpy as np
import rasterio
from aggregate import union,write
ROOT=Path(__file__).resolve().parents[1]

def main():
    jobs=[j for j in json.loads((ROOT/'config/jobs.json').read_text()) if j['scenario']=='primary']
    avulsions={(r['site_id'],r['signature']):r for r in csv.DictReader((ROOT/'data/results/signature_ratios.csv').open())}
    for policy in ['concurrent_parent','all_selected_parent']:
        folder=ROOT/'data/derived/sensitivity'/policy;folder.mkdir(parents=True,exist_ok=True)
        available={}
        for job in jobs:
            out=ROOT/job['output'];jid=job['job_id']
            annual=list(csv.DictReader((out/'annual.csv').open()))
            manifest=dict(line.rstrip('\n').split('\t',1) for line in (ROOT/job['manifest']).open())
            for sig in ['B','W']:
                if manifest['parent_'+sig]=='NONE':continue
                with rasterio.open(ROOT/manifest['parent_'+sig]) as ds:mask=ds.read(1)==1
                with rasterio.open(out/('annual_'+sig+'.tif')) as ds:
                    total=np.zeros((ds.height,ds.width),dtype='uint16');profile=ds.profile.copy()
                    for i,row in enumerate(annual,1):
                        if policy=='all_selected_parent' or row['role']=='A':total+=(ds.read(i)==1)&mask
                path=folder/(jid+'_'+sig+'.tif');profile.update(count=1,dtype='uint16',nodata=None,compress='deflate')
                with rasterio.open(path,'w',**profile) as ds:ds.write(total,1)
                available.setdefault((job['site_id'],sig),[]).append(path)
        rows=[]
        for key,av in avulsions.items():
            count,_,_=union(available.get(key,[]))
            rows.append(dict(site_id=key[0],signature=key[1],avulsion_pixels=av['avulsion_pixels'],parent_pixels=count,complete=int(bool(available.get(key)))))
        out=ROOT/'data/results/sensitivity'/policy;out.mkdir(parents=True,exist_ok=True)
        write(out/'counts.csv',rows)
        subprocess.run([str(ROOT/'build/fingerprint'),'summarize',str(out/'counts.csv'),str(out)],cwd=ROOT,check=True)
        print('Calculated',policy,flush=True)
if __name__=='__main__':main()
