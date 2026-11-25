"""Calculate layer occupancy from axis-aligned detection rectangles."""

from math import isfinite
from typing import Iterable

Box = tuple[float, float, float, float]


def validate_box(box: Iterable[float]) -> Box:
    """Validate an xyxy rectangle with finite coordinates and positive area."""
    x1, y1, x2, y2 = map(float, box)

    if not all(map(isfinite, (x1, y1, x2, y2))):
        raise ValueError("Coordinates must be finite.")

    if x1 >= x2 or y1 >= y2:
        raise ValueError("Rectangle must have positive area.")

    return x1, y1, x2, y2


def merge_intervals(intervals):
    """Merge overlapping one-dimensional intervals."""
    merged = []

    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])

    return merged


# pylint: disable=too-many-locals
def union_area(boxes: Iterable[Box], bounds: Box) -> float:
    """Compute rectangle union area clipped to the layer bounds."""
    left, top, right, bottom = validate_box(bounds)
    clipped = []

    # Clip object boxes to the layer boundaries.
    for box in boxes:
        x1, y1, x2, y2 = validate_box(box)

        rect = (
            max(left, x1),
            max(top, y1),
            min(right, x2),
            min(bottom, y2),
        )

        if rect[0] < rect[2] and rect[1] < rect[3]:
            clipped.append(rect)

    # Collect all horizontal boundary coordinates.
    edges = sorted({x for rect in clipped for x in (rect[0], rect[2])})

    area = 0.0

    # Calculate the union area of each vertical strip.
    for a, b in zip(edges, edges[1:]):
        intervals = merge_intervals(
            (y1, y2) for x1, y1, x2, y2 in clipped if x1 < b and x2 > a
        )

        area += (b - a) * sum(end - start for start, end in intervals)

    return area


def stock_status(ratio: float) -> str:
    """Map an unrounded occupancy ratio in [0, 1] to a stock status."""

    if not 0 <= ratio <= 1:
        raise ValueError("Occupancy ratio must be between 0 and 1.")

    if ratio == 0:
        return "empty"

    if ratio < 0.2:
        return "low_stock"

    if ratio < 0.8:
        return "medium_stock"

    if ratio < 1:
        return "high_stock"

    return "full"


def analyze_layer(
    layer_id: str,
    bounds: Box,
    boxes: Iterable[Box],
) -> dict:
    """Return JSON-compatible occupancy metrics for one known layer."""

    x1, y1, x2, y2 = validate_box(bounds)

    layer_area = (x2 - x1) * (y2 - y1)

    if not isfinite(layer_area) or layer_area <= 0:
        raise ValueError("Layer area must be finite and positive.")

    occupied_area = min(
        layer_area,
        union_area(boxes, (x1, y1, x2, y2)),
    )

    ratio = occupied_area / layer_area

    # Correct only floating-point noise at complete coverage.
    if 1 - ratio <= 1e-12:
        ratio = 1.0
        occupied_area = layer_area

    status = stock_status(ratio)

    return {
        "layer_id": layer_id,
        "bounds": [x1, y1, x2, y2],
        "layer_area": layer_area,
        "occupied_area": occupied_area,
        "occupancy_ratio": ratio,
        "occupancy_percent": ratio * 100,
        "status": status,
        "alert": status in ("empty", "low_stock"),
    }


def analyze_layers(layers: Iterable[dict]) -> list[dict]:
    """Analyze layer records containing layer_id, bounds and object records."""

    return [
        analyze_layer(
            layer["layer_id"],
            layer["bounds"],
            (obj["bbox"] for obj in layer["objects"]),
        )
        for layer in layers
    ]
