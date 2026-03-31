import os
import json
import logging
import tempfile
import base64
import requests # type: ignore
from datetime import datetime
from typing import Any, Union, cast, Optional, List, Dict

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session # type: ignore
from flask_sqlalchemy import SQLAlchemy # type: ignore
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user # type: ignore
from flask_babel import Babel, gettext # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from gtts import gTTS # type: ignore
import google.generativeai as genai # type: ignore
from dotenv import load_dotenv # type: ignore

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# Load environment variables from the .env file
load_dotenv()

# Gemini AI Config
GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")

if GOOGLE_AI_API_KEY:
    # Remove quotes and whitespace that might be in the .env value
    clean_key = str(GOOGLE_AI_API_KEY).strip().strip('"').strip("'")
    genai.configure(api_key=clean_key)
    genai_client = genai.GenerativeModel("gemini-1.5-flash")
    # Using a safe way to show key prefix to satisfy linter
    key_prefix = clean_key[:8] if len(clean_key) >= 8 else clean_key
    logging.info(f"Google AI API configured with key starting with: {key_prefix}...")
else:
    genai_client = None
    logging.warning("GOOGLE_AI_API_KEY not found in environment. AI Assistant will be disabled.")

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
    id: int = db.Column(db.Integer, primary_key=True)
    phone_number: str = db.Column(db.String(15), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(128), nullable=False)
    language_preference: str = db.Column(db.String(5), default='en')
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)

    farmer_profile = db.relationship('FarmerProfile', backref='user', uselist=False)
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True)
    activities = db.relationship('Activity', backref='user', lazy=True)

