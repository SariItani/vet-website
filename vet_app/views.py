import os
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
import uuid
from vet_app import app, get_db_connection, mail
from flask_mail import Message
from apscheduler.schedulers.background import BackgroundScheduler


def send_vaccine_reminders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT u.email, p.name as pet_name, pv.vaccine_name, pv.due_date FROM Users u JOIN Pets p ON u.id = p.user_id JOIN pet_vaccines pv ON p.id = pv.pet_id WHERE pv.due_date = CURDATE() + INTERVAL 1 DAY')
    reminders = cursor.fetchall()
    cursor.close()
    conn.close()

    for reminder in reminders:
        msg = Message('Vaccine Reminder', recipients=[reminder['email']])
        msg.body = f"Dear {reminder['email']},\n\nThis is a reminder that your pet {reminder['pet_name']} is due for the {reminder['vaccine_name']} vaccine tomorrow ({reminder['due_date']}).\n\nBest regards,\nVetClinic"
        mail.send(msg)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_vaccine_reminders, 'interval', days=1)
    scheduler.start()

start_scheduler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Password validation
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[\W_]', password):
            flash('Password must be at least 8 characters long, contain at least one uppercase letter, and one special character.', 'danger')
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM Users WHERE email = %s', (email,))
        existing_email = cursor.fetchone()
        if existing_email:
            flash('Registration Failed. Email already exists.', 'danger')
            return redirect(url_for('register'))

        password_hashed = generate_password_hash(password)
        verification_token = str(uuid.uuid4())

        # Send verification email
        verification_link = url_for('verify_email', token=verification_token, _external=True)
        msg = Message('Email Verification', recipients=[email])
        msg.body = f'Please click the link to verify your email: {verification_link}'
        mail.send(msg)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO Users (name, email, password, verification_token) VALUES (%s, %s, %s, %s)', (name, email, password_hashed, verification_token))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Registration successful. Please check your email to verify your account.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture.filename != '':
                picture_path = os.path.join(app.root_path, 'static/uploads', profile_picture.filename)
                profile_picture.save(picture_path)
                cursor.execute('UPDATE Users SET profile_picture = %s WHERE id = %s', (profile_picture.filename, user_id))
                conn.commit()
                flash('Profile picture updated successfully.', 'success')
        
        # Handle password change
        password = request.form.get('password')
        if password:
            if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[\W_]', password):
                flash('Password must be at least 8 characters long, contain at least one uppercase letter, and one special character.', 'danger')
            else:
                password_hashed = generate_password_hash(password)
                cursor.execute('UPDATE Users SET password = %s WHERE id = %s', (password_hashed, user_id))
                conn.commit()
                flash('Password updated successfully.', 'success')
    
    cursor.execute('SELECT * FROM Users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('profile.html', user=user)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM Users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            reset_token = str(uuid.uuid4())
            reset_link = url_for('reset_password', token=reset_token, _external=True)
            msg = Message('Password Reset Request', recipients=[email])
            msg.body = f'Please click the link to reset your password: {reset_link}'
            mail.send(msg)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE Users SET reset_token = %s WHERE email = %s', (reset_token, email))
            conn.commit()
            cursor.close()
            conn.close()

            flash('Password reset email sent. Please check your email.', 'info')
        else:
            flash('Email not found.', 'danger')
    return render_template('reset_password_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form['password']
        password_hashed = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE Users SET password = %s, reset_token = NULL WHERE reset_token = %s', (password_hashed, token))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Password reset successful. You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/verify_email/<token>')
def verify_email(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Users WHERE verification_token = %s', (token,))
    user = cursor.fetchone()
    if user:
        cursor.execute('UPDATE Users SET verified = TRUE, verification_token = NULL WHERE id = %s', (user[0],))
        conn.commit()
        flash('Email verified successfully. You can now log in.', 'success')
    else:
        flash('Invalid or expired token.', 'danger')
    cursor.close()
    conn.close()
    return redirect(url_for('login'))

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
            if not user['verified']:
                flash('Please verify your email before logging in.', 'danger')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['username'] = user['name']
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
    cursor.execute('SELECT p.id, p.name, p.type, GROUP_CONCAT(pv.vaccine_name SEPARATOR ", ") as vaccines FROM Pets p LEFT JOIN pet_vaccines pv ON p.id = pv.pet_id WHERE p.user_id = %s GROUP BY p.id', (user_id,))
    pets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', pets=pets, username=session.get('username'))

@app.route('/add_pet', methods=['POST'])
def add_pet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    name = request.form['name']
    type = request.form['type']
    vaccine_name = request.form['vaccine_name']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Pets (user_id, name, type) VALUES (%s, %s, %s)', (user_id, name, type))
    pet_id = cursor.lastrowid
    cursor.execute('INSERT INTO pet_vaccines (pet_id, vaccine_name) VALUES (%s, %s)', (pet_id, vaccine_name))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete_pet/<int:pet_id>', methods=['POST'])
def delete_pet(pet_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Pets WHERE id = %s', (pet_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Pet deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_pet/<int:pet_id>', methods=['GET', 'POST'])
def edit_pet(pet_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        name = request.form['name']
        type = request.form['type']
        vaccine_name = request.form['vaccine_name']
        cursor.execute('UPDATE Pets SET name = %s, type = %s WHERE id = %s', (name, type, pet_id))
        cursor.execute('DELETE FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
        cursor.execute('INSERT INTO pet_vaccines (pet_id, vaccine_name) VALUES (%s, %s)', (pet_id, vaccine_name))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Pet updated successfully.', 'success')
        return redirect(url_for('dashboard'))
    cursor.execute('SELECT p.id, p.name, p.type, pv.vaccine_name FROM Pets p LEFT JOIN pet_vaccines pv ON p.id = pv.pet_id WHERE p.id = %s', (pet_id,))
    pet = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit_pet.html', pet=pet)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))
