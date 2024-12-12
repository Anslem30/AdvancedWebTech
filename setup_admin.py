from main import app
from models import db, User


def create_admin():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print("Admin user already exists!")
            return

        # Create new admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')  # Default password set for admin, but can be changed

        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")


if __name__ == '__main__':
    create_admin()
