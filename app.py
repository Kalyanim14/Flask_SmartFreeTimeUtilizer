import os
import re
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
CORS(app, origins=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(","))

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be configured")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
    )


def create_token(username):
    payload = {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def auth_required(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            return jsonify({"message": "Authentication required"}), 401
        try:
            g.username = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])["sub"]
        except jwt.PyJWTError:
            return jsonify({"message": "Session is invalid or expired"}), 401
        return handler(*args, **kwargs)
    return wrapped


def db_error():
    return jsonify({"message": "The service is temporarily unavailable"}), 500


def task_from_row(row):
    for key in ("created_at", "updated_at", "completed_at", "due_at", "reminder_at"):
        if row.get(key) and hasattr(row[key], "isoformat"):
            row[key] = row[key].isoformat()
    return row


def parse_tasks(ai_response):
    sections = re.split(r"\n---+\n", ai_response)
    tasks = []
    for section in sections:
        title_match = re.search(r"^###\s*Task\s*\d+\s*[–-]\s*(.+)$", section, re.MULTILINE)
        if not title_match:
            continue
        title = title_match.group(1).strip()
        description_match = re.search(r"\*\*Detailed Description\*\*\s*\n?([\s\S]*?)(?=\n\*\*Small Tips\*\*|$)", section)
        description = description_match.group(1).strip() if description_match else ""
        tasks.append((title[:255], description))
    return tasks


def parse_tasks(ai_response):
    heading_pattern = re.compile(
        r"^###\s*Task\s*\d+\s*(?:[-–—]|â€“)\s*(.+)$", re.MULTILINE
    )
    matches = list(heading_pattern.finditer(ai_response))
    tasks = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(ai_response)
        section = ai_response[match.end():section_end]
        description_match = re.search(
            r"\*\*Detailed Description\*\*\s*\n?([\s\S]*?)(?=\n\*\*Small Tips\*\*|\n---|$)",
            section,
        )
        description = description_match.group(1).strip() if description_match else section.strip()
        if title:
            tasks.append((title[:255], description))
    return tasks[:3]


def generate_plan(prompt):
    def call(model):
        return client.chat.completions.create(
            extra_headers={"X-Title": "SmartFreeTimeUtilizer"},
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor who provides concise, practical learning tasks."},
                {"role": "user", "content": prompt},
            ],
        ).choices[0].message.content.strip()

    try:
        return call("mistralai/mistral-7b-instruct:free")
    except Exception:
        return call("nvidia/nemotron-3-nano-30b-a3b:free")


