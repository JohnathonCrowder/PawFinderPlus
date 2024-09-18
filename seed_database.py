# seed_database.py
from app.__init__Old import create_app
from app.extensions import db
from app.models import Dog
from datetime import date
import random

def seed_database():
    app = create_app()
    with app.app_context():
        # First, check if we already have dogs in the database
        if Dog.query.count() > 0:
            print("Database already contains dogs. Skipping seeding.")
            return

        # Sample data
        dog_breeds = [
            "Labrador Retriever", "German Shepherd", "Golden Retriever", 
            "French Bulldog", "Bulldog", "Poodle", "Beagle", 
            "Rottweiler", "Dachshund", "Yorkshire Terrier"
        ]
        
        dog_names = [
            "Max", "Luna", "Charlie", "Lucy", "Cooper", "Bella", "Rocky", 
            "Daisy", "Bailey", "Molly", "Buddy", "Sadie", "Jack", "Maggie", "Oliver"
        ]
        
        dog_colors = [
            "Black", "White", "Brown", "Golden", "Cream", "Gray", 
            "Red", "Blue Merle", "Brindle", "Spotted"
        ]

        # Create 5 sample dogs
        for i in range(5):
            # Generate a random date of birth between 1 and 5 years ago
            years_old = random.randint(1, 5)
            days_old = years_old * 365 + random.randint(-30, 30)  # Add some randomness
            dob = date.today().replace(year=date.today().year - years_old)

            # Create the dog
            new_dog = Dog(
                name=random.choice(dog_names),
                breed=random.choice(dog_breeds),
                date_of_birth=dob,
                gender=random.choice(["Male", "Female"]),
                weight=round(random.uniform(5.0, 30.0), 1),  # Random weight between 5 and 30 kg
                color=random.choice(dog_colors)
            )
            db.session.add(new_dog)
        
        # Commit the changes
        db.session.commit()
        print("Database seeded with 5 sample dogs!")

if __name__ == "__main__":
    seed_database()