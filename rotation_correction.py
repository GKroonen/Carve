# -*- coding: utf-8 -*-
"""Grapheme-specific rotation correction for Carve.

This stable public filename can be replaced by script-specific rule sets while
preserving the public API documented below.

Expected input unit:
    unit["grapheme"]
    unit["strokes"]  # normalized polylines: [[(x, y), ...], ...]

Important:
- RTL-to-LTR mirroring is performed by the annotator before this module is called.
- This module uses rotation only; it never reflects a sign.
- Most graphemes are aligned to a vertical longitudinal axis.
- The angle-shaped k variant, structurally sideways o subtype, and wide Øvre-Stabu-type j
  are aligned to a horizontal structural axis.

Public API:
    align_unit(unit) -> copied/aligned unit
    alignment_axis(grapheme, strokes) -> (axis_angle, rule_name)
    ORIENTATION_RULES
"""

import math
import unicodedata

# Temporary diagnostic weights for the generic principal-stave detector.
# Values are normalized internally, so only their relative magnitudes matter.
PRINCIPAL_STAVE_WEIGHTS = {
    "chord": 25.0,
    "length": 12.0,
    "straightness": 22.0,
    "vertical_extent": 18.0,
    "verticality": 23.0,
}

def set_principal_stave_weights(chord=None, length=None, straightness=None, vertical_extent=None, verticality=None):
    updates = {
        "chord": chord,
        "length": length,
        "straightness": straightness,
        "vertical_extent": vertical_extent,
        "verticality": verticality,
    }
    for key, value in updates.items():
        if value is not None:
            try:
                PRINCIPAL_STAVE_WEIGHTS[key] = max(0.0, float(value))
            except (TypeError, ValueError):
                pass
    return dict(PRINCIPAL_STAVE_WEIGHTS)

def get_principal_stave_weights():
    return dict(PRINCIPAL_STAVE_WEIGHTS)



# ---------------------------------------------------------------------------
# Basic geometry
# ---------------------------------------------------------------------------

def _all_points(strokes):
    return [p for stroke in strokes for p in stroke]


def _polyline_length(stroke):
    return sum(
        math.hypot(
            stroke[i][0] - stroke[i - 1][0],
            stroke[i][1] - stroke[i - 1][1],
        )
        for i in range(1, len(stroke))
    )


def _fit_axis(stroke):
    """Fit an undirected principal axis to all points of one stroke.

    This is more stable than using only its two endpoints, especially when
    endpoint placement is slightly irregular.
    """
    if len(stroke) < 2:
        return 0.0

    cx = sum(x for x, _ in stroke) / len(stroke)
    cy = sum(y for _, y in stroke) / len(stroke)
    sxx = sum((x - cx) ** 2 for x, _ in stroke)
    syy = sum((y - cy) ** 2 for _, y in stroke)
    sxy = sum((x - cx) * (y - cy) for x, y in stroke)

    if abs(sxx - syy) < 1e-15 and abs(sxy) < 1e-15:
        dx = stroke[-1][0] - stroke[0][0]
        dy = stroke[-1][1] - stroke[0][1]
        return math.atan2(dy, dx)

    # Principal-component orientation.
    return 0.5 * math.atan2(2.0 * sxy, sxx - syy)


def _stroke_stats(stroke):
    if len(stroke) < 2:
        return {
            "length": 0.0,
            "chord": 0.0,
            "straightness": 0.0,
            "angle": 0.0,
            "vertical_extent": 0.0,
            "horizontal_extent": 0.0,
            "centroid_x": 0.0,
            "centroid_y": 0.0,
        }

    length = _polyline_length(stroke)
    chord = math.hypot(
        stroke[-1][0] - stroke[0][0],
        stroke[-1][1] - stroke[0][1],
    )
    xs = [p[0] for p in stroke]
    ys = [p[1] for p in stroke]

    return {
        "length": length,
        "chord": chord,
        "straightness": chord / max(length, 1e-9),
        "angle": _fit_axis(stroke),
        "vertical_extent": max(ys) - min(ys),
        "horizontal_extent": max(xs) - min(xs),
        "centroid_x": sum(xs) / len(xs),
        "centroid_y": sum(ys) / len(ys),
    }


def _axial_mean_angle(angles):
    """Mean of undirected axes (angles modulo pi)."""
    if not angles:
        return None
    sx = sum(math.cos(2 * a) for a in angles)
    sy = sum(math.sin(2 * a) for a in angles)
    if abs(sx) < 1e-12 and abs(sy) < 1e-12:
        return angles[0]
    return 0.5 * math.atan2(sy, sx)


def _target_rotation(axis_angle, target):
    if axis_angle is None:
        return 0.0

    target_angle = 0.0 if target == "horizontal" else math.pi / 2
    candidates = [
        target_angle - axis_angle,
        target_angle + math.pi - axis_angle,
    ]
    candidates = [((a + math.pi) % (2 * math.pi)) - math.pi for a in candidates]
    return min(candidates, key=abs)


def _rotate(strokes, angle):
    pts = _all_points(strokes)
    if not pts:
        return [list(stroke) for stroke in strokes]

    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    ca, sa = math.cos(angle), math.sin(angle)

    return [
        [
            (
                cx + ca * (x - cx) - sa * (y - cy),
                cy + sa * (x - cx) + ca * (y - cy),
            )
            for x, y in stroke
        ]
        for stroke in strokes
    ]


def _renormalize(strokes):
    pts = _all_points(strokes)
    if not pts:
        return strokes

    xmin = min(x for x, _ in pts)
    ymin = min(y for _, y in pts)
    ymax = max(y for _, y in pts)
    height = max(ymax - ymin, 1e-9)

    return [
        [((x - xmin) / height, (y - ymin) / height) for x, y in stroke]
        for stroke in strokes
    ]


def _bounds(strokes):
    pts = _all_points(strokes)
    if not pts:
        return 0.0, 0.0, 0.0, 0.0
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# Generic landmark rules
# ---------------------------------------------------------------------------

def _longest_stroke_axis(strokes, stats):
    idx = max(range(len(strokes)), key=lambda i: stats[i]["length"])
    return stats[idx]["angle"], "longest stroke"


