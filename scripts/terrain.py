#!/usr/bin/env python3
"""Acquire independent elevation tiles for regional context (not slope fitting)."""
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import numpy as np
import requests
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds

ROOT=Path(__file__).resolve().parents[1]
REGIONS={
 'andes_north':[-77,0,-69,10],
 'andes_central':[-68,-24,-61,-13],
 'himalaya':[77,25,99,31],
 'new_guinea':[127,-11,151,1],
}

def tilexy(lon,lat,z):
 return (int((lon+180)/360*2**z),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*2**z))

def fetch(tile):
 z,x,y=tile
 p=ROOT/'data/geography/tiles'/f'{z}_{x}_{y}.tif'
 url=f'https://elevation-tiles-prod.s3.amazonaws.com/geotiff/{z}/{x}/{y}.tif'
 if not p.exists():
  if os.environ.get('AVULSION_OFFLINE')=='1':raise FileNotFoundError('Offline terrain tile missing: '+str(p))
  r=requests.get(url,timeout=60);r.raise_for_status();p.write_bytes(r.content)
 return {'path':str(p.relative_to(ROOT)),'url':url,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
 (ROOT/'data/geography/tiles').mkdir(parents=True,exist_ok=True)
 provenance=[]
 for name,bbox in REGIONS.items():
  z=7;x0,y0=tilexy(bbox[0],bbox[3],z);x1,y1=tilexy(bbox[2],bbox[1],z)
  tiles=[(z,x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)]
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   records=list(pool.map(fetch,tiles))
  provenance.extend(records)
  sources=[rasterio.open(ROOT/r['path']) for r in records]
  arr,trans=merge(sources,nodata=-32768)
  dest=np.full((600,800),np.nan,dtype='float32')
  reproject(arr[0],dest,src_transform=trans,src_crs=sources[0].crs,src_nodata=-32768,
    dst_transform=from_bounds(*bbox,800,600),dst_crs='EPSG:4326',dst_nodata=np.nan,resampling=Resampling.bilinear)
  for s in sources:s.close()
  np.savez_compressed(ROOT/'data/geography'/f'{name}.npz',elevation=dest,bbox=np.array(bbox))
  print(name,len(tiles),'independent tiles',flush=True)
 (ROOT/'data/provenance/terrain.json').parent.mkdir(parents=True,exist_ok=True)
 (ROOT/'data/provenance/terrain.json').write_text(json.dumps({'source':'Mapzen/Terrain Tiles, based on public elevation surveys','purpose':'regional context only; not a substitute for channel-slope measurements','tiles':provenance},indent=2))
if __name__=='__main__':main()
