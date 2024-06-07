from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
import uuid
from vet_app import app, get_db_connection, mail
from flask_mail import Message

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

        password_hashed = generate_password_hash(password)
        verification_token = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO Users (name, email, password, verification_token) VALUES (%s, %s, %s, %s)', (name, email, password_hashed, verification_token))
        conn.commit()
        cursor.close()
        conn.close()

        # Send verification email
        verification_link = url_for('verify_email', token=verification_token, _external=True)
        msg = Message('Email Verification', recipients=[email])
        msg.body = f'Please click the link to verify your email: {verification_link}'
        mail.send(msg)

        flash('Registration successful. Please check your email to verify your account.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

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
    cursor.execute('SELECT p.id, p.name, GROUP_CONCAT(v.name SEPARATOR ", ") as vaccines FROM Pets p LEFT JOIN pet_vaccines pv ON p.id = pv.pet_id LEFT JOIN Vaccines v ON pv.vaccine_id = v.id WHERE p.user_id = %s GROUP BY p.id', (user_id,))
    pets = cursor.fetchall()
    cursor.execute('SELECT * FROM Vaccines')
    vaccines = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', pets=pets, vaccines=vaccines, username=session.get('username'))

@app.route('/add_pet', methods=['POST'])
def add_pet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    name = request.form['name']
    vaccine_id = request.form['vaccine_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Pets (user_id, name) VALUES (%s, %s)', (user_id, name))
    pet_id = cursor.lastrowid
    cursor.execute('INSERT INTO pet_vaccines (pet_id, vaccine_id) VALUES (%s, %s)', (pet_id, vaccine_id))
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
        vaccine_id = request.form['vaccine_id']
        cursor.execute('UPDATE Pets SET name = %s WHERE id = %s', (name, pet_id))
        cursor.execute('DELETE FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
        cursor.execute('INSERT INTO pet_vaccines (pet_id, vaccine_id) VALUES (%s, %s)', (pet_id, vaccine_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Pet updated successfully.', 'success')
        return redirect(url_for('dashboard'))
    cursor.execute('SELECT * FROM Pets WHERE id = %s', (pet_id,))
    pet = cursor.fetchone()
    cursor.execute('SELECT * FROM Vaccines')
    vaccines = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('edit_pet.html', pet=pet, vaccines=vaccines)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))
