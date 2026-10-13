#!/usr/bin/env python3
"""Original plots from saved calculations. No published figure files are inputs."""
import argparse
import csv
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.runtime/matplotlib'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rasterio
from rasterio.windows import Window

plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                     'savefig.dpi':180,'pdf.fonttype':42})
OUT=ROOT/'figures'
COLORS={'V':'#317b9d','B':'#b96b36','H':'#639050','G':'#845da7'}

def rows(path):
    return list(csv.DictReader(path.open())) if path.exists() else []
def finish(fig,name):
    OUT.mkdir(exist_ok=True)
    for suffix in ['pdf','png']:fig.savefig(OUT/(name+'.'+suffix),bbox_inches='tight')
    plt.close(fig)
def unavailable(ax,text):
    ax.axis('off');ax.text(.5,.5,text,ha='center',va='center',transform=ax.transAxes,wrap=True,color='#744c40')
def site_labels(ax,group):
    ax.figure.canvas.draw();renderer=ax.figure.canvas.get_renderer();occupied=[]
    offsets=[(3,2),(3,-8),(-3,2),(-3,-8),(4,12),(4,-18),(-4,12),(-4,-18),
             (16,20),(16,-26),(-16,20),(-16,-26),(25,30),(25,-36),(-25,30),(-25,-36)]
    for s in group:
        xy=float(s['longitude_deg']),float(s['latitude_deg'])
        for dx,dy in offsets:
            label=ax.annotate(s['site_id'],xy,xytext=(dx,dy),textcoords='offset points',
                              fontsize=5,ha='left' if dx>0 else 'right')
            bbox=label.get_window_extent(renderer).expanded(1.12,1.25)
            if not any(bbox.overlaps(old) for old in occupied):
                occupied.append(bbox)
                if abs(dx)+abs(dy)>15:
                    ax.annotate('',xy,xytext=(dx,dy),textcoords='offset points',
                                arrowprops={'arrowstyle':'-','lw':.3,'color':'gray'})
                break
            label.remove()
        else:
            label=ax.annotate(s['site_id'],xy,xytext=(35,42),textcoords='offset points',fontsize=5)
            occupied.append(label.get_window_extent(renderer))
def jobs():
    return {j['job_id']:j for j in json.loads((ROOT/'config/jobs.json').read_text())}
def selected():
    return {r['site_id']:r['signature'] for r in rows(ROOT/'data/results/style_ratios.csv')}
def raster(path,window=None):
    with rasterio.open(path) as ds:
        win=Window(*window) if window else None
        a=ds.read(1,window=win)
        bounds=rasterio.windows.bounds(win,ds.transform) if win else ds.bounds
        scale=1000 if ds.crs and ds.crs.is_projected and ds.crs.linear_units=='metre' else 1
        label='km' if scale==1000 else 'degrees'
        left,bottom,right,top=bounds
        return a,[left/scale,right/scale,bottom/scale,top/scale],label
def footprint(ax,job_id,signature=None,window=None,parent=True):
    if job_id.endswith('_mosaic'):
        site=job_id.removesuffix('_mosaic');job={'site_id':site};out=ROOT/'data/derived/events'/site
    else:
        job=jobs()[job_id];out=ROOT/job['output']
    explicit_signature=signature is not None
    signature=signature or selected().get(job['site_id'],'W')
    path=out/('avulsion_'+signature+'.tif')
    if not path.exists():
        if explicit_signature:unavailable(ax,'No supplied mask for this signature.');return None
        available=[s for s in ['W','B'] if (out/('avulsion_'+s+'.tif')).exists()]
        if not available:unavailable(ax,'No avulsion mask for this image part.');return None
        signature=available[0];path=out/('avulsion_'+signature+'.tif')
    a,extent,unit=raster(path,window)
    vp=out/('avulsion_'+signature+'_valid.tif')
    valid,_,_=raster(vp,window) if vp.exists() else (a>0,None,None)
    im=ax.imshow(np.ma.masked_where((a==0)|(valid==0),a),extent=extent,origin='upper',
                 cmap='viridis',vmin=1,vmax=max(2,int(a.max())),interpolation='nearest')
    ax.set_facecolor('#f0f0ed')
    pp=out/('parent_'+signature+'.tif')
    if parent and pp.exists():
        p,_,_=raster(pp,window)
        if np.any(p):
            x=np.linspace(extent[0],extent[1],p.shape[1],endpoint=False)+(extent[1]-extent[0])/p.shape[1]/2
            y=np.linspace(extent[3],extent[2],p.shape[0],endpoint=False)+(extent[2]-extent[3])/p.shape[0]/2
            ax.contour(x,y,p>0,levels=[.5],colors='#222222',linewidths=.45,linestyles='--')
    ax.set_xlabel(f'Easting ({unit})' if unit=='km' else 'Longitude (degrees)')
    ax.set_ylabel(f'Northing ({unit})' if unit=='km' else 'Latitude (degrees)')
    return im

