import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime, timedelta

# Make sure you have the ai_services.py file with placeholder functions
# from ai_services import load_prediction_model, get_risk_prediction

# --- 1. App Initialization & Configuration ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+mysqlconnector://root:2580@127.0.0.1/student_platform_db"
app.config['SECRET_KEY'] = "a-very-strong-secret-key-for-this-hackathon"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- 2. Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'teacher', 'student'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    user = db.relationship('User', backref='student', uselist=False)
    attendance = db.relationship('AttendanceRecord', backref='student', lazy='dynamic')

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    user = db.relationship('User', backref='teacher', uselist=False)

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)

class AttendanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    start_time = db.Column(db.DateTime, server_default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)

# --- 3. User Loader & Decorators ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

# --- 4. Main & Authentication Routes ---
@app.route('/')
def home():
    # MODIFICATION: Pass current_user to the home template
    return render_template('home.html', current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # This route is added back to prevent BuildErrors from the login page toggle
    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role')
        # For a real app, you would add full_name and create a student/teacher profile
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(request.form.get('password'))
        new_user = User(username=username, password_hash=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- 5. Dashboard Redirector ---
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin': return redirect(url_for('admin_dashboard'))
    if current_user.role == 'teacher': return redirect(url_for('teacher_dashboard'))
    if current_user.role == 'student': return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

# --- 6. Admin Routes ---
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/add_user', methods=['POST'])
@login_required
@role_required('admin')
def add_user():
    # This function is called by the form in the admin dashboard
    # (Your full add_user logic here)
    flash('User added successfully (logic to be built).')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/complaints')
@login_required
@role_required('admin')
def view_complaints():
    complaints = Complaint.query.all()
    return render_template('complaints.html', complaints=complaints)

# --- 7. Teacher Routes ---
@app.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    active_session = AttendanceSession.query.filter_by(teacher_id=current_user.teacher.id, is_active=True).first()
    return render_template('teacher_dashboard.html', active_session=active_session)

# (Add other teacher routes like start/stop session here)

# --- 8. Student Routes ---
@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/student/attendance')
@login_required
@role_required('student')
def student_attendance_page():
    # This is the missing function that caused the error
    return render_template('attendance.html')

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


# --- 9. Run Application ---
if __name__ == '__main__':
    with app.app_context():
        pass
    app.run(host='0.0.0.0', port=5000, debug=True)