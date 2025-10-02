import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from PIL import Image
from resizeimage import resizeimage
import cv2
import numpy as np
import pyzbar.pyzbar as pyzbar

app = Flask(__name__)
app.secret_key = 'your-secret-key-123'  # Change this for production
app.config['UPLOAD_FOLDER'] = 'Student_QR'
DATABASE = 'database.db'
SCANNED_FILE = 'scanned_qr_codes.txt'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database functions
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                is_admin BOOLEAN DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                class TEXT NOT NULL,
                phone TEXT NOT NULL,
                alt_phone TEXT,
                qr_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        # Create admin user if not exists
        cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, ?)',
                         ('admin', generate_password_hash('admin123'), 'admin@school.edu', 1))
        conn.commit()

def log_scan(data):
    with open(SCANNED_FILE, 'a') as f:
        f.write(f"{datetime.now().isoformat()}|{data}\n")

# Decorators
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        
        db = get_db()
        user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        db.close()
        
        if not user or not user['is_admin']:
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        email = request.form['email']
        
        try:
            db = get_db()
            db.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', 
                      (username, password, email))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists!', 'danger')
        finally:
            db.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            flash('Login successful!', 'success')
            return redirect(request.args.get('next') or url_for('index'))
        else:
            flash('Invalid username or password!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/generator')
@login_required
def generator():
    return render_template('generator.html')

@app.route('/generate_qr', methods=['POST'])
@login_required
def generate_qr():
    data = request.form
@app.route('/debug')
@login_required
def debug():
    db = get_db()
    
    # Check students table
    students = db.execute('SELECT * FROM students').fetchall()
    print("Students:", [dict(student) for student in students])
    
    # Check scans table
    scans = db.execute('SELECT * FROM scans').fetchall()
    print("Scans:", [dict(scan) for scan in scans])
    
    # Check users table
    users = db.execute('SELECT * FROM users').fetchall()
    print("Users:", [dict(user) for user in users])
    
    db.close()
    
    return jsonify({
        'students_count': len(students),
        'scans_count': len(scans),
        'users_count': len(users)
    })
