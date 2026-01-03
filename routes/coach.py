from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from utils import create_notification
import jwt
import os
from werkzeug.utils import secure_filename

coach_bp = Blueprint('coach', __name__)

@coach_bp.route('/coaches', methods=['GET'])
def get_coaches():
    """Get all coaches with their profile info"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT c.coach_id, u.user_id, u.full_name, u.email, u.profile_picture,
               c.specialization, c.experience_years, c.bio, c.hourly_rate
        FROM coaches c
        JOIN users u ON c.user_id = u.user_id
        ORDER BY u.full_name
    """)
    
    coaches = cursor.fetchall()
    cursor.close()
    
    return jsonify({'coaches': coaches}), 200

@coach_bp.route('/coach/<int:coach_id>', methods=['GET'])
def get_coach_details(coach_id):
    """Get detailed information about a specific coach"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT c.coach_id, u.user_id, u.full_name, u.email, u.phone_number,
               u.profile_picture, c.specialization, c.experience_years, 
               c.bio, c.hourly_rate, c.certifications
        FROM coaches c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.coach_id = %s
    """, (coach_id,))
    
    coach = cursor.fetchone()
    cursor.close()
    
    if coach:
        return jsonify({'coach': coach}), 200
    return jsonify({'error': 'Coach not found'}), 404

