from flask import Flask, session, redirect, url_for, request, flash, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, current_user
from datetime import timedelta
import os
import logging
from PROJECT.models import Admin, User, ServiceProfessional, db

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
    login_manager.login_view = 'auth.user_login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        role = session.get('role')

        if role == 'admin':
            return Admin.query.get(int(user_id))
        elif role == 'service_professional':
            return ServiceProfessional.query.get(int(user_id))
        elif role == 'user':
            return User.query.get(int(user_id))
        return None

    # Custom error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Register Blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Database Initialization
    with app.app_context():
        try:
            db.create_all()

            # Seed admin if no admin exists
            if not Admin.query.first():
                dummy_admin = Admin(username='admin', role=0)
                dummy_admin.set_password('admin123')
                db.session.add(dummy_admin)
                db.session.commit()

            # Seed demo data if no services exist
            from PROJECT.seed import seed_demo_data
            seed_demo_data()

        except Exception as e:
            logging.error(f"Error during app setup: {e}")

    return app
