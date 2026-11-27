"""Unit tests for the YOLO snack detector."""

#  tests coverage 96%

import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from PIL import Image

from detector import SnackDetector


@pytest.fixture(name="image_bytes")
def sample_image_bytes():
    """Create valid image bytes for detector tests."""
    image = Image.new("RGB", (2, 2), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_mock_model(class_ids, names=None):
    """Create a fake YOLO model with predefined detections."""
    if names is None:
        names = {0: "bottle", 1: "cup", 2: "apple"}

    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.names = names

    boxes = []

    for class_id in class_ids:
        box = MagicMock()
        box.cls.item.return_value = class_id
        box.conf.item.return_value = 0.9
        box.xyxy[0].tolist.return_value = [0.1, 0.2, 1.5, 1.8]
        boxes.append(box)

    mock_result.boxes = boxes
    mock_model.predict.return_value = [mock_result]

    return mock_model


def test_count_multiple_classes(image_bytes):
    """Count multiple detected object classes."""
    model = make_mock_model([0, 0, 0, 1, 1])
    detector = SnackDetector(model=model)

    result = detector.detect_items(image_bytes)

    assert result == {"bottle": 3, "cup": 2}
    model.predict.assert_called_once()


def test_empty_detections(image_bytes):
    """Return an empty dictionary when no objects are found."""
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    result = detector.detect_items(image_bytes)

    assert isinstance(result, dict)
    assert not result


def test_single_class(image_bytes):
    """Count objects belonging to only one class."""
    model = make_mock_model([2, 2, 2, 2])
    detector = SnackDetector(model=model)

    result = detector.detect_items(image_bytes)

    assert result == {"apple": 4}


def test_empty_image():
    """Reject empty image bytes."""
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    with pytest.raises(ValueError, match="cannot be empty"):
        detector.detect_items(b"")

    model.predict.assert_not_called()


def test_invalid_image():
    """Reject bytes that are not a valid image."""
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    with pytest.raises(ValueError, match="Invalid image"):
        detector.detect_items(b"not an image")

    model.predict.assert_not_called()


def test_model_receives_rgb_image(image_bytes):
    """Ensure the model receives an RGB Pillow image."""
    model = make_mock_model([0])
    detector = SnackDetector(model=model)

    detector.detect_items(image_bytes)

    args, kwargs = model.predict.call_args
    assert isinstance(args[0], Image.Image)
    assert args[0].mode == "RGB"
    assert kwargs["verbose"] is False


def test_model_reused_between_calls(image_bytes):
    """Verify the same model instance handles multiple images."""
    model = make_mock_model([0])
    detector = SnackDetector(model=model)

    detector.detect_items(image_bytes)
    detector.detect_items(image_bytes)

    assert model.predict.call_count == 2
    assert detector.model is model


def test_detect_objects_returns_detection_data(image_bytes):
    """Return image dimensions and complete detection records."""
    model = make_mock_model([0, 1])
    detector = SnackDetector(model=model)

    result = detector.detect_objects(image_bytes)

    assert result["image_width"] == 2
    assert result["image_height"] == 2
    assert len(result["objects"]) == 2

    assert result["objects"][0] == {
        "class": "bottle",
        "confidence": 0.9,
        "bbox": [0.1, 0.2, 1.5, 1.8],
    }

    assert result["objects"][1]["class"] == "cup"
    model.predict.assert_called_once()


def test_detect_objects_confidence_parameter(image_bytes):
    """Pass the requested confidence threshold to YOLO."""
    model = make_mock_model([0])
    detector = SnackDetector(model=model)

    detector.detect_objects(
        image_bytes,
        confidence=0.35,
    )

    _, kwargs = model.predict.call_args

    assert kwargs["conf"] == 0.35
    assert kwargs["verbose"] is False


def test_detect_objects_default_confidence(image_bytes):
    """Use the default confidence threshold."""
    model = make_mock_model([0])
    detector = SnackDetector(model=model)

    detector.detect_objects(image_bytes)

    _, kwargs = model.predict.call_args

    assert kwargs["conf"] == 0.10


def test_detect_objects_empty_result(image_bytes):
    """Preserve image dimensions when no objects are detected."""
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    result = detector.detect_objects(image_bytes)

    assert result["image_width"] == 2
    assert result["image_height"] == 2
    assert isinstance(result["objects"], list)
    assert not result["objects"]


@pytest.mark.parametrize(
    "confidence",
    [-0.1, 1.1, float("nan")],
)
def test_detect_objects_invalid_confidence(image_bytes, confidence):
    """Reject invalid confidence thresholds."""
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    with pytest.raises(
        ValueError,
        match="Confidence must be between 0 and 1",
    ):
        detector.detect_objects(
            image_bytes,
            confidence=confidence,
        )

    model.predict.assert_not_called()


@pytest.mark.parametrize(
    "invalid_bytes, message",
    [
        (b"", "cannot be empty"),
        (b"not an image", "Invalid image"),
    ],
)
def test_detect_objects_invalid_image(invalid_bytes, message):
    """Reject empty or invalid image data."""
    model = make_mock_model([])
    detector = SnackDetector(model=model)

    with pytest.raises(ValueError, match=message):
        detector.detect_objects(invalid_bytes)

    model.predict.assert_not_called()


def test_save_detections(image_bytes, tmp_path):
    """Save detection results as a valid JSON file."""
    model = make_mock_model([0, 1])
    detector = SnackDetector(model=model)

    detections = detector.detect_objects(image_bytes)
    output_path = tmp_path / "detections.json"

    saved_path = detector.save_detections(
        detections,
        output_path,
    )

    assert saved_path == output_path
    assert output_path.is_file()

    with output_path.open("r", encoding="utf-8") as file:
        saved_data = json.load(file)

    assert saved_data == detections


def test_save_detections_creates_directory(tmp_path):
    """Create missing parent directories for JSON output."""
    detections = {
        "image_width": 2,
        "image_height": 2,
        "objects": [],
    }

    output_path = tmp_path / "results" / "fridge" / "test.json"

    saved_path = SnackDetector.save_detections(
        detections,
        output_path,
    )

    assert saved_path == output_path
    assert output_path.is_file()
    assert output_path.parent.is_dir()


def test_save_detections_rejects_nan(tmp_path):
    """Reject non-finite values in JSON detection data."""
    detections = {
        "confidence": float("nan"),
    }

    with pytest.raises(ValueError):
        SnackDetector.save_detections(
            detections,
            tmp_path / "invalid.json",
        )
