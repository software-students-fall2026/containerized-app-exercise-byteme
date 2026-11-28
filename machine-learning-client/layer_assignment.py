"""Assign detected objects to refrigerator storage layers."""

import json
from pathlib import Path

from occupancy import validate_box


DEFAULT_OVERLAP_THRESHOLD = 0.5


def box_area(box):
    """Calculate the area of an xyxy bounding box."""
    x1, y1, x2, y2 = validate_box(box)

    return (x2 - x1) * (y2 - y1)


def intersection_area(box_a, box_b):
    """Calculate the intersection area of two bounding boxes."""
    ax1, ay1, ax2, ay2 = validate_box(box_a)
    bx1, by1, bx2, by2 = validate_box(box_b)

    width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0.0, min(ay2, by2) - max(ay1, by1))

    return width * height


def overlap_ratio(object_box, layer_box):
    """Return the proportion of an object located inside a layer."""
    return intersection_area(object_box, layer_box) / box_area(object_box)


def vertical_center(box):
    """Return the vertical center coordinate of a bounding box."""
    _, y1, _, y2 = validate_box(box)

    return (y1 + y2) / 2


def sort_layers(layers):
    """Sort detected layers from top to bottom."""
    return sorted(
        layers,
        key=lambda layer: vertical_center(layer["bbox"]),
    )


def initialize_layer_records(layers):
    """Create ordered layer records with initially empty object lists."""
    records = []

    for index, layer in enumerate(sort_layers(layers), start=1):
        records.append(
            {
                "layer_id": f"layer_{index}",
                "bounds": list(validate_box(layer["bbox"])),
                "confidence": float(layer["confidence"]),
                "objects": [],
            }
        )

    return records


def find_best_layer(object_box, layers, threshold):
    """Find the layer containing the largest proportion of an object."""
    best_layer = None
    best_score = 0.0

    for layer in layers:
        score = overlap_ratio(object_box, layer["bounds"])

        if score > best_score:
            best_layer = layer
            best_score = score

    if best_score < threshold:
        return None

    return best_layer


def validate_image_dimensions(object_detections, layer_detections):
    """Ensure both detection results use the same image dimensions."""
    object_dimensions = (
        object_detections["image_width"],
        object_detections["image_height"],
    )

    layer_dimensions = (
        layer_detections["image_width"],
        layer_detections["image_height"],
    )

    if object_dimensions != layer_dimensions:
        raise ValueError("Object and layer image dimensions do not match")

    if any(dimension <= 0 for dimension in object_dimensions):
        raise ValueError("Image dimensions must be positive")


def assign_objects_to_layers(
    object_detections,
    layer_detections,
    threshold=DEFAULT_OVERLAP_THRESHOLD,
):
    """Group detected objects into ordered refrigerator layer records."""
    if not 0 <= threshold <= 1:
        raise ValueError("Overlap threshold must be between 0 and 1")

    validate_image_dimensions(object_detections, layer_detections)

    records = initialize_layer_records(layer_detections["layers"])

    for obj in object_detections["objects"]:
        object_box = validate_box(obj["bbox"])

        layer = find_best_layer(
            object_box,
            records,
            threshold,
        )

        if layer is not None:
            layer["objects"].append(
                {
                    **obj,
                    "bbox": list(object_box),
                }
            )

    return records


def save_layer_records(layers, output_path):
    """Save grouped layer records as a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(layers, file, indent=2, allow_nan=False)

    return path
