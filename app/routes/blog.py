from flask import Blueprint, render_template, request, redirect, url_for, flash,current_app, send_file
from flask_login import login_required, current_user
from app.models import BlogPost, Category
from werkzeug.utils import secure_filename
from app.extensions import db
from app.utils import allowed_file
import os
from io import BytesIO



bp = Blueprint('blog', __name__)

@bp.route('/blog')
def blog_index():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    
    query = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc())
    
    if category:
        query = query.filter(BlogPost.categories.any(name=category))
    
    pagination = query.paginate(page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    
    # Get the most recent post for the featured section
    featured_post = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).first()
    
    recent_posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(5).all()
    categories = Category.query.all()
    
    return render_template('blog/index.html', 
                           posts=posts, 
                           pagination=pagination, 
                           featured_post=featured_post,
                           recent_posts=recent_posts, 
                           categories=categories)

@bp.route('/blog/<int:post_id>')
def blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if not post.is_published and (not current_user.is_authenticated or current_user.id != post.author_id):
        abort(404)
    
    # Get related posts (posts with the same category)
    related_posts = BlogPost.query.filter(
        BlogPost.id != post.id,
        BlogPost.is_published == True,
        BlogPost.categories.any(BlogPost.categories.contains(post.categories[0]) if post.categories else None)
    ).order_by(BlogPost.created_at.desc()).limit(3).all()

    return render_template('blog/post.html', post=post, related_posts=related_posts)

@bp.route('/blog/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        is_published = 'publish' in request.form
        
        post = BlogPost(title=title, content=content, author_id=current_user.id, is_published=is_published)
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                post.image_filename = filename
                post.image_data = file.read()
                post.image_mimetype = file.mimetype

        # Handle categories
        category_ids = request.form.getlist('categories')
        categories = Category.query.filter(Category.id.in_(category_ids)).all()
        post.categories = categories

        db.session.add(post)
        db.session.commit()

        flash('Your post has been created!', 'success')
        return redirect(url_for('blog.blog_post', post_id=post.id))

    categories = Category.query.all()
    return render_template('blog/new_post.html', categories=categories)

@bp.route('/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if post.author_id != current_user.id and not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.is_published = 'publish' in request.form

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                post.image_filename = filename
                post.image_data = file.read()
                post.image_mimetype = file.mimetype

        # Handle categories
        category_ids = request.form.getlist('categories')
        categories = Category.query.filter(Category.id.in_(category_ids)).all()
        post.categories = categories

        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('blog.blog_post', post_id=post.id))

    categories = Category.query.all()
    return render_template('blog/edit_post.html', post=post, categories=categories)

@bp.route('/blog/image/<int:post_id>')
def get_blog_image(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if post.image_data:
        return send_file(
            BytesIO(post.image_data),
            mimetype=post.image_mimetype,
            as_attachment=False,
            download_name=post.image_filename
        )
    else:
        abort(404)

@bp.route('/blog/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('You do not have permission to delete this post.', 'error')
        return redirect(url_for('blog.blog_index'))
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('blog.blog_index'))