def _principal_stave_axis(strokes, stats):
    """General principal-stave detector with tunable diagnostic weights.

    Besides size/straightness cues, this now contains an explicit *axial
    verticality* term.  A perfectly vertical fitted stroke scores 1.0 and a
    horizontal stroke 0.0.  This is intentionally separate from vertical
    extent: a long diagonal can have substantial vertical extent without being
    a plausible main stave.
    """
    max_length = max((s["length"] for s in stats), default=1.0) or 1.0
    max_chord = max((s["chord"] for s in stats), default=1.0) or 1.0
    max_v = max((s["vertical_extent"] for s in stats), default=1.0) or 1.0

    w = PRINCIPAL_STAVE_WEIGHTS
    total_w = sum(max(0.0, float(v)) for v in w.values()) or 1.0
    wn = {k: max(0.0, float(v)) / total_w for k, v in w.items()}

    scores = []
    for st in stats:
        # _fit_axis is axial; abs(sin(angle)) is therefore orientation-direction
        # invariant and equals 1 for vertical, 0 for horizontal.
        verticality = abs(math.sin(st["angle"]))
        score = (
            wn["chord"] * (st["chord"] / max_chord)
            + wn["length"] * (st["length"] / max_length)
            + wn["straightness"] * st["straightness"]
            + wn["vertical_extent"] * (st["vertical_extent"] / max_v)
            + wn["verticality"] * verticality
        )
        scores.append(score)

    idx = max(range(len(scores)), key=lambda i: scores[i])
    return stats[idx]["angle"], "principal stave"


def _leftmost_plausible_stave_axis(strokes, stats, rule_name):
    """Select the leftmost long, reasonably straight stroke."""
    _, ymin, _, ymax = _bounds(strokes)
    total_h = max(ymax - ymin, 1e-9)

    candidates = [
        i for i, st in enumerate(stats)
        if st["vertical_extent"] >= 0.48 * total_h
        and st["straightness"] >= 0.62
    ]
    if not candidates:
        candidates = [
            i for i, st in enumerate(stats)
            if st["vertical_extent"] >= 0.38 * total_h
        ]
    if not candidates:
        axis, _ = _principal_stave_axis(strokes, stats)
        return axis, f"{rule_name} fallback"

    idx = min(
        candidates,
        key=lambda i: (
            stats[i]["centroid_x"],
            -stats[i]["straightness"],
            -stats[i]["vertical_extent"],
            -stats[i]["length"],
        ),
    )
    return stats[idx]["angle"], rule_name


def _mean_two_principal_axes(strokes, stats):
    max_v = max((st["vertical_extent"] for st in stats), default=1.0) or 1.0
    max_c = max((st["chord"] for st in stats), default=1.0) or 1.0

    ranked = sorted(
        range(len(strokes)),
        key=lambda i: (
            0.50 * stats[i]["straightness"]
            + 0.30 * (stats[i]["vertical_extent"] / max_v)
            + 0.20 * (stats[i]["chord"] / max_c)
        ),
        reverse=True,
    )[:2]

    if len(ranked) >= 2:
        return (
            _axial_mean_angle([stats[i]["angle"] for i in ranked]),
            "mean two principal staves",
        )
    if ranked:
        return stats[ranked[0]]["angle"], "single-stave fallback"
    return None, "no axis"


def _point_segment_distance(point, a, b):
    """Shortest distance from *point* to the finite segment a-b."""
    px, py = point
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    denom = vx * vx + vy * vy
    if denom <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * vx + (py - ay) * vy) / denom
    t = max(0.0, min(1.0, t))
    qx, qy = ax + t * vx, ay + t * vy
    return math.hypot(px - qx, py - qy)


def _point_polyline_distance(point, stroke):
    if not stroke:
        return float("inf")
    if len(stroke) == 1:
        return math.hypot(point[0] - stroke[0][0], point[1] - stroke[0][1])
    return min(
        _point_segment_distance(point, stroke[i - 1], stroke[i])
        for i in range(1, len(stroke))
    )


def _axial_angle_difference(a, b):
    """Smallest difference between two undirected axes, in radians."""
    delta = abs((a - b) % math.pi)
    return min(delta, math.pi - delta)


def _confident_single_main_stave_axis(grapheme, strokes, stats):
    """Find only unambiguous single-main-stave e/d/m structures.

    A candidate must be long and straight, have a secondary stroke attached,
    and lack either a comparable parallel stave or a comparable crossing axis.
    Ambiguous forms therefore retain the established multi-stave rule.
    """
    if len(strokes) < 2:
        return None

    xmin, ymin, xmax, ymax = _bounds(strokes)
    span = max(xmax - xmin, ymax - ymin, 1e-9)
    candidates = [
        i for i, st in enumerate(stats)
        if st["straightness"] >= 0.78
        and st["chord"] >= 0.58 * span
    ]
    if not candidates:
        return None

    dominance_required = {"e": 1.18, "d": 1.28, "m": 1.35}[grapheme]
    attachment_tolerance = 0.10 * span
    ranked = sorted(
        candidates,
        key=lambda i: (
            stats[i]["chord"],
            stats[i]["straightness"],
            stats[i]["length"],
        ),
        reverse=True,
    )

    for idx in ranked:
        main = stats[idx]
        main_chord = max(main["chord"], 1e-9)
        competitors = [
            j for j, other in enumerate(stats)
            if j != idx
            and other["straightness"] >= 0.68
            and other["chord"] >= 0.20 * span
        ]
        second_chord = max(
            (stats[j]["chord"] for j in competitors),
            default=0.0,
        )
        if second_chord and main_chord / second_chord < dominance_required:
            continue

        if any(
            stats[j]["chord"] >= 0.68 * main_chord
            and _axial_angle_difference(main["angle"], stats[j]["angle"])
                <= math.radians(30.0)
            for j in competitors
        ):
            continue

        if any(
            stats[j]["chord"] >= 0.86 * main_chord
            and _axial_angle_difference(main["angle"], stats[j]["angle"])
                >= math.radians(35.0)
            for j in competitors
        ):
            continue

        attachments = 0
        for j, stroke in enumerate(strokes):
            if j == idx or not stroke:
                continue
            endpoints = [stroke[0]] if len(stroke) == 1 else [stroke[0], stroke[-1]]
            if min(
                _point_polyline_distance(point, strokes[idx])
                for point in endpoints
            ) <= attachment_tolerance:
                attachments += 1
        if attachments:
            return main["angle"], f"{grapheme} single main stave"

    return None


