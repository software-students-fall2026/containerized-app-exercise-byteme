"""Unit tests for vending machine layout configurations."""

import json

import pytest

from layout import load_layout, parse_slot, validate_bbox


def write_layout(path, slots):
    """Write a temporary machine layout for testing."""

    data = {
        "machine_id": "machine_01",
        "layout_id": "beverage_5x9",
        "slots": slots,
    }

    path.write_text(json.dumps(data), encoding="utf-8")

    return path


def test_load_layout(tmp_path):
    """Verify that a valid machine layout can be loaded."""

    path = write_layout(
        tmp_path / "layout.json",
        [
            {
                "slot_id": "201",
                "product_name": "Peach Tea",
                "bbox": [0.1, 0.2, 0.3, 0.4],
            },
            {
                "slot_id": "202",
                "product_name": "Water",
            },
        ],
    )

    layout = load_layout(path)

    assert layout.machine_id == "machine_01"
    assert layout.layout_id == "beverage_5x9"
    assert len(layout.slots) == 2
    assert layout.get_slot("201").product_name == "Peach Tea"
    assert layout.get_slot("202").bbox is None


def test_unknown_slot(tmp_path):
    """Verify that requesting an unknown slot raises an error."""

    path = write_layout(
        tmp_path / "layout.json",
        [{"slot_id": "201", "product_name": "Tea"}],
    )

    layout = load_layout(path)

    with pytest.raises(KeyError):
        layout.get_slot("999")


def test_duplicate_slot_ids(tmp_path):
    """Verify that duplicate slot IDs are rejected."""

    path = write_layout(
        tmp_path / "layout.json",
        [
            {"slot_id": "201", "product_name": "Tea"},
            {"slot_id": "201", "product_name": "Water"},
        ],
    )

    with pytest.raises(ValueError, match="Duplicate slot IDs"):
        load_layout(path)


def test_empty_layout(tmp_path):
    """Verify that a layout without slots is rejected."""

    path = write_layout(tmp_path / "layout.json", [])

    with pytest.raises(ValueError):
        load_layout(path)


def test_missing_layout(tmp_path):
    """Verify that missing configuration files raise an error."""

    with pytest.raises(FileNotFoundError):
        load_layout(tmp_path / "missing.json")


def test_valid_bbox():
    """Verify that valid normalized coordinates are accepted."""

    assert validate_bbox([0.1, 0.2, 0.3, 0.4]) == (
        0.1,
        0.2,
        0.3,
        0.4,
    )


def test_optional_bbox():
    """Verify that coordinates can be omitted."""

    assert validate_bbox(None) is None


@pytest.mark.parametrize(
    "bbox",
    [
        [0.1, 0.2, 0.3],
        [-0.1, 0.2, 0.3, 0.4],
        [0.1, 0.2, 1.2, 0.4],
        [0.4, 0.2, 0.1, 0.5],
        [0.1, 0.4, 0.3, 0.2],
        [0.1, 0.2, 0.1, 0.4],
        ["0.1", 0.2, 0.3, 0.4],
    ],
)
def test_invalid_bbox(bbox):
    """Verify that malformed bounding boxes are rejected."""

    with pytest.raises(ValueError):
        validate_bbox(bbox)


@pytest.mark.parametrize(
    "data",
    [
        {"slot_id": "", "product_name": "Tea"},
        {"slot_id": "201", "product_name": ""},
        {"slot_id": 201, "product_name": "Tea"},
    ],
)
def test_invalid_slot(data):
    """Verify that invalid slot metadata is rejected."""

    with pytest.raises(ValueError):
        parse_slot(data)
