from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Dog, VetAppointment, AppointmentCategory
from app.extensions import db
from datetime import datetime, timedelta

bp = Blueprint('vet', __name__)

@bp.route('/vet_appointments')
@login_required
def vet_appointments():
    user_dogs = Dog.query.filter_by(user_id=current_user.id).all()
    
    filter_type = request.args.get('filter', 'upcoming')
    category_filter = request.args.get('category')
    
    base_query = VetAppointment.query.join(Dog).filter(Dog.user_id == current_user.id)
    
    now = datetime.utcnow()
    if filter_type == 'upcoming':
        base_query = base_query.filter(VetAppointment.date >= now)
    elif filter_type == 'past':
        base_query = base_query.filter(VetAppointment.date < now)
    elif filter_type == 'this_week':
        week_end = now + timedelta(days=7)
        base_query = base_query.filter(VetAppointment.date.between(now, week_end))
    elif filter_type == 'this_month':
        month_end = now + timedelta(days=30)
        base_query = base_query.filter(VetAppointment.date.between(now, month_end))

    if category_filter:
        try:
            category_enum = AppointmentCategory[category_filter.upper()]
            base_query = base_query.filter(VetAppointment.category == category_enum)
        except KeyError:
            flash(f"Invalid category filter: {category_filter}", "error")
    
    appointments = base_query.order_by(VetAppointment.date).all()
    
    return render_template('vet_appointments.html', 
                           user_dogs=user_dogs, 
                           appointments=appointments, 
                           now=now, 
                           filter_type=filter_type, 
                           category_filter=category_filter,
                           categories=AppointmentCategory)

@bp.route('/dog/<int:dog_id>/appointments')
@login_required
def dog_appointments(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    if dog.user_id != current_user.id:
        flash('You do not have permission to view this dog\'s appointments.', 'error')
        return redirect(url_for('dog.dog_management'))
    
    selected_category = request.args.get('category', 'all')
    
    appointments_query = VetAppointment.query.filter_by(dog_id=dog_id)
    
    if selected_category != 'all':
        appointments_query = appointments_query.filter(VetAppointment.category == AppointmentCategory[selected_category])
    
    appointments = appointments_query.order_by(VetAppointment.date).all()
    
    now = datetime.utcnow()
    return render_template('dog_appointments.html', 
                           dog=dog, 
                           appointments=appointments, 
                           now=now,
                           categories=AppointmentCategory,
                           selected_category=selected_category)

@bp.route('/add_appointment', methods=['GET', 'POST'])
@login_required
def add_appointment():
    if request.method == 'POST':
        dog_id = request.form['dog_id']
        date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        category = AppointmentCategory[request.form['category']]
        description = request.form['description']
        veterinarian = request.form['veterinarian']
        location = request.form['location']
        
        new_appointment = VetAppointment(
            dog_id=dog_id,
            date=date,
            category=category,
            description=description,
            veterinarian=veterinarian,
            location=location
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        flash('Appointment added successfully!', 'success')
        return redirect(url_for('vet.dog_appointments', dog_id=dog_id))
    
    dogs = Dog.query.filter_by(user_id=current_user.id).all()
    return render_template('add_appointment.html', dogs=dogs, categories=AppointmentCategory)

@bp.route('/appointment/<int:appointment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_appointment(appointment_id):
    appointment = VetAppointment.query.get_or_404(appointment_id)
    if appointment.dog.user_id != current_user.id:
        flash('You do not have permission to edit this appointment.', 'error')
        return redirect(url_for('vet_appointments'))
    
    if request.method == 'POST':
        appointment.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        appointment.category = AppointmentCategory[request.form['category']]
        appointment.description = request.form['description']
        appointment.veterinarian = request.form['veterinarian']
        appointment.location = request.form['location']
        appointment.completed = 'completed' in request.form
        db.session.commit()
        flash('Appointment updated successfully!', 'success')
        return redirect(url_for('vet.dog_appointments', dog_id=appointment.dog_id))
    
    return render_template('edit_appointment.html', appointment=appointment, categories=AppointmentCategory)

@bp.route('/appointment/<int:appointment_id>/delete', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    appointment = VetAppointment.query.get_or_404(appointment_id)
    if appointment.dog.user_id != current_user.id:
        flash('You do not have permission to delete this appointment.', 'error')
        return redirect(url_for('vet_appointments'))
    
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment deleted successfully!', 'success')
    return redirect(url_for('vet.dog_appointments', dog_id=appointment.dog_id))