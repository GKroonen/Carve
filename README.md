# Carve

**A runic annotation and analysis platform**

Carve provides an integrated workflow from the manual annotation of individual
signs to quantitative comparison, clustering, mapping and publication-ready
visualization. It is intended for formal graphemic analysis, especially of
runic signs and their variants.

## Getting started

### Windows application

Download `Carve_1.1.exe` from the latest GitHub release and run it. The compiled
Windows application does not require a separate Python installation.

Windows may display a warning because the application is not digitally signed.
If the file was downloaded from this repository's official release page, choose
**More info** and then **Run anyway**.

### Python source

The source release consists of:

- `Carve_1.1.py` — the main application;
- `rotation_correction.py` — the external sign-orientation rules;
- `carve_land.py` — the coastline geometry used by the map views.

Keep all three files in the same directory. Carve requires Python 3 with Tkinter,
Pillow and NumPy. ReportLab is required for PDF export:

```bash
python -m pip install pillow numpy reportlab
python Carve_1.1.py
```

The rotation rules are intentionally kept in a separate module so that they can
be inspected and adapted for different scripts or analytical conventions under
the terms of GNU GPLv3.

The coastline geometry is derived from Natural Earth 1:50m Land data, which
are in the public domain.

## Projects and data

Create a new project or open an existing Carve project. Projects store sign
annotations, image and sign metadata, and relevant analysis settings. Recently
opened projects are remembered between sessions.

Images can be opened individually for annotation. Existing annotation data can
also be imported from CSV, and annotation data can be exported to CSV.

## Application modes

The **Mode** menu provides seven complementary views. Analytical modes share
the selected sign values and the common normalization, distance-metric and
inclusion settings where applicable.

### Sign editing

Click along a stroke to enter its points. Use **Finish stroke** to complete the
current stroke and **Finish sign** when all strokes belonging to the sign have
been entered.

For each sign, enter its grapheme and, where appropriate, component, writing
direction and completeness. Composite signs (bindrunes) are entered by
separating their component graphemes with `+`.

Carve 1.1 also supports ambiguous readings. Separate alternative values with a
comma, for example `p,r`. An ambiguous sign is stored once as a physical sign
but can be included under either interpretation in analyses. The **Ambiguous**
checkbox controls its analytical inclusion and is off by default. Commas and
plus signs cannot be combined in one sign value.

Image-level metadata include location, coordinates, object type and number,
and date range. Metadata can be applied to all signs belonging to the same
image. Existing signs can be selected from the **Saved signs** pane and edited,
deleted or located in the source image.

### Sign inventory

**Sign inventory** displays the annotated forms grouped by sign value and at a
common scale, allowing their geometry to be compared independently of image
size and position. Right-to-left signs are mirrored for comparison. Individual
forms remain linked to the corresponding saved sign and source image.

The inventory can include or exclude incomplete and ambiguous signs, display
stroke components in different colours, and either retain a continuous layout
or wrap the inventory to the available screen width.

**Correct rotation** applies grapheme-specific orientation rules intended to
reduce differences caused by the orientation of signs in the original
inscriptions. For some signs, including particular *j* and *s* variants, this
normalization is partly graphemic rather than strictly epigraphic. The rules are
defined in `rotation_correction.py`.

All normalized signs are scaled to a common height. Relative epigraphic size is
consequently not preserved; characteristically small forms, including some *k*
and *ng* variants, are enlarged. Normalized forms should therefore be
interpreted primarily as comparisons of shape, not absolute sign size.

### Similarity network

The **Similarity network** compares normalized sign forms using the selected
geometric distance metric. Rotation correction can be applied before distances
are calculated. The network is intended to reveal recurrent formal similarities
and intermediate forms rather than a historical genealogy.

The network can represent individual signs, site medoids or site averages.
Users can choose the number of nearest neighbours, an MDS or force-directed
layout, label display and chronological, geographical or legacy colour fills.

Available distance measures are:

- **Chamfer** — measures nearest-point distances between forms;
- **Hausdorff** — emphasizes the greatest nearest-point discrepancy;
- **Procrustes** — compares forms after geometric alignment;
- **Fréchet** — compares the course of curves;

Different metrics emphasize different aspects of sign geometry and may
therefore produce somewhat different similarity patterns. The selected metric
is shared with **Subclustering** and **Pairwise comparison**.

Nodes can be coloured chronologically or geographically. In Carve 1.1, the
colour scale initially fits the signs currently displayed. Click the chronology
or geography legend to toggle between that displayed range and the full range
of the project. This is useful when the visible data have been restricted by
the period or other analysis filters.

### Subclustering

**Subclustering** groups forms of one or more selected sign values through an
average-linkage hierarchy based on the active distance metric. The number of
clusters can be entered directly or changed by dragging the cut line through
the displayed dendrogram.

Each cluster can be represented by:

- a **medoid** — the observed sign with the smallest overall distance to the
  other members of the cluster;
- an **average** — a synthetic representation of the common geometry of the
  clustered forms;
- a **sign matrix** — a simplified structural representation derived from the
  average form.

The view also supports matrix-symmetry options, coloured strokes, chronological
or geographical fills, manual removal of clusters and merging clusters whose
visible sign matrices are identical. The resulting subvariant medoids, averages
and matrices can be reused as representatives in other analytical modes.

