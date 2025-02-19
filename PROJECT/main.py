from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, session, url_for, flash
from flask_login import login_required, current_user
from .models import Admin, Service, ServiceRequest, ServiceProfessional, User, db
from sqlalchemy import func

main = Blueprint('main', __name__)

# ─── Home ──────────────────────────────────────────────────
@main.route('/')
def home():
    return render_template('home.html')

# ─── Admin Dashboard ──────────────────────────────────────
@main.route('/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('main.home'))

    search_query = request.args.get('search', '').strip()

    # Stats
    total_services = Service.query.count()
    total_customers = User.query.count()
    total_professionals = ServiceProfessional.query.count()
    total_requests = ServiceRequest.query.count()

    # Lists
    services_all = Service.query.all()
    pending_professionals = ServiceProfessional.query.filter_by(status='pending').all()
    approved_professionals = ServiceProfessional.query.filter_by(status='approved').all()
    all_customers = User.query.all()
    service_requests_all = ServiceRequest.query.order_by(ServiceRequest.date_requested.desc()).all()

    # Search filtering
    if search_query:
        services_all = Service.query.filter(
            Service.name.ilike(f'%{search_query}%') |
            Service.description.ilike(f'%{search_query}%')
        ).all()
        approved_professionals = ServiceProfessional.query.filter(
            (ServiceProfessional.name.ilike(f'%{search_query}%') |
             ServiceProfessional.service_type.ilike(f'%{search_query}%')) &
            (ServiceProfessional.status == 'approved')
        ).all()
        service_requests_all = ServiceRequest.query.join(Service).filter(
            Service.name.ilike(f'%{search_query}%') |
            ServiceRequest.status.ilike(f'%{search_query}%')
        ).order_by(ServiceRequest.date_requested.desc()).all()

    # Chart data for service requests by service
    request_counts = db.session.query(
        Service.name, func.count(ServiceRequest.id)
    ).join(ServiceRequest, ServiceRequest.service_id == Service.id)\
     .group_by(Service.name).all()
    
    chart_labels = [r[0] for r in request_counts]
    chart_data = [r[1] for r in request_counts]

    # Professional ratings for chart
    rated_pros = ServiceProfessional.query.filter(
        ServiceProfessional.rating.isnot(None),
        ServiceProfessional.status == 'approved'
    ).all()
    rating_labels = [p.name for p in rated_pros]
    rating_data = [round(p.rating, 1) for p in rated_pros]

    return render_template('admin_dashboard.html',
                           services=services_all,
                           pending_professionals=pending_professionals,
                           approved_professionals=approved_professionals,
                           service_requests=service_requests_all,
                           all_customers=all_customers,
                           search_query=search_query,
                           total_services=total_services,
                           total_customers=total_customers,
                           total_professionals=total_professionals,
                           total_requests=total_requests,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           rating_labels=rating_labels,
                           rating_data=rating_data)

# ─── Customer Dashboard ───────────────────────────────────
@main.route('/user/dashboard')
@login_required
def user_dashboard():
    if not isinstance(current_user, User):
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('main.home'))

    search_query = request.args.get('search', '').strip()
    pincode_query = request.args.get('pincode', '').strip()

    services_query = Service.query
    if search_query:
        services_query = services_query.filter(
            Service.name.ilike(f'%{search_query}%') |
            Service.description.ilike(f'%{search_query}%')
        )

    services = services_query.all()
    service_requests = ServiceRequest.query.filter_by(user_id=current_user.id)\
        .order_by(ServiceRequest.date_requested.desc()).all()

    return render_template('user_dashboard.html',
                           search_query=search_query,
                           services=services,
                           service_requests=service_requests)

