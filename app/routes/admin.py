from flask import Blueprint, render_template, abort, request, jsonify
from flask_login import login_required, current_user
from app.models import User, Dog, Litter, VetAppointment, AccountType, DogStatus,AppointmentCategory
from app.extensions import db
from sqlalchemy import func, or_, extract
from datetime import datetime, timedelta


bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)  # Forbidden
    
    total_users = User.query.count()
    total_dogs = Dog.query.count()
    total_litters = Litter.query.count()
    total_appointments = VetAppointment.query.count()

    # User registration data for the last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    user_registrations = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= seven_days_ago).group_by(func.date(User.created_at)).all()

    user_registration_dates = [str(reg.date) for reg in user_registrations]
    user_registration_counts = [reg.count for reg in user_registrations]

    # Dog breeds distribution
    dog_breed_data = db.session.query(Dog.breed, func.count(Dog.id)).group_by(Dog.breed).order_by(func.count(Dog.id).desc()).limit(5).all()
    dog_breeds = [breed for breed, _ in dog_breed_data]
    dog_breed_counts = [count for _, count in dog_breed_data]

    # Recent activity (you'll need to implement an Activity model to track user actions)
    # If you haven't implemented the Activity model yet, you can comment out or remove this line
    # recent_activities = Activity.query.order_by(Activity.date.desc()).limit(10).all()

    return render_template('admin/dashboard.html', 
                           total_users=total_users,
                           total_dogs=total_dogs,
                           total_litters=total_litters,
                           total_appointments=total_appointments,
                           user_registration_dates=user_registration_dates,
                           user_registration_counts=user_registration_counts,
                           dog_breeds=dog_breeds,
                           dog_breed_counts=dog_breed_counts)
                           # recent_activities=recent_activities)  # Uncomment this line when you implement the Activity model

@bp.route('/users')
@login_required
def user_management():
    if not current_user.is_admin:
        abort(403)

    # Get filter parameters from request
    account_type = request.args.get('account_type')
    is_admin = request.args.get('is_admin')
    search = request.args.get('search', '')

    # Start with base query
    query = User.query

    # Apply filters
    if account_type:
        query = query.filter(User.account_type == AccountType[account_type])
    
    if is_admin:
        query = query.filter(User.is_admin == (is_admin.lower() == 'true'))

    if search:
        query = query.filter(User.username.ilike(f'%{search}%') | User.email.ilike(f'%{search}%'))

    # Execute query
    users = query.all()

    # Get data for graphs
    total_users = User.query.count()
    users_by_account_type = db.session.query(User.account_type, func.count(User.id)).group_by(User.account_type).all()
    
    # Users registered in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users_last_30_days = User.query.filter(User.created_at >= thirty_days_ago).count()
    
    # Users with dogs
    users_with_dogs = db.session.query(func.count(func.distinct(Dog.user_id))).scalar()
    
    # Average dogs per user
    total_dogs = Dog.query.count()
    if total_users > 0:
        avg_dogs_per_user = total_dogs / total_users
    else:
        avg_dogs_per_user = 0
    
    # User registration over time (last 12 months)
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    user_growth = db.session.query(
        extract('year', User.created_at).label('year'),
        extract('month', User.created_at).label('month'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= twelve_months_ago)\
     .group_by('year', 'month')\
     .order_by('year', 'month')\
     .all()

    # Format user_growth data for the template
    user_growth_formatted = [
        {
            'date': datetime(year=int(year), month=int(month), day=1).strftime('%B %Y'),
            'count': count
        }
        for year, month, count in user_growth
    ]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/partials/user_list.html', 
                               users=users,
                               AccountType=AccountType)
    else:
        return render_template('admin/user_management.html', 
                               users=users, 
                               AccountType=AccountType,
                               current_account_type=account_type,
                               current_is_admin=is_admin,
                               search=search,
                               total_users=total_users,
                               users_by_account_type=users_by_account_type,
                               new_users_last_30_days=new_users_last_30_days,
                               users_with_dogs=users_with_dogs,
                               avg_dogs_per_user=avg_dogs_per_user,
                               user_growth=user_growth_formatted)
    
    
@bp.route('/dogs')
@login_required
def dog_management():
    if not current_user.is_admin:
        abort(403)

    # Get filter parameters from request
    breed = request.args.get('breed')
    status = request.args.get('status')
    search = request.args.get('search', '')

    # Start with base query
    query = Dog.query

    # Apply filters
    if breed:
        query = query.filter(Dog.breed == breed)
    
    if status:
        query = query.filter(Dog.status == DogStatus[status])

    if search:
        query = query.filter(Dog.name.ilike(f'%{search}%'))

    # Execute query
    dogs = query.all()

    # Get unique breeds for filter options
    breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
    breeds = [breed[0] for breed in breeds if breed[0]]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/partials/dog_list.html', 
                               dogs=dogs,
                               DogStatus=DogStatus)
    else:
        return render_template('admin/dog_management.html', 
                               dogs=dogs, 
                               breeds=breeds,
                               DogStatus=DogStatus,
                               current_breed=breed,
                               current_status=status,
                               search=search)

