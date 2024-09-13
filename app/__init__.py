import os
from flask import Flask, render_template, url_for, request, redirect, flash, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime, date
from .extensions import db
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Dog, DogImage
from flask import send_file
from io import BytesIO


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dogbreeder.db'
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize the database
    db.init_app(app)

    # Ensure the upload folder exists
    os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)

    # Create database tables
    with app.app_context():
        db.create_all()

    def allowed_file(filename):
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    

    #######################    Login Code   ##################################

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Registration route
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

    # Login route
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

    # Logout route
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Logged out successfully.', 'success')
        return redirect(url_for('home'))
    
    ##### User Settings Routes #########

    @app.route('/user_settings', methods=['GET', 'POST'])
    @login_required
    def user_settings():
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'change_email':
                new_email = request.form.get('new_email')
                if User.query.filter_by(email=new_email).first():
                    flash('Email already exists', 'error')
                else:
                    current_user.email = new_email
                    db.session.commit()
                    flash('Email updated successfully', 'success')

            elif action == 'change_password':
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                if check_password_hash(current_user.password_hash, current_password):
                    current_user.set_password(new_password)
                    db.session.commit()
                    flash('Password updated successfully', 'success')
                else:
                    flash('Current password is incorrect', 'error')

            elif action == 'delete_account':
                password_confirm = request.form.get('password_confirm')
                if check_password_hash(current_user.password_hash, password_confirm):
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

        return render_template('user_settings.html')
    


    ########################     Page Routes    ##################################

    @app.route('/')
    def home():
        # This will be replaced in the next step
        return render_template('index.html')
    
    @app.route('/dog_management')
    @login_required
    def dog_management():
        dogs = Dog.query.filter_by(user_id=current_user.id).all()
        return render_template('dog_management.html', dogs=dogs)

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    


    @app.route('/add_dog', methods=['GET', 'POST'])
    def add_dog():
        if request.method == 'POST':
            name = request.form['name']
            breed = request.form['breed']
            date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            gender = request.form['gender']
            weight = float(request.form['weight']) if request.form['weight'] else None
            color = request.form['color']
            
            new_dog = Dog(
                name=name, 
                breed=breed, 
                date_of_birth=date_of_birth, 
                gender=gender, 
                weight=weight, 
                color=color,
                user_id=current_user.id  # Associate dog with current user 
                
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
        return render_template('add_dog.html')

    @app.route('/dog/<int:id>', methods=['GET', 'POST'])
    def dog_detail(id):
        dog = Dog.query.get_or_404(id)
        if request.method == 'POST':
            dog.name = request.form['name']
            dog.breed = request.form['breed']
            dog.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            dog.gender = request.form['gender']
            dog.weight = float(request.form['weight']) if request.form['weight'] else None
            dog.color = request.form['color']

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
        return render_template('dog_detail.html', dog=dog)
    
    @app.route('/dog/<int:id>/profile')
    def dog_profile(id):
        dog = Dog.query.get_or_404(id)
        return render_template('dog_profile.html', dog=dog, date=date)
    
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

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    return app