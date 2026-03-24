import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_babel import Babel, gettext
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from gtts import gTTS
import google.generativeai as genai
import tempfile
import base64
from dotenv import load_dotenv

# ------------------- Flask App Config -------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krishi_sakhi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ------------------- Extensions -------------------
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
babel = Babel(app)

# ------------------- Gemini AI Config -------------------
# Load environment variables from the .env file
load_dotenv()

# Load API key from environment (Google AI Studio key)
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")

if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)
    genai_client = genai.GenerativeModel("gemini-1.5-flash")  # ✅ free-tier friendly model
else:
    genai_client = None
    print("⚠️ Warning: GOOGLE_AI_API_KEY not set. AI features will be unavailable.")

# ------------------- Languages -------------------
LANGUAGES = {
    'en': 'English',
    'ml': 'മലയാളം (Malayalam)',
    'hi': 'हिन्दी (Hindi)',
    'ta': 'தமிழ் (Tamil)',
    'te': 'తెలుగు (Telugu)',
    'kn': 'ಕನ್ನಡ (Kannada)'
}

# ------------------- Database Models -------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    language_preference = db.Column(db.String(5), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farmer_profile = db.relationship('FarmerProfile', backref='user', uselist=False)
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True)
    activities = db.relationship('Activity', backref='user', lazy=True)

class FarmerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    land_size = db.Column(db.Float)
    crop_type = db.Column(db.String(100))
    soil_type = db.Column(db.String(50))
    irrigation_type = db.Column(db.String(50))
    experience_years = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    language = db.Column(db.String(5), default='en')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_recorded = db.Column(db.Date, default=datetime.utcnow)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------- Flask-Login -------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_locale():
    # Check if user is authenticated and has a language preference
    if current_user.is_authenticated and hasattr(current_user, 'language_preference'):
        return current_user.language_preference
    # Fall back to session or browser preference
    return session.get('language', request.accept_languages.best_match(LANGUAGES.keys()) or 'en')

babel.init_app(app, locale_selector=get_locale)

@app.context_processor
def inject_template_vars():
    return {
        'get_locale': get_locale,
        'languages': LANGUAGES
    }

# ------------------- Helper Functions -------------------


# ------------------- Weather API -------------------
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', 'demo-key')
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5"

def get_weather_data(location):
    """
    Fetches weather data from OpenWeather API.
    Returns demo data if no API key is provided.
    """
    try:
        if WEATHER_API_KEY == 'demo-key':
            logging.warning("Using demo weather data (no API key set)")
            # Return demo data
            return {
                'weather': [{'main': 'Clear', 'description': 'clear sky', 'icon': '01d'}],
                'main': {'temp': 28, 'feels_like': 30, 'humidity': 65, 'pressure': 1013},
                'wind': {'speed': 3.5},
                'name': location.split(',')[0] if location else 'Demo Location'
            }
        
        # Build request
        url = f"{WEATHER_BASE_URL}/weather"
        params = {'q': location, 'appid': WEATHER_API_KEY, 'units': 'metric'}
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Weather API failed with status {response.status_code}: {response.text}")
    
    except Exception as e:
        logging.error(f"Weather API error: {e}", exc_info=True)

    # Fallback if API fails
    return {
        'weather': [{'main': 'Clear', 'description': 'clear sky', 'icon': '01d'}],
        'main': {'temp': 28, 'feels_like': 30, 'humidity': 65, 'pressure': 1013},
        'wind': {'speed': 3.5},
        'name': location.split(',')[0] if location else 'Unknown Location'
    }



# Load API key from environment (Google AI Studio key)
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")

if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)
    genai_client = genai.GenerativeModel("gemini-1.5-flash")  # ✅ free-tier friendly model
else:
    genai_client = None
    print("⚠️ Warning: GOOGLE_AI_API_KEY not set. AI features will be unavailable.")

