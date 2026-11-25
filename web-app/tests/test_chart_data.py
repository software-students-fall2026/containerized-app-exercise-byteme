"""Tests for the dashboard chart data builder."""

# pylint: disable=missing-function-docstring

from chart_data import build_dashboard_data

RECORDS = [
    {"timestamp": "t1", "counts": {"bottle": 5, "cup": 2}},
    {"timestamp": "t2", "counts": {"bottle": 4}},
]


def test_empty_records():
    assert build_dashboard_data([]) == {
        "history": {"labels": [], "datasets": []},
        "current": {"labels": [], "data": []},
        "low_stock": [],
        "shelves": [],
        "fill_history": {"labels": [], "datasets": []},
        "alerts": [],
    }


def test_history_fills_missing_counts_with_zero():
    history = build_dashboard_data(RECORDS)["history"]
    assert history["labels"] == ["t1", "t2"]
    assert history["datasets"] == [
        {"label": "bottle", "data": [5, 4]},
        {"label": "cup", "data": [2, 0]},
    ]


def test_current_uses_latest_record():
    current = build_dashboard_data(RECORDS)["current"]
    assert current == {"labels": ["bottle", "cup"], "data": [4, 0]}


def test_low_stock_uses_threshold():
    assert build_dashboard_data(RECORDS)["low_stock"] == ["cup"]
    result = build_dashboard_data(RECORDS, threshold=5)
    assert result["low_stock"] == ["bottle", "cup"]


SHELF_RECORDS = [
    {
        "timestamp": "t1",
        "shelves": [
            {
                "shelf_id": "S1",
                "fill_ratio": 0.5,
                "status": "in_stock",
                "detected": ["milk"],
                "missing": [],
            },
            {
                "shelf_id": "S2",
                "fill_ratio": 0.2,
                "status": "low_stock",
                "detected": [],
                "missing": ["eggs"],
            },
        ],
    },
    {
        "timestamp": "t2",
        "shelves": [
            {
                "shelf_id": "S1",
                "fill_ratio": 0.05,
                "status": "empty",
                "detected": [],
                "missing": ["milk"],
            },
        ],
    },
]


def test_shelves_use_latest_record():
    data = build_dashboard_data(SHELF_RECORDS)
    assert [shelf["shelf_id"] for shelf in data["shelves"]] == ["S1"]
    assert data["shelves"][0]["status"] == "empty"


def test_fill_history_has_one_series_per_shelf():
    history = build_dashboard_data(SHELF_RECORDS)["fill_history"]
    assert history["labels"] == ["t1", "t2"]
    assert history["datasets"] == [
        {"label": "S1", "data": [0.5, 0.05]},
        {"label": "S2", "data": [0.2, None]},
    ]


def test_alerts_for_empty_shelf():
    assert build_dashboard_data(SHELF_RECORDS)["alerts"] == [
        {"shelf_id": "S1", "status": "empty", "missing": ["milk"]}
    ]


def test_alerts_for_missing_items_on_stocked_shelf():
    records = [
        {
            "timestamp": "t1",
            "shelves": [
                {
                    "shelf_id": "S1",
                    "fill_ratio": 0.6,
                    "status": "in_stock",
                    "missing": ["eggs"],
                }
            ],
        }
    ]
    assert build_dashboard_data(records)["alerts"] == [
        {"shelf_id": "S1", "status": "in_stock", "missing": ["eggs"]}
    ]


def test_old_count_records_have_no_shelf_data():
    data = build_dashboard_data(RECORDS)
    assert data["shelves"] == []
    assert data["alerts"] == []
    assert data["fill_history"] == {"labels": [], "datasets": []}
