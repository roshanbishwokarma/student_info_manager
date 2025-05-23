from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import pandas as pd
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # replace with a strong random string

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password123'


# Create DB and table if not exists
def init_db():

    print("📂 Creating the database...")
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Students table (already created)
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT NOT NULL,
            class_name TEXT NOT NULL
        )
    ''')

    # ✅ Attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')

    # ✅ Results table
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject TEXT,
            marks INTEGER,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')


    conn.commit()
    conn.close()

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        class_name = request.form['class_name']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO students (name, roll_no, class_name) VALUES (?, ?, ?)",
                  (name, roll_no, class_name))
        conn.commit()
        conn.close()
        return redirect('/students')
    return render_template('add_student.html')

@app.route('/students')
def students():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students")
    students = c.fetchall()
    conn.close()
    return render_template('view_students.html', students=students)

from datetime import date

@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        selected_date = request.form['date']
        for student_id in request.form.getlist('student_id'):
            status = request.form.get(f'status_{student_id}')
            c.execute('INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)',
                      (student_id, selected_date, status))
        conn.commit()
        conn.close()
        return redirect('/attendance_records')
    
    c.execute("SELECT * FROM students")
    students = c.fetchall()
    conn.close()
    return render_template('mark_attendance.html', students=students, today=str(date.today()))

@app.route('/attendance_records')
def attendance_records():
    filter_date = request.args.get('date')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if filter_date:
        c.execute('''
            SELECT a.date, s.name, s.roll_no, s.class_name, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.date = ?
            ORDER BY a.date DESC
        ''', (filter_date,))
    else:
        c.execute('''
            SELECT a.date, s.name, s.roll_no, s.class_name, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            ORDER BY a.date DESC
        ''')

    records = c.fetchall()
    conn.close()
    return render_template('view_attendance.html', records=records)
    import pandas as pd  # Make sure this is at the top of app.py

@app.route('/export_attendance')
def export_attendance():
    filter_date = request.args.get('date')

    conn = sqlite3.connect('database.db')
    query = '''
        SELECT a.date, s.name AS student_name, s.roll_no, s.class_name, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
    '''
    if filter_date:
        query += " WHERE a.date = ?"
        df = pd.read_sql_query(query, conn, params=(filter_date,))
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()

    # Save Excel file
    filename = "attendance_export.xlsx"
    df.to_excel(filename, index=False)

    from flask import send_file
    return send_file(filename, as_attachment=True)

@app.route('/add_result', methods=['GET', 'POST'])
def add_result():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        marks = request.form['marks']

        c.execute('INSERT INTO results (student_id, subject, marks) VALUES (?, ?, ?)',
                  (student_id, subject, marks))
        conn.commit()
        conn.close()
        return redirect('/view_results')

    c.execute("SELECT * FROM students")
    students = c.fetchall()
    conn.close()
    return render_template('add_result.html', students=students)
from flask import request

@app.route('/view_results')
@login_required
def view_results():
    class_filter = request.args.get('class_filter', '').strip()
    student_filter = request.args.get('student_filter', '').strip()

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    query = '''
        SELECT r.subject, r.marks, s.name, s.roll_no, s.class_name, r.id
        FROM results r
        JOIN students s ON r.student_id = s.id
        WHERE 1=1
    '''
    params = []

    if class_filter:
        query += " AND s.class_name = ?"
        params.append(class_filter)

    if student_filter:
        query += " AND s.name LIKE ?"
        params.append(f"%{student_filter}%")

    query += " ORDER BY s.class_name, s.name"

    c.execute(query, params)
    results = c.fetchall()
    conn.close()
    return render_template('view_results.html', results=results)


@app.route('/edit_result/<int:result_id>', methods=['GET', 'POST'])
def edit_result(result_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        subject = request.form['subject']
        marks = request.form['marks']

        c.execute('UPDATE results SET subject = ?, marks = ? WHERE id = ?', (subject, marks, result_id))
        conn.commit()
        conn.close()
        return redirect('/view_results')

    # GET request - fetch current result details
    c.execute('''
        SELECT r.subject, r.marks, r.student_id, s.name
        FROM results r
        JOIN students s ON r.student_id = s.id
        WHERE r.id = ?
    ''', (result_id,))
    result = c.fetchone()
    conn.close()

    if result is None:
        return "Result not found", 404

    return render_template('edit_result.html', result=result, result_id=result_id)
@app.route('/delete_result/<int:result_id>', methods=['POST', 'GET'])
def delete_result(result_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM results WHERE id = ?', (result_id,))
    conn.commit()
    conn.close()
    return redirect('/view_results')
from flask import request

@app.route('/search_student', methods=['GET'])
def search_student():
    query = request.args.get('query')
    students = []
    if query:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # Search students by name (case-insensitive)
        c.execute("SELECT * FROM students WHERE name LIKE ?", ('%' + query + '%',))
        students = c.fetchall()
        conn.close()
    return render_template('search_student.html', students=students)

from flask import request, session, redirect, url_for, flash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))  # or dashboard page
        else:
            flash('Invalid Credentials. Please try again.', 'danger')
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))




if __name__ == '__main__':
    init_db()
    app.run(debug=True)

import threading
import webview
import time
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello from Flask!"

def run_flask():
    app.run(debug=False, use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Optional: wait 1 second to be safe
    # time.sleep(1)
    
    webview.create_window("My Flask App", "http://127.0.0.1:5000")
