from fastapi.testclient import TestClient


def test_health(monkeypatch):
    for k, v in {
        "JWT_SECRET": "x",
        "DB2_HOST": "x",
        "DB2_DATABASE": "x",
        "DB2_USER": "x",
        "DB2_PASSWORD": "x",
        "BB_UEM_OAUTH_URL": "https://x",
        "BB_UEM_COB_URL": "https://x",
        "BB_UEM_CLIENT_ID": "x",
        "BB_UEM_CLIENT_SECRET": "x",
        "BB_UEM_GW_APP_KEY": "x",
        "BB_UEM_P12_PATH": "/tmp/x.p12",
        "BB_UEM_P12_PASSWORD": "x",
        "BB_UEM_CER_PATH": "/tmp/x.cer",
    }.items():
        monkeypatch.setenv(k, v)

    from app.main import app

    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
