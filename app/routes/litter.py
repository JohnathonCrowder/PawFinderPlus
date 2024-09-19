from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import Litter, LitterImage, Dog, DogStatus
from app.extensions import db
from app.utils import allowed_file
from datetime import datetime, timedelta
from io import BytesIO
from sqlalchemy import or_, and_, func

bp = Blueprint('litter', __name__)

@bp.route('/litter_management')
@login_required
def litter_management():
    # Get filter parameters from request
    breed = request.args.get('breed')
    age = request.args.get('age')
    search = request.args.get('search', '')

    # Start with base query
    query = Litter.query.filter_by(user_id=current_user.id)

    # Apply filters
    if breed:
        query = query.filter(or_(Litter.father.has(breed=breed), Litter.mother.has(breed=breed)))
    
    if age:
        today = datetime.utcnow().date()
        if age == '0-8 weeks':
            date_limit = today - timedelta(weeks=8)
            query = query.filter(Litter.date_of_birth >= date_limit)
        elif age == '8-16 weeks':
            start_date = today - timedelta(weeks=16)
            end_date = today - timedelta(weeks=8)
            query = query.filter(Litter.date_of_birth.between(start_date, end_date))
        elif age == '16+ weeks':
            date_limit = today - timedelta(weeks=16)
            query = query.filter(Litter.date_of_birth <= date_limit)

    if search:
        query = query.filter(or_(
            Litter.name.ilike(f'%{search}%'),
            Litter.father.has(Dog.name.ilike(f'%{search}%')),
            Litter.mother.has(Dog.name.ilike(f'%{search}%'))
        ))

    # Execute query
    litters = query.all()

    # Get unique breeds for filter options
    breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
    breeds = [breed[0] for breed in breeds]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/litter_list.html', 
                               litters=litters)
    else:
        return render_template('litter_management.html', 
                               litters=litters, 
                               breeds=breeds, 
                               current_breed=breed,
                               current_age=age,
                               search=search)


@bp.route('/add_litter', methods=['GET', 'POST'])
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
        return redirect(url_for('litter.litter_management'))

    all_dogs = Dog.query.filter(Dog.user_id == current_user.id).order_by(Dog.date_of_birth).all()
    return render_template('add_litter.html', dogs=all_dogs)

@bp.route('/edit_litter/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_litter(id):
    litter = Litter.query.get_or_404(id)
    if request.method == 'POST':
        litter.name = request.form['name']
        litter.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
        litter.father_id = request.form['father_id']
        litter.mother_id = request.form['mother_id']
        litter.is_public = 'is_public' in request.form
        puppy_ids = request.form.getlist('puppies')
        
        litter.puppies = []
        for puppy_id in puppy_ids:
            puppy = Dog.query.get(puppy_id)
            litter.puppies.append(puppy)

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
        return redirect(url_for('litter.litter_management'))

    all_dogs = Dog.query.filter(Dog.user_id == current_user.id).order_by(Dog.date_of_birth).all()
    return render_template('edit_litter.html', litter=litter, dogs=all_dogs)

@bp.route('/litter/<int:id>')
def litter_detail(id):
    litter = Litter.query.get_or_404(id)
    if not litter.is_public and (not current_user.is_authenticated or current_user.id != litter.user_id):
        flash('This litter is not publicly visible.', 'error')
        return redirect(url_for('main.home'))
    return render_template('litter_detail.html', litter=litter, DogStatus=DogStatus)

@bp.route('/litter_image/<int:image_id>')
def get_litter_image(image_id):
    image = LitterImage.query.get_or_404(image_id)
    return send_file(
        BytesIO(image.data),
        mimetype=image.mimetype,
        as_attachment=False,
        download_name=image.filename
    )

@bp.route('/litter/<int:litter_id>/delete_image/<int:image_id>', methods=['POST'])
@login_required
def delete_litter_image(litter_id, image_id):
    image = LitterImage.query.get_or_404(image_id)
    if image.litter_id != litter_id or image.litter.user_id != current_user.id:
        flash('Invalid image!', 'error')
        return redirect(url_for('litter.edit_litter', id=litter_id))
    
    db.session.delete(image)
    db.session.commit()
    flash('Image deleted successfully!', 'success')
    return redirect(url_for('litter.edit_litter', id=litter_id))

@bp.route('/delete_litter/<int:id>', methods=['POST'])
@login_required
def delete_litter(id):
    litter = Litter.query.get_or_404(id)
    if litter.user_id != current_user.id:
        flash('You do not have permission to delete this litter.', 'error')
        return redirect(url_for('litter.litter_management'))
    
    db.session.delete(litter)
    db.session.commit()
    flash('Litter has been deleted successfully.', 'success')
    return redirect(url_for('litter.litter_management'))

@bp.route('/public_litters')
def public_litters():
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of litters per page

    breed = request.args.get('breed')
    age = request.args.get('age')
    min_price = request.args.get('minPrice', type=float)
    max_price = request.args.get('maxPrice', type=float)
    status = request.args.get('status')
    sort = request.args.get('sort', 'newest')
    search = request.args.get('search')

    query = Litter.query.filter_by(is_public=True)

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

    if sort == 'oldest':
        query = query.order_by(Litter.date_of_birth.asc())
    elif sort == 'price_low':
        query = query.order_by(Litter.puppies.any(Dog.price.asc()))
    elif sort == 'price_high':
        query = query.order_by(Litter.puppies.any(Dog.price.desc()))
    else:  # newest
        query = query.order_by(Litter.date_of_birth.desc())

    paginated_litters = query.paginate(page=page, per_page=per_page, error_out=False)

    breeds = db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()
    breeds = [breed[0] for breed in breeds]

    min_price_overall = db.session.query(func.min(Dog.price)).scalar() or 0
    max_price_overall = db.session.query(func.max(Dog.price)).scalar() or 10000

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('public_litters_content.html', 
                            litters=paginated_litters.items,
                            pagination=paginated_litters,
                            DogStatus=DogStatus)

    featured_count = 5
    breed = request.args.get('breed')

    if breed:
        breed_litters = Litter.query.filter(Litter.is_public == True)\
            .filter((Litter.father.has(breed=breed)) | (Litter.mother.has(breed=breed)))\
            .order_by(func.random())\
            .limit(featured_count)\
            .all()
        
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