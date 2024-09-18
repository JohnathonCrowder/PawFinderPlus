import os
from flask import Flask, render_template, url_for, request, redirect, flash, send_file
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from .extensions import db
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Dog, DogImage, Litter, LitterImage, Message, DogStatus, VetAppointment, AppointmentCategory
from io import BytesIO
from flask_migrate import Migrate
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, func
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import current_app
import json





def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dogbreeder.db'
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize the database
    db.init_app(app)
    migrate = Migrate(app, db)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def allowed_file(filename):
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



    socketio = SocketIO(app)

    @socketio.on('join')
    def on_join(data):
        room = data['room']
        join_room(room)

    @socketio.on('leave')
    def on_leave(data):
        room = data['room']
        leave_room(room)

    @socketio.on('message')
    def handle_message(data):
        room = data['room']
        emit('message', data, room=room)

    if __name__ == '__main__':
        socketio.run(app)



    # User Settings Routes
    @app.route('/user_settings')
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
            'instagram': current_user.instagram or ''
        }
        return render_template('user_settings.html', user_data=user_data)

    @app.route('/update_profile', methods=['POST'])
    @login_required
    def update_profile():
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                # Read the file data and store it in the database
                current_user.profile_picture_data = file.read()
                current_user.profile_picture_filename = secure_filename(file.filename)
                current_user.profile_picture_mimetype = file.mimetype

        # Update other profile information
        current_user.full_name = request.form.get('full_name', '').strip() or None
        current_user.location = request.form.get('location', '').strip() or None
        current_user.phone_number = request.form.get('phone_number', '').strip() or None
        current_user.bio = request.form.get('bio', '').strip() or None
        

        def format_url(url):
            if url and not url.startswith(('http://', 'https://')):
                return f'https://{url}'
            return url

        current_user.website = format_url(request.form.get('website', '').strip()) or None
        current_user.facebook = format_url(request.form.get('facebook', '').strip()) or None
        current_user.instagram = format_url(request.form.get('instagram', '').strip()) or None

        # Commit changes to the database
        db.session.commit()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_settings'))

    @app.route('/profile_picture/<int:user_id>')
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

    @app.route('/remove_profile_picture', methods=['POST'])
    @login_required
    def remove_profile_picture():
        current_user.profile_picture_data = None
        current_user.profile_picture_filename = None
        current_user.profile_picture_mimetype = None
        db.session.commit()
        flash('Profile picture removed successfully.', 'success')
        return redirect(url_for('user_settings'))
    

    @app.route('/profile/<username>')
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

        return render_template('user_profile.html', 
                            user=user, 
                            dogs=dogs,
                            litters=litters,
                            total_dogs=total_dogs, 
                            total_litters=total_litters,
                            dog_breeds=dog_breeds,
                            is_own_profile=is_own_profile,
                            DogStatus=DogStatus)

    # Existing Routes
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return redirect(url_for('register'))
            
            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'error')
                return redirect(url_for('register'))
            
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Logged out successfully.', 'success')
        return redirect(url_for('home'))

    @app.route('/')
    def home():
        return render_template('index.html')
    
    @app.route('/dog_management')
    @login_required
    def dog_management():
        search = request.args.get('search', '')
        if search:
            dogs = Dog.query.filter(
                Dog.user_id == current_user.id,
                or_(
                    Dog.name.ilike(f'%{search}%'),
                    Dog.breed.ilike(f'%{search}%')
                )
            ).all()
        else:
            dogs = Dog.query.filter_by(user_id=current_user.id).all()
        return render_template('dog_management.html', dogs=dogs, search=search)
    
    @app.route('/public_litters')
    def public_litters():
        page = request.args.get('page', 1, type=int)
        per_page = 9  # Number of litters per page

        # Get filter parameters
        breed = request.args.get('breed')
        age = request.args.get('age')
        min_price = request.args.get('minPrice', type=float)
        max_price = request.args.get('maxPrice', type=float)
        status = request.args.get('status')
        sort = request.args.get('sort', 'newest')
        search = request.args.get('search')

        # Start with base query
        query = Litter.query.filter_by(is_public=True)

        # Apply filters
        if breed:
            query = query.filter(or_(Litter.father.has(breed=breed), Litter.mother.has(breed=breed)))

        if age:
            today = datetime.utcnow().date()
            if age == '0-4 weeks':
                date_limit = today - timedelta(weeks=4)
                query = query.filter(Litter.date_of_birth >= date_limit)
            elif age == '4-8 weeks':
                start_date = today - timedelta(weeks=8)
                end_date = today - timedelta(weeks=4)
                query = query.filter(Litter.date_of_birth.between(start_date, end_date))
            elif age == '8+ weeks':
                date_limit = today - timedelta(weeks=8)
                query = query.filter(Litter.date_of_birth <= date_limit)

        if min_price is not None and max_price is not None:
            query = query.filter(Litter.puppies.any(and_(
                Dog.price >= min_price,
                Dog.price <= max_price,
                Dog.status.in_([DogStatus.AVAILABLE_NOW, DogStatus.AVAILABLE_SOON])
            )))

        if status:
            query = query.filter(Litter.puppies.any(Dog.status == DogStatus[status]))

        if search:
            search_term = f"%{search}%"
            query = query.filter(or_(
                Litter.name.ilike(search_term),
                Litter.father.has(Dog.name.ilike(search_term)),
                Litter.mother.has(Dog.name.ilike(search_term)),
                Litter.father.has(Dog.breed.ilike(search_term)),
                Litter.mother.has(Dog.breed.ilike(search_term))
            ))

        # Apply sorting
        if sort == 'oldest':
            query = query.order_by(Litter.date_of_birth.asc())
        elif sort == 'price_low':
            query = query.order_by(Litter.puppies.any(Dog.price.asc()))
        elif sort == 'price_high':
            query = query.order_by(Litter.puppies.any(Dog.price.desc()))
        else:  # newest
            query = query.order_by(Litter.date_of_birth.desc())

        # Paginate results
        paginated_litters = query.paginate(page=page, per_page=per_page, error_out=False)

        # Get unique breeds for the filter dropdown
        breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
        breeds = [breed[0] for breed in breeds]

        # Get min and max prices for the price range slider
        min_price_overall = db.session.query(func.min(Dog.price)).scalar() or 0
        max_price_overall = db.session.query(func.max(Dog.price)).scalar() or 10000

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render_template('public_litters_content.html', 
                                litters=paginated_litters.items,
                                pagination=paginated_litters,
                                DogStatus=DogStatus)

        # Get featured litters
        featured_count = 5  # Number of featured litters to display
        breed = request.args.get('breed')

        if breed:
            # If a breed is specified, prioritize that breed
            breed_litters = Litter.query.filter(Litter.is_public == True)\
                .filter((Litter.father.has(breed=breed)) | (Litter.mother.has(breed=breed)))\
                .order_by(func.random())\
                .limit(featured_count)\
                .all()
            
            # If we don't have enough of the specified breed, fill with random litters
            if len(breed_litters) < featured_count:
                remaining_count = featured_count - len(breed_litters)
                other_litters = Litter.query.filter(Litter.is_public == True)\
                    .filter(~((Litter.father.has(breed=breed)) | (Litter.mother.has(breed=breed))))\
                    .order_by(func.random())\
                    .limit(remaining_count)\
                    .all()
                featured_litters = breed_litters + other_litters
            else:
                featured_litters = breed_litters
        else:
            # If no breed is specified, select random litters
            featured_litters = Litter.query.filter_by(is_public=True)\
                .order_by(func.random())\
                .limit(featured_count)\
                .all()

        return render_template('public_litters.html', 
                            litters=paginated_litters.items,
                            pagination=paginated_litters,
                            featured_litters=featured_litters,
                            breeds=breeds,
                            min_price=min_price_overall,
                            max_price=max_price_overall,
                            current_breed=breed,
                            current_age=age,
                            current_status=status,
                            current_sort=sort,
                            search=search,
                            DogStatus=DogStatus)
    
    def load_json_data(filename):
        with open(filename) as f:
            data = json.load(f)
        return sorted(data['breeds'] if 'breeds' in data else data['colors'])

    @app.route('/add_dog', methods=['GET', 'POST'])
    @login_required
    def add_dog():
        if request.method == 'POST':
            name = request.form['name']
            breed = request.form['breed']
            date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            gender = request.form['gender']
            weight = float(request.form['weight']) if request.form['weight'] else None
            color = request.form['color']
            father_id = request.form.get('father_id')
            mother_id = request.form.get('mother_id')
            is_public = 'is_public' in request.form  
            status = DogStatus(request.form['status'])
            price = float(request.form['price']) if request.form['price'] else None
            
            new_dog = Dog(
                name=name, 
                breed=breed, 
                date_of_birth=date_of_birth, 
                gender=gender, 
                weight=weight, 
                color=color,
                father_id=father_id if father_id else None,
                mother_id=mother_id if mother_id else None,
                status=status,
                price=price,
                user_id=current_user.id,
                is_public=is_public  
            )
            db.session.add(new_dog)
            db.session.commit()

            # Handle image uploads
            if 'images' in request.files:
                for image in request.files.getlist('images'):
                    if image and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        image_data = image.read()
                        mimetype = image.mimetype
                        new_image = DogImage(filename=filename, data=image_data, mimetype=mimetype, dog_id=new_dog.id)
                        db.session.add(new_image)

            db.session.commit()
            flash('Dog added successfully!', 'success')
            return redirect(url_for('dog_management'))

        # Load and sort dog breeds and colors from JSON files
        breeds = load_json_data('dog_breeds.json')
        colors = load_json_data('dog_colors.json')
        statuses = [status.value for status in DogStatus]

        # Get all dogs for parent selection
        all_dogs = Dog.query.filter_by(user_id=current_user.id).all()
        return render_template('add_dog.html', all_dogs=all_dogs, breeds=breeds, colors=colors, statuses=statuses)
    

    @app.route('/contact_owner/<int:dog_id>')
    @login_required
    def contact_owner(dog_id):
        dog = Dog.query.get_or_404(dog_id)
        if dog.user_id == current_user.id:
            flash('You cannot contact yourself.', 'error')
            return redirect(url_for('dog_profile', id=dog_id))

        # Create a unique conversation ID
        conversation_id = f"{min(current_user.id, dog.user_id)}_{max(current_user.id, dog.user_id)}"

        # Check if a conversation already exists
        existing_message = Message.query.filter_by(conversation_id=conversation_id).first()

        if existing_message:
            # If a conversation exists, redirect to it
            return redirect(url_for('conversation', user_id=dog.user_id))
        else:
            # If no conversation exists, create a new one with an initial message
            new_message = Message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                recipient_id=dog.user_id,
                content=f"Hello, I'm interested in your dog {dog.name}."
            )
            db.session.add(new_message)
            db.session.commit()
            flash('Your message has been sent to the owner.', 'success')
            return redirect(url_for('conversation', user_id=dog.user_id))
    
    @app.route('/dog/<int:id>/family_tree')
    @login_required
    def dog_family_tree(id):
        dog = Dog.query.options(
            joinedload(Dog.father).joinedload(Dog.images),
            joinedload(Dog.mother).joinedload(Dog.images),
            joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.images),
            joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.images),
            joinedload(Dog.mother).joinedload(Dog.father).joinedload(Dog.images),
            joinedload(Dog.mother).joinedload(Dog.mother).joinedload(Dog.images),
            joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.images),
            joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.images),
            joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.father).joinedload(Dog.images),
            joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.mother).joinedload(Dog.images),
            joinedload(Dog.images)
        ).get_or_404(id)

        litter = Litter.query.filter(Litter.puppies.any(id=dog.id)).first()

        return render_template('family_tree.html', dog=dog, litter=litter)
    
    @app.route('/litter_image/<int:image_id>')
    def get_litter_image(image_id):
        image = LitterImage.query.get_or_404(image_id)
        return send_file(
            BytesIO(image.data),
            mimetype=image.mimetype,
            as_attachment=False,
            download_name=image.filename
        )
    
    @app.route('/litter/<int:litter_id>/delete_image/<int:image_id>', methods=['POST'])
    @login_required
    def delete_litter_image(litter_id, image_id):
        image = LitterImage.query.get_or_404(image_id)
        if image.litter_id != litter_id or image.litter.user_id != current_user.id:
            flash('Invalid image!', 'error')
            return redirect(url_for('edit_litter', id=litter_id))
        
        db.session.delete(image)
        db.session.commit()
        flash('Image deleted successfully!', 'success')
        return redirect(url_for('edit_litter', id=litter_id))

    @app.route('/edit_litter/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_litter(id):
        litter = Litter.query.get_or_404(id)
        if request.method == 'POST':
            litter.name = request.form['name']
            litter.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            litter.father_id = request.form['father_id']
            litter.mother_id = request.form['mother_id']
            litter.is_public = 'is_public' in request.form  # Add this line
            puppy_ids = request.form.getlist('puppies')
            
            # Clear existing puppies and add new ones
            litter.puppies = []
            for puppy_id in puppy_ids:
                puppy = Dog.query.get(puppy_id)
                litter.puppies.append(puppy)

            # Handle new image uploads
            if 'images' in request.files:
                for image in request.files.getlist('images'):
                    if image and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        image_data = image.read()
                        mimetype = image.mimetype
                        new_image = LitterImage(filename=filename, data=image_data, mimetype=mimetype, litter_id=litter.id)
                        db.session.add(new_image)

            db.session.commit()
            flash('Litter updated successfully!', 'success')
            return redirect(url_for('litter_management'))

        # Get all dogs for this user
        all_dogs = Dog.query.filter(Dog.user_id == current_user.id).order_by(Dog.date_of_birth).all()

        return render_template('edit_litter.html', litter=litter, dogs=all_dogs)

    @app.route('/dog/<int:id>', methods=['GET', 'POST'])
    @login_required
    def dog_detail(id):
        dog = Dog.query.get_or_404(id)
        if request.method == 'POST':
            dog.name = request.form['name']
            dog.breed = request.form['breed']
            dog.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            dog.gender = request.form['gender']
            dog.weight = float(request.form['weight']) if request.form['weight'] else None
            dog.color = request.form['color']
            dog.is_public = 'is_public' in request.form
            dog.status = DogStatus(request.form['status'])
            dog.price = float(request.form['price']) if request.form['price'] else None
            
            # Handle father and mother updates
            father_id = request.form.get('father_id')
            mother_id = request.form.get('mother_id')
            dog.father_id = int(father_id) if father_id else None
            dog.mother_id = int(mother_id) if mother_id else None

            # Handle new image uploads
            if 'images' in request.files:
                for image in request.files.getlist('images'):
                    if image and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        image_data = image.read()
                        mimetype = image.mimetype
                        new_image = DogImage(filename=filename, data=image_data, mimetype=mimetype, dog_id=dog.id)
                        db.session.add(new_image)

            db.session.commit()
            flash('Dog updated successfully!', 'success')
            return redirect(url_for('dog_detail', id=dog.id))

        # Load and sort dog breeds and colors from JSON files
        breeds = load_json_data('dog_breeds.json')
        colors = load_json_data('dog_colors.json')
        statuses = [status.value for status in DogStatus]

        # Get all dogs for parent selection, excluding the current dog
        all_dogs = Dog.query.filter(Dog.id != id, Dog.user_id == current_user.id).all()
        return render_template('dog_detail.html', dog=dog, all_dogs=all_dogs, breeds=breeds, colors=colors, statuses=statuses)
    
    @app.route('/change_email', methods=['POST'])
    @login_required
    def change_email():
        new_email = request.form.get('new_email')
        if User.query.filter_by(email=new_email).first():
            flash('Email already exists', 'error')
        else:
            current_user.email = new_email
            db.session.commit()
            flash('Email updated successfully', 'success')
        return redirect(url_for('user_settings'))

    @app.route('/change_password', methods=['POST'])
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
        return redirect(url_for('user_settings'))

    @app.route('/delete_account', methods=['POST'])
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
            return redirect(url_for('home'))
        else:
            flash('Password is incorrect', 'error')
        return redirect(url_for('user_settings'))
    
    @app.route('/delete_litter/<int:id>', methods=['POST'])
    @login_required
    def delete_litter(id):
        litter = Litter.query.get_or_404(id)
        if litter.user_id != current_user.id:
            flash('You do not have permission to delete this litter.', 'error')
            return redirect(url_for('litter_management'))
        
        db.session.delete(litter)
        db.session.commit()
        flash('Litter has been deleted successfully.', 'success')
        return redirect(url_for('litter_management'))
    
    @app.route('/dog/<int:id>/profile')
    def dog_profile(id):
        dog = Dog.query.get_or_404(id)
        if not dog.is_public and (not current_user.is_authenticated or current_user.id != dog.user_id):
            flash('This dog profile is not publicly visible.', 'error')
            return redirect(url_for('home'))
        return render_template('dog_profile.html', dog=dog, date=date, DogStatus=DogStatus)
    
    @app.route('/dog_image/<int:image_id>')
    def get_dog_image(image_id):
        image = DogImage.query.get_or_404(image_id)
        return send_file(
            BytesIO(image.data),
            mimetype=image.mimetype,
            as_attachment=False,
            download_name=image.filename
        )

    @app.route('/dog/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_dog(id):
        dog = Dog.query.get_or_404(id)
        
        # Delete the dog from the database (this will also delete associated DogImage records)
        db.session.delete(dog)
        db.session.commit()
        flash('Dog deleted successfully!', 'success')
        return redirect(url_for('dog_management'))

    @app.route('/dog/<int:id>/delete_image/<int:image_id>', methods=['POST'])
    @login_required
    def delete_image(id, image_id):
        image = DogImage.query.get_or_404(image_id)
        if image.dog_id != id:
            flash('Invalid image!', 'error')
            return redirect(url_for('dog_detail', id=id))
        
        # Delete from database
        db.session.delete(image)
        db.session.commit()
        flash('Image deleted successfully!', 'success')
        return redirect(url_for('dog_detail', id=id))

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')
    
    @app.route('/add_litter', methods=['GET', 'POST'])
    @login_required
    def add_litter():
        if request.method == 'POST':
            name = request.form['name']
            date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            father_id = request.form['father_id']
            mother_id = request.form['mother_id']
            puppy_ids = request.form.getlist('puppies')
            is_public = 'is_public' in request.form

            new_litter = Litter(
                name=name,
                date_of_birth=date_of_birth,
                father_id=father_id,
                mother_id=mother_id,
                user_id=current_user.id,
                is_public=is_public
            )
            db.session.add(new_litter)
            db.session.commit()

            for puppy_id in puppy_ids:
                puppy = Dog.query.get(puppy_id)
                new_litter.puppies.append(puppy)

            # Handle image uploads
            if 'images' in request.files:
                for image in request.files.getlist('images'):
                    if image and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        image_data = image.read()
                        mimetype = image.mimetype
                        new_image = LitterImage(filename=filename, data=image_data, mimetype=mimetype, litter_id=new_litter.id)
                        db.session.add(new_image)

            db.session.commit()
            flash('Litter added successfully!', 'success')
            return redirect(url_for('litter_management'))

        # Get all dogs for this user
        all_dogs = Dog.query.filter(Dog.user_id == current_user.id).order_by(Dog.date_of_birth).all()

        return render_template('add_litter.html', dogs=all_dogs)
    
    @app.route('/messages')
    @login_required
    def messages():
        conversations = db.session.query(
            Message.conversation_id,
            User.id.label('user_id'),
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

        return render_template('messages.html', conversations=conversations)

    @app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
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
            return redirect(url_for('conversation', user_id=user_id))
        
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
        
        return render_template('conversation.html', messages=messages, other_user=other_user)

    @app.route('/litter_management')
    @login_required
    def litter_management():
        litters = Litter.query.filter_by(user_id=current_user.id).all()
        return render_template('litter_management.html', litters=litters)

    @app.route('/litter/<int:id>')
    def litter_detail(id):
        litter = Litter.query.get_or_404(id)
        if not litter.is_public and (not current_user.is_authenticated or current_user.id != litter.user_id):
            flash('This litter is not publicly visible.', 'error')
            return redirect(url_for('home'))
        return render_template('litter_detail.html', litter=litter, DogStatus=DogStatus)

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    



##########################    Vet Routes    #######################


    @app.route('/dog/<int:dog_id>/appointments')
    @login_required
    def dog_appointments(dog_id):
        dog = Dog.query.get_or_404(dog_id)
        if dog.user_id != current_user.id:
            flash('You do not have permission to view this dog\'s appointments.', 'error')
            return redirect(url_for('dog_management'))
        
        # Get the selected category from query parameters
        selected_category = request.args.get('category', 'all')
        
        # Base query
        appointments_query = VetAppointment.query.filter_by(dog_id=dog_id)
        
        # Apply category filter if a specific category is selected
        if selected_category != 'all':
            appointments_query = appointments_query.filter(VetAppointment.category == AppointmentCategory[selected_category])
        
        # Order appointments by date
        appointments = appointments_query.order_by(VetAppointment.date).all()
        
        now = datetime.utcnow()
        return render_template('dog_appointments.html', 
                            dog=dog, 
                            appointments=appointments, 
                            now=now,
                            categories=AppointmentCategory,
                            selected_category=selected_category)

    @app.route('/add_appointment', methods=['GET', 'POST'])
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
            return redirect(url_for('dog_appointments', dog_id=dog_id))
        
        dogs = Dog.query.filter_by(user_id=current_user.id).all()
        return render_template('add_appointment.html', dogs=dogs, categories=AppointmentCategory)

    @app.route('/appointment/<int:appointment_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_appointment(appointment_id):
        appointment = VetAppointment.query.get_or_404(appointment_id)
        if appointment.dog.user_id != current_user.id:
            flash('You do not have permission to edit this appointment.', 'error')
            return redirect(url_for('dog_management'))
        
        if request.method == 'POST':
            appointment.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
            appointment.category = AppointmentCategory[request.form['category']]
            appointment.description = request.form['description']
            appointment.veterinarian = request.form['veterinarian']
            appointment.location = request.form['location']
            appointment.completed = 'completed' in request.form
            db.session.commit()
            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('dog_appointments', dog_id=appointment.dog_id))
        
        return render_template('edit_appointment.html', appointment=appointment, categories=AppointmentCategory)

    @app.route('/appointment/<int:appointment_id>/delete', methods=['POST'])
    @login_required
    def delete_appointment(appointment_id):
        appointment = VetAppointment.query.get_or_404(appointment_id)
        if appointment.dog.user_id != current_user.id:
            flash('You do not have permission to delete this appointment.', 'error')
            return redirect(url_for('dog_management'))
        
        db.session.delete(appointment)
        db.session.commit()
        flash('Appointment deleted successfully!', 'success')
        return redirect(url_for('dog_appointments', dog_id=appointment.dog_id))
    

    @app.route('/vet_appointments')
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


    return app


