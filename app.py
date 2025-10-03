from flask import Flask, render_template, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from config import Config
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
mysql = MySQL(app)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Import blueprints AFTER app initialization
from routes.auth import auth_bp
from routes.athlete import athlete_bp
from routes.coach import coach_bp

# Register blueprints ONCE
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(athlete_bp, url_prefix='/api/athlete')
app.register_blueprint(coach_bp, url_prefix='/api/coach')

# Serve HTML pages
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/athlete/dashboard')
def athlete_dashboard():
    return render_template('athlete/dashboard.html')

@app.route('/coach/dashboard')
def coach_dashboard():
    return render_template('coach/dashboard.html')

@app.route('/athlete/performance')
def athlete_performance():
    return render_template('athlete/performance.html')

@app.route('/athlete/find-coach')
def athlete_find_coach():
    return render_template('athlete/find_coach.html')

@app.route('/coach/requests')
def coach_requests():
    return render_template('coach/requests.html')

@app.route('/athlete/profile')
def athlete_profile():
    return render_template('athlete/profile.html')

@app.route('/coach/profile')
def coach_profile():
    return render_template('coach/profile.html')

@app.route('/athlete/coach-detail')
def athlete_coach_detail():
    return render_template('athlete/coach_detail.html')

@app.route('/coach/athlete-detail')
def coach_athlete_detail():
    return render_template('coach/athlete_detail.html')

@app.route('/athlete/analytics')
def athlete_analytics():
    return render_template('athlete/analytics.html')

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/coach/analytics')
def coach_analytics():
    return render_template('coach/analytics.html')

@app.route('/coach/assign-task')
def coach_assign_task():
    return render_template('coach/assign_task.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
