import jwt
from flask import request, jsonify, make_response, current_app, g
from functools import wraps
from bson import ObjectId
import bcrypt
from datetime import datetime, timedelta

from db import get_db

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

def setup_auth_routes(app):

    @app.route('/auth/register', methods=['POST'])
    def register_user():
        data = request.get_json()
        db = get_db()
        users_collection = db.users

        if not data or 'email' not in data or 'password' not in data or 'role' not in data:
            return make_response(jsonify({"error": "Missing email, password, or role"}), 400)

        if data['role'] not in ['admin', 'recruiter', 'user']:
            return make_response(jsonify({"error": "Invalid role specified"}), 400)

        existing_user = users_collection.find_one({'email': data['email']})
        if existing_user:
            return make_response(jsonify({
                "error": "User with this email already exists.",
                "debug": {"email": data['email']}
            }), 409)

        hashed_password = hash_password(data['password'])
        new_user = {
            "email": data['email'],
            "password": hashed_password,
            "role": data['role'],
            "created_at": datetime.utcnow()
        }
        result = users_collection.insert_one(new_user)
        return make_response(jsonify({"message": "User registered successfully", "user_id": str(result.inserted_id)}), 201)

    @app.route('/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        db = get_db()
        users_collection = db.users

        if not data or 'email' not in data or 'password' not in data:
            return make_response(jsonify({
                "error": "Missing 'email' or 'password' in request.",
                "debug": {"received": list(data.keys()) if data else None}
            }), 400)
        
        user = users_collection.find_one({'email': data['email']})
        if not user:
            return make_response(jsonify({
                "error": "User with that email does not exist.",
                "debug": {"email": data['email']}
            }), 401)
        
        if not check_password(user['password'], data['password']):
            return make_response(jsonify({
                "error": "Password is incorrect.",
                "debug": {
                    "hashed_password": str(user['password']),
                    "password_type": str(type(user['password'])).split("'")[1]
                }
            }), 401)

        try:
            token = jwt.encode({
                'user_id': str(user['_id']),
                'role': user['role'],
                'exp': datetime.utcnow() + timedelta(minutes=60)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")
        except Exception as e:
            return make_response(jsonify({"error": "Token generation failed.", "exception": str(e)}), 500)

        return jsonify({'token': token})

    @app.route('/auth/logout', methods=['POST'])
    @token_required
    def logout():
        """Logout endpoint - Token invalidation happens client-side"""
        return make_response(jsonify({
            'message': 'Successfully logged out. Please remove token from client.'
        }), 200)

# Decorator for token requirement
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', None)
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            db = get_db()
            current_user = db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
            # Pass user role and id for permission checks
            g.current_user_id = str(current_user['_id'])
            g.current_user_role = current_user['role']

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(*args, **kwargs)
    return decorated

# Decorator for role-based access
def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.current_user_role not in roles:
                return jsonify({'message': 'You do not have permission to perform this action'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return wrapper