def get_ai_response(message, user_context=None):
    """
    Generate AI response using Google AI Studio (Gemini model).
    Uses gemini-1.5-flash for free-tier friendly performance.
    """
    if not genai_client:
        return "AI service is unavailable because GOOGLE_AI_API_KEY is not set."

    try:
        # Build contextual prompt
        context = "You are Krishi Sakhi, an AI farming assistant for Indian farmers."
        if user_context:
            if user_context.get("location"):
                context += f" Farmer location: {user_context['location']}."
            if user_context.get("crop_type"):
                context += f" Crop: {user_context['crop_type']}."
            if user_context.get("soil_type"):
                context += f" Soil: {user_context['soil_type']}."

        full_prompt = f"{context}\n\nFarmer's question: {message}"

        # Generate response
        response = genai_client.generate_content(full_prompt)

        # Extract text safely
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        elif hasattr(response, "candidates") and response.candidates:
            return response.candidates[0].content.parts[0].text
        else:
            logging.warning("Google AI response missing expected attributes")
            return "I couldn't generate a proper response right now."

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Google AI API error: {error_msg}", exc_info=True)

        # Graceful quota / rate limit handling
        if "quota" in error_msg.lower() or "429" in error_msg:
            return "⚠️ Free usage quota exceeded. Please wait a few minutes and try again."
        elif "SERVICE_DISABLED" in error_msg:
            return "⚠️ Google AI Studio API is not enabled for your project. Please enable it from Google Cloud Console."
        else:
            return "AI service is temporarily unavailable. Please try again later."

# The resource ID for the "Current Daily Price..." dataset from OGD
OGD_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070" 

