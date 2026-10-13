#!/usr/bin/env python3
"""Run every configured part and preserve per-part success/failure evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--part');ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    jobs=json.loads((ROOT/'config/jobs.json').read_text())
    jobs=[j for j in jobs if not args.part or j['job_id']==args.part]
    if not jobs:raise ValueError('No configured jobs matched')
    def run(job):
        out=ROOT/job['output'];out.mkdir(parents=True,exist_ok=True)
        start=time.monotonic()
        with (out/'execution.log').open('w') as log:
            result=subprocess.run([str(ROOT/'build/fingerprint'),str(ROOT/job['manifest']),str(out)],
                                  cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        print(job['job_id'], 'completed' if result.returncode==0 else 'FAILED',flush=True)
        return {'job_id':job['job_id'],'site_id':job['site_id'],
                'exit_code':result.returncode,'seconds':time.monotonic()-start}
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:records=list(pool.map(run,jobs))
    filename='analysis_runs'+('_'+args.part if args.part else '')+'.json'
    (ROOT/'data/results'/filename).write_text(json.dumps(records,indent=2)+'\n')
    if any(r['exit_code'] for r in records):raise SystemExit(1)

if __name__=='__main__':main()
