def create_notification(mysql, user_id, notification_type, title, message, related_id=None):
    """
    Helper function to create notifications
    
    Args:
        mysql: MySQL connection object
        user_id: User ID to notify
        notification_type: 'request', 'task', 'goal', 'message', 'system'
        title: Notification title
        message: Notification message
        related_id: Optional related entity ID
    """
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO notifications (user_id, notification_type, title, message, related_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, notification_type, title, message, related_id))
    mysql.connection.commit()
    cursor.close()