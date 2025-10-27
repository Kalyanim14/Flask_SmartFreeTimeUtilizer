from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI
import traceback

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())

@app.route('/api/process-data', methods=['POST'])
def process_data():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        required_fields = ['name', 'age', 'topic', 'purpose']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Optional context-aware fields
        domain = data.get('domain', 'general learner')
        time_available = data.get('time_available', 'Not specified')
        interest = data.get('interest', 'Not specified')
        context = data.get('context', 'Not provided')

        # Extract user input
        name = data['name']
        age = data['age']
        topic = data['topic']
        purpose = data['purpose']

        # Construct AI prompt
        user_prompt = (
            f"User info:\n"
            f"- Name: {name}\n"
            f"- Age: {age}\n"
            f"- Domain/Background: {domain}\n"
            f"- Current Interest: {interest}\n"
            f"- Time Available: {time_available}\n"
            f"- Topic: {topic}\n"
            f"- Purpose: {purpose}\n"
            f"- Context: {context}\n\n"
            f"Generate an explanation or learning guide tailored to this user.\n"
            f"The response should:\n"
            f"1. Match their knowledge level (based on domain).\n"
            f"2. Connect the explanation to their current interests.\n"
            f"3. Fit within the time they have (e.g., short summary if less time, detailed guide if more).\n"
            f"4. Be friendly, easy to follow, and motivating.\n"
            f"End with a short suggestion for what the user can do next related to the topic."
        )

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "SmartFreeTimeUtilizer"
            },
            model="tngtech/deepseek-r1t2-chimera:free",
            messages=[
                {"role": "system", "content": "You are a friendly AI tutor who personalizes content based on user's domain, interest, and available time."},
                {"role": "user", "content": user_prompt}
            ]
        )

        ai_response = completion.choices[0].message.content.strip()

        return jsonify({
            'success': True,
            'response': ai_response
        })

    except Exception as e:
        traceback.print_exc()
        print(f"Error in process-data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Backend is running with OpenRouter AI integration'
    })


@app.route('/')
def home():
    return jsonify({
        'message': 'Flask Backend is running!',
        'endpoints': {
            'health': '/api/health (GET)',
            'process_data': '/api/process-data (POST)'
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
        host='0.0.0.0',
        port=port
    )
