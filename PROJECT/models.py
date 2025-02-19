from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Integer, default=0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Integer, default=1)
    is_blocked = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create_user(name, username, phone, address, pincode, password):
        new_user = User(
            name=name,
            username=username,
            phone=phone,
            address=address,
            pincode=pincode,
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return new_user


class ServiceProfessional(UserMixin, db.Model):
    __tablename__ = 'service_professional'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    service_type = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(255))
    pincode = db.Column(db.String(10))
    status = db.Column(db.String(20), default='pending')
    role = db.Column(db.Integer, default=2)
    rating = db.Column(db.Float, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def update_professional_rating(professional_id):
        service_requests = ServiceRequest.query.filter(
            ServiceRequest.service_professional_id == professional_id,
            ServiceRequest.rating.isnot(None)
        ).all()

        if service_requests:
            total_rating = 0
            count = 0
            for sr in service_requests:
                try:
                    val = int(sr.rating)
                    if 1 <= val <= 5:
                        total_rating += val
                        count += 1
                except (ValueError, TypeError):
                    continue

            if count > 0:
                avg_rating = round(total_rating / count, 1)
                professional = ServiceProfessional.query.get(professional_id)
                if professional:
                    professional.rating = avg_rating
                    db.session.commit()


class Service(db.Model):
    __tablename__ = 'service'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.Integer, default=60)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create_service(service_name, description, price, time_required=60):
        new_service = Service(
            name=service_name,
            description=description,
            price=price,
            time_required=time_required
        )
        db.session.add(new_service)
        db.session.commit()
        return new_service

    @staticmethod
    def update_service(service_id, service_name, description, price, time_required=None):
        service = Service.query.get(service_id)
        if service:
            service.name = service_name
            service.description = description
            service.price = price
            if time_required is not None:
                service.time_required = time_required
            db.session.commit()
            return True
        return False


class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    service_professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id'), nullable=True)
    date_requested = db.Column(db.DateTime, default=datetime.utcnow)
    date_of_service = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending')
    date_accepted = db.Column(db.DateTime, nullable=True)
    date_completed = db.Column(db.DateTime, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    review = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref='service_history')
    service = db.relationship('Service', backref='service_requests')
    professional = db.relationship('ServiceProfessional', backref='assigned_requests')

    def __init__(self, user_id, service_id, date_of_service=None):
        self.user_id = user_id
        self.service_id = service_id
        self.service_professional_id = None
        self.status = 'pending'
        self.date_accepted = None
        self.date_completed = None
        self.date_requested = datetime.utcnow()
        self.date_of_service = date_of_service

    def accept(self, professional_id):
        self.service_professional_id = professional_id
        self.status = 'accepted'
        self.date_accepted = datetime.utcnow()

    def reject(self):
        self.status = 'rejected'

    def close(self, rating=None, review=None):
        self.status = 'closed'
        self.date_completed = datetime.utcnow()
        self.rating = rating
        self.review = review
        if self.service_professional_id and rating:
            ServiceProfessional.update_professional_rating(self.service_professional_id)
