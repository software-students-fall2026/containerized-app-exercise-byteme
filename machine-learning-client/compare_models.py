"""Compare YOLO11 models on a vending machine image."""

from collections import Counter
from pathlib import Path
from time import perf_counter

from PIL import Image
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "fixtures/nyu_sample.jpg"
OUTPUT_DIR = BASE_DIR / "detection_outputs"

MODELS = ["yolo11n.pt", "yolo11s.pt", "yolo11m.pt"]
CONFIDENCE = 0.10
IMAGE_SIZE = 640


def main():
    """Compare YOLO models on the same vending machine image."""

    OUTPUT_DIR.mkdir(exist_ok=True)

    for model_name in MODELS:
        print(f"\n=== Testing {model_name} ===")

        model = YOLO(model_name)

        start = perf_counter()

        result = model.predict(
            source=str(IMAGE_PATH),
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            device="cpu",
            verbose=False,
        )[0]

        elapsed = perf_counter() - start

        counts = Counter(result.names[int(box.cls.item())] for box in result.boxes)

        print("Counts:", dict(counts))
        print(f"Elapsed time: {elapsed:.2f}s")

        annotated = result.plot()
        output_path = OUTPUT_DIR / f"{Path(model_name).stem}_result.jpg"

        Image.fromarray(annotated[:, :, ::-1]).save(output_path)

        print("Saved:", output_path)


if __name__ == "__main__":
    main()
