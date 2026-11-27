"""YOLO-based object detection for snack inventory tracking."""

import json
from collections import Counter
from io import BytesIO
from pathlib import Path


class SnackDetector:  # pylint: disable=too-few-public-methods
    """Detect objects and expose their original image coordinates"""

    def __init__(self, model=None, model_path="yolo11m.pt"):
        """Initialize the detector with a YOLO model"""
        if model is None:
            from ultralytics import YOLO  # pylint: disable=import-outside-toplevel

            model = YOLO(model_path)

        self.model = model

    @staticmethod
    def _load_image(image_bytes):
        """Decode image bytes into an RGB Pillow image."""
        if not image_bytes:
            raise ValueError("Image data cannot be empty")

        from PIL import Image  # pylint: disable=import-outside-toplevel

        try:
            with Image.open(BytesIO(image_bytes)) as image:
                image.load()
                return image.convert("RGB")
        except (OSError, ValueError) as exc:
            raise ValueError("Invalid image data") from exc

    def detect_items(self, image_bytes):
        """Return legacy object counts by class name."""
        image = self._load_image(image_bytes)
        counts = Counter()

        for result in self.model.predict(image, verbose=False):
            for box in result.boxes:
                counts[result.names[int(box.cls.item())]] += 1

        return dict(counts)

    def detect_objects(self, image_bytes, confidence=0.10):
        """Return image dimensions and JSON-compatible object detections."""
        if not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

        image = self._load_image(image_bytes)

        results = self.model.predict(
            image,
            conf=confidence,
            verbose=False,
        )

        objects = []

        for result in results:
            for box in result.boxes:
                objects.append(
                    {
                        "class": result.names[int(box.cls.item())],
                        "confidence": float(box.conf.item()),
                        "bbox": [float(value) for value in box.xyxy[0].tolist()],
                    }
                )

        return {
            "image_width": image.width,
            "image_height": image.height,
            "objects": objects,
        }

    @staticmethod
    def save_detections(detections, output_path):
        """Save detection data as JSON and return the output path."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(detections, file, indent=2, allow_nan=False)

        return path
