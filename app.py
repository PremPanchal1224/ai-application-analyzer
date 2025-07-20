from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import uuid
import mimetypes
import json
from datetime import datetime
from document_processor import DocumentAnalyzer
from ai_recommender import AIInsightGenerator
from admin_manager import AdminManager, NotificationManager
from email_manager import NotificationService, EmailManager
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

# Initialize notification service
notification_service = NotificationService()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database setup
def init_db():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Existing users table (keep as is)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Enhanced applications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            date_of_birth DATE,
            nationality TEXT,
            target_university TEXT,
            course TEXT,
            academic_level TEXT,
            gpa REAL,
            gre_score INTEGER,
            toefl_score INTEGER,
            ielts_score REAL,
            work_experience TEXT,
            statement_of_purpose TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications (id)
        )
    ''')
    
    # Analysis results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            result_data TEXT,
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications (id)
        )
    ''')
    
    # Admin actions log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER,
            admin_user_id INTEGER,
            action TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications (id),
            FOREIGN KEY (admin_user_id) REFERENCES users (id)
        )
    ''')
    
    # System notifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # System settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, role FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'student')
        
        # Check if user exists
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            flash('Username or email already exists!')
            conn.close()
            return render_template('register.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                      (username, email, password_hash, role))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Send welcome email in background
        def send_welcome_async():
            notification_service.notify_new_registration(user_id)
        
        thread = threading.Thread(target=send_welcome_async)
        thread.daemon = True
        thread.start()
        
        flash('Registration successful! Please check your email and then log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, password_hash, role FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[3], password):
            user = User(user_data[0], user_data[1], user_data[2], user_data[4])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        # Get user's application count
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM applications WHERE user_id = ?', (current_user.id,))
        app_count = cursor.fetchone()[0]
        conn.close()
        
        return render_template('student_dashboard.html', app_count=app_count)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    # Get all applications
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.id, a.full_name, a.email, a.target_university, 
               a.course, a.status, a.created_at, u.username
        FROM applications a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
    ''')
    applications = cursor.fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', applications=applications)

@app.route('/application/new')
@login_required
def new_application():
    if current_user.role != 'student':
        flash('Only students can create applications!')
        return redirect(url_for('dashboard'))
    return render_template('new_application.html')

