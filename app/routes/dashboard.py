from flask import Blueprint, render_template, current_app, jsonify, request
from flask_login import login_required, current_user
from app.models import Dog, Litter, VetAppointment, Message, DogStatus, AppointmentCategory, User
from app.extensions import db
from sqlalchemy import func, case, or_
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
    
    # Get user's conversations
    conversations = db.session.query(
        Message.conversation_id,
        func.max(Message.timestamp).label('last_message_time'),
        func.count(Message.id).filter(Message.read == False, Message.recipient_id == current_user.id).label('unread_count')
    ).filter(
        or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
    ).group_by(Message.conversation_id).order_by(func.max(Message.timestamp).desc()).limit(10).all()

    conversation_details = []
    for conv in conversations:
        last_message = Message.query.filter_by(conversation_id=conv.conversation_id).order_by(Message.timestamp.desc()).first()
        other_user_id = last_message.recipient_id if last_message.sender_id == current_user.id else last_message.sender_id
        other_user = User.query.get(other_user_id)
        
        conversation_details.append({
            'conversation_id': conv.conversation_id,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': conv.unread_count
        })

    return render_template('dashboard/user_dashboard.html',
                           total_dogs=total_dogs,
                           total_litters=total_litters,
                           dog_status_distribution=dog_status_distribution,
                           age_distribution=age_distribution,
                           litter_size_distribution=litter_size_distribution,
                           upcoming_appointments=upcoming_appointments,
                           AppointmentCategory=AppointmentCategory,
                           conversation_details=conversation_details,
                           DogStatus=DogStatus)


@bp.route('/dashboard/messages/<conversation_id>')
@login_required
def get_conversation_messages(conversation_id):
    last_id = request.args.get('last_id', 0, type=int)
    messages = Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.id > last_id
    ).order_by(Message.timestamp.asc()).all()
    
    # Mark messages as read
    for message in messages:
        if message.recipient_id == current_user.id and not message.read:
            message.read = True
    db.session.commit()

    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_sender': msg.sender_id == current_user.id
    } for msg in messages]
    return jsonify(messages_data)

@bp.route('/dashboard/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    new_message = Message(
        conversation_id=data['conversation_id'],
        sender_id=current_user.id,
        recipient_id=data['recipient_id'],
        content=data['content'],
        timestamp=datetime.utcnow()
    )
    db.session.add(new_message)
    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': {
            'id': new_message.id,
            'content': new_message.content,
            'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_sender': True
        }
    })

@bp.route('/dashboard/check_new_messages')
@login_required
def check_new_messages():
    last_check = request.args.get('last_check', type=float)
    last_id = request.args.get('last_id', 0, type=int)
    last_check_datetime = datetime.fromtimestamp(last_check)
    
    new_messages = Message.query.filter(
        Message.recipient_id == current_user.id,
        Message.timestamp > last_check_datetime,
        Message.id > last_id
    ).all()

    new_message_data = [{
        'id': msg.id,
        'conversation_id': msg.conversation_id,
        'sender_id': msg.sender_id,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in new_messages]

    return jsonify(new_message_data)