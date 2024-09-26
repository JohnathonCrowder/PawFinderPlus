from flask import render_template
from app.extensions import db  # Import the db object directly


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Use the imported db object
        return render_template('errors/500.html'), 500