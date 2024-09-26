from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import User, Message, Dog
from app.extensions import db
from sqlalchemy import or_, and_

bp = Blueprint('message', __name__)

@bp.route('/messages')
@login_required
def messages():
    conversations = db.session.query(
        Message.conversation_id,
        User.id.label('user_id'),  # Change this line
        User.username,
        db.func.max(Message.timestamp).label('last_message_time')
    ).join(
        User, 
        db.or_(Message.sender_id == User.id, Message.recipient_id == User.id)
    ).filter(
        db.and_(
            User.id != current_user.id,
            db.or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
        )
    ).group_by(
        Message.conversation_id, User.id, User.username
    ).order_by(
        db.desc('last_message_time')
    ).all()

    current_app.logger.info(f"Retrieved {len(conversations)} conversations for user {current_user.id}")

    return render_template('messages/messages.html', conversations=conversations)

@bp.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    other_user = User.query.get_or_404(user_id)
    
    # Create a unique conversation ID
    conversation_id = f"{min(current_user.id, user_id)}_{max(current_user.id, user_id)}"
    
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            new_message = Message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                recipient_id=user_id,
                content=content
            )
            db.session.add(new_message)
            db.session.commit()
        return redirect(url_for('message.conversation', user_id=user_id))
    
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    
    return render_template('messages/conversation.html', messages=messages, other_user=other_user)

@bp.route('/contact_owner/<int:dog_id>')
@login_required
def contact_owner(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    if dog.user_id == current_user.id:
        flash('You cannot contact yourself.', 'error')
        return redirect(url_for('dog.dog_profile', id=dog_id))

    conversation_id = f"{min(current_user.id, dog.user_id)}_{max(current_user.id, dog.user_id)}"

    existing_message = Message.query.filter_by(conversation_id=conversation_id).first()

    if existing_message:
        return redirect(url_for('message.conversation', user_id=dog.user_id))
    else:
        new_message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            recipient_id=dog.user_id,
            content=f"Hello, I'm interested in your dog {dog.name}."
        )
        db.session.add(new_message)
        db.session.commit()
        flash('Your message has been sent to the owner.', 'success')
        return redirect(url_for('message.conversation', user_id=dog.user_id))