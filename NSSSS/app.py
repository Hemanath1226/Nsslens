import os
from flask import Flask, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename # For secure file handling

# --- Configuration ---
app = Flask(__name__)
# Configure SQLite database (database.db will be created in the same directory)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nss_lens.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress warning
db = SQLAlchemy(app)

# Directory to save uploaded photos
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Create uploads folder if it doesn't exist
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed image file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    vit_id = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False) # In real app, hash this!

    def __repr__(self):
        return f"<User {self.vit_id}>"

class PhotoSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    vit_id = db.Column(db.String(20), nullable=False)
    photo_title = db.Column(db.String(200), nullable=False)
    theme = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(200), nullable=False) # Path to saved photo
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<Photo {self.photo_title} by {self.full_name}>"

# --- Database Initialization (Run this ONCE to create the tables) ---
# You would run this in your terminal or in a separate script/function
# from app import app, db
# with app.app_context():
#     db.create_all()

# --- Routes (API Endpoints) ---

@app.route('/')
def index():
    return redirect(url_for('static', filename='index.html')) # Serve the registration page by default

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        data = request.form
        full_name = data.get('fullName')
        vit_id = data.get('vitId')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirmPassword')

        if not all([full_name, vit_id, email, password, confirm_password]):
            return jsonify({'message': 'All fields are required!'}), 400

        if password != confirm_password:
            return jsonify({'message': 'Passwords do not match!'}), 400

        # Basic VIT ID format validation (should match frontend pattern)
        import re
        if not re.match(r'^[0-9]{2}[A-Z]{3}[0-9]{4}$', vit_id):
            return jsonify({'message': 'Invalid VIT ID format.'}), 400

        # Check if user already exists
        if User.query.filter_by(vit_id=vit_id).first() or User.query.filter_by(email=email).first():
            return jsonify({'message': 'User with this VIT ID or Email already exists!'}), 409 # Conflict

        # In a real application, you would hash the password here:
        # hashed_password = generate_password_hash(password)

        new_user = User(
            full_name=full_name,
            vit_id=vit_id,
            email=email,
            password=password # For demonstration, storing plain password. DO NOT do this in production!
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            return jsonify({'message': 'Registration successful!'}), 201 # Created
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Error registering user: {str(e)}'}), 500


@app.route('/submit_photo', methods=['POST'])
def submit_photo():
    if request.method == 'POST':
        # Get text data
        full_name = request.form.get('fullName')
        vit_id = request.form.get('vitId')
        photo_title = request.form.get('photoTitle')
        theme = request.form.get('theme')
        description = request.form.get('description')

        if not all([full_name, vit_id, photo_title, theme]):
            return jsonify({'message': 'Required fields are missing!'}), 400

        # Basic VIT ID format validation
        import re
        if not re.match(r'^[0-9]{2}[A-Z]{3}[0-9]{4}$', vit_id):
            return jsonify({'message': 'Invalid VIT ID format.'}), 400

        # Handle file upload
        if 'photoFile' not in request.files:
            return jsonify({'message': 'No photo file part in the request!'}), 400
        
        photo_file = request.files['photoFile']
        
        if photo_file.filename == '':
            return jsonify({'message': 'No selected photo file!'}), 400

        if photo_file and allowed_file(photo_file.filename):
            filename = secure_filename(photo_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure unique filename to prevent overwrites (e.g., add timestamp or UUID)
            # For simplicity, we'll just save it directly.
            # In production, consider adding a unique ID to filename.
            
            try:
                photo_file.save(file_path) # Save the file
            except Exception as e:
                return jsonify({'message': f'Error saving file: {str(e)}'}), 500

            new_submission = PhotoSubmission(
                full_name=full_name,
                vit_id=vit_id,
                photo_title=photo_title,
                theme=theme,
                description=description,
                photo_filename=filename # Store only the filename, not full path
            )

            try:
                db.session.add(new_submission)
                db.session.commit()
                return jsonify({'message': 'Photo submitted successfully!'}), 201 # Created
            except Exception as e:
                db.session.rollback()
                # If database insertion fails, delete the saved file
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'message': f'Error saving submission to database: {str(e)}'}), 500
        else:
            return jsonify({'message': 'Invalid file type. Only PNG, JPG, JPEG are allowed!'}), 400


# --- Run the Flask App ---
if __name__ == '__main__':
    # Initialize the database within the app context
    with app.app_context():
        db.create_all() # Creates tables if they don't exist
    app.run(debug=True) # Run in debug mode (auto-reloads on code changes, useful for development)