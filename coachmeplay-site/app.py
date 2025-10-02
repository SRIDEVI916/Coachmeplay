# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import bcrypt

app = Flask(__name__)
app.secret_key = os.urandom(24) # Use a fixed secret key in production

# --- SIMULATED USER DATA FOR DEMO ---
# Generate a new hash for 'password123' using bcrypt
DUMMY_HASHED_PASSWORD = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt())

SIMULATED_USERS = {
    "athlete@example.com": {
        "id": 1,
        "fullname": "Alex Runner",
        "email": "athlete@example.com",
        "password": DUMMY_HASHED_PASSWORD,
        "role": "athlete"
    },
    "coach@example.com": {
        "id": 2,
        "fullname": "Coach Smith",
        "email": "coach@example.com",
        "password": DUMMY_HASHED_PASSWORD,
        "role": "coach"
    },
    "venue@example.com": {
        "id": 3,
        "fullname": "City Sports Center",
        "email": "venue@example.com",
        "password": DUMMY_HASHED_PASSWORD,
        "role": "venue"
    }
}
NEXT_USER_ID = 4

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

# --- Routes ---
@app.route("/")
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not fullname or not email or not password or not role:
            flash("All fields are required.", "error")
            return render_template("register.html")

        allowed_roles = ['athlete', 'coach', 'venue']
        if role not in allowed_roles:
             flash("Please select a valid role (Athlete, Coach, or Venue).", "error")
             return render_template("register.html")

        if email in SIMULATED_USERS:
            flash("Email address already registered. Please login.", "info")
            return render_template("register.html")

        hashed_pw = hash_password(password)
        global NEXT_USER_ID
        new_user = {
            "id": NEXT_USER_ID,
            "fullname": fullname,
            "email": email,
            "password": hashed_pw,
            "role": role
        }
        SIMULATED_USERS[email] = new_user
        NEXT_USER_ID += 1

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html")

        user = SIMULATED_USERS.get(email)
        if user and check_password(user['password'], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["fullname"] = user["fullname"]
            flash(f"Welcome back, {user['fullname']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    role = session.get('role')
    if role == "athlete":
        return redirect(url_for("athlete_dashboard"))
    elif role == "coach":
        return redirect(url_for("coach_dashboard"))
    elif role == "venue":
        return redirect(url_for("venue_dashboard"))
    else:
        flash("Unknown user role.", "error")
        return redirect(url_for('home'))

@app.route("/athlete-dashboard")
def athlete_dashboard():
    if 'user_id' not in session or session.get('role') != 'athlete':
        flash('Access denied or please log in.', 'warning')
        return redirect(url_for('login'))
    return render_template("athlete/athlete_dashboard.html", user_name=session.get('fullname'))

@app.route("/coach-dashboard")
def coach_dashboard():
    if 'user_id' not in session or session.get('role') != 'coach':
        flash('Access denied or please log in.', 'warning')
        return redirect(url_for('login'))
    return render_template("coach/coach_dashboard.html", user_name=session.get('fullname'))

@app.route("/venue-dashboard")
def venue_dashboard():
    if 'user_id' not in session or session.get('role') != 'venue':
        flash('Access denied or please log in.', 'warning')
        return redirect(url_for('login'))
    return render_template("venue/venue_dashboard.html", user_name=session.get('fullname'))

# --- NEW ROUTES FOR ENHANCED PAGES ---
@app.route("/market")
def market():
    return render_template("market.html")

@app.route("/find-coach")
def find_coach():
    return render_template("find_coach.html")

@app.route("/reviews")
def reviews():
    return render_template("reviews.html")

@app.route("/training")
def training():
    if 'user_id' not in session or session.get('role') != 'athlete':
        flash('Please log in as an athlete to view training plans.', 'warning')
        return redirect(url_for('login'))
    return render_template("training.html")

@app.route("/progress")
def progress():
    if 'user_id' not in session or session.get('role') != 'athlete':
        flash('Please log in as an athlete to view progress.', 'warning')
        return redirect(url_for('login'))
    return render_template("progress.html")

@app.route("/feedback")
def feedback():
    return render_template("feedback.html")

@app.route("/diet")
def diet():
    if 'user_id' not in session or session.get('role') != 'athlete':
        flash('Please log in as an athlete to view diet plans.', 'warning')
        return redirect(url_for('login'))
    return render_template("diet.html")

@app.route("/cart")
def cart():
    return render_template("cart.html")

@app.route("/community")
def community():
    return render_template("community.html")
@app.route("/venue")
def venue():
    return render_template("venue.html")

# --- DEBUG ROUTE ---
@app.route("/test-password")
def test_password():
    test_password = "password123"
    if bcrypt.checkpw(test_password.encode('utf-8'), DUMMY_HASHED_PASSWORD):
        return "✓ Password verification works"
    else:
        return "✗ Password verification FAILED"

if __name__ == "__main__":
    app.run(debug=True)