def _one_or_two_p_staves_axis(strokes, stats):
    """p: use one full-height main stave or the consensus of two.

    Short vertical branch segments are deliberately excluded.  This retains
    the historic single-stave behaviour while allowing double-stave p forms
    to contribute both of their structural uprights.
    """
    _, ymin, _, ymax = _bounds(strokes)
    total_h = max(ymax - ymin, 1e-9)
    candidates = [
        i for i, st in enumerate(stats)
        if st["vertical_extent"] >= 0.55 * total_h
        and st["straightness"] >= 0.62
        and abs(math.sin(st["angle"])) >= math.cos(math.radians(40.0))
    ]
    if not candidates:
        axis, _ = _principal_stave_axis(strokes, stats)
        return axis, "p principal-stave fallback"

    ranked = sorted(
        candidates,
        key=lambda i: (
            stats[i]["vertical_extent"],
            stats[i]["straightness"],
            stats[i]["chord"],
            stats[i]["length"],
        ),
        reverse=True,
    )
    if len(ranked) == 1:
        return stats[ranked[0]]["angle"], "p single main stave"

    chosen = ranked[:2]
    return (
        _axial_mean_angle([stats[i]["angle"] for i in chosen]),
        "p two-main-stave consensus",
    )


def _outermost_long_staves_axis(strokes, stats):
    """d: mean axis of the two plausible outer staves.

    Candidate strokes must span a substantial part of the dominant dimension.
    Straightness is used to reject internal diagonals where possible.  When
    the outer staves are clearly horizontal, the caller can treat the form as
    a sideways d.
    """
    xmin, ymin, xmax, ymax = _bounds(strokes)
    total_w = max(xmax - xmin, 1e-9)
    total_h = max(ymax - ymin, 1e-9)
    sideways = total_w >= 1.18 * total_h

    def stave_extent(st):
        return st["chord"] if sideways else st["vertical_extent"]

    total_extent = total_w if sideways else total_h

    candidates = [
        i for i, st in enumerate(stats)
        if stave_extent(st) >= 0.52 * total_extent
        and st["straightness"] >= 0.58
    ]
    if len(candidates) < 2:
        candidates = [
            i for i, st in enumerate(stats)
            if stave_extent(st) >= 0.45 * total_extent
            and st["straightness"] >= 0.48
        ]
    if len(candidates) < 2:
        axis, rule = _mean_two_principal_axes(strokes, stats)
        return axis, rule, False

    # Take the outer candidates by transverse centroid. If several strokes
    # occupy nearly the same side, prefer the straighter/more extensive one.
    centroid_key = "centroid_y" if sideways else "centroid_x"
    extent_key = "chord" if sideways else "vertical_extent"
    left_band = sorted(
        candidates,
        key=lambda i: stats[i][centroid_key],
    )
    right_band = list(reversed(left_band))

    left_min = stats[left_band[0]][centroid_key]
    right_max = stats[right_band[0]][centroid_key]
    spread = max(right_max - left_min, 1e-9)
    tolerance = 0.12 * spread

    left_candidates = [
        i for i in candidates
        if stats[i][centroid_key] <= left_min + tolerance
    ]
    right_candidates = [
        i for i in candidates
        if stats[i][centroid_key] >= right_max - tolerance
    ]

    left = max(
        left_candidates,
        key=lambda i: (
            stats[i]["straightness"],
            stats[i][extent_key],
            stats[i]["length"],
        ),
    )
    right_pool = [i for i in right_candidates if i != left]
    if not right_pool:
        right_pool = [i for i in candidates if i != left]
    if not right_pool:
        return stats[left]["angle"], "single outer stave fallback"

    right = max(
        right_pool,
        key=lambda i: (
            stats[i]["straightness"],
            stats[i][extent_key],
            stats[i]["length"],
        ),
    )

    axis = _axial_mean_angle([stats[left]["angle"], stats[right]["angle"]])
    sideways_d = sideways and abs(math.cos(axis)) >= math.cos(math.radians(25.0))
    return (
        axis,
        "sideways d outer horizontal staves" if sideways_d else "outermost long staves",
        sideways_d,
    )


def _extremal_centroids(strokes, fraction=0.12):
    pts = _all_points(strokes)
    if len(pts) < 2:
        return None, None

    ys = sorted(y for _, y in pts)
    n = max(1, int(math.ceil(len(pts) * fraction)))
    top_cut = ys[min(n - 1, len(ys) - 1)]
    bottom_cut = ys[max(0, len(ys) - n)]

    top = [p for p in pts if p[1] <= top_cut]
    bottom = [p for p in pts if p[1] >= bottom_cut]

    top_c = (
        sum(x for x, _ in top) / len(top),
        sum(y for _, y in top) / len(top),
    )
    bottom_c = (
        sum(x for x, _ in bottom) / len(bottom),
        sum(y for _, y in bottom) / len(bottom),
    )
    return top_c, bottom_c


def _extremal_axis(strokes, fraction=0.12):
    top, bottom = _extremal_centroids(strokes, fraction)
    if top is None or bottom is None:
        return None
    return math.atan2(bottom[1] - top[1], bottom[0] - top[0])


def _horizontal_extremal_axis(strokes, fraction=0.12):
    pts = _all_points(strokes)
    if len(pts) < 2:
        return None

    xs = sorted(x for x, _ in pts)
    n = max(1, int(math.ceil(len(pts) * fraction)))
    left_cut = xs[min(n - 1, len(xs) - 1)]
    right_cut = xs[max(0, len(xs) - n)]

    left = [p for p in pts if p[0] <= left_cut]
    right = [p for p in pts if p[0] >= right_cut]

    lx = sum(x for x, _ in left) / len(left)
    ly = sum(y for _, y in left) / len(left)
    rx = sum(x for x, _ in right) / len(right)
    ry = sum(y for _, y in right) / len(right)
    return math.atan2(ry - ly, rx - lx)


# ---------------------------------------------------------------------------
# Intersections and junctions
# ---------------------------------------------------------------------------

def _segment_intersection(a, b, c, d):
    x1, y1 = a
    x2, y2 = b
    x3, y3 = c
    x4, y4 = d

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) < 1e-10:
        return None

    px = (
        (x1 * y2 - y1 * x2) * (x3 - x4)
        - (x1 - x2) * (x3 * y4 - y3 * x4)
    ) / denominator
    py = (
        (x1 * y2 - y1 * x2) * (y3 - y4)
        - (y1 - y2) * (x3 * y4 - y3 * x4)
    ) / denominator

    def within(value, a0, a1):
        return min(a0, a1) - 1e-8 <= value <= max(a0, a1) + 1e-8

    if (
        within(px, x1, x2)
        and within(py, y1, y2)
        and within(px, x3, x4)
        and within(py, y3, y4)
    ):
        return px, py
    return None


