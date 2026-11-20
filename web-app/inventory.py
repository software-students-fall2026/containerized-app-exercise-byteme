"""Helpers for reading inventory records from MongoDB."""


def serialize(record):
    """Return a JSON-friendly copy of a record (datetime -> ISO string)."""
    result = dict(record)
    timestamp = result.get("timestamp")
    if hasattr(timestamp, "isoformat"):
        result["timestamp"] = timestamp.isoformat()
    return result


def get_history(collection, limit=100):
    """Return up to ``limit`` most recent records, oldest first."""
    cursor = collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return [serialize(record) for record in reversed(list(cursor))]


def get_latest(collection):
    """Return the most recent record, or None if there are no records."""
    record = collection.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])
    return serialize(record) if record else None
