from flask import Blueprint, request, jsonify, current_app
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = data
        except:
            return jsonify({'error': 'Invalid token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    from app import mysql
    data = request.json
    required_fields = ['email', 'password', 'user_type', 'full_name', 'phone_number', 'date_of_birth']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("INSERT INTO users (email, password_hash, user_type, full_name, phone_number, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s)",
                      (data['email'], hashed_password, data['user_type'], data['full_name'], data['phone_number'], data['date_of_birth']))
        mysql.connection.commit()
        user_id = cursor.lastrowid
        
        if data['user_type'] == 'athlete':
            cursor.execute("INSERT INTO athletes (user_id) VALUES (%s)", (user_id,))
        else:
            cursor.execute("INSERT INTO coaches (user_id) VALUES (%s)", (user_id,))
        
        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'Registration successful', 'user_id': user_id}), 201
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    from app import mysql
    data = request.json
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
    user = cursor.fetchone()
    
    if user and bcrypt.checkpw(data['password'].encode('utf-8'), user['password_hash'].encode('utf-8')):
        cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user['user_id'],))
        mysql.connection.commit()
        cursor.close()
        
        token = jwt.encode({
            'user_id': user['user_id'],
            'user_type': user['user_type'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user_type': user['user_type'],
            'user_id': user['user_id'],
            'full_name': user['full_name']
        }), 200
    else:
        cursor.close()
        return jsonify({'error': 'Invalid credentials'}), 401

