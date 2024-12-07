import os


class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///library.db'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
