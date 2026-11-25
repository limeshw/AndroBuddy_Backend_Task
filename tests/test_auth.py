def test_register_and_login_success(client):
    """Test 1A: Register new customer, verify duplicate 409, login and fetch /auth/me."""
    # 1. Register new customer
    register_payload = {
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "SecurePassword123",
    }
    response = client.post("/auth/register", json=register_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "customer"
    assert "password_hash" not in data  # Never leak password hash

    # 2. Duplicate registration returns 409 Conflict
    dup_response = client.post("/auth/register", json=register_payload)
    assert dup_response.status_code == 409

    # 3. Login returns JWT token
    login_payload = {
        "email": "newuser@example.com",
        "password": "SecurePassword123",
    }
    login_resp = client.post("/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 4. GET /auth/me returns current user without password hash
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "newuser@example.com"
    assert "password_hash" not in me_data


def test_register_password_too_short(client):
    """Password with less than 8 characters should fail validation."""
    payload = {
        "email": "short@example.com",
        "full_name": "Short Pass",
        "password": "short",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422

