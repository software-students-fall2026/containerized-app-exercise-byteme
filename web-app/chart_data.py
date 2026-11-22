"""Turn raw inventory records into the JSON shape the dashboard expects."""

LOW_STOCK_THRESHOLD = 3


def _count(record, name):
    """Return how many items of ``name`` a record has (0 if absent)."""
    return record.get("counts", {}).get(name, 0)


def build_dashboard_data(records, threshold=LOW_STOCK_THRESHOLD):
    """Build chart data from records sorted oldest to newest.

    Returns a dict with ``history`` (line chart), ``current`` (bar chart of
    the latest snapshot) and ``low_stock`` (names below ``threshold``).
    """
    classes = sorted({name for record in records for name in record["counts"]})
    latest = records[-1] if records else {}
    current = [_count(latest, name) for name in classes]

    return {
        "history": {
            "labels": [record["timestamp"] for record in records],
            "datasets": [
                {"label": name, "data": [_count(r, name) for r in records]}
                for name in classes
            ],
        },
        "current": {"labels": classes, "data": current},
        "low_stock": [
            name for name, count in zip(classes, current) if count < threshold
        ],
    }