class FarmerProfile(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name: str = db.Column(db.String(100), nullable=False)
    location: Optional[str] = db.Column(db.String(100), nullable=True)
    land_size: Optional[float] = db.Column(db.Float)
    crop_type: Optional[str] = db.Column(db.String(100))
    soil_type: Optional[str] = db.Column(db.String(50))
    irrigation_type: Optional[str] = db.Column(db.String(50))
    experience_years: Optional[int] = db.Column(db.Integer)
    updated_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatMessage(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message: str = db.Column(db.Text, nullable=False)
    response: str = db.Column(db.Text)
    timestamp: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    language: str = db.Column(db.String(5), default='en')

class Activity(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type: str = db.Column(db.String(50), nullable=False)
    description: str = db.Column(db.Text, nullable=False)
    date_recorded: datetime = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    timestamp: datetime = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------- Flask-Login -------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
            return f"❌ Google API Error: {error_msg}"

# The resource ID for the "Current Daily Price..." dataset from OGD
OGD_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070" 

CROP_IMAGES = {
    'rice':         'https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=300&q=80',
    'wheat':        'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=300&q=80',
    'sugarcane':    'https://images.unsplash.com/photo-1594911771101-fa08124f5933?auto=format&fit=crop&w=300&q=80',
    'cotton':       'https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?auto=format&fit=crop&w=300&q=80',
    'onion':        'https://images.unsplash.com/photo-1508747703725-719777637510?auto=format&fit=crop&w=300&q=80',
    'tomato':       'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=300&q=80',
    'potato':       'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=300&q=80',
    'maize':        'https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=300&q=80',
    'corn':         'https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=300&q=80',
    'soybean':      'https://images.unsplash.com/photo-1595855759920-86582396756a?auto=format&fit=crop&w=300&q=80',
    'carrot':       'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?auto=format&fit=crop&w=300&q=80',
    'banana':       'https://images.unsplash.com/photo-1528825871115-3581a5387919?auto=format&fit=crop&w=300&q=80',
    'mango':        'https://images.unsplash.com/photo-1601493700631-2b16ec4b4716?auto=format&fit=crop&w=300&q=80',
    'apple':        'https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?auto=format&fit=crop&w=300&q=80',
    'grapes':       'https://images.unsplash.com/photo-1537640538966-79f369143f8f?auto=format&fit=crop&w=300&q=80',
    'grape':        'https://images.unsplash.com/photo-1537640538966-79f369143f8f?auto=format&fit=crop&w=300&q=80',
    'garlic':       'https://images.unsplash.com/photo-1615397349754-cfa2066a298e?auto=format&fit=crop&w=300&q=80',
    'ginger':       'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?auto=format&fit=crop&w=300&q=80',
    'turmeric':     'https://images.unsplash.com/photo-1615485291234-9d694218aeb3?auto=format&fit=crop&w=300&q=80',
    'chilli':       'https://images.unsplash.com/photo-1583119022894-919a68a3d0e3?auto=format&fit=crop&w=300&q=80',
    'chili':        'https://images.unsplash.com/photo-1583119022894-919a68a3d0e3?auto=format&fit=crop&w=300&q=80',
    'pepper':       'https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?auto=format&fit=crop&w=300&q=80',
    'capsicum':     'https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?auto=format&fit=crop&w=300&q=80',
    'peas':         'https://images.unsplash.com/photo-1587735243615-c03f25aaff15?auto=format&fit=crop&w=300&q=80',
    'beans':        'https://images.unsplash.com/photo-1567306301408-9b74779a11af?auto=format&fit=crop&w=300&q=80',
    'bottle gourd': 'https://images.unsplash.com/photo-1556801712-76c379107f77?auto=format&fit=crop&w=300&q=80',
    'brinjal':      'https://images.unsplash.com/photo-1568584711075-3d021a7c3ca3?auto=format&fit=crop&w=300&q=80',
    'eggplant':     'https://images.unsplash.com/photo-1568584711075-3d021a7c3ca3?auto=format&fit=crop&w=300&q=80',
    'cabbage':      'https://images.unsplash.com/photo-1594282486552-05b4d80fbb9f?auto=format&fit=crop&w=300&q=80',
    'cauliflower':  'https://images.unsplash.com/photo-1568584711271-de36b87dc7b6?auto=format&fit=crop&w=300&q=80',
    'spinach':      'https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=300&q=80',
    'amaranthus':   'https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=300&q=80',
    'coriander':    'https://images.unsplash.com/photo-1601315379734-425a469078e4?auto=format&fit=crop&w=300&q=80',
    'bitter gourd': 'https://images.unsplash.com/photo-1607305387299-a3d9611cd469?auto=format&fit=crop&w=300&q=80',
    'cucumber':     'https://images.unsplash.com/photo-1604977042946-1eecc30f269e?auto=format&fit=crop&w=300&q=80',
    'pumpkin':      'https://images.unsplash.com/photo-1570586437263-ab629fccc818?auto=format&fit=crop&w=300&q=80',
    'radish':       'https://images.unsplash.com/photo-1582284540020-8acbe03f4924?auto=format&fit=crop&w=300&q=80',
    'drumstick':    'https://images.unsplash.com/photo-1567306301408-9b74779a11af?auto=format&fit=crop&w=300&q=80',
    'orange':       'https://images.unsplash.com/photo-1547514701-42782101795e?auto=format&fit=crop&w=300&q=80',
    'lemon':        'https://images.unsplash.com/photo-1590502593747-42a996133562?auto=format&fit=crop&w=300&q=80',
    'lime':         'https://images.unsplash.com/photo-1590502593747-42a996133562?auto=format&fit=crop&w=300&q=80',
    'groundnut':    'https://images.unsplash.com/photo-1567306301408-9b74779a11af?auto=format&fit=crop&w=300&q=80',
    'peanut':       'https://images.unsplash.com/photo-1567306301408-9b74779a11af?auto=format&fit=crop&w=300&q=80',
    'sunflower':    'https://images.unsplash.com/photo-1597848212624-a19eb35e2651?auto=format&fit=crop&w=300&q=80',
    'mustard':      'https://images.unsplash.com/photo-1615485290368-0c7f27c489a5?auto=format&fit=crop&w=300&q=80',
    'jowar':        'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=300&q=80',
    'bajra':        'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=300&q=80',
    'arhar':        'https://images.unsplash.com/photo-1567306301408-9b74779a11af?auto=format&fit=crop&w=300&q=80',
    'moong':        'https://images.unsplash.com/photo-1567306301408-9b74779a11af?auto=format&fit=crop&w=300&q=80',
    'urad':         'https://images.unsplash.com/photo-1567306301408-9b74779a11af?auto=format&fit=crop&w=300&q=80',
    'lentil':       'https://images.unsplash.com/photo-1534483509719-3feaee7c30da?auto=format&fit=crop&w=300&q=80',
    'coconut':      'https://images.unsplash.com/photo-1555694702-a8e3e3463d91?auto=format&fit=crop&w=300&q=80',
    'watermelon':   'https://images.unsplash.com/photo-1563114773-84221bd62daa?auto=format&fit=crop&w=300&q=80',
    'papaya':       'https://images.unsplash.com/photo-1526318472351-c75fcf070305?auto=format&fit=crop&w=300&q=80',
    'pomegranate':  'https://images.unsplash.com/photo-1541344999736-83eca272f6fc?auto=format&fit=crop&w=300&q=80',
}
DEFAULT_CROP_IMAGE = 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=300&q=80'

def get_crop_image(crop_name):
    """Returns the best matching crop image URL for a given crop name."""
    name = crop_name.lower().strip()
    # Exact match first
    if name in CROP_IMAGES:
        return CROP_IMAGES[name]
    # Partial match: crop key is a word inside the crop name
    for key, url in CROP_IMAGES.items():
        if key in name:
            return url
    return DEFAULT_CROP_IMAGE

def get_market_prices_from_ogd(api_key, resource_id):
    """
    Fetches daily market prices from the OGD Platform India API.
    """
    base_url = f"https://api.data.gov.in/resource/{resource_id}"
    params = {
        'api-key': api_key,
        'format': 'json',
        'limit': 300
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=45)
        response.raise_for_status()
        data = response.json()
        
        records = data.get('records', [])
        formatted_data: List[Dict[str, Any]] = []
        
        for record in records:
            try:
                formatted_data.append({
                    'name': str(record.get('commodity') or 'N/A').lower().strip(),
                    'price_modal': float(record.get('modal_price') or 0),
                    'price_min': float(record.get('min_price') or 0),
                    'price_max': float(record.get('max_price') or 0),
                    'unit': str(record.get('unit') or 'per quintal'),
                    'market': str(record.get('market') or 'N/A'),
                    'state': str(record.get('state') or 'N/A')
                })
            except (ValueError, TypeError):
                continue
        
        return formatted_data

    except requests.exceptions.Timeout:
        logging.warning("OGD API timed out, returning demo data")
        return _get_demo_market_prices()
    except requests.exceptions.RequestException as e:
        logging.warning(f"OGD API error: {e}, returning demo data")
        return _get_demo_market_prices()

def _get_demo_market_prices():
    """Returns expanded demo market price data when the API is unavailable."""
    return [
        {'name': 'rice', 'price_modal': 2183, 'price_min': 2000, 'price_max': 2400, 'unit': 'per quintal', 'market': 'Karnal APMC', 'state': 'Haryana'},
        {'name': 'wheat', 'price_modal': 2275, 'price_min': 2100, 'price_max': 2450, 'unit': 'per quintal', 'market': 'Ludhiana APMC', 'state': 'Punjab'},
        {'name': 'onion', 'price_modal': 1850, 'price_min': 1600, 'price_max': 2100, 'unit': 'per quintal', 'market': 'Lasalgaon APMC', 'state': 'Maharashtra'},
        {'name': 'tomato', 'price_modal': 2400, 'price_min': 2000, 'price_max': 2800, 'unit': 'per quintal', 'market': 'Kolar APMC', 'state': 'Karnataka'},
        {'name': 'potato', 'price_modal': 1200, 'price_min': 1000, 'price_max': 1400, 'unit': 'per quintal', 'market': 'Agra APMC', 'state': 'Uttar Pradesh'},
        {'name': 'cotton', 'price_modal': 6830, 'price_min': 6500, 'price_max': 7200, 'unit': 'per quintal', 'market': 'Rajkot APMC', 'state': 'Gujarat'},
        {'name': 'sugarcane', 'price_modal': 350, 'price_min': 320, 'price_max': 380, 'unit': 'per quintal', 'market': 'Pune APMC', 'state': 'Maharashtra'},
        {'name': 'maize', 'price_modal': 1950, 'price_min': 1800, 'price_max': 2100, 'unit': 'per quintal', 'market': 'Gulbarga APMC', 'state': 'Karnataka'},
        {'name': 'soybean', 'price_modal': 4500, 'price_min': 4200, 'price_max': 4800, 'unit': 'per quintal', 'market': 'Indore APMC', 'state': 'Madhya Pradesh'},
        {'name': 'carrot', 'price_modal': 2800, 'price_min': 2400, 'price_max': 3200, 'unit': 'per quintal', 'market': 'Jaipur APMC', 'state': 'Rajasthan'},
        {'name': 'banana', 'price_modal': 1500, 'price_min': 1200, 'price_max': 1800, 'unit': 'per quintal', 'market': 'Jalgaon APMC', 'state': 'Maharashtra'},
        {'name': 'grapes', 'price_modal': 4500, 'price_min': 4000, 'price_max': 5200, 'unit': 'per quintal', 'market': 'Nashik APMC', 'state': 'Maharashtra'},
        {'name': 'garlic', 'price_modal': 8500, 'price_min': 7500, 'price_max': 9500, 'unit': 'per quintal', 'market': 'Mandsaur APMC', 'state': 'Madhya Pradesh'},
        {'name': 'ginger', 'price_modal': 6200, 'price_min': 5800, 'price_max': 6800, 'unit': 'per quintal', 'market': 'Kochi APMC', 'state': 'Kerala'},
        {'name': 'chilli', 'price_modal': 12500, 'price_min': 11000, 'price_max': 14000, 'unit': 'per quintal', 'market': 'Guntur APMC', 'state': 'Andhra Pradesh'},
        {'name': 'capsicum', 'price_modal': 3200, 'price_min': 2800, 'price_max': 3600, 'unit': 'per quintal', 'market': 'Solan APMC', 'state': 'Himachal Pradesh'},
        {'name': 'cauliflower', 'price_modal': 1800, 'price_min': 1500, 'price_max': 2200, 'unit': 'per quintal', 'market': 'Bareilly APMC', 'state': 'Uttar Pradesh'},
        {'name': 'cabbage', 'price_modal': 900, 'price_min': 700, 'price_max': 1100, 'unit': 'per quintal', 'market': 'Sonipat APMC', 'state': 'Haryana'},
        {'name': 'coconut', 'price_modal': 2500, 'price_min': 2200, 'price_max': 2800, 'unit': 'per 1000 nuts', 'market': 'Kozhikode APMC', 'state': 'Kerala'},
        {'name': 'mango', 'price_modal': 4200, 'price_min': 3500, 'price_max': 5000, 'unit': 'per quintal', 'market': 'Ratnagiri APMC', 'state': 'Maharashtra'},
        {'name': 'orange', 'price_modal': 3800, 'price_min': 3200, 'price_max': 4500, 'unit': 'per quintal', 'market': 'Nagpur APMC', 'state': 'Maharashtra'},
        {'name': 'lentil', 'price_modal': 6400, 'price_min': 6000, 'price_max': 6800, 'unit': 'per quintal', 'market': 'Sagar APMC', 'state': 'Madhya Pradesh'},
    ]

# ------------------- Routes -------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            phone_number = data.get('phone_number')
            password = data.get('password')
            language_preference = data.get('language_preference', 'en')
            location = data.get('location', '')
        else:
            name = request.form.get('name')
            phone_number = request.form.get('phone_number')
            password = request.form.get('password')
            language_preference = request.form.get('language_preference', 'en')
            location = request.form.get('location', '')

        if not phone_number or not password:
            if request.is_json:
                return jsonify({'status': 'error', 'message': 'Missing fields'}), 400
            flash('Missing fields!', 'error')
            return render_template('signup.html', languages=LANGUAGES)

        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            if request.is_json:
                return jsonify({'status': 'error', 'message': 'Phone already registered'}), 400
            flash('Phone number already registered!', 'error')
            return render_template('signup.html', languages=LANGUAGES)

        user = User(
            phone_number=phone_number, # type: ignore
            password_hash=generate_password_hash(password), # type: ignore
            language_preference=language_preference # type: ignore
        )
        db.session.add(user)
        db.session.commit()

        profile = FarmerProfile(
            user_id=user.id, # type: ignore
            name=name, # type: ignore
            location=location # type: ignore
        )
        db.session.add(profile)
        db.session.commit()

        login_user(user)
        if request.is_json:
            return jsonify({'status': 'success', 'message': 'Account created'})
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('signup.html', languages=LANGUAGES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            phone_number = data.get('phone_number')
            password = data.get('password')
        else:
            phone_number = request.form.get('phone_number')
            password = request.form.get('password')

        user = None
        if phone_number:
            user = User.query.filter_by(phone_number=phone_number).first()
            if user and not check_password_hash(user.password_hash, password):
                user = None
        else:
            # Login by password only
            all_users = User.query.filter(User.password_hash != None).all()
            for u in all_users:
                if check_password_hash(u.password_hash, password):
                    user = u
                    break

        if user:
            login_user(user)
            if request.is_json or request.args.get('format') == 'json':
                return jsonify({'status': 'success', 'message': 'Logged in successfully', 'user_id': user.id})
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            msg = 'Invalid password!' if not phone_number else 'Invalid phone number or password!'
            if request.is_json:
                return jsonify({'status': 'error', 'message': msg}), 401
            flash(msg, 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    weather_data = None
    if current_user.farmer_profile and current_user.farmer_profile.location:
        weather_data = get_weather_data(current_user.farmer_profile.location)

    recent_chats = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.desc()).limit(5).all() # type: ignore
    recent_activities = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.timestamp.desc()).limit(5).all() # type: ignore
    
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
        top_crops = ['rice', 'wheat', 'sugarcane', 'cotton', 'onion', 'tomato', 'potato', 'maize', 'soybean']
        seen = set()
        for record in market_prices_list:
            crop = str(record.get('name', ''))
            matched = next((c for c in top_crops if c in crop or crop in c), None)
            if matched and matched not in seen:
                market_prices_dict[matched] = {
                    'price': record['price_modal'],
                    'unit': record['unit'],
                    'trend': 'stable',
                    'trend_value': 0.0
                }
                seen.add(matched)
    
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
            'pulses': 'Pulses', 'carrot': 'Carrot', 'banana': 'Banana',
            'grapes': 'Grapes', 'garlic': 'Garlic', 'ginger': 'Ginger',
            'chilli': 'Chilli', 'capsicum': 'Capsicum', 'cauliflower': 'Cauliflower',
            'cabbage': 'Cabbage', 'coconut': 'Coconut', 'mango': 'Mango',
            'orange': 'Orange', 'lentil': 'Lentil'
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
    
    # Build a fresh list with translations and images (safe for linter)
    detailed_prices: List[Dict[str, Any]] = []
    
    for p in prices:
        crop_name = str(p.get('name', ''))
        # Get language mapping
        lang_dict = crop_translations.get(user_language, crop_translations['en'])
        
        # Translate name
        translated = lang_dict.get(crop_name)
        if not translated:
            translated = next((v for k, v in lang_dict.items() if k in crop_name), crop_name.capitalize())
            
        # Create a clean record
        record = {
            'name': crop_name,
            'translated_name': translated,
            'price_modal': p.get('price_modal', 0),
            'price_min': p.get('price_min', 0),
            'price_max': p.get('price_max', 0),
            'unit': p.get('unit', 'per quintal'),
            'market': p.get('market', 'N/A'),
            'state': p.get('state', 'N/A'),
            'img_url': get_crop_image(crop_name)
        }
        detailed_prices.append(record)
    
    return render_template('market_prices.html', market_prices=detailed_prices, language=user_language)

@app.route('/activities')
@login_required
def activities():
    """Farming activities page"""
    user_activities = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.timestamp.desc()).all() # type: ignore
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
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.asc()).all() # type: ignore
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
        user_id=current_user.id, # type: ignore
        message=message, # type: ignore
        response=ai_response, # type: ignore
        language=current_user.language_preference # type: ignore
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
        user_id=current_user.id, # type: ignore
        activity_type=activity_type, # type: ignore
        description=description # type: ignore
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

# ------------------- REST API Endpoints (Mobile App Support) -------------------

@app.route('/api/dashboard')
@login_required
def api_dashboard():
    """Returns dashboard data for mobile app as JSON"""
    weather_data = None
    if current_user.farmer_profile and current_user.farmer_profile.location:
        weather_data = get_weather_data(current_user.farmer_profile.location)

    # Market prices
    ogd_api_key = os.getenv('OGD_API_KEY')
    market_prices_list = get_market_prices_from_ogd(ogd_api_key, OGD_RESOURCE_ID) if ogd_api_key else []
    
    top_crops = ['rice', 'wheat', 'sugarcane', 'cotton', 'onion']
    filtered_prices = []
    seen = set()
    for p in market_prices_list:
        name = str(p.get('name', '')).lower()
        matched = next((c for c in top_crops if c in str(name)), None)
        if matched and matched not in seen:
            p_copy = dict(p)
            p_copy['img_url'] = get_crop_image(matched)
            filtered_prices.append(p_copy)
            seen.add(matched)

    recent_chats = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.desc()).limit(3).all()
    
    return jsonify({
        'weather': weather_data,
        'market_prices': filtered_prices,
        'recent_messages': [{'msg': c.message, 'resp': c.response[:100] + '...'} for c in recent_chats],
        'user': {
            'name': current_user.farmer_profile.name if current_user.farmer_profile else 'Farmer',
            'language': current_user.language_preference
        }
    })

