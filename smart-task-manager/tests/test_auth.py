def test_register_page_loads(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"Create account" in resp.data


def test_register_success(client):
    resp = client.post("/register", data={
        "name": "Alice",
        "email": "alice@test.com",
        "password": "secret",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Ready" in resp.data or b"Welcome" in resp.data


def test_register_missing_fields(client):
    resp = client.post("/register", data={
        "name": "", "email": "", "password": "",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"required" in resp.data


def test_register_duplicate_email(client):
    client.post("/register", data={
        "name": "A", "email": "dup@test.com", "password": "x",
    })
    client.post("/logout")
    resp = client.post("/register", data={
        "name": "B", "email": "dup@test.com", "password": "y",
    }, follow_redirects=True)
    assert b"already exists" in resp.data


def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_login_success(client):
    client.post("/register", data={
        "name": "Alice", "email": "alice@test.com", "password": "secret",
    })
    client.post("/logout")
    resp = client.post("/login", data={
        "email": "alice@test.com", "password": "secret",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Logout" in resp.data


def test_login_invalid(client):
    resp = client.post("/login", data={
        "email": "noone@test.com", "password": "wrong",
    }, follow_redirects=True)
    assert b"Invalid" in resp.data


def test_logout(auth):
    resp = auth.post("/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert b"logged out" in resp.data.lower()


def test_unauthenticated_redirects_to_login(client):
    resp = client.get("/dashboard", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_already_logged_in_redirects_away(client):
    client.post("/register", data={
        "name": "Alice", "email": "alice@test.com", "password": "secret",
    })
    resp = client.get("/register", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Logout" in resp.data


def test_index_redirects_authenticated(auth):
    resp = auth.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Work dashboard" in resp.data


def test_index_redirects_unauthenticated(client):
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_login_already_authenticated_redirects(auth):
    resp = auth.get("/login", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Logout" in resp.data


def test_register_already_authenticated_redirects(auth):
    resp = auth.get("/register", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Logout" in resp.data