def _intersection_records(strokes):
    """Return geometric intersections with involved stroke indices."""
    records = []
    for i in range(len(strokes)):
        for j in range(i + 1, len(strokes)):
            for a, b in zip(strokes[i][:-1], strokes[i][1:]):
                for c, d in zip(strokes[j][:-1], strokes[j][1:]):
                    point = _segment_intersection(a, b, c, d)
                    if point is None:
                        continue

                    existing = None
                    for rec in records:
                        if math.hypot(
                            point[0] - rec["point"][0],
                            point[1] - rec["point"][1],
                        ) < 0.025:
                            existing = rec
                            break

                    if existing:
                        existing["strokes"].update((i, j))
                    else:
                        records.append({
                            "point": point,
                            "strokes": {i, j},
                        })
    return records


def _endpoint_clusters(strokes, threshold=0.12):
    endpoints = []
    for stroke_index, stroke in enumerate(strokes):
        if len(stroke) >= 2:
            endpoints.append((stroke[0][0], stroke[0][1], stroke_index))
            endpoints.append((stroke[-1][0], stroke[-1][1], stroke_index))

    groups = []
    for endpoint in endpoints:
        placed = False
        for group in groups:
            gx = sum(x[0] for x in group) / len(group)
            gy = sum(x[1] for x in group) / len(group)
            if math.hypot(endpoint[0] - gx, endpoint[1] - gy) <= threshold:
                group.append(endpoint)
                placed = True
                break
        if not placed:
            groups.append([endpoint])
    return groups


def _junction_records(strokes):
    """Combine true crossings and close endpoint junctions."""
    records = _intersection_records(strokes)

    for group in _endpoint_clusters(strokes):
        stroke_ids = {item[2] for item in group}
        if len(stroke_ids) < 2:
            continue

        point = (
            sum(item[0] for item in group) / len(group),
            sum(item[1] for item in group) / len(group),
        )
        existing = None
        for rec in records:
            if math.hypot(
                point[0] - rec["point"][0],
                point[1] - rec["point"][1],
            ) < 0.04:
                existing = rec
                break

        if existing:
            existing["strokes"].update(stroke_ids)
        else:
            records.append({"point": point, "strokes": stroke_ids})

    return records


# ---------------------------------------------------------------------------
# Grapheme-specific rules
# ---------------------------------------------------------------------------

def _o_structural_axis_canonical(strokes):
    """Estimate o from a loop/diamond axis plus the bisector of two tails.

    Input is expected in a *canonical vertical frame*: the loop is above the
    tails.  The routine deliberately avoids inscription-specific landmarks.

    1. locate the structural junction where the loop closes and the two tails
       continue;
    2. fit the centre-line of the upper loop/diamond from horizontal slices;
    3. estimate two tail trajectories immediately below the junction and take
       their directional bisector;
    4. take the axial consensus of loop axis and tail bisector.
    """
    pts = _all_points(strokes)
    if not pts:
        return None, "o no points"

    xmin, ymin, xmax, ymax = _bounds(strokes)
    width = max(xmax - xmin, 1e-9)
    height = max(ymax - ymin, 1e-9)
    scale = max(width, height)

    # --- structural loop/tail junction ---------------------------------
    records = _junction_records(strokes)
    candidates = []
    for rec in records:
        xj, yj = rec["point"]
        involved = [strokes[i] for i in rec["strokes"] if i < len(strokes)]
        involved_pts = [p for st in involved for p in st]
        if not involved_pts:
            continue
        above = yj - min(y for _, y in involved_pts)
        below = max(y for _, y in involved_pts) - yj
        if above >= 0.22 * height and below >= 0.10 * height:
            # Prefer a junction with a substantial loop above and two useful
            # continuations below; among those, the lower junction is the
            # natural bottom point of the upper diamond.
            candidates.append((yj, above + below, rec))

    if not candidates:
        return None, "o no loop-tail junction"

    _, _, junction = max(candidates, key=lambda item: (item[0], item[1]))
    xj, yj = junction["point"]

    # --- diamond / upper-loop centre-line ------------------------------
    def horizontal_intersections(y):
        xs = []
        for stroke in strokes:
            for p1, p2 in zip(stroke, stroke[1:]):
                x1, y1 = p1
                x2, y2 = p2
                # Ignore material clearly below the loop/tail junction.
                if min(y1, y2) > yj + 0.025 * height:
                    continue
                if abs(y2 - y1) < 1e-12:
                    if abs(y - y1) <= 0.006 * height:
                        xs.extend((x1, x2))
                    continue
                if min(y1, y2) <= y <= max(y1, y2):
                    t = (y - y1) / (y2 - y1)
                    if -1e-9 <= t <= 1.0 + 1e-9:
                        xs.append(x1 + t * (x2 - x1))
        return sorted(xs)

    loop_top = min(y for _, y in pts if y <= yj + 0.025 * height)
    loop_h = max(yj - loop_top, 1e-9)
    centres = []
    for i in range(1, 18):
        y = loop_top + i * loop_h / 18.0
        xs = horizontal_intersections(y)
        if len(xs) >= 2:
            # The lateral envelope is what a visually fitted diamond uses.
            centres.append(((xs[0] + xs[-1]) / 2.0, y))

    loop_axis = None
    if len(centres) >= 4:
        loop_axis = _fit_axis(centres)
    elif len(centres) >= 2:
        loop_axis = math.atan2(
            centres[-1][1] - centres[0][1],
            centres[-1][0] - centres[0][0],
        )
    else:
        # Conservative fallback: reconstructed loop centre to junction.
        upper = [p for p in pts if p[1] <= yj - 0.12 * height]
        if upper:
            top_band_limit = min(y for _, y in upper) + 0.18 * loop_h
            top_band = [p for p in upper if p[1] <= top_band_limit]
            if top_band:
                tx = sum(x for x, _ in top_band) / len(top_band)
                ty = sum(y for _, y in top_band) / len(top_band)
                loop_axis = math.atan2(yj - ty, xj - tx)

    # --- two lower tail trajectories ----------------------------------
    tail_candidates = []
    for idx, stroke in enumerate(strokes):
        if len(stroke) < 2:
            continue

        # A tail must approach the junction and then extend appreciably below
        # it.  Use only the proximal lower portion, so distant curvature or an
        # unusually long terminal hook does not dominate its trajectory.
        dmin = min(math.hypot(x - xj, y - yj) for x, y in stroke)
        ys_below = [y for _, y in stroke if y >= yj - 0.015 * height]
        if not ys_below or max(ys_below) - yj < 0.10 * height:
            continue
        if dmin > 0.11 * scale:
            continue

        lower = [(x, y) for x, y in stroke if y >= yj - 0.02 * height]
        if len(lower) < 2:
            continue
        max_y = max(y for _, y in lower)
        proximal_limit = yj + 0.60 * (max_y - yj)
        proximal = [(x, y) for x, y in lower if y <= proximal_limit + 1e-12]
        if len(proximal) < 2:
            proximal = lower[:]

        axis = _fit_axis(proximal)
        # Turn undirected fitted axis into a vector that points downward.
        vx, vy = math.cos(axis), math.sin(axis)
        if vy < 0:
            vx, vy = -vx, -vy
        vertical_progress = max_y - yj
        tail_candidates.append((vertical_progress, idx, vx, vy))

    # Prefer the two strongest distinct downward continuations.
    tail_candidates.sort(reverse=True)
    tail_axis = None
    if len(tail_candidates) >= 2:
        _, _, vx1, vy1 = tail_candidates[0]
        _, _, vx2, vy2 = tail_candidates[1]
        bx, by = vx1 + vx2, vy1 + vy2
        if math.hypot(bx, by) > 1e-9:
            tail_axis = math.atan2(by, bx)

    # --- consensus ------------------------------------------------------
    if loop_axis is not None and tail_axis is not None:
        axis = _axial_mean_angle([loop_axis, tail_axis])
        return axis, "o diamond + tail-bisector consensus"
    if loop_axis is not None:
        return loop_axis, "o diamond-axis fallback"
    if tail_axis is not None:
        return tail_axis, "o tail-bisector fallback"
    return None, "o no structural axis"


