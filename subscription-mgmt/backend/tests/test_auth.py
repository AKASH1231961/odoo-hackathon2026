"""Tests for auth endpoints: register, login, RBAC."""


def test_register_success(client):
    resp = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "Test@1234",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "customer"


def test_register_duplicate(client):
    client.post("/auth/register", json={
        "email": "dup@example.com", "password": "Test@1234",
    })
    resp = client.post("/auth/register", json={
        "email": "dup@example.com", "password": "Test@1234",
    })
    assert resp.status_code == 400


def test_register_weak_password(client):
    resp = client.post("/auth/register", json={
        "email": "weak@example.com", "password": "password",
    })
    assert resp.status_code == 422  # Pydantic validation error


def test_login_success(client):
    client.post("/auth/register", json={
        "email": "login@example.com", "password": "Login@123",
    })
    resp = client.post("/auth/login", json={
        "email": "login@example.com", "password": "Login@123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "refresh_token" in resp.json()


def test_login_wrong_password(client):
    resp = client.post("/auth/login", json={
        "email": "nobody@example.com", "password": "Wrong@123",
    })
    assert resp.status_code == 401


def test_protected_route_without_token(client):
    resp = client.get("/users")
    assert resp.status_code == 401


def test_customer_cannot_access_admin(client):
    # Register customer
    client.post("/auth/register", json={
        "email": "cust@example.com", "password": "Cust@1234",
    })
    login = client.post("/auth/login", json={
        "email": "cust@example.com", "password": "Cust@1234",
    })
    token = login.json()["access_token"]
    resp = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

