from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "earth_engine" in data
    assert data["earth_engine"]["project"] == "prithvix-514718"


def test_datasets_endpoint():
    response = client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert "smap" in data
    assert "gpm" in data
    assert "landsat" in data
    assert "nasa_power" in data
    assert "modis" in data
    assert "srtm" in data
    assert "grace" in data
    assert "ecostress" in data
