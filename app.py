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
    titles = []
    titles += re.findall(r"### Task \d+ – (.+)", response_text)
    titles += re.findall(r"\*\*Task\s*\d+\s*–\s*(.+?)\*\*", response_text)
    return [t.strip() for t in titles if t.strip()]

# ================= Auth Routes =================

@app.route("/signup", methods=["POST"])
def signup():
    conn = None
    cursor = None

    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        username = (data.get("username") or "").strip()
        password = data.get("password")

        if not username or not password:
            return jsonify({"message": "Username and password required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            return jsonify({"message": "User already exists!"}), 400

        cursor.execute(
            "INSERT INTO users (username, name, password) VALUES (%s,%s,%s)",
            (username, name, password)
        )

        conn.commit()

        return jsonify({"message": "Signup successful!"}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/signin", methods=["POST"])
def signin():

    conn = None
    cursor = None

    try:
        data = request.get_json() or {}
        username = (data.get("username") or "").strip()
        password = data.get("password")

        if not username or not password:
            return jsonify({"message": "Username and password required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT name,password FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        if user and user["password"] == password:
            return jsonify({
                "message": "Login successful!",
                "name": user["name"]
            }), 200

        return jsonify({"message": "Invalid credentials!"}), 401

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ================= Smart Free Time Utilizer =================

@app.route('/api/process-data', methods=['POST'])
def process_data():

    conn = None
    cursor = None

    try:

        data = request.json or {}

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        for field in ['username','name','age','topic']:
            if not str(data.get(field,'')).strip():
                return jsonify({'error': f'Missing field: {field}'}), 400

        username = data['username']
        name = data['name']
        age = data['age']
        topic = data['topic']
        domain = data.get('domain','general learner')
        time_available = data.get('time_available','Not specified')
        context = data.get('context','Not provided')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ===== Fetch previous titles =====
        cursor.execute(
            "SELECT title FROM history WHERE username=%s ORDER BY timestamp DESC LIMIT 3",
            (username,)
        )

        rows = cursor.fetchall()

        recent_history_summary = (
            "\n".join(f"- {r['title']}" for r in rows)
            if rows else "No prior history."
        )

        # ===== STRICT AI FORMAT PROMPT =====
        user_prompt = f"""
I'm {name}, a {age}-year-old {domain}.

I have {time_available} available to learn about {topic}.

Context: {context}

Previously learned:
{recent_history_summary}

Generate EXACTLY 3 learning micro-tasks.

STRICT FORMAT:

### Task 1 – <Title>

**Detailed Description**
Write 4–6 sentences explaining the task clearly.

**Small Tips**
- Tip 1
- Tip 2
- Tip 3

---

### Task 2 – <Title>

**Detailed Description**
Write 4–6 sentences explaining the task clearly.

**Small Tips**
- Tip 1
- Tip 2
- Tip 3

---

### Task 3 – <Title>

**Detailed Description**
Write 4–6 sentences explaining the task clearly.

**Small Tips**
- Tip 1
- Tip 2
- Tip 3

Rules:
- Use headings exactly like above
- Use bullet points
- Do not add extra sections
"""

        def get_ai_response(model):

            return client.chat.completions.create(

                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "SmartFreeTimeUtilizer"
                },

                model=model,

                messages=[
                    {"role":"system","content":"You are a helpful AI tutor who provides structured learning tasks."},
                    {"role":"user","content":user_prompt}
                ]

            ).choices[0].message.content.strip()

        # ===== AI Call =====
        try:
            ai_response = get_ai_response("mistralai/mistral-7b-instruct:free")
        except Exception as e:
            print("Fallback model used:", e)
            ai_response = get_ai_response("nvidia/nemotron-3-nano-30b-a3b:free")

        # ===== Save FULL AI conversation =====
        cursor.execute(
            """
            INSERT INTO ai_history (username,user_prompt,ai_response)
            VALUES (%s,%s,%s)
            """,
            (username,user_prompt,ai_response)
        )

        # ===== Save titles only =====
        titles = extract_titles(ai_response)

        for title in titles:
            cursor.execute(
                "INSERT INTO history (username,title,timestamp) VALUES (%s,%s,%s)",
                (username,title,int(time.time()))
            )

        conn.commit()

        return jsonify({
            "success":True,
            "response":ai_response
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error':str(e)}),500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ================= AI HISTORY =================

@app.route('/api/ai-history/<username>', methods=['GET'])
def get_ai_history(username):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT user_prompt,ai_response,created_at
        FROM ai_history
        WHERE username=%s
        ORDER BY created_at DESC
        """,
        (username,)
    )

    history = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({"history":history})

# ================= TITLE HISTORY =================

@app.route('/api/history/<username>', methods=['GET'])
def get_history(username):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT ai_response, created_at
        FROM ai_history
        WHERE username=%s
        ORDER BY created_at DESC
    """, (username,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({"history": rows})

@app.route('/api/history/<username>', methods=['DELETE'])
def delete_history(username):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history WHERE username=%s",(username,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message":"History cleared"})

# ================= Health =================

@app.route('/api/health', methods=['GET'])
def health_check():

    return jsonify({
        "status":"healthy",
        "message":"Backend running correctly"
    })

@app.route('/')
def home():

    return jsonify({
        "message":"Flask + MySQL backend running",
        "endpoints":[
            "/signup",
            "/signin",
            "/api/process-data",
            "/api/history/<username>",
            "/api/ai-history/<username>"
        ]
    })

# ================= Run =================

if __name__ == '__main__':

    port = int(os.environ.get('PORT',5000))

    app.run(
        debug=True,
        host='0.0.0.0',
        port=port
    )