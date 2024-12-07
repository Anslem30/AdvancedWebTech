from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

# Association table for the many-to-many relationship between users and books
user_saved_books = db.Table('user_saved_books',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True)
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)  # Added this line

    saved_books = db.relationship('Book', secondary=user_saved_books,
                                  backref=db.backref('saved_by', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_administrator(self):
        return self.is_admin


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_books_id = db.Column(db.String(50), unique=True, nullable=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    available = db.Column(db.Boolean, default=True)