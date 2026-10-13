#!/usr/bin/env python3
"""Known overlapping tiles test exact physical-pixel area accounting."""
import json
from pathlib import Path
import sys
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from aggregate import union
OUT=ROOT/'.runtime/mosaic_test';OUT.mkdir(exist_ok=True)
def tile(name,data,x=0,crs='EPSG:32620'):
    path=OUT/(name+'.tif')
    with rasterio.open(path,'w',driver='GTiff',width=2,height=2,count=1,dtype='uint16',crs=crs,
                       transform=rasterio.Affine(30,0,x,0,-30,-60)) as ds:ds.write(np.array(data,dtype='uint16'),1)
    return path
a=tile('a',[[1,2],[0,4]]);b=tile('b',[[3,0],[0,1]],30)
assert union([a,b],OUT/'mosaic.tif')==(4,5,1)
with rasterio.open(OUT/'mosaic.tif') as ds:
    assert np.array_equal(ds.read(1),[[1,3,0],[0,4,1]])
    assert ds.transform==rasterio.Affine(30,0,0,0,-30,-60)
assert union([])==(0,0,0)
assert union([a,a])==(3,6,3)
assert union([tile('phase_a',[[1,2],[0,4]],15),tile('phase_b',[[3,0],[0,1]],45)])==(4,5,1)
for bad in [tile('shifted',[[1,0],[0,0]],15),tile('different_crs',[[1,0],[0,0]],30,'EPSG:32619')]:
    try:union([a,bad])
    except ValueError:pass
    else:raise AssertionError('Incompatible grid accepted')
(ROOT/'data/results/mosaic_checks.json').write_text(json.dumps({'checks':8,'passed':True},indent=2)+'\n')
print('Passed 8 exact mosaic checks.')
