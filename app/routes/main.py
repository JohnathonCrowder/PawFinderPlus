from flask import Blueprint, render_template
from flask_login import current_user


bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return render_template('index.html')

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/contact')
def contact():
    return render_template('contact.html')

@bp.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')