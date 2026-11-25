"""Test layer occupancy using exported YOLO detection coordinates."""

import csv
from pathlib import Path

from occupancy import analyze_layer

BASE_DIR = Path(__file__).resolve().parent

CSV_PATH = BASE_DIR / "detection_outputs" / "YOLOm_ref_test.csv"

IMAGE_WIDTH = 723

IMAGE_HEIGHT = 900

CONFIDENCE_THRESHOLD = 0.10

EXCLUDED_CLASSES = {"refrigerator"}


def main():
    """Read detection coordinates and analyze a single layer."""

    boxes = []

    with CSV_PATH.open(
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            if float(row["confidence"]) < CONFIDENCE_THRESHOLD:
                continue

            if row["class"] in EXCLUDED_CLASSES:
                continue

            box = tuple(float(row[key]) for key in ("x1", "y1", "x2", "y2"))

            boxes.append(box)

    result = analyze_layer(
        layer_id="layer_01",
        bounds=(0, 0, IMAGE_WIDTH, IMAGE_HEIGHT),
        boxes=boxes,
    )

    print(f"Detected objects: {len(boxes)}")
    print(f"Layer area: {result['layer_area']:.2f} px²")
    print(f"Occupied area: {result['occupied_area']:.2f} px²")
    print(f"Occupancy: {result['occupancy_percent']:.2f}%")
    print(f"Status: {result['status']}")
    print(f"Alert: {result['alert']}")


if __name__ == "__main__":
    main()
