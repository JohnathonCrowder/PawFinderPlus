from flask import Blueprint, render_template, abort, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import User, Dog, Litter, VetAppointment, AccountType, DogStatus,AppointmentCategory
from app.extensions import db
from sqlalchemy import func, or_, extract, distinct
from datetime import datetime, timedelta
from flask import render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from app.admin.backup import create_backup, restore_backup, list_backups
import os
import time


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

    # Get data for graphs and statistics
    total_dogs = Dog.query.count()
    dogs_by_status = db.session.query(Dog.status, func.count(Dog.id)).group_by(Dog.status).all()
    
    # Dogs added in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_dogs_last_30_days = Dog.query.filter(Dog.created_at >= thirty_days_ago).count()
    
    # Top 5 breeds
    top_breeds = db.session.query(Dog.breed, func.count(Dog.id).label('count')).\
        group_by(Dog.breed).\
        order_by(func.count(Dog.id).desc()).\
        limit(5).all()
    
    # Average age of dogs
    avg_age = db.session.query(func.avg(func.julianday('now') - func.julianday(Dog.date_of_birth)) / 365.25).scalar()
    
    # Dog registration over time (last 12 months)
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    dog_growth = db.session.query(
        func.strftime('%Y-%m', Dog.created_at).label('month'),
        func.count(Dog.id)
    ).filter(Dog.created_at >= twelve_months_ago).group_by('month').order_by('month').all()

    dog_growth_formatted = [
        {
            'date': datetime.strptime(month, '%Y-%m').strftime('%B %Y'),
            'count': count
        }
        for month, count in dog_growth
    ]

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
                               search=search,
                               total_dogs=total_dogs,
                               dogs_by_status=dogs_by_status,
                               new_dogs_last_30_days=new_dogs_last_30_days,
                               top_breeds=top_breeds,
                               avg_age=avg_age,
                               dog_growth=dog_growth_formatted)

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

    # Get data for graphs and statistics
    total_litters = Litter.query.count()
    
    # Count total puppies (dogs associated with litters)
    total_puppies = db.session.query(func.count(distinct(Dog.id))).\
        join(Litter.puppies).scalar() or 0
    
    # Litters added in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_litters_last_30_days = Litter.query.filter(Litter.date_of_birth >= thirty_days_ago).count()
    
    # Average puppies per litter
    avg_puppies_per_litter = db.session.query(
        func.avg(
            db.session.query(func.count(Dog.id))
            .join(Litter.puppies)
            .filter(Litter.id == Litter.id)
            .group_by(Litter.id)
            .correlate(Litter)
        )
    ).scalar() or 0

    # Round to 2 decimal places
    avg_puppies_per_litter = round(avg_puppies_per_litter, 2)
    
    # Top 5 breeds in litters
    top_breeds = db.session.query(Dog.breed, func.count(distinct(Litter.id)).label('count')).\
        join(Litter.puppies).\
        group_by(Dog.breed).\
        order_by(func.count(distinct(Litter.id)).desc()).\
        limit(5).all()
    
    # Litter registration over time (last 12 months)
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    litter_growth = db.session.query(
        func.strftime('%Y-%m', Litter.date_of_birth).label('month'),
        func.count(Litter.id)
    ).filter(Litter.date_of_birth >= twelve_months_ago).group_by('month').order_by('month').all()

    litter_growth_formatted = [
        {
            'date': datetime.strptime(month, '%Y-%m').strftime('%B %Y'),
            'count': count
        }
        for month, count in litter_growth
    ]

    # Litter size distribution
    litter_sizes = db.session.query(
        func.count(Dog.id).label('size'),
        func.count(func.distinct(Litter.id)).label('count')
    ).select_from(Litter).join(Litter.puppies).group_by(Litter.id).all()

    # Process the results to get the distribution
    size_distribution = {}
    for size, _ in litter_sizes:
        if size not in size_distribution:
            size_distribution[size] = 0
        size_distribution[size] += 1

    litter_sizes = sorted(size_distribution.items())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/partials/litter_list.html', 
                               litters=litters)
    else:
        return render_template('admin/litter_management.html', 
                           litters=litters, 
                           breeds=breeds,
                           current_breed=breed,
                           current_age=age,
                           search=search,
                           total_litters=total_litters,
                           total_puppies=total_puppies,
                           new_litters_last_30_days=new_litters_last_30_days,
                           avg_puppies_per_litter=avg_puppies_per_litter,
                           top_breeds=top_breeds,
                           litter_growth=litter_growth_formatted,
                           litter_sizes=litter_sizes)

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










