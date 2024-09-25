from flask import Blueprint, render_template, request   
from flask_login import current_user
from app.models import Litter, BlogPost, DogStatus, User, Dog, AccountType
from sqlalchemy import or_, func
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
    search = request.args.get('search', '')
    breed = request.args.get('breed', '')
    location = request.args.get('location', '')
    show_free = request.args.get('show_free', 'false') == 'true'

    query = User.query

    if not show_free:
        query = query.filter(User.account_type.in_([AccountType.BASIC, AccountType.PREMIUM]))

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

    query = query.options(
        db.joinedload(User.dogs),
        db.joinedload(User.litters)
    )

    page = request.args.get('page', 1, type=int)
    breeders = query.paginate(page=page, per_page=20, error_out=False)

    breeder_info = {}
    for breeder in breeders.items:
        breeder_info[breeder.id] = {
            'breeds': list(set(dog.breed for dog in breeder.dogs)),
            'followers_count': breeder.followers.count(),
            'dogs_count': len(breeder.dogs),
            'litters_count': len(breeder.litters),
            'available_dogs_count': sum(1 for dog in breeder.dogs if dog.status in [DogStatus.AVAILABLE_NOW, DogStatus.AVAILABLE_SOON])
        }

    breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
    breeds = [breed[0] for breed in breeds]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/breeder_results.html', 
                               breeders=breeders, 
                               breeder_info=breeder_info,
                               show_free=show_free, 
                               AccountType=AccountType)
    
    return render_template('breeder_network.html', 
                           breeders=breeders, 
                           breeder_info=breeder_info,
                           breeds=breeds, 
                           show_free=show_free, 
                           AccountType=AccountType)

@bp.route('/breeder-quick-view/<int:breeder_id>')
def breeder_quick_view(breeder_id):
    breeder = User.query.options(
        db.joinedload(User.dogs),
        db.joinedload(User.litters)
    ).get_or_404(breeder_id)

    breeder_info = {
        'breeds': list(set(dog.breed for dog in breeder.dogs)),
        'followers_count': breeder.followers.count(),
        'dogs_count': len(breeder.dogs),
        'litters_count': len(breeder.litters),
        'available_dogs_count': sum(1 for dog in breeder.dogs if dog.status in [DogStatus.AVAILABLE_NOW, DogStatus.AVAILABLE_SOON])
    }

    return render_template('partials/breeder_quick_view.html', 
                           breeder=breeder, 
                           breeder_info=breeder_info,
                           AccountType=AccountType)