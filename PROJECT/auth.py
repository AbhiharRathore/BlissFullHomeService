from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from flask_login import login_user, login_required, logout_user
from .models import Admin, User, ServiceProfessional, Service, db

auth = Blueprint('auth', __name__)


@auth.route('/select_user_type', methods=['POST'])
def select_user_type():
    user_type = request.form.get('user_type')
    session['user_type'] = user_type

    if user_type == 'user':
        return redirect(url_for('auth.user_signup'))
    elif user_type == 'service_professional':
        return redirect(url_for('auth.service_professional_signup'))
    elif user_type == 'admin':
        return redirect(url_for('auth.admin_login'))
    else:
        flash('Please select a user type.', 'warning')
        return redirect(url_for('main.home'))


@auth.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('auth.admin_login'))

        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin, remember=True)
            session['role'] = 'admin'
            flash('Welcome, Admin!', 'success')
            return redirect(url_for('main.admin_dashboard'))

        flash('Invalid credentials.', 'danger')
        return redirect(url_for('auth.admin_login'))

    return render_template('admin_login.html')


@auth.route('/signup/user', methods=['GET', 'POST'])
def user_signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        pincode = request.form.get('pincode', '').strip()
        password = request.form.get('pwd', '').strip()
        confirm_password = request.form.get('confpwd', '').strip()

        # Backend validation
        if not all([name, username, phone, address, pincode, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.user_signup'))

        if len(password) < 5:
            flash('Password must be at least 5 characters.', 'danger')
            return redirect(url_for('auth.user_signup'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.user_signup'))

        if len(pincode) != 6 or not pincode.isdigit():
            flash('Pincode must be exactly 6 digits.', 'danger')
            return redirect(url_for('auth.user_signup'))

        if not phone.isdigit() or len(phone) < 10:
            flash('Please enter a valid phone number (at least 10 digits).', 'danger')
            return redirect(url_for('auth.user_signup'))

        # Check duplicate username across all user tables
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.user_signup'))
        if ServiceProfessional.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.user_signup'))

        new_user = User.create_user(name, username, phone, address, pincode, password)
        login_user(new_user)
        session['role'] = 'user'
        flash('Signup successful! Welcome to BlissfulHome Services.', 'success')
        return redirect(url_for('main.user_dashboard'))

    return render_template('user_signup.html')


@auth.route('/login/user', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('auth.user_login'))

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Check if user is blocked
            if user.is_blocked:
                flash('Your account has been blocked. Please contact support.', 'danger')
                return redirect(url_for('auth.user_login'))

            login_user(user, remember=True)
            session['role'] = 'user'
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('main.user_dashboard'))

        flash('Invalid username or password.', 'danger')
        return redirect(url_for('auth.user_login'))

    return render_template('user_login.html')


@auth.route('/service_professional/signup', methods=['GET', 'POST'])
def service_professional_signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('pwd', '').strip()
        confirm_password = request.form.get('confpwd', '').strip()
        phone = request.form.get('phone', '').strip()
        service_type = request.form.get('service_type', '').strip()
        experience = request.form.get('experience', '').strip()
        address = request.form.get('address', '').strip()
        pincode = request.form.get('pincode', '').strip()

        # Backend validation
        if not all([name, username, password, confirm_password, phone, service_type, experience, address, pincode]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        if len(password) < 5:
            flash('Password must be at least 5 characters.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        if not phone.isdigit() or len(phone) < 10:
            flash('Please enter a valid phone number.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        if len(pincode) != 6 or not pincode.isdigit():
            flash('Pincode must be exactly 6 digits.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        try:
            exp_val = int(experience)
            if exp_val < 0:
                flash('Experience must be a positive number.', 'danger')
                return redirect(url_for('auth.service_professional_signup'))
        except ValueError:
            flash('Experience must be a valid number.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        # Check duplicate username across all tables
        if User.query.filter_by(username=username).first() or \
           ServiceProfessional.query.filter_by(username=username).first() or \
           Admin.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        # Validate service type exists
        service = Service.query.filter(Service.name.ilike(service_type)).first()
        if not service:
            flash(f'Service type "{service_type}" does not exist. Please choose from available services.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        new_professional = ServiceProfessional(
            name=name,
            username=username,
            phone=phone,
            service_type=service.name,  # Use the exact name from DB
            experience=exp_val,
            address=address,
            pincode=pincode,
            status='pending'
        )
        new_professional.set_password(password)

        try:
            db.session.add(new_professional)
            db.session.commit()
            flash('Account created successfully. Awaiting approval from admin.', 'success')
            return redirect(url_for('auth.service_professional_login'))
        except Exception:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

    # Pass available services for the dropdown
    services = Service.query.all()
    return render_template('service_professional_signup.html', services=services)


@auth.route('/service_professional/login', methods=['POST', 'GET'])
def service_professional_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('auth.service_professional_login'))

        user = ServiceProfessional.query.filter_by(username=username).first()

        if not user:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.service_professional_login'))

        if user.status == 'blocked':
            flash('Your account has been blocked. Please contact support.', 'danger')
            return redirect(url_for('auth.service_professional_login'))

        if user.status == 'rejected':
            flash('Your registration has been rejected. Please contact support.', 'danger')
            return redirect(url_for('auth.service_professional_login'))

        if not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.service_professional_login'))

        if user.status == 'approved':
            login_user(user)
            session['role'] = 'service_professional'
            flash(f'Welcome, {user.name}!', 'success')
            return redirect(url_for('main.professional_dashboard'))
        else:
            flash('Your account is still pending approval by an admin.', 'warning')
            return redirect(url_for('auth.service_professional_login'))

    return render_template('service_professional_login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))
