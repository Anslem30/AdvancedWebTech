from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy database object
db = SQLAlchemy()

# Association table for the many-to-many relationship between users and books
# This allows users to save multiple books, and books to be saved by multiple users
user_saved_books = db.Table('user_saved_books',
                            db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                            db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True)
                            )


class User(db.Model):  # User model representing registered users in the system
    id = db.Column(db.Integer, primary_key=True)  # Primary key for the user
    username = db.Column(db.String(80), unique=True, nullable=False)  # Username with unique constraint
    email = db.Column(db.String(120), unique=True, nullable=False)  # Email with unique constraint
    password_hash = db.Column(db.String(128))  # Hashed password for secure storage
    is_admin = db.Column(db.Boolean, default=False)

    # Relationship to saved books using the association table
    saved_books = db.relationship('Book', secondary=user_saved_books,
                                  backref=db.backref('saved_by', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_administrator(self):
        return self.is_admin


class Book(db.Model):  # Book model representing books in the library
    id = db.Column(db.Integer, primary_key=True)
    google_books_id = db.Column(db.String(50), unique=True, nullable=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    available = db.Column(db.Boolean, default=True)
