from flask import Blueprint, render_template, abort, current_app, request
from flask_login import login_required, current_user
from app.models import User, Dog, Litter, VetAppointment
from app.extensions import db
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@login_required
def admin_dashboard():
    current_app.logger.info(f"Admin dashboard accessed by {current_user.username}")
    if not current_user.is_admin:
        current_app.logger.warning(f"Non-admin user {current_user.username} attempted to access admin dashboard")
        abort(403)  # Forbidden
    
    total_users = User.query.count()
    total_dogs = Dog.query.count()
    total_litters = Litter.query.count()
    total_appointments = VetAppointment.query.count()
    
    return render_template('admin/dashboard.html', 
                           total_users=total_users,
                           total_dogs=total_dogs,
                           total_litters=total_litters,
                           total_appointments=total_appointments)

@bp.route('/users')
@login_required
def user_management():
    if not current_user.is_admin:
        abort(403)
    users = User.query.all()
    return render_template('admin/user_management.html', users=users)

@bp.route('/dogs')
@login_required
def dog_management():
    if not current_user.is_admin:
        abort(403)
    dogs = Dog.query.all()
    return render_template('admin/dog_management.html', dogs=dogs)

@bp.route('/litters')
@login_required
def litter_management():
    if not current_user.is_admin:
        abort(403)
    litters = Litter.query.all()
    return render_template('admin/litter_management.html', litters=litters)

@bp.route('/appointments')
@login_required
def appointment_management():
    if not current_user.is_admin:
        abort(403)
    appointments = VetAppointment.query.all()
    now = datetime.utcnow()
    return render_template('admin/appointment_management.html', appointments=appointments, now=now)



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