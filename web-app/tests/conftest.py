"""Shared pytest fixtures."""

# pylint: disable=redefined-outer-name

import mongomock
import pytest

from app import create_app


@pytest.fixture
def collection():
    """An in-memory fake MongoDB collection."""
    return mongomock.MongoClient().db.inventory


@pytest.fixture
def app(collection):
    """The Flask app wired to the fake collection (used by pytest-flask)."""
    return create_app(
        {"TESTING": True, "ML_CLIENT_URL": "http://ml.test"},
        collection=collection,
    )