def _rotate_for_o_canonical(strokes, quarter_turn):
    """Rotate coordinates about their centroid for temporary o analysis."""
    return _rotate(strokes, quarter_turn)


def _o_axis_rule_target(strokes, stats):
    """Generalized o rule: same structure for vertical and sideways variants.

    Ordinary o is analysed directly in a vertical frame.  A strongly sideways
    o is temporarily quarter-turned into that same frame, analysed by the exact
    same diamond+tails rule, and its estimated axis is transformed back.  Thus
    the two variants differ only in target orientation, not in structural logic.
    """
    xmin, ymin, xmax, ymax = _bounds(strokes)
    width = max(xmax - xmin, 1e-9)
    height = max(ymax - ymin, 1e-9)

    if width >= 1.20 * height:
        # Himmelstalund-like sideways o.  Try both quarter-turn directions;
        # whichever produces the more credible canonical loop/tail structure
        # is accepted.  In practice this also handles mirror-side tail placement.
        attempts = []
        for q in (math.pi / 2, -math.pi / 2):
            canonical = _rotate_for_o_canonical(strokes, q)
            axis_c, rule = _o_structural_axis_canonical(canonical)
            if axis_c is None:
                continue
            # Transform axis back to original coordinates.
            axis_original = axis_c - q
            # Prefer a result whose recovered axis is intrinsically horizontal.
            horiz = abs(math.cos(axis_original))
            attempts.append((horiz, axis_original, rule))
        if attempts:
            _, axis, rule = max(attempts, key=lambda item: item[0])
            return axis, rule + " [sideways]", "horizontal", 55.0
        return (
            _horizontal_extremal_axis(strokes),
            "o sideways structural fallback",
            "horizontal",
            55.0,
        )

    axis, rule = _o_structural_axis_canonical(strokes)
    return axis, rule, "vertical", 35.0


def _g_axis(strokes):
    """g: mean of the left and right side axes from upper/lower extrema."""
    pts = _all_points(strokes)
    if len(pts) < 4:
        return _extremal_axis(strokes)

    ys = sorted(y for _, y in pts)
    n = max(2, int(math.ceil(len(pts) * 0.18)))
    top = [p for p in pts if p[1] <= ys[min(n - 1, len(ys) - 1)]]
    bottom = [p for p in pts if p[1] >= ys[max(0, len(ys) - n)]]
    if not top or not bottom:
        return _extremal_axis(strokes)

    left_top = min(top, key=lambda p: p[0])
    right_top = max(top, key=lambda p: p[0])
    left_bottom = min(bottom, key=lambda p: p[0])
    right_bottom = max(bottom, key=lambda p: p[0])

    left_axis = math.atan2(
        left_bottom[1] - left_top[1],
        left_bottom[0] - left_top[0],
    )
    right_axis = math.atan2(
        right_bottom[1] - right_top[1],
        right_bottom[0] - right_top[0],
    )
    return _axial_mean_angle([left_axis, right_axis])

def _line_intersection_infinite(p1, v1, p2, v2):
    """Intersection of two infinite parametric lines, or None if near-parallel."""
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    if abs(cross) < 1e-6:
        return None
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    t = (dx * v2[1] - dy * v2[0]) / cross
    return (p1[0] + t * v1[0], p1[1] + t * v1[1])


