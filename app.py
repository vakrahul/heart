import os
import json
import re
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import joblib
import numpy as np
import easyocr
import docx
import firebase_admin
from firebase_admin import credentials, auth

# --- Firebase Setup ---
try:
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate("firebase-service-account-key.json") # Update this path
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
    FIREBASE_ENABLED = True
except Exception as e:
    print(f"Warning: Firebase initialization failed: {e}")
    FIREBASE_ENABLED = False

# --- App Configuration & Extensions ---
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['PIC_UPLOAD_FOLDER'] = os.path.join(basedir, 'static/profile_pics')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PIC_UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Load ML Model, Scaler, and OCR Reader ---
try:
    model = joblib.load('heart_model.joblib')
    scaler = joblib.load('scaler.joblib')
    print("ML Model and Scaler loaded successfully.")
except FileNotFoundError:
    model, scaler = None, None
    print("WARNING: Model/scaler files not found.")

try:
    reader = easyocr.Reader(['en'])
    print("EasyOCR reader initialized successfully.")
except Exception as e:
    reader = None
    print(f"WARNING: EasyOCR initialization failed: {e}. OCR will be disabled.")

# --- Database Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=True)  # Made nullable for Firebase users
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)  # New field for Firebase UID
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    assessments = db.relationship('Assessment', backref='author', lazy=True)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    riskLevel = db.Column(db.Integer, nullable=False)
    riskText = db.Column(db.String(50), nullable=False)
    confidenceScore = db.Column(db.Float, nullable=False)
    inputs = db.Column(db.Text, nullable=False)
    documentName = db.Column(db.String(150), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Firebase Helper Functions ---
def verify_firebase_token(id_token):
    """Verify Firebase ID token and return decoded token"""
    if not FIREBASE_ENABLED:
        return None
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Firebase token verification failed: {e}")
        return None

def get_or_create_user_from_firebase(decoded_token, display_name=None, user_email=None):
    firebase_uid = decoded_token['uid']
    email_from_token = decoded_token.get('email')

    # Use user_email if provided, otherwise fallback to token's email
    email_to_use = user_email if user_email else email_from_token

    # Prioritize the display_name passed as a parameter
    # If not provided, try from decoded_token, then fallback to email prefix
    if not display_name:
        display_name = decoded_token.get('name') or decoded_token.get('display_name')
        if not display_name and email_to_use:
            display_name = email_to_use.split('@')[0]
    
    # If display_name is still None after all attempts, set a generic fallback or the email itself
    if not display_name:
        display_name = email_to_use # Fallback to email if no name found anywhere

    user = User.query.filter_by(firebase_uid=firebase_uid).first()

    if not user:
        # Check if user exists by email (for migration purposes, e.g., if they registered traditionally first)
        user = User.query.filter_by(email=email_to_use).first()
        if user:
            # Update existing user with Firebase UID and the new display name
            user.firebase_uid = firebase_uid
            user.fullName = display_name # Always update with the best available display name
            user.email = email_to_use # Ensure email is consistent
        else:
            # Create new user
            user = User(
                fullName=display_name,
                email=email_to_use,
                firebase_uid=firebase_uid,
                password=None # No password needed for Firebase users
            )
            db.session.add(user)
    else:
        # User already exists by firebase_uid, ensure fullName and email are up-to-date
        user.fullName = display_name
        user.email = email_to_use # Update email in case it changed in Firebase
    
    db.session.commit()
    return user

def calculate_risk_with_model(inputs):
    if not model or not scaler:
        return {"riskLevel": 0, "riskText": "Model Not Loaded", "confidenceScore": 0}
    try:
        feature_order = [
            'male', 'age', 'education', 'currentSmoker', 'cigsPerDay', 'BPMeds',
            'prevalentStroke', 'prevalentHyp', 'diabetes', 'totChol', 'sysBP',
            'diaBP', 'BMI', 'heartRate', 'glucose'
        ]
        input_data = [float(inputs.get(feature, 0)) for feature in feature_order]
        input_array = np.array(input_data).reshape(1, -1)
        scaled_input = scaler.transform(input_array)
        prediction_proba = model.predict_proba(scaled_input)[0]
        risk_level = round(prediction_proba[1] * 100)
        confidence_score = round(max(prediction_proba) * 100, 1)

        if risk_level > 75:
            risk_text = "Very High Risk"
        elif risk_level > 50:
            risk_text = "High Risk"
        elif risk_level > 25:
            risk_text = "Moderate Risk"
        else:
            risk_text = "Low Risk"
        return {"riskLevel": risk_level, "riskText": risk_text, "confidenceScore": confidence_score}
    except Exception as e:
        print(f"Prediction Error: {e}")
        return {"riskLevel": 0, "riskText": "Input Error", "confidenceScore": 0}

@app.cli.command("init-db")
def init_db_command():
    with app.app_context():
        db.create_all()
    print("Initialized the database.")

def get_bot_response(user_message):
    user_message = user_message.lower()
    if "symptom" in user_message:
        return "Common symptoms include chest pain and shortness of breath."
    elif "precaution" in user_message:
        return "To lower risk: eat a balanced diet and exercise regularly."
    else:
        return "Sorry, I can only answer about 'symptoms' or 'precautions'."

def extract_values_from_text(text):
    if not reader:
        return {}
    extracted_data = {}
    text = text.lower()
    patterns = {
        'age': r"age[\s:]*(\d{1,3})",
        'male': r"(?:sex|gender)[\s:]*(?:is\s+)?(?:.*?)?\b(male|female|m|f)\b",  # Improved pattern
        'education': r"(?:education|edu)[\s:]+(\d)",
        'currentSmoker': r"(?:smoker|smoking)[\s:]+(yes|no)",
        'cigsPerDay': r"(?:cigs per day|cigs/day)[\s:]+(\d+)",
        'BPMeds': r"(?:bp meds|medication)[\s:]+(yes|no)",
        'prevalentStroke': r"stroke[\s:]+(yes|no)",
        'prevalentHyp': r"(?:hypertension|prevalent hyp)[\s:]+(yes|no)",
        'diabetes': r"diabetes[\s:]+(yes|no)",
        'totChol': r"(?:total cholesterol|chol)[\s\(\)a-z/]*[:\s]+(\d{2,3})",
        'sysBP': r"(?:systolic bp|sys bp)[\s\(\)a-z/]*[:\s]+(\d{2,3})",
        'diaBP': r"(?:diastolic bp|dia bp)[\s\(\)a-z/]*[:\s]+(\d{2,3})",
        'BMI': r"(?:bmi|body mass index)[\s\(\)]*[:\s]+([\d]+\.?[\d]*)",
        'heartRate': r"(?:heart rate|hr)[\s\(\)a-z]*[:\s]+(\d{2,3})",
        'glucose': r"(?:glucose|blood sugar)[\s\(\)a-z/]*[:\s]+(\d{2,3})"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip().lower()
            # Fixed logic for Sex/Gender
            if key == 'male': # Convert to male field: 1 for male, 0 for female
                if value in ['male', 'm']:
                    extracted_data[key] = '1'
                elif value in ['female', 'f']:
                    extracted_data[key] = '0'
                # If unclear, don't set the value
            elif key in ['currentSmoker', 'BPMeds', 'prevalentStroke', 'prevalentHyp', 'diabetes']:
                extracted_data[key] = '1' if 'yes' in value else '0'
            else:
                extracted_data[key] = value
    return extracted_data

# --- New Firebase Authentication Routes ---
@app.route('/firebase-auth', methods=['POST'])
def firebase_auth():
    """Handle Firebase authentication"""
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        auth_type = data.get('authType', 'login')  # 'login' or 'signup'
        user_email = data.get('userEmail') # Explicitly passed from frontend
        display_name = data.get('displayName') # Explicitly passed from frontend
        firebase_uid = data.get('uid')

        if not id_token:
            return jsonify({"success": False, "message": "No ID token provided"}), 400

        # Verify Firebase token
        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            return jsonify({"success": False, "message": "Invalid token"}), 401

        # Use the provided display_name and user_email from the frontend
        # Fallback to decoded_token if not present (though frontend should provide them)
        final_display_name = display_name if display_name else decoded_token.get('name') or decoded_token.get('display_name')
        final_user_email = user_email if user_email else decoded_token.get('email')

        if not final_display_name and final_user_email:
            final_display_name = final_user_email.split('@')[0]

        if not final_user_email: # Should not happen if Firebase token is valid
            return jsonify({"success": False, "message": "User email not found in token or request."}), 400

        user = get_or_create_user_from_firebase(
            decoded_token,
            display_name=final_display_name,
            user_email=final_user_email
        )

        # Log in the user using Flask-Login
        login_user(user, remember=True)

        # Set session flag for welcome animation if it's a signup
        if auth_type == 'signup':
            session['show_welcome_animation'] = True

        return jsonify({
            "success": True,
            "message": f"Welcome back, {user.fullName}!",
            "redirect": url_for('dashboard')
        })
    except Exception as e:
        print(f"Firebase auth error: {e}")
        return jsonify({"success": False, "message": "Authentication failed"}), 500

# --- Routes (keeping original routes unchanged, removing traditional signup/login handling) ---
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    bot_response = get_bot_response(user_message)
    return jsonify({"response": bot_response})

@app.route('/ocr-process', methods=['POST'])
@login_required
def ocr_process():
    if not reader:
        return jsonify({"error": "OCR system not available"}), 500
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)
    text = ''
    try:
        if file.filename.lower().endswith('.docx'):
            doc = docx.Document(filepath)
            text = " ".join([p.text for p in doc.paragraphs])
        else: # Assume image
            result = reader.readtext(filepath, detail=0)
            text = " ".join(result)
    except Exception as e:
        print(f"OCR Error: {e}")
        return jsonify({"error": "Failed to process file"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
    extracted_data = extract_values_from_text(text)
    return jsonify(extracted_data)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # Removed traditional POST handling, all signup goes via firebase-auth endpoint
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # Removed traditional POST handling, all login goes via firebase-auth endpoint
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    show_animation = session.pop('show_welcome_animation', False)
    assessments = Assessment.query.filter_by(author=current_user).order_by(Assessment.date.desc()).all()
    now = datetime.utcnow()
    monthly_assessments = sum(1 for a in assessments if a.date.year == now.year and a.date.month == now.month)
    chart_labels = [a.date.strftime('%b %d') for a in assessments[:7]][::-1]
    chart_data = [a.riskLevel for a in assessments[:7]][::-1]
    return render_template('dashboard.html', assessments=assessments, monthly_assessments=monthly_assessments, show_animation=show_animation, chart_labels=chart_labels, chart_data=chart_data)

@app.route('/assessment')
@login_required
def assessment():
    return render_template('assessment.html')

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    inputs = {key: request.form.get(key) for key in request.form}
    result = calculate_risk_with_model(inputs)
    new_assessment = Assessment(
        riskLevel=result['riskLevel'],
        riskText=result['riskText'],
        confidenceScore=result['confidenceScore'],
        inputs=json.dumps(inputs),
        author=current_user
    )
    db.session.add(new_assessment)
    db.session.commit()
    return redirect(url_for('result', assessment_id=new_assessment.id))

@app.route('/result/<int:assessment_id>')
@login_required
def result(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.author != current_user:
        return redirect(url_for('dashboard'))
    inputs = json.loads(assessment.inputs)
    risk_factors, precautions, insights_text = [], [], ""
    if assessment.riskLevel > 50:
        insights_text = "Your result suggests a **high probability** of heart disease."
        precautions.append('**Schedule an appointment** with your doctor.')
        if float(inputs.get('sysBP', 0)) > 140:
            risk_factors.append({'title': 'High Blood Pressure', 'description': f"BP of {inputs.get('sysBP')} mmHg is elevated."})
    else:
        insights_text = "Your result indicates a **low probability** of heart disease."
        precautions.append('**Continue with your healthy lifestyle** and regular check-ups.')
    return render_template('result.html', assessment=assessment, inputs=inputs, risk_factors=risk_factors, precautions=precautions, insights_text=insights_text)

@app.route('/profile')
@login_required
def profile():
    assessments = Assessment.query.filter_by(author=current_user).order_by(Assessment.date.desc()).all()
    for assessment in assessments:
        assessment.inputs_dict = json.loads(assessment.inputs)
    return render_template('profile.html', assessments=assessments)

@app.route('/profile/update_pic', methods=['POST'])
@login_required
def update_profile_pic():
    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file.filename != '':
            random_hex = secrets.token_hex(8)
            _, f_ext = os.path.splitext(file.filename)
            picture_fn = random_hex + f_ext
            picture_path = os.path.join(app.config['PIC_UPLOAD_FOLDER'], picture_fn)
            if current_user.image_file != 'default.jpg':
                try:
                    os.remove(os.path.join(app.config['PIC_UPLOAD_FOLDER'], current_user.image_file))
                except OSError:
                    pass
            file.save(picture_path)
            current_user.image_file = picture_fn
            db.session.commit()
            flash('Your profile picture has been updated!', 'success')
    return redirect(url_for('profile'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)