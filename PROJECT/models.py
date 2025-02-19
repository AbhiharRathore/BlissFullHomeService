from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Integer, default=0)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Integer, default=1)
    blocked = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create_user(name, username, phone, address, pincode, password):
        new_user = User(
            name=name,
            username=username,
            phone=phone,
            address=address,
            pincode=pincode,
            password=password
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user

class ServiceProfessional(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    service_type = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(255))
    pincode = db.Column(db.String(10))
    status = db.Column(db.String(20), default='pending')
    role = db.Column(db.Integer, default=2)
    rating = db.Column(db.Float, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)

    @staticmethod
    def update_professional_rating(professional_id):
        service_requests = ServiceRequest.query.filter(ServiceRequest.service_professional_id == professional_id, ServiceRequest.rating.isnot(None)).all()
        
        if service_requests:
            total_rating = sum([int(sr.rating) if sr.rating and isinstance(sr.rating, (int, float, str)) and str(sr.rating).isdigit() else 0 for sr in service_requests])

            avg_rating = total_rating / len(service_requests)
            
            professional = ServiceProfessional.query.get(professional_id)
            professional.rating = avg_rating
            db.session.commit()

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def date_created(self):
        return self.created_at.strftime('%Y-%m-%d') if self.created_at else 'N/A'

    @staticmethod
    def create_service(service_name, description, price):
        new_service = Service(
            name=service_name,
            description=description,
            price=price
        )
        db.session.add(new_service)
        db.session.commit()
        return new_service

    @staticmethod
    def update_service(service_id, service_name, description, price):
        service = Service.query.get(service_id)
        if service:
            service.name = service_name
            service.description = description
            service.price = price
            db.session.commit()
            return True
        return False

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    service_professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id'), default=None)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    date_requested = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    date_accepted = db.Column(db.DateTime, nullable=True)
    date_completed = db.Column(db.DateTime, nullable=True)
    rating = db.Column(db.Integer)
    review = db.Column(db.Text, nullable=True)
    remarks = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref='service_history')
    service = db.relationship('Service', backref='service_history')
    professional = db.relationship('ServiceProfessional', backref='service_requests')

    def __init__(self, user, serv, remarks=None):
        self.user_id = user
        self.service_id = serv
        self.service_professional_id = None
        self.status = 'pending'
        self.date_accepted = None
        self.date_completed = None
        self.date_requested = datetime.utcnow()
        self.remarks = remarks
    
    def accept(self, pro):
        self.service_professional_id = pro
        self.status = 'accepted'
        self.date_accepted = datetime.utcnow()

    def close(self, rating):
        self.status = 'closed'
        self.date_completed = datetime.utcnow()
        self.rating = rating
        if self.service_professional_id:
            ServiceProfessional.update_professional_rating(self.service_professional_id)
