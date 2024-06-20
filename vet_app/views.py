import os
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
import uuid
from vet_app import app, get_db_connection, mail
from flask_mail import Message
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image


def save_and_resize_image(image, filename):
    image_path = os.path.join(app.root_path, 'static/uploads', filename)
    image.save(image_path)
    img = Image.open(image_path)
    img.thumbnail((150, 150))
    img.save(image_path)
    print("image saved successfully at:", image_path)

def send_vaccine_reminders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT u.email, p.name as pet_name, pv.vaccine_name, pv.vaccination_date
        FROM pet_vaccines pv
        JOIN Pets p ON pv.pet_id = p.id
        JOIN Users u ON p.user_id = u.id
        WHERE pv.vaccination_date = CURDATE()
    ''')
    reminders = cursor.fetchall()
    cursor.close()
    conn.close()

    for reminder in reminders:
        msg = Message('Vaccine Reminder', recipients=[reminder['email']])
        msg.body = f'Dear pet owner, this is a reminder for your pet {reminder["pet_name"]}\'s vaccine: {reminder["vaccine_name"]} scheduled for today.'
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

        cursor.execute('INSERT INTO Users (name, email, password, verification_token, registration_date) VALUES (%s, %s, %s, %s, CURDATE())', (name, email, password_hashed, verification_token))
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
        # Handle username update
        username = request.form.get('username')
        if username:
            cursor.execute('UPDATE Users SET name = %s WHERE id = %s', (username, user_id))
            conn.commit()
            session['username'] = username
        
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture.filename != '':
                picture_path = os.path.join(app.root_path, 'static/uploads', profile_picture.filename)
                profile_picture.save(picture_path)
                cursor.execute('UPDATE Users SET profile_picture = %s WHERE id = %s', (profile_picture.filename, user_id))
                conn.commit()
        
        # Handle profile picture removal
        if 'remove_picture' in request.form:
            cursor.execute('SELECT profile_picture FROM Users WHERE id = %s', (user_id,))
            user = cursor.fetchone()
            if user['profile_picture']:
                picture_path = os.path.join(app.root_path, 'static/uploads', user['profile_picture'])
                if os.path.exists(picture_path):
                    os.remove(picture_path)
                cursor.execute('UPDATE Users SET profile_picture = NULL WHERE id = %s', (user_id,))
                conn.commit()

        # Handle password change
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if old_password and new_password and confirm_password:
            cursor.execute('SELECT password FROM Users WHERE id = %s', (user_id,))
            user = cursor.fetchone()
            if not check_password_hash(user['password'], old_password):
                flash('Old password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                if len(new_password) < 8 or not re.search(r'[A-Z]', new_password) or not re.search(r'[\W_]', new_password):
                    flash('Password must be at least 8 characters long, contain at least one uppercase letter, and one special character.', 'danger')
                else:
                    password_hashed = generate_password_hash(new_password)
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

        cursor.execute('SELECT * FROM Employees WHERE email = %s', (email,))
        employee = cursor.fetchone()
        if employee and check_password_hash(employee['password'], password):
            session['employee_id'] = employee['id']
            session['employee_role'] = employee['role']
            return redirect(url_for('admin_dashboard'))
        
        cursor.execute('SELECT * FROM Users WHERE email = %s', (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user['password'], password):
            if not user['verified']:
                flash('Please verify your email before logging in.', 'danger')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['username'] = user['name']
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'employee_id' not in session or session.get('employee_role') not in ['admin', 'employee']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get total users
    cursor.execute('SELECT COUNT(*) as total_users FROM Users')
    total_users = cursor.fetchone()['total_users']

    # Get total pets
    cursor.execute('SELECT COUNT(*) as total_pets FROM Pets')
    total_pets = cursor.fetchone()['total_pets']

    # Get new verified users in the last 30 days
    cursor.execute('SELECT COUNT(*) as new_users FROM Users WHERE registration_date >= CURDATE() - INTERVAL 30 DAY')
    new_users = cursor.fetchone()['new_users']

    # Get new pets in the last 30 days
    cursor.execute('SELECT COUNT(*) as new_pets FROM Pets WHERE registration_date >= CURDATE() - INTERVAL 30 DAY')
    new_pets = cursor.fetchone()['new_pets']

    # Get most popular pet type
    cursor.execute('SELECT type, COUNT(*) as count FROM Pets GROUP BY type ORDER BY count DESC LIMIT 1')
    popular_pet_type = cursor.fetchone()
    if popular_pet_type:
        popular_pet_type = popular_pet_type['type']

    # Get most common vaccines
    cursor.execute('SELECT vaccine_name, COUNT(*) as count FROM pet_vaccines GROUP BY vaccine_name ORDER BY count DESC LIMIT 1')
    common_vaccine = cursor.fetchone()
    if common_vaccine: 
        common_vaccine = common_vaccine['vaccine_name']

    # Get total recent vaccines
    cursor.execute('SELECT COUNT(*) as recent_vaccines FROM pet_vaccines WHERE vaccination_date >= CURDATE() - INTERVAL 30 DAY')
    recent_vaccines = cursor.fetchone()['recent_vaccines']

    cursor.close()
    conn.close()

    return render_template('admin_dashboard.html', total_users=total_users, total_pets=total_pets, new_users=new_users, new_pets=new_pets, popular_pet_type=popular_pet_type, common_vaccine=common_vaccine, recent_vaccines=recent_vaccines)

@app.route('/manage_pets')
def manage_pets():
    if 'employee_id' not in session or session.get('employee_role') not in ['admin', 'employee']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT p.id, p.name, p.type, GROUP_CONCAT(CONCAT(pv.vaccine_name, ' (', pv.vaccination_date, ')') SEPARATOR ", ") as vaccines, p.photo, u.name as owner_name, u.email as owner_email
        FROM Pets p
        LEFT JOIN pet_vaccines pv ON p.id = pv.pet_id
        LEFT JOIN Users u ON p.user_id = u.id
        GROUP BY p.id
    ''')
    pets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('manage_pets.html', pets=pets)

