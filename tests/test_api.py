import os
import tempfile
from fastapi.testclient import TestClient
from app import main

def test_full_lifecycle(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(main, "DB_PATH", os.path.join(tmp, "test.db"))
        with TestClient(main.app) as client:
            created = client.post("/api/links", json={"url":"https://example.org/path"})
            assert created.status_code == 201
            code = created.json()["code"]
            redirect = client.get(f"/{code}", follow_redirects=False)
            assert redirect.status_code == 307
            assert redirect.headers["location"] == "https://example.org/path"
            stats = client.get(f"/api/links/{code}/analytics")
            assert stats.json()["clicks"] == 1
            assert client.get("/missing-code").status_code == 404
            assert client.post("/api/links", json={"url":"not-a-url"}).status_code == 422
