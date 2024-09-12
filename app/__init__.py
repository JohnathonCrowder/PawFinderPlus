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
        gender = db.Column(db.String(10), nullable=False)
        weight = db.Column(db.Float)
        color = db.Column(db.String(50))
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
            gender = request.form['gender']
            weight = float(request.form['weight']) if request.form['weight'] else None
            color = request.form['color']
            new_dog = Dog(name=name, breed=breed, date_of_birth=date_of_birth, gender=gender, weight=weight, color=color)
            db.session.add(new_dog)
            db.session.commit()
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
            db.session.commit()
            return redirect(url_for('home'))
        return render_template('dog_detail.html', dog=dog)

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    return app