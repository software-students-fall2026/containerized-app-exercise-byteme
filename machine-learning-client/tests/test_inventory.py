"""Unit tests for inventory status processing."""

import pytest

from inventory import (
    StockStatus,
    build_inventory_result,
    collect_alerts,
    determine_status,
    should_alert,
)


@pytest.mark.parametrize(
    "class_name, expected",
    [
        ("empty", StockStatus.EMPTY),
        ("low_stock", StockStatus.LOW_STOCK),
        ("in_stock", StockStatus.IN_STOCK),
    ],
)
def test_valid_stock_status(class_name, expected):
    """Verify that valid predictions map to stock statuses."""

    assert determine_status(class_name, 0.95) == expected


def test_low_confidence():
    """Verify that uncertain predictions become unknown."""

    assert determine_status("empty", 0.30) == StockStatus.UNKNOWN


def test_confidence_boundary():
    """Verify that confidence equal to the threshold is accepted."""

    assert determine_status("empty", 0.70) == StockStatus.EMPTY


def test_custom_threshold():
    """Verify that a custom confidence threshold is respected."""

    result = determine_status("in_stock", 0.80, threshold=0.90)

    assert result == StockStatus.UNKNOWN


def test_unknown_class():
    """Verify that unsupported prediction classes become unknown."""

    assert determine_status("bottle", 0.95) == StockStatus.UNKNOWN


def test_class_name_normalization():
    """Verify that capitalization and whitespace are normalized."""

    assert determine_status(" EMPTY ", 0.95) == StockStatus.EMPTY


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan")])
def test_invalid_confidence(confidence):
    """Verify that invalid confidence values are rejected."""

    with pytest.raises(ValueError):
        determine_status("empty", confidence)


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_invalid_threshold(threshold):
    """Verify that invalid confidence thresholds are rejected."""

    with pytest.raises(ValueError):
        determine_status("empty", 0.95, threshold)


@pytest.mark.parametrize(
    "status, expected",
    [
        (StockStatus.EMPTY, True),
        (StockStatus.LOW_STOCK, True),
        (StockStatus.IN_STOCK, False),
        (StockStatus.UNKNOWN, False),
    ],
)
def test_should_alert(status, expected):
    """Verify alert rules for all supported stock statuses."""

    assert should_alert(status) is expected


def test_build_inventory_result():
    """Verify that predictions produce structured inventory results."""

    result = build_inventory_result(
        machine_id="machine_01",
        slot_id="201",
        product_name="Peach Tea",
        class_name="low_stock",
        confidence=0.92,
    )

    assert result.to_dict() == {
        "machine_id": "machine_01",
        "slot_id": "201",
        "product_name": "Peach Tea",
        "status": "low_stock",
        "confidence": 0.92,
        "alert": True,
    }


def test_collect_alerts():
    """Verify that only empty and low-stock slots generate alerts."""

    results = [
        build_inventory_result("machine_01", "201", "Tea", "empty", 0.95),
        build_inventory_result("machine_01", "202", "Water", "low_stock", 0.90),
        build_inventory_result("machine_01", "203", "Juice", "in_stock", 0.95),
        build_inventory_result("machine_01", "204", "Soda", "empty", 0.30),
    ]

    alerts = collect_alerts(results)

    assert len(alerts) == 2
    assert [item["slot_id"] for item in alerts] == ["201", "202"]


def test_collect_empty_alerts():
    """Verify that an empty result list generates no alerts."""

    assert not collect_alerts([])
