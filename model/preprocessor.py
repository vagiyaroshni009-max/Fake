"""
Text preprocessing and feature extraction for review analysis
"""
import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings('ignore')

# Import NLTK initialization module to ensure resources are available
try:
    from model.nltk_init import ensure_nltk_resources, verify_nltk_ready
    print("[PREPROCESSOR] Ensuring NLTK resources...")
    ensure_nltk_resources()
    verify_nltk_ready()
except ImportError:
    print("[PREPROCESSOR] WARNING: NLTK init module not found, using fallback...")
    # Fallback initialization if nltk_init module is not available
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet', quiet=True)

class ReviewPreprocessor:
    """
    Handle text preprocessing and feature extraction for fake review detection
    """
    
    def __init__(self, vectorizer_path='model/trained_models/tfidf_vectorizer.pkl'):
        """Initialize preprocessor with necessary NLTK resources"""
        try:
            import pickle
            import os
            
            print("[PREPROCESSOR] Initializing ReviewPreprocessor...")
            self.stop_words = set(stopwords.words('english'))
            print(f"[PREPROCESSOR] ✓ Loaded {len(self.stop_words)} stopwords")
            
            self.lemmatizer = WordNetLemmatizer()
            print("[PREPROCESSOR] ✓ WordNetLemmatizer initialized")
            
            # Try to load pre-trained vectorizer
            self.vectorizer_path = vectorizer_path
            if os.path.exists(vectorizer_path):
                try:
                    with open(vectorizer_path, 'rb') as f:
                        self.vectorizer = pickle.load(f)
                    # Try to access n_features_in_ to verify vectorizer is properly initialized
                    if hasattr(self.vectorizer, 'n_features_in_'):
                        print(f"[PREPROCESSOR] ✓ Loaded pre-trained TF-IDF Vectorizer ({self.vectorizer.n_features_in_} features)")
                    else:
                        # Vectorizer loaded but doesn't have n_features_in_ - re-initialize to ensure compatibility
                        print(f"[PREPROCESSOR] ⚠ Loaded vectorizer is missing metadata, reinitializing...")
                        old_vocab = self.vectorizer.vocabulary_ if hasattr(self.vectorizer, 'vocabulary_') else None
                        self.vectorizer = TfidfVectorizer(max_features=1000, vocabulary=old_vocab)
                        print("[PREPROCESSOR] ✓ TF-IDF Vectorizer reinitialized")
                except Exception as e:
                    print(f"[PREPROCESSOR] ⚠ Could not load pre-trained vectorizer: {e}, creating new one")
                    self.vectorizer = TfidfVectorizer(max_features=1000)
                    print("[PREPROCESSOR] ✓ TF-IDF Vectorizer configured (new)")
            else:
                self.vectorizer = TfidfVectorizer(max_features=1000)
                print("[PREPROCESSOR] ✓ TF-IDF Vectorizer configured (new)")
            
            # Test tokenization to verify NLTK is working
            test_tokens = word_tokenize("Test")
            print(f"[PREPROCESSOR] ✓ Tokenization test passed")
            
        except Exception as e:
            print(f"[PREPROCESSOR] ✗ Initialization error: {e}")
            print("[PREPROCESSOR] WARNING: Some NLTK features may not work correctly")
            
            # Set defaults for graceful degradation
            self.stop_words = set()  # Empty set if loading fails
            self.lemmatizer = WordNetLemmatizer()
            self.vectorizer = TfidfVectorizer(max_features=1000)
    
    def clean_text(self, text):
        """
        Clean and normalize text
        
        Args:
            text (str): Raw review text
            
        Returns:
            str: Cleaned text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def tokenize_and_lemmatize(self, text):
        """
        Tokenize and lemmatize text
        
        Args:
            text (str): Cleaned text
            
        Returns:
            str: Processed text with lemmatized tokens
        """
        try:
            # Tokenize
            tokens = word_tokenize(text)
            
            # Remove stopwords and lemmatize
            tokens = [
                self.lemmatizer.lemmatize(word)
                for word in tokens
                if word not in self.stop_words and len(word) > 2
            ]
            
            return ' '.join(tokens)
        except Exception as e:
            print(f"[PREPROCESSOR] ⚠ Tokenization error: {e}")
            # Fallback: simple split if tokenization fails
            words = text.split()
            words = [w for w in words if w not in self.stop_words and len(w) > 2]
            return ' '.join(words)
    
    def preprocess(self, text):
        """
        Complete preprocessing pipeline
        
        Args:
            text (str): Raw review text
            
        Returns:
            str: Fully preprocessed text
        """
        try:
            text = self.clean_text(text)
            text = self.tokenize_and_lemmatize(text)
            return text
        except Exception as e:
            print(f"[PREPROCESSOR] ✗ Preprocessing error: {e}")
            # Return cleaned text as fallback
            try:
                return self.clean_text(text)
            except:
                # Ultimate fallback - return as-is but lowercased
                return text.lower() if isinstance(text, str) else str(text).lower()
    
    def extract_features(self, texts):
        """
        Extract TF-IDF features from texts
        
        Args:
            texts (list): List of preprocessed texts
            
        Returns:
            sparse matrix: TF-IDF feature matrix
        """
        return self.vectorizer.fit_transform(texts)
    
    def get_tfidf_features(self, texts):
        """
        Get TF-IDF features for given texts
        
        Args:
            texts (list): List of preprocessed texts
            
        Returns:
            sparse matrix: TF-IDF feature matrix
        """
        return self.vectorizer.transform(texts)


class SimilarityAnalyzer:
    """
    Analyze similarity between reviews for duplicate detection
    """
    
    def __init__(self):
        """Initialize similarity analyzer"""
        pass
    
    @staticmethod
    def calculate_similarity(text1, text2):
        """
        Calculate cosine similarity between two texts
        
        Args:
            text1 (str): First text
            text2 (str): Second text
            
        Returns:
            float: Similarity score (0-1)
        """
        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 2))
        tfidf = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
        return similarity[0][0]
    
    @staticmethod
    def find_duplicate_threshold(reviews, threshold=0.85):
        """
        Find duplicate reviews based on similarity threshold
        
        Args:
            reviews (list): List of review texts
            threshold (float): Similarity threshold (default: 0.85)
            
        Returns:
            dict: Dictionary with duplicate groups
        """
        duplicates = {}
        processed = set()
        
        for i, review1 in enumerate(reviews):
            if i in processed:
                continue
            
            group = [i]
            for j in range(i + 1, len(reviews)):
                if j in processed:
                    continue
                
                similarity = SimilarityAnalyzer.calculate_similarity(
                    review1, reviews[j]
                )
                
                if similarity >= threshold:
                    group.append(j)
                    processed.add(j)
            
            if len(group) > 1:
                duplicates[i] = group
                processed.add(i)
        
        return duplicates


class AnomalyDetector:
    """
    Detect anomalies in review ratings and patterns
    """
    
    @staticmethod
    def detect_rating_anomaly(ratings, z_threshold=2.5):
        """
        Detect anomalous ratings using Z-score method
        
        Args:
            ratings (list): List of ratings
            z_threshold (float): Z-score threshold
            
        Returns:
            list: Indices of anomalous ratings
        """
        ratings = np.array(ratings)
        mean = np.mean(ratings)
        std = np.std(ratings)
        
        if std == 0:
            return []
        
        z_scores = np.abs((ratings - mean) / std)
        anomalies = np.where(z_scores > z_threshold)[0].tolist()
        
        return anomalies
    
    @staticmethod
    def detect_pattern_anomaly(review_lengths, text_similarities, threshold=0.8):
        """
        Detect anomalous patterns in review length and similarity
        
        Args:
            review_lengths (list): List of review lengths
            text_similarities (list): List of similarity scores
            threshold (float): Threshold for anomaly detection
            
        Returns:
            list: Indices of anomalous reviews
        """
        anomalies = []
        
        # Check for suspiciously similar reviews
        for i, similarity in enumerate(text_similarities):
            if similarity > threshold:
                anomalies.append(i)
        
        return anomalies
