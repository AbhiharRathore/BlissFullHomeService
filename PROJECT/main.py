from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, session, url_for, flash
from flask_login import login_required, current_user
from .models import Admin, Service, ServiceRequest, ServiceProfessional, User, db

main = Blueprint('main', __name__)


# ──────────────────────────────────────────────
# Helper: role checking decorators
# ──────────────────────────────────────────────

def admin_required(f):
    """Decorator to ensure the current user is an admin."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin' or not isinstance(current_user, Admin):
            flash('You are not authorized to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


def professional_required(f):
    """Decorator to ensure the current user is an approved professional."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'service_professional' or not isinstance(current_user, ServiceProfessional):
            flash('You are not authorized to access this page.', 'danger')
            return redirect(url_for('main.home'))
        if current_user.status == 'blocked':
            flash('Your account has been blocked.', 'danger')
            return redirect(url_for('main.home'))
        if current_user.status != 'approved':
            flash('Your account is not yet approved.', 'warning')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


def customer_required(f):
    """Decorator to ensure the current user is a non-blocked customer."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'user' or not isinstance(current_user, User):
            flash('You are not authorized to access this page.', 'danger')
            return redirect(url_for('main.home'))
        if current_user.is_blocked:
            flash('Your account has been blocked.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


# ──────────────────────────────────────────────
# Home
# ──────────────────────────────────────────────

@main.route('/')
def home():
    return render_template('home.html')


# ──────────────────────────────────────────────
# Admin Dashboard & Management
# ──────────────────────────────────────────────

@main.route('/admin/dashboard', methods=['GET'])
@login_required
@admin_required
def admin_dashboard():
    search_query = request.args.get('search', '').strip()

    if search_query:
        services = Service.query.filter(
            (Service.name.ilike(f'%{search_query}%')) |
            (Service.description.ilike(f'%{search_query}%'))
        ).all()
        professionals = ServiceProfessional.query.filter(
            (ServiceProfessional.name.ilike(f'%{search_query}%')) |
            (ServiceProfessional.username.ilike(f'%{search_query}%')) |
            (ServiceProfessional.service_type.ilike(f'%{search_query}%'))
        ).all()
        all_requests = ServiceRequest.query.filter(
            ServiceRequest.status.ilike(f'%{search_query}%')
        ).all()
    else:
        services = Service.query.all()
        professionals = []
        all_requests = ServiceRequest.query.all()

    pending_professionals = ServiceProfessional.query.filter_by(status='pending').all()
    approved_professionals = ServiceProfessional.query.filter_by(status='approved').all()
    customers = User.query.all()

    return render_template('admin_dashboard.html',
                           services=services,
                           pending_professionals=pending_professionals,
                           approved_professionals=approved_professionals,
                           service_requests=all_requests,
                           search_query=search_query,
                           professionals=professionals,
                           customers=customers)


@main.route('/admin/service/manage', methods=['GET', 'POST'])
@main.route('/admin/service/manage/<int:service_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def service_manage(service_id=None):
    if request.method == 'POST':
        service_name = request.form.get('service_name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price', '').strip()
        time_str = request.form.get('time_required', '60').strip()

        # Validation
        if not service_name or not description or not price_str:
            flash('All fields are required.', 'danger')
            return redirect(url_for('main.service_manage', service_id=service_id))

        try:
            price = float(price_str)
            if price <= 0:
                raise ValueError
        except ValueError:
            flash('Price must be a positive number.', 'danger')
            return redirect(url_for('main.service_manage', service_id=service_id))

        try:
            time_required = int(time_str)
            if time_required <= 0:
                raise ValueError
        except ValueError:
            time_required = 60

        if service_id:
            service = Service.query.get(service_id)
            if service:
                service.name = service_name
                service.description = description
                service.price = price
                service.time_required = time_required
                db.session.commit()
                flash('Service updated successfully!', 'success')
            else:
                flash('Service not found!', 'danger')
        else:
            new_service = Service(name=service_name, description=description,
                                  price=price, time_required=time_required)
            db.session.add(new_service)
            db.session.commit()
            flash('New service added successfully!', 'success')

        return redirect(url_for('main.service_manage'))

    services = Service.query.all()
    service = None
    if service_id:
        service = Service.query.get(service_id)

    return render_template('service_manage.html', service=service, services=services)


@main.route('/admin/service/delete/<int:service_id>', methods=['POST'])
@login_required
@admin_required
def delete_service(service_id):
    service = Service.query.get(service_id)
    if not service:
        flash('Service not found!', 'danger')
        return redirect(url_for('main.service_manage'))

    # Check if service has active requests
    active_requests = ServiceRequest.query.filter(
        ServiceRequest.service_id == service_id,
        ServiceRequest.status.in_(['pending', 'accepted'])
    ).count()

    if active_requests > 0:
        flash(f'Cannot delete "{service.name}" — it has {active_requests} active request(s). Close them first.', 'danger')
        return redirect(url_for('main.service_manage'))

    try:
        # Delete completed/closed/rejected requests first
        ServiceRequest.query.filter_by(service_id=service_id).delete()
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('Error deleting service. Please try again.', 'danger')

    return redirect(url_for('main.service_manage'))


# ──────────────────────────────────────────────
# Admin: Professional Management
# ──────────────────────────────────────────────

@main.route('/admin/approve/professional/<int:professional_id>', methods=['POST'])
@login_required
@admin_required
def approve_professional(professional_id):
    professional = ServiceProfessional.query.get(professional_id)
    if professional:
        professional.status = 'approved'
        db.session.commit()
        flash(f'Professional "{professional.name}" approved successfully!', 'success')
    else:
        flash('Professional not found!', 'danger')
    return redirect(url_for('main.admin_dashboard'))


@main.route('/admin/reject/professional/<int:professional_id>', methods=['POST'])
@login_required
@admin_required
def reject_professional(professional_id):
    professional = ServiceProfessional.query.get(professional_id)
    if professional:
        professional.status = 'rejected'
        db.session.commit()
        flash(f'Professional "{professional.name}" rejected.', 'info')
    else:
        flash('Professional not found!', 'danger')
    return redirect(url_for('main.admin_dashboard'))


@main.route('/admin/block/professional/<int:professional_id>', methods=['POST'])
@login_required
@admin_required
def block_professional(professional_id):
    professional = ServiceProfessional.query.get_or_404(professional_id)
    professional.status = 'blocked'
    db.session.commit()
    flash(f'Professional "{professional.name}" has been blocked.', 'success')
    return redirect(url_for('main.admin_dashboard'))


@main.route('/admin/unblock/professional/<int:professional_id>', methods=['POST'])
@login_required
@admin_required
def unblock_professional(professional_id):
    professional = ServiceProfessional.query.get_or_404(professional_id)
    professional.status = 'approved'
    db.session.commit()
    flash(f'Professional "{professional.name}" has been unblocked.', 'success')
    return redirect(url_for('main.view_blocked_professionals'))


@main.route('/admin/blocked_professionals')
@login_required
@admin_required
def view_blocked_professionals():
    blocked_professionals = ServiceProfessional.query.filter_by(status='blocked').all()
    return render_template('blocked_professionals.html', blocked_professionals=blocked_professionals)


# ──────────────────────────────────────────────
# Admin: Customer Management
# ──────────────────────────────────────────────

@main.route('/admin/block/customer/<int:customer_id>', methods=['POST'])
@login_required
@admin_required
def block_customer(customer_id):
    customer = User.query.get_or_404(customer_id)
    customer.is_blocked = True
    db.session.commit()
    flash(f'Customer "{customer.name}" has been blocked.', 'success')
    return redirect(url_for('main.admin_dashboard'))


@main.route('/admin/unblock/customer/<int:customer_id>', methods=['POST'])
@login_required
@admin_required
def unblock_customer(customer_id):
    customer = User.query.get_or_404(customer_id)
    customer.is_blocked = False
    db.session.commit()
    flash(f'Customer "{customer.name}" has been unblocked.', 'success')
    return redirect(url_for('main.admin_dashboard'))


# ──────────────────────────────────────────────
# Customer Dashboard & Features
# ──────────────────────────────────────────────

@main.route('/user/dashboard')
@login_required
@customer_required
def user_dashboard():
    search_query = request.args.get('search', '').strip()

    if search_query:
        services = Service.query.filter(
            Service.name.ilike(f'%{search_query}%') |
            Service.description.ilike(f'%{search_query}%')
        ).all()
    else:
        services = Service.query.all()

    service_requests = ServiceRequest.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html',
                           search_query=search_query,
                           services=services,
                           service_requests=service_requests)


@main.route('/user/profile', methods=['GET', 'POST'])
@login_required
@customer_required
def user_profile():
    user = current_user

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        pincode = request.form.get('pincode', '').strip()

        if not all([name, phone, address, pincode]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('main.user_profile'))

        user.name = name
        user.phone = phone
        user.address = address
        user.pincode = pincode

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')

        return redirect(url_for('main.user_profile'))

    return render_template('user_profile.html', user=user)


@main.route('/booking/<int:service_id>', methods=['POST', 'GET'])
@login_required
@customer_required
def booking(service_id):
    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        # Create the service request
        req = ServiceRequest(user_id=current_user.id, service_id=service_id)
        db.session.add(req)
        db.session.commit()
        flash('Service booked successfully!', 'success')
        return redirect(url_for('main.user_dashboard'))

    return render_template('booking.html', service=service)


@main.route('/close_service/<int:request_id>', methods=['POST'])
@login_required
@customer_required
def close_service(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)

    # Ensure the customer owns this request
    if service_request.user_id != current_user.id:
        flash('You are not authorized to close this request.', 'danger')
        return redirect(url_for('main.user_dashboard'))

    # Validate state transition
    if service_request.status in ('closed', 'completed'):
        flash('This request is already closed.', 'warning')
        return redirect(url_for('main.user_dashboard'))

    service_request.status = 'closed'
    service_request.date_completed = datetime.utcnow()
    db.session.commit()
    flash('Service request closed. Please submit your rating.', 'success')
    return redirect(url_for('main.submit_rating', service_request_id=request_id))


@main.route('/submit_rating/<int:service_request_id>', methods=['GET', 'POST'])
@login_required
@customer_required
def submit_rating(service_request_id):
    service_request = ServiceRequest.query.get_or_404(service_request_id)

    if service_request.user_id != current_user.id:
        flash('You are not authorized to rate this service request.', 'danger')
        return redirect(url_for('main.user_dashboard'))

    if service_request.status not in ('closed', 'accepted'):
        flash('You can only rate closed or completed services.', 'warning')
        return redirect(url_for('main.user_dashboard'))

    if request.method == 'POST':
        rating_val = request.form.get('rating')
        review_text = request.form.get('review', '').strip()

        if not rating_val:
            flash('Please provide a rating.', 'danger')
            return redirect(url_for('main.submit_rating', service_request_id=service_request_id))

        try:
            rating_int = int(rating_val)
            if not (1 <= rating_int <= 5):
                raise ValueError
        except ValueError:
            flash('Please provide a rating between 1 and 5.', 'danger')
            return redirect(url_for('main.submit_rating', service_request_id=service_request_id))

        service_request.rating = rating_int
        service_request.review = review_text
        service_request.status = 'completed'
        service_request.date_completed = service_request.date_completed or datetime.utcnow()

        if service_request.service_professional_id:
            ServiceProfessional.update_professional_rating(service_request.service_professional_id)

        try:
            db.session.commit()
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('main.user_dashboard'))
        except Exception:
            db.session.rollback()
            flash('An error occurred while submitting your rating.', 'danger')
            return redirect(url_for('main.submit_rating', service_request_id=service_request_id))

    return render_template('rating.html', service_request=service_request)


# ──────────────────────────────────────────────
# Professional Dashboard & Features
# ──────────────────────────────────────────────

@main.route('/serviceprofessional/dashboard', endpoint='professional_dashboard')
@login_required
@professional_required
def dashboard():
    search_query = request.args.get('search_query', '').strip()

    # Query pending requests matching this professional's service type
    todays_query = db.session.query(ServiceRequest, Service, User) \
        .join(Service, ServiceRequest.service_id == Service.id) \
        .join(User, ServiceRequest.user_id == User.id) \
        .filter(ServiceRequest.status == 'pending') \
        .filter(Service.name == current_user.service_type)

    if search_query:
        todays_query = todays_query.filter(
            (User.name.ilike(f'%{search_query}%')) |
            (User.address.ilike(f'%{search_query}%')) |
            (User.pincode.ilike(f'%{search_query}%')) |
            (User.phone.ilike(f'%{search_query}%'))
        )

    todays_services = todays_query.all()

    # Show closed/completed services assigned to this professional
    closed_services = db.session.query(ServiceRequest, Service, User) \
        .join(Service, ServiceRequest.service_id == Service.id) \
        .join(User, ServiceRequest.user_id == User.id) \
        .filter(ServiceRequest.service_professional_id == current_user.id) \
        .filter(ServiceRequest.status.in_(['closed', 'completed'])) \
        .all()

    # Show accepted services for this professional
    accepted_services = db.session.query(ServiceRequest, Service, User) \
        .join(Service, ServiceRequest.service_id == Service.id) \
        .join(User, ServiceRequest.user_id == User.id) \
        .filter(ServiceRequest.service_professional_id == current_user.id) \
        .filter(ServiceRequest.status == 'accepted') \
        .all()

    return render_template('professional_dashboard.html',
                           todays_services=todays_services,
                           closed_services=closed_services,
                           accepted_services=accepted_services)


@main.route('/professionalprofile', methods=['GET', 'POST'])
@login_required
@professional_required
def edit_professional_profile():
    professional_data = ServiceProfessional.query.get(current_user.id)

    if professional_data is None:
        flash('No professional profile found.', 'danger')
        return redirect(url_for('main.professional_dashboard'))

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        experience = request.form.get('experience', '').strip()
        address = request.form.get('address', '').strip()
        pincode = request.form.get('pincode', '').strip()

        if not all([phone, experience, address, pincode]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('main.edit_professional_profile'))

        professional_data.phone = phone
        professional_data.experience = int(experience)
        professional_data.address = address
        professional_data.pincode = pincode

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')

        return redirect(url_for('main.edit_professional_profile'))

    return render_template('professional_profile.html', professional=professional_data)


@main.route('/serviceprofessional/accept_service/<int:service_request_id>', methods=['POST'])
@login_required
@professional_required
def accept_service(service_request_id):
    service_request = ServiceRequest.query.get(service_request_id)

    if not service_request:
        flash('Service request not found.', 'danger')
        return redirect(url_for('main.professional_dashboard'))

    if service_request.status != 'pending':
        flash('This service request is no longer available.', 'warning')
        return redirect(url_for('main.professional_dashboard'))

    if service_request.service_professional_id is not None:
        flash('This service request has already been accepted.', 'warning')
        return redirect(url_for('main.professional_dashboard'))

    # Verify the service type matches
    service = Service.query.get(service_request.service_id)
    if service and service.name != current_user.service_type:
        flash('This service request does not match your service type.', 'danger')
        return redirect(url_for('main.professional_dashboard'))

    service_request.accept(current_user.id)
    db.session.commit()

    flash('Service request accepted successfully!', 'success')
    return redirect(url_for('main.professional_dashboard'))


@main.route('/serviceprofessional/reject_service/<int:service_request_id>', methods=['POST'])
@login_required
@professional_required
def reject_service(service_request_id):
    service_request = ServiceRequest.query.get(service_request_id)

    if not service_request:
        flash('Service request not found.', 'danger')
        return redirect(url_for('main.professional_dashboard'))

    if service_request.status != 'pending':
        flash('This service request is no longer available.', 'warning')
        return redirect(url_for('main.professional_dashboard'))

    service_request.reject()
    db.session.commit()

    flash('Service request rejected.', 'info')
    return redirect(url_for('main.professional_dashboard'))


# ──────────────────────────────────────────────
# Public Services Page
# ──────────────────────────────────────────────

@main.route('/services', methods=['GET'])
def services():
    all_services = Service.query.all()
    return render_template('services.html', services=all_services)


# ──────────────────────────────────────────────
# Summary Page
# ──────────────────────────────────────────────

@main.route('/summary')
@login_required
@admin_required
def summary():
    total_services = Service.query.count()
    total_customers = User.query.count()
    total_professionals = ServiceProfessional.query.count()
    total_requests = ServiceRequest.query.count()
    pending_requests = ServiceRequest.query.filter_by(status='pending').count()
    completed_requests = ServiceRequest.query.filter_by(status='completed').count()
    closed_requests = ServiceRequest.query.filter_by(status='closed').count()

    return render_template('summary.html',
                           total_services=total_services,
                           total_customers=total_customers,
                           total_professionals=total_professionals,
                           total_requests=total_requests,
                           pending_requests=pending_requests,
                           completed_requests=completed_requests,
                           closed_requests=closed_requests)


# ──────────────────────────────────────────────
# API: Search (JSON)
# ──────────────────────────────────────────────

@main.route('/api/search', methods=['GET'])
@login_required
def api_search():
    search_query = request.args.get('q', '').strip()

    if not search_query:
        return jsonify({'services': [], 'professionals': []})

    try:
        services = Service.query.filter(
            (Service.name.ilike(f'%{search_query}%')) |
            (Service.description.ilike(f'%{search_query}%'))
        ).all()

        professionals = ServiceProfessional.query.filter(
            (ServiceProfessional.name.ilike(f'%{search_query}%')) |
            (ServiceProfessional.service_type.ilike(f'%{search_query}%'))
        ).all()

        results = {
            'services': [{
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'price': s.price,
            } for s in services],
            'professionals': [{
                'id': p.id,
                'name': p.name,
                'service_type': p.service_type,
                'status': p.status,
                'rating': p.rating,
            } for p in professionals],
        }
        return jsonify(results)
    except Exception:
        return jsonify({'error': 'An error occurred during the search.'}), 500