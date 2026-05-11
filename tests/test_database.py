from datetime import date

from extensions import db
from models import Task, User


def test_task_default_status_and_priority(auth):
    resp = auth.post("/tasks", json={"title": "Defaults test"})
    assert resp.status_code == 201
    task = resp.get_json()["task"]
    assert task["status"] == "todo"
    assert task["priority"] == "medium"


def test_task_user_isolation(auth):
    auth.post("/tasks", json={"title": "Alice task"})
    auth.post("/logout")
    auth.post("/register", data={
        "name": "Bob",
        "email": "bob@test.com",
        "password": "secret",
    })
    resp = auth.get("/tasks")
    assert resp.status_code == 200
    tasks = resp.get_json()["tasks"]
    assert len(tasks) == 0


def test_task_due_date_optional(auth):
    resp = auth.post("/tasks", json={"title": "No due date"})
    assert resp.status_code == 201
    assert resp.get_json()["task"]["due_date"] is None


def test_task_default_position(auth, app):
    resp = auth.post("/tasks", json={"title": "Position test"})
    assert resp.status_code == 201
    task = resp.get_json()["task"]
    from extensions import db
    from models import Task
    row = db.session.get(Task, task["id"])
    assert row.position == 0.0 or row.position is None


def test_task_cascade_delete(auth, app):
    auth.post("/tasks", json={"title": "Cascade me"})
    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None
    assert Task.query.count() == 1
    db.session.delete(user)
    db.session.commit()
    assert Task.query.count() == 0
