from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from app.models import Dog, Litter, VetAppointment, Message, DogStatus
from app.extensions import db
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def user_dashboard():
    # Fetch required data
    total_dogs = Dog.query.filter_by(user_id=current_user.id).count()
    total_litters = Litter.query.filter_by(user_id=current_user.id).count()
    
    # Recent dogs
    recent_dogs = Dog.query.filter_by(user_id=current_user.id).order_by(Dog.created_at.desc()).limit(5).all()
    
    # Recent litters
    recent_litters = Litter.query.filter_by(user_id=current_user.id).order_by(Litter.date_of_birth.desc()).limit(5).all()
    
    # Upcoming vet appointments
    upcoming_appointments = VetAppointment.query.join(Dog).filter(
        Dog.user_id == current_user.id,
        VetAppointment.date >= datetime.utcnow()
    ).order_by(VetAppointment.date).limit(5).all()
    
    # Unread messages count
    unread_messages_count = Message.query.filter_by(recipient_id=current_user.id, read=False).count()
    
    # Dog status distribution
    dog_status_distribution = db.session.query(
        Dog.status, func.count(Dog.id)
    ).filter_by(user_id=current_user.id).group_by(Dog.status).all()
    
    # Account usage
    public_dogs_count = Dog.query.filter_by(user_id=current_user.id, is_public=True).count()
    public_litters_count = Litter.query.filter_by(user_id=current_user.id, is_public=True).count()
    dog_limit = current_user.get_dog_limit()
    litter_limit = current_user.get_litter_limit()
    
    account_limits = {
        'dogs': 'Unlimited' if dog_limit == float('inf') else dog_limit,
        'litters': 'Unlimited' if litter_limit == float('inf') else litter_limit
    }

    
    # Profile completion
    profile_completion = calculate_profile_completion(current_user)
    
    return render_template('dashboard/user_dashboard.html',
                           total_dogs=total_dogs,
                           total_litters=total_litters,
                           recent_dogs=recent_dogs,
                           recent_litters=recent_litters,
                           upcoming_appointments=upcoming_appointments,
                           unread_messages_count=unread_messages_count,
                           dog_status_distribution=dog_status_distribution,
                           public_dogs_count=public_dogs_count,
                           public_litters_count=public_litters_count,
                           account_limits=account_limits,
                           profile_completion=profile_completion)

def calculate_profile_completion(user):
    fields = ['full_name', 'location', 'phone_number', 'bio', 'website']
    filled_fields = sum(1 for field in fields if getattr(user, field))
    return (filled_fields / len(fields)) * 100