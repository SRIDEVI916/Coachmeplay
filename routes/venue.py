from flask import Blueprint, request, jsonify
from datetime import datetime

venue_bp = Blueprint('venue', __name__)

@venue_bp.route('/venues', methods=['GET'])
def get_venues():
    """Get all venues with optional filters"""
    from app import mysql
    sport_type = request.args.get('sport_type')
    city = request.args.get('city')
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM venues WHERE is_active = TRUE"
    params = []
    if sport_type:
        query += " AND sport_type = %s"
        params.append(sport_type)
    if city:
        query += " AND city = %s"
        params.append(city)
    query += " ORDER BY venue_name ASC"
    cursor.execute(query, tuple(params) if params else None)
    venues = cursor.fetchall()
    cursor.close()
    return jsonify({'venues': venues}), 200

@venue_bp.route('/venues/<int:venue_id>', methods=['GET'])
def get_venue_detail(venue_id):
    """Get venue details"""
    from app import mysql
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM venues WHERE venue_id = %s", (venue_id,))
    venue = cursor.fetchone()
    cursor.close()
    if venue:
        return jsonify({'venue': venue}), 200
    return jsonify({'error': 'Venue not found'}), 404

def pad_time_string(t):
    # Pads a time string "H:M:S" --> "HH:MM:SS"
    parts = str(t).split(':')
    return ':'.join([p.zfill(2) for p in parts])

@venue_bp.route('/venues/<int:venue_id>/availability', methods=['GET'])
def check_venue_availability(venue_id):
    """Check venue availability for a specific date"""
    from app import mysql
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date parameter required'}), 400
    cursor = mysql.connection.cursor()
    # Get existing bookings
    cursor.execute("""
        SELECT start_time, end_time 
        FROM venue_bookings 
        WHERE venue_id = %s AND booking_date = %s AND status != 'cancelled'
        ORDER BY start_time
    """, (venue_id, date))
    bookings = cursor.fetchall()
    cursor.close()
    # Convert time objects to zero-padded strings
    booked_slots = []
    for b in bookings:
        booked_slots.append({
            'start': pad_time_string(b['start_time']),
            'end': pad_time_string(b['end_time'])
        })
    # Optional: Debug logging (remove in production)
    print(f"Returning booked_slots for venue {venue_id} on {date}: {booked_slots}")
    return jsonify({'booked_slots': booked_slots}), 200

@venue_bp.route('/bookings/create', methods=['POST'])
def create_booking():
    """Create a venue booking"""
    from app import mysql
    import traceback
    data = request.json
    cursor = mysql.connection.cursor()
    try:
        # Check venue exists
        cursor.execute("SELECT hourly_rate FROM venues WHERE venue_id = %s", (data['venue_id'],))
        venue = cursor.fetchone()
        if not venue:
            cursor.close()
            return jsonify({'error': 'Venue not found'}), 404
        # Check for conflicts
        cursor.execute("""
            SELECT booking_id FROM venue_bookings 
            WHERE venue_id = %s AND booking_date = %s AND status != 'cancelled'
            AND (
                (start_time < %s AND end_time > %s) OR
                (start_time < %s AND end_time > %s) OR
                (start_time >= %s AND end_time <= %s)
            )
        """, (
            data['venue_id'], data['booking_date'],
            data['start_time'], data['start_time'],
            data['end_time'], data['end_time'],
            data['start_time'], data['end_time']
        ))
        if cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Time slot already booked'}), 400
        # Calculate duration and cost - handle HH:MM:SS format
        start_time_str = data['start_time']
        end_time_str = data['end_time']
        if start_time_str.count(':') == 2:
            start = datetime.strptime(start_time_str, '%H:%M:%S')
            end = datetime.strptime(end_time_str, '%H:%M:%S')
        else:
            start = datetime.strptime(start_time_str, '%H:%M')
            end = datetime.strptime(end_time_str, '%H:%M')
        duration = (end - start).seconds / 3600
        total_cost = float(venue['hourly_rate']) * duration
        # Create booking
        cursor.execute("""
            INSERT INTO venue_bookings 
            (user_id, venue_id, booking_date, start_time, end_time, total_cost, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'confirmed')
        """, (
            data['user_id'],
            data['venue_id'],
            data['booking_date'],
            start_time_str,
            end_time_str,
            total_cost
        ))
        booking_id = cursor.lastrowid
        mysql.connection.commit()
        cursor.close()
        return jsonify({
            'message': 'Booking confirmed successfully',
            'booking_id': booking_id,
            'total_amount': total_cost
        }), 201
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        print(f"Booking error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/bookings/<int:user_id>', methods=['GET'])
def get_user_bookings(user_id):
    """Get user's venue bookings"""
    from app import mysql
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT vb.*, v.venue_name, v.sport_type, v.location, v.image_url
        FROM venue_bookings vb
        JOIN venues v ON vb.venue_id = v.venue_id
        WHERE vb.user_id = %s
        ORDER BY vb.booking_date DESC, vb.start_time DESC
    """, (user_id,))
    bookings = cursor.fetchall()
    cursor.close()
    # Convert time objects to zero-padded strings for JSON serialization
    for booking in bookings:
        if booking.get('start_time'):
            booking['start_time'] = pad_time_string(booking['start_time'])
        if booking.get('end_time'):
            booking['end_time'] = pad_time_string(booking['end_time'])
    return jsonify({'bookings': bookings}), 200

@venue_bp.route('/bookings/<int:booking_id>/cancel', methods=['PUT'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    from app import mysql
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            UPDATE venue_bookings 
            SET status = 'cancelled'
            WHERE booking_id = %s
        """, (booking_id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'Booking cancelled successfully'}), 200
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500
