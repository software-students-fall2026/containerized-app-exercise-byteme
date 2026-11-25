"""Turn raw inventory records into the JSON shape the dashboard expects."""

LOW_STOCK_THRESHOLD = 3
ALERT_STATUSES = {"empty", "low_stock"}


def _count(record, name):
    """Return how many items of ``name`` a record has (0 if absent)."""
    return record.get("counts", {}).get(name, 0)


def _fill_ratio(record, shelf_id):
    """Return a shelf's fill ratio in a record, or None if it is absent."""
    for shelf in record["shelves"]:
        if shelf["shelf_id"] == shelf_id:
            return shelf["fill_ratio"]
    return None


def _alerts(shelves):
    """List shelves that are empty/low or have missing items."""
    return [
        {
            "shelf_id": shelf["shelf_id"],
            "status": shelf["status"],
            "missing": shelf.get("missing", []),
        }
        for shelf in shelves
        if shelf["status"] in ALERT_STATUSES or shelf.get("missing")
    ]


def build_dashboard_data(records, threshold=LOW_STOCK_THRESHOLD):
    """Build chart data from records sorted oldest to newest.

    Returns ``history`` (line chart), ``current`` (bar chart of the latest
    snapshot) and ``low_stock`` (names below ``threshold``) for item counts,
    plus ``shelves`` (latest shelf status), ``fill_history`` (fill ratio per
    shelf over time) and ``alerts`` (shelves that need attention).
    """
    classes = sorted({name for record in records for name in record.get("counts", {})})
    latest = records[-1] if records else {}
    current = [_count(latest, name) for name in classes]

    shelf_records = [record for record in records if record.get("shelves")]
    shelf_ids = sorted(
        {shelf["shelf_id"] for record in shelf_records for shelf in record["shelves"]}
    )
    latest_shelves = latest.get("shelves", [])

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
        "shelves": latest_shelves,
        "fill_history": {
            "labels": [record["timestamp"] for record in shelf_records],
            "datasets": [
                {
                    "label": shelf_id,
                    "data": [_fill_ratio(r, shelf_id) for r in shelf_records],
                }
                for shelf_id in shelf_ids
            ],
        },
        "alerts": _alerts(latest_shelves),
    }
