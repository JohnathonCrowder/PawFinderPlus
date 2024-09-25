from flask import Blueprint, render_template, request   
from flask_login import current_user
from app.models import Litter, BlogPost, DogStatus, User, Dog
from sqlalchemy import or_
from app.extensions import db





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

@bp.route('/breeder-network')
def breeder_network():
    # Get query parameters
    search = request.args.get('search', '')
    breed = request.args.get('breed', '')
    location = request.args.get('location', '')

    # Base query
    query = User.query

    # Apply filters
    if search:
        query = query.filter(or_(
            User.username.ilike(f'%{search}%'),
            User.full_name.ilike(f'%{search}%')
        ))
    if breed:
        query = query.join(User.dogs).filter(Dog.breed == breed)
    if location:
        query = query.filter(or_(
            User.city.ilike(f'%{location}%'),
            User.state.ilike(f'%{location}%'),
            User.country.ilike(f'%{location}%')
        ))

    # Paginate results
    page = request.args.get('page', 1, type=int)
    breeders = query.paginate(page=page, per_page=20, error_out=False)

    # Get all unique breeds for the filter
    breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
    breeds = [breed[0] for breed in breeds]

    return render_template('breeder_network.html', breeders=breeders, breeds=breeds)