@coach_bp.route('/coaching-request', methods=['POST'])
def send_coaching_request():
    """Send a coaching request from athlete to coach"""
    from app import mysql
    
    data = request.json
    required_fields = ['athlete_id', 'coach_id', 'message']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    athlete_id = data['athlete_id']
    coach_id = data['coach_id']
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            SELECT request_id FROM coaching_requests 
            WHERE athlete_id = %s AND coach_id = %s AND status = 'pending'
        """, (athlete_id, coach_id))
        
        if cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'You already have a pending request with this coach'}), 400
        
        cursor.execute("""
            INSERT INTO coaching_requests (athlete_id, coach_id, message, status, request_date)
            VALUES (%s, %s, %s, 'pending', NOW())
        """, (athlete_id, coach_id, data['message']))
        
        mysql.connection.commit()
        request_id = cursor.lastrowid
        
        cursor.execute("SELECT u.full_name FROM athletes a JOIN users u ON a.user_id = u.user_id WHERE a.athlete_id = %s", (athlete_id,))
        athlete_result = cursor.fetchone()
        athlete_name = athlete_result['full_name'] if athlete_result else 'An athlete'
        
        cursor.execute("SELECT user_id FROM coaches WHERE coach_id = %s", (coach_id,))
        coach_result = cursor.fetchone()
        if coach_result:
            create_notification(
                mysql,
                coach_result['user_id'],
                'request',
                'New Coaching Request',
                f'{athlete_name} wants you as their coach!',
                request_id
            )
        
        cursor.close()
        
        return jsonify({
            'message': 'Coaching request sent successfully!',
            'request_id': request_id
        }), 201
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@coach_bp.route('/coaching-requests/athlete/<int:athlete_id>', methods=['GET'])
def get_athlete_requests(athlete_id):
    """Get all coaching requests made by an athlete"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT cr.request_id, cr.message, cr.status, cr.request_date, cr.response_date,
               c.coach_id, u.full_name as coach_name, c.specialization
        FROM coaching_requests cr
        JOIN coaches c ON cr.coach_id = c.coach_id
        JOIN users u ON c.user_id = u.user_id
        WHERE cr.athlete_id = %s
        ORDER BY cr.request_date DESC
    """, (athlete_id,))
    
    requests = cursor.fetchall()
    cursor.close()
    
    return jsonify({'requests': requests}), 200

@coach_bp.route('/coaching-requests/coach/<int:coach_id>', methods=['GET'])
def get_coach_requests(coach_id):
    """Get all coaching requests received by a coach"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT cr.request_id, cr.message, cr.status, cr.request_date,
               a.athlete_id, u.full_name as athlete_name, u.email as athlete_email
        FROM coaching_requests cr
        JOIN athletes a ON cr.athlete_id = a.athlete_id
        JOIN users u ON a.user_id = u.user_id
        WHERE cr.coach_id = %s
        ORDER BY cr.request_date DESC
    """, (coach_id,))
    
    requests = cursor.fetchall()
    cursor.close()
    
    return jsonify({'requests': requests}), 200

@coach_bp.route('/coaching-request/<int:request_id>', methods=['PUT'])
def respond_to_request(request_id):
    """Coach accepts or rejects a coaching request"""
    from app import mysql
    
    data = request.json
    
    if 'status' not in data or data['status'] not in ['accepted', 'rejected']:
        return jsonify({'error': 'Invalid status'}), 400
    
    status = data['status']
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            SELECT athlete_id, coach_id 
            FROM coaching_requests 
            WHERE request_id = %s
        """, (request_id,))
        
        request_info = cursor.fetchone()
        
        if not request_info:
            cursor.close()
            return jsonify({'error': 'Request not found'}), 404
        
        athlete_id = request_info['athlete_id']
        coach_id = request_info['coach_id']
        
        cursor.execute("""
            UPDATE coaching_requests 
            SET status = %s, response_date = NOW()
            WHERE request_id = %s
        """, (status, request_id))
        
        if status == 'accepted':
            cursor.execute("""
                UPDATE athletes 
                SET coach_id = %s
                WHERE athlete_id = %s
            """, (coach_id, athlete_id))
        
        mysql.connection.commit()
        
        cursor.execute("SELECT user_id FROM athletes WHERE athlete_id = %s", (athlete_id,))
        athlete_result = cursor.fetchone()
        
        cursor.execute("SELECT u.full_name FROM coaches c JOIN users u ON c.user_id = u.user_id WHERE c.coach_id = %s", (coach_id,))
        coach_result = cursor.fetchone()
        coach_name = coach_result['full_name'] if coach_result else 'Your coach'
        
        if athlete_result:
            if status == 'accepted':
                create_notification(
                    mysql,
                    athlete_result['user_id'],
                    'request',
                    'Request Accepted!',
                    f'{coach_name} accepted your coaching request!',
                    request_id
                )
            elif status == 'rejected':
                create_notification(
                    mysql,
                    athlete_result['user_id'],
                    'request',
                    'Request Declined',
                    'Your coaching request was declined.',
                    request_id
                )
        
        cursor.close()
        
        return jsonify({'message': f'Request {status} successfully'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@coach_bp.route('/coach-info/<int:user_id>', methods=['GET'])
def get_coach_info(user_id):
    """Get coach ID from user ID"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT coach_id FROM coaches WHERE user_id = %s", (user_id,))
    coach = cursor.fetchone()
    cursor.close()
    
    if coach:
        return jsonify({'coach_id': coach['coach_id']}), 200
    return jsonify({'error': 'Coach not found'}), 404

@coach_bp.route('/profile/<int:coach_id>', methods=['GET'])
def get_coach_profile(coach_id):
    """Get coach's detailed profile"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT c.coach_id, c.specialization, c.experience_years, c.bio, 
               c.hourly_rate, c.certifications, c.achievements, c.coaching_philosophy,
               c.rating, c.total_reviews,
               u.user_id, u.full_name, u.email, u.phone_number, u.profile_picture
        FROM coaches c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.coach_id = %s
    """, (coach_id,))
    
    profile = cursor.fetchone()
    cursor.close()
    
    if profile:
        return jsonify({'profile': profile}), 200
    return jsonify({'error': 'Profile not found'}), 404

@coach_bp.route('/profile', methods=['PUT'])
def update_coach_profile():
    """Update coach's profile"""
    from app import mysql
    
    data = request.json
    
    if 'coach_id' not in data:
        return jsonify({'error': 'Coach ID required'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE coaches 
            SET specialization = %s, experience_years = %s, bio = %s, 
                hourly_rate = %s, certifications = %s, achievements = %s, 
                coaching_philosophy = %s
            WHERE coach_id = %s
        """, (
            data.get('specialization'),
            data.get('experience_years'),
            data.get('bio'),
            data.get('hourly_rate'),
            data.get('certifications'),
            data.get('achievements'),
            data.get('coaching_philosophy'),
            data['coach_id']
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Profile updated successfully'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@coach_bp.route('/my-athletes/<int:coach_id>', methods=['GET'])
def get_coach_athletes(coach_id):
    """Get list of athletes assigned to this coach"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT a.athlete_id, u.user_id, u.full_name, u.email, u.profile_picture,
               a.sport_type, a.skill_level, a.age, a.height, a.weight
        FROM athletes a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.coach_id = %s
        ORDER BY u.full_name
    """, (coach_id,))
    
    athletes = cursor.fetchall()
    cursor.close()
    
    return jsonify({'athletes': athletes}), 200

@coach_bp.route('/athlete-detail/<int:athlete_id>', methods=['GET'])
def get_athlete_detail(athlete_id):
    """Get detailed information about a specific athlete"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            u.user_id,
            u.email,
            u.full_name,
            u.phone_number,
            u.date_of_birth,
            u.profile_picture,
            a.athlete_id,
            a.sport_type,
            a.skill_level,
            a.height,
            a.weight,
            TIMESTAMPDIFF(YEAR, u.date_of_birth, CURDATE()) as age
        FROM athletes a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.athlete_id = %s
    """, (athlete_id,))
    
    athlete = cursor.fetchone()
    cursor.close()
    
    if athlete:
        return jsonify({'athlete': athlete}), 200
    
    return jsonify({'error': 'Athlete not found'}), 404

@coach_bp.route('/all-athletes', methods=['GET'])
def get_all_athletes():
    """Get all athletes for messaging"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            u.user_id, 
            u.full_name, 
            u.profile_picture,
            a.athlete_id
        FROM users u
        JOIN athletes a ON u.user_id = a.user_id
        WHERE u.user_type = 'athlete'
        ORDER BY u.full_name
    """)
    
    athletes = cursor.fetchall()
    cursor.close()
    
    return jsonify({'athletes': athletes}), 200

@coach_bp.route('/assignments', methods=['POST'])
def create_assignment():
    """Coach creates task assignment for athlete"""
    from app import mysql
    
    data = request.json
    required_fields = ['coach_id', 'athlete_id', 'task_title', 'due_date']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    coach_id = data['coach_id']
    athlete_id = data['athlete_id']
    task_title = data['task_title']
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO coach_assignments (coach_id, athlete_id, task_title, task_description, due_date, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """, (
            coach_id,
            athlete_id,
            task_title,
            data.get('task_description', ''),
            data['due_date'],
            data.get('priority', 'medium')
        ))
        
        mysql.connection.commit()
        assignment_id = cursor.lastrowid
        
        cursor.execute("SELECT u.full_name FROM coaches c JOIN users u ON c.user_id = u.user_id WHERE c.coach_id = %s", (coach_id,))
        coach_result = cursor.fetchone()
        coach_name = coach_result['full_name'] if coach_result else 'Your coach'
        
        cursor.execute("SELECT user_id FROM athletes WHERE athlete_id = %s", (athlete_id,))
        athlete_result = cursor.fetchone()
        
        if athlete_result:
            create_notification(
                mysql,
                athlete_result['user_id'],
                'task',
                'New Assignment',
                f'{coach_name} assigned you: {task_title}',
                assignment_id
            )
        
        cursor.close()
        
        return jsonify({
            'message': 'Assignment created successfully',
            'assignment_id': assignment_id
        }), 201
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@coach_bp.route('/assignments/athlete/<int:athlete_id>', methods=['GET'])
def get_athlete_assignments(athlete_id):
    """Get all assignments for an athlete"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT a.assignment_id, a.task_title, a.task_description, a.due_date, 
               a.status, a.priority, a.created_date,
               c.coach_id, u.full_name as coach_name
        FROM coach_assignments a
        JOIN coaches c ON a.coach_id = c.coach_id
        JOIN users u ON c.user_id = u.user_id
        WHERE a.athlete_id = %s
        ORDER BY a.due_date ASC
    """, (athlete_id,))
    
    assignments = cursor.fetchall()
    cursor.close()
    
    return jsonify({'assignments': assignments}), 200

# ========== WORKOUT PLANS ==========

@coach_bp.route('/workout-plans/create', methods=['POST'])
def create_workout_plan():
    from app import mysql
    data = request.json
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO workout_plans 
            (coach_id, athlete_id, plan_name, description, duration_weeks, difficulty_level, is_template)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data['coach_id'],
            data.get('athlete_id'),
            data['plan_name'],
            data.get('description'),
            data.get('duration_weeks'),
            data.get('difficulty_level'),
            data.get('is_template', False)
        ))
        
        plan_id = cursor.lastrowid
        
        for session in data.get('sessions', []):
            cursor.execute("""
                INSERT INTO workout_sessions 
                (plan_id, session_name, day_number, description)
                VALUES (%s, %s, %s, %s)
            """, (plan_id, session['name'], session['day'], session.get('description')))
            
            session_id = cursor.lastrowid
            
            for idx, exercise in enumerate(session.get('exercises', [])):
                cursor.execute("""
                    INSERT INTO workout_exercises 
                    (session_id, exercise_name, sets, reps, duration, rest_time, notes, order_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_id,
                    exercise['name'],
                    exercise.get('sets'),
                    exercise.get('reps'),
                    exercise.get('duration'),
                    exercise.get('rest_time'),
                    exercise.get('notes'),
                    idx + 1
                ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Workout plan created successfully', 'plan_id': plan_id}), 201
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@coach_bp.route('/workout-plans/<int:coach_id>', methods=['GET'])
def get_coach_workout_plans(coach_id):
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            wp.*,
            u.full_name as athlete_name,
            COUNT(DISTINCT ws.session_id) as session_count
        FROM workout_plans wp
        LEFT JOIN athletes a ON wp.athlete_id = a.athlete_id
        LEFT JOIN users u ON a.user_id = u.user_id
        LEFT JOIN workout_sessions ws ON wp.plan_id = ws.plan_id
        WHERE wp.coach_id = %s
        GROUP BY wp.plan_id
        ORDER BY wp.created_at DESC
    """, (coach_id,))
    
    plans = cursor.fetchall()
    cursor.close()
    
    return jsonify({'plans': plans}), 200

