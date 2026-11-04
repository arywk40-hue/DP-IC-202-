"""Authentication end-to-end, fail-closed Google claims and session privacy."""
from pathlib import Path
import sqlite3
import tempfile
import time

from fastapi.testclient import TestClient
import pytest

from server import dashboard
from server.auth import AuthStore, verify_google_credential


def test_demo_identity_session_logout_and_disabled_by_default(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "auth.sqlite"
        with TestClient(dashboard.create_app(db)) as client:
            config = client.get('/api/auth/config').json()
            assert config == {"googleClientId": "", "demoAuthEnabled": False,
                              "authEnabled": False, "mode": "disabled"}
            assert client.post('/api/auth/demo-login', json={}).status_code == 404
            assert client.get('/api/auth/me').status_code == 401

        with TestClient(dashboard.create_app(db, demo_auth_enabled=True)) as client:
            assert client.get('/api/auth/config').json()['demoAuthEnabled'] is True
            assert client.post('/api/auth/demo-login', json={"email": "victim@example.com"}).status_code == 422
            login = client.post('/api/auth/demo-login', json={})
            assert login.status_code == 200
            data = login.json()
            assert data['user']['provider'] == 'demo'
            assert data['user']['email'] == 'demo@localhost'
            token = data['token']
            headers = {"Authorization": f"Bearer {token}"}
            assert client.get('/api/auth/me', headers=headers).json()['user']['provider'] == 'demo'
            with sqlite3.connect(db) as conn:
                stored = conn.execute('SELECT token_hash FROM sessions').fetchone()[0]
            assert stored != token
            assert client.post('/api/auth/logout', headers=headers).json()['ok']
            assert client.get('/api/auth/me', headers=headers).status_code == 401


def test_google_verification_requires_client_audience_issuer_expiry_and_verified_email(monkeypatch):
    now = int(time.time())
    claims = {"aud": "indra-client", "iss": "https://accounts.google.com",
              "exp": str(now + 120), "email_verified": True,
              "sub": "google-subject", "email": "person@example.org", "name": "Person"}

    class Response:
        status_code = 200
        def __init__(self, body): self.body = body
        def json(self): return self.body

    monkeypatch.setattr('server.auth.httpx.get', lambda *a, **kw: Response(claims.copy()))
    with pytest.raises(ValueError, match='not configured'):
        verify_google_credential('credential', '')
    user = verify_google_credential('credential', 'indra-client')
    assert user['provider'] == 'google' and user['id'] == 'google-subject'

    for key, value, message in [
        ('aud', 'another-client', 'audience'),
        ('iss', 'attacker.example', 'issuer'),
        ('exp', str(now - 1), 'expired'),
        ('email_verified', False, 'not verified'),
    ]:
        changed = claims.copy(); changed[key] = value
        monkeypatch.setattr('server.auth.httpx.get', lambda *a, _body=changed, **kw: Response(_body))
        with pytest.raises(ValueError, match=message):
            verify_google_credential('credential', 'indra-client')
