from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app.extensions import db
from sqlalchemy import func

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = UserRole[request.form['role']]
        
        if User.query.filter(func.lower(User.username) == username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter(func.lower(User.email) == email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('auth.register'))
        
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', UserRole=UserRole)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()  # Strip whitespace and convert to lowercase
        password = request.form['password']
        user = User.query.filter(func.lower(User.username) == username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('main.home'))

@bp.route('/change_email', methods=['POST'])
@login_required
def change_email():
    new_email = request.form.get('new_email')
    if User.query.filter_by(email=new_email).first():
        flash('Email already exists', 'error')
    else:
        current_user.email = new_email
        db.session.commit()
        flash('Email updated successfully', 'success')
    return redirect(url_for('user.user_settings'))

@bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    if current_user.check_password(current_password):
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password updated successfully', 'success')
    else:
        flash('Current password is incorrect', 'error')
    return redirect(url_for('user.user_settings'))

@bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    password_confirm = request.form.get('password_confirm')
    if current_user.check_password(password_confirm):
        # Delete user's dogs and associated images
        for dog in current_user.dogs:
            db.session.delete(dog)
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        flash('Your account has been deleted', 'success')
        return redirect(url_for('main.home'))
    else:
        flash('Password is incorrect', 'error')
    return redirect(url_for('user.user_settings'))