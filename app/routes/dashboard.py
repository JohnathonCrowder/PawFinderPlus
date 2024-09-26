from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from app.models import Dog, Litter, VetAppointment, Message, DogStatus
from app.extensions import db
from sqlalchemy import func, case
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def user_dashboard():
    # Key statistics
    total_dogs = Dog.query.filter_by(user_id=current_user.id).count()
    total_litters = Litter.query.filter_by(user_id=current_user.id).count()
    
    # Dog status distribution
    dog_status_distribution = db.session.query(
        Dog.status, func.count(Dog.id)
    ).filter_by(user_id=current_user.id).group_by(Dog.status).all()
    
    # Age distribution of dogs
    current_date = datetime.now().date()
    age_distribution = db.session.query(
        case(
            (current_date - Dog.date_of_birth < timedelta(days=365), 'Puppy'),
            (current_date - Dog.date_of_birth < timedelta(days=365*7), 'Adult'),
            else_='Senior'
        ).label('age_group'),
        func.count(Dog.id)
    ).filter_by(user_id=current_user.id).group_by('age_group').all()
    
    # Litter size distribution
    subquery = db.session.query(
        Litter.id,
        func.count(Dog.id).label('puppy_count')
    ).join(Litter.puppies)\
     .filter(Litter.user_id == current_user.id)\
     .group_by(Litter.id)\
     .subquery()

    litter_size_distribution = db.session.query(
        subquery.c.puppy_count.label('litter_size'),
        func.count(subquery.c.id).label('count')
    ).group_by('litter_size').all()
    
    # Upcoming appointments
    upcoming_appointments = VetAppointment.query.join(Dog).filter(
        Dog.user_id == current_user.id,
        VetAppointment.date >= datetime.utcnow()
    ).order_by(VetAppointment.date).limit(5).all()
    
    # Recent litters
    recent_litters = Litter.query.filter_by(user_id=current_user.id).order_by(Litter.date_of_birth.desc()).limit(5).all()

    return render_template('dashboard/user_dashboard.html',
                           total_dogs=total_dogs,
                           total_litters=total_litters,
                           dog_status_distribution=dog_status_distribution,
                           age_distribution=age_distribution,
                           litter_size_distribution=litter_size_distribution,
                           upcoming_appointments=upcoming_appointments,
                           recent_litters=recent_litters,
                           DogStatus=DogStatus)