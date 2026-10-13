#!/usr/bin/env python3
"""Audit physical overlaps, then send independently computed union counts to C++."""
import csv
import json
from pathlib import Path
import subprocess
import numpy as np
import rasterio

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/results'
def write(path,rows,fields=None):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)

def union(paths,output=None):
    """Exact union on the supplied aligned metric grids, without resampling."""
    tiles=[];crs=None;resolution=None;origin=None
    for path in paths:
        with rasterio.open(path) as ds:
            t=ds.transform
            if t.b or t.d or t.a<=0 or t.e>=0:raise ValueError('Unsupported rotated grid')
            if crs is not None and (ds.crs!=crs or (t.a,t.e)!=resolution):
                raise ValueError('Multipart grids require a separately justified resampling policy')
            crs=ds.crs;resolution=(t.a,t.e)
            if origin is None:origin=(t.c,t.f)
            x,y=(t.c-origin[0])/t.a,(t.f-origin[1])/t.e
            if abs(x-round(x))>1e-6 or abs(y-round(y))>1e-6:raise ValueError('Unaligned pixel origin')
            tiles.append((round(x),round(y),ds.read(1)))
            profile=ds.profile.copy()
    if not tiles:return 0,0,0
    x0=min(t[0] for t in tiles);y0=min(t[1] for t in tiles)
    nx=max(x+a.shape[1] for x,y,a in tiles)-x0;ny=max(y+a.shape[0] for x,y,a in tiles)-y0
    covered=np.zeros((ny,nx),dtype=np.uint16);total=0
    for x,y,a in tiles:
        total+=int(np.count_nonzero(a))
        view=covered[y-y0:y-y0+a.shape[0],x-x0:x-x0+a.shape[1]]
        np.maximum(view,a,out=view)
    unique=int(np.count_nonzero(covered))
    if output is not None:
        output.parent.mkdir(parents=True,exist_ok=True)
        profile.update(count=1,dtype='uint16',nodata=None,width=nx,height=ny,
                       transform=rasterio.Affine(resolution[0],0,origin[0]+x0*resolution[0],0,resolution[1],origin[1]+y0*resolution[1]),compress='deflate')
        with rasterio.open(output,'w',**profile) as ds:ds.write(covered,1)
    return unique,total,total-unique

def main():
    jobs=json.loads((ROOT/'config/jobs.json').read_text())
    primary=[j for j in jobs if j['scenario']=='primary']
    bindings={b['job_id']:b for b in json.loads((ROOT/'config/data_bindings.json').read_text())}
    parts=[];overlaps=[]
    for j in jobs:
        for r in csv.DictReader((ROOT/j['output']/'areas.csv').open()):parts.append(dict(job_id=j['job_id'],site_id=j['site_id'],scenario=j['scenario'],**r))
    write(OUT/'part_counts.csv',parts)
    for scenario in ['primary','onset28']:
        current=primary if scenario=='primary' else [j for j in primary if j['job_id']!='B14_b']+[j for j in jobs if j['scenario']=='onset28']
        records=[];summed=[]
        for site in sorted({j['site_id'] for j in current}):
            group=[j for j in current if j['site_id']==site]
            for sig in ['B','W']:
                r={'site_id':site,'signature':sig};s=dict(r);complete=True
                for role in ['avulsion','parent']:
                    paths=[ROOT/j['output']/(role+'_'+sig+'.tif') for j in group if role+'_'+sig in bindings[j['job_id']]['masks']]
                    if not paths:complete=False
                    mosaic=ROOT/'data/derived/events'/site/(role+'_'+sig+'.tif') if scenario=='primary' else None
                    unique,total,duplicate=union(paths,mosaic)
                    r[role+'_pixels']=unique;s[role+'_pixels']=total
                    overlaps.append(dict(scenario=scenario,site_id=site,signature=sig,role=role,
                        image_parts=len(paths),summed_pixels=total,union_pixels=unique,duplicate_pixels=duplicate))
                r['complete']=s['complete']=int(complete);records.append(r);summed.append(s)
        folder=OUT if scenario=='primary' else OUT/'sensitivity'/scenario
        folder.mkdir(parents=True,exist_ok=True)
        write(folder/'union_counts.csv',records)
        subprocess.run([str(ROOT/'build/fingerprint'),'summarize',str(folder/'union_counts.csv'),str(folder)],cwd=ROOT,check=True)
        sumfolder=OUT/'sensitivity'/('summed_parts' if scenario=='primary' else 'summed_parts_onset28')
        sumfolder.mkdir(parents=True,exist_ok=True);write(sumfolder/'counts.csv',summed)
        subprocess.run([str(ROOT/'build/fingerprint'),'summarize',str(sumfolder/'counts.csv'),str(sumfolder)],cwd=ROOT,check=True)
    write(OUT/'overlap_audit.csv',overlaps)
    # Geometry is created separately from explicitly documented visual observations.
    geometry={r['site_id']:r for r in csv.DictReader((OUT/'independent_geometry.csv').open())} if (OUT/'independent_geometry.csv').exists() else {}
    join=[]
    for r in csv.DictReader((OUT/'style_ratios.csv').open()):
        g=geometry.get(r['site_id'],{})
        join.append(dict(site_id=r['site_id'],style_ratio=r['style_ratio'],**{k:g.get(k,'NA') for k in ['width_m','distance_m','slope','morphology']}))
    write(OUT/'geometry_join.csv',join)
    subprocess.run([str(ROOT/'build/fingerprint'),'statistics',str(OUT/'geometry_join.csv'),str(OUT)],cwd=ROOT,check=True)
    print('Aggregated',len(join),'events, with explicit temporal and overlap sensitivities.')
if __name__=='__main__':main()