def fig1():
    sites=rows(ROOT/'config/sites.csv')
    groups=[('V','andes_north','(a) Northern Andes'),('B','andes_central','(b) Central Andes'),
            ('H','himalaya','(c) Himalaya'),('G','new_guinea','(d) New Guinea')]
    fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    for ax,(prefix,region,title) in zip(axs.flat,groups):
        d=np.load(ROOT/'data/geography'/(region+'.npz'));lo,la,hi,ha=d['bbox']
        im=ax.imshow(d['elevation'],extent=[lo,hi,la,ha],vmin=0,vmax=5000,cmap='Greys',aspect='auto')
        group=[s for s in sites if s['site_id'].startswith(prefix)]
        for s in group:
            xy=float(s['longitude_deg']),float(s['latitude_deg'])
            ax.scatter(*xy,s=16,color=COLORS[prefix],edgecolor='white',linewidth=.3)
        ax.set(title=title+f' ({len(group)} events)',xlabel='Longitude (degrees)',ylabel='Latitude (degrees)')
        site_labels(ax,group)
    fig.colorbar(im,ax=axs.ravel().tolist(),label='Independent regional terrain elevation (m)',shrink=.55)
    fig.suptitle('Study locations from permitted metadata; independently generated maps')
    finish(fig,'fig1')
    fig,ax=plt.subplots(figsize=(8,3),layout='constrained')
    land=json.loads((ROOT/'data/geography/ne_110m_land.geojson').read_text())
    for feature in land['features']:
        geom=feature['geometry'];polygons=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
        for polygon in polygons:
            ring=np.asarray(polygon[0]);ax.fill(ring[:,0],ring[:,1],color='#ddddda',edgecolor='#888888',linewidth=.3,zorder=0)
    for prefix,_,title in groups:
        group=[s for s in sites if s['site_id'].startswith(prefix)]
        ax.scatter([float(s['longitude_deg']) for s in group],[float(s['latitude_deg']) for s in group],
                   s=12,c=COLORS[prefix],label=title[4:])
    ax.set(xlim=(-180,180),ylim=(-60,70),xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',
           title='Global locator from site coordinates')
    ax.legend(ncols=4,fontsize=7);ax.grid(alpha=.2);finish(fig,'fig1_locator')

def atlas():
    for jid,j in jobs().items():
        fig,axs=plt.subplots(1,2,figsize=(10,4),layout='constrained')
        for ax,sig in zip(axs,['B','W']):
            im=footprint(ax,jid,sig)
            ax.set_title(jid+' — '+('brightness' if sig=='B' else 'wetness'))
            if im is not None:fig.colorbar(im,ax=ax,label='Detected years',shrink=.8)
        finish(fig,'atlas_'+jid)

def ratios():
    data=rows(ROOT/'data/results/style_ratios.csv')
    data=[r for r in data if np.isfinite(float(r['style_ratio'])) and float(r['style_ratio'])>0]
    data.sort(key=lambda r:float(r['style_ratio']))
    fig,ax=plt.subplots(figsize=(12,5),layout='constrained')
    for i,r in enumerate(data):
        ax.scatter(i,float(r['style_ratio']),color=COLORS[r['site_id'][0]],s=24)
    ax.set_xticks(range(len(data)),[r['site_id'] for r in data],rotation=90,fontsize=7)
    ax.set(yscale='log',ylabel='Recomputed avulsion / parent pixel count',xlabel='Event (sorted by computed ratio)',
           title='Independent downstream calculations from supplied images and masks')
    ax.axhline(1,c='gray',lw=.7,ls='--');finish(fig,'recomputed_ratios')

