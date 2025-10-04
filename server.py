import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy 
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime, timedelta
from ml_models.quiz_generator_v3 import generate_personalized_quiz, generate_weekly_quiz, assign_weekly_points, start_integrated_chatbot

from flask import session  # Added import for session

import threading
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+mysqlconnector://root:2580@127.0.0.1/student_platform_db"
app.config['SECRET_KEY'] = "a-very-strong-secret-key-for-this-hackathon"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    db.create_all()
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Track server start time for logout all users on restart
server_start_time = time.time()

# Background thread to stop attendance sessions after 3 minutes
def attendance_session_watcher():
    while True:
        time.sleep(30)  # check every 30 seconds
        with app.app_context():
            active_sessions = AttendanceSession.query.filter_by(is_active=True).all()
            now = datetime.utcnow()
            for session in active_sessions:
                if session.start_time and (now - session.start_time).total_seconds() >= 180:
                    session.is_active = False
                    db.session.commit()

# Start the background thread
threading.Thread(target=attendance_session_watcher, daemon=True).start()

# --- New Model for Weekly Quiz Activation ---
class WeeklyQuizStatus(db.Model):
    __tablename__ = 'weekly_quiz_status'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=False)

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash(f"Access for {role}s only.", "danger")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes for Teacher to Activate/Deactivate Weekly Quiz ---
@app.route('/teacher/weekly_quiz_status', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def weekly_quiz_status():
    status = WeeklyQuizStatus.query.first()
    if request.method == 'POST':
        action = request.form.get('action')
        if not status:
            status = WeeklyQuizStatus(is_active=False)
            db.session.add(status)
        if action == 'activate':
            status.is_active = True
            flash('Weekly quiz activated.', 'success')
        elif action == 'deactivate':
            status.is_active = False
            flash('Weekly quiz deactivated.', 'info')
        db.session.commit()
        return redirect(url_for('weekly_quiz_status'))
    return render_template('weekly_quiz_status.html', status=status)

# --- Modify Weekly Quiz Route to Check Activation ---
@app.route('/quiz/weekly')
@login_required
def weekly_quiz():
    status = WeeklyQuizStatus.query.first()
    if not status or not status.is_active:
        flash('Weekly quiz is not active currently.', 'warning')
        return redirect(url_for('dashboard'))
    quiz = generate_weekly_quiz()
    return render_template('quiz.html', quiz=quiz)

# --- Leaderboard Route ---
@app.route('/leaderboard')
@login_required
def leaderboard():
    # Mock implementation: get top 3 users by weekly quiz scores
    # In real app, query database for actual scores
    top_users = [
        {'username': 'user1', 'score': 95, 'reward': 1000},
        {'username': 'user2', 'score': 90, 'reward': 750},
        {'username': 'user3', 'score': 85, 'reward': 500},
    ]
    return render_template('leaderboard.html', top_users=top_users)

# --- Academic Analysis Route ---
@app.route('/academic_analysis')
@login_required
@role_required('student')
def academic_analysis():
    # Mock data for charts
    attendance_data = {'Present': 80, 'Absent': 20}
    quiz_scores = [70, 75, 80, 85, 90]
    academic_marks = [65, 70, 75, 80, 85]
    return render_template('academic_analysis.html',
                           attendance_data=attendance_data,
                           quiz_scores=quiz_scores,
                           academic_marks=academic_marks)

# Before request handler to logout users if server restarted after their login
@app.before_request
def check_session_validity():
    if current_user.is_authenticated:
        # Flask session does not store login time by default, so we store it in session on login
        login_time = session.get('login_time')
        if login_time is None:
            # Set login time if not set
            session['login_time'] = time.time()
        else:
            if login_time < server_start_time:
                logout_user()
                flash('You have been logged out due to server restart. Please login again.', 'info')
                return redirect(url_for('login'))

# --- Models ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    user = db.relationship('User', backref=db.backref('student', uselist=False))

class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    user = db.relationship('User', backref=db.backref('teacher', uselist=False))

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)

class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    start_time = db.Column(db.DateTime, server_default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)

class Complaint(db.Model):
    __tablename__ = 'complaints'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Main & Authentication Routes ---
@app.route('/')
def home():
    return render_template('home.html', current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            session['login_time'] = time.time()  # Set login time in session on successful login
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        role = request.form.get('role')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        if role == 'student':
            new_profile = Student(full_name=full_name, user_id=new_user.id)
        elif role == 'teacher':
            new_profile = Teacher(full_name=full_name, user_id=new_user.id)
        else: 
            new_profile = None

        if new_profile:
            db.session.add(new_profile)
            db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- Dashboard Redirector ---
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin': return redirect(url_for('admin_dashboard'))
    if current_user.role == 'teacher': return redirect(url_for('teacher_dashboard'))
    if current_user.role == 'student': return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))
    
# --- Admin Routes ---
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    # In a real app, you'd query for this data
    at_risk_students = []
    all_students = []
    return render_template('admin_dashboard.html', at_risk_students=at_risk_students, all_students=all_students)