### Pairwise comparison

**Pairwise comparison** measures how persistently every pair of signs remains
together across all possible cuts of the average-linkage hierarchy. It is not a
simple table of raw geometric distances. For each pair, the matrix reports the
largest cluster count *k* at which the two signs still belong to the same
cluster. Higher values therefore indicate a more persistent formal affinity.

Rows and columns are ordered by similarity between their complete
co-clustering profiles. An optional dendrogram shows that profile-based order,
while the heatmap provides the exact integer value for every pair. When several
sign values are analysed together, Carve also reports a graphemic-separation
AUC: the probability that a same-value pair has a higher persistence score than
a pair with different values. Sign labels are used only for this diagnostic;
they do not affect distances, clustering or the pairwise matrix itself.

Pairwise comparison uses the active distance metric and the shared
normalization, incomplete-sign and ambiguous-sign settings. Enter one sign,
comma-separated sign values, or `*` to compare all eligible signs.

### Sign map

The **Sign map** displays the geographical distribution of signs or analytical
representatives where coordinates are available. Signs can be grouped as
individual forms, by site or by stored subvariant. Sites can be represented by
medoids or averages; subvariants can additionally be represented by sign
matrices. Optional coastlines, full-project extent, circles, colour fills and a
numbered-list label mode support both exploration and publication figures.

Carve 1.1 introduces collision-aware placement for labels beside signs. Labels
are kept close to their signs while competing positions are evaluated to reduce
label–label and label–sign overlap.

### Time–longitude

**Time–longitude** plots sign forms against longitude and archaeological date,
with dotted date-range lines where ranges are available. As on the Sign map,
forms can be displayed individually or grouped by site or subvariant. Site
groups use medoids or averages, while subvariants can also use sign matrices.
The **Disperse** option separates signs that would otherwise occupy the same or
nearly the same position.

The **beside signs** label mode can use horizontal or vertical labels depending
on the available space, including vertical placement along date-range lines.
Labels use a soft background to keep text legible without fully obscuring the
figure.

The shared **Figure scale** control changes rune and text size in the Similarity
network, Sign map and Time–longitude views.

## Normalization menu

The **Normalization** menu controls the shared preprocessing of sign geometry
in the analytical modes. These operations are applied to analytical copies of
the signs and do not alter the manually annotated strokes stored in the
project. When several options are enabled, Carve applies them in this order:
**Orientation → Trim overhangs / Equalize parallel staves → Crop outline →
Proportion**.

- **Orientation** applies the grapheme-specific rotation rules defined in
  `rotation_correction.py`. It is enabled by default.
- **Proportion** normalizes horizontal and vertical extent independently, so
  differences in aspect ratio do not determine the comparison.
- **Trim overhangs** conservatively shortens small terminal stroke portions
  that extend beyond a qualifying junction, crossing or paired stave.
- **Equalize parallel staves** removes small unmatched terminal extensions from
  qualifying parallel main staves.
- **Crop outline** clips geometry that extends beyond conservatively inferred
  lateral stave boundaries while preserving the boundary staves themselves.
- **Settings…** opens the advanced controls in **Sign inventory**. These include
  the weights used to identify a main stave and the tolerances for junctions,
  overhang trimming, parallel-stave equalization and outline cropping. **Reset**
  restores their defaults.

The final three operations are conservative analytical touch-ups and are off
by default. Because normalization choices and tolerance values can affect
distances, networks and clusters, they should be recorded when results are
reported. Carve includes the active normalization settings in XLSX analytical
exports.

## Saving and exporting

Save the project regularly using **Save project**. Annotation data can also be
saved as CSV.

Analytical figures can be exported through **Save image**. Carve supports JPG,
SVG and PDF output, including dotted date-range lines and label backgrounds
consistent with the on-screen visualization. PDF export from the Python source
requires ReportLab.

## Interpretation and limitations

Carve is designed for formal graphemic comparison. Normalization, orientation
correction, clustering, average forms and sign matrices are analytical
transformations and should not be treated as direct reconstructions of
historical sign production or development.

Manual stroke annotation inevitably involves interpretative decisions,
particularly for damaged or ambiguous inscriptions. Analytical results may
also depend on the selected distance metric, filtering, normalization and
clustering settings.

Normalization deliberately removes absolute sign size, while orientation
correction removes some inscription-specific orientation. Both transformations
facilitate comparison but should be considered when interpreting the results.

## Version and licence

Current version: **Carve 1.1**

Copyright © 2026 Guus Kroonen

Carve is free software released under the
[GNU General Public License, version 3](LICENSE.md). You may use, study, modify
and redistribute the source. Distributed modified versions must remain under
GNU GPLv3, retain the applicable copyright and licence notices, and be marked
as modified.

See [LICENSE.md](LICENSE.md) for the complete licence terms and
[CHANGELOG.md](CHANGELOG.md) for version history.

## Reference

- Carve, all versions: <https://doi.org/10.5281/zenodo.22079175>
- Carve 1.0.0: <https://doi.org/10.5281/zenodo.22079176>
- Carve 1.1.0: <https://doi.org/10.5281/zenodo.24427093>
