#!/usr/bin/env python3
"""Check real rasters against separately accumulated annual detections."""
import csv
import json
from pathlib import Path
import numpy as np
import rasterio

ROOT=Path(__file__).resolve().parents[1]
def main():
    jobs=json.loads((ROOT/'config/jobs.json').read_text());checks=[]
    def check(job,name,value):
        checks.append({'job_id':job,'check':name,'passed':bool(value)})
        if not value:raise AssertionError(job+': '+name)
    for job in jobs:
        jid=job['job_id'];out=ROOT/job['output']
        manifest=dict(line.rstrip('\n').split('\t',1) for line in (ROOT/job['manifest']).open())
        annual=list(csv.DictReader((out/'annual.csv').open()))
        counts={r['role']+'_'+r['signature']:r for r in csv.DictReader((out/'areas.csv').open())}
        for sig in ['B','W']:
            with rasterio.open(out/('annual_'+sig+'.tif')) as ds:
                # Each part is evaluated one annual band at a time to limit memory.
                sums={k:np.zeros((ds.height,ds.width),dtype=np.uint16) for k in ['A','P']}
                valids={k:np.zeros((ds.height,ds.width),dtype=np.uint16) for k in ['A','P']}
                check(jid,sig+'/annual_count',ds.count==len(annual))
                for j,record in enumerate(annual,1):
                    a=ds.read(j);valid=a!=255
                    check(jid,sig+f'/binary_{j}',np.all((a==0)|(a==1)|(a==255)))
                    role=record['role'];sums[role]+=(a==1);valids[role]+=valid
                    check(jid,sig+f'/valid_{j}',np.count_nonzero(valid)==int(record['valid_pixels']))
                    check(jid,sig+f'/count_{j}',np.count_nonzero(a==1)==int(record['bright_pixels' if sig=='B' else 'wet_pixels']))
            for role,flag in [('avulsion','A'),('parent','P')]:
                key=role+'_'+sig
                if manifest[key]=='NONE':continue
                with rasterio.open(manifest[key]) as ds:mask=ds.read(1)==1
                with rasterio.open(out/(key+'.tif')) as ds:actual=ds.read(1)
                with rasterio.open(out/(key+'_valid.tif')) as ds:valid=ds.read(1)
                check(jid,key+'/temporal_sum',np.array_equal(actual,sums[flag]*mask))
                check(jid,key+'/validity_sum',np.array_equal(valid,valids[flag]*mask))
                check(jid,key+'/union_count',np.count_nonzero(actual)==int(counts[key]['fingerprint_pixels']))
                check(jid,key+'/coverage',np.count_nonzero(valid)==int(counts[key]['observed_mask_pixels']))
                check(jid,key+'/bounded',np.all(actual<=valid))
        print('Checked',jid,flush=True)
    (ROOT/'data/results/real_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(f'Passed {len(checks)} real-data checks.')

if __name__=='__main__':main()