def statistics():
    data=rows(ROOT/'data/results/statistical_points.csv')
    fig,axs=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ax,key,label in zip(axs,['normalized_distance','slope'],['Distance / width','Channel-belt slope']):
        usable=[r for r in data if float(r[key])>0 and float(r['style_ratio'])>0]
        if usable:
            for r in usable:ax.scatter(float(r[key]),float(r['style_ratio']),color=COLORS[r['site_id'][0]],s=22)
            ax.set(xscale='log',yscale='log',xlabel=label,ylabel='Style ratio')
        else:unavailable(ax,'Not reproduced\n\nIndependent '+label.lower()+' measurements\nare unavailable for a quantitative relationship.')
    finish(fig,'fig3')
    summary=rows(ROOT/'data/results/group_summaries.csv')
    for name,quantity,title in [('fig4','style_ratio','Avulsion style by channel morphology'),
                                ('supp3a','slope','Slope by channel morphology'),
                                ('supp3b','normalized_distance','Distance / width by channel morphology')]:
        fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
        use=[r for r in summary if r['quantity']==quantity and int(r['n'])>0]
        if use:
            stats=[dict(label={'1':'Multithread','2':'Transitional','3':'Single-thread'}[r['morphology']],
                        med=float(r['median']),q1=float(r['q25']),q3=float(r['q75']),
                        whislo=float(r['min']),whishi=float(r['max']),fliers=[]) for r in use]
            ax.bxp(stats);ax.set(title=title+' — illustrative subset only',ylabel=quantity.replace('_',' '))
            for i,r in enumerate(use,1):ax.text(i,.98,'n='+r['n'],transform=ax.get_xaxis_transform(),ha='center',va='top')
        else:
            missing='mountain-front distances' if quantity=='normalized_distance' else 'slopes and morphology' if quantity=='slope' else 'morphology classifications'
            unavailable(ax,'Not reproduced\n\nIndependent '+missing+'\nare unavailable for these distributions.')
        finish(fig,name)

def manuscript_fingerprints():
    cfg=json.loads((ROOT/'config/figure_views.json').read_text())
    fig,axs=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for ax,key,title in zip(axs,['fig2a','fig2b'],['(a) B12 full-event mosaic','(b) B12 illustrative detail']):
        v=cfg[key];im=footprint(ax,v['job_id'],v.get('signature'),v.get('window'))
        ax.set_title(title+' — '+selected().get('B12','NA')+' filter')
        if im is not None:fig.colorbar(im,ax=ax,label='Number of detected years',shrink=.8)
    finish(fig,'fig2ab')
    fig,axs=plt.subplots(2,4,figsize=(12,6),layout='constrained')
    v=cfg['fig2b'];job=jobs()[v['job_id']];sig=v.get('signature') or selected().get(job['site_id'],'W')
    annual=rows(ROOT/job['output']/'annual.csv')
    for col,year in enumerate([2007,2010,2013,2017]):
        unavailable(axs[0,col],'WorldView reference imagery\nnot supplied in the data archive.')
        axs[0,col].set_title(f'(c) {year} validation')
        matching=[i+1 for i,r in enumerate(annual) if r['year']==str(year)]
        if not matching:unavailable(axs[1,col],f'No resolved band for {year}');continue
        with rasterio.open(ROOT/job['output']/('annual_'+sig+'.tif')) as ds:
            win=Window(*v['window']) if v.get('window') else None
            a=ds.read(matching[0],window=win)
        manifest=dict(line.rstrip('\n').split('\t',1) for line in (ROOT/job['manifest']).open())
        with rasterio.open(manifest['avulsion_'+sig]) as ds:mask=ds.read(1,window=win)==1
        a[~mask]=0
        axs[1,col].imshow(np.ma.masked_where(a!=1,a),cmap='Blues',vmin=0,vmax=1,interpolation='nearest')
        axs[1,col].set_title(f'{year}: recomputed {sig} detections')
        axs[1,col].set(xlabel='Column in selected view',ylabel='Row in selected view')
    finish(fig,'fig2c')
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for ax,key,title in zip(axs,['fig5c','fig5e'],['(c) Sarare V15','(e) Sarare V11']):
        v=cfg[key];im=footprint(ax,v['job_id'],v.get('signature'),v.get('window'))
        ax.set_title(title+' — '+selected().get(v['job_id'],'NA')+' filter')
        if im is not None:fig.colorbar(im,ax=ax,label='Detected years',shrink=.8)
    finish(fig,'fig5ce')
    fig,axs=plt.subplots(1,3,figsize=(12,4.5),layout='constrained')
    for ax,key,title in zip(axs[:2],['supp2a','supp2b'],['(a) B11 fingerprint','(b) B11 detail']):
        v=cfg[key];im=footprint(ax,v['job_id'],v.get('signature'),v.get('window'));ax.set_title(title)
        if im is not None:fig.colorbar(im,ax=ax,label='Detected years',shrink=.8)
    unavailable(axs[2],'(c) Not reproduced\n\nCorresponding WorldView\nvalidation imagery unavailable.')
    finish(fig,'supp2')

