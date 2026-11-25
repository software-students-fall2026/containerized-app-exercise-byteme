"""Load and validate vending machine layout configurations."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Slot:
    """Represent a single vending machine slot."""

    slot_id: str
    product_name: str
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class MachineLayout:
    """Represent the layout of a vending machine."""

    machine_id: str
    layout_id: str
    slots: tuple[Slot, ...]

    def get_slot(self, slot_id: str) -> Slot:
        """Return a slot matching the given slot ID."""

        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot

        raise KeyError(f"Unknown slot ID: {slot_id}")


def validate_bbox(
    bbox: list[float] | None,
) -> tuple[float, float, float, float] | None:
    """Validate optional normalized bounding box coordinates."""

    if bbox is None:
        return None

    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError("Bounding box must contain four coordinates.")

    if not all(type(value) in (int, float) and 0.0 <= value <= 1.0 for value in bbox):
        raise ValueError("Coordinates must be between 0 and 1.")

    x1, y1, x2, y2 = bbox

    if x1 >= x2 or y1 >= y2:
        raise ValueError("Bounding box must have a positive area.")

    return x1, y1, x2, y2


def parse_slot(data: dict) -> Slot:
    """Create and validate a slot from configuration data."""

    slot_id = data["slot_id"]
    product_name = data["product_name"]

    if not isinstance(slot_id, str) or not slot_id.strip():
        raise ValueError("Slot ID must be a non-empty string.")

    if not isinstance(product_name, str) or not product_name.strip():
        raise ValueError("Product name must be a non-empty string.")

    return Slot(
        slot_id=slot_id,
        product_name=product_name,
        bbox=validate_bbox(data.get("bbox")),
    )


def load_layout(path: str | Path) -> MachineLayout:
    """Load a vending machine layout from a JSON file."""

    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    machine_id = data["machine_id"]
    layout_id = data["layout_id"]

    if not isinstance(machine_id, str) or not machine_id.strip():
        raise ValueError("Machine ID must be a non-empty string.")

    if not isinstance(layout_id, str) or not layout_id.strip():
        raise ValueError("Layout ID must be a non-empty string.")

    slots = tuple(parse_slot(item) for item in data["slots"])

    if not slots:
        raise ValueError("Machine layout must contain at least one slot.")

    slot_ids = [slot.slot_id for slot in slots]

    if len(slot_ids) != len(set(slot_ids)):
        raise ValueError("Duplicate slot IDs are not allowed.")

    return MachineLayout(
        machine_id=machine_id,
        layout_id=layout_id,
        slots=slots,
    )
