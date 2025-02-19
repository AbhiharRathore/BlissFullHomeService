"""Seed demo data for the application."""
from PROJECT.models import db, User, ServiceProfessional, Service, ServiceRequest


def seed_demo_data():
    """Create demo data if the database is empty."""
    # Only seed if no services exist (first run)
    if Service.query.first():
        return

    # Create demo services
    services = [
        Service(name='Electrician', description='Professional electrical repairs, wiring, and installations for your home.', price=200, time_required=60),
        Service(name='Salon', description='Professional haircuts, shaving, facials, and makeup services at home.', price=300, time_required=90),
        Service(name='Plumbing', description='Expert plumbing services including pipe repair, fitting, and maintenance.', price=250, time_required=60),
        Service(name='Cleaning', description='Thorough home cleaning services including deep cleaning and sanitization.', price=150, time_required=120),
        Service(name='AC Repair', description='Air conditioner servicing, repair, gas refilling, and installation.', price=400, time_required=90),
    ]
    for s in services:
        db.session.add(s)
    db.session.commit()

    # Create demo customers
    customers = []
    customer_data = [
        ('Rahul Sharma', 'rahul', '9876543210', '12 MG Road, Sector 5', '110001', 'pass123'),
        ('Priya Patel', 'priya', '9876543211', '45 Lakeview Colony', '400001', 'pass123'),
        ('Amit Kumar', 'amit', '9876543212', '78 Gandhi Nagar', '560001', 'pass123'),
    ]
    for name, username, phone, address, pincode, pwd in customer_data:
        u = User.create_user(name, username, phone, address, pincode, pwd)
        customers.append(u)

    # Create demo professionals
    pro_data = [
        ('Suresh Electricals', 'suresh', 'pass123', '9988776655', 'Electrician', 5, '23 Industrial Area', '110002', 'approved'),
        ('Meena Beauty', 'meena', 'pass123', '9988776656', 'Salon', 3, '56 Market Road', '400002', 'approved'),
        ('Rajesh Plumbing', 'rajesh', 'pass123', '9988776657', 'Plumbing', 7, '89 Workshop Lane', '560002', 'pending'),
        ('Kavita Cleaners', 'kavita', 'pass123', '9988776658', 'Cleaning', 2, '34 Service Road', '110003', 'approved'),
    ]
    for name, username, pwd, phone, stype, exp, addr, pin, status in pro_data:
        pro = ServiceProfessional(
            name=name, username=username, phone=phone,
            service_type=stype, experience=exp,
            address=addr, pincode=pin, status=status
        )
        pro.set_password(pwd)
        db.session.add(pro)
    db.session.commit()

    # Create demo service requests
    electrician = Service.query.filter_by(name='Electrician').first()
    salon = Service.query.filter_by(name='Salon').first()
    suresh = ServiceProfessional.query.filter_by(username='suresh').first()
    meena = ServiceProfessional.query.filter_by(username='meena').first()

    # A completed request
    sr1 = ServiceRequest(user_id=customers[0].id, service_id=electrician.id)
    sr1.accept(suresh.id)
    sr1.close(rating=4, review='Great work, very professional!')
    db.session.add(sr1)

    # An accepted request
    sr2 = ServiceRequest(user_id=customers[1].id, service_id=salon.id)
    sr2.accept(meena.id)
    db.session.add(sr2)

    # A pending request
    sr3 = ServiceRequest(user_id=customers[2].id, service_id=electrician.id)
    db.session.add(sr3)

    db.session.commit()

    # Update professional ratings
    ServiceProfessional.update_professional_rating(suresh.id)