def context_figures():
    directory=ROOT/'data/results/context'
    records=json.loads((directory/'manifest.json').read_text())
    ready={r['name']:r for r in records if r['status']=='saved'}
    arrays={name:np.load(directory/(name+'.npz')) for name in ready}
    def draw(ax,name,limits):
        if name not in arrays:unavailable(ax,'No resolved input view');return
        d=arrays[name];a=d['tct'];valid=np.isfinite(a).all(axis=0)
        lo,hi=limits
        image=np.moveaxis(np.clip((a-lo[:,None,None])/(hi-lo)[:,None,None],0,1),0,-1)
        image[~valid]=.85
        left,bottom,right,top=d['bounds']
        ax.imshow(image,extent=[left,right,bottom,top],origin='upper')
        ax.set_title(str(int(d['year']))+' — TCT false color')
        ax.set(xlabel='Input-grid x',ylabel='Input-grid y')
    def limits(names):
        pool=[arrays[n]['tct'].reshape(3,-1) for n in names if n in arrays]
        if not pool:return np.zeros(3),np.ones(3)
        pool=np.concatenate(pool,axis=1)
        low=np.nanquantile(pool,.02,axis=1);high=np.nanquantile(pool,.98,axis=1)
        high=np.where(high>low,high,low+1)
        return low,high
    names=['supp1_'+str(y) for y in [1995,2011,2013,2015]]
    stretch=limits(names)
    fig,axs=plt.subplots(2,2,figsize=(10,9),layout='constrained')
    for ax,name in zip(axs.flat,names):draw(ax,name,stretch)
    fig.suptitle('B12 temporal context from supplied components\nRed: brightness; green: greenness; blue: wetness; common 2–98% stretch')
    finish(fig,'supp1')
    names=['fig5b','fig5d'];stretch5=limits(names)
    fig,axs=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for ax,name in zip(axs,names):draw(ax,name,stretch5)
    fig.suptitle('Sarare context: supplied TCT components, independently rendered\nThese are not the published 2019 Google Earth images')
    finish(fig,'fig5_context')
    fig,ax=plt.subplots(figsize=(8,3.5),layout='constrained')
    for r in rows(ROOT/'config/sites.csv'):
        if r['site_id'] not in ['V11','V15']:continue
        xy=float(r['longitude_deg']),float(r['latitude_deg'])
        ax.scatter(*xy,c=COLORS['V'],s=35);ax.annotate(r['site_id'],xy,xytext=(5,5),textcoords='offset points')
    ax.set(xlim=(-72.1,-71.2),ylim=(7.05,7.4),xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',
           title='Sarare study-event locations; river course not independently traced')
    ax.grid(alpha=.2);finish(fig,'fig5a')
    (directory/'display_stretches.json').write_text(json.dumps({
        'supp1':{'low':stretch[0].tolist(),'high':stretch[1].tolist()},
        'fig5':{'low':stretch5[0].tolist(),'high':stretch5[1].tolist()},
        'channels':['TCB','TCG','TCW'],'quantiles':[.02,.98],
        'note':'Common stretch within each multi-panel comparison; no inverse RGB reconstruction.'},indent=2)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--figure',default='all');args=ap.parse_args()
    actions={'fig1':fig1,'atlas':atlas,'ratios':ratios,'statistics':statistics,
             'fingerprints':manuscript_fingerprints,'context':context_figures}
    if args.figure=='all':
        for action in actions.values():action()
    else:actions[args.figure]()

if __name__=='__main__':main()