def _k_two_arm_bisector(strokes):
    """Structural symmetry axis for two-arm angular k forms.

    The two stroke trajectories are fitted from the apex-side 45% of each arm.
    Their fitted lines are virtually extended to an apex and the internal
    angular bisector is used as the intrinsic axis.  This is independent of arm
    length and works for <, >, ^ and v (and their mirrored counterparts).
    """
    if len(strokes) != 2 or any(len(st) < 2 for st in strokes):
        return None

    xmin, ymin, xmax, ymax = _bounds(strokes)
    scale = max(math.hypot(xmax - xmin, ymax - ymin), 1e-9)

    # Choose the pair of endpoints that most plausibly faces the virtual apex.
    endpoint_pairs = []
    for ea, pa in enumerate((tuple(strokes[0][0]), tuple(strokes[0][-1]))):
        for eb, pb in enumerate((tuple(strokes[1][0]), tuple(strokes[1][-1]))):
            endpoint_pairs.append((math.hypot(pa[0]-pb[0], pa[1]-pb[1]), ea, eb, pa, pb))
    _, ea, eb, pa, pb = min(endpoint_pairs, key=lambda item: item[0])

    def proximal(stroke, end_index, fraction=0.45):
        pts = list(stroke if end_index == 0 else reversed(stroke))
        if len(pts) <= 2:
            return pts
        # Select by accumulated arclength so digitisation density is irrelevant.
        total = _polyline_length(pts)
        limit = max(fraction * total, 1e-9)
        out = [pts[0]]
        acc = 0.0
        for a, b in zip(pts, pts[1:]):
            seg = math.hypot(b[0]-a[0], b[1]-a[1])
            acc += seg
            out.append(b)
            if acc >= limit:
                break
        return out

    prox_a = proximal(strokes[0], ea)
    prox_b = proximal(strokes[1], eb)
    if len(prox_a) < 2 or len(prox_b) < 2:
        return None

    axis_a = _fit_axis(prox_a)
    axis_b = _fit_axis(prox_b)
    va = (math.cos(axis_a), math.sin(axis_a))
    vb = (math.cos(axis_b), math.sin(axis_b))
    ca = (sum(x for x, _ in prox_a)/len(prox_a), sum(y for _, y in prox_a)/len(prox_a))
    cb = (sum(x for x, _ in prox_b)/len(prox_b), sum(y for _, y in prox_b)/len(prox_b))
    apex = _line_intersection_infinite(ca, va, cb, vb)
    if apex is None:
        return None

    # Reject intersections implausibly remote from the observed arms.
    near_mid = ((pa[0]+pb[0])/2.0, (pa[1]+pb[1])/2.0)
    if math.hypot(apex[0]-near_mid[0], apex[1]-near_mid[1]) > 0.75 * scale:
        return None

    # Point each fitted trajectory away from the virtual apex, then bisect them.
    def outward_vector(prox, axis):
        far = max(prox, key=lambda p: math.hypot(p[0]-apex[0], p[1]-apex[1]))
        vx, vy = math.cos(axis), math.sin(axis)
        if vx*(far[0]-apex[0]) + vy*(far[1]-apex[1]) < 0:
            vx, vy = -vx, -vy
        return vx, vy

    va = outward_vector(prox_a, axis_a)
    vb = outward_vector(prox_b, axis_b)
    dot = max(-1.0, min(1.0, va[0]*vb[0] + va[1]*vb[1]))
    opening = math.degrees(math.acos(dot))
    if opening < 20.0 or opening > 160.0:
        return None
    bx, by = va[0] + vb[0], va[1] + vb[1]
    if math.hypot(bx, by) < 1e-9:
        return None
    axis = math.atan2(by, bx)

    # < and > have horizontal symmetry axes; ^ and v vertical ones.
    hcorr = abs(_target_rotation(axis, "horizontal"))
    vcorr = abs(_target_rotation(axis, "vertical"))
    target = "horizontal" if hcorr <= vcorr else "vertical"
    return axis, target


def _k_curved_open_axis(strokes):
    """Symmetry axis for a single curved open k: ( or )."""
    if len(strokes) != 1 or len(strokes[0]) < 4:
        return None
    st = strokes[0]
    p0, p1 = tuple(st[0]), tuple(st[-1])
    vx, vy = p1[0]-p0[0], p1[1]-p0[1]
    chord = math.hypot(vx, vy)
    if chord < 1e-9:
        return None
    # Signed perpendicular deviation from endpoint chord.
    deviations = []
    for p in st[1:-1]:
        d = (vx*(p[1]-p0[1]) - vy*(p[0]-p0[0])) / chord
        deviations.append((abs(d), d, p))
    if not deviations:
        return None
    max_dev = max(item[0] for item in deviations)
    xmin, ymin, xmax, ymax = _bounds(strokes)
    scale = max(xmax-xmin, ymax-ymin, 1e-9)
    if max_dev < 0.10 * scale:
        return None
    # Use the high-deviation band only to determine which side of the chord
    # contains the bow.  The symmetry-axis *angle* itself is the exact
    # perpendicular to the endpoint chord through its midpoint.  This prevents
    # asymmetric curvature or uneven digitisation from tilting the axis.
    band = [(d, p) for ad, d, p in deviations if ad >= 0.80 * max_dev]
    mean_signed_dev = sum(d for d, _p in band) / len(band)

    # A perpendicular to chord vector (vx, vy) is (-vy, vx).  Choose its
    # polarity toward the observed bulge; polarity is conceptually useful even
    # though the downstream orientation comparison treats axes axially.
    px, py = -vy, vx
    if mean_signed_dev < 0.0:
        px, py = -px, -py
    axis = math.atan2(py, px)
    return axis, "horizontal"


def _k_axis_rule_target(strokes, stats):
    """Generalized k: angular/curved open symmetry, Y, stave, then fallback."""
    # Open two-arm family: <, >, ^, v.  Fit proximal trajectories, virtually
    # extend them to an apex, and use their angular bisector.
    angular = _k_two_arm_bisector(strokes)
    if angular is not None:
        axis, target = angular
        return axis, "k angular virtual-apex bisector", target, 55.0

    # Curved open family: ( / ).  Endpoint chord midpoint -> robust maximum
    # bulge is the curved analogue of an angular bisector.
    curved = _k_curved_open_axis(strokes)
    if curved is not None:
        axis, target = curved
        return axis, "k curved chord-perpendicular symmetry", target, 55.0

    endpoint_groups = _endpoint_clusters(strokes, threshold=0.14)

    # Y type: identify a junction and choose the stem topologically.
    junctions = [g for g in endpoint_groups if len({e[2] for e in g}) >= 3]
    if junctions and len(strokes) >= 3:
        junction = max(junctions, key=lambda g: len({e[2] for e in g}))
        jp = (sum(e[0] for e in junction)/len(junction), sum(e[1] for e in junction)/len(junction))
        ids = sorted({e[2] for e in junction})
        free = []
        for si in ids:
            st = strokes[si]
            if len(st) < 2:
                continue
            ends = [(st[0][0], st[0][1]), (st[-1][0], st[-1][1])]
            p = max(ends, key=lambda q: math.hypot(q[0]-jp[0], q[1]-jp[1]))
            vx, vy = p[0]-jp[0], p[1]-jp[1]
            norm = max(math.hypot(vx, vy), 1e-9)
            free.append((p, (vx/norm, vy/norm)))
        if len(free) >= 3:
            best = None
            for i, (p, v) in enumerate(free):
                others = [free[j][1] for j in range(len(free)) if j != i]
                best_pair = None
                for a in range(len(others)):
                    for b in range(a+1, len(others)):
                        dot = max(-1.0, min(1.0, others[a][0]*others[b][0] + others[a][1]*others[b][1]))
                        ang = math.acos(dot)
                        if best_pair is None or ang < best_pair[0]:
                            best_pair = (ang, others[a], others[b])
                if best_pair is None:
                    continue
                _, va, vb = best_pair
                bx, by = va[0]+vb[0], va[1]+vb[1]
                bn = math.hypot(bx, by)
                if bn < 1e-9:
                    continue
                opposite = (-bx/bn, -by/bn)
                score = v[0]*opposite[0] + v[1]*opposite[1]
                if best is None or score > best[0]:
                    best = (score, p)
            if best is not None and best[0] >= 0.55:
                stem_tip = best[1]
                axis = math.atan2(stem_tip[1]-jp[1], stem_tip[0]-jp[0])
                return axis, "k-Y mirror-invariant stem", "vertical", 55.0

    # Strong stave type.
    _, ymin, _, ymax = _bounds(strokes)
    total_h = max(ymax-ymin, 1e-9)
    stave_candidates = [i for i, st in enumerate(stats)
                        if st["vertical_extent"] >= 0.62*total_h and st["straightness"] >= 0.78]
    if stave_candidates:
        idx = max(stave_candidates, key=lambda i: (stats[i]["vertical_extent"], stats[i]["straightness"], stats[i]["chord"]))
        return stats[idx]["angle"], "k-stave", "vertical", 40.0

    return _extremal_axis(strokes), "k generic fallback", "vertical", 35.0

