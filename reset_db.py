from main import app
from models import db
# Use Flask application context to ensure database reset operations are performed correctly

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database tables dropped and recreated.")
