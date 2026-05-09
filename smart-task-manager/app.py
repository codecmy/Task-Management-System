from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
from flask import Flask, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import case, inspect, or_, text

from config import Config
from extensions import db, login_manager, socketio


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    login_manager.login_view = "login"
    login_manager.login_message_category = "warning"

    from models import Task, TaskPriority, TaskStatus, User

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

    def build_task_insights(tasks):
        today = date.today()
        upcoming_limit = today + timedelta(days=7)
        active_tasks = [task for task in tasks if task.status == TaskStatus.TODO.value]
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
            socketio.emit("task_created", {"title": task.title, "user_id": current_user.id})
            flash("Task added.", "success")
            return redirect(url_for("dashboard"))

        status_filter = request.args.get("status", "all").lower()
        priority_filter = request.args.get("priority", "all").lower()
        search = request.args.get("q", "").strip()
        task_query = Task.query.filter_by(user_id=current_user.id)
        all_user_tasks = task_query.all()

        if status_filter in {TaskStatus.TODO.value, TaskStatus.DONE.value}:
            task_query = task_query.filter_by(status=status_filter)

        if priority_filter in {priority.value for priority in TaskPriority}:
            task_query = task_query.filter_by(priority=priority_filter)

        if search:
            pattern = f"%{search}%"
            task_query = task_query.filter(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )

        tasks = task_query.order_by(
            case((Task.status == TaskStatus.TODO.value, 0), else_=1),
            case(
                (Task.priority == TaskPriority.HIGH.value, 0),
                (Task.priority == TaskPriority.MEDIUM.value, 1),
                else_=2,
            ),
            Task.due_date.is_(None),
            Task.due_date.asc(),
            Task.created_at.desc(),
        ).all()

        stats = {
            "total": len(all_user_tasks),
            "todo": sum(1 for task in all_user_tasks if task.status == TaskStatus.TODO.value),
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
        db.session.delete(task)
        db.session.commit()
        flash("Task deleted.", "success")
        return redirect(url_for("dashboard"))

    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        task_columns = [column["name"] for column in inspector.get_columns("task")]
        if "priority" not in task_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE task ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT 'medium'")
                )

    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, debug=True)