@app.route('/manage_employees')
def manage_employees():
    if 'employee_id' not in session or session.get('employee_role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Employees')
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('manage_employees.html', employees=employees)

@app.route('/add_employee', methods=['POST'])
def add_employee():
    if 'employee_id' not in session or session.get('employee_role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    password_hashed = generate_password_hash(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Employees (email, password, role) VALUES (%s, %s, %s)', (email, password_hashed, role))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_employee', methods=['POST'])
def edit_employee():
    if 'employee_id' not in session or session.get('employee_role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    employee_id = request.form['employee_id']
    email = request.form['email']
    role = request.form['role']
    password = request.form.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if password:
        password_hashed = generate_password_hash(password)
        cursor.execute('UPDATE Employees SET email = %s, role = %s, password = %s WHERE id = %s', (email, role, password_hashed, employee_id))
    else:
        cursor.execute('UPDATE Employees SET email = %s, role = %s WHERE id = %s', (email, role, employee_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('manage_employees'))

@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    if 'employee_id' not in session or session.get('employee_role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Employees WHERE id = %s', (employee_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Employee deleted successfully.', 'success')
    return redirect(url_for('manage_employees'))

@app.route('/admin_edit_pet/<int:pet_id>', methods=['GET', 'POST'])
def admin_edit_pet(pet_id):
    if 'employee_id' not in session or session.get('employee_role') not in ['admin', 'employee']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        name = request.form['name']
        type = request.form['type']
        
        vaccines = request.form.getlist('vaccine_name[]')
        vaccination_dates = request.form.getlist('vaccination_date[]')
        
        if 'pet_photo' in request.files:
            pet_photo = request.files['pet_photo']
            if pet_photo.filename != '':
                photo_filename = pet_photo.filename
                save_and_resize_image(pet_photo, photo_filename)
                cursor.execute('UPDATE Pets SET photo = %s WHERE id = %s', (photo_filename, pet_id))
        
        cursor.execute('UPDATE Pets SET name = %s, type = %s WHERE id = %s', (name, type, pet_id))
        cursor.execute('DELETE FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
        for vaccine_name, vaccination_date in zip(vaccines, vaccination_dates):
            cursor.execute('INSERT INTO pet_vaccines (pet_id, vaccine_name, vaccination_date) VALUES (%s, %s, %s)', (pet_id, vaccine_name, vaccination_date))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('manage_pets'))
    
    cursor.execute('SELECT id, name, type, photo FROM Pets WHERE id = %s', (pet_id,))
    pet = cursor.fetchone()
    cursor.execute('SELECT vaccine_name, vaccination_date FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
    pet['vaccines'] = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_edit_pet.html', pet=pet)

@app.route('/admin_delete_pet/<int:pet_id>', methods=['POST'])
def admin_delete_pet(pet_id):
    if 'employee_id' not in session or session.get('employee_role') not in ['admin', 'employee']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Pets WHERE id = %s', (pet_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Pet deleted successfully.', 'success')
    return redirect(url_for('manage_pets'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT p.id, p.name, p.type, GROUP_CONCAT(CONCAT(pv.vaccine_name, ' (', pv.vaccination_date, ')') SEPARATOR ", ") as vaccines, p.photo 
        FROM Pets p 
        LEFT JOIN pet_vaccines pv ON p.id = pv.pet_id 
        WHERE p.user_id = %s 
        GROUP BY p.id
    ''', (user_id,))
    pets = cursor.fetchall()
    user = cursor.execute('SELECT * from Users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', pets=pets, username=session.get('username'), user=user)

@app.route('/add_pet', methods=['POST'])
def add_pet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    name = request.form['name']
    type = request.form['type']
    
    vaccines = request.form.getlist('vaccine_name[]')
    vaccination_dates = request.form.getlist('vaccination_date[]')
    
    photo_filename = None
    if 'pet_photo' in request.files:
        pet_photo = request.files['pet_photo']
        if pet_photo.filename != '':
            photo_filename = pet_photo.filename
            save_and_resize_image(pet_photo, photo_filename)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Pets (user_id, name, type, photo, registration_date) VALUES (%s, %s, %s, %s, CURDATE())', (user_id, name, type, photo_filename))
    pet_id = cursor.lastrowid
    for vaccine_name, vaccination_date in zip(vaccines, vaccination_dates):
        cursor.execute('INSERT INTO pet_vaccines (pet_id, vaccine_name, vaccination_date) VALUES (%s, %s, %s)', (pet_id, vaccine_name, vaccination_date))
    conn.commit()
    cursor.close()
    conn.close()
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
        
        vaccines = request.form.getlist('vaccine_name[]')
        vaccination_dates = request.form.getlist('vaccination_date[]')
        
        if 'pet_photo' in request.files:
            pet_photo = request.files['pet_photo']
            if pet_photo.filename != '':
                photo_filename = pet_photo.filename
                save_and_resize_image(pet_photo, photo_filename)
                cursor.execute('UPDATE Pets SET photo = %s WHERE id = %s', (photo_filename, pet_id))
        
        cursor.execute('UPDATE Pets SET name = %s, type = %s WHERE id = %s', (name, type, pet_id))
        cursor.execute('DELETE FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
        for vaccine_name, vaccination_date in zip(vaccines, vaccination_dates):
            cursor.execute('INSERT INTO pet_vaccines (pet_id, vaccine_name, vaccination_date) VALUES (%s, %s, %s)', (pet_id, vaccine_name, vaccination_date))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    
    cursor.execute('SELECT id, name, type, photo FROM Pets WHERE id = %s', (pet_id,))
    pet = cursor.fetchone()
    cursor.execute('SELECT vaccine_name, vaccination_date FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
    pet['vaccines'] = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('edit_pet.html', pet=pet)

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

@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    if 'employee_id' not in session or session.get('employee_role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    if 'new_logo' in request.files:
        new_logo = request.files['new_logo']
        if new_logo.filename != '':
            logo_path = os.path.join(app.root_path, 'static/assets', 'new_logo.jpeg')
            new_logo.save(logo_path)
            flash('Logo updated successfully.', 'success')
        else:
            flash('No file selected.', 'danger')
    else:
        flash('No file selected.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
