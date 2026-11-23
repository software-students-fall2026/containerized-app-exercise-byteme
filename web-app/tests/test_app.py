"""Tests for the Flask routes."""

# pylint: disable=missing-function-docstring

import io
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests


def seed(collection):
    collection.insert_many(
        [
            {"timestamp": datetime(2026, 11, 20, 10, 0), "counts": {"bottle": 3}},
            {
                "timestamp": datetime(2026, 11, 20, 11, 0),
                "counts": {"bottle": 2, "cup": 1},
            },
        ]
    )


def image_data(content_type="image/jpeg", name="shelf.jpg"):
    return {"image": (io.BytesIO(b"fake-bytes"), name, content_type)}


def ml_response(status_code=200, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    return response


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_pages_render(client):
    assert client.get("/").status_code == 200
    assert client.get("/capture").status_code == 200


def test_api_inventory_empty(client):
    data = client.get("/api/inventory").get_json()
    assert data == {
        "history": {"labels": [], "datasets": []},
        "current": {"labels": [], "data": []},
        "low_stock": [],
    }


def test_api_inventory_returns_chart_data(client, collection):
    seed(collection)
    data = client.get("/api/inventory").get_json()
    assert data["history"]["labels"] == [
        "2026-11-20T10:00:00",
        "2026-11-20T11:00:00",
    ]
    assert data["history"]["datasets"] == [
        {"label": "bottle", "data": [3, 2]},
        {"label": "cup", "data": [0, 1]},
    ]
    assert data["current"] == {"labels": ["bottle", "cup"], "data": [2, 1]}
    assert data["low_stock"] == ["bottle", "cup"]


def test_api_inventory_limit(client, collection):
    seed(collection)
    data = client.get("/api/inventory?limit=1").get_json()
    assert data["history"]["labels"] == ["2026-11-20T11:00:00"]


def test_api_inventory_limit_is_clamped(client, collection):
    seed(collection)
    data = client.get("/api/inventory?limit=0").get_json()
    assert len(data["history"]["labels"]) == 1


def test_upload_requires_image(client):
    response = client.post("/upload", data={})
    assert response.status_code == 400


def test_upload_rejects_non_image(client):
    response = client.post(
        "/upload",
        data=image_data("text/plain", "notes.txt"),
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


@patch("app.requests.post")
def test_upload_forwards_image_to_ml_client(mock_post, client):
    mock_post.return_value = ml_response(200, {"counts": {"bottle": 2}})
    response = client.post(
        "/upload", data=image_data(), content_type="multipart/form-data"
    )
    assert response.status_code == 200
    assert response.get_json() == {"counts": {"bottle": 2}}
    assert mock_post.call_args.args[0] == "http://ml.test/analyze"


@patch("app.requests.post")
def test_upload_returns_502_when_ml_client_fails(mock_post, client):
    mock_post.return_value = ml_response(500)
    response = client.post(
        "/upload", data=image_data(), content_type="multipart/form-data"
    )
    assert response.status_code == 502


@patch("app.requests.post")
def test_upload_returns_502_when_ml_client_unreachable(mock_post, client):
    mock_post.side_effect = requests.ConnectionError()
    response = client.post(
        "/upload", data=image_data(), content_type="multipart/form-data"
    )
    assert response.status_code == 502


@patch("app.requests.post")
def test_upload_returns_502_on_invalid_json(mock_post, client):
    bad = ml_response(200)
    bad.json.side_effect = ValueError("bad json")
    mock_post.return_value = bad
    response = client.post(
        "/upload", data=image_data(), content_type="multipart/form-data"
    )
    assert response.status_code == 502


def test_upload_rejects_unsupported_image_type(client):
    response = client.post(
        "/upload",
        data=image_data("image/gif", "shelf.gif"),
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


@patch("app.requests.post")
def test_upload_returns_504_on_timeout(mock_post, client):
    mock_post.side_effect = requests.Timeout()
    response = client.post(
        "/upload", data=image_data(), content_type="multipart/form-data"
    )
    assert response.status_code == 504


def test_upload_rejects_oversized_file(app, client):
    app.config["MAX_CONTENT_LENGTH"] = 5
    response = client.post(
        "/upload", data=image_data(), content_type="multipart/form-data"
    )
    assert response.status_code == 413
    assert "too large" in response.get_json()["error"]