#################    Database Backup Routes   ##############################




@bp.route('/backup', methods=['GET', 'POST'])
@login_required
def backup_restore():
    if not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        if 'create_backup' in request.form:
            backup_file = create_backup()
            flash('Backup created successfully', 'success')
        elif 'restore_backup' in request.form:
            if 'backup_file' not in request.files:
                flash('No file part', 'error')
            else:
                file = request.files['backup_file']
                if file.filename == '':
                    flash('No selected file', 'error')
                elif file:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['BACKUP_DIR'], filename)
                    file.save(file_path)
                    restore_backup(file_path)
                    os.remove(file_path)  # Remove the temporary file
                    flash('Backup restored successfully', 'success')

    backups = list_backups()
    return render_template('admin/backup_restore.html', backups=backups)

@bp.route('/database-management', methods=['GET', 'POST'])
@login_required
def database_management():
    if not current_user.is_admin:
        abort(403)  # Forbidden

    if request.method == 'POST':
        if 'create_backup' in request.form:
            try:
                backup_file = create_backup()
                flash(f'Backup created successfully: {os.path.basename(backup_file)}', 'success')
            except Exception as e:
                flash(f'Error creating backup: {str(e)}', 'error')
        elif 'restore_backup' in request.form:
            if 'backup_file' not in request.files:
                flash('No file part', 'error')
            else:
                file = request.files['backup_file']
                if file.filename == '':
                    flash('No selected file', 'error')
                elif file and file.filename.endswith('.zip'):
                    try:
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(current_app.config['BACKUP_DIR'], filename)
                        file.save(file_path)
                        restore_backup(file_path)
                        flash('Database restored successfully from backup', 'success')
                        
                        # Schedule file deletion
                        def delete_file(file_path, retries=5, delay=1):
                            for _ in range(retries):
                                try:
                                    os.remove(file_path)
                                    break
                                except PermissionError:
                                    time.sleep(delay)
                            else:
                                current_app.logger.warning(f"Could not delete file: {file_path}")

                        import threading
                        threading.Thread(target=delete_file, args=(file_path,)).start()

                        # Reconnect to the database
                        db.engine.dispose()
                        db.session.remove()
                        
                        # Redirect to force a new request and reconnection
                        return redirect(url_for('admin.database_management'))
                    except Exception as e:
                        flash(f'Error restoring backup: {str(e)}', 'error')
                else:
                    flash('Invalid file format. Please upload a zip file.', 'error')

    backups = list_backups()
    return render_template('admin/database_management.html', backups=backups)


@bp.route('/download-backup/<filename>')
@login_required
def download_backup(filename):
    if not current_user.is_admin:
        abort(403)  # Forbidden

    backup_path = os.path.join(current_app.config['BACKUP_DIR'], filename)
    if os.path.exists(backup_path):
        return send_file(backup_path, as_attachment=True)
    else:
        flash('Backup file not found', 'error')
        return redirect(url_for('admin.database_management'))

@bp.route('/delete-backup/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    if not current_user.is_admin:
        abort(403)  # Forbidden

    file_path = os.path.join(current_app.config['BACKUP_DIR'], filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            flash('Backup deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting backup: {str(e)}', 'error')
    else:
        flash('Backup file not found', 'error')

    return redirect(url_for('admin.database_management'))