@app.route('/add_user', methods=['POST'])
@login_required
@role_required('admin')
def add_user():
    full_name = request.form.get('full_name')
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    if User.query.filter_by(username=username).first():
        flash('Username already exists.')
        return redirect(url_for('admin_dashboard'))

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()

    if role == 'student':
        new_profile = Student(full_name=full_name, user_id=new_user.id)
    elif role == 'teacher':
        new_profile = Teacher(full_name=full_name, user_id=new_user.id)
    else:
        new_profile = None

    if new_profile:
        db.session.add(new_profile)
        db.session.commit()

    flash('User added successfully.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/complaints')
@login_required
@role_required('admin')
def view_complaints():
    complaints = Complaint.query.order_by(Complaint.submitted_at.desc()).all()
    return render_template('complaints.html', complaints=complaints)

# --- Teacher Routes ---
@app.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    assignments = Assignment.query.filter_by(teacher_id=current_user.teacher.id).all()
    active_session = AttendanceSession.query.filter_by(teacher_id=current_user.teacher.id, is_active=True).first()
    return render_template('teacher_dashboard.html', active_session=active_session, assignments=assignments)

@app.route('/start_attendance_session', methods=['POST'])
@login_required
@role_required('teacher')
def start_attendance_session():
    existing = AttendanceSession.query.filter_by(teacher_id=current_user.teacher.id, is_active=True).first()
    if existing:
        flash('Session already active.')
        return redirect(url_for('teacher_dashboard'))
    new_session = AttendanceSession(teacher_id=current_user.teacher.id)
    db.session.add(new_session)
    db.session.commit()
    flash('Attendance session started.')
    return redirect(url_for('teacher_dashboard'))

@app.route('/stop_attendance_session', methods=['POST'])
@login_required
@role_required('teacher')
def stop_attendance_session():
    session = AttendanceSession.query.filter_by(teacher_id=current_user.teacher.id, is_active=True).first()
    if session:
        session.is_active = False
        db.session.commit()
        flash('Session stopped.')
    return redirect(url_for('teacher_dashboard'))

@app.route('/create_assignment', methods=['POST'])
@login_required
@role_required('teacher')
def create_assignment():
    title = request.form.get('title')
    if title:
        new_assignment = Assignment(title=title, teacher_id=current_user.teacher.id)
        db.session.add(new_assignment)
        db.session.commit()
        flash('Assignment created.')
    return redirect(url_for('teacher_dashboard'))

@app.route('/view_submissions/<int:assignment_id>')
@login_required
@role_required('teacher')
def view_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.teacher.id:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    # Since no submissions model, pass empty list
    submissions = []
    return render_template('view_submission.html', assignment=assignment, submissions=submissions)

# --- Student Routes ---
@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/student/attendance')
@login_required
@role_required('student')
def student_attendance_page():
    # Check if there is any active attendance session
    active_session = AttendanceSession.query.filter_by(is_active=True).first()
    if not active_session:
        flash('Attendance session is not active currently. Please wait for your teacher to start the session.', 'warning')
        return redirect(url_for('student_dashboard'))
    return render_template('attendance.html')

@app.route('/api_mark_attendance', methods=['POST'])
@login_required
@role_required('student')
def api_mark_attendance():
    from flask import jsonify
    import base64
    import io
    from PIL import Image
    import numpy as np

    # Check if attendance session is active
    active_session = AttendanceSession.query.filter_by(is_active=True).first()
    if not active_session:
        return jsonify({'status': 'error', 'message': 'Attendance session is not active. Cannot mark attendance.'})

    data = request.get_json()
    image_data = data.get('image', None)
    if not image_data:
        return jsonify({'status': 'error', 'message': 'No image data provided.'})

    # Remove the data URL prefix
    header, encoded = image_data.split(',', 1)
    image_bytes = base64.b64decode(encoded)

    # Load image with PIL
    image = Image.open(io.BytesIO(image_bytes))

    # Here you would call your face recognition logic to identify students
    # For now, we mock the recognized names as the logged in user
    recognized_names = [current_user.username]

    # Mark attendance logic (mock)
    # In real app, you would update AttendanceRecord for recognized students

    return jsonify({'status': 'success', 'names': recognized_names})

@app.route('/student/complaint', methods=['GET', 'POST'])
@login_required
@role_required('student')
def submit_complaint():
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            new_complaint = Complaint(message=message)
            db.session.add(new_complaint)
            db.session.commit()
            flash('Your anonymous suggestion has been submitted.', 'success')
        return redirect(url_for('student_dashboard'))
    return render_template('submit_complaint.html')

# --- Quiz Routes ---
@app.route('/quiz/personalized')
@login_required
def personalized_quiz():
    user_id = current_user.username
    context = request.args.get('context', "General educational content about science and math.")
    quiz = generate_personalized_quiz(user_id, context)
    return render_template('quiz.html', quiz=quiz)

@app.route('/quiz/points')
@login_required
def quiz_points():
    # Mock team rankings
    team_rankings = ["Team A", "Team B", "Team C"]
    points = assign_weekly_points(team_rankings)
    return render_template('points.html', points=points)

from ml_models.chatbot_v2_web import WebChatbot
from flask import jsonify

chatbot_instance = WebChatbot()

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/chatbot_message', methods=['POST'])
@login_required
def chatbot_message():
    data = request.get_json()
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    bot_response, chat_history = chatbot_instance.get_response(user_message)
    return jsonify({
        'response': bot_response,
        'chat_history': chat_history
    })

import sys

if __name__ == '__main__':
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    app.run(host='0.0.0.0', port=port, debug=True)
