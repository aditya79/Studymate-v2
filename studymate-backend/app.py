from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import re
from datetime import datetime
from pymongo import MongoClient
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import secrets

# load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# configure CORS - allow frontend to talk to backend
CORS(app, supports_credentials=True, origins=['http://localhost:3000'])

# create uploads folder for storing files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# connect to MongoDB
try:
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    print(f"Connecting to MongoDB at: {MONGODB_URI}")
    
    mongo_client = MongoClient(MONGODB_URI)
    # test connection
    mongo_client.admin.command('ping')
    
    db = mongo_client['studymate']
    users_collection = db['users']
    files_collection = db['files']
    flashcards_collection = db['flashcards']
    
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f" MongoDB connection error: {e}")
    print("Make sure MongoDB is running on your system")

# Google OAuth client ID
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '268330777379-evaefa7i8q2gl0tpeuakj2qdi6sdunj7.apps.googleusercontent.com')

# simple NLP function to generate flashcards
def generate_flashcards(text):
    print("Generating flashcards...")
    cards = []
    
    # split text into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    print(f"Found {len(sentences)} sentences")
    
    # look for patterns to create Q&A
    for sentence in sentences:
        lower = sentence.lower()
        
        # pattern: "X is Y"
        if ' is ' in lower:
            parts = re.split(r'\s+is\s+', sentence, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                cards.append({
                    'question': f'What is {parts[0].strip()}?',
                    'answer': parts[1].strip()
                })
        
        # pattern: "X are Y"
        elif ' are ' in lower:
            parts = re.split(r'\s+are\s+', sentence, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                cards.append({
                    'question': f'What are {parts[0].strip()}?',
                    'answer': parts[1].strip()
                })
    
    # if no patterns found, create generic flashcards
    if len(cards) == 0:
        print("No patterns found, creating generic cards")
        for i, sentence in enumerate(sentences[:5]):
            cards.append({
                'question': f'What is key concept {i+1}?',
                'answer': sentence.strip()
            })
    
    print(f"Generated {len(cards)} flashcards")
    return cards

# route: google login
@app.route('/api/google-login', methods=['POST'])
def google_login():
    try:
        data = request.get_json()
        token = data.get('credential')
        
        if not token:
            return jsonify({'status': 'error', 'message': 'No token provided'}), 400
        
        # verify google token
        print("Verifying Google token...")
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # extract user info
        user_id = idinfo['sub']
        email = idinfo.get('email')
        name = idinfo.get('name')
        picture = idinfo.get('picture')
        
        print(f"Google login: {email}")
        
        # check if user exists in database
        user = users_collection.find_one({'google_id': user_id})
        
        if not user:
            # create new user
            user_doc = {
                'google_id': user_id,
                'email': email,
                'name': name,
                'picture': picture,
                'auth_method': 'google',
                'created_at': datetime.now()
            }
            users_collection.insert_one(user_doc)
            print(f"Created new user: {email}")
        
        # store in session
        session['user_id'] = user_id
        session['email'] = email
        session['name'] = name
        session['picture'] = picture
        
        return jsonify({
            'status': 'success',
            'user': {
                'email': email,
                'name': name,
                'picture': picture
            }
        })
        
    except ValueError as e:
        print(f"Token verification failed: {e}")
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 401
    except Exception as e:
        print(f"Google login error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# route: check if user is logged in
@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'email': session.get('email'),
                'name': session.get('name'),
                'picture': session.get('picture')
            }
        })
    return jsonify({'authenticated': False})

# route: logout
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'success'})

# route: upload file
@app.route('/api/upload', methods=['POST'])
def upload_file():
    # check if user is logged in
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    # secure the filename
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    print(f"Uploading file: {filename}")
    file.save(filepath)
    
    # generate flashcards if txt file
    flashcards = []
    if filename.endswith('.txt'):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                flashcards = generate_flashcards(content)
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        # placeholder for non-txt files
        flashcards = [
            {'question': 'What is the main topic?', 'answer': 'Review the document for details.'},
            {'question': 'Key concept?', 'answer': 'Upload .txt files for auto-generated cards.'}
        ]
    
    # save to MongoDB
    file_doc = {
        'user_id': session['user_id'],
        'user_email': session['email'],
        'filename': filename,
        'filepath': filepath,
        'size': os.path.getsize(filepath),
        'upload_date': datetime.now(),
        'flashcards': flashcards
    }
    
    result = files_collection.insert_one(file_doc)
    print(f"Saved to MongoDB with ID: {result.inserted_id}")
    
    return jsonify({
        'status': 'success',
        'filename': filename,
        'flashcard_count': len(flashcards)
    })

# route: get user's files
@app.route('/api/files', methods=['GET'])
def get_files():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    # find all files for this user
    files = list(files_collection.find({'user_id': session['user_id']}))
    
    # convert to JSON-friendly format
    result = []
    for f in files:
        result.append({
            'id': str(f['_id']),
            'filename': f['filename'],
            'size': f['size'],
            'upload_date': f['upload_date'].isoformat(),
            'flashcard_count': len(f.get('flashcards', []))
        })
    
    print(f"Found {len(result)} files for user")
    return jsonify({'files': result})

# route: get flashcards for a file
@app.route('/api/flashcards/<file_id>', methods=['GET'])
def get_flashcards(file_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    from bson.objectid import ObjectId
    
    try:
        # find file by ID
        file_doc = files_collection.find_one({
            '_id': ObjectId(file_id),
            'user_id': session['user_id']
        })
        
        if not file_doc:
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        flashcards = file_doc.get('flashcards', [])
        print(f"Returning {len(flashcards)} flashcards")
        
        return jsonify({
            'status': 'success',
            'flashcards': flashcards,
            'filename': file_doc['filename']
        })
        
    except Exception as e:
        print(f"Error getting flashcards: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# route: delete file
@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    from bson.objectid import ObjectId
    
    try:
        # find file
        file_doc = files_collection.find_one({
            '_id': ObjectId(file_id),
            'user_id': session['user_id']
        })
        
        if not file_doc:
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        # delete from filesystem
        if os.path.exists(file_doc['filepath']):
            os.remove(file_doc['filepath'])
        
        # delete from database
        files_collection.delete_one({'_id': ObjectId(file_id)})
        
        print(f"Deleted file: {file_doc['filename']}")
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error deleting file: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# route: get user statistics
@app.route('/api/stats', methods=['GET'])
def get_stats():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    # count files
    file_count = files_collection.count_documents({'user_id': session['user_id']})
    
    # count total flashcards
    pipeline = [
        {'$match': {'user_id': session['user_id']}},
        {'$project': {'card_count': {'$size': '$flashcards'}}},
        {'$group': {'_id': None, 'total': {'$sum': '$card_count'}}}
    ]
    
    result = list(files_collection.aggregate(pipeline))
    card_count = result[0]['total'] if result else 0
    
    return jsonify({
        'total_files': file_count,
        'total_cards': card_count
    })

# run the application
if __name__ == '__main__':
    print("=" * 60)
    print(" Starting StudyMate Flask Server with MongoDB")
    print("=" * 60)
    print(f" MongoDB URI: {os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')}")
    print(f" Google OAuth: {'Configured' if GOOGLE_CLIENT_ID else 'Not configured'}")
    print("=" * 60)
    app.run(debug=True, port=5000, host='0.0.0.0')
