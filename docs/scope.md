# Processed-data experiment

This exercise changes the starting data in the previous independent
reproduction of Valenza et al. (2020). The accepted inputs are the authors'
annual, median-reduced, tasseled-cap GeoTIFFs; parent and avulsion masks; and
the metadata needed to interpret them. The user explicitly approved site
coordinates, band/year mappings and time-window metadata. Published channel
widths, slopes, distances, morphology labels, areas and style ratios remain
excluded from analysis inputs. Published plots are never digitized.

No author MATLAB, Earth Engine or plotting implementation is opened or run.
The data archive may contain such files; extraction uses a data-only allowlist.
No author fingerprint or figure is substituted for a recomputed fingerprint.
Original C++ implements percentile filtering, annual detections, temporal
aggregation and masked pixel counting. Original Python handles data formats,
configuration, plotting and report assembly. Algorithms shared with the first
exercise keep that exercise's mathematical conventions where possible.

This is independence of downstream implementation, not independence of data
preprocessing or manual delineation. The first experiment's assistant had
seen published tabulated measurements during its feasibility assessment.
During this experiment the supplement was extracted as text, including its
published table. Those values are excluded from machine-readable inputs and
are not used to choose thresholds, masks or observation windows. No claim of
a blinded replication is made.

The new project stays under /data/data2. The first project is unchanged.
The deliverables remain a reproducible procedure, saved computed outputs,
original figure scripts, a panel ledger, LaTeX source and compiled PDF,
published to a new private repository under the authenticated GitHub account.

Data archive: https://datacore.iu.edu/concern/data_sets/4x51hk339
Persistent record: https://hdl.handle.net/2022/25284
Paper: https://doi.org/10.1038/s41467-020-15859-9
