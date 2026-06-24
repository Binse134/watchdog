def test_signup_sets_session_cookie_and_me_works(client):
    response = client.post("/auth/signup", json={"email": "new@example.com", "password": "testpass123"})
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


def test_signup_duplicate_email_is_rejected(client):
    client.post("/auth/signup", json={"email": "dupe@example.com", "password": "testpass123"})
    response = client.post("/auth/signup", json={"email": "dupe@example.com", "password": "testpass123"})
    assert response.status_code == 409


def test_signup_password_too_short_is_rejected(client):
    response = client.post("/auth/signup", json={"email": "short@example.com", "password": "short"})
    assert response.status_code == 422


def test_login_wrong_password_is_rejected(client):
    client.post("/auth/signup", json={"email": "login@example.com", "password": "testpass123"})
    client.post("/auth/logout")

    response = client.post("/auth/login", json={"email": "login@example.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_login_unknown_email_is_rejected(client):
    response = client.post("/auth/login", json={"email": "ghost@example.com", "password": "whatever123"})
    assert response.status_code == 401


def test_login_correct_password_succeeds(client):
    client.post("/auth/signup", json={"email": "loginok@example.com", "password": "testpass123"})
    client.post("/auth/logout")

    response = client.post("/auth/login", json={"email": "loginok@example.com", "password": "testpass123"})
    assert response.status_code == 200

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "loginok@example.com"


def test_logout_invalidates_session(client):
    client.post("/auth/signup", json={"email": "logout@example.com", "password": "testpass123"})
    client.post("/auth/logout")

    me = client.get("/auth/me")
    assert me.status_code == 401


def test_me_without_session_is_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_delete_account_clears_session_and_removes_user(client):
    client.post("/auth/signup", json={"email": "delete@example.com", "password": "testpass123"})

    response = client.delete("/auth/me")
    assert response.status_code == 204

    me = client.get("/auth/me")
    assert me.status_code == 401

    # Re-signup with the same email succeeds, proving the row is gone.
    response = client.post("/auth/signup", json={"email": "delete@example.com", "password": "testpass123"})
    assert response.status_code == 200


def test_delete_account_requires_auth(client):
    response = client.delete("/auth/me")
    assert response.status_code == 401


def test_change_password_with_correct_current_password(client):
    client.post("/auth/signup", json={"email": "changepw@example.com", "password": "oldpass123"})

    response = client.patch(
        "/auth/me/password", json={"current_password": "oldpass123", "new_password": "newpass123"}
    )
    assert response.status_code == 200

    client.post("/auth/logout")
    response = client.post("/auth/login", json={"email": "changepw@example.com", "password": "newpass123"})
    assert response.status_code == 200


def test_change_password_with_wrong_current_password_is_rejected(client):
    client.post("/auth/signup", json={"email": "wrongpw@example.com", "password": "oldpass123"})

    response = client.patch(
        "/auth/me/password", json={"current_password": "not-the-password", "new_password": "newpass123"}
    )
    assert response.status_code == 400

    client.post("/auth/logout")
    response = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "oldpass123"})
    assert response.status_code == 200


def test_change_password_requires_auth(client):
    response = client.patch(
        "/auth/me/password", json={"current_password": "whatever123", "new_password": "newpass123"}
    )
    assert response.status_code == 401


def test_forgot_password_sends_email_for_known_address(client, monkeypatch):
    client.post("/auth/signup", json={"email": "forgot@example.com", "password": "testpass123"})
    client.post("/auth/logout")

    sent = {}

    def fake_send_email(to, subject, html):
        sent["to"] = to
        sent["html"] = html
        return None

    monkeypatch.setattr("app.auth.send_email", fake_send_email)

    response = client.post("/auth/forgot-password", json={"email": "forgot@example.com"})
    assert response.status_code == 200
    assert sent["to"] == "forgot@example.com"
    assert "reset-password?token=" in sent["html"]


def test_forgot_password_unknown_email_returns_same_generic_response(client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.auth.send_email", lambda *a, **k: calls.append(a))

    response = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert calls == []


def test_reset_password_with_valid_token_updates_password(client, monkeypatch):
    client.post("/auth/signup", json={"email": "reset@example.com", "password": "oldpass123"})
    client.post("/auth/logout")

    captured = {}
    monkeypatch.setattr(
        "app.auth.send_email",
        lambda to, subject, html: captured.update(html=html) or None,
    )
    client.post("/auth/forgot-password", json={"email": "reset@example.com"})
    token = captured["html"].split("token=")[1].split('"')[0]

    response = client.post("/auth/reset-password", json={"token": token, "new_password": "brandnewpass"})
    assert response.status_code == 200

    response = client.post("/auth/login", json={"email": "reset@example.com", "password": "brandnewpass"})
    assert response.status_code == 200


def test_reset_password_with_invalid_token_is_rejected(client):
    response = client.post("/auth/reset-password", json={"token": "garbage", "new_password": "newpass123"})
    assert response.status_code == 400


def test_reset_password_with_tampered_token_is_rejected(client, monkeypatch):
    client.post("/auth/signup", json={"email": "tamper@example.com", "password": "oldpass123"})
    client.post("/auth/logout")

    captured = {}
    monkeypatch.setattr(
        "app.auth.send_email",
        lambda to, subject, html: captured.update(html=html) or None,
    )
    client.post("/auth/forgot-password", json={"email": "tamper@example.com"})
    token = captured["html"].split("token=")[1].split('"')[0]

    response = client.post("/auth/reset-password", json={"token": token + "x", "new_password": "newpass123"})
    assert response.status_code == 400