@bp.route('/litters')
@login_required
def litter_management():
    if not current_user.is_admin:
        abort(403)

    # Get filter parameters from request
    breed = request.args.get('breed')
    age = request.args.get('age')
    search = request.args.get('search', '')

    # Start with base query
    query = Litter.query

    # Apply filters
    if breed:
        query = query.filter(or_(Litter.father.has(breed=breed), Litter.mother.has(breed=breed)))
    
    if age:
        today = datetime.utcnow().date()
        if age == '0-8 weeks':
            date_limit = today - timedelta(weeks=8)
            query = query.filter(Litter.date_of_birth >= date_limit)
        elif age == '8-16 weeks':
            start_date = today - timedelta(weeks=16)
            end_date = today - timedelta(weeks=8)
            query = query.filter(Litter.date_of_birth.between(start_date, end_date))
        elif age == '16+ weeks':
            date_limit = today - timedelta(weeks=16)
            query = query.filter(Litter.date_of_birth <= date_limit)

    if search:
        query = query.filter(or_(
            Litter.name.ilike(f'%{search}%'),
            Litter.father.has(Dog.name.ilike(f'%{search}%')),
            Litter.mother.has(Dog.name.ilike(f'%{search}%'))
        ))

    # Execute query
    litters = query.all()

    # Get unique breeds for filter options
    breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
    breeds = [breed[0] for breed in breeds if breed[0]]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/partials/litter_list.html', 
                               litters=litters)
    else:
        return render_template('admin/litter_management.html', 
                               litters=litters, 
                               breeds=breeds,
                               current_breed=breed,
                               current_age=age,
                               search=search)

@bp.route('/appointments')
@login_required
def appointment_management():
    if not current_user.is_admin:
        abort(403)

    # Get filter parameters from request
    status = request.args.get('status')
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search', '')

    # Start with base query
    query = VetAppointment.query

    # Apply filters
    now = datetime.utcnow()
    if status == 'upcoming':
        query = query.filter(VetAppointment.date >= now)
    elif status == 'past':
        query = query.filter(VetAppointment.date < now)
    elif status == 'completed':
        query = query.filter(VetAppointment.completed == True)

    if category:
        query = query.filter(VetAppointment.category == AppointmentCategory[category])

    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(VetAppointment.date >= start_date)

    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(VetAppointment.date <= end_date)

    if search:
        query = query.join(Dog).join(User).filter(or_(
            Dog.name.ilike(f'%{search}%'),
            User.username.ilike(f'%{search}%'),
            VetAppointment.veterinarian.ilike(f'%{search}%')
        ))

    # Execute query
    appointments = query.order_by(VetAppointment.date).all()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/partials/appointment_list.html', 
                               appointments=appointments,
                               now=now)
    else:
        return render_template('admin/appointment_management.html', 
                               appointments=appointments,
                               AppointmentCategory=AppointmentCategory,
                               now=now,
                               current_status=status,
                               current_category=category,
                               current_start_date=start_date,
                               current_end_date=end_date,
                               search=search)



@bp.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403

@bp.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404


@bp.route('/dogs/<int:dog_id>/delete', methods=['POST'])
@login_required
def delete_dog(dog_id):
    if not current_user.is_admin:
        abort(403)
    dog = Dog.query.get_or_404(dog_id)
    db.session.delete(dog)
    db.session.commit()
    flash(f'Dog {dog.name} has been deleted.', 'success')
    return redirect(url_for('admin.dog_management'))


@bp.route('/litters/<int:litter_id>/delete', methods=['POST'])
@login_required
def delete_litter(litter_id):
    if not current_user.is_admin:
        abort(403)
    litter = Litter.query.get_or_404(litter_id)
    db.session.delete(litter)
    db.session.commit()
    flash(f'Litter {litter.name} has been deleted.', 'success')
    return redirect(url_for('admin.litter_management'))

@bp.route('/appointments/<int:appointment_id>/delete', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    if not current_user.is_admin:
        abort(403)
    appointment = VetAppointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash(f'Appointment for {appointment.dog.name} has been deleted.', 'success')
    return redirect(url_for('admin.appointment_management'))