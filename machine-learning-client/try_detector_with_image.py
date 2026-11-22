'''test the YOLO snack detector with real vending machine pictures, manual verification'''
# Important: required numpy < 2

from pathlib import Path
from detector import SnackDetector


def test_real_image():
    image_path = (
        Path(__file__).parent
        / "fixtures"
        / "test_sample.png"
    )

    detector = SnackDetector()
    image_bytes = image_path.read_bytes()

    counts = detector.detect_items(image_bytes)

    print("Detection result:", counts)

    assert isinstance(counts, dict)
    assert all(isinstance(v, int) for v in counts.values())