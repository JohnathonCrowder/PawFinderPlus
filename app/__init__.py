import os
from flask import Flask, render_template, url_for, request, redirect, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from datetime import date  # Add this at the top


db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dogbreeder.db'
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    db.init_app(app)

    # Ensure the upload folder exists
    os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)

    class Dog(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        breed = db.Column(db.String(100), nullable=False)
        date_of_birth = db.Column(db.Date, nullable=False)
        gender = db.Column(db.String(10), nullable=False)
        weight = db.Column(db.Float)
        color = db.Column(db.String(50))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        images = db.relationship('DogImage', backref='dog', lazy=True, cascade="all, delete-orphan")

    class DogImage(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        filename = db.Column(db.String(255), nullable=False)
        dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
        uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    with app.app_context():
        db.create_all()

    def allowed_file(filename):
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @app.route('/')
    def home():
        dogs = Dog.query.all()
        return render_template('index.html', dogs=dogs)

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
            
            new_dog = Dog(name=name, breed=breed, date_of_birth=date_of_birth, 
                          gender=gender, weight=weight, color=color)
            db.session.add(new_dog)
            db.session.commit()

            # Handle image uploads
            if 'images' in request.files:
                for image in request.files.getlist('images'):
                    if image and allowed_file(image.filename):
                        filename = secure_filename(f"{new_dog.id}_{image.filename}")
                        image.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))
                        new_image = DogImage(filename=filename, dog_id=new_dog.id)
                        db.session.add(new_image)
            
            db.session.commit()
            flash('Dog added successfully!', 'success')
            return redirect(url_for('home'))
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
                        filename = secure_filename(f"{dog.id}_{image.filename}")
                        image.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))
                        new_image = DogImage(filename=filename, dog_id=dog.id)
                        db.session.add(new_image)

            db.session.commit()
            flash('Dog updated successfully!', 'success')
            return redirect(url_for('dog_detail', id=dog.id))
        return render_template('dog_detail.html', dog=dog)
    
    @app.route('/dog/<int:id>/profile')
    def dog_profile(id):
        dog = Dog.query.get_or_404(id)
        return render_template('dog_profile.html', dog=dog, date=date)

    @app.route('/dog/<int:id>/delete', methods=['POST'])
    def delete_dog(id):
        dog = Dog.query.get_or_404(id)
        
        # Delete associated image files
        for image in dog.images:
            try:
                os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], image.filename))
            except Exception as e:
                app.logger.error(f"Error deleting file {image.filename}: {str(e)}")
        
        # Delete the dog from the database (this will also delete associated DogImage records)
        db.session.delete(dog)
        db.session.commit()
        flash('Dog deleted successfully!', 'success')
        return redirect(url_for('home'))

    @app.route('/dog/<int:id>/delete_image/<int:image_id>', methods=['POST'])
    def delete_image(id, image_id):
        image = DogImage.query.get_or_404(image_id)
        if image.dog_id != id:
            flash('Invalid image!', 'error')
            return redirect(url_for('dog_detail', id=id))
        
        # Delete the file
        try:
            os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], image.filename))
        except Exception as e:
            flash(f'Error deleting image file: {str(e)}', 'error')
        
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