@app.route('/scanned_qr_codes')
@login_required
def scanned_qr_codes():
    db = get_db()
    scans = db.execute('''
        SELECT scans.*, students.name, students.department, students.class 
        FROM scans 
        LEFT JOIN students ON scans.student_id = students.student_id
        ORDER BY scan_time DESC
    ''').fetchall()
    db.close()
    
    return render_template('scanned_qr_codes.html', scans=scans)
    
    
    # Validate required fields
    required_fields = ['student_id', 'student_name', 'department', 'class', 'phone']
    if not all(data.get(field) for field in required_fields):
        return {'status': 'error', 'message': 'All required fields must be filled'}, 400
    
    # Create QR data string
    qr_data = f"Student ID: {data['student_id']}\n"
    qr_data += f"Name: {data['student_name']}\n"
    qr_data += f"Department: {data['department']}\n"
    qr_data += f"Class: {data['class']}\n"
    qr_data += f"Phone: {data['phone']}\n"
    qr_data += f"Alt Phone: {data.get('alt_phone', '')}"
    
    # Generate QR code
    filename = f"std_{data['student_id']}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        qr = qrcode.make(qr_data)
        qr = resizeimage.resize_cover(qr, [300, 300])
        qr.save(filepath)
        
        # Save to database
        db = get_db()
        db.execute('''
            INSERT INTO students (student_id, name, department, class, phone, alt_phone, qr_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['student_id'],
            data['student_name'],
            data['department'],
            data['class'],
            data['phone'],
            data.get('alt_phone', ''),
            filename
        ))
        db.commit()
        db.close()
        
        return {
            'status': 'success',
            'qr_url': url_for('get_qr', filename=filename),
            'student_id': data['student_id']
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/qr_codes/<filename>')
def get_qr(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/scanner')
@login_required
def scanner():
    return render_template('scanner.html')

@app.route('/scan_qr', methods=['POST'])
@login_required
def scan_qr():
    if 'file' not in request.files:
        return {'status': 'error', 'message': 'No file uploaded'}, 400
    
    file = request.files['file']
    if file.filename == '':
        return {'status': 'error', 'message': 'No selected file'}, 400
    
    try:
        # Read image file
        img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
        
        # Decode QR code
        decoded_objects = pyzbar.decode(img)
        if not decoded_objects:
            return {'status': 'error', 'message': 'No QR code detected'}, 400
        
        # Process decoded data
        data = decoded_objects[0].data.decode('utf-8')
        student_id = data.split('\n')[0].split(': ')[1]  # Extract student ID
        
        # Log the scan
        log_scan(data)
        db = get_db()
        db.execute('INSERT INTO scans (student_id) VALUES (?)', (student_id,))
        db.commit()
        
        # Get student details
        student = db.execute('''
            SELECT * FROM students WHERE student_id = ?
        ''', (student_id,)).fetchone()
        db.close()
        
        if not student:
            return {'status': 'error', 'message': 'Student not found'}, 404
        
        return {
            'status': 'success',
            'data': data,
            'student': dict(student)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/saved_qr_codes')
@login_required
def saved_qr_codes():
    db = get_db()
    students = db.execute('SELECT * FROM students ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('saved_qr_codes.html', students=students)

@app.route('/scan_history')
@login_required
def scan_history():
    scans = []
    if os.path.exists(SCANNED_FILE):
        with open(SCANNED_FILE, 'r') as f:
            scans = [line.strip().split('|', 1) for line in f.readlines()]
    
    db = get_db()
    db_scans = db.execute('''
        SELECT scans.*, students.name 
        FROM scans 
        JOIN students ON scans.student_id = students.student_id
        ORDER BY scan_time DESC
    ''').fetchall()
    db.close()
    
    return render_template('scan_history.html', 
                         file_scans=scans,
                         db_scans=db_scans)

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    student_count = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    scan_count = db.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    recent_scans = db.execute('''
        SELECT scans.*, students.name 
        FROM scans 
        JOIN students ON scans.student_id = students.student_id
        ORDER BY scan_time DESC LIMIT 5
    ''').fetchall()
    recent_students = db.execute('''
        SELECT * FROM students ORDER BY created_at DESC LIMIT 5
    ''').fetchall()
    db.close()
    
    return render_template('admin_dashboard.html', 
                         student_count=student_count,
                         scan_count=scan_count,
                         user_count=user_count,
                         recent_scans=recent_scans,
                         recent_students=recent_students)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    student_count = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    scan_count = db.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    db.close()
    return render_template('dashboard.html', student_count=student_count, scan_count=scan_count)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)



# import os
# import sqlite3
# from datetime import datetime
# from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session, flash, jsonify
# from werkzeug.security import generate_password_hash, check_password_hash
# import qrcode
# from PIL import Image
# import cv2
# import numpy as np
# import pyzbar.pyzbar as pyzbar
# from functools import wraps

# app = Flask(__name__)
# app.secret_key = 'your-secret-key-123-change-in-production'
# app.config['UPLOAD_FOLDER'] = 'static/Student_QR'
# DATABASE = 'database.db'

# # Ensure upload directory exists
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# # Database functions
# def get_db():
#     db = sqlite3.connect(DATABASE)
#     db.row_factory = sqlite3.Row
#     return db

# def init_db():
#     with sqlite3.connect(DATABASE) as conn:
#         cursor = conn.cursor()
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT UNIQUE NOT NULL,
#                 password TEXT NOT NULL,
#                 email TEXT UNIQUE NOT NULL,
#                 is_admin BOOLEAN DEFAULT 0,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         ''')
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS students (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 student_id TEXT UNIQUE NOT NULL,
#                 name TEXT NOT NULL,
#                 department TEXT NOT NULL,
#                 class TEXT NOT NULL,
#                 phone TEXT NOT NULL,
#                 alt_phone TEXT,
#                 qr_code TEXT,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         ''')
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS scans (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 student_id TEXT NOT NULL,
#                 student_name TEXT NOT NULL,
#                 department TEXT NOT NULL,
#                 scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (student_id) REFERENCES students (student_id)
#             )
#         ''')
        
#         # Create admin user if not exists
#         cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
#         if not cursor.fetchone():
#             cursor.execute('INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, ?)',
#                          ('admin', generate_password_hash('admin123'), 'admin@school.edu', 1))
#         conn.commit()

# # Decorators
# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session:
#             flash('Please login to access this page.', 'danger')
#             return redirect(url_for('login', next=request.url))
#         return f(*args, **kwargs)
#     return decorated_function

# def admin_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session:
#             flash('Please login to access this page.', 'danger')
#             return redirect(url_for('login', next=request.url))
        
#         db = get_db()
#         user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
#         db.close()
        
#         if not user or not user['is_admin']:
#             flash('Admin access required.', 'danger')
#             return redirect(url_for('index'))
#         return f(*args, **kwargs)
#     return decorated_function

# # Routes
# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         email = request.form['email']
        
#         if len(password) < 6:
#             flash('Password must be at least 6 characters long.', 'danger')
#             return render_template('register.html')
        
#         hashed_password = generate_password_hash(password)
        
#         try:
#             db = get_db()
#             db.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', 
#                       (username, hashed_password, email))
#             db.commit()
#             flash('Registration successful! Please login.', 'success')
#             return redirect(url_for('login'))
#         except sqlite3.IntegrityError:
#             flash('Username or email already exists!', 'danger')
#         finally:
#             db.close()
    
#     return render_template('register.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
        
#         db = get_db()
#         user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
#         db.close()
        
#         if user and check_password_hash(user['password'], password):
#             session['user_id'] = user['id']
#             session['username'] = user['username']
#             session['is_admin'] = bool(user['is_admin'])
#             flash('Login successful!', 'success')
#             return redirect(request.args.get('next') or url_for('dashboard'))
#         else:
#             flash('Invalid username or password!', 'danger')
    
#     return render_template('login.html')

# @app.route('/logout')
# def logout():
#     session.clear()
#     flash('You have been logged out.', 'info')
#     return redirect(url_for('index'))

# @app.route('/dashboard')
# @login_required
# def dashboard():
#     db = get_db()
    
#     # Get counts for dashboard
#     student_count = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
#     scan_count = db.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    
#     # Get recent scans
#     recent_scans = db.execute('''
#         SELECT scans.*, students.name, students.department 
#         FROM scans 
#         JOIN students ON scans.student_id = students.student_id 
#         ORDER BY scan_time DESC LIMIT 5
#     ''').fetchall()
    
#     db.close()
    
#     return render_template('dashboard.html', 
#                          student_count=student_count, 
#                          scan_count=scan_count,
#                          recent_scans=recent_scans)

# @app.route('/generator')
# @login_required
# def generator():
#     return render_template('generator.html')

# @app.route('/generate_qr', methods=['POST'])
# @login_required
# def generate_qr():
#     try:
#         data = request.get_json()
        
#         # Validate required fields
#         required_fields = ['student_id', 'student_name', 'department', 'class', 'phone']
#         for field in required_fields:
#             if not data.get(field):
#                 return jsonify({'status': 'error', 'message': f'{field} is required'}), 400
        
#         # Create QR data string
#         qr_data = f"STUDENT_ID:{data['student_id']}\n"
#         qr_data += f"NAME:{data['student_name']}\n"
#         qr_data += f"DEPARTMENT:{data['department']}\n"
#         qr_data += f"CLASS:{data['class']}\n"
#         qr_data += f"PHONE:{data['phone']}\n"
#         qr_data += f"ALT_PHONE:{data.get('alt_phone', '')}"
        
#         # Generate QR code
#         filename = f"std_{data['student_id']}.png"
#         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
#         qr = qrcode.QRCode(
#             version=1,
#             error_correction=qrcode.constants.ERROR_CORRECT_L,
#             box_size=10,
#             border=4,
#         )
#         qr.add_data(qr_data)
#         qr.make(fit=True)
        
#         img = qr.make_image(fill_color="black", back_color="white")
#         img = img.resize((300, 300), Image.Resampling.LANCZOS)
#         img.save(filepath)
        
#         # Save to database
#         db = get_db()
#         db.execute('''
#             INSERT OR REPLACE INTO students (student_id, name, department, class, phone, alt_phone, qr_code)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         ''', (
#             data['student_id'],
#             data['student_name'],
#             data['department'],
#             data['class'],
#             data['phone'],
#             data.get('alt_phone', ''),
#             filename
#         ))
#         db.commit()
#         db.close()
        
#         return jsonify({
#             'status': 'success',
#             'qr_url': f"/static/Student_QR/{filename}",
#             'student_id': data['student_id'],
#             'message': 'QR Code generated successfully!'
#         })
        
#     except Exception as e:
#         return jsonify({'status': 'error', 'message': str(e)}), 500

# @app.route('/scanner')
# @login_required
# def scanner():
#     return render_template('scanner.html')

# @app.route('/scan_qr', methods=['POST'])
# @login_required
# def scan_qr():
#     try:
#         if 'file' not in request.files:
#             return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        
#         file = request.files['file']
#         if file.filename == '':
#             return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        
#         # Read and process image
#         img_array = np.frombuffer(file.read(), np.uint8)
#         img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
#         if img is None:
#             return jsonify({'status': 'error', 'message': 'Invalid image file'}), 400
        
#         # Decode QR code
#         decoded_objects = pyzbar.decode(img)
#         if not decoded_objects:
#             return jsonify({'status': 'error', 'message': 'No QR code detected'}), 400
        
#         # Process decoded data
#         data = decoded_objects[0].data.decode('utf-8')
#         print("QR Code Data:", data)
        
#         # Parse QR data
#         qr_data = {}
#         for line in data.split('\n'):
#             if ':' in line:
#                 key, value = line.split(':', 1)
#                 qr_data[key.strip()] = value.strip()
        
#         # Extract student ID
#         student_id = qr_data.get('STUDENT_ID')
#         if not student_id:
#             return jsonify({'status': 'error', 'message': 'Student ID not found in QR code'}), 400
        
#         # Save scan to database
#         db = get_db()
        
#         # Get student details
#         student = db.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
        
#         if not student:
#             return jsonify({'status': 'error', 'message': f'Student with ID {student_id} not found in database'}), 404
        
#         print(f"Found student: {student['name']}")
        
#         # Insert scan record
#         db.execute('''
#             INSERT INTO scans (student_id, student_name, department)
#             VALUES (?, ?, ?)
#         ''', (student_id, student['name'], student['department']))
        
#         db.commit()
        
#         # Verify the scan was saved
#         new_scan = db.execute('SELECT * FROM scans WHERE student_id = ? ORDER BY scan_time DESC LIMIT 1', 
#                              (student_id,)).fetchone()
#         db.close()
        
#         print(f"Scan saved with ID: {new_scan['id'] if new_scan else 'Unknown'}")
        
#         return jsonify({
#             'status': 'success',
#             'data': qr_data,
#             'student': {
#                 'student_id': student['student_id'],
#                 'name': student['name'],
#                 'department': student['department'],
#                 'class': student['class'],
#                 'phone': student['phone']
#             },
#             'scan_id': new_scan['id'] if new_scan else None,
#             'message': 'QR Code scanned and saved successfully!'
#         })
        
#     except Exception as e:
#         print(f"Scan error: {str(e)}")
#         return jsonify({'status': 'error', 'message': str(e)}), 500

# @app.route('/saved_qr_codes')
# @login_required
# def saved_qr_codes():
#     db = get_db()
#     students = db.execute('SELECT * FROM students ORDER BY created_at DESC').fetchall()
#     db.close()
#     return render_template('saved_qr_codes.html', students=students)

# @app.route('/scan_history')
# @login_required
# def scan_history():
#     try:
#         db = get_db()
        
#         # Get scan history with student details
#         scans = db.execute('''
#             SELECT 
#                 scans.id,
#                 scans.student_id,
#                 scans.student_name,
#                 scans.department,
#                 scans.scan_time,
#                 students.class,
#                 students.phone
#             FROM scans 
#             LEFT JOIN students ON scans.student_id = students.student_id
#             ORDER BY scans.scan_time DESC
#         ''').fetchall()
        
#         db.close()
        
#         print(f"Found {len(scans)} scans in database")
        
#         return render_template('scan_history.html', scans=scans)
        
#     except Exception as e:
#         print(f"Scan history error: {str(e)}")
#         return render_template('scan_history.html', scans=[])

# @app.route('/scanned_qr_codes')
# @login_required
# def scanned_qr_codes():
#     return redirect(url_for('scan_history'))

# @app.route('/admin/dashboard')
# @admin_required
# def admin_dashboard():
#     db = get_db()
    
#     # Get statistics
#     student_count = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
#     scan_count = db.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
#     user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    
#     # Get recent activity
#     recent_scans = db.execute('''
#         SELECT scans.*, students.name 
#         FROM scans 
#         JOIN students ON scans.student_id = students.student_id
#         ORDER BY scan_time DESC LIMIT 10
#     ''').fetchall()
    
#     recent_students = db.execute('''
#         SELECT * FROM students ORDER BY created_at DESC LIMIT 5
#     ''').fetchall()
    
#     recent_users = db.execute('''
#         SELECT * FROM users ORDER BY created_at DESC LIMIT 5
#     ''').fetchall()
    
#     db.close()
    
#     return render_template('admin_dashboard.html', 
#                          student_count=student_count,
#                          scan_count=scan_count,
#                          user_count=user_count,
#                          recent_scans=recent_scans,
#                          recent_students=recent_students,
#                          recent_users=recent_users)

# @app.route('/about')
# def about():
#     return render_template('about.html')

# @app.route('/contact')
# def contact():
#     return render_template('contact.html')

# # Debug and Test Routes
# @app.route('/debug')
# @login_required
# def debug():
#     db = get_db()
    
#     # Check students table
#     students = db.execute('SELECT * FROM students').fetchall()
#     students_data = [dict(student) for student in students]
    
#     # Check scans table
#     scans = db.execute('SELECT * FROM scans').fetchall()
#     scans_data = [dict(scan) for scan in scans]
    
#     # Check users table
#     users = db.execute('SELECT * FROM users').fetchall()
#     users_data = [dict(user) for user in users]
    
#     db.close()
    
#     return jsonify({
#         'students': students_data,
#         'scans': scans_data,
#         'users': users_data,
#         'students_count': len(students_data),
#         'scans_count': len(scans_data),
#         'users_count': len(users_data)
#     })

# @app.route('/test_generate')
# @login_required
# def test_generate():
#     """Generate a test student and QR code"""
#     db = get_db()
    
#     # Create a test student
#     test_student = {
#         'student_id': 'TEST001',
#         'name': 'Test Student',
#         'department': 'Computer Science',
#         'class': 'CS101',
#         'phone': '1234567890',
#         'alt_phone': ''
#     }
    
#     try:
#         # Generate QR data
#         qr_data = f"STUDENT_ID:{test_student['student_id']}\n"
#         qr_data += f"NAME:{test_student['name']}\n"
#         qr_data += f"DEPARTMENT:{test_student['department']}\n"
#         qr_data += f"CLASS:{test_student['class']}\n"
#         qr_data += f"PHONE:{test_student['phone']}\n"
#         qr_data += f"ALT_PHONE:{test_student['alt_phone']}"
        
#         # Generate QR code
#         filename = f"std_{test_student['student_id']}.png"
#         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
#         qr = qrcode.QRCode(
#             version=1,
#             error_correction=qrcode.constants.ERROR_CORRECT_L,
#             box_size=10,
#             border=4,
#         )
#         qr.add_data(qr_data)
#         qr.make(fit=True)
        
#         img = qr.make_image(fill_color="black", back_color="white")
#         img = img.resize((300, 300), Image.Resampling.LANCZOS)
#         img.save(filepath)
        
#         # Save to database
#         db.execute('''
#             INSERT OR REPLACE INTO students (student_id, name, department, class, phone, alt_phone, qr_code)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         ''', (
#             test_student['student_id'],
#             test_student['name'],
#             test_student['department'],
#             test_student['class'],
#             test_student['phone'],
#             test_student['alt_phone'],
#             filename
#         ))
        
#         db.commit()
#         db.close()
        
#         return jsonify({
#             'status': 'success',
#             'message': 'Test student created successfully!',
#             'qr_url': f"/static/Student_QR/{filename}",
#             'student': test_student
#         })
        
#     except Exception as e:
#         return jsonify({'status': 'error', 'message': str(e)}), 500

# # API Routes for statistics
# @app.route('/api/stats')
# @login_required
# def api_stats():
#     db = get_db()
    
#     student_count = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
#     scan_count = db.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    
#     # Today's scans
#     today_scans = db.execute('''
#         SELECT COUNT(*) FROM scans WHERE DATE(scan_time) = DATE('now')
#     ''').fetchone()[0]
    
#     db.close()
    
#     return jsonify({
#         'students': student_count,
#         'scans': scan_count,
#         'today_scans': today_scans
#     })

# if __name__ == '__main__':
#     init_db()
#     app.run(debug=True, host='0.0.0.0', port=5000)