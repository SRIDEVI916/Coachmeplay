from flask import Flask, render_template, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from config import Config
import os
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize MySQL
mysql = MySQL(app)

# File upload configuration
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# CORS Configuration - Manual approach for better control
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Import blueprints AFTER app initialization
from routes.auth import auth_bp
from routes.athlete import athlete_bp
from routes.coach import coach_bp
from routes.notification import notification_bp
from routes.message import message_bp
from routes.shop import shop_bp
from routes.venue import venue_bp
from routes.feedback import feedback_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(athlete_bp, url_prefix='/api/athlete')
app.register_blueprint(coach_bp, url_prefix='/api/coach')
app.register_blueprint(notification_bp, url_prefix='/api/notifications')
app.register_blueprint(message_bp, url_prefix='/api/messages')
app.register_blueprint(shop_bp, url_prefix='/api/shop')
app.register_blueprint(venue_bp, url_prefix='/api/venue')
app.register_blueprint(feedback_bp, url_prefix='/api/feedback')

# ========== HTML PAGE ROUTES ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

# Athlete Routes
@app.route('/athlete/dashboard')
def athlete_dashboard():
    return render_template('athlete/dashboard.html')

@app.route('/athlete/performance')
def athlete_performance():
    return render_template('athlete/performance.html')

@app.route('/athlete/nutrition')
def athlete_nutrition():
    return render_template('athlete/nutrition.html')

@app.route('/athlete/find-coach')
def athlete_find_coach():
    return render_template('athlete/find_coach.html')

@app.route('/athlete/profile')
def athlete_profile():
    return render_template('athlete/profile.html')

@app.route('/athlete/coach-detail')
def athlete_coach_detail():
    return render_template('athlete/coach_detail.html')

@app.route('/athlete/analytics')
def athlete_analytics():
    return render_template('athlete/analytics.html')

@app.route('/athlete/my-workouts')
def athlete_my_workouts():
    return render_template('athlete/my_workouts.html')

@app.route('/athlete/workout-plan/<int:plan_id>')
def athlete_workout_detail(plan_id):
    return render_template('athlete/workout_detail.html')

@app.route('/athlete/workout-session')
def athlete_workout_session():
    return render_template('athlete/workout_session.html')

# Coach Routes
@app.route('/coach/dashboard')
def coach_dashboard():
    return render_template('coach/dashboard.html')

@app.route('/coach/requests')
def coach_requests():
    return render_template('coach/requests.html')

@app.route('/coach/profile')
def coach_profile():
    return render_template('coach/profile.html')

@app.route('/coach/athlete-detail')
def coach_athlete_detail():
    return render_template('coach/athlete_detail.html')

@app.route('/coach/analytics')
def coach_analytics():
    return render_template('coach/analytics.html')

@app.route('/coach/assign-task')
def coach_assign_task():
    return render_template('coach/assign_task.html')

@app.route('/coach/students')
def coach_students():
    return render_template('coach/students.html')

@app.route('/coach/athlete/<int:athlete_id>')
def coach_athlete_detail_view(athlete_id):
    return render_template('coach/athlete_detail.html')

@app.route('/coach/workout-plans')
def coach_workout_plans():
    return render_template('coach/workout_plans.html')

@app.route('/coach/create-workout')
def coach_create_workout():
    return render_template('coach/create_workout.html')

@app.route('/coach/workout-plan/<int:plan_id>')
def coach_workout_detail(plan_id):
    return render_template('coach/workout_detail.html')

# Messages
@app.route('/messages')
def messages():
    return render_template('messages.html')

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/rentals')
def rentals():
    return render_template('rentals.html')

@app.route('/venues')
def venues():
    return render_template('venues.html')

@app.route('/my-bookings')
def my_bookings():
    return render_template('my_bookings.html')

@app.route('/athlete/feedback')
def athlete_feedback():
    return render_template('athlete_feedback.html')

@app.route('/coach/give-feedback')
def coach_give_feedback():
    return render_template('coach_give_feedback.html')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)  