#!/usr/bin/env python3
"""Independent, explicitly annotated four-example geometry exercise."""
import csv
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'.runtime/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.warp import transform
from aggregate import write
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/results'

def main():
    annotations=json.loads((ROOT/'config/independent_geometry_annotations.json').read_text())
    jobs={j['job_id']:j for j in json.loads((ROOT/'config/jobs.json').read_text())}
    records=[];sections=[];profiles=[]
    fig,axs=plt.subplots(2,2,figsize=(12,10),layout='constrained')
    for a,ax in zip(annotations,axs.flat):
        job=jobs[a['image_part']];out=ROOT/job['output']
        annual=list(csv.DictReader((out/'annual.csv').open()))
        ix=next(i for i,r in enumerate(annual) if int(r['year'])==a['year'])
        manifest=dict(line.rstrip('\n').split('\t',1) for line in (ROOT/job['manifest']).open())
        with rasterio.open(out/'annual_W.tif') as ds:
            water=ds.read(ix+1);t=ds.transform;crs=ds.crs
        rgb=[]
        for component in 'BGW':
            with rasterio.open(ROOT/manifest[component]) as ds:rgb.append(ds.read(int(annual[ix]['band'])))
        rgb=np.stack(rgb);low=np.nanquantile(rgb,.02,axis=(1,2));high=np.nanquantile(rgb,.98,axis=(1,2))
        rgb=np.moveaxis(np.clip((rgb-low[:,None,None])/(high-low)[:,None,None],0,1),0,-1)
        rgb[~np.isfinite(rgb).all(axis=2)]=.85
        ax.imshow(rgb,interpolation='nearest');widths=[]
        for i,ends in enumerate(a['transects'],1):
            p,q=np.array(ends,dtype=float);length=np.linalg.norm((q-p)*[t.a,t.e]);n=int(np.ceil(length))
            xy=p+(q-p)*(np.arange(n)[:,None]+.5)/n
            cells=np.floor(xy).astype(int);valid=((cells[:,0]>=0)&(cells[:,0]<water.shape[1])&(cells[:,1]>=0)&(cells[:,1]<water.shape[0]))
            values=water[cells[valid,1],cells[valid,0]]
            reliable=valid.all() and (values!=255).all() and (values==1).any() and values[0]!=1 and values[-1]!=1
            width=float(np.count_nonzero(values==1)*length/n) if reliable else float('nan')
            if reliable:widths.append(width)
            sections.append(dict(site_id=a['site_id'],year=a['year'],section=i,wet_width_m=width,
                step_m=length/n,visually_resolved_threads=a['visually_resolved_flow_threads'][i-1],
                valid=int(reliable),note='1m sampling integrates30m pixel cells; it does not create1m resolution.'))
            ax.plot(*np.array(ends).T,c='yellow',lw=1);ax.text(*p,str(i),c='yellow',fontsize=8)
        points=np.array(a['centerline_pixels'],dtype=float);slope=float('nan');endpoint=float('nan');length=0;ols=float('nan')
        if len(points):
            coords=np.array([t*tuple(p) for p in points]);distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(coords,axis=0),axis=1))]
            length=float(distance[-1]);s=np.arange(0,length+1,30.);xx=np.interp(s,distance,coords[:,0]);yy=np.interp(s,distance,coords[:,1])
            lon,lat=transform(crs,'EPSG:4326',xx.tolist(),yy.tolist());z=[]
            for x,y in zip(lon,lat):
                ns='N' if y>=0 else 'S';ew='E' if x>=0 else 'W'
                name=f'{ns}{abs(int(np.floor(y))):02d}{ew}{abs(int(np.floor(x))):03d}.hgt'
                path=ROOT/'data/geography/elevation'/name
                if not path.exists():z.append(np.nan);continue
                with rasterio.open(path) as ds:
                    sample=next(ds.sample([(x,y)]))[0];z.append(float(sample) if sample!=-32768 else np.nan)
            z=np.array(z);good=np.isfinite(z)
            if good.sum()>2:
                ols=float(-np.polyfit(s[good],z[good],1)[0]);endpoint=float((z[good][0]-z[good][-1])/(s[good][-1]-s[good][0]))
                # Written paper methods call for kilometer-scale reaches; unresolved
                # sign or incomplete terrain support does not become a positive slope.
                if length>=5000 and good.all() and ols>0 and endpoint>0:slope=ols
            for d,h in zip(s,z):profiles.append(dict(site_id=a['site_id'],distance_m=float(d),elevation_m=float(h)))
            ax.plot(*points.T,c='#ff703d',lw=1)
        threads=a['visually_resolved_flow_threads']
        morphology=3 if all(x==1 for x in threads) else 1 if all(x>1 for x in threads) else 2
        records.append(dict(site_id=a['site_id'],width_m=float(np.mean(widths)) if len(widths)==3 else 'NA',distance_m='NA',
            slope=slope if np.isfinite(slope) else 'NA',morphology=morphology,width_sections_valid=len(widths),
            width_pixel_scale_m=abs(t.a),profile_length_m=length,slope_ols_attempt=ols,slope_endpoint_attempt=endpoint,
            note='Four prespecified illustrative cases; coarse single-date observations; no independent mountain-front distance.'))
        ax.set_title(a['site_id']+f' — {a["year"]}; independently annotated');ax.set(xlabel='Native pixel column',ylabel='Native pixel row')
        # Show the entire annotated region with enough surrounding channel context.
        allpoints=np.concatenate([np.array(a['transects']).reshape(-1,2),points.reshape(-1,2)])
        low=allpoints.min(axis=0)-25;high=allpoints.max(axis=0)+25
        ax.set_xlim(max(0,low[0]),min(water.shape[1],high[0]));ax.set_ylim(min(water.shape[0],high[1]),max(0,low[1]))
    write(OUT/'independent_geometry.csv',records);write(OUT/'width_sections.csv',sections);write(OUT/'elevation_profiles.csv',profiles)
    for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('geometry_observations.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    print('Measured four illustrative image examples; unresolved geometry remains missing.')
if __name__=='__main__':main()
