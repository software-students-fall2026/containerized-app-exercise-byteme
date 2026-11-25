"""YOLO-based object detection for snack inventory tracking."""

from collections import Counter
from io import BytesIO


class SnackDetector:  # pylint: disable=too-few-public-methods
    """Detect and count objects in vending machine images"""

    def __init__(self, model=None, model_path="yolo11m.pt"):
        """Initialize the detector with a YOLO model"""
        if model is None:
            from ultralytics import YOLO  # pylint: disable=import-outside-toplevel

            model = YOLO(model_path)

        self.model = model

    def detect_items(self, image_bytes):
        """Return detected object counts by class name"""
        if not image_bytes:
            raise ValueError("Image data cannot be empty")

        from PIL import Image  # pylint: disable=import-outside-toplevel

        try:
            image = Image.open(BytesIO(image_bytes))
            image.load()
            image = image.convert("RGB")
        except (OSError, ValueError) as exc:
            raise ValueError("Invalid image data") from exc

        results = self.model.predict(image, verbose=False)
        counts = Counter()

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls.item())
                class_name = result.names[class_id]
                counts[class_name] += 1

        return dict(counts)
