"""
Flask application for Fake Review Detection
Main entry point for the web application
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
import numpy as np
from scipy.sparse import csr_matrix
from collections import Counter, defaultdict

# Initialize NLTK resources FIRST, before importing any ML modules
print("\n" + "="*60)
print("INITIALIZING APPLICATION...")
print("="*60)
print("[APP_INIT] Step 1: Initializing NLTK resources...")
try:
    from model.nltk_init import ensure_nltk_resources, verify_nltk_ready
    ensure_nltk_resources()
    verify_nltk_ready()
    print("[APP_INIT] âœ“ NLTK initialization complete")
except Exception as e:
    print(f"[APP_INIT] âš  NLTK initialization warning: {e}")
    print("[APP_INIT] Continuing with preprocessing fallback...")

# Import database utilities
print("[APP_INIT] Step 2: Initializing database utilities...")
from database.db_config import (
    get_db_connection,
    init_database,
    execute_query,
    execute_insert,
    insert_review_if_not_exists
)

# Ensure DB is ready as soon as app starts
print("[APP_INIT] Step 2.1: Verifying database connection and tables...")
db_ready = init_database()
if not db_ready:
    print("[APP_INIT] ERROR: Database initialization failed")
    raise RuntimeError("Database initialization failed. Check MySQL connection/config.")
else:
    test_conn = get_db_connection()
    if test_conn:
        test_conn.close()

# Import ML models
print("[APP_INIT] Step 3: Initializing ML models...")
from model.detector import FakeReviewDetector, SentimentAnalyzer
from model.preprocessor import ReviewPreprocessor, SimilarityAnalyzer, AnomalyDetector
from model.scraper import ReviewScraper

# Initialize Flask app
print("[APP_INIT] Step 4: Initializing Flask application...")
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize components
print("[APP_INIT] Step 5: Initializing preprocessing pipeline...")
preprocessor = ReviewPreprocessor()
print("[APP_INIT] Step 6: Initializing ML detector...")
detector = FakeReviewDetector()
print("[APP_INIT] Step 7: Initializing sentiment analyzer...")
sentiment_analyzer = SentimentAnalyzer()
print("[APP_INIT] Step 8: Initializing review scraper...")
scraper = ReviewScraper()
print("[APP_INIT] Step 9: Initializing similarity analyzer...")
similarity_analyzer = SimilarityAnalyzer()
print("[APP_INIT] Step 10: Initializing anomaly detector...")
anomaly_detector = AnomalyDetector()

# Load pre-trained models if they exist
print("[APP_INIT] Step 11: Loading pre-trained models...")
detector.load_models()
print("[APP_INIT] âœ“ All components initialized successfully!")
print("="*60 + "\n")

def login_required(f):
    """
    Decorator to check if user is logged in
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTHENTICATION ROUTES ====================
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/')
def index():
    """Home page - show landing page first"""
    return render_template('home.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page and authentication
    """
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        print(f"[LOGIN] Login attempt for: {email}")
        
        # Validate input
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        # Validate email format
        if not is_valid_email(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        try:
            # Query user from database
            result = execute_query(
                "SELECT id, password FROM users WHERE email = %s",
                (email,)
            )
            
            if result and check_password_hash(result[0]['password'], password):
                session['user_id'] = result[0]['id']
                session['email'] = email
                print(f"[LOGIN] Login successful for user: {email}")
                return jsonify({'success': True, 'message': 'Login successful'}), 200
            else:
                print(f"[LOGIN] Invalid credentials for: {email}")
                return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        except Exception as e:
            print(f"[LOGIN] Exception: {type(e).__name__}: {str(e)}")
            return jsonify({'success': False, 'message': f'Login error: {str(e)}'}), 500
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Signup page and user registration
    """
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Debug: Print received data
            print(f"[SIGNUP] Received data: {data}")
            
            if not data:
                print("[SIGNUP] No JSON data received")
                return jsonify({'success': False, 'message': 'No data received'}), 400
            
            email = data.get('email', '').strip() if data.get('email') else ''
            password = data.get('password', '').strip() if data.get('password') else ''
            confirm_password = data.get('confirm_password', '').strip() if data.get('confirm_password') else ''
            
            print(f"[SIGNUP] Email: {email}, Password length: {len(password)}")
            
            # Validate input
            if not email or not password or not confirm_password:
                msg = 'All fields required'
                print(f"[SIGNUP] Validation failed: {msg}")
                return jsonify({'success': False, 'message': msg}), 400
            
            # Validate email format
            if not is_valid_email(email):
                msg = 'Invalid email format'
                print(f"[SIGNUP] {msg}")
                return jsonify({'success': False, 'message': msg}), 400
            
            # Validate password strength
            if len(password) < 6:
                msg = 'Password must be at least 6 characters'
                print(f"[SIGNUP] {msg}")
                return jsonify({'success': False, 'message': msg}), 400
            
            # Check password match
            if password != confirm_password:
                msg = 'Passwords do not match'
                print(f"[SIGNUP] {msg}")
                return jsonify({'success': False, 'message': msg}), 400
            
            # Check if user already exists
            print(f"[SIGNUP] Checking if user {email} already exists...")
            existing = execute_query(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )
            
            if existing:
                msg = 'Email already registered'
                print(f"[SIGNUP] {msg}")
                return jsonify({'success': False, 'message': msg}), 409
            
            # Create new user
            print(f"[SIGNUP] Creating new user: {email}")
            hashed_password = generate_password_hash(password)
            
            user_id = execute_insert(
                "INSERT INTO users (email, password) VALUES (%s, %s)",
                (email, hashed_password)
            )
            
            print(f"[SIGNUP] Insert result - user_id: {user_id}")
            
            # Check if insert was successful
            if user_id is None or user_id == 0:
                msg = 'Failed to create user account'
                print(f"[SIGNUP] ERROR: {msg}")
                return jsonify({'success': False, 'message': msg}), 500
            
            # Set session
            session['user_id'] = user_id
            session['email'] = email
            print(f"[SIGNUP] User registered successfully - ID: {user_id}")
            
            return jsonify({'success': True, 'message': 'Signup successful'}), 200
        
        except ValueError as ve:
            msg = f'Invalid input format: {str(ve)}'
            print(f"[SIGNUP] ValueError: {msg}")
            return jsonify({'success': False, 'message': msg}), 400
        
        except Exception as e:
            error_msg = str(e)
            print(f"[SIGNUP] Exception occurred: {type(e).__name__}: {error_msg}")
            
            # Show specific error message to user
            if 'duplicate' in error_msg.lower():
                return jsonify({'success': False, 'message': 'Email already exists'}), 409
            elif 'connection' in error_msg.lower():
                return jsonify({'success': False, 'message': 'Database connection error'}), 500
            else:
                return jsonify({'success': False, 'message': f'Registration error: {error_msg}'}), 500
    
    return render_template('signup.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Forgot password page - reset link would be sent via email
    """
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email or not is_valid_email(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        try:
            # Check if user exists
            user = execute_query(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )
            
            if user:
                # In production, send reset email here
                return jsonify({
                    'success': True,
                    'message': 'Password reset link sent to email (Feature in production)'
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'message': 'If email exists, reset link will be sent'
                }), 200
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    
    return render_template('forgot_password.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

def clean_fetched_reviews(raw_reviews):
    """
    Filter and normalize fetched reviews so only valid review text is analyzed/saved.
    """
    cleaned = []
    seen_texts = set()
    dropped = 0

    for review in raw_reviews or []:
        if not isinstance(review, dict):
            dropped += 1
            continue

        review_text = str(review.get('text') or review.get('review_text') or '').strip()
        if not review_text:
            dropped += 1
            continue

        review_text = ' '.join(review_text.split())
        normalized = review_text.lower()
        if normalized in seen_texts:
            dropped += 1
            continue

        # Reuse scraper validation to remove delivery/system-like content.
        if not ReviewScraper.is_valid_review(review_text):
            dropped += 1
            continue

        seen_texts.add(normalized)

        cleaned.append({
            'text': review_text,
            'rating': review.get('rating'),
            'reviewer': review.get('reviewer', 'Anonymous')
        })

    print(f"[ANALYZE] Reviews after cleaning: {len(cleaned)} (dropped: {dropped})")
    return cleaned

def _normalize_username(username):
    """Return a safe username label for reviewer insights."""
    if username is None:
        return 'Anonymous'
    normalized = str(username).strip()
    return normalized if normalized else 'Anonymous'

def _normalize_text_signature(review_text):
    """
    Build a lightweight signature used to detect repeated similar review text.
    This avoids expensive pairwise similarity checks for every review.
    """
    normalized = ' '.join(str(review_text or '').lower().split())
    if not normalized:
        return ''
    words = normalized.split()
    return ' '.join(words[:12])

def _is_verified_purchase(value):
    """Normalize verified_purchase values from multiple possible source formats."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'true', '1', 'yes', 'y', 'verified'}
    return False

def _to_float(value):
    """Best-effort numeric conversion for ratings."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def analyze_reviewer_insights(reviews):
    """
    Aggregate reviewer-level insights from analyzed reviews.

    Input reviews may use either:
    - username/review_text/predicted_sentiment/predicted_fake_or_genuine
    OR
    - reviewer/text/sentiment/prediction (existing app output)
    """
    reviews = reviews or []
    normalized_reviews = []

    has_verified_purchase_field = False
    verified_purchase_count = 0

    for review in reviews:
        if not isinstance(review, dict):
            continue

        username = _normalize_username(review.get('username') or review.get('reviewer'))
        review_text = str(review.get('review_text') or review.get('text') or '').strip()
        rating = _to_float(review.get('rating'))
        sentiment = str(review.get('predicted_sentiment') or review.get('sentiment') or '').strip().lower()
        prediction = str(review.get('predicted_fake_or_genuine') or review.get('prediction') or '').strip().lower()

        if 'verified_purchase' in review:
            has_verified_purchase_field = True
            if _is_verified_purchase(review.get('verified_purchase')):
                verified_purchase_count += 1

        is_positive = (rating is not None and rating >= 4) or sentiment == 'positive'
        is_negative = (rating is not None and rating <= 2) or sentiment == 'negative'
        is_fake = prediction == 'fake'
        is_genuine = prediction == 'genuine'

        normalized_reviews.append({
            'username': username,
            'is_positive': is_positive,
            'is_negative': is_negative,
            'is_fake': is_fake,
            'is_genuine': is_genuine,
            'text_signature': _normalize_text_signature(review_text)
        })

    total_reviews = len(normalized_reviews)
    reviewer_counts = Counter(item['username'] for item in normalized_reviews)

    positive_reviews_count = sum(1 for item in normalized_reviews if item['is_positive'])
    negative_reviews_count = sum(1 for item in normalized_reviews if item['is_negative'])
    fake_count = sum(1 for item in normalized_reviews if item['is_fake'])
    genuine_count = sum(1 for item in normalized_reviews if item['is_genuine'])

    positive_by_user = Counter()
    fake_by_user = Counter()
    text_signature_by_user = defaultdict(Counter)

    for item in normalized_reviews:
        username = item['username']
        if item['is_positive']:
            positive_by_user[username] += 1
        if item['is_fake']:
            fake_by_user[username] += 1
        if item['text_signature']:
            text_signature_by_user[username][item['text_signature']] += 1

    top_positive_reviewers = [
        {'username': username, 'count': count}
        for username, count in positive_by_user.items()
        if count > 1
    ]
    top_positive_reviewers.sort(key=lambda item: (-item['count'], item['username'].lower()))

    suspicious_reviewers = []
    for username, user_review_count in reviewer_counts.items():
        reasons = []
        fake_ratio = (fake_by_user[username] / user_review_count) if user_review_count else 0.0
        repeated_text_found = any(
            count > 1 for count in text_signature_by_user[username].values()
        )

        if user_review_count > 1:
            reasons.append(f"posted {user_review_count} reviews")
        if user_review_count > 2 and fake_ratio > 0.5:
            reasons.append(f"high fake ratio ({fake_ratio:.0%} fake)")
        if repeated_text_found:
            reasons.append("repeated similar review text")

        if reasons:
            suspicious_reviewers.append({
                'username': username,
                'reason': '; '.join(reasons),
                'review_count': user_review_count,
                'fake_ratio': round(fake_ratio, 2)
            })

    suspicious_reviewers.sort(
        key=lambda item: (-item['review_count'], -item['fake_ratio'], item['username'].lower())
    )

    insights = {
        'total_reviews': total_reviews,
        'total_reviewers': len(reviewer_counts),
        'positive_reviews_count': positive_reviews_count,
        'negative_reviews_count': negative_reviews_count,
        'genuine_count': genuine_count,
        'fake_count': fake_count,
        'top_positive_reviewers': top_positive_reviewers,
        'suspicious_reviewers': suspicious_reviewers
    }

    if has_verified_purchase_field:
        insights['verified_purchase_count'] = verified_purchase_count

    return insights

# ==================== MAIN APPLICATION ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_reviews():
    """
    Main API endpoint for analyzing reviews
    Expects: {url: str, use_sample: bool (optional), platform: str (optional)}
    """
    try:
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
        use_sample = data.get('use_sample', False)
        selected_platform = str(data.get('platform', 'auto')).strip().lower()
        
        user_id = session.get('user_id')
        
        print(f"\n[ANALYZE] Starting review analysis")
        print(f"[ANALYZE] URL provided: {bool(url)}, Use sample: {use_sample}, Platform: {selected_platform}")
        
        # Validate URL
        if not url and not use_sample:
            return jsonify({'success': False, 'message': 'Product URL required'}), 400

        allowed_platforms = {'auto', 'amazon', 'flipkart', 'shopsy', 'meesho', 'myntra'}
        if selected_platform not in allowed_platforms:
            return jsonify({
                'success': False,
                'message': 'Invalid platform. Choose from amazon, flipkart, shopsy, meesho, myntra'
            }), 400
        
        # Get reviews
        reviews = []
        platform = 'Unknown'
        fetch_warning = None
        
        if use_sample:
            print(f"[ANALYZE] Using sample data as requested")
            reviews, platform = scraper.create_sample_reviews(), 'Sample'
        else:
            if not ReviewScraper.validate_url(url):
                return jsonify({'success': False, 'message': 'Invalid URL format'}), 400
            
            print(f"[ANALYZE] Scraping reviews from URL using platform '{selected_platform}'...")
            reviews, platform = scraper.fetch_all_reviews(url, selected_platform)
            
            # If scraping returned no reviews, automatically fallback to sample data
            if not reviews:
                fetch_warning = 'Unable to fetch reviews'
                print(f"[ANALYZE] âš  Scraping failed or returned 0 reviews. Using sample data as fallback.")
                reviews, platform = scraper.create_sample_reviews(), 'Sample (Fallback)'
        
        print(f"[ANALYZE] Number of reviews fetched: {len(reviews)}")
        reviews = clean_fetched_reviews(reviews)
        print(f"[ANALYZE] Total reviews to process: {len(reviews)}")
        for idx, preview_review in enumerate(reviews[:2], 1):
            preview_text = preview_review.get('text', '')[:140]
            print(f"[ANALYZE] Preview review {idx}: {preview_text}")
        
        # Ensure we have reviews to process
        if not reviews:
            fetch_warning = 'Unable to fetch reviews'
            print(f"[ANALYZE] ERROR: No reviews available even after fallback")
            return jsonify({
                'success': False,
                'message': 'Unable to fetch or process reviews. Please try again.'
            }), 500
        
        # Save product to database
        product_id = execute_insert(
            "INSERT INTO products (user_id, url, product_name) VALUES (%s, %s, %s)",
            (user_id, url if not use_sample else 'Sample Product', 'Product')
        )
        
        print(f"[ANALYZE] Product saved with ID: {product_id}")
        
        # Analyze reviews
        print(f"[ANALYZE] Running ML analysis pipeline...")
        product_url = url if not use_sample else 'Sample Product'
        analysis_results = analyze_review_batch(reviews, product_id, product_url)
        
        print(f"[ANALYZE] Analysis complete. Results: {len(analysis_results)} reviews")
        print(f"[ANALYZE] Predictions: {sum(1 for r in analysis_results if r['prediction'] == 'Fake')} Fake, {sum(1 for r in analysis_results if r['prediction'] == 'Genuine')} Genuine")
        
        # Save analysis results to database
        save_analysis_results(product_id, analysis_results)
        
        return jsonify({
            'success': True,
            'reviews': analysis_results,
            'product_id': product_id,
            'platform': platform,
            'fetch_warning': fetch_warning,
            'total_reviews': len(analysis_results)
        }), 200
    
    except Exception as e:
        error_msg = str(e)
        print(f"[ANALYZE] ERROR: {error_msg}")
        print(f"[ANALYZE] Exception type: {type(e).__name__}")
        return jsonify({'success': False, 'message': f'Analysis error: {error_msg}'}), 500

@app.route('/reviewer-insights', methods=['POST'])
@login_required
def reviewer_insights():
    """
    Reviewer insights endpoint.
    Supports two modes:
    1) Fast path: use provided reviews from request payload
    2) Pipeline path: fetch + predict using existing review analysis flow
    """
    try:
        data = request.get_json(silent=True) or {}
        provided_reviews = data.get('reviews')

        # Fast path for frontend add-on rendering after /api/analyze completes.
        if isinstance(provided_reviews, list):
            insights = analyze_reviewer_insights(provided_reviews)
            return jsonify({
                'success': True,
                'insights': insights,
                'source': 'provided_reviews'
            }), 200

        # Pipeline path: mirrors existing /api/analyze flow without modifying it.
        url = str(data.get('url', '')).strip()
        use_sample = data.get('use_sample', False)
        selected_platform = str(data.get('platform', 'auto')).strip().lower()
        user_id = session.get('user_id')

        if not url and not use_sample:
            return jsonify({'success': False, 'message': 'Product URL required'}), 400

        allowed_platforms = {'auto', 'amazon', 'flipkart', 'shopsy', 'meesho', 'myntra'}
        if selected_platform not in allowed_platforms:
            return jsonify({
                'success': False,
                'message': 'Invalid platform. Choose from amazon, flipkart, shopsy, meesho, myntra'
            }), 400

        reviews = []
        platform = 'Unknown'
        fetch_warning = None

        if use_sample:
            reviews, platform = scraper.create_sample_reviews(), 'Sample'
        else:
            if not ReviewScraper.validate_url(url):
                return jsonify({'success': False, 'message': 'Invalid URL format'}), 400

            reviews, platform = scraper.fetch_all_reviews(url, selected_platform)
            if not reviews:
                fetch_warning = 'Unable to fetch reviews'
                reviews, platform = scraper.create_sample_reviews(), 'Sample (Fallback)'

        reviews = clean_fetched_reviews(reviews)
        if not reviews:
            return jsonify({
                'success': False,
                'message': 'Unable to fetch or process reviews. Please try again.'
            }), 500

        product_url = url if not use_sample else 'Sample Product'
        product_id = execute_insert(
            "INSERT INTO products (user_id, url, product_name) VALUES (%s, %s, %s)",
            (user_id, product_url, 'Product')
        )

        analysis_results = analyze_review_batch(reviews, product_id, product_url)
        save_analysis_results(product_id, analysis_results)

        insights = analyze_reviewer_insights(analysis_results)
        return jsonify({
            'success': True,
            'insights': insights,
            'reviews': analysis_results,
            'product_id': product_id,
            'platform': platform,
            'fetch_warning': fetch_warning,
            'total_reviews': len(analysis_results),
            'source': 'pipeline'
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"[INSIGHTS] ERROR: {error_msg}")
        return jsonify({'success': False, 'message': f'Reviewer insights error: {error_msg}'}), 500

def analyze_review_batch(reviews, product_id, product_url):
    """
    Analyze a batch of reviews

    Args:
        reviews (list): List of review dictionaries
        product_id (int): Product ID for database
        product_url (str): Product URL used for review storage and duplicate checks

    Returns:
        list: Analyzed reviews with predictions
    """
    print(f"[BATCH_ANALYSIS] Starting analysis of {len(reviews)} reviews")

    analyzed = []
    review_texts = []
    preprocessing_texts = []
    ratings = []

    # Preprocess all reviews
    print(f"[BATCH_ANALYSIS] Step 1: Preprocessing reviews...")
    for i, review in enumerate(reviews):
        text = review.get('text', '')
        review_texts.append(text)
        preprocessed = preprocessor.preprocess(text)
        preprocessing_texts.append(preprocessed)

        rating = review.get('rating')
        if rating:
            ratings.append(rating)

    print(f"[BATCH_ANALYSIS] Preprocessing complete. Texts ready for vectorization.")

    # Extract TF-IDF features
    print(f"[BATCH_ANALYSIS] Step 2: Extracting TF-IDF features...")
    try:
        features = preprocessor.get_tfidf_features(preprocessing_texts)
        features_array = features.toarray()
        print(f"[BATCH_ANALYSIS] Features extracted: shape {features_array.shape}")
    except Exception:
        # If fit hasn't been called, fit and transform
        features = preprocessor.vectorizer.fit_transform(preprocessing_texts)
        features_array = features.toarray()
        print(f"[BATCH_ANALYSIS] Features fitted and extracted: shape {features_array.shape}")

    # Make predictions using ensemble
    print(f"[BATCH_ANALYSIS] Step 3: Running ML ensemble predictions...")
    predictions, probabilities, confidence = detector.predict_ensemble(features_array)
    print(f"[BATCH_ANALYSIS] Predictions complete")

    # Detect duplicates
    print(f"[BATCH_ANALYSIS] Step 4: Checking for duplicate reviews...")
    duplicate_indices = set()
    text_similarities = []
    for i in range(len(review_texts)):
        max_similarity = 0
        for j in range(i + 1, len(review_texts)):
            sim = similarity_analyzer.calculate_similarity(review_texts[i], review_texts[j])
            max_similarity = max(max_similarity, sim)

            if sim > 0.85:
                duplicate_indices.add(i)
                duplicate_indices.add(j)

        text_similarities.append(max_similarity)

    # Detect anomalies (if we have ratings)
    print(f"[BATCH_ANALYSIS] Step 5: Detecting rating anomalies...")
    anomaly_indices = set()
    if ratings:
        anomaly_indices = set(anomaly_detector.detect_rating_anomaly(ratings))
        print(f"[BATCH_ANALYSIS] Found {len(anomaly_indices)} anomalies")
    else:
        print(f"[BATCH_ANALYSIS] No ratings available for anomaly detection")

    # Analyze sentiment
    print(f"[BATCH_ANALYSIS] Step 6: Analyzing sentiment...")
    sentiments = sentiment_analyzer.batch_analyze_sentiment(review_texts)
    print(f"[BATCH_ANALYSIS] Sentiment analysis complete")

    # Prepare results
    print(f"[BATCH_ANALYSIS] Step 7: Preparing results...")
    print(f"[BATCH_ANALYSIS] Found {len(duplicate_indices)} reviews marked as duplicates")

    fake_count = 0
    inserted_count = 0
    duplicate_skipped_count = 0
    insert_errors = []

    for i, review in enumerate(reviews):
        prediction = 'Fake' if predictions[i] == 1 else 'Genuine'
        if prediction not in ('Fake', 'Genuine'):
            print(f"[BATCH_ANALYSIS] Invalid prediction value at review {i}: {prediction}. Forcing Genuine.")
            prediction = 'Genuine'
        if prediction == 'Fake':
            fake_count += 1

        fake_prob = probabilities[i][1] if len(probabilities[i]) > 1 else 0
        confidence_percent = round(confidence[i] * 100, 2)
        try:
            confidence_percent = float(confidence_percent)
        except (TypeError, ValueError):
            print(f"[BATCH_ANALYSIS] Invalid confidence at review {i}: {confidence_percent}. Using 0.0")
            confidence_percent = 0.0
        sentiment = sentiments[i]['label']

        is_duplicate = i in duplicate_indices
        is_anomaly = i in anomaly_indices

        analyzed_review = {
            'id': i,
            'text': review.get('text', ''),
            'rating': review.get('rating'),
            'reviewer': review.get('reviewer', 'Anonymous'),
            'prediction': prediction,
            'confidence': confidence_percent,
            'sentiment': sentiment,
            'is_duplicate': is_duplicate,
            'is_anomaly': is_anomaly,
            'probability': round(fake_prob, 4)
        }

        analyzed.append(analyzed_review)

        # Save to database while preventing duplicate inserts
        try:
            review_text = str(review.get('text', '')).strip()
            if not review_text:
                print(f"[BATCH_ANALYSIS] Skipping review {i}: empty review text")
                continue

            if not product_url or not str(product_url).strip():
                error_msg = f"[BATCH_ANALYSIS] Missing product_url for review {i}"
                print(error_msg)
                insert_errors.append(error_msg)
                continue

            inserted = insert_review_if_not_exists(
                product_id=product_id,
                product_url=str(product_url).strip(),
                review_text=review_text,
                prediction=prediction,
                confidence=confidence_percent,
                reviewer_name=review.get('reviewer'),
                rating=review.get('rating'),
                sentiment=sentiment,
                is_duplicate=is_duplicate,
                is_anomaly=is_anomaly
            )

            if inserted:
                inserted_count += 1
            else:
                duplicate_skipped_count += 1

        except Exception as e:
            error_msg = f"[BATCH_ANALYSIS] ERROR: Failed to save review {i}: {str(e)}"
            print(error_msg)
            insert_errors.append(error_msg)

    print(f"[BATCH_ANALYSIS] ANALYSIS COMPLETE: {fake_count} Fake, {len(reviews) - fake_count} Genuine out of {len(reviews)} reviews")
    print(f"[BATCH_ANALYSIS] Reviews inserted: {inserted_count}")
    print(f"[BATCH_ANALYSIS] Duplicate reviews skipped: {duplicate_skipped_count}")

    if insert_errors:
        raise Exception(f"Review insert failures detected ({len(insert_errors)}). First error: {insert_errors[0]}")

    return analyzed

def save_analysis_results(product_id, analysis_results):
    """Save analysis summary to database"""
    try:
        fake_count = sum(1 for r in analysis_results if r['prediction'] == 'Fake')
        genuine_count = len(analysis_results) - fake_count
        fake_percentage = (fake_count / len(analysis_results) * 100) if analysis_results else 0
        
        execute_insert(
            """INSERT INTO analysis_results (product_id, total_reviews, fake_count, genuine_count, fake_percentage)
               VALUES (%s, %s, %s, %s, %s)""",
            (product_id, len(analysis_results), fake_count, genuine_count, round(fake_percentage, 2))
        )
        print(f"[SAVE_RESULTS] âœ“ Saved analysis summary: {fake_count} Fake, {genuine_count} Genuine ({fake_percentage:.1f}% fake)")
    except Exception as e:
        print(f"[ANALYZE] Error saving analysis results: {str(e)}")

@app.route('/api/history')
@login_required
def get_analysis_history():
    """Get user's analysis history"""
    try:
        user_id = session.get('user_id')
        
        results = execute_query(
            """SELECT p.id, p.url, p.product_name, a.total_reviews, a.fake_count, 
                      a.genuine_count, a.fake_percentage, a.analysis_date
               FROM products p
               LEFT JOIN analysis_results a ON p.id = a.product_id
               WHERE p.user_id = %s
               ORDER BY p.created_at DESC
               LIMIT 10""",
            (user_id,)
        )
        
        return jsonify({'success': True, 'history': results}), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/product/<int:product_id>')
@login_required
def get_product_details(product_id):
    """Get detailed analysis for a product"""
    try:
        user_id = session.get('user_id')
        
        # Verify product belongs to user
        product = execute_query(
            "SELECT * FROM products WHERE id = %s AND user_id = %s",
            (product_id, user_id)
        )
        
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        
        # Get reviews
        reviews = execute_query(
            "SELECT * FROM reviews WHERE product_id = %s",
            (product_id,)
        )
        
        # Get summary
        summary = execute_query(
            "SELECT * FROM analysis_results WHERE product_id = %s",
            (product_id,)
        )
        
        return jsonify({
            'success': True,
            'product': product[0],
            'reviews': reviews,
            'summary': summary[0] if summary else None
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== UTILITY FUNCTIONS ====================

def is_valid_email(email):
    """
    Validate email format
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'success': False, 'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ==================== APPLICATION INITIALIZATION ====================

if __name__ == "__main__":
    # Initialize database
    init_database()
    
    # Run Flask app
    app.run()

