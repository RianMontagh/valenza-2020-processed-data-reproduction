#!/usr/bin/env python3
"""Inspect allowed raster and mask formats without reading author programs."""
import json
import re
from pathlib import Path
import rasterio
from scipy.io import whosmat

ROOT=Path(__file__).resolve().parents[1]
def main():
    records=[]
    for path in sorted((ROOT/'data/inputs/extracted').rglob('*')):
        if not path.is_file():continue
        rec={'path':str(path.relative_to(ROOT)),'name':path.name,'bytes':path.stat().st_size}
        if path.suffix.lower() in ['.tif','.tiff']:
            with rasterio.open(path) as ds:
                rec.update(width=ds.width,height=ds.height,bands=ds.count,dtypes=list(ds.dtypes),
                           crs=str(ds.crs),transform=list(ds.transform),nodata=ds.nodata,
                           descriptions=[ds.descriptions[i-1] or ds.tags(i).get('DESCRIPTION') for i in range(1,ds.count+1)],
                           tags=ds.tags())
        elif path.suffix.lower()=='.mat':
            rec['variables']=[{'name':n,'shape':list(s),'type':t} for n,s,t in whosmat(path)]
        records.append(rec)
    (ROOT/'data/inputs/file_inventory.json').write_text(json.dumps(records,indent=2,default=str)+'\n')
    print(f'Inspected {len(records)} allowed data files.')

if __name__=='__main__':main()
