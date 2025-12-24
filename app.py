from flask import Flask, request, jsonify
from flask_cors import CORS
import os, traceback, time, re
from dotenv import load_dotenv
from openai import OpenAI
import mysql.connector

# ================= Load ENV =================
load_dotenv()

app = Flask(__name__)
CORS(app)

# ================= MySQL Connection =================
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=int(os.getenv("MYSQL_PORT", 3306))
    )

# ================= OpenRouter Client =================
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# ================= Utilities =================
def extract_titles(response_text):
    """
    Robust title extractor for LLM responses.
    Supports:
    - **Title**: Something
    - **Title**\nSomething
    - ### Title\nSomething
    - **Task 1: Something**
    """

    titles = []

    # Case 1: **Title**: Something
    titles += re.findall(r"\*\*Title\*\*[:\n]\s*(.+)", response_text)

    # Case 2: ### Title\nSomething
    titles += re.findall(r"###\s*Title\s*\n(.+)", response_text)

    # Case 3: **Task X: Something**
    titles += re.findall(r"\*\*Task\s*\d+\s*:\s*(.+?)\*\*", response_text)

    # Cleanup
    return [t.strip() for t in titles if t.strip()]


# ================= Auth Routes =================

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            return jsonify({"message": "User already exists!"}), 400

        cursor.execute(
            "INSERT INTO users (username, name, password) VALUES (%s, %s, %s)",
            (username, name, password)
        )
        conn.commit()
        return jsonify({"message": "Signup successful!"}), 201

    finally:
        cursor.close()
        conn.close()


@app.route("/signin", methods=["POST"])
def signin():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT name, password FROM users WHERE username=%s",
        (username,)
    )
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and user["password"] == password:
        return jsonify({"message": "Login successful!", "name": user["name"]}), 200

    return jsonify({"message": "Invalid credentials!"}), 401

# ================= Smart Free Time Utilizer =================

@app.route('/api/process-data', methods=['POST'])
def process_data():
    try:
        data = request.json or {}
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        for field in ['username', 'name', 'age', 'topic']:
            if not str(data.get(field, '')).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        username = data['username']
        name = data['name']
        age = data['age']
        topic = data['topic']
        domain = data.get('domain', 'general learner')
        time_available = data.get('time_available', 'Not specified')
        context = data.get('context', 'Not provided')

        # ===== Fetch recent history (titles only) =====
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT title FROM history WHERE username=%s ORDER BY timestamp DESC LIMIT 3",
            (username,)
        )
        rows = cursor.fetchall()

        recent_history_summary = (
            "\n".join(f"- {r['title']}" for r in rows)
            if rows else "No prior history."
        )

        user_prompt = (
            f"I'm {name}, a {age}-year-old in {domain}. "
            f"I have {time_available} to learn {topic} in context: {context}. "
            f"Previously I have learnt about:\n{recent_history_summary}\n\n"
            "Please provide EXACTLY 3 micro-tasks. For EACH task, give this structure:\n"
            "1. **Title**:\n"
            "2. **Detailed Description** (4–6 sentences)\n"
            "3. **Small Tips** (bullet list of 3 items)\n\n"
            "Use clear headings and proper formatting."
        )

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "SmartFreeTimeUtilizer"
            },
            model="tngtech/deepseek-r1t2-chimera:free",
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor who provides structured, well-formatted learning tasks."},
                {"role": "user", "content": user_prompt}
            ]
        )

        ai_response = completion.choices[0].message.content.strip()

        # ===== Store ONLY titles =====
        titles = extract_titles(ai_response)
        for title in titles:
            cursor.execute(
                "INSERT INTO history (username, title, timestamp) VALUES (%s, %s, %s)",
                (username, title, int(time.time()))
            )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "response": ai_response
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ================= History Routes =================

@app.route('/api/history/<username>', methods=['GET'])
@app.route('/history/<username>', methods=['GET'])
def get_history(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT title, timestamp FROM history WHERE username=%s ORDER BY timestamp DESC",
        (username,)
    )
    history = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify({"history": history}), 200


@app.route('/api/history/<username>', methods=['DELETE'])
def delete_history(username):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history WHERE username=%s", (username,))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({"message": "History cleared"}), 200

# ================= Health & Home =================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Backend running correctly"
    })

@app.route('/')
def home():
    return jsonify({
        "message": "Flask + MySQL backend is running",
        "endpoints": [
            "/signup",
            "/signin",
            "/api/process-data",
            "/api/history/<username>"
        ]
    })

# ================= Run =================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
