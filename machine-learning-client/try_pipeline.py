"""Run an end-to-end test of the refrigerator analysis pipeline."""

import json
from pathlib import Path
from time import perf_counter

from detector import SnackDetector
from layer_detector import LayerDetector
from layer_assignment import assign_objects_to_layers, save_layer_records
from occupancy import analyze_layers


BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "fixtures/refrigerator_sample.jpg"
OUTPUT_DIR = BASE_DIR / "outputs"

OBJECT_CONFIDENCE = 0.10
LAYER_CONFIDENCE = 0.25
OVERLAP_THRESHOLD = 0.50


def save_json(data, filename):
    """Save JSON-compatible pipeline results."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    path = OUTPUT_DIR / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, allow_nan=False)

    return path


def print_results(layer_records, occupancy_results):
    """Display object assignments and occupancy results."""
    print("\n========== PIPELINE RESULTS ==========")

    for record, result in zip(layer_records, occupancy_results):
        print(f"\nLayer: {result['layer_id']}")
        print(f"Bounds: {result['bounds']}")
        print(f"Layer confidence: {record['confidence']:.4f}")

        objects = record["objects"]
        print(f"Objects detected: {len(objects)}")

        for obj in objects:
            print(f"  - {obj['class']}: " f"confidence={obj['confidence']:.4f}")

        print(f"Layer area: {result['layer_area']:.2f}")
        print(f"Occupied area: {result['occupied_area']:.2f}")
        print(f"Occupancy: {result['occupancy_percent']:.2f}%")
        print(f"Stock status: {result['status']}")
        print(f"Alert: {result['alert']}")


def main():
    """Execute all three refrigerator analysis modules."""
    total_start = perf_counter()

    print(f"Input image: {IMAGE_PATH}")
    image_bytes = IMAGE_PATH.read_bytes()

    # Initialize both YOLO models.
    print("\nInitializing models...")
    object_detector = SnackDetector()
    layer_detector = LayerDetector()

    # Module 1: Object detection.
    print("\n========== MODULE 1 ==========")
    start = perf_counter()

    object_detections = object_detector.detect_objects(
        image_bytes,
        confidence=OBJECT_CONFIDENCE,
    )

    object_count = len(object_detections["objects"])

    save_json(object_detections, "object_detections.json")

    print(f"Detected objects: {object_count}")
    print(f"Execution time: {perf_counter() - start:.3f}s")

    # Module 2A: Layer detection.
    print("\n========== MODULE 2A ==========")
    start = perf_counter()

    layer_detections = layer_detector.detect_layers(
        image_bytes,
        confidence=LAYER_CONFIDENCE,
    )

    layer_count = len(layer_detections["layers"])

    save_json(layer_detections, "layer_detections.json")

    print(f"Detected layers: {layer_count}")
    print(f"Execution time: {perf_counter() - start:.3f}s")

    if layer_count == 0:
        raise RuntimeError("No refrigerator layers detected")

    # Module 2B: Object-to-layer assignment.
    print("\n========== MODULE 2B ==========")
    start = perf_counter()

    layer_records = assign_objects_to_layers(
        object_detections,
        layer_detections,
        threshold=OVERLAP_THRESHOLD,
    )

    save_layer_records(
        layer_records,
        OUTPUT_DIR / "layer_records.json",
    )

    assigned_count = sum(len(layer["objects"]) for layer in layer_records)

    print(f"Layer records: {len(layer_records)}")
    print(f"Assigned objects: {assigned_count}")
    print(f"Unassigned objects: {object_count - assigned_count}")
    print(f"Execution time: {perf_counter() - start:.3f}s")

    # Module 3: Occupancy calculation.
    print("\n========== MODULE 3 ==========")
    start = perf_counter()

    occupancy_results = analyze_layers(layer_records)

    save_json(occupancy_results, "occupancy_results.json")

    print(f"Analyzed layers: {len(occupancy_results)}")
    print(f"Execution time: {perf_counter() - start:.3f}s")

    # Basic integration checks.
    assert len(layer_records) == layer_count
    assert len(occupancy_results) == layer_count
    assert assigned_count <= object_count

    assert all(0 <= result["occupancy_ratio"] <= 1 for result in occupancy_results)

    assert all(
        record["layer_id"] == result["layer_id"]
        for record, result in zip(layer_records, occupancy_results)
    )

    # Display final results.
    print_results(layer_records, occupancy_results)

    print("\n========== TEST SUMMARY ==========")
    print("All integration checks passed.")
    print(f"Total execution time: {perf_counter() - total_start:.3f}s")
    print(f"Results saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
