"""Detect refrigerator storage layers using a fine-tuned YOLO model."""

from io import BytesIO
from pathlib import Path


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "weights" / "fridge_layers.pt"

LAYER_CLASS_NAME = "layers"
DEFAULT_CONFIDENCE = 0.25
IMAGE_SIZE = 640


class LayerDetector:  # pylint: disable=too-few-public-methods
    """Detect refrigerator layers and expose their bounding boxes."""

    def __init__(self, model=None, model_path=DEFAULT_MODEL_PATH):
        """Initialize the detector with a trained layer detection model."""
        if model is None:
            from ultralytics import YOLO  # pylint: disable=import-outside-toplevel

            model = YOLO(str(model_path))

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

    def detect_layers(self, image_bytes, confidence=DEFAULT_CONFIDENCE):
        """Return image dimensions and detected layer bounding boxes."""
        if not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

        image = self._load_image(image_bytes)

        results = self.model.predict(
            image,
            conf=confidence,
            imgsz=IMAGE_SIZE,
            verbose=False,
        )

        layers = []

        for result in results:
            for box in result.boxes:
                class_name = result.names[int(box.cls.item())]

                if class_name != LAYER_CLASS_NAME:
                    continue

                layers.append(
                    {
                        "confidence": float(box.conf.item()),
                        "bbox": [float(value) for value in box.xyxy[0].tolist()],
                    }
                )

        return {
            "image_width": image.width,
            "image_height": image.height,
            "layers": layers,
        }
