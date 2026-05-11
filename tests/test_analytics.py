from datetime import date, datetime, timedelta

import pytest


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
    assert "focus_score" in data
    assert "on_time_pct" in data
    assert "avg_completion_days" in data
    assert "streak" in data
    assert "today_completed" in data
    assert "velocity" in data
    assert "productivity_score" in data
    assert "weekly_completions" in data
    assert "weekly_labels" in data
    assert "weekly_high_priority" in data
    assert "weekly_start_dates" in data
    assert "weekly_end_dates" in data
    assert "streak_days" in data
    assert "percentile" in data
    assert "completions_this_week" in data
    assert "completions_this_month" in data
    assert "high_this_week" in data
    assert "high_this_month" in data


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
    assert data["focus_score"] == 0.0
    assert data["on_time_pct"] == 100.0
    assert data["avg_completion_days"] == 0.0
    assert data["streak"] == 0
    assert data["today_completed"] is False
    assert data["velocity"] == 0.0
    assert data["productivity_score"] == 0.0
    assert data["completions_this_week"] == 0
    assert data["completions_this_month"] == 0
    assert data["high_this_week"] == 0
    assert data["high_this_month"] == 0
    assert len(data["weekly_completions"]) == 8
    assert len(data["weekly_labels"]) == 8
    assert len(data["weekly_high_priority"]) == 8
    assert len(data["weekly_start_dates"]) == 8
    assert len(data["weekly_end_dates"]) == 8
    assert len(data["streak_days"]) == 49
    assert all(c == 0 for c in data["weekly_completions"])
    assert all(c == 0 for c in data["weekly_high_priority"])
    assert all(d["count"] == 0 for d in data["streak_days"])


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
    assert data["focus_score"] == 0.0
    assert isinstance(data["streak"], int)
    assert isinstance(data["velocity"], float)
    assert isinstance(data["productivity_score"], float)


def test_api_analytics_unauthenticated(client):
    resp = client.get("/api/analytics")
    assert resp.status_code == 401


def test_analytics_overdue_calculation(auth):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    auth.post("/tasks", json={"title": "Overdue task", "due_date": yesterday})
    data = auth.get("/api/analytics").get_json()
    assert data["overdue"] == 1
    assert data["due_soon"] == 0


def test_analytics_due_soon_calculation(auth):
    soon = (date.today() + timedelta(days=3)).isoformat()
    auth.post("/tasks", json={"title": "Soon task", "due_date": soon})
    data = auth.get("/api/analytics").get_json()
    assert data["due_soon"] == 1
    assert data["overdue"] == 0


def test_dashboard_insight_recommendations(auth):
    resp = auth.get("/dashboard")
    assert b"Capture the next important outcome" in resp.data

    auth.post("/tasks", json={"title": "Active task"})
    resp = auth.get("/dashboard")
    assert b"active work without urgent deadlines" in resp.data

    soon = (date.today() + timedelta(days=3)).isoformat()
    auth.post("/tasks", json={"title": "Soon task", "due_date": soon})
    resp = auth.get("/dashboard")
    assert b"next seven days" in resp.data

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    auth.post("/tasks", json={"title": "Overdue task", "due_date": yesterday})
    resp = auth.get("/dashboard")
    assert b"overdue work" in resp.data


def test_analytics_module_directly():
    from analytics import get_task_analytics

    class FakeTask:
        def __init__(self, status, priority, due_date=None,
                     created_at=None, completed_at=None):
            self.status = status
            self.priority = priority
            self.due_date = due_date
            self.created_at = created_at
            self.completed_at = completed_at

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
    assert result["focus_score"] == 0.0
    assert result["on_time_pct"] == 100.0
    assert result["avg_completion_days"] == 0.0
    assert result["streak"] == 0
    assert result["today_completed"] is False
    assert result["velocity"] == 0.0
    assert result["productivity_score"] == 31.7
    assert result["completions_this_week"] == 0
    assert result["completions_this_month"] == 0
    assert len(result["weekly_completions"]) == 8
    assert len(result["weekly_labels"]) == 8
    assert len(result["streak_days"]) == 49


def test_analytics_module_empty():
    from analytics import get_task_analytics

    result = get_task_analytics([])
    assert result["total"] == 0
    assert result["completed"] == 0
    assert result["pending"] == 0
    assert result["completion_pct"] == 0.0
    assert result["focus_score"] == 0.0
    assert result["on_time_pct"] == 100.0
    assert result["avg_completion_days"] == 0.0
    assert result["streak"] == 0
    assert result["today_completed"] is False
    assert result["velocity"] == 0.0
    assert result["productivity_score"] == 0.0
    assert len(result["weekly_completions"]) == 8
    assert all(c == 0 for c in result["weekly_completions"])
    assert len(result["streak_days"]) == 49
    assert all(d["count"] == 0 for d in result["streak_days"])


# ─── completed_at tests ─────────────────────────────────────────────


def test_completed_at_set_when_done_via_api(auth):
    created = auth.post("/tasks", json={"title": "Finish me"}).get_json()
    tid = created["task"]["id"]
    assert created["task"]["completed_at"] is None

    resp = auth.put(f"/tasks/{tid}", json={"status": "done"})
    data = resp.get_json()
    assert data["task"]["status"] == "done"
    assert data["task"]["completed_at"] is not None


def test_completed_at_cleared_when_undone_via_api(auth):
    created = auth.post("/tasks", json={"title": "Toggle me"}).get_json()
    tid = created["task"]["id"]
    auth.put(f"/tasks/{tid}", json={"status": "done"})
    resp = auth.put(f"/tasks/{tid}", json={"status": "todo"})
    data = resp.get_json()
    assert data["task"]["status"] == "todo"
    assert data["task"]["completed_at"] is None


