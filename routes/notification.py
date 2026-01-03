from flask import Blueprint, request, jsonify, current_app
from routes.auth import token_required

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/', methods=['GET'])
@token_required
def get_notifications(current_user):
    from app import mysql
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
        SELECT notification_id, notification_type, title, message, 
               is_read, related_id, created_at 
        FROM notifications 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 50
    """, (current_user['user_id'],))
    
    notifications = cursor.fetchall()
    cursor.close()
    
    return jsonify({'notifications': notifications}), 200

@notification_bp.route('/unread-count', methods=['GET'])
@token_required
def get_unread_count(current_user):
    from app import mysql
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM notifications 
        WHERE user_id = %s AND is_read = FALSE
    """, (current_user['user_id'],))
    
    result = cursor.fetchone()
    cursor.close()
    
    return jsonify({'count': result['count']}), 200

@notification_bp.route('/<int:notification_id>/read', methods=['PUT'])
@token_required
def mark_as_read(current_user, notification_id):
    from app import mysql
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
        UPDATE notifications 
        SET is_read = TRUE 
        WHERE notification_id = %s AND user_id = %s
    """, (notification_id, current_user['user_id']))
    
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'message': 'Notification marked as read'}), 200

@notification_bp.route('/mark-all-read', methods=['PUT'])
@token_required
def mark_all_read(current_user):
    from app import mysql
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
        UPDATE notifications 
        SET is_read = TRUE 
        WHERE user_id = %s
    """, (current_user['user_id'],))
    
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'message': 'All notifications marked as read'}), 200