def get_market_prices_from_ogd(api_key, resource_id):
    """
    Fetches daily market prices from the OGD Platform India API.
    """
    base_url = f"https://api.data.gov.in/resource/{resource_id}"
    params = {
        'api-key': api_key,
        'format': 'json',
        'limit': 100
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        records = data.get('records', [])
        formatted_data = []
        
        for record in records:
            # Safely extract data from the record
            formatted_data.append({
                'name': record.get('commodity', 'N/A').lower(),
                'price_modal': float(record.get('modal_price', 0)),
                'price_min': float(record.get('min_price', 0)),
                'price_max': float(record.get('max_price', 0)),
                'unit': record.get('unit', 'per quintal'),
                'market': record.get('market', 'N/A'),
                'state': record.get('state', 'N/A')
            })
        
        return formatted_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return [] # Return an empty list to avoid errors

# ------------------- Routes -------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        phone_number = request.form['phone_number']
        password = request.form['password']
        language_preference = request.form.get('language_preference', 'en')
        location = request.form.get('location', '')

        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            flash('Phone number already registered!', 'error')
            return render_template('signup.html', languages=LANGUAGES)

        user = User(
            phone_number=phone_number,
            password_hash=generate_password_hash(password),
            language_preference=language_preference
        )
        db.session.add(user)
        db.session.commit()

        profile = FarmerProfile(
            user_id=user.id,
            name=name,
            location=location
        )
        db.session.add(profile)
        db.session.commit()

        login_user(user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('signup.html', languages=LANGUAGES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        password = request.form['password']

        user = User.query.filter_by(phone_number=phone_number).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid phone number or password!', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    weather_data = None
    if current_user.farmer_profile and current_user.farmer_profile.location:
        weather_data = get_weather_data(current_user.farmer_profile.location)

    recent_chats = ChatMessage.query.filter_by(user_id=current_user.id)\
                                   .order_by(ChatMessage.timestamp.desc())\
                                   .limit(5).all()
    recent_activities = Activity.query.filter_by(user_id=current_user.id)\
                                     .order_by(Activity.timestamp.desc())\
                                     .limit(5).all()
    
    # Get the OGD API key from environment variables
    ogd_api_key = os.getenv('OGD_API_KEY')
    
    # Check if the API key was loaded correctly
    if not ogd_api_key:
        logging.error("OGD_API_KEY not found in .env file for dashboard.")
        market_prices_list = []
    else:
        # Call the function with the API key and resource ID
        market_prices_list = get_market_prices_from_ogd(ogd_api_key, OGD_RESOURCE_ID)

    # Convert the list to a dictionary for the dashboard to maintain compatibility
    market_prices_dict = {}
    if market_prices_list:
        # Get only a limited number of top crops for the dashboard view
        top_crops = ['rice', 'wheat', 'sugarcane', 'cotton', 'onion', 'tomato']
        for record in market_prices_list:
            if record['name'] in top_crops:
                market_prices_dict[record['name']] = {
                    'price': record['price_modal'],
                    'unit': record['unit'],
                    # You would need to determine trend and trend_value from historical data, 
                    # for now, using a placeholder.
                    'trend': 'stable', 
                    'trend_value': 0.0
                }
    
    return render_template('dashboard.html',
                           weather=weather_data,
                           recent_chats=recent_chats,
                           recent_activities=recent_activities,
                           market_prices=market_prices_dict)

@app.route('/weather')
@login_required
def weather():
    """Weather information page"""
    weather_data = None
    location = None
    
    if current_user.farmer_profile and current_user.farmer_profile.location:
        location = current_user.farmer_profile.location
        weather_data = get_weather_data(location)
    
    return render_template('weather.html', 
                           weather=weather_data, 
                           location=location)

@app.route('/market_prices')
@login_required
def market_prices():
    """Market prices page with detailed crop information"""
    
    # Get the OGD API key from environment variables
    ogd_api_key = os.getenv('OGD_API_KEY')
    
    if not ogd_api_key:
        print("Error: OGD_API_KEY not found in .env file.")
        prices = []
    else:
        prices = get_market_prices_from_ogd(ogd_api_key, OGD_RESOURCE_ID)
    
    # Get user's preferred language for translations
    user_language = current_user.language_preference if current_user.is_authenticated else 'en'
    
    # Crop name translations based on user language
    crop_translations = {
        'en': {
            'rice': 'Rice', 'wheat': 'Wheat', 'sugarcane': 'Sugarcane',
            'cotton': 'Cotton', 'onion': 'Onion', 'tomato': 'Tomato',
            'potato': 'Potato', 'maize': 'Maize', 'soybean': 'Soybean',
            'pulses': 'Pulses'
        },
        'hi': {
            'rice': 'चावल', 'wheat': 'गेहूँ', 'sugarcane': 'गन्ना',
            'cotton': 'कपास', 'onion': 'प्याज', 'tomato': 'टमाटर',
            'potato': 'आलू', 'maize': 'मक्का', 'soybean': 'सोयाबीन',
            'pulses': 'दालें'
        },
        'ml': {
            'rice': 'അരി', 'wheat': 'ഗോതമ്പ്', 'sugarcane': 'കരിമ്പ്',
            'cotton': 'പരുത്തി', 'onion': 'ഉള്ളി', 'tomato': 'തക്കാളി',
            'potato': 'ഉരുളക്കിഴങ്ങ്', 'maize': 'ചോളം', 'soybean': 'സോയാബീൻ',
            'pulses': 'പയർവർഗങ്ങൾ'
        },
        'ta': {
            'rice': 'அரிசி', 'wheat': 'கோதுமை', 'sugarcane': 'கரும்பு',
            'cotton': 'பருத்தி', 'onion': 'வெங்காயம்', 'tomato': 'தக்காളി',
            'potato': 'உருளைக்கிழങ്ങ്', 'maize': 'சோளம்', 'soybean': 'சோயா',
            'pulses': 'பருப்பு வகைகள்'
        },
        'te': {
            'rice': 'బియ్యం', 'wheat': 'గోధుమ', 'sugarcane': 'చెరకు',
            'cotton': 'పత్తి', 'onion': 'ఉల్లిపాయ', 'tomato': 'టమాట',
            'potato': 'బంగాళాదుంప', 'maize': 'మొక్కజొన్న', 'soybean': 'సోయా',
            'pulses': 'పప్పులు'
        },
        'kn': {
            'rice': 'ಅಕ್ಕಿ', 'wheat': 'ಗೋಧಿ', 'sugarcane': 'ಕಬ್ಬು',
            'cotton': 'ಹತ್ತಿ', 'onion': 'ಈರುಳ್ಳಿ', 'tomato': 'ಟೊಮೇಟೊ',
            'potato': 'ಆಲೂಗಡ್ಡೆ', 'maize': 'ಜೋಳ', 'soybean': 'ಸೋಯಾ',
            'pulses': 'ಕಾಳುಗಳು'
        }
    }
    
    # Add translated crop names to the prices data
    for price in prices:
        crop_name = price['name']
        price['translated_name'] = crop_translations.get(user_language, crop_translations['en']).get(crop_name, crop_name)
    
    return render_template('market_prices.html', market_prices=prices, language=user_language)

@app.route('/activities')
@login_required
def activities():
    """Farming activities page"""
    user_activities = Activity.query.filter_by(user_id=current_user.id)\
                                   .order_by(Activity.timestamp.desc())\
                                   .all()
    return render_template('activities.html', activities=user_activities)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    profile = current_user.farmer_profile
    
    if request.method == 'POST':
        # Handle profile update
        profile.name = request.form.get('name', profile.name)
        profile.location = request.form.get('location', profile.location)
        profile.land_size = float(request.form.get('land_size', 0)) or profile.land_size
        profile.crop_type = request.form.get('crop_type', profile.crop_type)
        profile.soil_type = request.form.get('soil_type', profile.soil_type)
        profile.irrigation_type = request.form.get('irrigation_type', profile.irrigation_type)
        profile.experience_years = int(request.form.get('experience_years', 0)) or profile.experience_years
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    # For GET requests, just render the profile page
    return render_template('profile.html', profile=profile)

@app.route('/chat')
@login_required
def chat():
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id)\
                                   .order_by(ChatMessage.timestamp.asc()).all()
    return render_template('chat.html', chat_history=chat_history)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    user_context = {}
    if current_user.farmer_profile:
        profile = current_user.farmer_profile
        user_context = {
            'location': profile.location,
            'crop_type': profile.crop_type,
            'soil_type': profile.soil_type
        }

    ai_response = get_ai_response(message, user_context)

    chat_message = ChatMessage(
        user_id=current_user.id,
        message=message,
        response=ai_response,
        language=current_user.language_preference
    )
    db.session.add(chat_message)
    db.session.commit()

    return jsonify({
        'response': ai_response,
        'timestamp': datetime.now().strftime('%H:%M')
    })

@app.route('/add_activity', methods=['POST'])
@login_required
def add_activity():
    """Add a new farming activity"""
    activity_type = request.form.get('activity_type')
    description = request.form.get('description')
    
    if not activity_type or not description:
        flash('Please fill in all fields', 'error')
        return redirect(url_for('activities'))
    
    new_activity = Activity(
        user_id=current_user.id,
        activity_type=activity_type,
        description=description
    )
    
    db.session.add(new_activity)
    db.session.commit()
    
    flash('Activity added successfully!', 'success')
    return redirect(url_for('activities'))

@app.route('/change_language/<language>')
def change_language(language):
    if language in LANGUAGES:
        if current_user.is_authenticated:
            current_user.language_preference = language
            db.session.commit()
        else:
            session['language'] = language
            
    return redirect(request.referrer or url_for('index'))

@app.route('/text_to_speech', methods=['POST'])
@login_required
def text_to_speech():
    data = request.get_json()
    text = data.get('text', '')
    language = current_user.language_preference
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        lang_map = {'en': 'en', 'ml': 'ml', 'hi': 'hi', 'ta': 'ta', 'te': 'te', 'kn': 'kn'}
        tts_lang = lang_map.get(language, 'en')
        tts = gTTS(text=text, lang=tts_lang)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts.save(tmp_file.name)
            with open(tmp_file.name, 'rb') as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            os.unlink(tmp_file.name)
            return jsonify({'audio': audio_data})
    except Exception as e:
        logging.error(f"TTS error: {e}")
        return jsonify({'error': 'TTS failed'}), 500

@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    """
    Receives audio from frontend mic and returns text.
    Expects form-data:
    - audio: audio file (wav)
    - language: selected language code (en, te, hi, etc.)
    """
    audio_file = request.files.get('audio')
    language = request.form.get('language', 'en')

    if not audio_file:
        return jsonify({'error': 'No audio file provided'}), 400

    try:
        # For now, return a placeholder since we don't have a real STT service
        # In a real implementation, you would integrate with Google Speech-to-Text or similar
        recognized_text = "This is a demo speech-to-text response. In a real implementation, this would be the transcribed text from your audio."
        
        return jsonify({'text': recognized_text})
    except Exception as e:
        logging.error(f"Speech-to-text error: {e}")
        return jsonify({'error': 'Speech-to-text failed'}), 500

# ------------------- Error Handlers -------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ------------------- Run App -------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
