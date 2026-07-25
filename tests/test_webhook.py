import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "VyaparAI"


def test_webhook_verify_correct_token():
    response = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "vyapar_ai_secret_verify_token",
        "hub.challenge": "test_challenge_123",
    })
    assert response.status_code == 200
    assert response.text == "test_challenge_123"


def test_webhook_verify_wrong_token():
    response = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token",
        "hub.challenge": "test_challenge_123",
    })
    assert response.status_code == 403


def test_webhook_receives_non_wa_payload():
    response = client.post("/webhook", json={"object": "something_else"})
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_non_owner_message_ignored():
    """Message from unknown sender should be silently ignored."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "9999999999",  # not the owner
                        "type": "text",
                        "text": {"body": "hello"},
                    }]
                }
            }]
        }]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_empty_body():
    response = client.post("/webhook", content=b"")
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert response.json()["reason"] == "empty body"


def test_webhook_malformed_json():
    response = client.post("/webhook", content=b"invalid json")
    assert response.status_code == 400
    assert "Invalid JSON body" in response.json()["detail"]


@pytest.mark.skip(reason="Requires live PostgreSQL container — run inside Docker")
def test_reports_stub_endpoints():
    for path in ["/reports/daily", "/reports/monthly", "/reports/outstanding"]:
        resp = client.get(path)
        assert resp.status_code == 200
