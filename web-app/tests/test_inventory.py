"""Tests for the MongoDB read helpers."""

# pylint: disable=missing-function-docstring

from datetime import datetime

from inventory import get_history, get_latest, serialize


def test_serialize_converts_datetime():
    record = {"timestamp": datetime(2026, 11, 20, 10, 0), "counts": {}}
    assert serialize(record)["timestamp"] == "2026-11-20T10:00:00"


def test_serialize_keeps_plain_timestamp():
    assert serialize({"timestamp": "already-a-string"})["timestamp"] == (
        "already-a-string"
    )


def test_get_latest_empty(collection):
    assert get_latest(collection) is None


def test_get_history_respects_limit(collection):
    collection.insert_many(
        [
            {"timestamp": datetime(2026, 11, 20, hour), "counts": {}}
            for hour in (9, 10, 11)
        ]
    )
    history = get_history(collection, limit=2)
    assert [r["timestamp"] for r in history] == [
        "2026-11-20T10:00:00",
        "2026-11-20T11:00:00",
    ]
