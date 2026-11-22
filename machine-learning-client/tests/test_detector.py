"""Unit tests for the YOLO snack detector."""
#  tests coverage 92%

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from PIL import Image

from detector import SnackDetector


# Create a valid image without using a real photo
@pytest.fixture
def image_bytes():
    image = Image.new("RGB", (2, 2), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# Create a fake YOLO model with predefined detections
def make_mock_model(class_ids, names=None):
    if names is None:
        names = {0: "bottle", 1: "cup", 2: "apple"}

    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.names = names

    boxes = []
    for class_id in class_ids:
        box = MagicMock()
        box.cls.item.return_value = class_id
        boxes.append(box)

    mock_result.boxes = boxes
    mock_model.predict.return_value = [mock_result]

    return mock_model


def test_count_multiple_classes(image_bytes):
    model = make_mock_model([0, 0, 0, 1, 1])
    detector = SnackDetector(model=model)

    result = detector.detect_items(image_bytes)

    assert result == {"bottle": 3, "cup": 2}
    model.predict.assert_called_once()


def test_empty_detections(image_bytes):
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    result = detector.detect_items(image_bytes)

    assert result == {}


def test_single_class(image_bytes):
    model = make_mock_model([2, 2, 2, 2])
    detector = SnackDetector(model=model)

    result = detector.detect_items(image_bytes)

    assert result == {"apple": 4}


# Reject empty image bytes
def test_empty_image():
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    with pytest.raises(ValueError, match="cannot be empty"):
        detector.detect_items(b"")

    model.predict.assert_not_called()


# Reject bytes that are not a valid image
def test_invalid_image():
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    with pytest.raises(ValueError, match="Invalid image"):
        detector.detect_items(b"not an image")

    model.predict.assert_not_called()


# Ensure the model receives an RGB Pillow image
def test_model_receives_rgb_image(image_bytes):
    model = make_mock_model([0])
    detector = SnackDetector(model=model)

    detector.detect_items(image_bytes)

    args, kwargs = model.predict.call_args
    assert isinstance(args[0], Image.Image)
    assert args[0].mode == "RGB"
    assert kwargs["verbose"] is False


# Verify the same model instance handles multiple images
def test_model_reused_between_calls(image_bytes):
    model = make_mock_model([0])
    detector = SnackDetector(model=model)

    detector.detect_items(image_bytes)
    detector.detect_items(image_bytes)

    assert model.predict.call_count == 2
    assert detector.model is model
