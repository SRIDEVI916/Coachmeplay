from flask import Blueprint, request, jsonify, current_app
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# OPTIONS handlers for all routes
@auth_bp.route('/me', methods=['OPTIONS'])
def me_options():
    print("OPTIONS /me called")
    return '', 200

@auth_bp.route('/register', methods=['OPTIONS'])
def register_options():
    print("OPTIONS /register called")
    return '', 200

@auth_bp.route('/login', methods=['OPTIONS'])
def login_options():
    print("OPTIONS /login called")
    return '', 200

@auth_bp.route('/profile', methods=['OPTIONS'])
def profile_options():
    print("OPTIONS /profile called")
    return '', 200

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
    print("POST /register called")
    data = request.json
    print(f"Registration data received: {data}")
    
    required_fields = ['email', 'password', 'user_type', 'full_name', 'phone_number', 'date_of_birth']
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        print(f"Missing fields: {missing}")
        return jsonify({'error': f'Missing required fields: {missing}'}), 400
    
    # Normalize user_type to lowercase
    user_type = data['user_type'].lower()
    print(f"User type normalized to: {user_type}")
    
    # Validate user_type
    if user_type not in ['athlete', 'coach']:
        return jsonify({'error': 'Invalid user type'}), 400
    
    # Convert date format from MM/DD/YYYY to YYYY-MM-DD
    try:
        date_obj = datetime.strptime(data['date_of_birth'], '%m/%d/%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        print(f"Date converted from {data['date_of_birth']} to {formatted_date}")
    except ValueError:
        # If already in correct format or invalid
        formatted_date = data['date_of_birth']
        print(f"Date kept as: {formatted_date}")
    
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor = mysql.connection.cursor()
    
    try:
        # Check if email already exists
        cursor.execute("SELECT email FROM users WHERE email = %s", (data['email'],))
        if cursor.fetchone():
            cursor.close()
            print(f"Email {data['email']} already exists")
            return jsonify({'error': 'Email already registered'}), 409
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (email, password_hash, user_type, full_name, phone_number, date_of_birth) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data['email'], hashed_password, user_type, data['full_name'], data['phone_number'], formatted_date))
        
        mysql.connection.commit()
        user_id = cursor.lastrowid
        print(f"User created with ID: {user_id}")
        
        # Insert into role-specific table
        if user_type == 'athlete':
            cursor.execute("INSERT INTO athletes (user_id) VALUES (%s)", (user_id,))
            print(f"Athlete record created for user {user_id}")
        else:
            cursor.execute("INSERT INTO coaches (user_id) VALUES (%s)", (user_id,))
            print(f"Coach record created for user {user_id}")
        
        mysql.connection.commit()
        cursor.close()
        print("Registration successful!")
        return jsonify({'message': 'Registration successful', 'user_id': user_id}), 201
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        print(f"Registration error: {str(e)}")
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    from app import mysql
    print("POST /login called")
    data = request.json
    print(f"Login attempt for email: {data.get('email')}")
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
    user = cursor.fetchone()
    
    if user and bcrypt.checkpw(data['password'].encode('utf-8'), user['password_hash'].encode('utf-8')):
        print(f"Login successful for user: {user['user_id']}")
        cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user['user_id'],))
        mysql.connection.commit()
        
        payload = {
            'user_id': user['user_id'],
            'user_type': user['user_type'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        # Add coach_id here if user is a coach
        if user['user_type'] == 'coach':
            cursor.execute("SELECT coach_id FROM coaches WHERE user_id = %s", (user['user_id'],))
            coach_row = cursor.fetchone()
            if coach_row and 'coach_id' in coach_row:
                payload['coach_id'] = coach_row['coach_id']
        
        cursor.close()
        
        token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user_type': user['user_type'],
            'user_id': user['user_id'],
            'full_name': user['full_name']
        }), 200
    else:
        cursor.close()
        print(f"Login failed for email: {data.get('email')}")
        return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user info from token"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    try:
        user_data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = user_data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401
    
    from app import mysql
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
        SELECT user_id, email, full_name, phone_number, user_type as role, profile_picture 
        FROM users 
        WHERE user_id = %s
    """, (user_id,))
    
    user = cursor.fetchone()
    cursor.close()
    
    if user:
        # If user is a coach, include coach_id from coaches table so clients can use it
        try:
            if user.get('role') == 'coach':
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT coach_id FROM coaches WHERE user_id = %s", (user['user_id'],))
                coach_row = cursor.fetchone()
                cursor.close()
                if coach_row and 'coach_id' in coach_row:
                    user['coach_id'] = coach_row['coach_id']
        except Exception:
            # Non-fatal: if we can't read coach_id, continue without it
            pass
        return jsonify({'user': user}), 200
    
    return jsonify({'error': 'User not found'}), 404

@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Get or update user profile"""
    from app import mysql
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    try:
        user_data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = user_data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401
    
    cursor = mysql.connection.cursor()
    
    if request.method == 'GET':
        # Get profile
        cursor.execute("""
            SELECT u.*, c.specialization, c.experience_years, c.certifications, c.bio, c.hourly_rate
            FROM users u
            LEFT JOIN coaches c ON u.user_id = c.user_id
            WHERE u.user_id = %s
        """, (user_id,))
        profile = cursor.fetchone()
        cursor.close()
        return jsonify({'profile': profile}), 200
    
    elif request.method == 'POST':
        # Update profile
        data = request.json
        
        try:
            # Update users table
            cursor.execute("""
                UPDATE users 
                SET full_name = %s, phone_number = %s, date_of_birth = %s
                WHERE user_id = %s
            """, (
                data.get('full_name'),
                data.get('phone_number'),
                data.get('date_of_birth'),
                user_id
            ))
            
            # Check if coach
            cursor.execute("SELECT user_type FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            
            if user and user['user_type'] == 'coach':
                # Update coaches table
                cursor.execute("""
                    UPDATE coaches 
                    SET specialization = %s, experience_years = %s, certifications = %s, bio = %s, hourly_rate = %s
                    WHERE user_id = %s
                """, (
                    data.get('specialization'),
                    data.get('experience_years'),
                    data.get('certifications'),
                    data.get('bio'),
                    data.get('hourly_rate'),
                    user_id
                ))
            
            mysql.connection.commit()
            cursor.close()
            return jsonify({'message': 'Profile updated successfully'}), 200
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            return jsonify({'error': str(e)}), 500