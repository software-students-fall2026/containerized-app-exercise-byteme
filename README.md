# Fridge Inventory Tracker

[![Lint](https://github.com/software-students-fall2026/containerized-app-exercise-byteme/actions/workflows/lint.yml/badge.svg)](https://github.com/software-students-fall2026/containerized-app-exercise-byteme/actions/workflows/lint.yml)

Fridge Inventory Tracker helps users monitor a fridge. Users take a photo in their browser or upload an image. The planned machine learning service detects objects, counts them by class, and saves inventory snapshots to MongoDB. The web dashboard displays current counts, inventory history, and low-stock alerts.

The project uses common object categories such as bottles, cups, and fruit rather than specific snack brands.

## Team

- [Tracy](https://github.com/TracyWang0904): web backend and web Dockerfile
- [Emma](https://github.com/emma6594): camera interface, dashboard, and chart formatting
- [Uuree](https://github.com/Uurii1003): database helpers, alerts, CI, seed data, and documentation
- [Jingjing](https://github.com/JingjingWang129): object detection, ML service, and Docker Compose

## Architecture

The completed system will run as three containers:

1. **Web app:** Flask application that accepts images, forwards them to the ML service, and reads inventory records.
2. **ML client:** Python service that analyzes images and saves detection results.
3. **Database:** MongoDB container that stores inventory snapshots.

```text
Browser camera or image upload
             |
             v
      Web app /upload
             |
             v
     ML client /analyze
             |
             v
     Detection → MongoDB
                     |
                     v
          Web app /api/inventory
                     |
                     v
                 Dashboard
```

## Current Status

Implemented:

- Flask routes for the dashboard, camera page, image upload, and inventory API
- Browser camera capture and image upload interface
- Current inventory and history charts
- Dashboard low-stock calculation and display
- MongoDB save/query helpers and unit tests
- Python 3.12 lint and formatting workflow
- Web app Dockerfile

Still in development:

- YOLO detector and ML `/analyze` service
- ML Dockerfile and three-service Docker Compose setup
- Seed script
- Persisted alert status and agreement on tracked classes
- Separate build/test workflows with coverage enforcement

Full image analysis requires the ML service, which is not yet included in this checkout.

## Requirements

- Python 3.12
- Pipenv
- Docker for running MongoDB
- A browser with camera permission, or an image file to upload

Browser camera capture requires localhost or HTTPS.

## Local Setup

Clone the repository:

```bash
git clone https://github.com/software-students-fall2026/containerized-app-exercise-byteme.git
cd containerized-app-exercise-byteme
```

Install each subsystem’s dependencies independently:

```bash
cd machine-learning-client
pipenv --python 3.12
pipenv sync --dev
```

```bash
cd ../web-app
pipenv --python 3.12
pipenv sync --dev
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `MONGO_URI` | MongoDB connection address | `mongodb://mongodb:27017` |
| `MONGO_DB_NAME` | Web app database name | `snack_tracker` |
| `ML_CLIENT_URL` | ML service base URL | `http://ml-client:5001` |

The ML database helper uses database `snack_tracker` and collection `inventory`. Keep the web app configured to use the same database.

For local development outside Docker, set:

```bash
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB_NAME="snack_tracker"
export ML_CLIENT_URL="http://localhost:5001"
```

Set these variables in the terminal where you start the application. The current code reads environment variables directly; it does not automatically load a `.env` file.

## Run MongoDB and the Web App

Start MongoDB:

```bash
docker run --name snack-mongodb \
  -p 127.0.0.1:27017:27017 \
  -v snack-mongo-data:/data/db \
  -d mongo
```

The named volume preserves database files between container restarts. To restart an existing stopped container, use:

```bash
docker start snack-mongodb
```

From the repository’s `web-app` directory, set the local environment variables above and run:

```bash
pipenv run flask --app app run --port 5050
```

Open [http://localhost:5050](http://localhost:5050).

The dashboard can display existing MongoDB records. Upload analysis will return an error until an ML service is running at `ML_CLIENT_URL`. No starter data is loaded automatically.

## Database Format

Inventory snapshots use this structure:

```python
{
    "timestamp": datetime.now(timezone.utc),
    "counts": {
        "bottle": 4,
        "cup": 2,
        "banana": 0,
    },
}
```

Timestamps are stored as MongoDB datetimes and returned as ISO-formatted strings. MongoDB’s internal `_id` is excluded from API output.

The ML database module provides:

- `get_collection()`
- `save_record(collection, counts)`
- `get_latest(collection)`
- `get_history(collection, limit=100)`

## Routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/` | Dashboard: shelf levels, alerts, latest photo, history chart |
| GET | `/capture` | Camera and upload interface: Take a photo with the camera or upload one|
| POST | `/upload` | Forward an image to the ML service: saves it as the latest photo if analysis is successful |
| GET | `/latest-photo` | The last successfully analyzed image (404 if none) |
| GET | `/health` | Checks MongoDB and the ML service |
| GET | `/api/inventory` | Dashboard data |

The ML endpoint `POST / analyze` retunrs `{"shelves": {"top": "low", "middle": "full"}}`

The latest photo is stored in the `latest_photo` collection as one document, `{"_id": "latest", "data": <bytes>, "mimetype": "image/jpeg"}`, which each new upload replaces.


Uploads use multipart field `image`. The planned ML endpoint is `POST /analyze`, with a response such as:

```json
{"shelves": {"top": "low", "middle": "full"}}
```

Levels are `low`, `moderate`, or `full`. The inventory API returns `history` (level per shelf over time), `current` (latest level per shelf) and `alerts` (shelves whose latest level is low).

The inventory API returns `history`, `current`, and `low_stock`.

Currently, low stock means **fewer than three items**. Item classes are inferred from the returned history; missing counts for those classes are treated as zero. Classes absent from the entire returned history are not tracked.

## Tests and Code Quality

Run commands from the relevant subsystem directory.

### Smoke Test

With the stack running (`docker compose up --build`), from `web-app/`:

```bash
pipenv run python smoke_test.py http://localhost:5050
```

It checks `/health`, `/api/inventory`, `/upload` and `/latest-photo`, and prints PASS or FAIL for each.

### Machine Learning Client

```bash
pipenv run black --check .
PYTHONPATH=. pipenv run pylint db.py tests/test_db.py
PYTHONPATH=. pipenv run pytest \
  --cov=db \
  --cov-report=term-missing \
  --cov-fail-under=80 tests
```

The database tests use mocked MongoDB. The verified database test run passed eight tests with 100% coverage of `db.py`.

### Web App

```bash
pipenv run black --check .
PYTHONPATH=. pipenv run pylint app.py inventory.py chart_data.py tests
pipenv run pytest \
  --cov=app \
  --cov=inventory \
  --cov=chart_data \
  --cov-report=term-missing \
  --cov-fail-under=80
```

Tests mock external services and do not require a running ML service or MongoDB instance.

The project requires at least 80% coverage for each subsystem. Coverage targets must expand as new application modules are added.

## Development Workflow

- Use Python 3.12.
- Create a feature branch for each task.
- Run Black, Pylint, and tests before opening a pull request.
- Include tests with new functionality.
- Request a teammate’s review and wait for passing checks before merging.