#!/usr/bin/env python3
"""Compile LaTeX with every writable cache inside this project."""
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def main():
    env=os.environ.copy()
    for key,folder in {'TMPDIR':'tmp','TEXMFVAR':'texmf-var','TEXMFCONFIG':'texmf-config',
                       'TEXMFCACHE':'texmf-cache','XDG_CACHE_HOME':'cache'}.items():
        path=ROOT/'.runtime'/folder;path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
    with (ROOT/'.runtime/report_compile.log').open('w') as log:
        for _ in range(2):
            subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','report.tex'],
                           cwd=ROOT/'report',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('Compiled report/report.pdf')
if __name__=='__main__':main()