@coach_bp.route('/workout-plans/detail/<int:plan_id>', methods=['GET'])
def get_workout_plan_detail(plan_id):
    from app import mysql
    
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT * FROM workout_plans WHERE plan_id = %s", (plan_id,))
    plan = cursor.fetchone()
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    cursor.execute("""
        SELECT * FROM workout_sessions 
        WHERE plan_id = %s 
        ORDER BY day_number
    """, (plan_id,))
    sessions = cursor.fetchall()
    
    for session in sessions:
        cursor.execute("""
            SELECT * FROM workout_exercises 
            WHERE session_id = %s 
            ORDER BY order_number
        """, (session['session_id'],))
        session['exercises'] = cursor.fetchall()
    
    cursor.close()
    
    plan['sessions'] = sessions
    return jsonify({'plan': plan}), 200

@coach_bp.route('/athlete-workouts/<int:athlete_id>', methods=['GET'])
def get_athlete_workouts(athlete_id):
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            wp.*,
            u.full_name as coach_name
        FROM workout_plans wp
        JOIN coaches c ON wp.coach_id = c.coach_id
        JOIN users u ON c.user_id = u.user_id
        WHERE wp.athlete_id = %s
        ORDER BY wp.created_at DESC
    """, (athlete_id,))
    
    plans = cursor.fetchall()
    cursor.close()
    
    return jsonify({'plans': plans}), 200

@coach_bp.route('/workout-plans/duplicate', methods=['POST', 'OPTIONS'])
def duplicate_workout_plan():
    """Duplicate a workout plan and assign to an athlete"""
    if request.method == 'OPTIONS':
        return '', 200
        
    from app import mysql
    data = request.json
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("SELECT * FROM workout_plans WHERE plan_id = %s", (data['plan_id'],))
        original_plan = cursor.fetchone()
        
        if not original_plan:
            cursor.close()
            return jsonify({'error': 'Plan not found'}), 404
        
        cursor.execute("""
            INSERT INTO workout_plans 
            (coach_id, athlete_id, plan_name, description, duration_weeks, difficulty_level, is_template)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            original_plan['coach_id'],
            data['athlete_id'],
            original_plan['plan_name'],
            original_plan['description'],
            original_plan['duration_weeks'],
            original_plan['difficulty_level'],
            False
        ))
        
        new_plan_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM workout_sessions WHERE plan_id = %s", (data['plan_id'],))
        sessions = cursor.fetchall()
        
        for session in sessions:
            cursor.execute("""
                INSERT INTO workout_sessions 
                (plan_id, session_name, day_number, description)
                VALUES (%s, %s, %s, %s)
            """, (new_plan_id, session['session_name'], session['day_number'], session['description']))
            
            new_session_id = cursor.lastrowid
            
            cursor.execute("SELECT * FROM workout_exercises WHERE session_id = %s", (session['session_id'],))
            exercises = cursor.fetchall()
            
            for exercise in exercises:
                cursor.execute("""
                    INSERT INTO workout_exercises 
                    (session_id, exercise_name, sets, reps, duration, rest_time, notes, order_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_session_id,
                    exercise['exercise_name'],
                    exercise['sets'],
                    exercise['reps'],
                    exercise['duration'],
                    exercise['rest_time'],
                    exercise['notes'],
                    exercise['order_number']
                ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Workout plan assigned successfully', 'new_plan_id': new_plan_id}), 201
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

# ========== ANALYTICS ==========

@coach_bp.route('/analytics/<int:coach_id>', methods=['GET'])
def get_coach_analytics(coach_id):
    """Get comprehensive analytics for coach"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM athletes 
            WHERE coach_id = %s
        """, (coach_id,))
        result = cursor.fetchone()
        total_athletes = result['count'] if result else 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT athlete_id) as count 
            FROM performance_tracking 
            WHERE athlete_id IN (SELECT athlete_id FROM athletes WHERE coach_id = %s)
            AND date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """, (coach_id,))
        result = cursor.fetchone()
        active_athletes = result['count'] if result else 0
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM coaching_requests 
            WHERE coach_id = %s AND status = 'pending'
        """, (coach_id,))
        result = cursor.fetchone()
        pending_requests = result['count'] if result else 0
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM coach_assignments 
            WHERE coach_id = %s AND status = 'completed'
        """, (coach_id,))
        result = cursor.fetchone()
        completed_tasks = result['count'] if result else 0
        
        cursor.execute("""
            SELECT DATE_FORMAT(request_date, '%%Y-%%m-%%d') as date, COUNT(*) as count 
            FROM coaching_requests 
            WHERE coach_id = %s AND request_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE_FORMAT(request_date, '%%Y-%%m-%%d')
            ORDER BY date
        """, (coach_id,))
        request_trends = cursor.fetchall()
        
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM coaching_requests 
            WHERE coach_id = %s
            GROUP BY status
        """, (coach_id,))
        rows = cursor.fetchall()
        request_status = {row['status']: row['count'] for row in rows} if rows else {}
        
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM coach_assignments 
            WHERE coach_id = %s
            GROUP BY status
        """, (coach_id,))
        rows = cursor.fetchall()
        task_completion = {row['status']: row['count'] for row in rows} if rows else {}
        
        cursor.close()
        
        return jsonify({
            'total_athletes': total_athletes,
            'active_athletes': active_athletes,
            'pending_requests': pending_requests,
            'completed_tasks': completed_tasks,
            'request_trends': request_trends,
            'request_status': request_status,
            'task_completion': task_completion
        }), 200
        
    except Exception as e:
        cursor.close()
        return jsonify({'error': str(e)}), 500

# ========== PROFILE PICTURE UPLOAD ==========

@coach_bp.route('/upload-picture', methods=['POST', 'OPTIONS'])
def upload_picture():
    """Upload coach profile picture"""
    if request.method == 'OPTIONS':
        return '', 200
    
    from app import mysql, allowed_file
    
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    try:
        user_data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = user_data['user_id']
    except:
        return jsonify({'error': 'Invalid token'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = 'static/uploads/profiles/'
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, f"{user_id}_{filename}")
        file.save(filepath)
        
        # Update database
        profile_url = f'/static/uploads/profiles/{user_id}_{filename}'
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE users SET profile_picture = %s WHERE user_id = %s", (profile_url, user_id))
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'message': 'Profile picture uploaded successfully',
            'profile_picture': profile_url
        }), 200
    
    return jsonify({'error': 'Invalid file type'}), 400
