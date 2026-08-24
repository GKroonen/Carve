# Carve
A Runic annotation and analysis platform

CARVE 1.0
README

ABOUT

Carve is a  Runic annotation and analysis platform. It provides 
an integrated workflow from the annotation of individual signs to quantitative 
analysis and publication-ready visualizations.


GETTING STARTED

Run Carve.exe and create a new project or open an existing Carve project.
Projects store sign annotations and associated metadata. Recently opened
projects are remembered between sessions.

Images can be opened individually for annotation. Existing annotation data can
also be imported from CSV.


ANNOTATING SIGNS

Click along a stroke to enter its points. Use Finish stroke to complete the
current stroke and Finish sign when all strokes belonging to the sign have
been entered.

For each sign, enter its grapheme and, where appropriate, component, writing
direction and completeness. Composite signs ('bindrunes') are entered by 
separating their component graphemes with +.

Image-level metadata include location, coordinates, object type and number,
and date range. Metadata can be applied to all signs belonging to the same
image.

Existing signs can be selected from the Saved signs pane and edited or
deleted.


NORMALIZED SIGNS

Normalized signs displays annotated forms at a common scale, allowing their
geometry to be compared independently of image size and position.
Right-to-left signs are mirrored for comparison.

Correct rotation applies grapheme-specific derotation rules intended to reduce
differences caused by the orientation of signs in the original inscriptions. 

For some signs, including the j and s runic variants, derotation is partly 
graphemic rather than strictly epigraphic. Carve normalizes these forms to 
facilitate comparison of their underlying structure.

All normalized signs are scaled to a common height. Relative epigraphic size
is consequently not preserved; characteristically small forms, including some
k and ng variants, are enlarged. Normalized forms should therefore be
interpreted primarily as comparisons of shape, not absolute sign size.


SIMILARITY ANALYSIS

The Similarity network compares normalized sign forms using the selected
geometric distance metric. Rotation correction can be applied before
distances are calculated. The network is intended to reveal recurrent formal
similarities and intermediate forms rather than a historical genealogy.

Available distance measures are:

- Chamfer: measures nearest-point distances between forms.
- Hausdorff: emphasizes the greatest nearest-point discrepancy.
- Procrustes: compares forms after geometric alignment.
- Fréchet: compares the course of curves.
- DTW (Dynamic Time Warping): compares ordered stroke trajectories while
  allowing local differences in progression.

Different metrics emphasize different aspects of sign geometry and may
therefore produce somewhat different similarity patterns.


CLUSTERING AND SUBVARIANTS

Cluster subvariants groups forms of a selected grapheme by geometric
similarity. The number of clusters can be selected manually; automatic
clustering considers up to min(20, n-1) clusters.

Each cluster can be represented by:

- a medoid: the observed sign with the smallest overall distance to the other
  members of the cluster;
- a consensus: a synthetic representation of the common geometry of the
  clustered forms;
- a sign matrix: a simplified structural representation derived from the
  consensus form.

These representations can also be used in other analytical views.


GEOGRAPHIC AND CHRONOLOGICAL VIEWS

The Sign map displays the geographical distribution of signs or analytical
representatives where coordinates are available.

Time-longitude plots sign forms against longitude and their archaeological
date, with date ranges shown where available.

Both views can display actual signs or representative medoids, consensuses,
and sign matrices.


SAVING AND EXPORTING

Save the project regularly using Save project. Annotation data can also be
saved as CSV.

Analytical figures can be exported in the formats offered by Save image,
including vector formats suitable for further editing and publication.


INTERPRETATION AND LIMITATIONS

Carve is designed for formal graphemic comparison. Normalization, derotation,
clustering, consensus forms and sign matrices are analytical transformations
and should not be treated as direct reconstructions of historical sign
production or development.

Manual stroke annotation inevitably involves interpretative decisions,
particularly for damaged or ambiguous inscriptions. Analytical results may
also depend on the selected distance metric and clustering settings.

Normalization deliberately removes absolute sign size, while derotation
removes some inscription-specific orientation. Both transformations facilitate
comparison but should be considered when interpreting the results.


REQUIREMENTS

The distributed Windows version runs as Carve.exe and does not require a
separate Python installation.


VERSION

Carve 1.0

Copyright (c) 2026 Guus KroonenSee LICENSE.txt for terms of use.


REFERENCE
DOI: https://doi.org/10.5281/zenodo.22079176
