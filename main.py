from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, session, request, abort
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from models import Book, User, db
import requests
import secrets

# Initialize Flask application
app = Flask(__name__)
app.static_folder = 'static'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'  # SQLite database configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = secrets.token_hex(16)  # Generate a secure random secret key
db.init_app(app)
GOOGLE_BOOKS_API_KEY = 'AIzaSyDaOLNtdD6eJRa5bnz1fHwCuvRYqpNchnQ'

# Initialize database and add initial books
with app.app_context():
    # Create all database tables
    db.create_all()

    # Add initial books if the database is empty
    if Book.query.count() == 0:
        book1 = Book(title='The Great Gatsby', author='F. Scott Fitzgerald',
                     description='A novel about the Roaring Twenties.')
        book2 = Book(title='To Kill a Mockingbird', author='Harper Lee',
                     description='A story of racial injustice in the American South.')
        book3 = Book(title='1984', author='George Orwell',
                     description='A dystopian novel about a totalitarian society.')
        db.session.add_all([book1, book2, book3])
        db.session.commit()

    # Dynamically add google_books_id column if it doesn't exist
    inspector = db.inspect(db.engine)
    if 'google_books_id' not in [c['name'] for c in inspector.get_columns('book')]:
        db.session.execute(text("ALTER TABLE book ADD COLUMN google_books_id VARCHAR(50)"))
        db.session.commit()


# Home route
@app.route('/')
def home():
    return render_template('index.html')


# Helper function to fetch book preview information from Google Books API
def fetch_book_preview_info(google_books_id):
    """Fetch preview information for a book from Google Books API"""
    url = f'https://www.googleapis.com/books/v1/volumes/{google_books_id}?key={GOOGLE_BOOKS_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            'preview_link': data.get('volumeInfo', {}).get('previewLink'),
            'pdf_link': data.get('accessInfo', {}).get('pdf', {}).get('downloadLink'),
            'epub_link': data.get('accessInfo', {}).get('epub', {}).get('downloadLink'),
            'preview_available': data.get('accessInfo', {}).get('viewability') != 'NO_PAGES',
            'download_available': any([
                data.get('accessInfo', {}).get('pdf', {}).get('isAvailable'),
                data.get('accessInfo', {}).get('epub', {}).get('isAvailable')
            ])
        }


