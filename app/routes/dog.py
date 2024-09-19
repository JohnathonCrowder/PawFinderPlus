from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import Dog, DogImage, DogStatus, Litter
from app.extensions import db
from app.utils import allowed_file, load_json_data
from datetime import datetime
from io import BytesIO
from datetime import datetime, timedelta

bp = Blueprint('dog', __name__)

@bp.route('/dog_management')
@login_required
def dog_management():
    # Get filter parameters from request
    breed = request.args.get('breed')
    age = request.args.get('age')
    status = request.args.get('status')
    search = request.args.get('search', '')

    # Start with base query
    query = Dog.query.filter_by(user_id=current_user.id)

    # Apply filters
    if breed:
        query = query.filter(Dog.breed == breed)
    
    if age:
        today = datetime.utcnow().date()
        if age == 'puppy':
            date_limit = today - timedelta(months=12)
            query = query.filter(Dog.date_of_birth >= date_limit)
        elif age == 'adult':
            date_limit = today - timedelta(years=7)
            query = query.filter(Dog.date_of_birth.between(date_limit, today - timedelta(months=12)))
        elif age == 'senior':
            date_limit = today - timedelta(years=7)
            query = query.filter(Dog.date_of_birth <= date_limit)

    if status:
        query = query.filter(Dog.status == DogStatus[status])

    if search:
        query = query.filter(Dog.name.ilike(f'%{search}%'))

    # Execute query
    dogs = query.all()

    # Get unique breeds for filter options
    breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
    breeds = [breed[0] for breed in breeds]

    return render_template('dog_management.html', 
                           dogs=dogs, 
                           breeds=breeds, 
                           current_breed=breed,
                           current_age=age,
                           current_status=status,
                           search=search,
                           DogStatus=DogStatus)

@bp.route('/add_dog', methods=['GET', 'POST'])
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
        return redirect(url_for('dog.dog_management'))

    breeds = load_json_data('dog_breeds.json')
    colors = load_json_data('dog_colors.json')
    statuses = [status.value for status in DogStatus]
    all_dogs = Dog.query.filter_by(user_id=current_user.id).all()
    return render_template('add_dog.html', all_dogs=all_dogs, breeds=breeds, colors=colors, statuses=statuses)

@bp.route('/dog/<int:id>', methods=['GET', 'POST'])
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
        
        father_id = request.form.get('father_id')
        mother_id = request.form.get('mother_id')
        dog.father_id = int(father_id) if father_id else None
        dog.mother_id = int(mother_id) if mother_id else None

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
        return redirect(url_for('dog.dog_detail', id=dog.id))

    breeds = load_json_data('dog_breeds.json')
    colors = load_json_data('dog_colors.json')
    statuses = [status.value for status in DogStatus]
    all_dogs = Dog.query.filter(Dog.id != id, Dog.user_id == current_user.id).all()
    return render_template('dog_detail.html', dog=dog, all_dogs=all_dogs, breeds=breeds, colors=colors, statuses=statuses)

@bp.route('/dog/<int:id>/profile')
def dog_profile(id):
    dog = Dog.query.get_or_404(id)
    if not dog.is_public and (not current_user.is_authenticated or current_user.id != dog.user_id):
        flash('This dog profile is not publicly visible.', 'error')
        return redirect(url_for('main.home'))
    return render_template('dog_profile.html', dog=dog, date=datetime.now().date(), DogStatus=DogStatus)

@bp.route('/dog_image/<int:image_id>')
def get_dog_image(image_id):
    image = DogImage.query.get_or_404(image_id)
    return send_file(
        BytesIO(image.data),
        mimetype=image.mimetype,
        as_attachment=False,
        download_name=image.filename
    )

@bp.route('/dog/<int:id>/delete', methods=['POST'])
@login_required
def delete_dog(id):
    dog = Dog.query.get_or_404(id)
    if dog.user_id != current_user.id:
        flash('You do not have permission to delete this dog.', 'error')
        return redirect(url_for('dog.dog_management'))
    
    db.session.delete(dog)
    db.session.commit()
    flash('Dog deleted successfully!', 'success')
    return redirect(url_for('dog.dog_management'))

@bp.route('/dog/<int:id>/delete_image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(id, image_id):
    image = DogImage.query.get_or_404(image_id)
    if image.dog_id != id:
        flash('Invalid image!', 'error')
        return redirect(url_for('dog.dog_detail', id=id))
    
    db.session.delete(image)
    db.session.commit()
    flash('Image deleted successfully!', 'success')
    return redirect(url_for('dog.dog_detail', id=id))

@bp.route('/dog/<int:id>/family_tree')
@login_required
def dog_family_tree(id):
    dog = Dog.query.options(
        db.joinedload(Dog.father).joinedload(Dog.images),
        db.joinedload(Dog.mother).joinedload(Dog.images),
        db.joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.images),
        db.joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.images),
        db.joinedload(Dog.mother).joinedload(Dog.father).joinedload(Dog.images),
        db.joinedload(Dog.mother).joinedload(Dog.mother).joinedload(Dog.images),
        db.joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.images),
        db.joinedload(Dog.father).joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.images),
        db.joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.father).joinedload(Dog.images),
        db.joinedload(Dog.father).joinedload(Dog.mother).joinedload(Dog.mother).joinedload(Dog.images),
        db.joinedload(Dog.images)
    ).get_or_404(id)

    litter = Litter.query.filter(Litter.puppies.any(id=dog.id)).first()

    return render_template('family_tree.html', dog=dog, litter=litter)