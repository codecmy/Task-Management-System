from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import case

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

    from models import Task, TaskStatus, User

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
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            due_date_raw = request.form.get("due_date", "").strip()
            due_date = None

            if due_date_raw:
                try:
                    due_date = datetime.strptime(due_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    flash("Use a valid due date.", "error")
                    return redirect(url_for("dashboard"))

            if not title:
                flash("Task title is required.", "error")
                return redirect(url_for("dashboard"))

            task = Task(
                title=title,
                description=description or None,
                due_date=due_date,
                user_id=current_user.id,
            )
            db.session.add(task)
            db.session.commit()
            socketio.emit("task_created", {"title": task.title, "user_id": current_user.id})
            flash("Task added.", "success")
            return redirect(url_for("dashboard"))

        tasks = (
            Task.query.filter_by(user_id=current_user.id)
            .order_by(
                case((Task.status == TaskStatus.TODO.value, 0), else_=1),
                Task.due_date.is_(None),
                Task.due_date.asc(),
                Task.created_at.desc(),
            )
            .all()
        )
        return render_template("dashboard.html", tasks=tasks)

    @app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
    @login_required
    def toggle_task(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
        task.status = TaskStatus.TODO.value if task.is_done else TaskStatus.DONE.value
        db.session.commit()
        flash("Task updated.", "success")
        return redirect(url_for("dashboard"))

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

    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, debug=True)