# ─── Professional Dashboard ───────────────────────────────
@main.route('/serviceprofessional/dashboard', endpoint='professional_dashboard')
@login_required
def dashboard():
    if session.get('role') != 'service_professional':
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('main.home'))

    prof = current_user

    # Pending requests matching this professional's service type
    todays_services = db.session.query(ServiceRequest, Service, User) \
        .join(Service, ServiceRequest.service_id == Service.id) \
        .join(User, ServiceRequest.user_id == User.id) \
        .filter(ServiceRequest.status == 'pending') \
        .filter(Service.name == prof.service_type) \
        .all()

    # Accepted by this professional
    accepted_services = db.session.query(ServiceRequest, Service, User) \
        .join(Service, ServiceRequest.service_id == Service.id) \
        .join(User, ServiceRequest.user_id == User.id) \
        .filter(ServiceRequest.service_professional_id == prof.id) \
        .filter(ServiceRequest.status == 'accepted') \
        .all()

    # Closed/completed by this professional
    closed_services = db.session.query(ServiceRequest, Service, User) \
        .join(Service, ServiceRequest.service_id == Service.id) \
        .join(User, ServiceRequest.user_id == User.id) \
        .filter(ServiceRequest.service_professional_id == prof.id) \
        .filter(ServiceRequest.status.in_(['closed', 'completed'])) \
        .all()

    return render_template('professional_dashboard.html',
                           todays_services=todays_services,
                           accepted_services=accepted_services,
                           closed_services=closed_services,
                           professional=prof)

