# Changelog

All notable user-facing changes to Carve are documented here.

## [1.1.0] — 2026-11-21

### Added

- A **Pairwise comparison** mode showing how persistently each pair of signs
  remains together across all cuts of the average-linkage hierarchy. The view
  includes a heatmap, optional dendrogram and a graphemic-separation AUC when
  multiple sign values are compared.
- A shared **Normalization** menu for the analytical modes, with controls for
  orientation, proportion, overhang trimming, parallel-stave equalization and
  outline cropping.
- Advanced normalization settings for main-stave identification, junction and
  overhang tolerances, parallel-stave equalization and outline cropping.
- Support for ambiguous sign readings using comma-separated alternatives such
  as `p,r`.
- An **Ambiguous** analysis checkbox, disabled by default.
- Separate analytical interpretation, orientation correction, component
  assignment and continuous instance numbering for ambiguous values, while
  retaining a single physical sign record.
- XLSX export of analytical distance matrices together with the active
  normalization and analysis settings.
- A shared figure-scale selector for the Similarity network, Sign map and
  Time–longitude views.
- Clickable chronological and geographical legends in the Similarity network.
  Both initially use the range of the displayed nodes and toggle to the full
  project range when clicked.
- A source distribution with orientation rules in the external
  `rotation_correction.py` module.
- Release of the source code under GNU GPLv3, permitting modification and
  redistribution while preserving attribution and copyleft requirements.

### Changed

- Expanded **Subclustering** with an average-linkage hierarchy, a draggable cut
  line, analysis of multiple sign values, and medoid, average and sign-matrix
  representations. Clusters can be removed manually or merged when their
  visible sign matrices are identical, and stored subvariants can be reused in
  other analytical modes.
- Expanded the **Similarity network** with individual, site-medoid and
  site-average representations; MDS and force-directed layouts; and
  chronological, geographical and legacy fills.
- Expanded the **Sign map** and **Time–longitude** views with grouping by
  individual sign, site or stored subvariant and with medoid, average and
  sign-matrix representatives where applicable.
- Unified normalization, distance-metric and inclusion controls across the
  analytical modes where applicable.
- Reworked label placement in the Sign map and Time–longitude views to reduce
  label–label and label–sign collisions while keeping labels close to signs.
- Consolidated the label display into the **beside signs** mode, with adaptive
  horizontal and vertical placement.
- Vertical Time–longitude labels can follow date-range lines; horizontal
  fallbacks are used when vertical placement would produce collisions.
- Date ranges are displayed with dotted lines, and labels use a subtle softened
  background for legibility.
- Tightened sign clusters and reduced excessive distance between clustered
  signs and their labels.
- Updated the figure-scale choices to 50%, 75%, 100%, 125% and 150%, with 100%
  as the default.
- Shortened the analytical inclusion controls to **Incomplete** and
  **Ambiguous**.
- Improved analytical and figure exports so that the saved output more closely
  matches the on-screen visualization.
- Renamed the preferred orientation module from a development-specific
  derotation filename to `rotation_correction.py`; legacy filenames remain
  available as fallbacks.

### Fixed

- Preserved the intended compact label form when **Extended labels** is not
  selected, including after changing grouping or dispersion settings.
- Prevented unintended horizontal displacement of ordinary Time–longitude
  labels.
- Improved consistency of label backgrounds and dotted date-range lines in
  JPG, SVG and PDF exports.
- Centered vertical labels more accurately on their date-range lines.
- Improved export handling of transparent label backgrounds.
- Preserved ambiguous signs and their metadata when saving and reopening
  projects.

## [1.0.0] — 2026-08-24

- First public release.
- Windows application for annotating, normalizing, comparing, clustering and
  visualizing runic sign forms.
