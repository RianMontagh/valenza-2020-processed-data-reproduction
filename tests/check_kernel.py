#!/usr/bin/env python3
"""Independent oracle for GDAL I/O, nodata, strict thresholds and temporal unions.

Fixtures are analytical validation cases; they are never plotted as river data.
"""
import csv
import json
from pathlib import Path
import subprocess
import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.runtime/tests'
WORK.mkdir(parents=True, exist_ok=True)
checks = []

def check(name, condition):
    if not bool(condition):
        raise AssertionError(name)
    checks.append({'check': name, 'passed': True})

def write(path, data, nodata=None, transform=None):
    if data.ndim == 2:
        data = data[None]
    with rasterio.open(path, 'w', driver='GTiff', width=data.shape[2], height=data.shape[1],
                       count=len(data), dtype=data.dtype, crs='EPSG:32619',
                       transform=transform or from_origin(300000, 900000, 30, 30),
                       nodata=nodata) as ds:
        ds.write(data)

def oracle(values, masks, roles):
    common = np.logical_and.reduce([np.isfinite(v) & (v != -9999) for v in values])
    arrays = [np.where(common, v, np.nan) for v in values]
    bright = np.zeros(common.shape, dtype=np.uint8)
    wet = bright.copy()
    for j in range(len(roles)):
        if common[j].any():
            qb,qg,qw = [np.nanquantile(a[j],p,method='linear') for a,p in zip(arrays,[.9,.5,.75])]
            bright[j] = (arrays[0][j] > qb) & (arrays[1][j] < qg)
            wet[j] = (arrays[2][j] > qw) & (arrays[1][j] < qg)
    results = {}
    for signature, detected in [('B',bright),('W',wet)]:
        for role, flag in [('avulsion','A'),('parent','P')]:
            selected = np.array(roles) == flag
            key = role + '_' + signature
            results[key] = (detected[selected].sum(axis=0) * masks[key],
                            common[selected].sum(axis=0) * masks[key])
    bright[~common] = 255; wet[~common] = 255
    return bright, wet, results

def main():
    rng = np.random.default_rng(704)
    for case in ['random','constant','missing','nonoverlap','all_parent_missing']:
        folder=WORK/case;folder.mkdir(exist_ok=True)
        shape=(5,11,13)
        data=[rng.normal(size=shape).astype('float64') for _ in range(3)]
        roles=['A','A','A','P','P']
        if case=='constant':
            data=[np.full(shape,7.,dtype='float64') for _ in range(3)]
        if case=='missing':
            data[0][0,:2]=-9999;data[1][1,:,3]=np.nan;data[2][2,:,7]=-9999
        if case=='all_parent_missing':
            for x in data:x[3:]=-9999
        masks={key:np.ones(shape[1:],dtype='uint8') for key in
               ['avulsion_B','parent_B','avulsion_W','parent_W']}
        for key in masks:
            masks[key][:,0]=0
            if case=='nonoverlap':masks[key][:5 if key.startswith('avulsion') else 8,:]=0
        manifest=[]
        for key,a in zip(['B','G','W'],data):
            path=folder/(key+'.tif');write(path,a,-9999);manifest.append((key,str(path)))
        for key,a in masks.items():
            path=folder/(key+'.tif');write(path,a);manifest.append((key,str(path)))
        layer_path=folder/'layers.csv'
        with layer_path.open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['band','year','role'])
            w.writerows((i+1,2017-i,role) for i,role in enumerate(roles))
        manifest.append(('layers',str(layer_path)))
        mp=folder/'manifest.tsv';mp.write_text(''.join(k+'\t'+v+'\n' for k,v in manifest))
        out=folder/'output'
        subprocess.run([str(ROOT/'build/fingerprint'),str(mp),str(out)],check=True,capture_output=True,text=True)
        bright,wet,results=oracle(data,masks,roles)
        for name,expected in [('annual_B',bright),('annual_W',wet)]:
            with rasterio.open(out/(name+'.tif')) as ds:
                check(case+'/'+name,np.array_equal(ds.read(),expected))
                check(case+'/'+name+'/nodata',ds.nodata==255)
        area_rows={r['role']+'_'+r['signature']:r for r in csv.DictReader((out/'areas.csv').open())}
        for key,(count,valid) in results.items():
            for suffix,expected in [('',count),('_valid',valid)]:
                with rasterio.open(out/(key+suffix+'.tif')) as ds:
                    check(case+'/'+key+suffix,np.array_equal(ds.read(1),expected))
            check(case+'/'+key+'/area',int(area_rows[key]['fingerprint_pixels'])==np.count_nonzero(count))
            check(case+'/'+key+'/area_units',float(area_rows[key]['pixel_area_native'])==900.)
        # A shifted mask must fail, rather than silently intersecting wrong pixels.
        write(folder/'parent_B.tif',masks['parent_B'],transform=from_origin(300030,900000,30,30))
        fail=subprocess.run([str(ROOT/'build/fingerprint'),str(mp),str(out)],capture_output=True,text=True)
        check(case+'/reject_shifted_mask',fail.returncode!=0 and 'grids differ' in fail.stderr)
    (ROOT/'data/results/kernel_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(f'Passed {len(checks)} independent raster-integration checks.')

if __name__=='__main__':main()
