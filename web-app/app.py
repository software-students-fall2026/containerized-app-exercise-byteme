"""Flask web app for the snack inventory tracker."""

import io
import os

import requests
from flask import Flask, jsonify, render_template, request, send_file
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from chart_data import build_dashboard_data
from inventory import get_history, parse_since

ML_TIMEOUT_SECONDS = 30
DEFAULT_HISTORY = 100
MAX_HISTORY = 500
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
HEALTH_TIMEOUT_SECONDS = 3
MONGO_TIMEOUT_MS = 2000


def forward_to_ml_client(url, image):
    """Send the image to the ML client and return (payload, status_code)."""
    try:
        response = requests.post(
            url,
            files={"image": (image.filename, image.stream, image.mimetype)},
            timeout=ML_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            return {"error": "ML client failed to analyze image"}, 502
        return response.json(), 200
    except ValueError:
        return {"error": "ML client returned invalid data"}, 502
    except requests.Timeout:
        return {"error": "ML client timed out"}, 504
    except requests.RequestException:
        return {"error": "Could not reach the ML client"}, 502


def check_mongo(collection):
    """Return "ok" if MongoDB answers a ping, otherwise "unreachable"."""
    try:
        collection.database.command("ping")
        return "ok"
    except PyMongoError:
        return "unreachable"


def check_ml_client(url):
    """Return "ok" if the ML client answers at all, otherwise "unreachable"."""
    try:
        requests.get(url, timeout=HEALTH_TIMEOUT_SECONDS)
        return "ok"
    except requests.RequestException:
        return "unreachable"


def save_latest_photo(collection, data, mimetype):
    """Store the uploaded image, replacing previous latest photo."""
    collection.database["latest_photo"].replace_one(
        {"_id": "latest"}, {"data": data, "mimetype": mimetype}, upsert=True
    )


def create_app(config=None, collection=None):
    """Create and configure the Flask app.

    ``collection`` lets tests inject a fake MongoDB collection.
    """
    app = Flask(__name__)
    app.config.update(
        MONGO_URI=os.getenv("MONGO_URI", "mongodb://mongodb:27017"),
        MONGO_DB_NAME=os.getenv("MONGO_DB_NAME", "snack_tracker"),
        ML_CLIENT_URL=os.getenv("ML_CLIENT_URL", "http://ml-client:5001"),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
    )
    if config:
        app.config.update(config)

    if collection is None:
        client = MongoClient(
            app.config["MONGO_URI"],
            tz_aware=True,
            serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
        )
        collection = client[app.config["MONGO_DB_NAME"]]["inventory"]

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "Image is too large (max 10 MB)"}), 413

    @app.route("/health")
    def health():
        checks = {
            "mongodb": check_mongo(collection),
            "ml_client": check_ml_client(app.config["ML_CLIENT_URL"]),
        }
        healthy = all(value == "ok" for value in checks.values())
        status = "ok" if healthy else "degraded"
        return jsonify({"status": status, **checks}), 200 if healthy else 503

    @app.route("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/capture")
    def capture():
        return render_template("capture.html")

    @app.route("/latest-photo")
    def latest_photo():
        doc = collection.database["latest_photo"].find_one({"_id": "latest"})
        if doc is None:
            return jsonify({"error": "No photo yet"}), 404
        response = send_file(io.BytesIO(doc["data"]), mimetype=doc["mimetype"])
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.route("/api/inventory")
    def api_inventory():
        limit = request.args.get("limit", DEFAULT_HISTORY, type=int)
        limit = max(1, min(limit, MAX_HISTORY))
        since = None
        since_raw = request.args.get("since")
        if since_raw:
            try:
                since = parse_since(since_raw)
            except ValueError:
                return (
                    jsonify({"error": "since must be an ISO 8601 timestamp"}),
                    400,
                )
        return jsonify(build_dashboard_data(get_history(collection, limit, since)))

    @app.route("/upload", methods=["POST"])
    def upload():
        image = request.files.get("image")
        if image is None or image.filename == "":
            return jsonify({"error": "No image uploaded"}), 400
        if image.mimetype not in ALLOWED_IMAGE_TYPES:
            return jsonify({"error": "Image must be JPEG, PNG, or WebP"}), 400

        url = f"{app.config['ML_CLIENT_URL']}/analyze"
        payload, status = forward_to_ml_client(url, image)
        if status == 200:
            image.stream.seek(0)
            data = image.read()
            try:
                save_latest_photo(collection, data, image.mimetype)
            except PyMongoError:
                app.logger.exception("Could not save latest photo")
        return jsonify(payload), status

    return app


if __name__ == "__main__":  # pragma: no cover
    create_app().run(host="0.0.0.0", port=5000)
