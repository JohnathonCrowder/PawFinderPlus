from flask import Blueprint, render_template, current_app, jsonify, request
from flask_login import login_required, current_user
from app.models import User, Dog, Litter, VetAppointment, Message, DogStatus, AppointmentCategory, BlogPost, UserRole
from app.extensions import db
from sqlalchemy import func, or_, extract, distinct, case
from datetime import datetime, timedelta
from itertools import chain
from sqlalchemy.orm import joinedload


bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def user_dashboard():
    if current_user.role == UserRole.SELLER:
        return seller_dashboard()
    else:
        return buyer_dashboard()

def seller_dashboard():
    total_dogs = Dog.query.filter_by(user_id=current_user.id).count()
    total_litters = Litter.query.filter_by(user_id=current_user.id).count()
    
    dog_status_distribution = db.session.query(
        Dog.status, func.count(Dog.id)
    ).filter_by(user_id=current_user.id).group_by(Dog.status).all()
    
    current_date = datetime.now().date()
    age_distribution = db.session.query(
        case(
            (current_date - Dog.date_of_birth < timedelta(days=365), 'Puppy'),
            (current_date - Dog.date_of_birth < timedelta(days=365*7), 'Adult'),
            else_='Senior'
        ).label('age_group'),
        func.count(Dog.id)
    ).filter_by(user_id=current_user.id).group_by('age_group').all()
    
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
    
    upcoming_appointments = VetAppointment.query.join(Dog).filter(
        Dog.user_id == current_user.id,
        VetAppointment.date >= datetime.utcnow()
    ).order_by(VetAppointment.date).limit(5).all()

    followed_users = [user.id for user in current_user.followed]
    recent_dogs = Dog.query.filter(Dog.user_id.in_(followed_users), Dog.is_public == True).order_by(Dog.created_at.desc()).limit(10).all()
    recent_litters = Litter.query.filter(Litter.user_id.in_(followed_users), Litter.is_public == True).order_by(Litter.date_of_birth.desc()).limit(10).all()
    recent_posts = BlogPost.query.filter(BlogPost.author_id.in_(followed_users), BlogPost.is_published == True).order_by(BlogPost.created_at.desc()).limit(10).all()

    feed_items = sorted(
        chain(
            ((dog, 'dog') for dog in recent_dogs),
            ((litter, 'litter') for litter in recent_litters),
            ((post, 'blog_post') for post in recent_posts)
        ),
        key=lambda x: get_datetime(x[0]),
        reverse=True
    )
    
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

    user_breeds = db.session.query(Dog.breed).filter(Dog.user_id == current_user.id).distinct().all()
    user_breeds = [breed[0] for breed in user_breeds]

    similar_breeders = db.session.query(User).join(Dog).filter(
        User.id != current_user.id,
        Dog.breed.in_(user_breeds)
    ).group_by(User.id).order_by(func.count(Dog.id).desc()).limit(5).all()

    for breeder in similar_breeders:
        breeder.dogs = Dog.query.filter_by(user_id=breeder.id).all()
        breeder.litters = Litter.query.filter_by(user_id=breeder.id).all()
        breeder.follower_count = breeder.followers.count()

    return render_template('dashboard/user_dashboard.html',
                           total_dogs=total_dogs,
                           total_litters=total_litters,
                           dog_status_distribution=dog_status_distribution,
                           age_distribution=age_distribution,
                           litter_size_distribution=litter_size_distribution,
                           upcoming_appointments=upcoming_appointments,
                           AppointmentCategory=AppointmentCategory,
                           conversation_details=conversation_details,
                           DogStatus=DogStatus,
                           feed_items=feed_items,
                           user_breeds=user_breeds,
                           similar_breeders=similar_breeders,
                           get_recent_activity=get_recent_activity)

