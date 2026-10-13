#!/usr/bin/env python3
"""Save explicit TCT input visualizations; never mislabel these as RGB photos."""
import csv
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window

ROOT=Path(__file__).resolve().parents[1]
def main():
    jobs={j['job_id']:j for j in json.loads((ROOT/'config/jobs.json').read_text())}
    config=json.loads((ROOT/'config/figure_views.json').read_text())
    output=ROOT/'data/results/context';output.mkdir(exist_ok=True)
    records=[]
    for entry in config.get('context',[]):
        job=jobs[entry['job_id']]
        manifest=dict(line.rstrip('\n').split('\t',1) for line in (ROOT/job['manifest']).open())
        annual=list(csv.DictReader((ROOT/job['output']/'annual.csv').open()))
        match=[r for r in annual if r['year']==str(entry['year'])]
        # Native band may be specified only when supported by saved interpretation metadata.
        if not match:
            records.append(dict(entry,status='missing resolved calendar band'));continue
        band=int(match[0]['band'])
        arrays=[]
        for key in ['B','G','W']:
            with rasterio.open(manifest[key]) as ds:
                win=Window(*entry['window']) if entry.get('window') else Window(0,0,ds.width,ds.height)
                factor=max(1,win.width/1200,win.height/1200)
                a=ds.read(band,window=win,out_shape=(int(win.height/factor),int(win.width/factor)),
                          masked=True,resampling=Resampling.nearest).astype('float32').filled(np.nan)
                bounds=rasterio.windows.bounds(win,ds.transform);crs=str(ds.crs)
            arrays.append(a)
        np.savez_compressed(output/(entry['name']+'.npz'),tct=np.stack(arrays),
                            bounds=np.array(bounds),crs=crs,year=entry['year'],native_band=band)
        records.append(dict(entry,status='saved',native_band=band,display='TCT B/G/W false color'))
    (output/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Saved',sum(r['status']=='saved' for r in records),'TCT context views.')
if __name__=='__main__':main()
