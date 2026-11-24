"""Helpers for reading inventory records from MongoDB."""

from datetime import datetime, timezone


def parse_since(value):
    """Parse an ISO 8601 string into a naive UTC datetime.

    Raises ValueError if the string is not a valid timestamp.
    """
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def serialize(record):
    """Return a JSON-friendly copy of a record (datetime -> ISO string)."""
    result = dict(record)
    timestamp = result.get("timestamp")
    if hasattr(timestamp, "isoformat"):
        result["timestamp"] = timestamp.isoformat()
    return result


def get_history(collection, limit=100, since=None):
    """Return up to ``limit`` most recent records, oldest first.

    If ``since`` is given, only records at or after that time are returned.
    """
    query = {"timestamp": {"$gte": since}} if since else {}
    cursor = collection.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return [serialize(record) for record in reversed(list(cursor))]


def get_latest(collection):
    """Return the most recent record, or None if there are no records."""
    record = collection.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])
    return serialize(record) if record else None
