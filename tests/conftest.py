import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from app import create_app
from extensions import db as _db


@pytest.fixture
def app():
    application = create_app()
    application.config.update({"TESTING": True})
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth(client):
    client.post("/register", data={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    return client


@pytest.fixture
def second_client(app):
    return app.test_client()


@pytest.fixture
def unauth_client(app):
    return app.test_client()
