"""Tests for inventory database helpers."""

# pylint: disable=redefined-outer-name

from datetime import datetime, timezone
from unittest.mock import patch

import mongomock
import pytest

from db import get_collection, get_history, get_latest, save_record, serialize


@pytest.fixture
def collection():
    """Return an isolated fake inventory collection."""
    return mongomock.MongoClient(tz_aware=True).snack_tracker.inventory


def test_get_collection_uses_environment(monkeypatch):
    """Use the configured URI and agreed database names."""
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017")

    with patch("db.MongoClient") as mock_client:
        result = get_collection()

    mock_client.assert_called_once_with(
        "mongodb://example:27017",
        tz_aware=True,
        serverSelectionTimeoutMS=5000,
    )
    assert result is mock_client.return_value["snack_tracker"]["inventory"]


def test_save_record(collection):
    """Save counts with a UTC timestamp and return JSON-safe data."""
    result = save_record(collection, {"bottle": 2})
    stored = collection.find_one()

    assert collection.count_documents({}) == 1
    assert stored["counts"] == {"bottle": 2}
    assert isinstance(stored["timestamp"], datetime)
    assert stored["timestamp"].utcoffset().total_seconds() == 0
    assert result["counts"] == {"bottle": 2}
    assert "_id" not in result
    assert datetime.fromisoformat(result["timestamp"]).utcoffset().total_seconds() == 0


def test_serialize_preserves_original():
    """Convert a timestamp and remove ID without changing the input."""
    timestamp = datetime(2026, 11, 20, tzinfo=timezone.utc)
    record = {"_id": "internal", "timestamp": timestamp, "counts": {}}

    result = serialize(record)

    assert result == {"timestamp": timestamp.isoformat(), "counts": {}}
    assert record["_id"] == "internal"
    assert record["timestamp"] is timestamp


def test_serialize_naive_timestamp():
    """Treat MongoDB's naive datetimes as UTC."""
    result = serialize({"timestamp": datetime(2026, 11, 20)})
    assert result["timestamp"] == "2026-11-20T00:00:00+00:00"


def test_empty_collection(collection):
    """Return sensible results before any snapshots exist."""
    assert get_latest(collection) is None
    assert get_history(collection) == []


def test_latest_and_history(collection):
    """Choose the newest records and return history oldest first."""
    for hour in (11, 9, 10):
        collection.insert_one(
            {
                "timestamp": datetime(2026, 11, 20, hour, tzinfo=timezone.utc),
                "counts": {"bottle": hour},
            }
        )

    latest = get_latest(collection)
    history = get_history(collection, limit=2)

    assert latest["counts"] == {"bottle": 11}
    assert "_id" not in latest
    assert [record["counts"]["bottle"] for record in history] == [10, 11]
    assert all("_id" not in record for record in history)


@pytest.mark.parametrize("limit", [0, -1])
def test_history_rejects_invalid_limit(collection, limit):
    """Prevent nonpositive limits from returning unlimited history."""
    with pytest.raises(ValueError, match="at least 1"):
        get_history(collection, limit=limit)