def insert_tasks(cursor, username, tasks, skill="General"):
    for title, description in tasks:
        cursor.execute(
            "INSERT INTO tasks (username, title, description, skill) VALUES (%s, %s, %s, %s)",
            (username, title, description, skill[:100]),
        )


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    name, username, password = (data.get("name") or "").strip(), (data.get("username") or "").strip(), data.get("password") or ""
    if not name or not username or len(password) < 8:
        return jsonify({"message": "Name, username, and an 8-character password are required"}), 400
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            return jsonify({"message": "Username is already in use"}), 409
        cursor.execute("INSERT INTO users (username, name, password) VALUES (%s, %s, %s)", (username, name, generate_password_hash(password)))
        connection.commit()
        return jsonify({"message": "Signup successful", "token": create_token(username), "name": name}), 201
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/signin", methods=["POST"])
def signin():
    data = request.get_json(silent=True) or {}
    username, password = (data.get("username") or "").strip(), data.get("password") or ""
    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT name, password FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        is_hashed = user and user["password"].startswith(("scrypt:", "pbkdf2:"))
        valid = user and (check_password_hash(user["password"], password) if is_hashed else user["password"] == password)
        if not valid:
            return jsonify({"message": "Invalid credentials"}), 401
        if not is_hashed:
            cursor.execute("UPDATE users SET password=%s WHERE username=%s", (generate_password_hash(password), username))
            connection.commit()
        return jsonify({"message": "Login successful", "token": create_token(username), "name": user["name"]})
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/process-data", methods=["POST"])
@auth_required
def process_data():
    data = request.get_json(silent=True) or {}
    required = ["name", "age", "topic", "domain", "time_available"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return jsonify({"message": f"Missing field: {', '.join(missing)}"}), 400
    prompt = f"""I am {data['name']}, a {data['age']}-year-old {data['domain']}.
I have {data['time_available']} to learn about {data['topic']}.
Context: {data.get('context') or 'None'}.
Generate exactly 3 learning micro-tasks in this format:
### Task 1 – <Title>
**Detailed Description**
2-4 practical sentences.
**Small Tips**
- Tip 1
- Tip 2
---
Repeat for Task 2 and Task 3."""
    try:
        ai_response = generate_plan(prompt)
        tasks = parse_tasks(ai_response)
        if len(tasks) != 3:
            return jsonify({"message": "The planner could not create all three tasks. Please try again."}), 502
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO ai_history (username, user_prompt, ai_response) VALUES (%s, %s, %s)", (g.username, prompt, ai_response))
        insert_tasks(cursor, g.username, tasks, data["topic"])
        for title, _ in tasks:
            cursor.execute("INSERT INTO history (username, title, timestamp) VALUES (%s, %s, %s)", (g.username, title, int(time.time())))
        connection.commit()
        return jsonify({"success": True, "response": ai_response, "tasks_created": len(tasks)})
    except Exception:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/profile", methods=["GET", "PATCH"])
@auth_required
def profile():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        if request.method == "GET":
            cursor.execute("SELECT username, name FROM users WHERE username=%s", (g.username,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"message": "Profile not found"}), 404
            return jsonify({"profile": user})

        name = (request.get_json(silent=True) or {}).get("name", "").strip()
        if not name:
            return jsonify({"message": "Name is required"}), 400
        cursor.execute("UPDATE users SET name=%s WHERE username=%s", (name[:120], g.username))
        connection.commit()
        return jsonify({"message": "Profile updated", "profile": {"username": g.username, "name": name[:120]}})
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/tasks", methods=["GET", "POST"])
@auth_required
def tasks():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        if request.method == "GET":
            cursor.execute("SELECT * FROM tasks WHERE username=%s ORDER BY created_at DESC", (g.username,))
            return jsonify({"tasks": [task_from_row(row) for row in cursor.fetchall()]})
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"message": "Task title is required"}), 400
        cursor.execute("INSERT INTO tasks (username, title, description, skill, due_at, reminder_at) VALUES (%s,%s,%s,%s,%s,%s)", (g.username, title[:255], (data.get("description") or "").strip(), (data.get("skill") or "General")[:100], data.get("due_at") or None, data.get("reminder_at") or None))
        connection.commit()
        return jsonify({"id": cursor.lastrowid, "message": "Task created"}), 201
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/tasks/<int:task_id>", methods=["PATCH", "DELETE"])
@auth_required
def update_task(task_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM tasks WHERE id=%s AND username=%s", (task_id, g.username))
        if not cursor.fetchone():
            return jsonify({"message": "Task not found"}), 404
        if request.method == "DELETE":
            cursor.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
        else:
            data = request.get_json(silent=True) or {}
            status = data.get("status")
            if status not in {"pending", "progressing", "done", "rejected"}:
                return jsonify({"message": "Invalid task status"}), 400
            completed_at = datetime.now(timezone.utc) if status == "done" else None
            cursor.execute("UPDATE tasks SET status=%s, completed_at=%s WHERE id=%s", (status, completed_at, task_id))
        connection.commit()
        return jsonify({"message": "Task updated"})
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/tasks/replan", methods=["POST"])
@auth_required
def replan():
    data = request.get_json(silent=True) or {}
    action = data.get("action", "restore")
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        if action == "restore":
            cursor.execute("UPDATE tasks SET status='pending' WHERE username=%s AND status='rejected'", (g.username,))
            connection.commit()
            return jsonify({"message": "Rejected tasks moved back to pending", "tasks_created": 0})
        cursor.execute("SELECT title FROM tasks WHERE username=%s AND status='rejected'", (g.username,))
        rejected = [row["title"] for row in cursor.fetchall()]
        prompt = "Create exactly 3 replacement learning tasks with headings `### Task N – Title` and a `**Detailed Description**` for a learner. Avoid these rejected tasks: " + ", ".join(rejected)
        ai_response = generate_plan(prompt)
        generated = parse_tasks(ai_response)
        insert_tasks(cursor, g.username, generated)
        connection.commit()
        return jsonify({"message": "Fresh tasks added", "tasks_created": len(generated)})
    except Exception:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/dashboard", methods=["GET"])
@auth_required
def dashboard():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT status, COUNT(*) AS count FROM tasks WHERE username=%s GROUP BY status", (g.username,))
        counts = {status: 0 for status in ("pending", "progressing", "done", "rejected")}
        counts.update({row["status"]: row["count"] for row in cursor.fetchall()})
        cursor.execute("SELECT skill, COUNT(*) AS total, SUM(status='done') AS completed FROM tasks WHERE username=%s GROUP BY skill ORDER BY completed DESC", (g.username,))
        skills = cursor.fetchall()
        cursor.execute("SELECT DISTINCT DATE(completed_at) AS day FROM tasks WHERE username=%s AND status='done' AND completed_at IS NOT NULL ORDER BY day DESC", (g.username,))
        days = {str(row["day"]) for row in cursor.fetchall()}
        streak = 0
        day = datetime.now(timezone.utc).date()
        while str(day) in days:
            streak += 1
            day -= timedelta(days=1)
        return jsonify({"counts": counts, "skills": skills, "streak": streak, "active_days": list(days)})
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/notifications", methods=["GET"])
@auth_required
def notifications():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, title, status, due_at, reminder_at FROM tasks WHERE username=%s AND status IN ('pending','progressing') AND ((reminder_at IS NOT NULL AND reminder_at <= UTC_TIMESTAMP()) OR (due_at IS NOT NULL AND due_at <= UTC_TIMESTAMP())) ORDER BY COALESCE(reminder_at, due_at)", (g.username,))
        return jsonify({"notifications": [task_from_row(row) for row in cursor.fetchall()]})
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/history", methods=["GET"])
@auth_required
def history():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT ai_response, created_at FROM ai_history WHERE username=%s ORDER BY created_at DESC", (g.username,))
        return jsonify({"history": [task_from_row(row) for row in cursor.fetchall()]})
    except mysql.connector.Error:
        return db_error()
    finally:
        if "cursor" in locals(): cursor.close()
        if "connection" in locals(): connection.close()


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
