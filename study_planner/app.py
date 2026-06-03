import os
import sqlite3
from datetime import date
from functools import wraps

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    g,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash


# ─────────────────────────────────────────────────────────────
# APP CONFIG
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-this")
app.config["DB_PATH"] = os.path.join(app.root_path, "study_planner.db")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"
login_manager.login_message = "Please log in to continue."


# ─────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def column_exists(conn, table_name, column_name):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(col["name"] == column_name for col in cols)


def init_db():
    conn = sqlite3.connect(app.config["DB_PATH"])
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            color TEXT DEFAULT '#6366f1',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            deadline TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            subject_id INTEGER,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        );

        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            duration INTEGER NOT NULL,
            date TEXT DEFAULT CURRENT_DATE,
            subject_id INTEGER,
            user_id INTEGER NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_hours INTEGER NOT NULL,
            progress_hours REAL DEFAULT 0,
            user_id INTEGER NOT NULL,
            deadline TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Simple migrations for older DB files
    if not column_exists(conn, "subjects", "color"):
        conn.execute("ALTER TABLE subjects ADD COLUMN color TEXT DEFAULT '#6366f1'")

    if not column_exists(conn, "tasks", "created_at"):
        conn.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")

    if not column_exists(conn, "notifications", "created_at"):
        conn.execute("ALTER TABLE notifications ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")

    if not column_exists(conn, "goals", "deadline"):
        conn.execute("ALTER TABLE goals ADD COLUMN deadline TEXT")

    if not column_exists(conn, "study_sessions", "notes"):
        conn.execute("ALTER TABLE study_sessions ADD COLUMN notes TEXT")

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# USER MODEL
# ─────────────────────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, user_id, name, email):
        self.id = str(user_id)
        self.name = name
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        return User(user["id"], user["name"], user["email"])
    return None


# ─────────────────────────────────────────────────────────────
# SMALL HELPERS
# ─────────────────────────────────────────────────────────────
def guest_only(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return view_func(*args, **kwargs)
    return wrapper


def clean_email(value):
    return (value or "").strip().lower()


def clean_text(value):
    return (value or "").strip()


# ─────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard" if current_user.is_authenticated else "login"))


@app.route("/register", methods=["GET", "POST"])
@guest_only
def register():
    if request.method == "POST":
        name = clean_text(request.form.get("name"))
        email = clean_email(request.form.get("email"))
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            flash("This email is already registered.", "error")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()

        flash("Account created successfully. Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@guest_only
def login():
    if request.method == "POST":
        email = clean_email(request.form.get("email"))
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        login_user(User(user["id"], user["name"], user["email"]), remember=True)
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    uid = current_user.id
    today = date.today().isoformat()

    tasks = conn.execute("""
        SELECT t.*, s.name AS subject_name
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE t.user_id = ?
        ORDER BY
            CASE t.priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                ELSE 3
            END,
            t.deadline ASC
    """, (uid,)).fetchall()

    goals = conn.execute(
        "SELECT * FROM goals WHERE user_id = ? ORDER BY id DESC",
        (uid,)
    ).fetchall()

    subjects = conn.execute(
        "SELECT * FROM subjects WHERE user_id = ? ORDER BY id DESC",
        (uid,)
    ).fetchall()

    total_minutes = conn.execute(
        "SELECT COALESCE(SUM(duration), 0) FROM study_sessions WHERE user_id = ?",
        (uid,)
    ).fetchone()[0]

    today_minutes = conn.execute(
        "SELECT COALESCE(SUM(duration), 0) FROM study_sessions WHERE user_id = ? AND date = ?",
        (uid, today)
    ).fetchone()[0]

    completed_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'Completed'",
        (uid,)
    ).fetchone()[0]

    pending_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'Pending'",
        (uid,)
    ).fetchone()[0]

    overdue_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'Pending' AND deadline < ?",
        (uid, today)
    ).fetchone()[0]

    notifications = conn.execute("""
        SELECT *
        FROM notifications
        WHERE user_id = ? AND is_read = 0
        ORDER BY created_at DESC, id DESC
    """, (uid,)).fetchall()

    weekly_rows = conn.execute("""
        SELECT date, SUM(duration) AS total
        FROM study_sessions
        WHERE user_id = ?
        GROUP BY date
        ORDER BY date DESC
        LIMIT 7
    """, (uid,)).fetchall()
    weekly = [dict(row) for row in weekly_rows]

    subject_stats_rows = conn.execute("""
        SELECT s.name, SUM(ss.duration) AS total_mins
        FROM study_sessions ss
        JOIN subjects s ON ss.subject_id = s.id
        WHERE ss.user_id = ?
        GROUP BY s.id
        ORDER BY total_mins DESC
        LIMIT 5
    """, (uid,)).fetchall()
    subject_stats = [dict(row) for row in subject_stats_rows]

    return render_template(
        "dashboard.html",
        tasks=tasks,
        goals=goals,
        subjects=subjects,
        total_hours=round(total_minutes / 60, 1),
        today_hours=round(today_minutes / 60, 1),
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        overdue_tasks=overdue_tasks,
        notifications=notifications,
        weekly=weekly,
        subject_stats=subject_stats,
        today=today,
    )


