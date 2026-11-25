"""Tests for the Flask routes."""

# pylint: disable=missing-function-docstring

import io
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests
from pymongo.errors import PyMongoError

from app import create_app


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


@patch("app.requests.get")
def test_health_ok(mock_get, client):
    mock_get.return_value = MagicMock(status_code=200)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "mongodb": "ok",
        "ml_client": "ok",
    }


@patch("app.requests.get", side_effect=requests.ConnectionError())
def test_health_503_when_ml_client_down(_mock_get, client):
    response = client.get("/health")
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "degraded"
    assert body["mongodb"] == "ok"
    assert body["ml_client"] == "unreachable"


@patch("app.requests.get")
def test_health_503_when_mongo_down(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    broken = MagicMock()
    broken.database.command.side_effect = PyMongoError("down")
    app = create_app({"TESTING": True, "ML_CLIENT_URL": "http://ml.test"}, broken)
    response = app.test_client().get("/health")
    assert response.status_code == 503
    assert response.get_json()["mongodb"] == "unreachable"


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


def test_api_inventory_since_filters_records(client, collection):
    collection.insert_many(
        [
            {"timestamp": datetime(2026, 11, 20, 9), "counts": {"chips": 5}},
            {"timestamp": datetime(2026, 11, 20, 11), "counts": {"chips": 3}},
        ]
    )
    response = client.get("/api/inventory?since=2026-11-20T10:00:00")
    assert response.status_code == 200
    assert len(response.get_json()["history"]["labels"]) == 1


def test_api_inventory_rejects_invalid_since(client):
    response = client.get("/api/inventory?since=yesterday")
    assert response.status_code == 400
    assert "ISO 8601" in response.get_json()["error"]


def test_latest_photo_404_when_none(client):
    response = client.get("/latest-photo")
    assert response.status_code == 404


@patch("app.requests.post")
def test_upload_saves_latest_photo(mock_post, client):
    mock_post.return_value = ml_response(200, {"counts": {"bottle": 2}})
    client.post("/upload", data=image_data(), content_type="multipart/form-data")
    response = client.get("/latest-photo")
    assert response.status_code == 200
    assert response.data == b"fake-bytes"
    assert response.mimetype == "image/jpeg"
    assert response.headers["Cache-Control"] == "no-cache"


@patch("app.requests.post")
def test_new_upload_replaces_latest_photo(mock_post, client):
    mock_post.return_value = ml_response(200, {"counts": {}})
    client.post("/upload", data=image_data(), content_type="multipart/form-data")
    client.post(
        "/upload",
        data={"image": (io.BytesIO(b"new-bytes"), "new.png", "image/png")},
        content_type="multipart/form-data",
    )
    response = client.get("/latest-photo")
    assert response.data == b"new-bytes"
    assert response.mimetype == "image/png"


def test_reject_upload_saves_no_photo(client):
    client.post(
        "/upload",
        data=image_data("text/plain", "notes.txt"),
        content_type="multipart/form-data",
    )
    assert client.get("/latest-photo").status_code == 404


@patch("app.requests.post")
def test_failed_analysis_saves_no_photo(mock_post, client):
    mock_post.return_value = ml_response(500)
    client.post("/upload", data=image_data(), content_type="multipart/form-data")
    assert client.get("/latest-photo").status_code == 404


@patch("app.save_latest_photo", side_effect=PyMongoError("write failed"))
@patch("app.requests.post")
def test_upload_still_succeeds_when_photo_save_fails(mock_post, _mock_save, client):
    mock_post.return_value = ml_response(200, {"counts": {"bottle": 2}})
    response = client.post(
        "/upload", data=image_data(), content_type="multipart/form-data"
    )
    assert response.status_code == 200
    assert response.get_json() == {"counts": {"bottle": 2}}


def test_requests_are_logged(client, caplog):
    with caplog.at_level(logging.INFO):
        client.get("/")
    assert "GET / -> 200" in caplog.text


@patch("app.requests.get")
def test_health_requests_are_not_logged(mock_get, client, caplog):
    mock_get.return_value = MagicMock(status_code=200)
    with caplog.at_level(logging.INFO):
        client.get("/health")
    assert "/health" not in caplog.text


@patch("app.requests.post")
def test_failed_ml_call_is_logged(mock_post, client, caplog):
    mock_post.return_value = ml_response(500)
    with caplog.at_level(logging.WARNING):
        client.post("/upload", data=image_data(), content_type="multipart/form-data")
    assert "ML client call failed with status 502" in caplog.text
