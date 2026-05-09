def test_analytics_page_loads(auth):
    resp = auth.get("/analytics")
    assert resp.status_code == 200
    assert b"Analytics" in resp.data or b"analytics" in resp.data.lower()


def test_analytics_shows_zero_state(auth):
    resp = auth.get("/analytics")
    assert b"0" in resp.data


def test_analytics_requires_auth(client):
    resp = client.get("/analytics", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_api_analytics_returns_json(auth):
    resp = auth.get("/api/analytics")
    assert resp.status_code == 200
    assert resp.is_json
    data = resp.get_json()
    assert "total" in data
    assert "completed" in data
    assert "pending" in data
    assert "completion_pct" in data
    assert "by_priority" in data
    assert "overdue" in data
    assert "due_soon" in data


def test_api_analytics_empty(auth):
    resp = auth.get("/api/analytics")
    data = resp.get_json()
    assert data["total"] == 0
    assert data["completed"] == 0
    assert data["pending"] == 0
    assert data["completion_pct"] == 0.0
    assert data["by_priority"] == {"high": 0, "medium": 0, "low": 0}
    assert data["overdue"] == 0
    assert data["due_soon"] == 0


def test_api_analytics_with_tasks(auth):
    auth.post("/tasks", json={"title": "Task A", "priority": "high"})
    auth.post("/tasks", json={"title": "Task B", "priority": "low"})
    auth.post("/tasks", json={"title": "Task C"})
    resp = auth.get("/api/analytics")
    data = resp.get_json()
    assert data["total"] == 3
    assert data["pending"] == 3
    assert data["completed"] == 0
    assert data["by_priority"]["high"] == 1
    assert data["by_priority"]["low"] == 1
    assert data["by_priority"]["medium"] == 1


def test_api_analytics_partial_completion(auth):
    t1 = auth.post("/tasks", json={"title": "Done task"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    auth.post("/tasks", json={"title": "Pending task"})
    resp = auth.get("/api/analytics")
    data = resp.get_json()
    assert data["total"] == 2
    assert data["completed"] == 1
    assert data["pending"] == 1
    assert data["completion_pct"] == 50.0


def test_api_analytics_unauthenticated(client):
    resp = client.get("/api/analytics")
    assert resp.status_code == 401


def test_analytics_module_directly():
    from analytics import get_task_analytics

    class FakeTask:
        def __init__(self, status, priority, due_date=None):
            self.status = status
            self.priority = priority
            self.due_date = due_date

    tasks = [
        FakeTask("todo", "high"),
        FakeTask("done", "low"),
        FakeTask("todo", "medium"),
    ]
    result = get_task_analytics(tasks)
    assert result["total"] == 3
    assert result["completed"] == 1
    assert result["pending"] == 2
    assert result["completion_pct"] == 33.3
    assert result["by_priority"]["high"] == 1


def test_analytics_module_empty():
    from analytics import get_task_analytics

    result = get_task_analytics([])
    assert result["total"] == 0
    assert result["completed"] == 0
    assert result["pending"] == 0
    assert result["completion_pct"] == 0.0
