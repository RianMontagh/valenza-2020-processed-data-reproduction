# River-avulsion fingerprints from processed images and masks

An independent downstream reproduction of Valenza et al. (2020),
[*Downstream changes in river avulsion style are related to channel morphology*](https://doi.org/10.1038/s41467-020-15859-9).
This second exercise starts with the deposited annual tasseled-cap images and
channel masks. The [first exercise](https://github.com/RianMontagh/valenza-2020-independent-reproduction)
remains in its separate repository.

Read the [compiled report](report/report.pdf), [LaTeX source](report/report.tex),
[numerical summary](data/results/result_summary.json), and
[32-panel ledger](data/results/panel_ledger.csv).

The pipeline evaluates 77 image-part/timing jobs covering 63 metadata events.
It generates annual detections, cumulative fingerprints, event area ratios,
explicit sensitivity calculations, and original figures. This is a **partial
scientific reproduction**: full geometry and morphology relationships and
separate high-resolution reference images remain unavailable. Software
validation does not establish scientific agreement.

The primary ratios span **0.0388–463.9**, compared with the paper's reported
**0.4–42.4**. Using the avulsion years for parent-channel accumulation changes
the maximum to **30.86**. These results identify a substantial sensitivity to
the time-window and fixed-mask signature assumptions; they do not reproduce
the reported quantitative range. All 63 primary ratios are defined, and the
saved rasters pass **6,974** consistency checks.

## Accepted inputs and independence

Accepted inputs are the authors' processed brightness, greenness and wetness
stacks, parent/avulsion masks, and interpretation metadata (IDs, coordinates,
native bands, year labels and onset indices). The numerical kernel is original
C++17, with original Python data-handling, observation and plotting scripts.
Independent public terrain supports maps and illustrative elevation profiles.

Author analysis/plotting code, tabulated widths, slopes, distances, morphology
classes, areas, ratios and signature selections are excluded from analysis
inputs. No figure is digitized or inserted as a generated result. Published
range/transition values appear only in the report's post-calculation comparison.
The report discloses prior exposure to published numbers; this is not a blinded
experiment. See [scope](docs/scope.md) and [methods](docs/methods.md).

Several limitations materially affect the results:

- The archive supplies one signature-named mask per channel role. Both newly
  calculated spectral filters use that same geometry; the smaller avulsion
  footprint chooses the filter. The mask filename does not choose it.
- Native bands are preserved. Six source metadata rows have internal
  inconsistencies, and embedded image years disagree with 33 selected labels
  across six jobs. All assignments are saved in
  [temporal_labels.csv](data/results/temporal_labels.csv).
- The primary parent window precedes avulsion onset. Alternatives use the
  avulsion years or all selected years. B14's two onset indices are also run.
- Primary multipart counts use an exact spatial union. A summed-part
  sensitivity and an overlap audit identify double-counting effects.
- Four independently annotated examples provide limited geometry observations.
  They cannot establish the paper's 63-event relationships or population
  distributions. Missing and unsuccessful observations remain explicit.
- TCT false-color context views are not conventional RGB, WorldView, or
  the publication's 2019 Google Earth scenes.

## Complete rebuild

Keep the checkout, dependencies and writable caches under `/data/data0` through
`/data/data7`. This working copy is under
`/data/data2/UW2UCSD_Whidbey_c2chien/rmontagh_valenza2020_processed`.
The source ZIP is about 28 GiB and extracts to about 30 GiB. Allow at least
65 GiB of free storage and roughly 16 GiB RAM for four simultaneous jobs on
large parts; reduce the worker count in `scripts/run_analysis.py` if needed.

System requirements are Python 3.11, a C++17 compiler, CMake, GDAL headers and
libraries, and pdfLaTeX with the packages named in `report/report.tex`.
Python versions are pinned in [requirements.txt](requirements.txt).

```bash
mkdir -p .runtime/tmp .runtime/cache .runtime/matplotlib
export TMPDIR="$PWD/.runtime/tmp"
export PIP_CACHE_DIR="$PWD/.runtime/cache/pip"
export MPLCONFIGDIR="$PWD/.runtime/matplotlib"
export PYTHONDONTWRITEBYTECODE=1
python3.11 -m venv .runtime/py311
.runtime/py311/bin/pip install -r requirements.txt
.runtime/py311/bin/python scripts/run_rebuild.py --download
```

The institutional archive may require restoration from long-term storage.
If the acquisition command reports that restoration was requested or is still
processing, retry the same command after the provider makes it available
(its estimate is about one hour). The current provider ignores HTTP range
requests; an interrupted download may restart. Missing data are never replaced
with invented inputs.

For the **documented procedure actually executed here**, with the frozen
archive and extracted inputs already present:

```bash
.runtime/py311/bin/python scripts/run_rebuild.py --offline
```

This command verifies all extracted input hashes, rebuilds C++, runs the
numerical tests, regenerates regional terrain arrays and every configured
analysis job, measures the documented geometry examples, aggregates events,
runs timing/overlap sensitivities, checks real rasters, regenerates every
figure and report table, compiles the PDF, and hashes the artifacts. It does
not skip an analysis job merely because its previous outputs exist. See the
[actual outcome](data/results/rebuild_outcome.json) and
[full command log](data/results/rebuild.log).

A new checkout includes small independent geographic inputs. They can also be
reacquired with `scripts/geography.py` and `scripts/terrain.py`. The large
institutional ZIP and extracted source data are excluded from Git. Their
[archive provenance](data/inputs/archive_provenance.json),
[member inventory](data/inputs/archive_inventory.csv), and
[file interpretation inventory](data/inputs/file_inventory.json) are retained.
Downloaded archives must match the frozen SHA-256; refreshing an input is an
explicit scientific change.

## Inspection and individual steps

The full procedure is preferred. These commands are useful for inspecting a
single calculation without rerunning everything:

```bash
.runtime/py311/bin/python scripts/acquire.py --status
.runtime/py311/bin/python scripts/inventory.py
.runtime/py311/bin/python scripts/audit_metadata.py
.runtime/py311/bin/python scripts/bind_data.py
.runtime/py311/bin/python scripts/prepare.py
.runtime/py311/bin/python scripts/run_analysis.py --part B11
.runtime/py311/bin/python scripts/check_results.py
.runtime/py311/bin/python scripts/plot.py --figure fingerprints
.runtime/py311/bin/python scripts/compile_report.py
```

Run commands from the repository root. `config/data_bindings.json` explicitly
maps each interpretation row to image stacks and mask variables. The bindings
use only filenames and permitted metadata. `config/manifests/` records the
portable C++ inputs; for example:

```bash
build/fingerprint config/manifests/B11.tsv data/derived/B11
```

The metadata extractor (`scripts/metadata.py`) refreshes only allowed workbook
columns A, B, C, G, H and I. Normal rebuilding uses the frozen configuration;
a source refresh is optional and may change the scientific inputs.

## Saved evidence

- `src/fingerprint.cpp`: numerical classification, accumulation, area-ratio
  selection and statistical summaries.
- `data/derived/`: annual detections, cumulative rasters, valid-year rasters,
  numerical counts and per-job logs. All are independently generated.
- `data/results/`: event tables, temporal/overlap audits, sensitivity tables,
  independent geometry, validation, execution records and artifact hashes.
- `config/independent_geometry_annotations.json`: explicit independent
  transects, thread counts and traced example reaches, recorded before
  calculating style ratios or slopes.
- `figures/`: generated manuscript counterparts, diagnostic event ratios,
  independent geometry views and a brightness/wetness atlas for every job.
- `report/`: report source, generated tables and compiled PDF.

Validation includes 378 analytical quantile checks, 105 separate raster-oracle
checks, 11 summary/regression checks, eight exact mosaic checks, and the
recorded real-data consistency checks. Test fixtures are never manuscript
data. The final panel ledger separates reproduced geographic content, partial
scientific correspondence and unreproduced panels.
