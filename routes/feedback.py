from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import jwt
from utils.logger import logger, log_exception

feedback_bp = Blueprint('feedback', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token missing'}), 401
        token = token.replace('Bearer ', '')
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = data
            print("Decoded JWT token payload:", current_user)
        except Exception as e:
            print("JWT decoding error:", e)
            return jsonify({'error': 'Invalid token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@feedback_bp.route('/athlete/<int:athlete_id>/received', methods=['GET'])
@token_required
@log_exception
def get_athlete_feedback(current_user, athlete_id):
    if current_user['user_type'] != 'athlete' or current_user['user_id'] != athlete_id:
        return jsonify({'error': 'Access denied'}), 403

    from app import mysql
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT f.*, 
               u.full_name AS coach_name, 
               u.profile_picture AS coach_image
        FROM feedback f
        JOIN users u ON f.coach_id = u.user_id
        WHERE f.athlete_id = %s
        ORDER BY f.created_at DESC
    """, (athlete_id,))
    feedbacks = cursor.fetchall()
    total_count = len(feedbacks)
    ratings = [f.get('performance_rating') for f in feedbacks if f.get('performance_rating') is not None]
    avg_rating = float(sum(ratings) / len(ratings)) if ratings else 0.0
    cursor.close()
    return jsonify({'feedbacks': feedbacks, 'total_count': total_count, 'avg_rating': avg_rating}), 200

@feedback_bp.route('/coach/<int:coach_id>/athletes', methods=['GET'])
@token_required
@log_exception
def get_coach_athletes(current_user, coach_id):
    if current_user['user_type'] != 'coach' or int(current_user.get('coach_id', 0)) != coach_id:
        return jsonify({'error': 'Access denied'}), 403

    from app import mysql
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT u.user_id, u.full_name, u.email, u.profile_picture, a.athlete_id
        FROM users u
        JOIN athletes a ON u.user_id = a.user_id
        JOIN coaching_requests cr ON a.athlete_id = cr.athlete_id
        WHERE cr.coach_id = %s AND cr.status = 'accepted'
    """, (coach_id,))
    athletes = cursor.fetchall()
    cursor.close()
    return jsonify({'athletes': athletes}), 200

@feedback_bp.route('/coach/<int:coach_id>/given', methods=['GET'])
@token_required
@log_exception
def get_coach_given_feedback(current_user, coach_id):
    if current_user['user_type'] != 'coach' or int(current_user.get('coach_id', 0)) != coach_id:
        return jsonify({'error': 'Access denied'}), 403

    from app import mysql
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT user_id FROM coaches WHERE coach_id = %s", (coach_id,))
    coach_user_row = cursor.fetchone()
    coach_user_id = coach_user_row['user_id'] if coach_user_row and 'user_id' in coach_user_row else None

    if not coach_user_id:
        cursor.close()
        return jsonify({'feedbacks': []}), 200

    cursor.execute("""
        SELECT f.*, 
               u.full_name AS athlete_name, 
               u.profile_picture AS athlete_image
        FROM feedback f
        JOIN users u ON f.athlete_id = u.user_id
        WHERE f.coach_id = %s
        ORDER BY f.created_at DESC
    """, (coach_user_id,))
    feedbacks = cursor.fetchall()
    cursor.close()
    return jsonify({'feedbacks': feedbacks}), 200

@feedback_bp.route('/create', methods=['POST'])
@token_required
@log_exception
def create_feedback(current_user):
    if current_user['user_type'] != 'coach':
        return jsonify({'error': 'Only coaches may give feedback'}), 403

    from app import mysql
    data = request.json
    coach_id = int(current_user.get('coach_id', 0))
    athlete_id = data.get('athlete_id')
    feedback_text = data.get('feedback_text', '')

    if not athlete_id or not feedback_text.strip():
        return jsonify({'error': 'Missing or empty fields'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 1 FROM coaching_requests WHERE coach_id=%s AND athlete_id=%s AND status='accepted'
    """, (coach_id, athlete_id))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({'error': 'Not your accepted athlete'}), 403

    try:
        cursor.execute("SELECT user_id FROM coaches WHERE coach_id = %s", (coach_id,))
        coach_user_row = cursor.fetchone()
        coach_user_id = coach_user_row['user_id'] if coach_user_row and 'user_id' in coach_user_row else None

        cursor.execute("SELECT user_id FROM athletes WHERE athlete_id = %s", (athlete_id,))
        athlete_user_row = cursor.fetchone()
        athlete_user_id = athlete_user_row['user_id'] if athlete_user_row and 'user_id' in athlete_user_row else None

        if not coach_user_id or not athlete_user_id:
            cursor.close()
            return jsonify({'error': 'Invalid coach or athlete id for insertion'}), 400

        performance_rating = data.get('performance_rating')
        focus_areas = data.get('focus_areas')
        strengths = data.get('strengths')
        improvements_needed = data.get('improvements_needed')

        cursor.execute("""
            INSERT INTO feedback 
            (coach_id, athlete_id, feedback_text, performance_rating, focus_areas, strengths, improvements_needed)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (coach_user_id, athlete_user_id, feedback_text, performance_rating, focus_areas, strengths, improvements_needed))
        mysql.connection.commit()
        feedback_id = cursor.lastrowid
        cursor.close()
        return jsonify({'message': 'Feedback submitted', 'feedback_id': feedback_id}), 201
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@feedback_bp.route('/<int:feedback_id>', methods=['GET', 'DELETE'])
@token_required
@log_exception
def feedback_detail_or_delete(current_user, feedback_id):
    from app import mysql
    cursor = mysql.connection.cursor()

    if request.method == 'GET':
        cursor.execute("""
            SELECT f.*,
                   uc.full_name AS coach_name,
                   uc.profile_picture AS coach_image,
                   ua.full_name AS athlete_name,
                   ua.user_id AS athlete_user_id
            FROM feedback f
            JOIN users uc ON f.coach_id = uc.user_id
            JOIN users ua ON f.athlete_id = ua.user_id
            WHERE f.feedback_id = %s
        """, (feedback_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return jsonify({'error': 'Feedback not found'}), 404

        if current_user.get('user_type') == 'athlete':
            if current_user.get('user_id') != row.get('athlete_id'):
                return jsonify({'error': 'Access denied'}), 403
        elif current_user.get('user_type') == 'coach':
            if current_user.get('user_id') != row.get('coach_id'):
                return jsonify({'error': 'Access denied'}), 403

        return jsonify({'feedback': row}), 200

    try:
        cursor.execute("SELECT coach_id FROM feedback WHERE feedback_id = %s", (feedback_id,))
        frow = cursor.fetchone()
        if not frow:
            cursor.close()
            return jsonify({'error': 'Feedback not found'}), 404

        if current_user.get('user_type') == 'coach' and current_user.get('user_id') != frow.get('coach_id'):
            cursor.close()
            return jsonify({'error': 'Access denied'}), 403

        cursor.execute("DELETE FROM feedback WHERE feedback_id = %s", (feedback_id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'Feedback deleted'}), 200
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500
