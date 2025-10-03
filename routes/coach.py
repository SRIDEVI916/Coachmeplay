from flask import Blueprint, request, jsonify
from datetime import datetime

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
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            SELECT request_id FROM coaching_requests 
            WHERE athlete_id = %s AND coach_id = %s AND status = 'pending'
        """, (data['athlete_id'], data['coach_id']))
        
        if cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'You already have a pending request with this coach'}), 400
        
        cursor.execute("""
            INSERT INTO coaching_requests (athlete_id, coach_id, message, status, request_date)
            VALUES (%s, %s, %s, 'pending', NOW())
        """, (data['athlete_id'], data['coach_id'], data['message']))
        
        mysql.connection.commit()
        request_id = cursor.lastrowid
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
    
    cursor = mysql.connection.cursor()
    
    try:
        # First, get the request details
        cursor.execute("""
            SELECT athlete_id, coach_id 
            FROM coaching_requests 
            WHERE request_id = %s
        """, (request_id,))
        
        request_info = cursor.fetchone()
        
        if not request_info:
            cursor.close()
            return jsonify({'error': 'Request not found'}), 404
        
        # Update request status
        cursor.execute("""
            UPDATE coaching_requests 
            SET status = %s, response_date = NOW()
            WHERE request_id = %s
        """, (data['status'], request_id))
        
        # If accepted, assign athlete to coach
        if data['status'] == 'accepted':
            cursor.execute("""
                UPDATE athletes 
                SET coach_id = %s
                WHERE athlete_id = %s
            """, (request_info['coach_id'], request_info['athlete_id']))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': f'Request {data["status"]} successfully'}), 200
        
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

@coach_bp.route('/upload-picture', methods=['POST'])
def upload_coach_picture():
    """Upload coach profile picture"""
    from app import mysql, allowed_file
    from werkzeug.utils import secure_filename
    import os
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"coach_{user_id}_{file.filename}")
        filepath = os.path.join('static/uploads/profiles', filename)
        file.save(filepath)
        
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                UPDATE users 
                SET profile_picture = %s
                WHERE user_id = %s
            """, (filepath, user_id))
            
            mysql.connection.commit()
            cursor.close()
            
            return jsonify({
                'message': 'Picture uploaded successfully',
                'file_path': '/' + filepath
            }), 200
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type. Use PNG, JPG, or GIF'}), 400

@coach_bp.route('/my-athletes/<int:coach_id>', methods=['GET'])
def get_coach_athletes(coach_id):
    """Get list of athletes assigned to this coach"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT a.athlete_id, u.full_name, u.email, u.profile_picture,
               a.sport_type, a.skill_level, a.age, a.height, a.weight
        FROM athletes a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.coach_id = %s
        ORDER BY u.full_name
    """, (coach_id,))
    
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
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO coach_assignments (coach_id, athlete_id, task_title, task_description, due_date, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """, (
            data['coach_id'],
            data['athlete_id'],
            data['task_title'],
            data.get('task_description', ''),
            data['due_date'],
            data.get('priority', 'medium')
        ))
        
        mysql.connection.commit()
        assignment_id = cursor.lastrowid
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
@coach_bp.route('/analytics/<int:coach_id>', methods=['GET'])
def get_coach_analytics(coach_id):
    """Get comprehensive analytics for coach"""
    from app import mysql
    from datetime import datetime, timedelta
    
    cursor = mysql.connection.cursor()
    
    try:
        # Total athletes
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM athletes 
            WHERE coach_id = %s
        """, (coach_id,))
        result = cursor.fetchone()
        total_athletes = result['count'] if result else 0
        
        # Active athletes (have logged performance in last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(DISTINCT athlete_id) as count 
            FROM performance_tracking 
            WHERE athlete_id IN (SELECT athlete_id FROM athletes WHERE coach_id = %s)
            AND date >= %s
        """, (coach_id, week_ago))
        result = cursor.fetchone()
        active_athletes = result['count'] if result else 0
        
        # Pending requests
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM coaching_requests 
            WHERE coach_id = %s AND status = 'pending'
        """, (coach_id,))
        result = cursor.fetchone()
        pending_requests = result['count'] if result else 0
        
        # Completed tasks
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM coach_assignments 
            WHERE coach_id = %s AND status = 'completed'
        """, (coach_id,))
        result = cursor.fetchone()
        completed_tasks = result['count'] if result else 0
        
        # Request trends (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT DATE_FORMAT(request_date, '%%Y-%%m-%%d') as date, COUNT(*) as count 
            FROM coaching_requests 
            WHERE coach_id = %s AND request_date >= %s
            GROUP BY DATE_FORMAT(request_date, '%%Y-%%m-%%d')
            ORDER BY date
        """, (coach_id, thirty_days_ago))
        request_trends = cursor.fetchall()
        
        # Request status distribution
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM coaching_requests 
            WHERE coach_id = %s
            GROUP BY status
        """, (coach_id,))
        rows = cursor.fetchall()
        request_status = {row['status']: row['count'] for row in rows} if rows else {}
        
        # Task completion distribution
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
        print(f"Coach analytics error: {str(e)}")
        return jsonify({
            'total_athletes': 0,
            'active_athletes': 0,
            'pending_requests': 0,
            'completed_tasks': 0,
            'request_trends': [],
            'request_status': {},
            'task_completion': {},
            'error': str(e)
        }), 200

@coach_bp.route('/athlete-performance/<int:coach_id>', methods=['GET'])
def get_individual_athlete_performance(coach_id):
    """Get individual performance stats for each athlete"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            a.athlete_id,
            u.full_name as athlete_name,
            a.sport_type,
            (SELECT COUNT(*) FROM performance_tracking WHERE athlete_id = a.athlete_id) as total_workouts,
            (SELECT COUNT(*) FROM goals WHERE athlete_id = a.athlete_id AND status = 'active') as active_goals,
            (SELECT COUNT(*) FROM goals WHERE athlete_id = a.athlete_id AND status = 'completed') as completed_goals,
            (SELECT COUNT(*) FROM coach_assignments WHERE athlete_id = a.athlete_id AND status = 'completed') as completed_tasks
        FROM athletes a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.coach_id = %s
        ORDER BY total_workouts DESC
    """, (coach_id,))
    
    performance = cursor.fetchall()
    cursor.close()
    
    return jsonify({'performance': performance}), 200




