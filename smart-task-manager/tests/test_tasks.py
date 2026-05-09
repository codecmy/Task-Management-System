def create_task(auth):
    auth.post("/dashboard", data={"title": "Test task"}, follow_redirects=True)


def get_task_id(auth):
    resp = auth.get("/dashboard")
    html = resp.data.decode()
    import re
    match = re.search(r'/tasks/(\d+)/edit', html)
    return int(match.group(1)) if match else None


def test_toggle_task(auth):
    create_task(auth)
    task_id = get_task_id(auth)
    assert task_id is not None
    resp = auth.post(f"/tasks/{task_id}/toggle", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Task updated" in resp.data


def test_edit_page_loads(auth):
    create_task(auth)
    task_id = get_task_id(auth)
    assert task_id is not None
    resp = auth.get(f"/tasks/{task_id}/edit")
    assert resp.status_code == 200
    assert b"Edit task" in resp.data


def test_edit_task_updates(auth):
    create_task(auth)
    task_id = get_task_id(auth)
    assert task_id is not None
    resp = auth.post(f"/tasks/{task_id}/edit", data={
        "title": "Updated title",
        "priority": "high",
        "due_date": "",
        "description": "New description",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Task updated" in resp.data
    assert b"Updated title" in resp.data


def test_delete_task(auth):
    create_task(auth)
    task_id = get_task_id(auth)
    assert task_id is not None
    resp = auth.post(f"/tasks/{task_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Task deleted" in resp.data


def test_toggle_nonexistent_task(auth):
    resp = auth.post("/tasks/99999/toggle", follow_redirects=True)
    assert resp.status_code == 404


def test_edit_nonexistent_task(auth):
    resp = auth.get("/tasks/99999/edit")
    assert resp.status_code == 404


def test_delete_nonexistent_task(auth):
    resp = auth.post("/tasks/99999/delete", follow_redirects=True)
    assert resp.status_code == 404


def test_export_csv(auth):
    create_task(auth)
    resp = auth.get("/tasks/export.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert b"title" in resp.data
