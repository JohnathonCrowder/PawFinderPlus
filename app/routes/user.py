from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from app.models import User, Dog, Litter, DogStatus, AccountType
from app.extensions import db
from app.utils import format_url, generate_shareable_link, generate_social_links
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime

bp = Blueprint('user', __name__)

@bp.route('/user_settings')
@login_required
def user_settings():
    user_data = {
        'full_name': current_user.full_name or '',
        'location': current_user.location or '',
        'phone_number': current_user.phone_number or '',
        'bio': current_user.bio or '',
        'has_profile_picture': current_user.profile_picture_data is not None,
        'website': current_user.website or '',
        'facebook': current_user.facebook or '',
        'instagram': current_user.instagram or '',
        'address': current_user.address,
        'city': current_user.city,
        'state': current_user.state,
        'country': current_user.country,
        'account_type': current_user.account_type,  
    }
    followed = current_user.followed.all()
    return render_template('user_settings.html', user_data=user_data, AccountType=AccountType, followed=followed)

@bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename:
            current_user.profile_picture_data = file.read()
            current_user.profile_picture_filename = secure_filename(file.filename)
            current_user.profile_picture_mimetype = file.mimetype

    current_user.full_name = request.form.get('full_name', '').strip() or None
    current_user.location = request.form.get('location', '').strip() or None
    current_user.phone_number = request.form.get('phone_number', '').strip() or None
    current_user.bio = request.form.get('bio', '').strip() or None
    

    current_user.address = request.form.get('address')
    current_user.city = request.form.get('city')
    current_user.state = request.form.get('state')
    current_user.country = request.form.get('country')
    current_user.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
    current_user.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None

    current_user.website = format_url(request.form.get('website', '').strip()) or None
    current_user.facebook = format_url(request.form.get('facebook', '').strip()) or None
    current_user.instagram = format_url(request.form.get('instagram', '').strip()) or None

    # Note: We're not changing the account_type here

    db.session.commit()

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('user.user_settings'))

@bp.route('/profile_picture/<int:user_id>')
def get_profile_picture(user_id):
    user = User.query.get_or_404(user_id)
    if user.profile_picture_data:
        return send_file(
            BytesIO(user.profile_picture_data),
            mimetype=user.profile_picture_mimetype,
            as_attachment=False,
            download_name=user.profile_picture_filename
        )
    else:
        # Return a default image or 404
        return send_file('path/to/default/profile/image.png', mimetype='image/png')

@bp.route('/remove_profile_picture', methods=['POST'])
@login_required
def remove_profile_picture():
    current_user.profile_picture_data = None
    current_user.profile_picture_filename = None
    current_user.profile_picture_mimetype = None
    db.session.commit()
    flash('Profile picture removed successfully.', 'success')
    return redirect(url_for('user.user_settings'))

@bp.route('/profile/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    is_own_profile = current_user.is_authenticated and current_user.id == user.id

    if is_own_profile:
        dogs = Dog.query.filter_by(user_id=user.id).all()
        litters = Litter.query.filter_by(user_id=user.id).all()
    else:
        dogs = Dog.query.filter_by(user_id=user.id, is_public=True).all()
        litters = Litter.query.filter_by(user_id=user.id, is_public=True).all()

    total_dogs = len(dogs) if is_own_profile else len([dog for dog in dogs if dog.is_public])
    total_litters = len(litters)
    dog_breeds = list(set(dog.breed for dog in dogs if is_own_profile or dog.is_public))

    user_data = {
        'address': user.address,
        'city': user.city,
        'state': user.state,
        'country': user.country
    }

    shareable_link = generate_shareable_link('user.user_profile', username=username)
    social_links = generate_social_links(shareable_link, f"Check out {user.username}'s profile on DogBreederPlus!")
   
                           

    return render_template('user_profile.html', 
                           user=user, 
                           dogs=dogs,
                           litters=litters,
                           total_dogs=total_dogs, 
                           total_litters=total_litters,
                           dog_breeds=dog_breeds,
                           is_own_profile=is_own_profile,
                           DogStatus=DogStatus,
                           user_data=user_data,
                           shareable_link=shareable_link, 
                           social_links=social_links,
                           followers_count=user.followers_count,
                           following_count=user.following_count)




####################   Changing Followers Code    #########################


@bp.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    if user_to_follow == current_user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'You cannot follow yourself'}), 400
        else:
            flash('You cannot follow yourself', 'error')
            return redirect(url_for('user.user_profile', username=user_to_follow.username))

    current_user.follow(user_to_follow)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'message': f'You are now following {user_to_follow.username}',
            'followers_count': user_to_follow.followers_count,
            'following_count': current_user.following_count
        })
    else:
        flash(f'You are now following {user_to_follow.username}', 'success')
        return redirect(url_for('user.user_profile', username=user_to_follow.username))

@bp.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    user_to_unfollow = User.query.get_or_404(user_id)
    if user_to_unfollow == current_user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'You cannot unfollow yourself'}), 400
        else:
            flash('You cannot unfollow yourself', 'error')
            return redirect(url_for('user.user_profile', username=user_to_unfollow.username))

    current_user.unfollow(user_to_unfollow)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'message': f'You have unfollowed {user_to_unfollow.username}',
            'followers_count': user_to_unfollow.followers_count,
            'following_count': current_user.following_count
        })
    else:
        flash(f'You have unfollowed {user_to_unfollow.username}', 'success')
        return redirect(url_for('user.user_profile', username=user_to_unfollow.username))




####################   Changing Account Types    ##########################

@bp.route('/account_management')
@login_required
def account_management():
    user_data = {
        'account_type': current_user.account_type,
        # Add other user data as needed
    }
    return render_template('account_management.html', user_data=user_data, AccountType=AccountType)

@bp.route('/change_account_type', methods=['POST'])
@login_required
def change_account_type():
    new_type = request.form.get('account_type')
    if new_type in AccountType.__members__:
        old_type = current_user.account_type
        new_account_type = AccountType[new_type]
        
        dogs_affected = 0
        litters_affected = 0
        
        if old_type == AccountType.PREMIUM and new_account_type == AccountType.BASIC:
            dogs_affected, litters_affected = current_user.switch_to_basic_account()
        elif new_account_type == AccountType.FREE:
            dogs_affected, litters_affected = current_user.switch_to_free_account()
        else:
            current_user.account_type = new_account_type
            db.session.commit()
        
        flash(f'Account type changed to {new_type}', 'success')
        
        if dogs_affected > 0 or litters_affected > 0:
            flash(f'{dogs_affected} dogs and {litters_affected} litters were set to private due to the account downgrade.', 'info')
    else:
        flash('Invalid account type', 'error')
    
    return redirect(url_for('user.account_management'))