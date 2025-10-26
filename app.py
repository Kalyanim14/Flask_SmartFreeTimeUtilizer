from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize OpenRouter client using OpenAI SDK
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

        # Extract user input
        name = data['name']
        age = data['age']
        topic = data['topic']
        purpose = data['purpose']
        context = data.get('context', 'Not provided')

        # Construct AI prompt
        user_prompt = (
            f"User info:\n"
            f"Name: {name}\n"
            f"Age: {age}\n"
            f"Topic: {topic}\n"
            f"Purpose: {purpose}\n"
            f"Context: {context}\n\n"
            f"Generate a friendly, well-structured, and helpful explanation or guidance for the user."
        )

        # Call OpenRouter API via OpenAI client (using a free model)
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:3000",  # Optional: your site URL
                "X-Title": "SmartFreeTimeUtilizer"       # Optional: your app/site name
            },
            model="tngtech/deepseek-r1t2-chimera:free",
            messages=[
                {"role": "system", "content": "You are a friendly AI tutor who provides helpful and age-appropriate information."},
                {"role": "user", "content": user_prompt}
            ]
        )

        ai_response = completion.choices[0].message.content.strip()

        return jsonify({
            'success': True,
            'response': ai_response
        })

    except Exception as e:
        # Print full error details in console
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
