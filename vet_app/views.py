from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
from vet_app import app, get_db_connection

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[\W_]', password):
            flash('Password must be at least 8 characters long, contain at least one uppercase letter, and one special character.', 'danger')
            return redirect(url_for('register'))

        password_hashed = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO Users (name, email, password) VALUES (%s, %s, %s)', (name, email, password_hashed))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM Users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Pets WHERE user_id = %s', (user_id,))
    pets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', pets=pets)

@app.route('/add_pet', methods=['POST'])
def add_pet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    name = request.form['name']
    type = request.form['type']
    age = request.form['age']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Pets (user_id, name, type, age) VALUES (%s, %s, %s, %s)', (user_id, name, type, age))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))
