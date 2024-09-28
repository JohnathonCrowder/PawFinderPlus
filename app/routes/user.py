from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app
from flask_login import login_required, current_user
from app.models import User, Dog, Litter, DogStatus, AccountType, BlogPost, UserRole
from app.extensions import db
from app.utils import format_url, generate_shareable_link, generate_social_links
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime, timedelta
from sqlalchemy import or_
from itertools import chain



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
        'role': current_user.role,  
    }
    followed = current_user.followed.all()
    return render_template('user/user_settings.html', user_data=user_data, AccountType=AccountType, UserRole=UserRole, followed=followed)

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
        return send_file('static\img\profile_photo_placeholder.png', mimetype='image/png')

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
   
                           

    return render_template('user/user_profile.html', 
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
    

####################   Follower Feed Route      ###########################        

@bp.route('/followed_feed')
@login_required
def followed_feed():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POSTS_PER_PAGE']
    
    # Get the IDs of users that the current user is following
    followed_users = [user.id for user in current_user.followed]
    
    # Set the time range for recent posts (e.g., last 30 days)
    recent_time = datetime.utcnow() - timedelta(days=30)
    
    # Fetch recent dogs
    dogs = Dog.query.filter(
        Dog.user_id.in_(followed_users),
        Dog.created_at > recent_time,
        Dog.is_public == True
    ).all()

    # Fetch recent litters
    litters = Litter.query.filter(
        Litter.user_id.in_(followed_users),
        Litter.date_of_birth > recent_time.date(),
        Litter.is_public == True
    ).all()

    # Fetch recent blog posts
    blog_posts = BlogPost.query.filter(
        BlogPost.author_id.in_(followed_users),
        BlogPost.created_at > recent_time,
        BlogPost.is_published == True
    ).all()

    # Combine all items
    all_items = list(chain(
        ((item, 'dog') for item in dogs),
        ((item, 'litter') for item in litters),
        ((item, 'blog_post') for item in blog_posts)
    ))

    # Define sorting key function
    def get_sort_key(item):
        obj, item_type = item
        if item_type == 'dog':
            return obj.created_at
        elif item_type == 'litter':
            return datetime.combine(obj.date_of_birth, datetime.min.time())
        elif item_type == 'blog_post':
            return obj.created_at
        else:
            return datetime.min

    # Sort combined items by date
    all_items.sort(key=get_sort_key, reverse=True)

    # Manual pagination
    total_items = len(all_items)
    start = (page - 1) * per_page
    end = start + per_page
    feed_items = all_items[start:end]

    # Create a pagination object
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total

        @property
        def pages(self):
            return (self.total + self.per_page - 1) // self.per_page

        @property
        def has_prev(self):
            return self.page > 1

        @property
        def has_next(self):
            return self.page < self.pages

        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = Pagination(feed_items, page, per_page, total_items)

    return render_template('user/followed_feed.html', 
                           feed_items=feed_items, 
                           pagination=pagination,
                           DogStatus=DogStatus)  


####################   Changing Account Types    ##########################

@bp.route('/account_management')
@login_required
def account_management():
    user_data = {
        'account_type': current_user.account_type,
        # Add other user data as needed
    }
    return render_template('user/account_management.html', user_data=user_data, AccountType=AccountType)

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


@bp.route('/switch_role', methods=['POST'])
@login_required
def switch_role():
    current_user.switch_role()
    flash(f'Your account has been switched to {current_user.role_name} mode.', 'success')
    return redirect(url_for('user.user_settings'))