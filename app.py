from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, traceback, time, re
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

USERS_FILE = "users.json"
HISTORY_FILE = "history.json"

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

def extract_titles(response_text):
    """
    Extract titles written as:
    **Title**: Something
    """
    pattern = r"\*\*Title\*\*:\s*(.+)"
    return re.findall(pattern, response_text)


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

    users[username] = {
        "name": name,
        "password": password
    }
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

        history = load_history()
        user_history = history.get(username, [])

        # History used ONLY as lightweight context
        recent_history_summary = "\n".join(
            f"- {h['title']}" for h in user_history[-3:]
        ) if user_history else "No prior history."

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

        # ===== Store ONLY titles in history =====
        titles = extract_titles(ai_response)
        for title in titles:
            user_history.append({
                "title": title,
                "timestamp": int(time.time())
            })

        history[username] = user_history[-10:]
        save_history(history)

        # IMPORTANT: response returned AS-IS (no modification)
        return jsonify({
            "success": True,
            "response": ai_response
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ========== History Routes ==========

@app.route('/api/history/<username>', methods=['GET'])
@app.route('/history/<username>', methods=['GET'])
def get_history(username):
    history = load_history()
    return jsonify({"history": history.get(username, [])}), 200

@app.route('/api/history/<username>', methods=['DELETE'])
def delete_history(username):
    history = load_history()
    history.pop(username, None)
    save_history(history)
    return jsonify({"message": "History cleared"}), 200


# ========== Health & Home ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Backend running correctly"
    })

@app.route('/')
def home():
    return jsonify({
        "message": "Flask Backend with title-only history is running",
        "endpoints": [
            "/signup",
            "/signin",
            "/api/process-data",
            "/api/history/<username>"
        ]
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