def _j_tip_extremal_axis(strokes):
    """Vertical extremal axis for j, using stroke tips only."""
    tips = []
    for stroke in strokes:
        if not stroke:
            continue
        tips.append(tuple(stroke[0]))
        if len(stroke) > 1:
            tips.append(tuple(stroke[-1]))
    if len(tips) < 2:
        return _extremal_axis(strokes)

    ymin = min(y for _, y in tips)
    ymax = max(y for _, y in tips)
    height = max(ymax - ymin, 1e-9)
    tol = 0.02 * height
    top = [p for p in tips if p[1] <= ymin + tol]
    bottom = [p for p in tips if p[1] >= ymax - tol]
    top_c = (
        sum(x for x, _ in top) / len(top),
        sum(y for _, y in top) / len(top),
    )
    bottom_c = (
        sum(x for x, _ in bottom) / len(bottom),
        sum(y for _, y in bottom) / len(bottom),
    )
    return math.atan2(
        bottom_c[1] - top_c[1],
        bottom_c[0] - top_c[0],
    )


def _j_open_horizontal_axis(strokes):
    """Return a horizontal axis for a clear open-horizontal j subtype.

    Supports both:
      1. two-stroke ^ / v components meeting at central junctions;
      2. single curved upper/lower strokes, as in Kalleby-like forms.

    In both cases the upper and lower components must define broadly parallel
    transverse axes and be clearly separated vertically.
    """
    if not strokes:
        return None

    xmin, ymin, xmax, ymax = _bounds(strokes)
    width = max(xmax - xmin, 1e-9)
    height = max(ymax - ymin, 1e-9)

    component_records = []

    # A. Explicit two-stroke ^ / v components meeting at a junction.
    groups = _endpoint_clusters(strokes, threshold=0.14)
    junctions = [g for g in groups if len({e[2] for e in g}) >= 2]

    used = set()
    for junction in junctions:
        stroke_ids = sorted({e[2] for e in junction})
        if len(stroke_ids) != 2:
            continue

        jx = sum(e[0] for e in junction) / len(junction)
        jy = sum(e[1] for e in junction) / len(junction)
        free = []
        for si in stroke_ids:
            stroke = strokes[si]
            if len(stroke) < 2:
                continue
            ends = [tuple(stroke[0]), tuple(stroke[-1])]
            free.append(max(
                ends,
                key=lambda p: math.hypot(p[0] - jx, p[1] - jy),
            ))

        if len(free) != 2:
            continue
        dx = free[1][0] - free[0][0]
        dy = free[1][1] - free[0][1]
        if math.hypot(dx, dy) < 0.20 * max(width, height):
            continue

        component_records.append({
            "axis": math.atan2(dy, dx),
            "cy": (free[0][1] + free[1][1]) / 2.0,
        })
        used.update(stroke_ids)

    # B. Single curved upper/lower components.
    # Use the chord between the two stroke tips as that component's
    # transverse axis. This captures Kalleby-like ∩ / ∪ components.
    for si, stroke in enumerate(strokes):
        if si in used or len(stroke) < 3:
            continue

        x0, y0 = stroke[0]
        x1, y1 = stroke[-1]
        chord = math.hypot(x1 - x0, y1 - y0)
        if chord < 0.28 * width:
            continue

        xs = [p[0] for p in stroke]
        ys = [p[1] for p in stroke]
        sx = max(xs) - min(xs)
        sy = max(ys) - min(ys)

        # The component should be clearly transverse rather than stave-like.
        if sx < 1.10 * max(sy, 1e-9):
            continue

        # Require visible curvature away from the endpoint chord.
        vx, vy = x1 - x0, y1 - y0
        max_dev = 0.0
        for px, py in stroke[1:-1]:
            dev = abs(vy * px - vx * py + x1 * y0 - y1 * x0) / max(chord, 1e-9)
            max_dev = max(max_dev, dev)
        if max_dev < 0.06 * height:
            continue

        component_records.append({
            "axis": math.atan2(y1 - y0, x1 - x0),
            "cy": sum(ys) / len(ys),
        })

    if len(component_records) < 2:
        return None

    # Pick the upper/lower pair with greatest vertical separation.
    best_pair = None
    best_sep = -1.0
    for i in range(len(component_records)):
        for j in range(i + 1, len(component_records)):
            a = component_records[i]
            b = component_records[j]
            sep = abs(a["cy"] - b["cy"])
            if sep > best_sep:
                best_sep = sep
                best_pair = (a, b)

    if best_pair is None or best_sep < 0.28 * height:
        return None

    a, b = best_pair
    disagreement = abs(
        ((a["axis"] - b["axis"] + math.pi / 2) % math.pi)
        - math.pi / 2
    )
    if disagreement > math.radians(40.0):
        return None

    return _axial_mean_angle([a["axis"], b["axis"]])



