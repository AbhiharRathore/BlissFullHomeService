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
        return redirect(url_for('main.home'))

# ─── Admin Login ───────────────────────────────────────────
@auth.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for('auth.admin_login'))

        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.password == password:
            login_user(admin, remember=True)
            session['role'] = 'admin'
            return redirect(url_for('main.admin_dashboard'))

        flash("Invalid credentials", "danger")
        return redirect(url_for('auth.admin_login'))

    return render_template('admin_login.html')

# ─── Customer Signup ───────────────────────────────────────
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
            flash("All fields are required.", "danger")
            return redirect(url_for('auth.user_signup'))

        if len(password) < 4:
            flash("Password must be at least 4 characters.", "danger")
            return redirect(url_for('auth.user_signup'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('auth.user_signup'))

        if len(pincode) != 6 or not pincode.isdigit():
            flash("Pincode must be exactly 6 digits.", "danger")
            return redirect(url_for('auth.user_signup'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already taken.", "danger")
            return redirect(url_for('auth.user_signup'))

        new_user = User.create_user(name, username, phone, address, pincode, password)
        flash("Signup successful! Please log in.", "success")
        return redirect(url_for('auth.user_login'))

    return render_template('user_signup.html')

# ─── Customer Login ────────────────────────────────────────
@auth.route('/login/user', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for('auth.user_login'))

        user = User.query.filter_by(username=username).first()

        if user and user.blocked:
            flash("Your account has been blocked. Please contact support.", "danger")
            return redirect(url_for('auth.user_login'))

        if user and user.password == password:
            login_user(user, remember=True)
            session['role'] = 'user'
            return redirect(url_for('main.user_dashboard'))

        flash("Invalid username or password.", "danger")
        return redirect(url_for('auth.user_login'))

    return render_template('user_login.html')

# ─── Professional Signup ───────────────────────────────────
@auth.route('/service_professional/signup', methods=['GET', 'POST'])
def service_professional_signup():
    services = Service.query.all()

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
        description = request.form.get('description', '').strip()

        # Backend validation
        if not all([name, username, password, confirm_password, phone, service_type, experience]):
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

        if len(password) < 4:
            flash("Password must be at least 4 characters.", "danger")
            return redirect(url_for('auth.service_professional_signup'))

        existing = ServiceProfessional.query.filter_by(username=username).first()
        if existing:
            flash("Username already taken.", "danger")
            return redirect(url_for('auth.service_professional_signup'))

        new_prof = ServiceProfessional(
            name=name,
            username=username,
            password=password,
            phone=phone,
            service_type=service_type,
            experience=int(experience),
            address=address,
            pincode=pincode,
            description=description,
            status='pending'
        )

        try:
            db.session.add(new_prof)
            db.session.commit()
            flash('Account created successfully. Awaiting approval from admin.', 'success')
            return redirect(url_for('auth.service_professional_login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('auth.service_professional_signup'))

    return render_template('service_professional_signup.html', services=services)

# ─── Professional Login ────────────────────────────────────
@auth.route('/service_professional/login', methods=['POST', 'GET'])
def service_professional_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for('auth.service_professional_login'))

        user = ServiceProfessional.query.filter_by(username=username).first()

        if user:
            if user.status == 'blocked':
                flash('Your account has been blocked. Please contact support.', 'danger')
                return redirect(url_for('main.home'))

            elif user.status == 'rejected':
                flash('Your application has been rejected. Please contact support.', 'danger')
                return redirect(url_for('auth.service_professional_login'))

            if user.password == password:
                if user.status == 'approved':
                    login_user(user)
                    session['role'] = 'service_professional'
                    flash('Login successful!', 'success')
                    return redirect(url_for('main.professional_dashboard'))
                else:
                    flash('Your account is still pending approval by an admin.', 'warning')
                    return redirect(url_for('auth.service_professional_login'))
            else:
                flash('Invalid username or password.', 'danger')
                return redirect(url_for('auth.service_professional_login'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.service_professional_login'))

    return render_template('service_professional_login.html')

# ─── Logout ───────────────────────────────────────────────
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.home'))
