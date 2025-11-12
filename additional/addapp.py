from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, traceback, time, re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
CORS(app)

USERS_FILE = "users.json"
HISTORY_FILE = "history.json"  # store compact user interaction summaries

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# ========== Utility Functions ==========

def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_json_file(filename, data):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_users():
    return load_json_file(USERS_FILE)

def save_users(users):
    save_json_file(USERS_FILE, users)

def load_history():
    return load_json_file(HISTORY_FILE)

def save_history(history):
    save_json_file(HISTORY_FILE, history)


# ========== Auth Routes ==========

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    users = load_users()
    if username in users:
        return jsonify({"message": "User already exists!"}), 400

    users[username] = {"name": name, "password": password}
    save_users(users)
    return jsonify({"message": "Signup successful!"}), 201


@app.route("/signin", methods=["POST"])
def signin():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    users = load_users()
    user = users.get(username)

    if user:
        if isinstance(user, str) and user == password:
            return jsonify({"message": "Login successful!", "name": ""}), 200
        if isinstance(user, dict) and user.get("password") == password:
            return jsonify({"message": "Login successful!", "name": user.get("name", "")}), 200

    return jsonify({"message": "Invalid credentials!"}), 401


# ========== Smart Free Time Utilizer Route ==========

@app.route('/api/process-data', methods=['POST'])
def process_data():
    try:
        data = request.json or {}
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        required_fields = ['username', 'name', 'age', 'topic']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        username = data['username']
        name = data['name']
        age = data['age']
        topic = data['topic']
        domain = data.get('domain', 'general learner')
        time_available = data.get('time_available', 'Not specified')
        context = data.get('context', 'Not provided')

        # Load previous user history
        history = load_history()
        user_history = history.get(username, [])
        recent_history_summary = "\n".join(
            [f"- {h.get('prompt_summary','?')} → {h.get('response_summary','')}" for h in user_history[-3:]]
        ) if user_history else "No prior history."

        user_prompt = (
            f"I'm {name}, a {age}-year-old in {domain}. "
            f"I have {time_available} to learn {topic} in context: {context}. "
            f"Previously I have learnt about:\n{recent_history_summary}\n\n"
            "Please provide EXACTLY 3 micro-tasks. For EACH task, give this structure:\n"
            "1. **Title**\n"
            "2. **Detailed Description** (4–6 sentences)\n"
            "3. **Small Tips** (bullet list of 3 items)\n\n"
            "Respond in clear sections."
        )

        # Call model with fallback
        try:
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "SmartFreeTimeUtilizer"
                },
                model="tngtech/deepseek-r1t2-chimera:free",
                messages=[
                    {"role": "system", "content": "You are a helpful AI tutor who provides structured, easy-to-follow learning tasks."},
                    {"role": "user", "content": user_prompt}
                ]
            )
        except Exception as e:
            print("⚠️ Deepseek failed, switching to backup:", e)
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "SmartFreeTimeUtilizer"
                },
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=[
                    {"role": "system", "content": "You are a helpful AI tutor who provides structured, easy-to-follow learning tasks."},
                    {"role": "user", "content": user_prompt}
                ]
            )

        ai_response_str = completion.choices[0].message.content.strip()

        # ---------- JSON-safe fallback ----------
        ai_response = ai_response_str
        prompt_summary = topic
        try:
            # Extract **Task Titles** from markdown
            titles = re.findall(r"## Task \d+: \*\*(.*?)\*\*", ai_response_str)
            if titles:
                prompt_summary = ", ".join(titles)
        except Exception as e:
            print(f"⚠️ Title extraction failed: {e}")

        response_summary = ai_response[:120].replace("\n", " ").strip()
        new_entry = {
            "prompt_summary": prompt_summary,
            "response_summary": response_summary,
            "timestamp": int(time.time())
        }

        user_history.append(new_entry)
        history[username] = user_history[-10:]
        save_history(history)

        return jsonify({
            "success": True,
            "response": ai_response
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ========== History Endpoints ==========

@app.route('/api/history/<username>', methods=['GET'])
@app.route('/history/<username>', methods=['GET'])
def get_history(username):
    history = load_history()
    user_history = history.get(username, [])
    return jsonify({"history": user_history}), 200


@app.route('/api/history/<username>', methods=['DELETE'])
def delete_history(username):
    history = load_history()
    if username in history:
        history.pop(username, None)
        save_history(history)
    return jsonify({"message": "History cleared"}), 200


# ========== Health & Root ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Backend running with user history support"
    })


@app.route('/')
def home():
    return jsonify({
        "message": "Flask Backend with History is running!",
        "endpoints": {
            "signup": "/signup (POST)",
            "signin": "/signin (POST)",
            "process_data": "/api/process-data (POST)",
            "history": "/api/history/<username> (GET)",
            "clear_history": "/api/history/<username> (DELETE)"
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
#additional app.py in case of emergency