# ─────────────────────────────────────────────────────────────
# SUBJECTS
# ─────────────────────────────────────────────────────────────
@app.route("/add_subject", methods=["POST"])
@login_required
def add_subject():
    name = clean_text(request.form.get("name"))
    color = request.form.get("color", "#6366f1")

    if not name:
        flash("Subject name is required.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()
    conn.execute(
        "INSERT INTO subjects (name, user_id, color) VALUES (?, ?, ?)",
        (name, current_user.id, color)
    )
    conn.commit()

    flash("Subject added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_subject/<int:sid>")
@login_required
def delete_subject(sid):
    conn = get_db()
    conn.execute(
        "DELETE FROM subjects WHERE id = ? AND user_id = ?",
        (sid, current_user.id)
    )
    conn.commit()

    flash("Subject deleted.", "success")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────────────────────
@app.route("/add_task", methods=["POST"])
@login_required
def add_task():
    title = clean_text(request.form.get("title"))
    deadline = request.form.get("deadline") or None
    priority = request.form.get("priority", "Medium")
    subject_id = request.form.get("subject_id") or None

    if not title:
        flash("Task title is required.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()
    conn.execute("""
        INSERT INTO tasks (title, deadline, priority, subject_id, user_id)
        VALUES (?, ?, ?, ?, ?)
    """, (title, deadline, priority, subject_id, current_user.id))
    conn.commit()

    flash("Task added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/complete_task/<int:tid>")
@login_required
def complete_task(tid):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET status = 'Completed' WHERE id = ? AND user_id = ?",
        (tid, current_user.id)
    )
    conn.commit()

    flash("Task marked as completed.", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_task/<int:tid>")
@login_required
def delete_task(tid):
    conn = get_db()
    conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (tid, current_user.id)
    )
    conn.commit()

    flash("Task deleted.", "success")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────────────────────
# GOALS
# ─────────────────────────────────────────────────────────────
@app.route("/add_goal", methods=["POST"])
@login_required
def add_goal():
    title = clean_text(request.form.get("title"))
    target_hours = request.form.get("target_hours", 0)
    deadline = request.form.get("deadline") or None

    if not title:
        flash("Goal title is required.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()
    conn.execute("""
        INSERT INTO goals (title, target_hours, user_id, deadline)
        VALUES (?, ?, ?, ?)
    """, (title, target_hours, current_user.id, deadline))
    conn.commit()

    flash("Goal created successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_goal/<int:gid>")
@login_required
def delete_goal(gid):
    conn = get_db()
    conn.execute(
        "DELETE FROM goals WHERE id = ? AND user_id = ?",
        (gid, current_user.id)
    )
    conn.commit()

    flash("Goal deleted.", "success")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────────────────────
# STUDY SESSIONS
# ─────────────────────────────────────────────────────────────
@app.route("/add_session", methods=["POST"])
@login_required
def add_session():
    duration = int(request.form.get("duration", 0) or 0)
    subject_id = request.form.get("subject_id") or None
    notes = clean_text(request.form.get("notes"))
    today = date.today().isoformat()

    if duration <= 0:
        flash("Session duration must be greater than 0.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()
    conn.execute("""
        INSERT INTO study_sessions (duration, date, subject_id, user_id, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (duration, today, subject_id, current_user.id, notes))

    hours = duration / 60
    goals = conn.execute(
        "SELECT id FROM goals WHERE user_id = ?",
        (current_user.id,)
    ).fetchall()

    for goal in goals:
        conn.execute("""
            UPDATE goals
            SET progress_hours = MIN(target_hours, progress_hours + ?)
            WHERE id = ?
        """, (hours, goal["id"]))

    conn.commit()

    flash("Study session logged successfully.", "success")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────────────────────
@app.route("/check_reminders")
@login_required
def check_reminders():
    conn = get_db()
    uid = current_user.id
    today = date.today().isoformat()

    overdue_tasks = conn.execute("""
        SELECT title
        FROM tasks
        WHERE user_id = ? AND status = 'Pending' AND deadline < ?
    """, (uid, today)).fetchall()

    added_count = 0

    for task in overdue_tasks:
        existing = conn.execute(
            "SELECT id FROM notifications WHERE user_id = ? AND message LIKE ?",
            (uid, f"%{task['title']}%")
        ).fetchone()

        if not existing:
            conn.execute(
                "INSERT INTO notifications (message, user_id) VALUES (?, ?)",
                (f"⚠️ Task overdue: {task['title']}", uid)
            )
            added_count += 1

    conn.commit()

    if added_count:
        flash(f"{added_count} reminder(s) added.", "success")
    else:
        flash("No new reminders found.", "info")

    return redirect(url_for("dashboard"))


@app.route("/mark_read/<int:nid>")
@login_required
def mark_read(nid):
    conn = get_db()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (nid, current_user.id)
    )
    conn.commit()

    flash("Notification marked as read.", "success")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    app.run(debug=True)