# ─── Service Management (Admin) ───────────────────────────
@main.route('/admin/service/manage', methods=['GET', 'POST'])
@main.route('/admin/service/manage/<int:service_id>', methods=['GET', 'POST'])
@login_required
def service_manage(service_id=None):
    if session.get('role') != 'admin':
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        service_name = request.form.get('service_name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '').strip()
        time_required = request.form.get('time_required', '').strip()

        if not all([service_name, description, price]):
            flash('Service name, description and price are required.', 'danger')
            return redirect(url_for('main.service_manage', service_id=service_id))

        if service_id:
            service = Service.query.get(service_id)
            if service:
                service.name = service_name
                service.description = description
                service.price = float(price)
                service.time_required = time_required
                db.session.commit()
                flash('Service updated successfully!', 'success')
            else:
                flash("Service not found!", "danger")
        else:
            new_service = Service(
                name=service_name,
                description=description,
                price=float(price),
                time_required=time_required
            )
            db.session.add(new_service)
            db.session.commit()
            flash('New service added successfully!', 'success')

        return redirect(url_for('main.admin_dashboard'))

    services = Service.query.all()
    service = None
    if service_id:
        service = Service.query.get(service_id)

    return render_template('service_manage.html', service=service, services=services)

# ─── Delete Service (Admin) ───────────────────────────────
@main.route('/admin/service/delete/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    if session.get('role') != 'admin':
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('main.home'))

    service = Service.query.get(service_id)
    if service:
        # Delete associated service requests first
        ServiceRequest.query.filter_by(service_id=service_id).delete()
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully!', 'success')
    else:
        flash('Service not found!', 'danger')

    return redirect(url_for('main.service_manage'))

# ─── User Profile ─────────────────────────────────────────
@main.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    user = current_user
    if request.method == 'POST':
        user.name = request.form.get('name', '').strip()
        user.phone = request.form.get('phone', '').strip()
        user.address = request.form.get('address', '').strip()
        user.pincode = request.form.get('pincode', '').strip()

        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception:
            db.session.rollback()
            flash("An error occurred. Please try again.", "danger")

        return redirect(url_for('main.user_profile'))

    return render_template('user_profile.html', user=user)

# ─── Professional Profile ─────────────────────────────────
@main.route('/professionalprofile', methods=['GET', 'POST'])
@login_required
def edit_professional_profile():
    professional_data = ServiceProfessional.query.get(current_user.id)

    if professional_data is None:
        flash('No professional profile found.', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        professional_data.name = request.form.get('name', professional_data.name).strip()
        professional_data.username = request.form.get('username', professional_data.username).strip()
        professional_data.phone = request.form.get('phone', professional_data.phone).strip()
        professional_data.experience = request.form.get('experience', professional_data.experience)
        professional_data.address = request.form.get('address', professional_data.address).strip()
        professional_data.pincode = request.form.get('pincode', professional_data.pincode).strip()
        professional_data.description = request.form.get('description', professional_data.description or '').strip()

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.edit_professional_profile'))

    return render_template('professional_profile.html', professional=professional_data)

# ─── Approve/Reject Professional (Admin) ──────────────────
@main.route('/admin/approve/professional/<int:professional_id>', methods=['POST'])
@login_required
def approve_professional(professional_id):
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    professional = ServiceProfessional.query.get(professional_id)
    if professional:
        professional.status = 'approved'
        db.session.commit()
        flash(f'{professional.name} has been approved!', 'success')
    else:
        flash('Professional not found!', 'danger')

    return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/reject/professional/<int:professional_id>', methods=['POST'])
@login_required
def reject_professional(professional_id):
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    professional = ServiceProfessional.query.get_or_404(professional_id)
    professional.status = 'rejected'
    db.session.commit()

    flash(f'{professional.name} has been rejected.', 'info')
    return redirect(url_for('main.admin_dashboard'))

# ─── Block/Unblock Professional (Admin) ───────────────────
@main.route('/admin/block/professional/<int:professional_id>', methods=['POST'])
@login_required
def block_professional(professional_id):
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    prof = ServiceProfessional.query.get_or_404(professional_id)
    prof.status = 'blocked'
    db.session.commit()
    flash(f'{prof.name} has been blocked.', 'warning')
    return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/unblock/professional/<int:professional_id>', methods=['POST'])
@login_required
def unblock_professional(professional_id):
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    prof = ServiceProfessional.query.get_or_404(professional_id)
    prof.status = 'approved'
    db.session.commit()
    flash(f'{prof.name} has been unblocked.', 'success')
    return redirect(url_for('main.view_blocked_professionals'))

# ─── Block/Unblock Customer (Admin) ───────────────────────
@main.route('/admin/block/user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    user = User.query.get_or_404(user_id)
    user.blocked = True
    db.session.commit()
    flash(f'{user.name} has been blocked.', 'warning')
    return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/unblock/user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    user = User.query.get_or_404(user_id)
    user.blocked = False
    db.session.commit()
    flash(f'{user.name} has been unblocked.', 'success')
    return redirect(url_for('main.admin_dashboard'))

# ─── Blocked Professionals View ───────────────────────────
@main.route('/admin/blocked_professionals')
@login_required
def view_blocked_professionals():
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    blocked_professionals = ServiceProfessional.query.filter_by(status='blocked').all()
    return render_template('blocked_professionals.html', blocked_professionals=blocked_professionals)

# ─── Services List ─────────────────────────────────────────
@main.route('/services', methods=['POST', 'GET'])
def services():
    services = Service.query.all()
    return render_template('services.html', services=services)

# ─── Booking ──────────────────────────────────────────────
@main.route('/booking/<int:service_id>', methods=['POST', 'GET'])
@login_required
def booking(service_id):
    if not isinstance(current_user, User):
        flash('Only customers can book services.', 'danger')
        return redirect(url_for('main.home'))

    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        remarks = request.form.get('remarks', '').strip()
        req = ServiceRequest(user=current_user.id, serv=service_id, remarks=remarks)
        db.session.add(req)
        db.session.commit()
        flash('Service booked successfully!', 'success')
        return redirect(url_for('main.user_dashboard'))

    return render_template('booking.html', service=service)

# ─── Accept/Reject Service Request (Professional) ─────────
@main.route('/serviceprofessional/accept_service/<int:service_request_id>', methods=['POST'])
@login_required
def accept_service(service_request_id):
    if session.get('role') != 'service_professional':
        return redirect(url_for('main.home'))

    service_request = ServiceRequest.query.get(service_request_id)
    if not service_request:
        flash("Service request not found.", "danger")
        return redirect(url_for('main.professional_dashboard'))

    if service_request.service_professional_id is not None:
        flash("This service request has already been accepted.", "warning")
        return redirect(url_for('main.professional_dashboard'))

    service_request.service_professional_id = current_user.id
    service_request.status = 'accepted'
    service_request.date_accepted = datetime.now()
    db.session.commit()

    flash(f"Service request #{service_request_id} has been accepted.", "success")
    return redirect(url_for('main.professional_dashboard'))

@main.route('/serviceprofessional/reject_service/<int:service_request_id>', methods=['POST'])
@login_required
def reject_service(service_request_id):
    if session.get('role') != 'service_professional':
        return redirect(url_for('main.home'))

    service_request = ServiceRequest.query.get(service_request_id)
    if not service_request:
        flash("Service request not found.", "danger")
        return redirect(url_for('main.professional_dashboard'))

    service_request.status = 'rejected'
    db.session.commit()

    flash(f"Service request #{service_request_id} has been rejected.", "info")
    return redirect(url_for('main.professional_dashboard'))

# ─── Close Service Request (Customer) ─────────────────────
@main.route('/close_service/<int:request_id>', methods=['POST'])
@login_required
def close_service(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)

    if service_request.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.user_dashboard'))

    service_request.status = 'closed'
    service_request.date_completed = datetime.now()
    db.session.commit()

    return redirect(url_for('main.submit_rating', service_request_id=request_id))

# ─── Submit Rating (Customer) ─────────────────────────────
@main.route('/submit_rating/<int:service_request_id>', methods=['GET', 'POST'])
@login_required
def submit_rating(service_request_id):
    service_request = ServiceRequest.query.get_or_404(service_request_id)

    if service_request.user_id != current_user.id:
        flash('You are not authorized to rate this service request.', 'danger')
        return redirect(url_for('main.user_dashboard'))

    if request.method == 'POST':
        rating = request.form.get('rating')
        review = request.form.get('review', '').strip()

        try:
            rating_int = int(rating)
            if not (1 <= rating_int <= 5):
                raise ValueError
        except (ValueError, TypeError):
            flash('Please provide a rating between 1 and 5.', 'danger')
            return redirect(url_for('main.submit_rating', service_request_id=service_request.id))

        service_request.rating = rating_int
        service_request.review = review
        service_request.status = 'completed'

        if service_request.service_professional_id:
            ServiceProfessional.update_professional_rating(service_request.service_professional_id)

        try:
            db.session.commit()
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('main.user_dashboard'))
        except Exception:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('main.submit_rating', service_request_id=service_request.id))

    return render_template('rating.html', service_request=service_request)

# ─── Edit Service Request (Customer) ──────────────────────
@main.route('/edit_request/<int:request_id>', methods=['GET', 'POST'])
@login_required
def edit_request(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)

    if service_request.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.user_dashboard'))

    if service_request.status not in ['pending']:
        flash('Only pending requests can be edited.', 'warning')
        return redirect(url_for('main.user_dashboard'))

    if request.method == 'POST':
        service_request.remarks = request.form.get('remarks', '').strip()
        db.session.commit()
        flash('Service request updated.', 'success')
        return redirect(url_for('main.user_dashboard'))

    return render_template('edit_request.html', service_request=service_request)

# ─── Summary / Charts (Admin) ─────────────────────────────
@main.route('/summary')
@login_required
def summary():
    if session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.home'))

    total_services = Service.query.count()
    total_customers = User.query.count()
    total_professionals = ServiceProfessional.query.count()
    total_requests = ServiceRequest.query.count()

    # Service request count by service
    request_counts = db.session.query(
        Service.name, func.count(ServiceRequest.id)
    ).join(ServiceRequest, ServiceRequest.service_id == Service.id)\
     .group_by(Service.name).all()

    chart_labels = [r[0] for r in request_counts]
    chart_data = [r[1] for r in request_counts]

    # Status distribution
    status_counts = db.session.query(
        ServiceRequest.status, func.count(ServiceRequest.id)
    ).group_by(ServiceRequest.status).all()

    status_labels = [s[0].capitalize() for s in status_counts]
    status_data = [s[1] for s in status_counts]

    # Professional ratings
    rated_pros = ServiceProfessional.query.filter(
        ServiceProfessional.rating.isnot(None),
        ServiceProfessional.status == 'approved'
    ).all()
    rating_labels = [p.name for p in rated_pros]
    rating_data = [round(p.rating, 1) for p in rated_pros]

    return render_template('summary.html',
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           status_labels=status_labels,
                           status_data=status_data,
                           rating_labels=rating_labels,
                           rating_data=rating_data,
                           total_services=total_services,
                           total_customers=total_customers,
                           total_professionals=total_professionals,
                           total_requests=total_requests)

# ─── Search API (JSON) ────────────────────────────────────
@main.route('/api/search', methods=['GET'])
@login_required
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'services': [], 'professionals': []})

    services = Service.query.filter(
        Service.name.ilike(f'%{query}%') |
        Service.description.ilike(f'%{query}%')
    ).all()

    professionals = ServiceProfessional.query.filter(
        ServiceProfessional.name.ilike(f'%{query}%') |
        ServiceProfessional.service_type.ilike(f'%{query}%')
    ).filter(ServiceProfessional.status == 'approved').all()

    return jsonify({
        'services': [{
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'price': s.price,
            'time_required': s.time_required
        } for s in services],
        'professionals': [{
            'id': p.id,
            'name': p.name,
            'service_type': p.service_type,
            'rating': p.rating,
            'experience': p.experience
        } for p in professionals]
    })