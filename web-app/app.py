"""Flask web app for the snack inventory tracker."""

import os

import requests
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient

from chart_data import build_dashboard_data
from inventory import get_history, parse_since

ML_TIMEOUT_SECONDS = 30
DEFAULT_HISTORY = 100
MAX_HISTORY = 500
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


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
        client = MongoClient(app.config["MONGO_URI"], tz_aware=True)
        collection = client[app.config["MONGO_DB_NAME"]]["inventory"]

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "Image is too large (max 10 MB)"}), 413

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/capture")
    def capture():
        return render_template("capture.html")

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
        return jsonify(payload), status

    return app


if __name__ == "__main__":  # pragma: no cover
    create_app().run(host="0.0.0.0", port=5000)