def test_completed_at_set_via_toggle(auth):
    auth.post("/dashboard", data={"title": "Toggle task"}, follow_redirects=True)
    resp = auth.get("/dashboard")
    import re
    match = re.search(r'/tasks/(\d+)/toggle', resp.data.decode())
    assert match is not None
    tid = match.group(1)
    auth.post(f"/tasks/{tid}/toggle", follow_redirects=True)
    resp = auth.get("/tasks")
    tasks = resp.get_json()["tasks"]
    task = next(t for t in tasks if t["id"] == int(tid))
    assert task["status"] == "done"
    assert task["completed_at"] is not None


def test_completed_at_in_task_dict(auth):
    resp = auth.post("/tasks", json={"title": "Check field"})
    task = resp.get_json()["task"]
    assert "completed_at" in task
    assert task["completed_at"] is None


# ─── Focus score tests ──────────────────────────────────────────────


def test_focus_score_all_high_priority(auth):
    t1 = auth.post("/tasks", json={"title": "A", "priority": "high"}).get_json()
    t2 = auth.post("/tasks", json={"title": "B", "priority": "high"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    auth.put(f"/tasks/{t2['task']['id']}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert data["focus_score"] == 100.0


def test_focus_score_mixed(auth):
    t1 = auth.post("/tasks", json={"title": "A", "priority": "high"}).get_json()
    t2 = auth.post("/tasks", json={"title": "B", "priority": "low"}).get_json()
    t3 = auth.post("/tasks", json={"title": "C", "priority": "medium"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    auth.put(f"/tasks/{t2['task']['id']}", json={"status": "done"})
    auth.put(f"/tasks/{t3['task']['id']}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert data["focus_score"] == pytest.approx(33.3, abs=0.1)


# ─── On-time rate tests ─────────────────────────────────────────────


def test_on_time_rate_all_on_time(auth):
    today_iso = date.today().isoformat()
    t1 = auth.post("/tasks", json={
        "title": "A", "due_date": today_iso,
    }).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert data["on_time_pct"] == 100.0


def test_on_time_rate_late(auth):
    yesterday = (date.today() - timedelta(days=2)).isoformat()
    t1 = auth.post("/tasks", json={
        "title": "Late", "due_date": yesterday,
    }).get_json()
    t2 = auth.post("/tasks", json={
        "title": "On time", "due_date": yesterday,
    }).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    old_completed = datetime.utcnow() - timedelta(days=5)
    created = auth.post("/tasks", json={
        "title": "Already late",
        "due_date": (date.today() - timedelta(days=10)).isoformat(),
    }).get_json()
    tid = created["task"]["id"]
    auth.put(f"/tasks/{tid}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert data["on_time_pct"] < 100.0


# ─── Streak tests ───────────────────────────────────────────────────


def test_streak_basic(auth):
    t1 = auth.post("/tasks", json={"title": "A"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    resp = auth.get("/api/analytics")
    data = resp.get_json()
    assert isinstance(data["streak"], int)
    assert isinstance(data["today_completed"], bool)
    assert isinstance(data["streak_days"], list)
    assert len(data["streak_days"]) == 49
    first = data["streak_days"][0]
    assert "date" in first
    assert "count" in first
    assert "day_name" in first


# ─── Velocity tests ─────────────────────────────────────────────────


def test_velocity_with_completions(auth):
    for i in range(5):
        t = auth.post("/tasks", json={"title": f"Task {i}"}).get_json()
        auth.put(f"/tasks/{t['task']['id']}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert data["velocity"] >= 0.0
    assert data["completions_this_week"] >= 1


# ─── Productivity score tests ───────────────────────────────────────


def test_productivity_score_in_range(auth):
    t1 = auth.post("/tasks", json={"title": "A", "priority": "high"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert 0.0 <= data["productivity_score"] <= 100.0


# ─── Percentile tests ───────────────────────────────────────────────


def test_percentile_in_api(auth):
    t1 = auth.post("/tasks", json={"title": "A"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert "percentile" in data
    assert 0.0 <= data["percentile"] <= 100.0


def test_percentile_single_user(auth):
    data = auth.get("/api/analytics").get_json()
    assert data["percentile"] == 100.0


# ─── Date filter tests ──────────────────────────────────────────────


def test_dashboard_date_filter_completed_after(auth):
    t1 = auth.post("/tasks", json={"title": "Older"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    t2 = auth.post("/tasks", json={"title": "Never done"}).get_json()
    resp = auth.get(f"/dashboard?completed_after={date.today().isoformat()}")
    assert resp.status_code == 200


def test_dashboard_date_filter_completed_before(auth):
    future = (date.today() + timedelta(days=30)).isoformat()
    resp = auth.get(f"/dashboard?completed_before={future}")
    assert resp.status_code == 200


# ─── compute_all_user_scores / get_percentile unit tests ────────────


def test_compute_all_user_scores_and_percentile_integration(auth):
    t1 = auth.post("/tasks", json={"title": "A", "priority": "high"}).get_json()
    auth.put(f"/tasks/{t1['task']['id']}", json={"status": "done"})
    data = auth.get("/api/analytics").get_json()
    assert "percentile" in data
    assert 0.0 <= data["percentile"] <= 100.0


def test_get_percentile_single():
    from analytics import get_percentile

    assert get_percentile(50.0, []) == 100.0
    assert get_percentile(50.0, [50.0]) == 100.0


def test_get_percentile_various():
    from analytics import get_percentile

    scores = [10, 20, 30, 40, 50]
    assert get_percentile(25, scores) == 40.0
    assert get_percentile(10, scores) == 0.0
    assert get_percentile(60, scores) == 100.0
    assert get_percentile(30, scores) == 40.0