@app.route('/api/market_prices')
@login_required
def api_market_prices():
    """Returns full market price list as JSON for mobile"""
    ogd_api_key = os.getenv('OGD_API_KEY')
    prices = get_market_prices_from_ogd(ogd_api_key, OGD_RESOURCE_ID) if ogd_api_key else []
    
    detailed_prices = []
    for p in prices:
        p_copy = dict(p)
        p_copy['img_url'] = get_crop_image(p_copy.get('name', ''))
        detailed_prices.append(p_copy)
        
    return jsonify({'status': 'success', 'data': detailed_prices})

@app.route('/api/activities', methods=['GET', 'POST'])
@login_required
def api_activities():
    """Mobile endpoint for viewing and adding farm activities"""
    if request.method == 'POST':
        data = request.get_json()
        activity_type = data.get('activity_type')
        description = data.get('description')
        
        if not activity_type or not description:
            return jsonify({'status': 'error', 'message': 'Missing fields'}), 400
            
        new_act = Activity(user_id=current_user.id, activity_type=activity_type, description=description) # type: ignore
        db.session.add(new_act)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Activity recorded'})

    # GET request
    acts = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.timestamp.desc()).all()
    return jsonify({
        'status': 'success',
        'activities': [{
            'id': a.id,
            'type': a.activity_type,
            'desc': a.description,
            'date': a.date_recorded.strftime('%Y-%m-%d') if a.date_recorded else None
        } for a in acts]
    })

@app.route('/api/profile')
@login_required
def api_profile():
    """Returns user profile data for mobile"""
    p = current_user.farmer_profile
    if not p:
        return jsonify({'error': 'Profile not found'}), 404
        
    return jsonify({
        'name': p.name,
        'location': p.location,
        'crops': p.crop_type,
        'land_size': p.land_size,
        'experience': p.experience_years,
        'language': current_user.language_preference
    })

# ------------------- Original TTS/STT Routes -------------------
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