@app.route('/application/submit', methods=['POST'])
@login_required
def submit_application():
    if current_user.role != 'student':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    try:
        # Get form data
        form_data = {
            'full_name': request.form['full_name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'date_of_birth': request.form['date_of_birth'],
            'nationality': request.form['nationality'],
            'target_university': request.form['target_university'],
            'course': request.form['course'],
            'academic_level': request.form['academic_level'],
            'gpa': float(request.form['gpa']) if request.form['gpa'] else None,
            'gre_score': int(request.form['gre_score']) if request.form['gre_score'] else None,
            'toefl_score': int(request.form['toefl_score']) if request.form['toefl_score'] else None,
            'ielts_score': float(request.form['ielts_score']) if request.form['ielts_score'] else None,
            'work_experience': request.form['work_experience'],
            'statement_of_purpose': request.form['statement_of_purpose']
        }
        
        # Insert application into database
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO applications (
                user_id, full_name, email, phone, date_of_birth, nationality,
                target_university, course, academic_level, gpa, gre_score,
                toefl_score, ielts_score, work_experience, statement_of_purpose
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_user.id, form_data['full_name'], form_data['email'],
            form_data['phone'], form_data['date_of_birth'], form_data['nationality'],
            form_data['target_university'], form_data['course'], form_data['academic_level'],
            form_data['gpa'], form_data['gre_score'], form_data['toefl_score'],
            form_data['ielts_score'], form_data['work_experience'], form_data['statement_of_purpose']
        ))
        
        application_id = cursor.lastrowid
        
        # Handle file uploads
        uploaded_files = []
        document_types = ['transcript', 'sop', 'resume', 'passport', 'test_scores', 'recommendation_letters']
        
        for doc_type in document_types:
            files = request.files.getlist(f'{doc_type}[]')
            for file in files:
                if file and file.filename != '' and allowed_file(file.filename):
                    # Generate unique filename
                    original_filename = secure_filename(file.filename)
                    file_extension = original_filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4()}.{file_extension}"
                    
                    # Create subdirectory for this application
                    app_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(application_id))
                    os.makedirs(app_upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(app_upload_dir, unique_filename)
                    file.save(file_path)
                    
                    # Get file info
                    file_size = os.path.getsize(file_path)
                    mime_type = mimetypes.guess_type(file_path)[0]
                    
                    # Save document record
                    cursor.execute('''
                        INSERT INTO documents (
                            application_id, document_type, original_filename,
                            stored_filename, file_path, file_size, mime_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        application_id, doc_type, original_filename,
                        unique_filename, file_path, file_size, mime_type
                    ))
                    
                    uploaded_files.append({'type': doc_type, 'filename': original_filename})
        
        conn.commit()
        conn.close()
        
        flash(f'Application submitted successfully! Uploaded {len(uploaded_files)} documents.')
        return redirect(url_for('view_applications'))
        
    except Exception as e:
        flash(f'Error submitting application: {str(e)}')
        return redirect(url_for('new_application'))

@app.route('/applications')
@login_required
def view_applications():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    if current_user.role == 'student':
        # Show only user's applications
        cursor.execute('''
            SELECT id, full_name, target_university, course, status, created_at
            FROM applications 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (current_user.id,))
    else:
        # Show all applications for admin
        cursor.execute('''
            SELECT a.id, a.full_name, a.target_university, a.course, a.status, a.created_at, u.username
            FROM applications a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
        ''')
    
    applications = cursor.fetchall()
    conn.close()
    
    return render_template('view_applications.html', applications=applications)

@app.route('/application/<int:app_id>')
@login_required
def view_application_details(app_id):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Get application details
    if current_user.role == 'student':
        cursor.execute('''
            SELECT * FROM applications 
            WHERE id = ? AND user_id = ?
        ''', (app_id, current_user.id))
    else:
        cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
    
    application = cursor.fetchone()
    
    if not application:
        flash('Application not found!')
        return redirect(url_for('view_applications'))
    
    # Get associated documents
    cursor.execute('''
        SELECT document_type, original_filename, file_size, uploaded_at
        FROM documents 
        WHERE application_id = ?
        ORDER BY document_type, uploaded_at
    ''', (app_id,))
    documents = cursor.fetchall()
    
    conn.close()
    
    return render_template('application_details.html', application=application, documents=documents)

@app.route('/application/<int:app_id>/analyze')
@login_required
def analyze_application(app_id):
    """Trigger document analysis for an application"""
    if current_user.role not in ['admin', 'student']:
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Get application data
    if current_user.role == 'student':
        cursor.execute('SELECT * FROM applications WHERE id = ? AND user_id = ?', (app_id, current_user.id))
    else:
        cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
    
    application = cursor.fetchone()
    if not application:
        flash('Application not found!')
        return redirect(url_for('view_applications'))
    
    # Get documents
    cursor.execute('''
        SELECT document_type, original_filename, stored_filename, file_path, mime_type
        FROM documents WHERE application_id = ?
    ''', (app_id,))
    documents = cursor.fetchall()
    
    if not documents:
        flash('No documents found to analyze!')
        return redirect(url_for('view_application_details', app_id=app_id))
    
    try:
        # Convert application tuple to dict for easier handling
        app_columns = ['id', 'user_id', 'full_name', 'email', 'phone', 'date_of_birth', 
                      'nationality', 'target_university', 'course', 'academic_level', 
                      'gpa', 'gre_score', 'toefl_score', 'ielts_score', 'work_experience', 
                      'statement_of_purpose', 'status', 'created_at', 'updated_at']
        
        form_data = dict(zip(app_columns, application))
        
        # Convert documents to list of dicts
        doc_list = []
        for doc in documents:
            doc_dict = {
                'document_type': doc[0],
                'original_filename': doc[1],
                'stored_filename': doc[2],
                'file_path': doc[3],
                'mime_type': doc[4]
            }
            doc_list.append(doc_dict)
        
        # Initialize analyzer and process documents
        analyzer = DocumentAnalyzer()
        analysis_results = analyzer.analyze_application_documents(app_id, doc_list, form_data)
        
        # Store analysis results in database
        cursor.execute('''
            INSERT INTO analysis_results (application_id, analysis_type, result_data, confidence_score)
            VALUES (?, ?, ?, ?)
        ''', (
            app_id,
            'document_verification',
            json.dumps(analysis_results),
            analysis_results['summary']['overall_confidence']
        ))
        
        conn.commit()
        flash(f'Analysis completed! Confidence Score: {analysis_results["summary"]["overall_confidence"]:.1f}%')
        
    except Exception as e:
        flash(f'Error during analysis: {str(e)}')
        print(f"Analysis error: {e}")  # For debugging
        
    finally:
        conn.close()
    
    return redirect(url_for('view_analysis_results', app_id=app_id))

@app.route('/application/<int:app_id>/analysis')
@login_required
def view_analysis_results(app_id):
    """View analysis results for an application"""
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Check access permissions
    if current_user.role == 'student':
        cursor.execute('SELECT id FROM applications WHERE id = ? AND user_id = ?', (app_id, current_user.id))
    else:
        cursor.execute('SELECT id FROM applications WHERE id = ?', (app_id,))
    
    if not cursor.fetchone():
        flash('Application not found!')
        return redirect(url_for('view_applications'))
    
    # Get analysis results
    cursor.execute('''
        SELECT result_data, confidence_score, created_at 
        FROM analysis_results 
        WHERE application_id = ? AND analysis_type = ?
        ORDER BY created_at DESC LIMIT 1
    ''', (app_id, 'document_verification'))
    
    analysis_row = cursor.fetchone()
    conn.close()
    
    if not analysis_row:
        flash('No analysis results found. Please run analysis first.')
        return redirect(url_for('view_application_details', app_id=app_id))
    
    try:
        analysis_results = json.loads(analysis_row[0])
        confidence_score = analysis_row[1]
        analysis_date = analysis_row[2]
        
        return render_template('analysis_results.html', 
                             analysis=analysis_results,
                             confidence_score=confidence_score,
                             analysis_date=analysis_date,
                             app_id=app_id)
        
    except Exception as e:
        flash(f'Error loading analysis results: {str(e)}')
        return redirect(url_for('view_application_details', app_id=app_id))

@app.route('/application/<int:app_id>/ai-analysis')
@login_required
def generate_ai_analysis(app_id):
    """Generate AI-powered analysis and recommendations"""
    if current_user.role not in ['admin', 'student']:
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Get application data
    if current_user.role == 'student':
        cursor.execute('SELECT * FROM applications WHERE id = ? AND user_id = ?', (app_id, current_user.id))
    else:
        cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
    
    application = cursor.fetchone()
    if not application:
        flash('Application not found!')
        return redirect(url_for('view_applications'))
    
    try:
        # Convert application to dict
        app_columns = ['id', 'user_id', 'full_name', 'email', 'phone', 'date_of_birth', 
                      'nationality', 'target_university', 'course', 'academic_level', 
                      'gpa', 'gre_score', 'toefl_score', 'ielts_score', 'work_experience', 
                      'statement_of_purpose', 'status', 'created_at', 'updated_at']
        
        application_data = dict(zip(app_columns, application))
        
        # Get existing document analysis if available
        cursor.execute('''
            SELECT result_data FROM analysis_results 
            WHERE application_id = ? AND analysis_type = ?
            ORDER BY created_at DESC LIMIT 1
        ''', (app_id, 'document_verification'))
        
        doc_analysis = None
        doc_result = cursor.fetchone()
        if doc_result:
            doc_analysis = json.loads(doc_result[0])
        
        # Generate AI insights
        ai_generator = AIInsightGenerator()
        ai_insights = ai_generator.generate_application_insights(application_data, doc_analysis)
        
        # Store AI analysis results
        cursor.execute('''
            INSERT INTO analysis_results (application_id, analysis_type, result_data, confidence_score)
            VALUES (?, ?, ?, ?)
        ''', (
            app_id,
            'ai_recommendations',
            json.dumps(ai_insights),
            ai_insights['overall_assessment']['overall_score']
        ))
        
        conn.commit()
        
        flash(f'AI Analysis completed! Overall Score: {ai_insights["overall_assessment"]["overall_score"]}/100')
        
    except Exception as e:
        flash(f'Error during AI analysis: {str(e)}')
        print(f"AI Analysis error: {e}")  # For debugging
        
    finally:
        conn.close()
    
    return redirect(url_for('view_ai_recommendations', app_id=app_id))

@app.route('/application/<int:app_id>/recommendations')
@login_required
def view_ai_recommendations(app_id):
    """View AI recommendations for an application"""
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Check access permissions
    if current_user.role == 'student':
        cursor.execute('SELECT id FROM applications WHERE id = ? AND user_id = ?', (app_id, current_user.id))
    else:
        cursor.execute('SELECT id FROM applications WHERE id = ?', (app_id,))
    
    if not cursor.fetchone():
        flash('Application not found!')
        return redirect(url_for('view_applications'))
    
    # Get AI analysis results
    cursor.execute('''
        SELECT result_data, confidence_score, created_at 
        FROM analysis_results 
        WHERE application_id = ? AND analysis_type = ?
        ORDER BY created_at DESC LIMIT 1
    ''', (app_id, 'ai_recommendations'))
    
    ai_result = cursor.fetchone()
    conn.close()
    
    if not ai_result:
        flash('No AI analysis found. Please generate AI recommendations first.')
        return redirect(url_for('view_application_details', app_id=app_id))
    
    try:
        ai_recommendations = json.loads(ai_result[0])
        confidence_score = ai_result[1]
        analysis_date = ai_result[2]
        
        return render_template('ai_recommendations.html',
                             recommendations=ai_recommendations,
                             confidence_score=confidence_score,
                             analysis_date=analysis_date,
                             app_id=app_id)
        
    except Exception as e:
        flash(f'Error loading AI recommendations: {str(e)}')
        return redirect(url_for('view_application_details', app_id=app_id))

@app.route('/dashboard/insights')
@login_required
def dashboard_insights():
    """Show AI insights dashboard for students"""
    if current_user.role != 'student':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Get user's applications with AI analysis
    cursor.execute('''
        SELECT a.id, a.full_name, a.target_university, a.course, a.status,
               ar.confidence_score, ar.created_at
        FROM applications a
        LEFT JOIN analysis_results ar ON a.id = ar.application_id 
        AND ar.analysis_type = 'ai_recommendations'
        WHERE a.user_id = ?
        ORDER BY a.created_at DESC
    ''', (current_user.id,))
    
    applications = cursor.fetchall()
    conn.close()
    
    return render_template('insights_dashboard.html', applications=applications)

# Enhanced Admin Routes
@app.route('/admin/enhanced')
@login_required
def enhanced_admin_dashboard():
    """Enhanced admin dashboard with detailed statistics"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    admin_manager = AdminManager()
    
    # Get dashboard statistics
    stats = admin_manager.get_dashboard_stats()
    
    # Get recent applications
    recent_apps = admin_manager.get_detailed_applications(limit=10)
    
    # Get analytics report
    analytics = admin_manager.generate_analytics_report(days=30)
    
    return render_template('enhanced_admin_dashboard.html', 
                         stats=stats,
                         recent_apps=recent_apps,
                         analytics=analytics)

@app.route('/admin/applications/manage')
@login_required
def manage_applications():
    """Application management interface"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    admin_manager = AdminManager()
    
    # Get filter parameters
    status_filter = request.args.get('status')
    
    # Get applications
    applications = admin_manager.get_detailed_applications(status_filter)
    
    return render_template('manage_applications.html', 
                         applications=applications,
                         status_filter=status_filter)

@app.route('/admin/application/<int:app_id>/update-status', methods=['POST'])
@login_required
def update_application_status(app_id):
    """Update application status with notifications"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    status = request.form['status']
    notes = request.form.get('notes', '')
    
    admin_manager = AdminManager()
    
    if admin_manager.update_application_status(app_id, status, notes):
        # Send notifications
        def send_notification_async():
            notification_service.notify_application_status_change(app_id, status, notes)
        
        # Send notification in background thread
        thread = threading.Thread(target=send_notification_async)
        thread.daemon = True
        thread.start()
        
        # Create in-app notification
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, full_name FROM applications WHERE id = ?', (app_id,))
        app_data = cursor.fetchone()
        conn.close()
        
        if app_data:
            notification_manager = NotificationManager()
            notification_manager.create_notification(
                app_data[0],
                f'Application Status Updated',
                f'Your application status has been updated to: {status.title()}. {notes if notes else ""}',
                'status_update'
            )
        
        flash(f'Application status updated to {status.title()} and notification sent.')
    else:
        flash('Error updating application status')
    
    return redirect(url_for('manage_applications'))

@app.route('/admin/bulk-update', methods=['POST'])
@login_required
def bulk_update_applications():
    """Bulk update multiple applications"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    app_ids = request.form.getlist('application_ids')
    status = request.form['bulk_status']
    notes = request.form.get('bulk_notes', '')
    
    if not app_ids:
        flash('No applications selected!')
        return redirect(url_for('manage_applications'))
    
    admin_manager = AdminManager()
    app_ids = [int(id) for id in app_ids]
    
    result = admin_manager.bulk_update_applications(app_ids, status, notes)
    
    # Send bulk notifications
    def send_bulk_notifications_async():
        for app_id in app_ids:
            notification_service.notify_application_status_change(app_id, status, notes)
    
    thread = threading.Thread(target=send_bulk_notifications_async)
    thread.daemon = True
    thread.start()
    
    flash(f'Bulk update completed: {result["success_count"]} successful, {result["failed_count"]} failed. Notifications sent.')
    
    return redirect(url_for('manage_applications'))

@app.route('/admin/users/manage')
@login_required
def manage_users():
    """User management interface"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    admin_manager = AdminManager()
    users = admin_manager.get_user_management_data()
    
    return render_template('manage_users.html', users=users)

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Detailed analytics page"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    admin_manager = AdminManager()
    
    # Get different time period reports
    days = int(request.args.get('days', 30))
    analytics = admin_manager.generate_analytics_report(days)
    
    return render_template('admin_analytics.html', 
                         analytics=analytics, 
                         selected_days=days)

@app.route('/admin/export/applications')
@login_required
def export_applications():
    """Export applications to CSV"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    status_filter = request.args.get('status')
    admin_manager = AdminManager()
    
    csv_data = admin_manager.export_applications_csv(status_filter)
    
    filename = f"applications_{status_filter or 'all'}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

# Notification Routes
@app.route('/notifications')
@login_required
def user_notifications():
    """User notifications page"""
    notification_manager = NotificationManager()
    notifications = notification_manager.get_user_notifications(current_user.id)
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/notification/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Mark notification as read"""
    notification_manager = NotificationManager()
    notification_manager.mark_as_read(notif_id)
    
    return redirect(url_for('user_notifications'))

@app.route('/admin/notifications/send', methods=['GET', 'POST'])
@login_required
def send_bulk_notification():
    """Send bulk notifications to users"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        message = request.form['message']
        recipient_type = request.form['recipient_type']  # 'all', 'students', 'admins'
        send_email = 'send_email' in request.form
        
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Get recipient emails based on type
        if recipient_type == 'all':
            cursor.execute('SELECT id, email, username FROM users')
        else:
            cursor.execute('SELECT id, email, username FROM users WHERE role = ?', (recipient_type.rstrip('s'),))
        
        recipients = cursor.fetchall()
        
        # Create in-app notifications
        notification_manager = NotificationManager()
        sent_count = 0
        
        for user_id, email, username in recipients:
            # Create in-app notification
            notification_manager.create_notification(user_id, title, message, 'admin')
            
            # Send email if requested
            if send_email:
                email_manager = EmailManager()
                email_sent = email_manager.send_email(
                    email,
                    title,
                    f"Dear {username},\n\n{message}\n\nBest regards,\nAI Application Analyzer Team"
                )
                if email_sent:
                    sent_count += 1
        
        conn.close()
        
        flash(f'Notification sent to {len(recipients)} users. {sent_count} emails sent.')
        return redirect(url_for('enhanced_admin_dashboard'))
    
    return render_template('send_notification.html')

@app.route('/admin/notifications/settings')
@login_required
def notification_settings():
    """Admin notification settings"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    return render_template('notification_settings.html')

@app.route('/test-email')
@login_required
def test_email():
    """Test email functionality (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    email_manager = EmailManager()
    test_sent = email_manager.send_email(
        current_user.email,
        "Test Email from AI Application Analyzer",
        "This is a test email to verify the email system is working correctly."
    )
    
    if test_sent:
        flash('Test email sent successfully!')
    else:
        flash('Failed to send test email. Please check email configuration.')
    
    return redirect(url_for('enhanced_admin_dashboard'))

# Settings update routes (placeholders for future implementation)
@app.route('/admin/settings/email', methods=['POST'])
@login_required
def update_email_settings():
    """Update email settings"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    flash('Email settings updated successfully!')
    return redirect(url_for('notification_settings'))

@app.route('/admin/settings/auto-notifications', methods=['POST'])
@login_required
def update_auto_notifications():
    """Update automatic notification settings"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    flash('Auto-notification settings updated!')
    return redirect(url_for('notification_settings'))

@app.route('/admin/settings/whatsapp', methods=['POST'])
@login_required
def update_whatsapp_settings():
    """Update WhatsApp settings"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    flash('WhatsApp settings updated!')
    return redirect(url_for('notification_settings'))

# User management routes (placeholders)
@app.route('/admin/user/create', methods=['POST'])
@login_required
def create_user():
    """Create new user"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    flash('User created successfully!')
    return redirect(url_for('manage_users'))

@app.route('/admin/user/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    """Update user details"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    flash('User updated successfully!')
    return redirect(url_for('manage_users'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    flash('User deleted successfully!')
    return redirect(url_for('manage_users'))

@app.route('/application/<int:app_id>/edit')
@login_required
def edit_application(app_id):
    """Edit application form"""
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Get application details
    if current_user.role == 'student':
        cursor.execute('''
            SELECT * FROM applications 
            WHERE id = ? AND user_id = ?
        ''', (app_id, current_user.id))
    else:
        cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
    
    application = cursor.fetchone()
    
    if not application:
        flash('Application not found!')
        return redirect(url_for('view_applications'))
    
    # Check if application can be edited (only pending applications)
    if application[16] != 'pending':  # status column
        flash('Only pending applications can be edited!')
        return redirect(url_for('view_application_details', app_id=app_id))
    
    # Get existing documents
    cursor.execute('''
        SELECT id, document_type, original_filename, file_size, uploaded_at
        FROM documents 
        WHERE application_id = ?
        ORDER BY document_type, uploaded_at
    ''', (app_id,))
    documents = cursor.fetchall()
    
    conn.close()
    
    # Convert application tuple to dict for easier template handling
    app_columns = ['id', 'user_id', 'full_name', 'email', 'phone', 'date_of_birth', 
                  'nationality', 'target_university', 'course', 'academic_level', 
                  'gpa', 'gre_score', 'toefl_score', 'ielts_score', 'work_experience', 
                  'statement_of_purpose', 'status', 'created_at', 'updated_at']
    
    application_dict = dict(zip(app_columns, application))
    
    return render_template('edit_application.html', 
                         application=application_dict, 
                         documents=documents, 
                         app_id=app_id)

@app.route('/application/<int:app_id>/update', methods=['POST'])
@login_required
def update_application(app_id):
    """Update application with new information"""
    if current_user.role != 'student':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Verify ownership and pending status
    cursor.execute('''
        SELECT status FROM applications 
        WHERE id = ? AND user_id = ?
    ''', (app_id, current_user.id))
    
    result = cursor.fetchone()
    if not result:
        flash('Application not found!')
        return redirect(url_for('view_applications'))
    
    if result[0] != 'pending':
        flash('Only pending applications can be edited!')
        return redirect(url_for('view_application_details', app_id=app_id))
    
    try:
        # Get form data
        form_data = {
            'full_name': request.form['full_name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'date_of_birth': request.form['date_of_birth'],
            'nationality': request.form['nationality'],
            'target_university': request.form['target_university'],
            'course': request.form['course'],
            'academic_level': request.form['academic_level'],
            'gpa': float(request.form['gpa']) if request.form['gpa'] else None,
            'gre_score': int(request.form['gre_score']) if request.form['gre_score'] else None,
            'toefl_score': int(request.form['toefl_score']) if request.form['toefl_score'] else None,
            'ielts_score': float(request.form['ielts_score']) if request.form['ielts_score'] else None,
            'work_experience': request.form['work_experience'],
            'statement_of_purpose': request.form['statement_of_purpose']
        }
        
        # Update application in database
        cursor.execute('''
            UPDATE applications SET
                full_name = ?, email = ?, phone = ?, date_of_birth = ?, nationality = ?,
                target_university = ?, course = ?, academic_level = ?, gpa = ?, gre_score = ?,
                toefl_score = ?, ielts_score = ?, work_experience = ?, statement_of_purpose = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (
            form_data['full_name'], form_data['email'], form_data['phone'], 
            form_data['date_of_birth'], form_data['nationality'], form_data['target_university'], 
            form_data['course'], form_data['academic_level'], form_data['gpa'], 
            form_data['gre_score'], form_data['toefl_score'], form_data['ielts_score'], 
            form_data['work_experience'], form_data['statement_of_purpose'], 
            app_id, current_user.id
        ))
        
        # Handle new file uploads
        uploaded_files = []
        document_types = ['transcript', 'sop', 'resume', 'passport', 'test_scores', 'recommendation_letters']
        
        for doc_type in document_types:
            files = request.files.getlist(f'{doc_type}[]')
            for file in files:
                if file and file.filename != '' and allowed_file(file.filename):
                    # Generate unique filename
                    original_filename = secure_filename(file.filename)
                    file_extension = original_filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4()}.{file_extension}"
                    
                    # Create subdirectory for this application (if it doesn't exist)
                    app_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(app_id))
                    os.makedirs(app_upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(app_upload_dir, unique_filename)
                    file.save(file_path)
                    
                    # Get file info
                    file_size = os.path.getsize(file_path)
                    mime_type = mimetypes.guess_type(file_path)[0]
                    
                    # Save document record
                    cursor.execute('''
                        INSERT INTO documents (
                            application_id, document_type, original_filename,
                            stored_filename, file_path, file_size, mime_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        app_id, doc_type, original_filename,
                        unique_filename, file_path, file_size, mime_type
                    ))
                    
                    uploaded_files.append({'type': doc_type, 'filename': original_filename})
        
        conn.commit()
        conn.close()
        
        flash(f'Application updated successfully! {len(uploaded_files)} new documents added.')
        return redirect(url_for('view_application_details', app_id=app_id))
        
    except Exception as e:
        flash(f'Error updating application: {str(e)}')
        return redirect(url_for('edit_application', app_id=app_id))

@app.route('/document/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    """Delete a specific document"""
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Get document info and verify ownership
    cursor.execute('''
        SELECT d.application_id, d.file_path, a.user_id, a.status
        FROM documents d
        JOIN applications a ON d.application_id = a.id
        WHERE d.id = ?
    ''', (doc_id,))
    
    result = cursor.fetchone()
    
    if not result:
        flash('Document not found!')
        return redirect(url_for('view_applications'))
    
    app_id, file_path, user_id, status = result
    
    # Check permissions
    if current_user.role == 'student' and user_id != current_user.id:
        flash('Access denied!')
        return redirect(url_for('view_applications'))
    
    if status != 'pending':
        flash('Cannot delete documents from non-pending applications!')
        return redirect(url_for('view_application_details', app_id=app_id))
    
    try:
        # Delete file from filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete record from database
        cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        conn.commit()
        
        flash('Document deleted successfully!')
        
    except Exception as e:
        flash(f'Error deleting document: {str(e)}')
    
    finally:
        conn.close()
    
    return redirect(url_for('edit_application', app_id=app_id))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
