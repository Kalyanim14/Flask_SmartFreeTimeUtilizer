from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import auth, credentials
import json

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin
if os.getenv('FIREBASE_CREDENTIALS'):
    try:
        cred_dict = json.loads(os.getenv('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin initialized successfully")
    except Exception as e:
        print(f"Firebase Admin initialization error: {e}")

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
    print("OpenAI client initialized successfully")
else:
    print("OPENAI_API_KEY not found in environment variables")
    client = None

def verify_firebase_token(id_token):
    """Verify Firebase ID token"""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Token verification error: {e}")
        return None

@app.route('/api/process-data', methods=['POST'])
def process_data():
    try:
        # Get authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized - No token provided'}), 401
        
        id_token = auth_header.split('Bearer ')[1]
        user = verify_firebase_token(id_token)
        
        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'age', 'topic', 'purpose']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Check if OpenAI client is initialized
        if not client:
            return jsonify({'error': 'OpenAI service not configured'}), 500

        # Create prompt for OpenAI
        prompt = f"""
        Create a personalized response based on the following information:
        
        Name: {data['name']}
        Age: {data['age']}
        Topic: {data['topic']}
        Purpose: {data['purpose']}
        Additional Context: {data.get('context', 'Not provided')}
        
        Please provide a comprehensive, engaging response that's appropriate for a {data['age']}-year-old 
        interested in {data['topic']}. The response should help with: {data['purpose']}
        
        Make the response friendly, informative, and tailored to the user's age and interests.
        """

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates personalized, engaging responses based on user input."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        ai_response = response.choices[0].message.content.strip()

        return jsonify({
            'success': True,
            'response': ai_response,
            'user': user.get('email', 'Unknown')
        })

    except Exception as e:
        print(f"Error in process-data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'openai_configured': client is not None,
        'firebase_configured': 'firebase_admin' in globals() and len(firebase_admin._apps) > 0
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)