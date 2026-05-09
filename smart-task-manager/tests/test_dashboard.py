def test_dashboard_loads(auth):
    resp = auth.get("/dashboard")
    assert resp.status_code == 200
    assert b"Work dashboard" in resp.data


def test_dashboard_shows_empty_state(auth):
    resp = auth.get("/dashboard")
    assert b"Your workspace is clear" in resp.data


def test_dashboard_requires_auth(client):
    resp = client.get("/dashboard", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_create_task_via_form(auth):
    resp = auth.post("/dashboard", data={
        "title": "Buy groceries",
        "priority": "high",
        "due_date": "2026-06-01",
        "description": "Milk and eggs",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Task added" in resp.data
    assert b"Buy groceries" in resp.data


def test_create_task_missing_title(auth):
    resp = auth.post("/dashboard", data={
        "title": "",
        "priority": "medium",
    }, follow_redirects=True)
    assert b"required" in resp.data or b"title" in resp.data.lower()


def test_create_task_invalid_due_date(auth):
    resp = auth.post("/dashboard", data={
        "title": "Bad date",
        "due_date": "not-a-date",
    }, follow_redirects=True)
    assert b"valid due date" in resp.data.lower()


def test_create_task_invalid_priority(auth):
    resp = auth.post("/dashboard", data={
        "title": "Bad priority",
        "priority": "urgent",
    }, follow_redirects=True)
    assert b"valid priority" in resp.data.lower()


def test_dashboard_shows_stats(auth):
    auth.post("/dashboard", data={"title": "Task A"}, follow_redirects=True)
    auth.post("/dashboard", data={"title": "Task B"}, follow_redirects=True)
    resp = auth.get("/dashboard")
    assert b"2 items tracked" in resp.data
    assert b"2 active" in resp.data


def test_dashboard_filter_by_status(auth):
    auth.post("/dashboard", data={"title": "Active task"}, follow_redirects=True)
    resp = auth.get("/dashboard?status=todo")
    assert resp.status_code == 200
    assert b"Active task" in resp.data


def test_dashboard_filter_by_priority(auth):
    auth.post("/dashboard", data={
        "title": "Critical work", "priority": "high",
    }, follow_redirects=True)
    resp = auth.get("/dashboard?priority=high")
    assert b"Critical work" in resp.data


def test_dashboard_search(auth):
    auth.post("/dashboard", data={"title": "UniqueTaskName"}, follow_redirects=True)
    resp = auth.get("/dashboard?q=UniqueTaskName")
    assert b"UniqueTaskName" in resp.data
