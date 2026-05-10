from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import case, inspect, or_, text

from config import Config
from extensions import db, login_manager, socketio
from flask_socketio import join_room, leave_room


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    login_manager.login_view = "login"
    login_manager.login_message_category = "warning"

    from analytics import get_task_analytics
    from models import Task, TaskPriority, TaskStatus, User

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.endpoint and request.endpoint.startswith("api_"):
            return jsonify({"error": "Authentication required"}), 401
        return redirect(url_for("login"))

    def parse_due_date(value):
        value = value.strip()
        if not value:
            return None

        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Use a valid due date.") from None

    def get_task_form_data():
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = parse_due_date(request.form.get("due_date", ""))
        priority = request.form.get("priority", TaskPriority.MEDIUM.value).strip().lower()

        if priority not in {item.value for item in TaskPriority}:
            raise ValueError("Choose a valid priority.")

        if not title:
            raise ValueError("Task title is required.")

        return {
            "title": title,
            "description": description or None,
            "due_date": due_date,
            "priority": priority,
        }

    def get_json_payload():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("Request body must be JSON")
        return data

    def normalize_optional_text(value, field_name):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be text")
        return value.strip() or None

    def normalize_required_text(value, field_name):
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be text")
        value = value.strip()
        if not value:
            raise ValueError(f"{field_name} is required")
        return value

    def normalize_priority(value):
        if value is None:
            value = TaskPriority.MEDIUM.value
        if not isinstance(value, str):
            raise ValueError("Priority must be text")
        priority = value.strip().lower()
        if priority not in {item.value for item in TaskPriority}:
            raise ValueError("Choose a valid priority.")
        return priority

    def normalize_status(value):
        if not isinstance(value, str):
            raise ValueError("Status must be text")
        status = value.strip().lower()
        if status not in {TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value, TaskStatus.DONE.value}:
            raise ValueError("Status must be 'todo', 'in_progress', or 'done'.")
        return status

    def normalize_due_date(value):
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise ValueError("Due date must be text in YYYY-MM-DD format")
        value = value.strip()
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Use a valid due date (YYYY-MM-DD).") from None

    def build_task_insights(tasks):
        today = date.today()
        upcoming_limit = today + timedelta(days=7)
        active_tasks = [task for task in tasks if task.status != TaskStatus.DONE.value]
        overdue = [
            task for task in active_tasks if task.due_date is not None and task.due_date < today
        ]
        due_soon = [
            task
            for task in active_tasks
            if task.due_date is not None and today <= task.due_date <= upcoming_limit
        ]
        completion_rate = round(
            (sum(1 for task in tasks if task.status == TaskStatus.DONE.value) / len(tasks)) * 100
        ) if tasks else 0

        if overdue:
            recommendation = "Start with overdue work before taking on anything new."
        elif due_soon:
            recommendation = "Your next seven days have movement. Review dates before adding more."
        elif active_tasks:
            recommendation = "You have active work without urgent deadlines. Choose one clear next action."
        else:
            recommendation = "Your workspace is clear. Capture the next important outcome."

        return {
            "completion_rate": completion_rate,
            "due_soon": len(due_soon),
            "overdue": len(overdue),
            "recommendation": recommendation,
        }

    def task_to_dict(task):
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    def emit_user_event(event, task_dict=None):
        tasks = Task.query.filter_by(user_id=current_user.id).all()
        stats = {
            "total": len(tasks),
            "todo": sum(1 for t in tasks if t.status == TaskStatus.TODO.value),
            "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS.value),
            "done": sum(1 for t in tasks if t.status == TaskStatus.DONE.value),
            "high": sum(1 for t in tasks if t.priority == TaskPriority.HIGH.value),
        }
        insights = build_task_insights(tasks)
        payload = {"stats": stats, "insights": insights}
        if task_dict is not None:
            payload["task"] = task_dict
        socketio.emit(event, payload, room=str(current_user.id))

    @socketio.on("connect")
    def handle_connect():
        if current_user.is_authenticated:
            join_room(str(current_user.id))

    @socketio.on("disconnect")
    def handle_disconnect():
        if current_user.is_authenticated:
            leave_room(str(current_user.id))

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not name or not email or not password:
                flash("Name, email, and password are required.", "error")
                return render_template("register.html")

            if User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "error")
                return render_template("register.html")

            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome. Your workspace is ready.", "success")
            return redirect(url_for("dashboard"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()

            if not user or not user.check_password(password):
                flash("Invalid email or password.", "error")
                return render_template("login.html")

            login_user(user)
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        if request.method == "POST":
            try:
                form_data = get_task_form_data()
            except ValueError as error:
                flash(str(error), "error")
                return redirect(url_for("dashboard"))

            task = Task(**form_data, user_id=current_user.id)
            db.session.add(task)
            db.session.commit()
            emit_user_event("task_created", task_to_dict(task))
            flash("Task added.", "success")
            return redirect(url_for("dashboard"))

        status_filter = request.args.get("status", "all").lower()
        priority_filter = request.args.get("priority", "all").lower()
        search = request.args.get("q", "").strip()
        task_query = Task.query.filter_by(user_id=current_user.id)
        all_user_tasks = task_query.all()

        if status_filter in {status.value for status in TaskStatus}:
            task_query = task_query.filter_by(status=status_filter)

        if priority_filter in {priority.value for priority in TaskPriority}:
            task_query = task_query.filter_by(priority=priority_filter)

        if search:
            pattern = f"%{search}%"
            task_query = task_query.filter(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )

        tasks = task_query.order_by(
            case(
                (Task.status == TaskStatus.TODO.value, 0),
                (Task.status == TaskStatus.IN_PROGRESS.value, 1),
                else_=2,
            ),
            case(
                (Task.priority == TaskPriority.HIGH.value, 0),
                (Task.priority == TaskPriority.MEDIUM.value, 1),
                else_=2,
            ),
            Task.position.asc().nullsfirst(),
            Task.due_date.is_(None),
            Task.due_date.asc(),
            Task.created_at.desc(),
        ).all()

        stats = {
            "total": len(all_user_tasks),
            "todo": sum(1 for task in all_user_tasks if task.status == TaskStatus.TODO.value),
            "in_progress": sum(1 for task in all_user_tasks if task.status == TaskStatus.IN_PROGRESS.value),
            "done": sum(1 for task in all_user_tasks if task.status == TaskStatus.DONE.value),
            "high": sum(1 for task in all_user_tasks if task.priority == TaskPriority.HIGH.value),
        }
        insights = build_task_insights(all_user_tasks)

        return render_template(
            "dashboard.html",
            insights=insights,
            priority_filter=priority_filter,
            search=search,
            stats=stats,
            status_filter=status_filter,
            tasks=tasks,
        )

    @app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
    @login_required
    def toggle_task(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
        task.status = TaskStatus.TODO.value if task.is_done else TaskStatus.DONE.value
        db.session.commit()
        emit_user_event("task_updated", task_to_dict(task))
        flash("Task updated.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_task(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

        if request.method == "POST":
            try:
                form_data = get_task_form_data()
            except ValueError as error:
                flash(str(error), "error")
                return render_template("edit_task.html", task=task)

            task.title = form_data["title"]
            task.description = form_data["description"]
            task.due_date = form_data["due_date"]
            task.priority = form_data["priority"]
            db.session.commit()
            emit_user_event("task_updated", task_to_dict(task))
            flash("Task updated.", "success")
            return redirect(url_for("dashboard"))

        return render_template("edit_task.html", task=task)

    @app.route("/tasks/export.csv")
    @login_required
    def export_tasks():
        tasks = (
            Task.query.filter_by(user_id=current_user.id)
            .order_by(Task.created_at.desc())
            .all()
        )
        rows = [
            {
                "title": task.title,
                "description": task.description or "",
                "priority": task.priority,
                "status": task.status,
                "due_date": task.due_date.isoformat() if task.due_date else "",
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
            for task in tasks
        ]
        output = StringIO()
        pd.DataFrame(rows).to_csv(output, index=False)
        return Response(
            output.getvalue(),
            headers={"Content-Disposition": "attachment; filename=smart_tasks.csv"},
            mimetype="text/csv",
        )

    @app.route("/tasks/<int:task_id>/delete", methods=["POST"])
    @login_required
    def delete_task(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
        task_dict = task_to_dict(task)
        db.session.delete(task)
        db.session.commit()
        emit_user_event("task_deleted", task_dict)
        flash("Task deleted.", "success")
        return redirect(url_for("dashboard"))

    # REST API routes

    @app.route("/tasks", methods=["POST"])
    @login_required
    def api_add_task():
        try:
            data = get_json_payload()
            title = normalize_required_text(data.get("title"), "Task title")
            description = normalize_optional_text(data.get("description"), "Description")
            priority = normalize_priority(data.get("priority"))
            due_date = normalize_due_date(data.get("due_date"))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            user_id=current_user.id,
        )
        db.session.add(task)
        db.session.commit()
        emit_user_event("task_created", task_to_dict(task))
        return jsonify({"message": "Task added", "task": task_to_dict(task)}), 201

    @app.route("/tasks", methods=["GET"])
    @login_required
    def api_get_tasks():
        status_filter = request.args.get("status", "all").lower()
        priority_filter = request.args.get("priority", "all").lower()
        search = request.args.get("q", "").strip()
        task_query = Task.query.filter_by(user_id=current_user.id)

        if status_filter in {status.value for status in TaskStatus}:
            task_query = task_query.filter_by(status=status_filter)

        if priority_filter in {priority.value for priority in TaskPriority}:
            task_query = task_query.filter_by(priority=priority_filter)

        if search:
            pattern = f"%{search}%"
            task_query = task_query.filter(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )

        tasks = task_query.order_by(
            case(
                (Task.status == TaskStatus.TODO.value, 0),
                (Task.status == TaskStatus.IN_PROGRESS.value, 1),
                else_=2,
            ),
            case(
                (Task.priority == TaskPriority.HIGH.value, 0),
                (Task.priority == TaskPriority.MEDIUM.value, 1),
                else_=2,
            ),
            Task.position.asc().nullsfirst(),
            Task.due_date.is_(None),
            Task.due_date.asc(),
            Task.created_at.desc(),
        ).all()

        return jsonify({"tasks": [task_to_dict(t) for t in tasks]})

    @app.route("/tasks/<int:task_id>", methods=["PUT"])
    @login_required
    def api_update_task(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
        if not task:
            return jsonify({"error": "Task not found"}), 404

        try:
            data = get_json_payload()
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        if "title" in data:
            try:
                task.title = normalize_required_text(data["title"], "Task title")
            except ValueError as error:
                return jsonify({"error": str(error)}), 400

        if "description" in data:
            try:
                task.description = normalize_optional_text(data.get("description"), "Description")
            except ValueError as error:
                return jsonify({"error": str(error)}), 400

        if "priority" in data:
            try:
                task.priority = normalize_priority(data["priority"])
            except ValueError as error:
                return jsonify({"error": str(error)}), 400

        if "due_date" in data:
            try:
                task.due_date = normalize_due_date(data["due_date"])
            except ValueError as error:
                return jsonify({"error": str(error)}), 400

        if "status" in data:
            try:
                task.status = normalize_status(data["status"])
            except ValueError as error:
                return jsonify({"error": str(error)}), 400

        db.session.commit()
        emit_user_event("task_updated", task_to_dict(task))
        return jsonify({"message": "Task updated", "task": task_to_dict(task)})

    @app.route("/tasks/<int:task_id>", methods=["DELETE"])
    @login_required
    def api_delete_task(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
        if not task:
            return jsonify({"error": "Task not found"}), 404

        task_dict = task_to_dict(task)
        db.session.delete(task)
        db.session.commit()
        emit_user_event("task_deleted", task_dict)
        return jsonify({"message": "Task deleted"})

    # ─── Analytics routes ───────────────────────────────────────────

    @app.route("/analytics")
    @login_required
    def analytics_view():
        tasks = Task.query.filter_by(user_id=current_user.id).all()
        analytics = get_task_analytics(tasks)
        return render_template("analytics.html", analytics=analytics)

    @app.route("/api/analytics")
    @login_required
    def api_analytics():
        tasks = Task.query.filter_by(user_id=current_user.id).all()
        analytics = get_task_analytics(tasks)
        return jsonify(analytics)

    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        task_columns = [column["name"] for column in inspector.get_columns("task")]
        if "priority" not in task_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE task ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT 'medium'")
                )
        if "position" not in task_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE task ADD COLUMN position FLOAT DEFAULT 0.0")
                )

    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")
