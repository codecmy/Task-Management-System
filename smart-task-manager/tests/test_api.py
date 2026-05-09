import json


def test_api_unauthenticated_returns_json(client):
    resp = client.get("/tasks")
    assert resp.status_code == 401
    assert resp.is_json
    assert resp.get_json()["error"] == "Authentication required"


def test_api_add_task(auth):
    resp = auth.post("/tasks", json={
        "title": "API task",
        "priority": "high",
        "due_date": "2026-06-15",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["message"] == "Task added"
    assert data["task"]["title"] == "API task"
    assert data["task"]["priority"] == "high"
    assert data["task"]["status"] == "todo"
    assert data["task"]["due_date"] == "2026-06-15"


def test_api_add_task_minimal(auth):
    resp = auth.post("/tasks", json={"title": "Minimal"})
    assert resp.status_code == 201
    assert resp.get_json()["task"]["priority"] == "medium"


def test_api_add_task_missing_title(auth):
    resp = auth.post("/tasks", json={"priority": "high"})
    assert resp.status_code == 400
    assert resp.is_json


def test_api_add_task_invalid_priority(auth):
    resp = auth.post("/tasks", json={
        "title": "Bad",
        "priority": "urgent",
    })
    assert resp.status_code == 400


def test_api_add_task_invalid_due_date(auth):
    resp = auth.post("/tasks", json={
        "title": "Bad date",
        "due_date": "not-a-date",
    })
    assert resp.status_code == 400


def test_api_add_task_not_json(auth):
    resp = auth.post("/tasks", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_api_get_tasks_empty(auth):
    resp = auth.get("/tasks")
    assert resp.status_code == 200
    assert resp.get_json() == {"tasks": []}


def test_api_get_tasks(auth):
    auth.post("/tasks", json={"title": "Task one"})
    auth.post("/tasks", json={"title": "Task two"})
    resp = auth.get("/tasks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["tasks"]) == 2


def test_api_get_tasks_filter_by_status(auth):
    t1 = auth.post("/tasks", json={"title": "Todo task"})
    tid = t1.get_json()["task"]["id"]
    auth.put(f"/tasks/{tid}", json={"status": "done"})
    resp = auth.get("/tasks?status=todo")
    assert len(resp.get_json()["tasks"]) == 0
    resp = auth.get("/tasks?status=done")
    assert len(resp.get_json()["tasks"]) == 1


def test_api_get_tasks_search(auth):
    auth.post("/tasks", json={"title": "Alpha task"})
    auth.post("/tasks", json={"title": "Beta task"})
    resp = auth.get("/tasks?q=Alpha")
    assert len(resp.get_json()["tasks"]) == 1


def test_api_update_task(auth):
    created = auth.post("/tasks", json={"title": "Original"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", json={
        "title": "Updated",
        "status": "done",
        "priority": "high",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["task"]["title"] == "Updated"
    assert data["task"]["status"] == "done"
    assert data["task"]["priority"] == "high"


def test_api_update_task_partial(auth):
    created = auth.post("/tasks", json={
        "title": "Partial",
        "description": "Old desc",
    }).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", json={"description": "New desc"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["task"]["title"] == "Partial"
    assert data["task"]["description"] == "New desc"


def test_api_update_task_not_found(auth):
    resp = auth.put("/tasks/99999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_api_update_task_invalid_status(auth):
    created = auth.post("/tasks", json={"title": "Bad status"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", json={"status": "invalid"})
    assert resp.status_code == 400


def test_api_delete_task(auth):
    created = auth.post("/tasks", json={"title": "Delete me"}).get_json()
    tid = created["task"]["id"]
    resp = auth.delete(f"/tasks/{tid}")
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Task deleted"
    get_resp = auth.get("/tasks")
    assert len(get_resp.get_json()["tasks"]) == 0


def test_api_delete_task_not_found(auth):
    resp = auth.delete("/tasks/99999")
    assert resp.status_code == 404