def _j_axis_rule_target(strokes, stats):
    """Conservative j derotation.

    A clearly detected open-horizontal subtype is horizontalized from the
    transverse axes of its upper and lower components. All other j forms,
    including zigzags, closed forms and open-vertical forms, are verticalized
    using the axis between the highest and lowest actual stroke tips.
    """
    open_axis = _j_open_horizontal_axis(strokes)
    if open_axis is not None:
        # Accept the open-horizontal interpretation only when it requires a
        # modest correction. Genuine examples such as Gallehus, Kalleby and
        # Øvre Stabu are already close to horizontal; large corrections are a
        # strong indication that another j subtype has been misclassified.
        open_correction = abs(_target_rotation(open_axis, "horizontal"))
        if open_correction <= math.radians(20.0):
            return (
                open_axis,
                "j open-horizontal component axes",
                "horizontal",
                20.0,
            )

    return (
        _j_tip_extremal_axis(strokes),
        "j stroke-tip extremal vertical",
        "vertical",
        90.0,
    )


# ---------------------------------------------------------------------------
# Rule dispatch
# ---------------------------------------------------------------------------

ORIENTATION_RULES = {
    "i": "longest stroke → vertical",
    "ï": "longest stroke → vertical",
    "l": "longest stroke → vertical",
    "z": "longest stroke → vertical",

    "f": "principal stave → vertical",
    "a": "principal stave → vertical",
    "t": "principal stave → vertical",
    "þ": "principal stave → vertical",
    "b": "principal stave → vertical",
    "p": "one main stave or mean of two main staves → vertical",
    "w": "principal stave → vertical",
    "n": "principal stave → vertical",
    "ng": "principal stave or frame side → vertical",

    "r": "leftmost straight stave → vertical",
    "u": "leftmost plausible stave → vertical",

    "d": "mean of outermost long staves → vertical; sideways subtype → horizontal",
    "h": "mean of two principal staves → vertical",
    "m": "mean of two principal staves → vertical",
    "e": "mean of two principal staves → vertical",

    "j": "ordinary extremal axis → vertical; wide subtype → horizontal",
    "s": "upper/lower extremal axis → vertical",

    "o": "ordinary crown/apex axis → vertical; sideways subtype → horizontal",
    "g": "mean side axes → vertical",

    "k": "mirror-invariant stave/Y/angle topology; angle subtype → horizontal",
}


def _alignment_spec(grapheme, strokes):
    """Return (axis, rule, target, maximum_correction_degrees)."""
    grapheme = unicodedata.normalize("NFC", str(grapheme or "").lower())
    if grapheme == "ï":
        grapheme = "i"
    if not strokes:
        return None, "none", "vertical", 0.0

    stats = [_stroke_stats(stroke) for stroke in strokes]

    if grapheme in {"i", "l", "z"}:
        axis, rule = _longest_stroke_axis(strokes, stats)
        return axis, rule, "vertical", 45.0

    if grapheme in {"f", "a", "t", "þ", "b", "w", "n", "ng"}:
        axis, rule = _principal_stave_axis(strokes, stats)
        if grapheme == "ng":
            rule = "ng principal stave or frame side"
        return axis, rule, "vertical", 40.0

    if grapheme == "p":
        axis, rule = _one_or_two_p_staves_axis(strokes, stats)
        return axis, rule, "vertical", 40.0

    if grapheme == "r":
        axis, rule = _leftmost_plausible_stave_axis(
            strokes, stats, "leftmost straight stave"
        )
        return axis, rule, "vertical", 35.0

    if grapheme == "u":
        axis, rule = _leftmost_plausible_stave_axis(
            strokes, stats, "leftmost u-stave"
        )
        return axis, rule, "vertical", 40.0

    if grapheme == "d":
        single = _confident_single_main_stave_axis(grapheme, strokes, stats)
        if single is not None:
            axis, rule = single
            return axis, rule, "vertical", 40.0
        axis, rule, sideways_d = _outermost_long_staves_axis(strokes, stats)
        # Conservative cap because d over-rotation was observed empirically.
        return axis, rule, "horizontal" if sideways_d else "vertical", 25.0

    if grapheme in {"h", "m", "e"}:
        if grapheme in {"m", "e"}:
            single = _confident_single_main_stave_axis(grapheme, strokes, stats)
            if single is not None:
                axis, rule = single
                return axis, rule, "vertical", 35.0
        axis, rule = _mean_two_principal_axes(strokes, stats)
        return axis, rule, "vertical", 35.0

    if grapheme == "j":
        return _j_axis_rule_target(strokes, stats)

    if grapheme == "s":
        return _extremal_axis(strokes), "s extremal vertical", "vertical", 40.0

    if grapheme == "o":
        return _o_axis_rule_target(strokes, stats)

    if grapheme == "g":
        return _g_axis(strokes), "mean side axes", "vertical", 40.0

    if grapheme == "k":
        return _k_axis_rule_target(strokes, stats)

    return (
        _extremal_axis(strokes),
        "generic extremal fallback",
        "vertical",
        35.0,
    )


def alignment_axis(grapheme, strokes):
    """Backward-compatible API: return only (axis_angle, rule_name)."""
    axis, rule, _target, _limit = _alignment_spec(grapheme, strokes)
    return axis, rule


def align_unit(unit):
    """Return a copied normalized rune unit after orientation correction."""
    corrected = dict(unit)
    strokes = [
        [tuple(point) for point in stroke]
        for stroke in unit.get("strokes", [])
    ]
    corrected["strokes"] = strokes

    axis, rule, target, max_correction = _alignment_spec(
        unit.get("grapheme", ""),
        strokes,
    )
    corrected["alignment_rule"] = rule
    corrected["alignment_target"] = target

    if axis is None:
        corrected["alignment_angle_deg"] = 0.0
        corrected["alignment_applied"] = False
        corrected["alignment_warning"] = "No reliable axis found"
        return corrected

    rotation = _target_rotation(axis, target)
    rotation_deg = math.degrees(rotation)

    # Safety guard against catastrophic automatic over-rotation.
    if abs(rotation_deg) > max_correction:
        corrected["alignment_angle_deg"] = 0.0
        corrected["alignment_applied"] = False
        corrected["alignment_warning"] = (
            f"Correction {rotation_deg:.1f}° exceeded "
            f"{max_correction:.1f}° safety limit"
        )
        return corrected

    corrected["strokes"] = _renormalize(_rotate(strokes, rotation))
    corrected["alignment_angle_deg"] = rotation_deg
    corrected["alignment_applied"] = True
    corrected["alignment_warning"] = ""
    return corrected