# User dashboard route
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if user_id:
        # Fetch user and their saved books
        user = User.query.get(user_id)
        saved_books = Book.query.filter(
            Book.id.in_([book.id for book in user.saved_books])
        ).all()
        recommended_books = Book.query.limit(3).all()

        # Add preview information to books
        for book in saved_books + recommended_books:
            if book.google_books_id:
                preview_info = fetch_book_preview_info(book.google_books_id)
                if preview_info:
                    book.preview_link = preview_info['preview_link']
                    book.can_preview = preview_info['preview_available']
                    book.can_download = preview_info['download_available']

        return render_template('dashboard.html',
                               user=user,
                               saved_books=saved_books,
                               recommended_books=recommended_books)
    else:
        # Redirect to login page if user is not authenticated
        flash('You need to log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))


# Books listing route with search functionality
@app.route('/books')
def books():
    search_term = request.args.get('search', '').strip()

    # Search books by title or author
    if search_term:
        books = Book.query.filter(
            or_(
                Book.title.ilike(f'%{search_term}%'),
                Book.author.ilike(f'%{search_term}%')
            )
        ).all()
    else:
        books = Book.query.all()

    return render_template('books.html', books=books)


# Route to read a book online
@app.route('/books/<int:book_id>/read')
def read_book(book_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to read books.', 'danger')
        return redirect(url_for('login'))

    book = Book.query.get_or_404(book_id)
    if not book.google_books_id:
        flash('This book is not available for online reading.', 'danger')
        return redirect(url_for('book_detail', book_id=book_id))

    # Fetch preview information
    preview_info = fetch_book_preview_info(book.google_books_id)
    if not preview_info or not preview_info['preview_available']:
        flash('Preview is not available for this book.', 'danger')
        return redirect(url_for('books'))

    return render_template('read_books.html',
                           book=book,
                           preview_link=preview_info['preview_link'],
                           can_download=preview_info['download_available'],
                           pdf_link=preview_info.get('pdf_link'),
                           epub_link=preview_info.get('epub_link'))


# Route to save a book to user's library
@app.route('/books/save/<int:book_id>', methods=['POST'])
def save_book(book_id):
    if not session.get('user_id'):
        flash('Please log in to save books.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    book = Book.query.get_or_404(book_id)

    # Check if book is already in user's library
    if book in user.saved_books:
        flash('This book is already in your library.', 'info')
    else:
        user.saved_books.append(book)
        db.session.commit()
        flash('Book saved to your library.', 'success')

    return redirect(url_for('dashboard'))


# Route to remove a book from user's library
@app.route('/books/remove/<int:book_id>', methods=['POST'])
def remove_saved_book(book_id):
    if not session.get('user_id'):
        flash('Please log in to manage your library.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    book = Book.query.get_or_404(book_id)

    # Remove book from user's saved books
    if book in user.saved_books:
        user.saved_books.remove(book)
        db.session.commit()
        flash('Book removed from your library.', 'success')

    return redirect(url_for('dashboard'))


# Contact page route
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Validate contact form submission
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not all([name, email, subject, message]):
            flash('Please fill in all fields.', 'error')
        else:
            # Placeholder for email sending logic
            flash('Thank you for your message! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))

    return render_template('contact_us.html')


# User registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        try:
            # Create new user with hashed password
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('You have successfully registered. Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            # Handle duplicate email error
            db.session.rollback()
            flash('An account with this email already exists. Please use a different email.', 'danger')
            return render_template('register.html')

    return render_template('register.html')


# User login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Validate user credentials
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('You have been logged in.', 'success')

            # Redirect to admin dashboard if user is an administrator
            if user.is_administrator():
                print(f"User '{user.username}' is an administrator. Redirecting to admin dashboard.")
                return redirect(url_for('admin_dashboard'))
            else:
                print(f"User '{user.username}' is not an administrator. Redirecting to dashboard.")
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')
    return render_template('login.html')


# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


# Decorator to require admin privileges
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in first.', 'danger')
            return redirect(url_for('login'))

        user = User.query.get(user_id)
        if not user or not user.is_administrator():
            abort(403)  # Forbidden access
        return f(*args, **kwargs)

    return decorated_function


# Admin dashboard route
@app.route('/admin')
@admin_required
def admin_dashboard():
    # Retrieve statistics for admin dashboard
    total_books = Book.query.count()
    total_users = User.query.count()
    users = User.query.all()
    recent_books = Book.query.order_by(Book.id.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_books=total_books,
                           total_users=total_users,
                           users=users,
                           recent_books=recent_books)


# Admin books management route
@app.route('/admin/books', methods=['GET', 'POST'])
def admin_books():
    if request.method == 'POST':
        # Add new book from admin form
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        available = 'available' in request.form

        new_book = Book(title=title, author=author, description=description, available=available)
        db.session.add(new_book)
        db.session.commit()

        return redirect(url_for('admin_books'))

    # Retrieve and display all books
    books = Book.query.all()
    return render_template('admin/books.html', books=books)


# Route to delete a book
@app.route('/admin/books/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('admin_books'))


# Route to edit a book
@app.route('/admin/books/<int:book_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_book(book_id):
    book = Book.query.get_or_404(book_id)

    if request.method == 'POST':
        # Update book details
        book.title = request.form['title']
        book.author = request.form['author']
        book.description = request.form['description']
        book.available = 'available' in request.form

        db.session.commit()
        flash('Book updated successfully.', 'success')
        return redirect(url_for('admin_books'))

    return render_template('admin/edit_book.html', book=book)


# Route to manage users
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)


# Route to toggle admin status
@app.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin_status(user_id):
    user = User.query.get_or_404(user_id)
    # Prevent self-demotion
    if user.id != session.get('user_id'):
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f'Admin status updated for {user.username}', 'success')
    else:
        flash('You cannot modify your own admin status', 'danger')
    return redirect(url_for('admin_users'))


# Route to populate books from Google Books API
@app.route('/admin/books/populate', methods=['GET', 'POST'])
@admin_required
def populate_books():
    if request.method == 'POST':
        # Fetch books from Google Books API
        query = request.form.get('query', 'popular books')
        books_data = fetch_books_from_google(query)
        added_count = 0

        # Add books to database
        for book_data in books_data:
            volume_info = book_data.get('volumeInfo', {})
            title = volume_info.get('title')
            authors = volume_info.get('authors', [])
            description = volume_info.get('description', '')
            google_books_id = book_data.get('id')

            if title and authors:
                # Check for duplicates
                existing_book = Book.query.filter_by(google_books_id=google_books_id).first()
                if not existing_book:
                    new_book = Book(
                        title=title,
                        author=', '.join(authors),
                        description=description[:500],
                        google_books_id=google_books_id
                    )
                    db.session.add(new_book)
                    added_count += 1

        db.session.commit()
        flash(f'Added {added_count} new books to the database.', 'success')
    return render_template('admin/populate_books.html')


# Helper function to fetch books from Google Books API
def fetch_books_from_google(query, max_results=40):
    url = f'https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}&key={GOOGLE_BOOKS_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('items', [])
    else:
        return []


    app.debug = False

# Main application entry point
if __name__ == '__main__':
    app.run()
