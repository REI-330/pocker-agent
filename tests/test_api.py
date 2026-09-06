from fastapi.testclient import TestClient

from pocker_agent.api import app


client = TestClient(app)


def fixture_payload() -> dict:
    return {
        "game_id": "api-demo",
        "title": "API Demo",
        "deck": {"suits": ["S"], "ranks": ["A", "K"]},
        "players": {"min_players": 2, "max_players": 2, "starting_hand_size": 1},
        "actions": [{"name": "play"}],
        "phases": [{"name": "main", "actions": ["play"]}],
    }


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_validate_and_simulate():
    validation = client.post("/api/rules/validate", json=fixture_payload())
    assert validation.status_code == 200
    assert validation.json()["valid"] is True

    simulation = client.post("/api/simulations?seed=3", json=fixture_payload())
    assert simulation.status_code == 200
    assert simulation.json()["completed"] is True
