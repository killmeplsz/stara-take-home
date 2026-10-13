import db

# Prevent database initialization when importing app for tests.
db.init_db = lambda: None

import app as stara  # noqa: E402
import pytest


@pytest.fixture
def client():
    stara.app.config.update(TESTING=True)

    with stara.app.test_client() as client:
        yield client


def test_create_customer_missing_fields(client):
    response = client.post("/customers", json={})

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Validation failed"
    assert "details" in data


def test_create_customer_invalid_status(client):
    response = client.post(
        "/customers",
        json={
            "name": "Budi Santoso",
            "phone": "081234567890",
            "status": "unknown",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed"


def test_list_customers_invalid_status(client):
    response = client.get("/customers?status=unknown")

    assert response.status_code == 400
    assert "status filter" in response.get_json()["error"]


def test_webhook_missing_phone_and_message(client):
    response = client.post(
        "/webhook/incoming-message",
        json={"name": "Budi Santoso"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Incomplete data"
    assert "phone is required" in data["details"]
    assert "message is required" in data["details"]


def test_webhook_empty_message(client):
    response = client.post(
        "/webhook/incoming-message",
        json={
            "phone": "081234567890",
            "message": "   ",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Incomplete data"


def test_unknown_endpoint_returns_json_404(client):
    response = client.get("/endpoint-tidak-ada")

    assert response.status_code == 404
    assert "error" in response.get_json()
