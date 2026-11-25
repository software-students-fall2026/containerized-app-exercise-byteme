"""Inspect YOLO detections on a real vending machine image."""

# Important: numpy < 2

import csv
from collections import Counter
from pathlib import Path

import pytest
from PIL import Image
from ultralytics import YOLO

from detector import SnackDetector

BASE_DIR = Path(__file__).resolve().parent

IMAGE_PATH = BASE_DIR / "fixtures" / "refrigerator_sample.jpg"

OUTPUT_DIR = BASE_DIR / "detection_outputs"

MODEL_PATH = "yolo11m.pt"

# Lower than the usual default to inspect weak detections.
CONFIDENCE = 0.10


def test_real_image():  # pylint: disable=too-many-locals
    """Run real detection and save visual diagnostics"""

    assert IMAGE_PATH.exists(), f"Image not found: {IMAGE_PATH}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_bytes = IMAGE_PATH.read_bytes()

    # Run the project's detector interface
    model = YOLO(MODEL_PATH)
    detector = SnackDetector(model=model)

    counts = detector.detect_items(image_bytes)

    print("\n=== PROJECT DETECTOR RESULT ===")
    print(counts)

    assert isinstance(counts, dict)

    # Run YOLO with a lower confidence threshold.
    results = model.predict(
        source=str(IMAGE_PATH),
        conf=CONFIDENCE,
        verbose=False,
    )

    result = results[0]

    # Extract individual detections.
    detections = []

    for box in result.boxes:
        class_id = int(box.cls.item())
        class_name = result.names[class_id]
        confidence = float(box.conf.item())

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        detections.append(
            {
                "class": class_name,
                "confidence": round(confidence, 4),
                "x1": round(x1, 1),
                "y1": round(y1, 1),
                "x2": round(x2, 1),
                "y2": round(y2, 1),
            }
        )

    # Print counts and detailed detections.
    visual_counts = Counter(item["class"] for item in detections)

    print("\n=== VISUALIZATION DETECTION COUNTS ===")
    print(dict(visual_counts))

    print("\n=== INDIVIDUAL DETECTIONS ===")

    for index, item in enumerate(detections, start=1):
        print(
            f"{index:02d}. "
            f"{item['class']:<15} "
            f"confidence={item['confidence']:.3f} "
            f"box=({item['x1']}, {item['y1']}, "
            f"{item['x2']}, {item['y2']})"
        )

    # Save annotated image.
    annotated = result.plot(
        conf=True,
        labels=True,
        line_width=2,
    )

    annotated_path = OUTPUT_DIR / "YOLOm_ref_test.jpg"

    Image.fromarray(annotated[:, :, ::-1]).save(annotated_path)

    # Save detections to CSV.
    csv_path = OUTPUT_DIR / "YOLOm_ref_test.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "class",
                "confidence",
                "x1",
                "y1",
                "x2",
                "y2",
            ],
        )
        writer.writeheader()
        writer.writerows(detections)

    print("\n=== OUTPUT FILES ===")
    print(f"Annotated image: {annotated_path}")
    print(f"Detection CSV:   {csv_path}")

    print("\n=== SUMMARY ===")
    print(f"Total detections: {len(detections)}")
    print(f"Classes: {dict(visual_counts)}")

    assert annotated_path.exists()
    assert csv_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
