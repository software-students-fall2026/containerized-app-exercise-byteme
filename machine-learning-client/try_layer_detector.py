"""Test the trained refrigerator layer detection model."""

from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "weights/fridge_layers.pt"

IMAGE_PATH = BASE_DIR / "fixtures/refrigerator_sample.jpg"


def main():
    """Run layer detection on a sample refrigerator image."""

    model = YOLO(str(MODEL_PATH))

    print("Model classes:", model.names)

    results = model.predict(
        source=str(IMAGE_PATH),
        conf=0.25,
        imgsz=640,
        device="cpu",
        save=True,
        project=str(BASE_DIR),
        name="layer_detection_test",
    )

    for result in results:
        print("Detected layers:", len(result.boxes))

        for box in result.boxes:
            bbox = box.xyxy[0].tolist()
            confidence = float(box.conf.item())

            print(f"BBox: {bbox}, " f"Confidence: {confidence:.4f}")


if __name__ == "__main__":
    main()
