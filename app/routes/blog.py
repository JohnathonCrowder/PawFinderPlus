from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import BlogPost
from app.extensions import db

bp = Blueprint('blog', __name__)

@bp.route('/blog')
def blog_index():
    posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).all()
    return render_template('blog/index.html', posts=posts)

@bp.route('/blog/<int:post_id>')
def blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if not post.is_published and (not current_user.is_authenticated or current_user.id != post.author_id):
        flash('This post is not available.', 'error')
        return redirect(url_for('blog.blog_index'))
    return render_template('blog/post.html', post=post)

@bp.route('/blog/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        is_published = 'publish' in request.form
        post = BlogPost(title=title, content=content, author_id=current_user.id, is_published=is_published)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('blog.blog_post', post_id=post.id))
    return render_template('blog/new_post.html')

@bp.route('/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('You do not have permission to edit this post.', 'error')
        return redirect(url_for('blog.blog_index'))
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.is_published = 'publish' in request.form
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('blog.blog_post', post_id=post.id))
    return render_template('blog/edit_post.html', post=post)

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