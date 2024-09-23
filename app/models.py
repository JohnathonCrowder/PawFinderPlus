# app/models.py
from .extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import LargeBinary, Table
from enum import Enum
from datetime import datetime


class DogStatus(Enum):
    AVAILABLE_NOW = "Available Now"
    AVAILABLE_SOON = "Available Soon"
    RESERVED = "Reserved"
    SOLD = "Sold"
    NOT_FOR_SALE = "Not for Sale"

class AppointmentCategory(Enum):
    CHECKUP = "Check-up"
    VACCINATION = "Vaccination"
    SURGERY = "Surgery"
    OTHER = "Other"

class AccountType(Enum):
    FREE = "Free"
    BASIC = "Basic"
    PREMIUM = "Premium"

# Add User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    dogs = db.relationship('Dog', backref='owner', lazy=True)

    #Account Type
    account_type = db.Column(db.Enum(AccountType), default=AccountType.FREE)

    #Contact Info
    website = db.Column(db.String(200))
    facebook = db.Column(db.String(200))
    instagram = db.Column(db.String(200))
    
    # New profile fields
    full_name = db.Column(db.String(120))
    location = db.Column(db.String(120))
    phone_number = db.Column(db.String(20))
    bio = db.Column(db.Text)

    # Profile picture stored directly in the database
    profile_picture_data = db.Column(LargeBinary)
    profile_picture_filename = db.Column(db.String(255))
    profile_picture_mimetype = db.Column(db.String(50))

    #Location
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    #Admin
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def public_dogs_count(self):
        return Dog.query.filter_by(user_id=self.id, is_public=True).count()

    @property
    def public_litters_count(self):
        return Litter.query.filter_by(user_id=self.id, is_public=True).count()

    @property
    def dogs_for_sale_count(self):
        return Dog.query.filter(Dog.user_id == self.id, 
                                Dog.is_public == True, 
                                Dog.status.in_([DogStatus.AVAILABLE_NOW, DogStatus.AVAILABLE_SOON])).count()

    def can_make_litter_public(self):
        if self.account_type == AccountType.FREE:
            return False
        elif self.account_type == AccountType.BASIC:
            return self.public_litters_count < 8
        else:  # PREMIUM
            return self.public_litters_count < 20

    def can_make_litter_public(self):
        if self.account_type == AccountType.FREE:
            return False
        elif self.account_type == AccountType.BASIC:
            return self.public_litters_count < 8
        else:  # PREMIUM
            return self.public_litters_count < 20

    def can_sell_dogs(self):
        return self.account_type != AccountType.FREE
    







class Dog(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    breed = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    weight = db.Column(db.Float)
    color = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.relationship('DogImage', backref='dog', lazy=True, cascade="all, delete-orphan")
    father_id = db.Column(db.Integer, db.ForeignKey('dog.id'))
    mother_id = db.Column(db.Integer, db.ForeignKey('dog.id'))
    father = db.relationship('Dog', remote_side=[id], backref='offspring_as_father', foreign_keys=[father_id])
    mother = db.relationship('Dog', remote_side=[id], backref='offspring_as_mother', foreign_keys=[mother_id])
    is_public = db.Column(db.Boolean, default=True)
    status = db.Column(db.Enum(DogStatus), default=DogStatus.AVAILABLE_NOW)
    price = db.Column(db.Float)
    vet_appointments = db.relationship('VetAppointment', back_populates='dog', lazy=True, cascade="all, delete-orphan")

    # Add a property to easily access the dog's litter
    @property
    def litter(self):
        return Litter.query.filter(
            (Litter.puppies.any(id=self.id))
        ).first()
    


class DogImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(LargeBinary, nullable=False)  # Store image data
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(50), nullable=False)  # Store mimetype
    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)






class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(50), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    
class VetAppointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    veterinarian = db.Column(db.String(100))
    location = db.Column(db.String(200))
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.Enum(AppointmentCategory), default=AppointmentCategory.OTHER)

    dog = db.relationship('Dog', back_populates='vet_appointments')

class Litter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    father_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    mother_id = db.Column(db.Integer, db.ForeignKey('dog.id'), nullable=False)
    father = db.relationship('Dog', foreign_keys=[father_id])
    mother = db.relationship('Dog', foreign_keys=[mother_id])
    puppies = db.relationship('Dog', secondary='litter_puppy', backref='litter')
    images = db.relationship('LitterImage', backref='litter', lazy=True, cascade="all, delete-orphan")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='litters')
    is_public = db.Column(db.Boolean, default=True)

    # Ensure puppies relationship is properly defined
    puppies = db.relationship('Dog', 
        secondary='litter_puppy', 
        backref=db.backref('litters', lazy='dynamic'),
        lazy='joined'  # This will eager load the puppies
    )

litter_puppy = db.Table('litter_puppy',
    db.Column('litter_id', db.Integer, db.ForeignKey('litter.id'), primary_key=True),
    db.Column('dog_id', db.Integer, db.ForeignKey('dog.id'), primary_key=True)
)


class LitterImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(LargeBinary, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(50), nullable=False)
    litter_id = db.Column(db.Integer, db.ForeignKey('litter.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


# Add this association table for the many-to-many relationship
blog_post_category = Table('blog_post_category', db.Model.metadata,
    db.Column('blog_post_id', db.Integer, db.ForeignKey('blog_post.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)
    
    # New image fields
    image_data = db.Column(db.LargeBinary)
    image_filename = db.Column(db.String(255))
    image_mimetype = db.Column(db.String(50))

    author = db.relationship('User', backref='blog_posts')
    categories = db.relationship('Category', secondary=blog_post_category, back_populates='posts')

    is_featured = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<BlogPost {self.title}>'
    

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('BlogPost', secondary=blog_post_category, back_populates='categories')

    def __repr__(self):
        return f'<Category {self.name}>'