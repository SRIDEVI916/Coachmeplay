from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

athlete_bp = Blueprint('athlete', __name__)

@athlete_bp.route('/performance', methods=['GET'])
def get_performance():
    """Get all performance records for an athlete"""
    from app import mysql
    
    athlete_id = request.args.get('athlete_id')
    
    if not athlete_id:
        return jsonify({'error': 'Athlete ID required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT performance_id, date, metric_type, metric_value, unit, notes 
        FROM performance_tracking 
        WHERE athlete_id = %s 
        ORDER BY date DESC
    """, (athlete_id,))
    
    performance_records = cursor.fetchall()
    cursor.close()
    
    return jsonify({'performance': performance_records}), 200

@athlete_bp.route('/performance', methods=['POST'])
def add_performance():
    """Add a new performance record"""
    from app import mysql
    
    data = request.json
    required_fields = ['athlete_id', 'date', 'metric_type', 'metric_value', 'unit']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO performance_tracking 
            (athlete_id, date, metric_type, metric_value, unit, notes) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data['athlete_id'], 
            data['date'], 
            data['metric_type'], 
            data['metric_value'],
            data['unit'],
            data.get('notes', '')
        ))
        
        mysql.connection.commit()
        performance_id = cursor.lastrowid
        cursor.close()
        
        return jsonify({
            'message': 'Performance record added successfully',
            'performance_id': performance_id
        }), 201
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@athlete_bp.route('/athlete-info/<int:user_id>', methods=['GET'])
def get_athlete_info(user_id):
    """Get athlete ID from user ID"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT athlete_id FROM athletes WHERE user_id = %s", (user_id,))
    athlete = cursor.fetchone()
    cursor.close()
    
    if athlete:
        return jsonify({'athlete_id': athlete['athlete_id']}), 200
    return jsonify({'error': 'Athlete not found'}), 404

@athlete_bp.route('/profile/<int:athlete_id>', methods=['GET'])
def get_athlete_profile(athlete_id):
    """Get athlete's detailed profile"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT a.athlete_id, a.height, a.weight, a.age, a.sport_type, a.sports_interest,
               a.achievements, a.bio, a.skill_level, u.full_name, u.email, u.phone_number, u.profile_picture
        FROM athletes a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.athlete_id = %s
    """, (athlete_id,))
    
    profile = cursor.fetchone()
    cursor.close()
    
    if profile:
        return jsonify({'profile': profile}), 200
    return jsonify({'error': 'Profile not found'}), 404

@athlete_bp.route('/profile', methods=['PUT'])
def update_athlete_profile():
    """Update athlete's profile with BMI calculation"""
    from app import mysql
    
    data = request.json
    
    if 'athlete_id' not in data:
        return jsonify({'error': 'Athlete ID required'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE athletes 
            SET height = %s, weight = %s, age = %s, sport_type = %s, sports_interest = %s,
                bio = %s, achievements = %s, skill_level = %s
            WHERE athlete_id = %s
        """, (
            data.get('height'),
            data.get('weight'),
            data.get('age'),
            data.get('sport_type'),
            data.get('sports_interest'),
            data.get('bio'),
            data.get('achievements'),
            data.get('skill_level'),
            data['athlete_id']
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        bmi = None
        bmi_category = None
        recommended_calories = None
        
        if data.get('height') and data.get('weight'):
            height_m = float(data['height']) / 100
            weight_kg = float(data['weight'])
            bmi = round(weight_kg / (height_m ** 2), 2)
            
            if bmi < 18.5:
                bmi_category = 'Underweight'
            elif 18.5 <= bmi < 25:
                bmi_category = 'Normal'
            elif 25 <= bmi < 30:
                bmi_category = 'Overweight'
            else:
                bmi_category = 'Obese'
            
            if data.get('age'):
                age = int(data['age'])
                bmr = (10 * weight_kg) + (6.25 * float(data['height'])) - (5 * age) + 5
                recommended_calories = round(bmr * 1.55)
        
        return jsonify({
            'message': 'Profile updated successfully',
            'bmi': bmi,
            'bmi_category': bmi_category,
            'recommended_calories': recommended_calories
        }), 200
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@athlete_bp.route('/upload-picture', methods=['POST'])
def upload_athlete_picture():
    """Upload athlete profile picture"""
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
        filename = secure_filename(f"athlete_{user_id}_{file.filename}")
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

@athlete_bp.route('/analytics/<int:athlete_id>', methods=['GET'])
def get_athlete_analytics(athlete_id):
    """Get comprehensive analytics for athlete"""
    from app import mysql
    from datetime import datetime, timedelta
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM performance_tracking 
            WHERE athlete_id = %s
        """, (athlete_id,))
        result = cursor.fetchone()
        total_workouts = result['count'] if result else 0
        
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM performance_tracking 
            WHERE athlete_id = %s AND date >= %s
        """, (athlete_id, week_ago))
        result = cursor.fetchone()
        week_workouts = result['count'] if result else 0
        
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT DATE_FORMAT(date, '%%Y-%%m-%%d') as date, AVG(metric_value) as value 
            FROM performance_tracking 
            WHERE athlete_id = %s AND date >= %s
            GROUP BY DATE_FORMAT(date, '%%Y-%%m-%%d')
            ORDER BY date
        """, (athlete_id, thirty_days_ago))
        performance_trend = cursor.fetchall()
        
        cursor.execute("""
            SELECT metric_type, COUNT(*) as count 
            FROM performance_tracking 
            WHERE athlete_id = %s
            GROUP BY metric_type
        """, (athlete_id,))
        rows = cursor.fetchall()
        metric_distribution = {row['metric_type']: row['count'] for row in rows} if rows else {}
        
        cursor.execute("""
            SELECT DAYNAME(date) as day, COUNT(*) as count 
            FROM performance_tracking 
            WHERE athlete_id = %s AND date >= %s
            GROUP BY DAYNAME(date)
        """, (athlete_id, week_ago))
        rows = cursor.fetchall()
        weekly_data = {row['day']: row['count'] for row in rows} if rows else {}
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM goals 
            WHERE athlete_id = %s AND status = 'active'
        """, (athlete_id,))
        result = cursor.fetchone()
        active_goals = result['count'] if result else 0
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM goals 
            WHERE athlete_id = %s AND status = 'completed'
        """, (athlete_id,))
        result = cursor.fetchone()
        completed_goals = result['count'] if result else 0
        
        cursor.close()
        
        return jsonify({
            'total_workouts': total_workouts,
            'week_workouts': week_workouts,
            'performance_trend': performance_trend,
            'metric_distribution': metric_distribution,
            'weekly_data': weekly_data,
            'active_goals': active_goals,
            'completed_goals': completed_goals
        }), 200
        
    except Exception as e:
        cursor.close()
        print(f"Analytics error: {str(e)}")
        return jsonify({
            'total_workouts': 0,
            'week_workouts': 0,
            'performance_trend': [],
            'metric_distribution': {},
            'weekly_data': {},
            'active_goals': 0,
            'completed_goals': 0,
            'error': str(e)
        }), 200

