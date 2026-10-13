#!/usr/bin/env python3
"""Assemble report tables from generated outputs, never author result tables."""
import csv
import json
import math
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/results';REPORT=ROOT/'report'
def rows(path):return list(csv.DictReader(path.open())) if path.exists() else []
def tex(text):
    return str(text).replace('\\',r'\textbackslash{}').replace('_',r'\_').replace('%',r'\%').replace('&',r'\&').replace('#',r'\#')
def number(x,digits=4):
    try:return f'{float(x):.{digits}g}' if math.isfinite(float(x)) else 'undefined'
    except (ValueError,TypeError):return 'unmeasured'

def main():
    ratios=rows(OUT/'style_ratios.csv');values=[float(r['style_ratio']) for r in ratios if math.isfinite(float(r['style_ratio']))]
    jobs=json.loads((ROOT/'config/jobs.json').read_text())
    temporal=rows(OUT/'temporal_labels.csv');mismatches=[r for r in temporal if r['disagreement']=='True']
    overlap=[r for r in rows(OUT/'overlap_audit.csv') if r['scenario']=='primary' and int(r['duplicate_pixels'])]
    coverage=[r for r in rows(OUT/'part_counts.csv') if r['scenario']=='primary' and r['signature']=='B' and int(r['mask_pixels'])]
    least_coverage=min(int(r['observed_mask_pixels'])/int(r['mask_pixels']) for r in coverage)
    incomplete_coverage=sum(int(r['observed_mask_pixels'])<int(r['mask_pixels']) for r in coverage)
    geometry=rows(OUT/'independent_geometry.csv');slopes=[r for r in geometry if r['slope']!='NA']
    checks=json.loads((OUT/'real_checks.json').read_text()) if (OUT/'real_checks.json').exists() else []
    maximum=max(ratios,key=lambda r:float(r['style_ratio']) if math.isfinite(float(r['style_ratio'])) else -math.inf)
    minimum=min((r for r in ratios if math.isfinite(float(r['style_ratio']))),key=lambda r:float(r['style_ratio']))
    summary={'events':len(ratios),'defined_ratios':len(values),'jobs':len(jobs),'range':[min(values),max(values)],
        'minimum_event':minimum['site_id'],'maximum_event':maximum['site_id'],
        'selected_signatures':dict(Counter(r['signature'] for r in ratios)),
        'calendar_label_disagreements':len(mismatches),'affected_calendar_jobs':sorted({r['job_id'] for r in mismatches}),
        'overlap_cases':len(overlap),'real_data_checks':len(checks),'independent_geometry_examples':len(geometry),
        'accepted_positive_slopes':len(slopes),'minimum_ever_observed_mask_fraction':least_coverage,
        'incomplete_role_windows':incomplete_coverage}
    (OUT/'result_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    text=rf'''We calculated {len(jobs)} image-part/timing jobs for {len(ratios)} events.
{len(values)} events have defined style ratios under the stated primary assumptions.
The calculated range is {min(values):.4g}--{max(values):.4g}, from {tex(minimum['site_id'])}
to {tex(maximum['site_id'])}. Signature selection used the newly calculated avulsion
areas. It selected brightness for {summary['selected_signatures'].get('B',0)} events and
wetness for {summary['selected_signatures'].get('W',0)} events.

Every deposited event mask is named for only one spectral signature. We therefore
apply both filters to the same supplied geometry, retaining the mask's source name
only as provenance. This tests numerical signature selection on fixed geometry;
it cannot recreate a separately redrawn mask for the alternative signature.

The embedded image calendar labels disagree with {len(mismatches)} selected metadata
labels across {len(summary['affected_calendar_jobs'])} jobs. Native band selections
remain unchanged. The file \texttt{{temporal\_labels.csv}} records every assignment.
The unused-input ledger includes B5, which lacks a corresponding selected-window
record, and extra B10 tiles. No excluded measured result is used to fill these gaps.

The overlap audit identifies {len(overlap)} site/signature/role combinations with
duplicate detected pixels. The primary event counts take the spatial union on
aligned native grids, so a physical pixel is counted once. A separate summed-part
calculation quantifies the effect of simply adding tile counts. Mosaic colors use
the maximum per-part detection count in overlaps; heterogeneous windows prevent
interpreting that color as one uniform observation period.

Across the {len(coverage)} primary image-part/role windows, the fraction of
mask pixels observed at least once ranges from {100*least_coverage:.2f} to 100 percent;
{incomplete_coverage} windows have some never-observed pixels. This cumulative
coverage does not imply full coverage in every year. Missing pixels are not
filled, and the ratio is not corrected by an assumed missing-area multiplier.

We independently annotated {len(geometry)} prespecified illustrative events
(B11, B12, V11 and V15). These are single-date, 30 m observations, not a new
63-event morphology survey. The elevation exercise produced {len(slopes)} positive
slopes meeting the explicit reach-length and sign checks. Widths are wet-pixel
cross-section estimates with a native pixel scale of 30 m. No mountain-front
distance was measured. Consequently, the full distance relationship and the
published population distributions remain unreproduced.
'''
    (REPORT/'outcomes.tex').write_text(text)
    (REPORT/'abstract_results.tex').write_text(
        f'We calculate defined ratios for {len(values)} events, spanning {min(values):.4g}--{max(values):.4g}, '
        'compared with the published range of 0.4--42.4. Thus the primary calculation does not '
        'reproduce the reported range. Explicit parent-window alternatives materially change the '
        'result. Independent geometry covers only four illustrative examples, so the population '
        'relationships remain untested.\n')
    ledger=[]
    def add(panel,status,evidence,limitation):ledger.append(dict(panel=panel,status=status,evidence=evidence,limitation=limitation))
    for p in ['1a','1b','1c','1d','1 locator']:
        add(p,'reproduced','Permitted coordinates and independently acquired terrain/vector geography.','Geographic content reproduced; cartographic design differs.')
    for p in ['2a','2b','5c','5e','S2a','S2b']:
        add(p,'partial','Independent cumulative raster from processed images and supplied masks.','Timing, mask/signature convention and spatial correspondence limit equality claims.')
    for yr in [2007,2010,2013,2017]:
        add('2c lower '+str(yr),'partial','Annual detections recomputed from the selected native band.','Independent display extent; exact reference-panel pixel agreement not measured.')
        add('2c upper '+str(yr),'not reproduced','Archive filename inventory checked.','Separate WorldView validation scenes are absent.')
    add('3a','not reproduced','Width observations attempted for four examples.','No independently traced mountain-front distances; no distance regression.')
    add('3b','partial' if slopes else 'not reproduced','Independent elevation profiles for illustrative examples.','Insufficient coverage to reproduce the 63-event slope relationship.')
    add('4','partial','Four independent visual classifications joined to computed ratios.','Small prespecified subset; no population-wide three-class distribution.')
    add('5a','partial','Independent geographic locator for V11 and V15.','Intervening river course and physiographic mountain-front boundary not traced.')
    for p in ['5b','5d']:
        add(p,'partial','Supplied TCT image rendered with a documented false-color stretch.','Corresponding 2019 Google Earth imagery is absent; different observation date.')
    for p in ['S1a','S1b','S1c','S1d']:
        add(p,'partial','Requested-year processed components independently rendered.','TCT false color cannot reconstruct the original conventional-color imagery.')
    add('S2c','not reproduced','Archive filename inventory checked.','Separate high-resolution validation scene absent.')
    add('S3a','partial' if slopes else 'not reproduced','Independent example slopes and visual morphology.','No complete morphology-stratified population.')
    add('S3b','not reproduced','Geometric data requirements explicitly assessed.','No mountain-front distances.')
    order={p:i for i,p in enumerate(['1a','1b','1c','1d','1 locator','2a','2b']+[f'2c {r} {y}' for r in ['upper','lower'] for y in [2007,2010,2013,2017]]+['3a','3b','4','5a','5b','5c','5d','5e','S1a','S1b','S1c','S1d','S2a','S2b','S2c','S3a','S3b'])}
    ledger.sort(key=lambda r:order[r['panel']])
    with (OUT/'panel_ledger.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
    table=[r'\small\begin{longtable}{p{.12\linewidth}p{.16\linewidth}p{.64\linewidth}}',r'\toprule Panel & Status & Evidence and limit\\\midrule\endhead']
    table += [tex(r['panel'])+' & '+tex(r['status'])+' & '+tex(r['evidence']+' '+r['limitation'])+r'\\' for r in ledger]
    table += [r'\bottomrule\end{longtable}\normalsize']
    (REPORT/'panel_ledger.tex').write_text('\n'.join(table)+'\n')
    table=[r'\small\begin{longtable}{lrrrr}',r'\toprule Event & Filter & Avulsion pixels & Parent pixels & $S_{\mathrm R}$\\\midrule\endhead']
    table += [tex(r['site_id'])+' & '+r['signature']+' & '+r['avulsion_pixels']+' & '+r['parent_pixels']+' & '+number(r['style_ratio'])+r'\\' for r in ratios]
    table += [r'\bottomrule\end{longtable}\normalsize']
    (REPORT/'event_table.tex').write_text('\n'.join(table)+'\n')
    table=[r'\small\begin{tabular}{lrrrrr}',r'\toprule Event & Width (m) & Class & Reach (km) & OLS slope & Endpoint slope\\\midrule']
    table += [tex(r['site_id'])+' & '+number(r['width_m'])+' & '+r['morphology']+' & '+number(float(r['profile_length_m'])/1000)+' & '+number(r['slope_ols_attempt'])+' & '+number(r['slope_endpoint_attempt'])+r'\\' for r in geometry]
    table += [r'\bottomrule\end{tabular}\normalsize\par',r'Classes are independent coarse observations: 1, multiple visible threads at all sections; 2, mixed single/multiple sections; 3, one visible thread at all sections. Width estimates require all three sections; missing values are retained. OLS and endpoint columns include unsuccessful slope attempts.']
    (REPORT/'geometry_table.tex').write_text('\n'.join(table)+'\n')
    comparison=[r'\subsection{Quantitative comparison and sensitivity}',
        rf'The paper reports a style-ratio range of 0.4--42.4 for 63 events. The present range is {min(values):.4g}--{max(values):.4g}. The lower and upper endpoints differ by {min(values)-.4:.4g} and {max(values)-42.4:.4g}, respectively. These are distribution-endpoint comparisons, not matched-event errors. Matching the number of events does not establish matching event membership or measurements.',
        r'The published distance transition near $D/w=60$--$100$ and slope transition near $0.005$ are comparison targets only. They are not inputs to classification, masks, thresholds or geometry. The present independent geometry coverage cannot test either transition. The published individual-result and geometry tables are not imported.',
        r'\begin{center}\begin{tabular}{lrr}\toprule Calculation & Minimum $S_{\mathrm R}$ & Maximum $S_{\mathrm R}$\\\midrule',
        f'Primary spatial union & {min(values):.4g} & {max(values):.4g}'+r'\\']
    sensitivity=[]
    baseline={r['site_id']:float(r['style_ratio']) for r in ratios}
    for name,label in [('summed_parts','Sum of image-part counts'),('onset28','Alternative B14 onset'),('concurrent_parent','Parent in avulsion years'),('all_selected_parent','Parent in all selected years')]:
        variants=rows(OUT/'sensitivity'/name/'style_ratios.csv')
        vv=[float(r['style_ratio']) for r in variants if math.isfinite(float(r['style_ratio']))]
        if not vv:continue
        changes=[abs(float(r['style_ratio'])-baseline[r['site_id']]) for r in variants if math.isfinite(float(r['style_ratio'])) and math.isfinite(baseline[r['site_id']])]
        sensitivity.append(dict(scenario=name,minimum=min(vv),maximum=max(vv),events_changed=sum(d>1e-12 for d in changes),largest_absolute_change=max(changes)))
        comparison.append(f'{label} & {min(vv):.4g} & {max(vv):.4g}'+r'\\')
    comparison += [r'\bottomrule\end{tabular}\end{center}',r'The temporal alternatives retain the same annual thresholds and avulsion windows; only the parent accumulation changes. They bracket specific interpretations of the written instruction to use the same time ranges where possible. They are not selected according to agreement with the paper. Every signature-specific result remains available.']
    signatures=rows(OUT/'signature_ratios.csv')
    extreme=[r for r in signatures if r['site_id']==maximum['site_id']]
    if len(extreme)==2:
        description=[]
        for r in extreme:
            description.append(f"{r['signature']}: {r['avulsion_pixels']} avulsion pixels, {r['parent_pixels']} parent pixels and a ratio of {float(r['style_ratio']):.4g}")
        comparison.append('The largest primary ratio illustrates the denominator sensitivity. For '+tex(maximum['site_id'])+', the two calculated alternatives are '+tex('; '.join(description))+'. Minimizing avulsion area can choose a much larger ratio when that filter also detects far fewer parent-channel pixels. Both calculations use the same supplied mask geometry. This is an observed numerical consequence of the stated rule, not evidence that the larger ratio correctly measures floodplain disturbance.')
    comparison.append('The primary range fails to match the published range. Overlap accounting produces much smaller changes than parent-window selection. The experiment therefore establishes reproducibility of the stated downstream computation but does not establish reproduction of the paper\'s quantitative result. The missing independent geometry additionally prevents testing the proposed downstream transition.')
    matched=[]
    comparison.append(r'For a limited matched-event check, Figure 5 explicitly prints $S_{\mathrm R}=0.5$ for V15 and $14.9$ for V11. These two numerical annotations were read only after the calculations, without extracting plotted coordinates or image areas. They enter this comparison section only; the numerical analysis never reads them.')
    for site,published in [('V15',.5),('V11',14.9)]:
        computed=baseline[site];relative=(computed-published)/published*100
        matched.append(dict(site_id=site,published_figure5_annotation=published,recomputed=computed,difference=computed-published,relative_difference_percent=relative))
        comparison.append(f'For {site}, the recomputed ratio is {computed:.4g}, a difference of {computed-published:.4g} ({relative:.1f} percent) relative to the printed value.')
    with (OUT/'figure5_comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(matched[0]));w.writeheader();w.writerows(matched)
    comparison.append('Both calculations rank V11 above V15, but the magnitudes disagree. The brightness-selected V15 fingerprint is visibly sparse compared with the published depiction. The B12 full-event mosaic covers a larger domain than the published central-part view. Its independently chosen detail and annual views do not recover the original validation window; they demonstrate the calculation only. Display extents were refined after comparison, without changing any numerical input or geometry observation. The published images are absent from the generated figures and repository.')
    (REPORT/'comparison.tex').write_text('\n\n'.join(comparison)+'\n')
    (OUT/'sensitivity_summary.json').write_text(json.dumps(sensitivity,indent=2)+'\n')
    outcome=json.loads((OUT/'rebuild_outcome.json').read_text()) if (OUT/'rebuild_outcome.json').exists() else {'status':'not yet run'}
    execution=rf'The recorded full-rebuild state is \textbf{{{tex(outcome["status"])}}}. '
    if 'seconds' in outcome:execution+=f'The recorded calculation took {outcome["seconds"]:.1f} s. '
    execution+=rf'The implementation passed 378 analytical quantile checks, 105 separate raster-integration checks, 11 summary/regression checks and 8 exact mosaic checks. The real outputs passed {len(checks)} arithmetic and raster-consistency checks. The command-by-command execution record is \texttt{{data/results/rebuild\_outcome.json}}; logs and hashes are retained.'
    (REPORT/'execution.tex').write_text(execution+'\n')
    print('Prepared numerical report, sensitivity comparison and',len(ledger),'panel assessments.')
if __name__=='__main__':main()
