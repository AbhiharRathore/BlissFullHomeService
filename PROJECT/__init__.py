from flask import Flask, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, current_user
from datetime import timedelta
import os
import logging
from PROJECT.models import Admin, User, ServiceProfessional, Service, db

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    class Config:
        SECRET_KEY = os.getenv('SECRET_KEY', 'thisismykey')
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        role = session.get('role')
        
        if role == 'admin':
            return Admin.query.get(int(user_id))
        elif role == 'service_professional':
            prof = ServiceProfessional.query.get(int(user_id))
            if prof and prof.status == 'blocked':
                return None
            return prof
        elif role == 'user':
            user = User.query.get(int(user_id))
            if user and user.blocked:
                return None
            return user
        return None

    @login_manager.unauthorized_handler
    def unauthorized():
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('main.home'))

    @app.before_request
    def clear_stale_session():
        # If user is not authenticated (e.g. blocked/deleted and load_user returned None)
        # but session still has data, clear it to fix UI state
        if not current_user.is_authenticated and 'role' in session:
            session.clear()

    # Register Blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Database Initialization
    with app.app_context():
        try:
            db.create_all()

            # Seed admin if none exists
            if not Admin.query.first():
                dummy_admin = Admin(username='admin', password='admin123', role=0)
                db.session.add(dummy_admin)
                db.session.commit()

            # Seed sample services if none exist
            if not Service.query.first():
                sample_services = [
                    Service(name='AC Servicing', description='Complete AC maintenance including cleaning, gas refill and repair', price=500, time_required='2 hours'),
                    Service(name='Plumbing', description='Fix leaks, install fixtures, pipe repairs and bathroom fittings', price=300, time_required='1-2 hours'),
                    Service(name='Electrical', description='Wiring, switch repair, fan installation and electrical safety checks', price=400, time_required='1-3 hours'),
                    Service(name='House Cleaning', description='Deep cleaning of rooms, kitchen, bathroom and common areas', price=600, time_required='3-4 hours'),
                    Service(name='Salon at Home', description='Haircut, facial, manicure, pedicure and beauty treatments at your doorstep', price=800, time_required='1-2 hours'),
                    Service(name='Gardening', description='Lawn mowing, plant care, landscaping and garden maintenance', price=350, time_required='2-3 hours'),
                    Service(name='Pest Control', description='Termite treatment, cockroach control, mosquito fogging and rodent control', price=700, time_required='2-3 hours'),
                    Service(name='Painting', description='Interior and exterior wall painting, texture work and waterproofing', price=1500, time_required='1-2 days'),
                ]
                for s in sample_services:
                    db.session.add(s)
                db.session.commit()

        except Exception as e:
            logging.error(f"Error during app setup: {e}")

    return app
