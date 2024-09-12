from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dogbreeder.db'
    db.init_app(app)

    class Dog(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        breed = db.Column(db.String(100), nullable=False)
        date_of_birth = db.Column(db.Date, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    with app.app_context():
        db.create_all()

    @app.route('/')
    def home():
        dogs = Dog.query.all()
        return render_template('index.html', dogs=dogs)

    @app.route('/add_dog', methods=['GET', 'POST'])
    def add_dog():
        if request.method == 'POST':
            name = request.form['name']
            breed = request.form['breed']
            date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            new_dog = Dog(name=name, breed=breed, date_of_birth=date_of_birth)
            db.session.add(new_dog)
            db.session.commit()
            return redirect(url_for('home'))
        return render_template('add_dog.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    return app