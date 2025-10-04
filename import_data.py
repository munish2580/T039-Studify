# import_data.py
import csv
from server import app, db, User, Student, Teacher # Imports from the configured server file
from werkzeug.security import generate_password_hash

def import_csv_data():
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()

        with open('student_data.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            print("Starting data import...")
            for row in reader:
                if User.query.filter_by(username=row['username']).first():
                    print(f"User '{row['username']}' already exists. Skipping.")
                    continue
                
                hashed_password = generate_password_hash(row['password'])
                new_user = User(username=row['username'], password_hash=hashed_password, role=row['role'])
                db.session.add(new_user)
                db.session.commit()

                if new_user.role == 'student':
                    new_profile = Student(full_name=row['full_name'], user_id=new_user.id)
                    db.session.add(new_profile)
                elif new_user.role == 'teacher':
                    new_profile = Teacher(full_name=row['full_name'], user_id=new_user.id)
                    db.session.add(new_profile)
                
                print(f"Added user: {new_user.username} (Role: {new_user.role})")

        db.session.commit()
        print("\nData import complete!")

if __name__ == '__main__':
    import_csv_data()