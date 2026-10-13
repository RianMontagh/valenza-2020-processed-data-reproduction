#!/usr/bin/env python3
"""Analytical cases for minimum-footprint selection and log-space regression."""
import csv
import json
import math
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'.runtime/summary_tests'
WORK.mkdir(parents=True,exist_ok=True)
checks=[]
def check(name,ok):
    if not ok:raise AssertionError(name)
    checks.append({'check':name,'passed':True})
def main():
    p=WORK/'counts.csv'
    p.write_text('site_id,signature,avulsion_pixels,parent_pixels,complete\n'
                 'minimum_area,B,10,1,1\nminimum_area,W,12,100,1\n'
                 'split,B,4,3,1\nsplit,B,6,2,1\n'
                 'tie,B,4,1,1\ntie,W,4,2,1\n'
                 'zero,B,5,0,1\nincomplete,W,5,2,0\n')
    subprocess.run([str(ROOT/'build/fingerprint'),'summarize',str(p),str(WORK)],check=True)
    r={v['site_id']:v for v in csv.DictReader((WORK/'style_ratios.csv').open())}
    check('select minimum area, not minimum ratio',r['minimum_area']['signature']=='B' and float(r['minimum_area']['style_ratio'])==10)
    check('sum parts before division',float(r['split']['style_ratio'])==2)
    check('brightness tie break',r['tie']['signature']=='B')
    check('zero denominator remains undefined',math.isnan(float(r['zero']['style_ratio'])))
    check('incomplete event remains undefined',math.isnan(float(r['incomplete']['style_ratio'])))
    p=WORK/'geometry.csv'
    p.write_text('site_id,style_ratio,width_m,distance_m,slope,morphology\n'
                 'a,10,10,1000,0.001,1\nb,100,10,10000,0.002,1\n'
                 'c,1000,10,100000,0.003,1\n'
                 'excluded,999,10,500,0.004,2\nmissing,NA,NA,NA,NA,NA\n')
    subprocess.run([str(ROOT/'build/fingerprint'),'statistics',str(p),str(WORK)],check=True)
    r=next(csv.DictReader((WORK/'regression.csv').open()))
    check('fit subset excludes D/w <= 60',int(r['n'])==3)
    check('exact power law slope',abs(float(r['log10_slope'])-1)<1e-12)
    check('exact power law intercept',abs(float(r['log10_intercept'])+1)<1e-12)
    check('exact power law explained variance',abs(float(r['r_squared'])-1)<1e-12)
    rows=list(csv.DictReader((WORK/'group_summaries.csv').open()))
    r=next(v for v in rows if v['morphology']=='1' and v['quantity']=='style_ratio')
    check('quartile convention',float(r['q25'])==55 and float(r['median'])==100 and float(r['q75'])==550)
    r=next(v for v in rows if v['morphology']=='3' and v['quantity']=='slope')
    check('missing category not filled',int(r['n'])==0 and math.isnan(float(r['median'])))
    (ROOT/'data/results/summary_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(f'Passed {len(checks)} analytical summary checks.')
if __name__=='__main__':main()
