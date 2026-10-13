# Independent downstream calculation

The input boundary is after annual median compositing and the tasseled-cap
transform. These upstream computations are accepted from the authors and
are not claimed as independently reproduced. The archive supplies separate
brightness (B), greenness (G), and wetness (W) stacks and manually delineated
parent/avulsion regions of interest. All three components are required.

For each selected annual band, exclude nonfinite values and GDAL nodata or
invalid pixels. Use the common valid support of all three components. Do not
interpret a finite zero as missing unless the file marks it as nodata.
Across that band's full image domain compute the 90th percentile of B,
50th percentile of G, and 75th percentile of W. Quantiles interpolate at
index (n-1)p in ascending samples, retaining the first exercise's convention.
The paper does not specify the interpolation convention.

The bright detection is (B > Q90(B)) AND (G < Q50(G)). The wet detection is
(W > Q75(W)) AND (G < Q50(G)). Both inequalities are strict. A uniform
scene therefore contributes no detections. A missing scene remains missing.

For each region of interest and its assigned observation years, sum the
binary detections. Count the union (sum > 0) once per pixel. Report a validity
count alongside every cumulative raster so unobserved regions can be
distinguished from observed absence. Pixel counts and the transform's native
pixel area are recorded separately; angular coordinates must not be
mistaken for metres. The dimensionless style ratio is the avulsion count
divided by the parent count. Zero parent counts give undefined ratios.

Where both signatures have valid masks, select the smaller total avulsion
fingerprint, rather than the smaller ratio. A tie selects brightness, as in
the first exercise. Preserve both estimates so this choice remains auditable.
Do not use the authors' spreadsheet signature-selection column.

The archive supplies one signature-named mask per role, not separate masks
for both filters. Apply its geometry to both filters and choose from the
newly calculated avulsion areas. Retain the original filename for provenance;
do not use its suffix to choose a filter. The alternative filter consequently
inherits a geometry originally delineated for a different signal. This is a
limitation of the available input boundary.

For multipart events, take exact spatial unions on aligned native grids.
Retain the raw sum and overlapping-pixel counts as a sensitivity calculation.
The composite display takes maximum per-part frequency in overlaps; it does
not imply a uniform window across parts.

## Temporal interpretation

Supplementary Data 1 columns G, H and I provide selected years, selected TIFF
bands and onset index. The onset index must refer to position within the
selected-band list: for example, V4 lists native bands 9 and 12 but onset 1.
Bands are ordered newest first. The implemented interpretation assigns
positions 1 through onset to avulsion and subsequent positions to parent.
This is an inference from the metadata and written description, not from
the authors' implementation. Every assignment is saved explicitly.

Several calendar labels disagree with their band lists. The exact supplied
band indices define the calculation; inconsistent calendar labels stay
unresolved unless TIFF descriptions or other permitted metadata resolve
them. Multiple onset values are separate scenarios, never silently reduced
to the one yielding a preferred result. Multi-part images must be checked
for overlap before pixel counts are combined.

The written methods also say parent and avulsion windows were matched where
possible. They do not unambiguously supply separate parent-window indices.
Two sensitivity calculations keep the annual thresholds and avulsion windows
fixed while accumulating the parent over avulsion years, or all selected
years. Neither alternative is chosen by agreement with published results.

## Geometry and statistical panels

The published methods additionally require mean channel width, traced
distance to a physiographically identified mountain front, slope measured
along a 5–10 km or longer channel-belt reach, and multiple cross-section
flow-thread counts. A region-of-interest polygon is not any of these
measurements. Published tabulations remain excluded. Statistics require
independently documented observations; absent measurements remain absent.

The provided tasseled-cap components are not conventional RGB imagery.
Views of these components must be labeled as such. A three-component
transform cannot uniquely recover six original Landsat bands. WorldView and
Google Earth reference panels require their corresponding source imagery;
their printed figures are not acceptable replacements.
