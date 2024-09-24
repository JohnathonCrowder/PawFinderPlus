from flask import Flask
from .extensions import db
from .config import Config
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .routes import init_app as init_routes
from flask.cli import with_appcontext
from .models import User
import click

migrate = Migrate()
socketio = SocketIO()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app) 

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

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

    @app.cli.command("make-admin")
    @click.argument("username")
    @with_appcontext
    def make_admin(username):
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_admin = True
            db.session.commit()
            click.echo(f"User {username} has been made an admin.")
        else:
            click.echo(f"User {username} not found.")

    return app