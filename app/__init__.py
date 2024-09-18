from flask import Flask
from .extensions import db
from .config import Config
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_login import LoginManager
from .routes import init_app as init_routes

migrate = Migrate()
socketio = SocketIO()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)

    # Set up login manager
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User  # Import here to avoid circular imports
        return User.query.get(int(user_id))

    # Register blueprints
    init_routes(app)

    # Register error handlers
    from . import error_handlers
    error_handlers.register_error_handlers(app)

    return app