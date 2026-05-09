from unittest.mock import patch


def test_emit_on_api_create(auth):
    with patch("extensions.socketio.emit") as mock_emit:
        resp = auth.post("/tasks", json={"title": "WS create"})
        assert resp.status_code == 201
        mock_emit.assert_called_once()
        args, kwargs = mock_emit.call_args
        assert args[0] == "task_created"
        assert "room" in kwargs


def test_emit_on_api_delete(auth):
    resp = auth.post("/tasks", json={"title": "WS delete"})
    tid = resp.get_json()["task"]["id"]
    with patch("extensions.socketio.emit") as mock_emit:
        resp = auth.delete(f"/tasks/{tid}")
        assert resp.status_code == 200
        mock_emit.assert_called_once()
        args, kwargs = mock_emit.call_args
        assert args[0] == "task_deleted"
        assert "room" in kwargs


def test_emit_on_html_create(auth):
    with patch("extensions.socketio.emit") as mock_emit:
        resp = auth.post("/dashboard", data={"title": "HTML task"}, follow_redirects=True)
        assert resp.status_code == 200
        mock_emit.assert_called_once()
        args, kwargs = mock_emit.call_args
        assert args[0] == "task_created"
        assert "room" in kwargs


def test_emit_on_html_toggle(auth):
    auth.post("/dashboard", data={"title": "Toggle me"})
    import re
    html = auth.get("/dashboard").data.decode()
    match = re.search(r"/tasks/(\d+)/toggle", html)
    assert match
    tid = match.group(1)
    with patch("extensions.socketio.emit") as mock_emit:
        auth.post(f"/tasks/{tid}/toggle", follow_redirects=True)
        mock_emit.assert_called_once()
        args, kwargs = mock_emit.call_args
        assert args[0] == "task_updated"
        assert "room" in kwargs
