from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, traceback
from dotenv import load_dotenv
from openai import OpenAI
import time

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
                # Corrupt or empty file -> return empty dict
                return {}
    return {}

def save_json_file(filename, data):
    # ensure directory exists (if you ever put files in a subdir)
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

    # store as object for future extensibility
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

    # Support older storage format (password string) and new object format
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

        required_fields = ['username', 'name', 'age', 'topic', 'purpose']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        username = data['username']
        domain = data.get('domain', 'general learner')
        time_available = data.get('time_available', 'Not specified')
        interest = data.get('interest', 'Not specified')
        context = data.get('context', 'Not provided')
        name = data['name']
        age = data['age']
        topic = data['topic']
        purpose = data['purpose']

        # load history
        history = load_history()
        user_history = history.get(username, [])

        # include short summaries of last few interactions
        recent_history_summary = "\n".join(
            [f"- {h.get('prompt_summary','?')} → {h.get('response_summary','')}" for h in user_history[-3:]]
        ) if user_history else "No prior history."

        # build user prompt for the model
        user_prompt = (
            f"User info:\n"
            f"- Name: {name}\n"
            f"- Age: {age}\n"
            f"- Domain: {domain}\n"
            f"- Interest: {interest}\n"
            f"- Time Available: {time_available}\n"
            f"- Topic: {topic}\n"
            f"- Purpose: {purpose}\n"
            f"- Context: {context}\n\n"
            f"Previous sessions (summarized):\n{recent_history_summary}\n\n"
            f"Now, generate a best suitable task to suite the user needs, suggest 3 best tasks to do with task name, description, resources, best possible ways to achieve the task, keep it conscise, credit-efficient"
        )

        try:
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "SmartFreeTimeUtilizer"
                },
                model="tngtech/deepseek-r1t2-chimera:free",
                messages=[
                    {"role": "system", "content": "You are a helpful AI tutor who provides context-aware, credit-efficient responses."},
                    {"role": "user", "content": user_prompt}
                ]
            )
        except Exception as e:
            print("⚠️ Deepseek model failed, switching to backup:", e)
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "SmartFreeTimeUtilizer"
                },
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=[
                    {"role": "system", "content": "You are a helpful AI tutor who provides context-aware, credit-efficient responses."},
                    {"role": "user", "content": user_prompt}
                ]
            )


        ai_response = completion.choices[0].message.content.strip()

        # compact token-efficient summaries & timestamp
        prompt_summary = (f"{topic} | {purpose}")[:80]
        response_summary = ai_response[:120].replace("\n", " ").strip()

        new_entry = {
            "prompt_summary": prompt_summary,
            "response_summary": response_summary,
            "timestamp": int(time.time())
        }

        user_history.append(new_entry)
        history[username] = user_history[-10:]  # keep last 10 entries only
        save_history(history)

        return jsonify({
            'success': True,
            'response': ai_response
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ========== History endpoints (aliases) ==========

@app.route('/api/history/<username>', methods=['GET'])
@app.route('/history/<username>', methods=['GET'])
def get_history(username):
    history = load_history()
    user_history = history.get(username, [])
    return jsonify({"history": user_history}), 200

# Optional: clear history for a user (useful for testing / UI "clear" button)
@app.route('/api/history/<username>', methods=['DELETE'])
def delete_history(username):
    history = load_history()
    if username in history:
        history.pop(username, None)
        save_history(history)
    return jsonify({"message": "History cleared"}), 200


# ========== Health & Home ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Backend running with user history support'
    })


@app.route('/')
def home():
    return jsonify({
        'message': 'Flask Backend with History is running!',
        'endpoints': {
            'signup': '/signup (POST)',
            'signin': '/signin (POST)',
            'process_data': '/api/process-data (POST)',
            'history': '/api/history/<username> (GET) (alias: /history/<username>)'
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
