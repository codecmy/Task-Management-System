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


def test_api_update_task_non_json_body(auth):
    created = auth.post("/tasks", json={"title": "Test"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", data="not json", content_type="application/json")
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


def test_api_add_task_with_in_progress_status(auth):
    resp = auth.post("/tasks", json={
        "title": "In progress task",
        "status": "in_progress",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["task"]["status"] == "todo"


def test_api_update_task_to_in_progress(auth):
    created = auth.post("/tasks", json={"title": "Start task"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.get_json()["task"]["status"] == "in_progress"


def test_api_get_tasks_filter_by_in_progress(auth):
    auth.post("/tasks", json={"title": "Task one"})
    t = auth.post("/tasks", json={"title": "In prog"}).get_json()
    auth.put(f"/tasks/{t['task']['id']}", json={"status": "in_progress"})
    resp = auth.get("/tasks?status=in_progress")
    assert len(resp.get_json()["tasks"]) == 1
    assert resp.get_json()["tasks"][0]["title"] == "In prog"


def test_api_get_tasks_filter_by_invalid_status(auth):
    auth.post("/tasks", json={"title": "Visible"})
    resp = auth.get("/tasks?status=invalid")
    assert len(resp.get_json()["tasks"]) == 1


def test_api_get_tasks_filter_by_priority(auth):
    auth.post("/tasks", json={"title": "High", "priority": "high"})
    auth.post("/tasks", json={"title": "Low", "priority": "low"})
    resp = auth.get("/tasks?priority=high")
    tasks = resp.get_json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "High"


def test_api_update_task_invalid_title_empty(auth):
    created = auth.post("/tasks", json={"title": "Original"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", json={"title": ""})
    assert resp.status_code == 400


def test_api_update_task_invalid_priority(auth):
    created = auth.post("/tasks", json={"title": "Original"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", json={"priority": "urgent"})
    assert resp.status_code == 400


def test_api_update_task_invalid_due_date(auth):
    created = auth.post("/tasks", json={"title": "Original"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}", json={"due_date": "bad-date"})
    assert resp.status_code == 400


def test_api_unauthorized_on_post(unauth_client):
    resp = unauth_client.post("/tasks", json={"title": "Nope"})
    assert resp.status_code == 401
    assert resp.is_json
    assert resp.get_json()["error"] == "Authentication required"


def test_api_unauthorized_on_put(unauth_client):
    resp = unauth_client.put("/tasks/1", json={"title": "Nope"})
    assert resp.status_code == 401
    assert resp.is_json
    assert resp.get_json()["error"] == "Authentication required"


def test_api_unauthorized_on_delete(unauth_client):
    resp = unauth_client.delete("/tasks/1")
    assert resp.status_code == 401
    assert resp.is_json
    assert resp.get_json()["error"] == "Authentication required"


# ─── Kanban API tests ────────────────────────────────────────────────


def test_kanban_requires_auth(client):
    resp = client.get("/api/kanban")
    assert resp.status_code == 401
    assert resp.is_json


def test_kanban_status_grouping(auth):
    auth.post("/tasks", json={"title": "Task A", "priority": "high"})
    auth.post("/tasks", json={"title": "Task B", "priority": "low"})
    auth.post("/tasks", json={"title": "Task C", "priority": "medium"})
    resp = auth.get("/api/kanban?group_by=status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["view"] == "status"
    assert len(data["columns"]) == 3
    todo_col = [c for c in data["columns"] if c["key"] == "todo"][0]
    assert todo_col["count"] == 3
    assert todo_col["label"] == "To Do"
    assert len(todo_col["tasks"]) == 3


def test_kanban_priority_grouping(auth):
    auth.post("/tasks", json={"title": "Task A", "priority": "high"})
    auth.post("/tasks", json={"title": "Task B", "priority": "low"})
    auth.post("/tasks", json={"title": "Task C", "priority": "medium"})
    resp = auth.get("/api/kanban?group_by=priority")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["view"] == "priority"
    assert len(data["columns"]) == 3
    for col in data["columns"]:
        assert "key" in col
        assert "label" in col
        assert "count" in col
        assert "tasks" in col


def test_kanban_invalid_group_by(auth):
    resp = auth.get("/api/kanban?group_by=invalid")
    assert resp.status_code == 400
    assert resp.is_json


def test_kanban_empty(auth):
    resp = auth.get("/api/kanban")
    data = resp.get_json()
    for col in data["columns"]:
        assert col["count"] == 0
        assert col["tasks"] == []


def test_move_task(auth):
    created = auth.post("/tasks", json={"title": "Movable"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}/move", json={
        "status": "in_progress",
        "position": 0.0,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["task"]["status"] == "in_progress"
    assert data["message"] == "Task moved"


def test_move_task_no_position(auth):
    created = auth.post("/tasks", json={"title": "Auto position"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}/move", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.get_json()["task"]["status"] == "done"


def test_move_task_invalid_status(auth):
    created = auth.post("/tasks", json={"title": "Bad move"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}/move", json={"status": "invalid"})
    assert resp.status_code == 400


def test_move_task_no_status(auth):
    created = auth.post("/tasks", json={"title": "No status"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}/move", json={"position": 0.0})
    assert resp.status_code == 400


def test_move_task_not_found(auth):
    resp = auth.put("/tasks/99999/move", json={"status": "done"})
    assert resp.status_code == 404


def test_reorder_task(auth):
    created = auth.post("/tasks", json={"title": "Reorder me"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}/reorder", json={"position": 5.0})
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Task reordered"


def test_reorder_task_no_position(auth):
    created = auth.post("/tasks", json={"title": "No pos"}).get_json()
    tid = created["task"]["id"]
    resp = auth.put(f"/tasks/{tid}/reorder", json={})
    assert resp.status_code == 400


def test_reorder_task_not_found(auth):
    resp = auth.put("/tasks/99999/reorder", json={"position": 0.0})
    assert resp.status_code == 404