@athlete_bp.route('/goals/<int:athlete_id>', methods=['GET'])
def get_athlete_goals(athlete_id):
    """Get all goals for an athlete"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT goal_id, goal_type, target_value, current_value, target_date, status, created_date
        FROM goals 
        WHERE athlete_id = %s
        ORDER BY created_date DESC
    """, (athlete_id,))
    
    goals = cursor.fetchall()
    cursor.close()
    
    return jsonify({'goals': goals}), 200

@athlete_bp.route('/goals', methods=['POST'])
def create_goal():
    """Create a new goal"""
    from app import mysql
    
    data = request.json
    required_fields = ['athlete_id', 'goal_type', 'target_value', 'current_value', 'target_date']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO goals (athlete_id, goal_type, target_value, current_value, target_date, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (
            data['athlete_id'],
            data['goal_type'],
            data['target_value'],
            data['current_value'],
            data['target_date']
        ))
        
        mysql.connection.commit()
        goal_id = cursor.lastrowid
        cursor.close()
        
        return jsonify({
            'message': 'Goal created successfully',
            'goal_id': goal_id
        }), 201
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@athlete_bp.route('/goals/<int:goal_id>/complete', methods=['PUT'])
def complete_goal(goal_id):
    """Mark a goal as completed"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE goals 
            SET status = 'completed', current_value = target_value
            WHERE goal_id = %s
        """, (goal_id,))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Goal marked as completed!'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@athlete_bp.route('/goals/<int:goal_id>/update-progress', methods=['PUT'])
def update_goal_progress(goal_id):
    """Update current progress value for a goal"""
    from app import mysql
    
    data = request.json
    
    if 'current_value' not in data:
        return jsonify({'error': 'Current value required'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE goals 
            SET current_value = %s
            WHERE goal_id = %s
        """, (data['current_value'], goal_id))
        
        cursor.execute("""
            SELECT target_value, current_value 
            FROM goals 
            WHERE goal_id = %s
        """, (goal_id,))
        
        goal = cursor.fetchone()
        if goal and goal['current_value'] >= goal['target_value']:
            cursor.execute("""
                UPDATE goals 
                SET status = 'completed'
                WHERE goal_id = %s
            """, (goal_id,))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Progress updated!'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@athlete_bp.route('/assignments/<int:assignment_id>/update-status', methods=['PUT'])
def update_assignment_status(assignment_id):
    """Athlete updates assignment status"""
    from app import mysql
    
    data = request.json
    
    if 'status' not in data or data['status'] not in ['pending', 'in_progress', 'completed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE coach_assignments 
            SET status = %s
            WHERE assignment_id = %s
        """, (data['status'], assignment_id))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Status updated successfully'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500
