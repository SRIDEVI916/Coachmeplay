from flask import Blueprint, request, jsonify
from datetime import datetime

message_bp = Blueprint('message', __name__)


@message_bp.route('/conversations', methods=['GET'])
def get_conversations():
    """Get list of all conversations for a user"""
    from app import mysql
    
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    cursor = mysql.connection.cursor()
    
    # Get all unique users this person has chatted with
    cursor.execute("""
        SELECT DISTINCT 
            CASE 
                WHEN sender_id = %s THEN receiver_id 
                ELSE sender_id 
            END as other_user_id,
            u.full_name,
            u.profile_picture,
            (SELECT message_text FROM messages 
             WHERE (sender_id = %s AND receiver_id = other_user_id) 
                OR (sender_id = other_user_id AND receiver_id = %s)
             ORDER BY sent_at DESC LIMIT 1) as last_message,
            (SELECT sent_at FROM messages 
             WHERE (sender_id = %s AND receiver_id = other_user_id) 
                OR (sender_id = other_user_id AND receiver_id = %s)
             ORDER BY sent_at DESC LIMIT 1) as last_message_time,
            (SELECT COUNT(*) FROM messages 
             WHERE sender_id = other_user_id AND receiver_id = %s AND is_read = FALSE) as unread_count
        FROM messages m
        JOIN users u ON u.user_id = CASE 
            WHEN m.sender_id = %s THEN m.receiver_id 
            ELSE m.sender_id 
        END
        WHERE sender_id = %s OR receiver_id = %s
        ORDER BY last_message_time DESC
    """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id))
    
    conversations = cursor.fetchall()
    cursor.close()
    
    return jsonify({'conversations': conversations}), 200


@message_bp.route('/messages/<int:other_user_id>', methods=['GET'])
def get_messages(other_user_id):
    """Get all messages between two users"""
    from app import mysql
    
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    cursor = mysql.connection.cursor()
    
    # Get all messages between these two users
    cursor.execute("""
        SELECT m.message_id, m.sender_id, m.receiver_id, m.message_text, 
               m.is_read, m.sent_at, u.full_name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.user_id
        WHERE (sender_id = %s AND receiver_id = %s) 
           OR (sender_id = %s AND receiver_id = %s)
        ORDER BY sent_at ASC
    """, (user_id, other_user_id, other_user_id, user_id))
    
    messages = cursor.fetchall()
    
    # Mark all messages from other user as read
    cursor.execute("""
        UPDATE messages 
        SET is_read = TRUE 
        WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
    """, (other_user_id, user_id))
    
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'messages': messages}), 200


@message_bp.route('/send', methods=['POST'])
def send_message():
    """Send a new message"""
    from app import mysql
    from utils import create_notification
    
    data = request.json
    required_fields = ['sender_id', 'receiver_id', 'message_text']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, message_text)
            VALUES (%s, %s, %s)
        """, (data['sender_id'], data['receiver_id'], data['message_text']))
        
        mysql.connection.commit()
        message_id = cursor.lastrowid
        
        # Get sender name
        cursor.execute("SELECT full_name FROM users WHERE user_id = %s", (data['sender_id'],))
        sender = cursor.fetchone()
        sender_name = sender['full_name'] if sender else 'Someone'
        
        # Notify receiver about new message
        create_notification(
            mysql,
            data['receiver_id'],
            'message',
            'New Message',
            f'{sender_name} sent you a message',
            message_id
        )
        
        cursor.close()
        
        return jsonify({
            'message': 'Message sent successfully',
            'message_id': message_id
        }), 201
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500


@message_bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """Get total unread message count for a user"""
    from app import mysql
    
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM messages 
        WHERE receiver_id = %s AND is_read = FALSE
    """, (user_id,))
    
    result = cursor.fetchone()
    count = result['count'] if result else 0
    
    cursor.close()
    
    return jsonify({'count': count}), 200


@message_bp.route('/mark-read/<int:message_id>', methods=['PUT'])
def mark_message_read(message_id):
    """Mark a specific message as read"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE messages 
            SET is_read = TRUE 
            WHERE message_id = %s
        """, (message_id,))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Message marked as read'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500
