#!/usr/bin/env python3
"""Run the full documented calculation and save its actual execution outcome."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PY=ROOT/'.runtime/py311/bin/python'

def main():
    ap=argparse.ArgumentParser();mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--download',action='store_true');mode.add_argument('--offline',action='store_true')
    args=ap.parse_args()
    env=os.environ.copy()
    for key,sub in {'TMPDIR':'tmp','PIP_CACHE_DIR':'cache/pip','MPLCONFIGDIR':'matplotlib',
                    'XDG_CACHE_HOME':'cache','TEXMFVAR':'texmf-var','TEXMFCONFIG':'texmf-config',
                    'TEXMFCACHE':'texmf-cache'}.items():
        path=ROOT/'.runtime'/sub;path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
    env['PYTHONDONTWRITEBYTECODE']='1'
    env['AVULSION_OFFLINE']='1' if args.offline else '0'
    result_dir=ROOT/'data/results';result_dir.mkdir(parents=True,exist_ok=True)
    steps=[['cmake','-S','.','-B','build'],['cmake','--build','build','-j','2'],
           ['ctest','--test-dir','build','--output-on-failure'],
           [str(PY),'tests/check_kernel.py'],[str(PY),'tests/check_summaries.py'],[str(PY),'tests/check_mosaic.py']]
    if args.download:steps.append([str(PY),'scripts/acquire.py'])
    steps += [[str(PY),'scripts/'+name+'.py'] for name in
              ['verify_inputs','terrain','inventory','audit_metadata','bind_data','prepare','run_analysis','geometry','aggregate','temporal_sensitivity','check_results',
               'context_views','plot','report_data','compile_report','manifest']]
    records=[];start=time.time();exit_code=0
    outcome={'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(start)),
             'mode':'download' if args.download else 'cached_inputs','status':'running','steps':records}
    path=result_dir/'rebuild_outcome.json';path.write_text(json.dumps(outcome,indent=2)+'\n')
    with (result_dir/'rebuild.log').open('w') as log:
        for command in steps:
            before=time.perf_counter();print('Running:', ' '.join(command),flush=True)
            log.write('\nCOMMAND: '+' '.join(command)+'\n');log.flush()
            r=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            records.append({'command':command,'exit_code':r.returncode,'seconds':time.perf_counter()-before})
            if r.returncode:
                exit_code=r.returncode;break
    outcome.update(status='completed' if exit_code==0 else 'failed',exit_code=exit_code,seconds=time.time()-start,
                   finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    path.write_text(json.dumps(outcome,indent=2)+'\n')
    if not exit_code:
        # Include the finished run record in the PDF, then refresh artifact hashes.
        with (result_dir/'report_finalize.log').open('w') as log:
            for name in ['report_data','compile_report','manifest']:
                final=subprocess.run([str(PY),'scripts/'+name+'.py'],cwd=ROOT,env=env,
                               stdout=log,stderr=subprocess.STDOUT)
                if final.returncode:
                    outcome.update(status='failed',exit_code=final.returncode,finalization_failed=name)
                    path.write_text(json.dumps(outcome,indent=2)+'\n');exit_code=final.returncode;break
    print('Rebuild',outcome['status'],'after',round(outcome['seconds'],2),'seconds.',flush=True)
    raise SystemExit(exit_code)

if __name__=='__main__':main()
