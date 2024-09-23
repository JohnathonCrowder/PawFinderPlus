from flask import Blueprint, render_template
from flask_login import current_user
from app.models import Litter, BlogPost, DogStatus



bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    featured_litters = Litter.query.filter_by(is_public=True).order_by(Litter.date_of_birth.desc()).limit(6).all()
    recent_blog_posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
    return render_template('index.html', featured_litters=featured_litters, recent_blog_posts=recent_blog_posts)

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/contact')
def contact():
    return render_template('contact.html')

@bp.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@bp.route('/terms-of-service')
def terms_of_service():
    return render_template('terms_of_service.html')