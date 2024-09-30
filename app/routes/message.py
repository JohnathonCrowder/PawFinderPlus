from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.models import User, Message
from app.extensions import db, socketio
from datetime import datetime
from sqlalchemy import or_, and_
from flask_socketio import emit, join_room, leave_room

bp = Blueprint('message', __name__)


@bp.route('/messages')
@login_required
def messages():
    conversations = db.session.query(
        Message.conversation_id,
        db.func.max(Message.timestamp).label('last_message_time')
    ).filter(
        or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
    ).group_by(Message.conversation_id).all()

    conversation_details = []
    for conv in conversations:
        last_message = Message.query.filter_by(conversation_id=conv.conversation_id).order_by(Message.timestamp.desc()).first()
        other_user_id = last_message.recipient_id if last_message.sender_id == current_user.id else last_message.sender_id
        other_user = User.query.get(other_user_id)
        
        unread_count = Message.query.filter_by(
            conversation_id=conv.conversation_id,
            recipient_id=current_user.id,
            read=False
        ).count()
        
        conversation_details.append({
            'conversation_id': conv.conversation_id,
            'other_user': other_user,
            'last_message': last_message,
            'last_message_time': conv.last_message_time,
            'unread_count': unread_count
        })
    
    conversation_details.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    return render_template('messages/messages.html', conversations=conversation_details)

@bp.route('/messages/<conversation_id>')
@login_required
def get_conversation_messages(conversation_id):
    last_message_id = request.args.get('last_id', 0, type=int)
    messages = Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.id > last_message_id
    ).order_by(Message.timestamp.asc()).all()
    
    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat() + 'Z',  # Add 'Z' to indicate UTC
        'is_sender': msg.sender_id == current_user.id,
        'sender_name': msg.sender.username,
        'read': msg.read
    } for msg in messages]
    
    # Mark messages as read
    Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.recipient_id == current_user.id,
        Message.read == False
    ).update({Message.read: True})
    db.session.commit()
    
    return jsonify(messages_data)

@bp.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.json
    conversation_id = data['conversation_id']
    recipient_id = data['recipient_id']
    content = data['content']

    new_message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
        timestamp=datetime.utcnow()  # Ensure UTC timestamp
    )
    db.session.add(new_message)
    db.session.commit()

    # Emit the new message via WebSocket
    socketio.emit('new_message', {
        'conversation_id': conversation_id,
        'message': {
            'id': new_message.id,
            'content': new_message.content,
            'timestamp': new_message.timestamp.isoformat() + 'Z',  # Add 'Z' to indicate UTC
            'sender_name': current_user.username,
            'is_sender': False
        }
    }, room=f"user_{recipient_id}")

    return jsonify({
        'status': 'success',
        'message': {
            'id': new_message.id,
            'content': new_message.content,
            'timestamp': new_message.timestamp.isoformat() + 'Z',  # Add 'Z' to indicate UTC
            'is_sender': True,
            'sender_name': current_user.username,
            'read': False
        }
    })

@bp.route('/messages/search', methods=['POST'])
@login_required
def search_conversations():
    search_term = request.json.get('search_term', '').lower()
    
    conversations = db.session.query(
        Message.conversation_id,
        db.func.max(Message.timestamp).label('last_message_time')
    ).filter(
        or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
    ).group_by(Message.conversation_id).all()
    
    search_results = []
    for conv in conversations:
        last_message = Message.query.filter_by(conversation_id=conv.conversation_id).order_by(Message.timestamp.desc()).first()
        other_user_id = last_message.recipient_id if last_message.sender_id == current_user.id else last_message.sender_id
        other_user = User.query.get(other_user_id)
        
        if (search_term in other_user.username.lower() or 
            search_term in last_message.content.lower()):
            search_results.append({
                'conversation_id': conv.conversation_id,
                'other_user': {
                    'id': other_user.id,
                    'username': other_user.username
                },
                'last_message': {
                    'content': last_message.content,
                    'timestamp': last_message.timestamp.isoformat()
                }
            })
    
    return jsonify(search_results)

@bp.route('/messages/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    conversation_id = request.json.get('conversation_id')
    Message.query.filter_by(
        conversation_id=conversation_id,
        recipient_id=current_user.id,
        read=False
    ).update({Message.read: True})
    db.session.commit()
    return jsonify({'status': 'success'})

@bp.route('/messages/delete', methods=['POST'])
@login_required
def delete_message():
    message_id = request.json.get('message_id')
    message = Message.query.get_or_404(message_id)
    
    if message.sender_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    db.session.delete(message)
    db.session.commit()
    return jsonify({'status': 'success'})

# WebSocket event handlers
@socketio.on('connect')
@login_required
def handle_connect():
    join_room(f"user_{current_user.id}")

@socketio.on('disconnect')
@login_required
def handle_disconnect():
    leave_room(f"user_{current_user.id}")

@socketio.on('typing')
def handle_typing(data):
    recipient_id = data['recipient_id']
    conversation_id = data['conversation_id']
    emit('user_typing', {
        'user_id': current_user.id,
        'conversation_id': conversation_id
    }, room=f"user_{recipient_id}")

@socketio.on('stop_typing')
def handle_stop_typing(data):
    recipient_id = data['recipient_id']
    conversation_id = data['conversation_id']
    emit('user_stop_typing', {
        'user_id': current_user.id,
        'conversation_id': conversation_id
    }, room=f"user_{recipient_id}")

# Utility functions
def get_or_create_conversation(user1_id, user2_id):
    conversation_id = f"{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"
    return conversation_id