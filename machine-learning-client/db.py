"""Save and retrieve snack inventory snapshots."""

import os
from datetime import datetime, timezone

from pymongo import MongoClient


def get_collection():
    """Connect to the inventory collection using MONGO_URI."""
    client = MongoClient(
        os.getenv("MONGO_URI", "mongodb://mongodb:27017"),
        tz_aware=True,
        serverSelectionTimeoutMS=5000,
    )
    return client["snack_tracker"]["inventory"]


def serialize(record):
    """Return a JSON-safe record without MongoDB's internal ID."""
    result = dict(record)
    result.pop("_id", None)

    timestamp = result.get("timestamp")
    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        result["timestamp"] = timestamp.astimezone(timezone.utc).isoformat()

    return result


def save_record(collection, counts):
    """Save one inventory snapshot and return its JSON-safe form."""
    record = {
        "timestamp": datetime.now(timezone.utc),
        "counts": dict(counts),
    }
    collection.insert_one(record)
    return serialize(record)


def get_latest(collection):
    """Return the latest snapshot, or None when inventory is empty."""
    record = collection.find_one(
        {},
        {"_id": 0},
        sort=[("timestamp", -1)],
    )
    return serialize(record) if record is not None else None


def get_history(collection, limit=100):
    """Return recent snapshots in oldest-to-newest order."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    cursor = collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return [serialize(record) for record in reversed(list(cursor))]
