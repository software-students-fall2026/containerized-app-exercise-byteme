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