@login_required
def buyer_dashboard():
    # Recent Litters
    recent_litters = Litter.query.filter_by(is_public=True).order_by(Litter.date_of_birth.desc()).limit(6).all()
    
    # Available Puppies
    available_puppies = Dog.query.filter(
        Dog.is_public == True,
        Dog.status.in_([DogStatus.AVAILABLE_NOW, DogStatus.AVAILABLE_SOON])
    ).options(
        joinedload(Dog.owner),  # Ensure owner info is eagerly loaded
        joinedload(Dog.images)  # Eagerly load images to avoid N+1 queries
    ).order_by(Dog.created_at.desc()).limit(10).all()
    
    # Available Breeds
    available_breeds = db.session.query(Dog.breed).filter(
        Dog.is_public == True, 
        Dog.status.in_([DogStatus.AVAILABLE_NOW, DogStatus.AVAILABLE_SOON])
    ).distinct().order_by(Dog.breed).all()
    available_breeds = [breed[0] for breed in available_breeds]

    # User's conversations
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

    # Upcoming Appointments
    upcoming_appointments = VetAppointment.query.join(Dog).filter(
        Dog.user_id == current_user.id,
        VetAppointment.date >= datetime.utcnow()
    ).order_by(VetAppointment.date).limit(5).all()

    # User Breeds (for similar breeders section)
    user_breeds = db.session.query(Dog.breed).filter(Dog.user_id == current_user.id).distinct().all()
    user_breeds = [breed[0] for breed in user_breeds]

    # Similar Breeders
    similar_breeders = db.session.query(User).join(Dog).filter(
        User.id != current_user.id,
        Dog.breed.in_(user_breeds)
    ).group_by(User.id).order_by(func.count(Dog.id).desc()).limit(5).all()

    for breeder in similar_breeders:
        breeder.dogs = Dog.query.filter_by(user_id=breeder.id).all()
        breeder.litters = Litter.query.filter_by(user_id=breeder.id).all()
        breeder.follower_count = breeder.followers.count()

    def get_recent_activity(user, limit=5):
        recent_activity = []
        
        recent_dogs = Dog.query.filter_by(user_id=user.id).order_by(Dog.created_at.desc()).limit(limit).all()
        for dog in recent_dogs:
            recent_activity.append({
                'type': 'dog',
                'text': f'Added new dog: {dog.name}',
                'date': dog.created_at,
                'icon': 'fas fa-dog'
            })
        
        recent_litters = Litter.query.filter_by(user_id=user.id).order_by(Litter.date_of_birth.desc()).limit(limit).all()
        for litter in recent_litters:
            recent_activity.append({
                'type': 'litter',
                'text': f'New litter born: {litter.name}',
                'date': datetime.combine(litter.date_of_birth, datetime.min.time()),
                'icon': 'fas fa-paw'
            })
        
        recent_activity.sort(key=lambda x: x['date'], reverse=True)
        
        return recent_activity[:limit]

    return render_template('dashboard/buyer_dashboard.html',
                           recent_litters=recent_litters,
                           available_puppies=available_puppies,
                           available_breeds=available_breeds,
                           conversation_details=conversation_details,
                           upcoming_appointments=upcoming_appointments,
                           user_breeds=user_breeds,
                           similar_breeders=similar_breeders,
                           get_recent_activity=get_recent_activity,
                           DogStatus=DogStatus,
                           AppointmentCategory=AppointmentCategory,
                           datetime=datetime)

@bp.route('/dashboard/messages/<conversation_id>')
@login_required
def get_conversation_messages(conversation_id):
    last_id = request.args.get('last_id', 0, type=int)
    messages = Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.id > last_id
    ).order_by(Message.timestamp.asc()).all()
    
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

def get_datetime(item):
    if hasattr(item, 'created_at'):
        return item.created_at
    elif hasattr(item, 'date_of_birth'):
        return datetime.combine(item.date_of_birth, datetime.min.time())
    else:
        return datetime.min
    
def get_recent_activity(user, limit=5):
    recent_activity = []
    
    recent_dogs = Dog.query.filter_by(user_id=user.id).order_by(Dog.created_at.desc()).limit(limit).all()
    for dog in recent_dogs:
        recent_activity.append({
            'type': 'dog',
            'text': f'Added new dog: {dog.name}',
            'date': dog.created_at,
            'icon': 'fas fa-dog'
        })
    
    recent_litters = Litter.query.filter_by(user_id=user.id).order_by(Litter.date_of_birth.desc()).limit(limit).all()
    for litter in recent_litters:
        recent_activity.append({
            'type': 'litter',
            'text': f'New litter born: {litter.name}',
            'date': datetime.combine(litter.date_of_birth, datetime.min.time()),
            'icon': 'fas fa-paw'
        })
    
    recent_activity.sort(key=lambda x: x['date'], reverse=True)
    
    return recent_activity[:limit]