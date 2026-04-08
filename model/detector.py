"""
Fake review detection models using XGBoost and SVM
"""
import pickle
import os
import numpy as np
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import warnings

warnings.filterwarnings('ignore')

class FakeReviewDetector:
    """
    Main class for fake review detection using multiple models
    """
    
    def __init__(self, model_dir='model/trained_models'):
        """
        Initialize the detector
        
        Args:
            model_dir (str): Directory to store trained models
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        self.xgb_model = None
        self.svm_model = None
        self.is_trained = False
    
    def train_xgboost(self, X_train, y_train, X_val=None, y_val=None):
        """
        Train XGBoost classifier
        
        Args:
            X_train (array): Training features
            y_train (array): Training labels (0=Genuine, 1=Fake)
            X_val (array): Validation features
            y_val (array): Validation labels
            
        Returns:
            dict: Training metrics
        """
        # Create XGBoost model
        self.xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        
        # Train model
        try:
            # Try new XGBoost API (version 2.0+)
            if X_val is not None:
                self.xgb_model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    callbacks=[xgb.callback.EarlyStopping(rounds=10, save_best=True)],
                    verbose=False
                )
            else:
                self.xgb_model.fit(X_train, y_train, verbose=False)
        except (TypeError, AttributeError):
            # Fallback for older versions
            if X_val is not None:
                self.xgb_model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=False
                )
            else:
                self.xgb_model.fit(X_train, y_train)
        
        # Calculate metrics
        y_pred = self.xgb_model.predict(X_train)
        metrics = {
            'accuracy': accuracy_score(y_train, y_pred),
            'precision': precision_score(y_train, y_pred, zero_division=0),
            'recall': recall_score(y_train, y_pred, zero_division=0),
            'f1': f1_score(y_train, y_pred, zero_division=0)
        }
        
        return metrics
    
    def train_svm(self, X_train, y_train):
        """
        Train SVM classifier
        
        Args:
            X_train (array): Training features
            y_train (array): Training labels (0=Genuine, 1=Fake)
            
        Returns:
            dict: Training metrics
        """
        # Create SVM model with RBF kernel
        self.svm_model = SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            probability=True,
            random_state=42
        )
        
        # Train model
        self.svm_model.fit(X_train, y_train)
        
        # Calculate metrics
        y_pred = self.svm_model.predict(X_train)
        metrics = {
            'accuracy': accuracy_score(y_train, y_pred),
            'precision': precision_score(y_train, y_pred, zero_division=0),
            'recall': recall_score(y_train, y_pred, zero_division=0),
            'f1': f1_score(y_train, y_pred, zero_division=0)
        }
        
        return metrics
    
    def predict_xgboost(self, X):
        """
        Make predictions using XGBoost
        
        Args:
            X (array): Feature matrix
            
        Returns:
            tuple: (predictions, probabilities)
        """
        if self.xgb_model is None:
            raise ValueError("XGBoost model not trained")
        
        predictions = self.xgb_model.predict(X)
        probabilities = self.xgb_model.predict_proba(X)
        
        return predictions, probabilities
    
    def predict_svm(self, X):
        """
        Make predictions using SVM
        
        Args:
            X (array): Feature matrix
            
        Returns:
            tuple: (predictions, probabilities)
        """
        if self.svm_model is None:
            raise ValueError("SVM model not trained")
        
        predictions = self.svm_model.predict(X)
        probabilities = self.svm_model.predict_proba(X)
        
        return predictions, probabilities
    
    def predict_ensemble(self, X):
        """
        Make predictions using ensemble of both models
        
        Args:
            X (array): Feature matrix
            
        Returns:
            tuple: (predictions, average_probabilities, confidence)
        """
        if self.xgb_model is None or self.svm_model is None:
            raise ValueError("Both models must be trained")
        
        xgb_pred, xgb_proba = self.predict_xgboost(X)
        svm_pred, svm_proba = self.predict_svm(X)
        
        # Average probabilities from both models
        avg_proba = (xgb_proba + svm_proba) / 2
        
        # Ensemble prediction (majority vote)
        predictions = (xgb_pred + svm_pred) / 2
        predictions = (predictions >= 0.5).astype(int)
        
        # Confidence is max probability
        confidence = np.max(avg_proba, axis=1)
        
        return predictions, avg_proba, confidence
    
    def save_models(self):
        """Save trained models and vectorizer to disk"""
        if self.xgb_model:
            xgb_path = os.path.join(self.model_dir, 'xgboost_model.pkl')
            with open(xgb_path, 'wb') as f:
                pickle.dump(self.xgb_model, f)
                print(f"[DETECTOR] Saved XGBoost model")
        
        if self.svm_model:
            svm_path = os.path.join(self.model_dir, 'svm_model.pkl')
            with open(svm_path, 'wb') as f:
                pickle.dump(self.svm_model, f)
                print(f"[DETECTOR] Saved SVM model")
    
    def load_models(self):
        """Load trained models and vectorizer from disk"""
        xgb_path = os.path.join(self.model_dir, 'xgboost_model.pkl')
        svm_path = os.path.join(self.model_dir, 'svm_model.pkl')
        
        xgb_loaded = False
        svm_loaded = False
        
        if os.path.exists(xgb_path):
            try:
                with open(xgb_path, 'rb') as f:
                    self.xgb_model = pickle.load(f)
                xgb_loaded = True
                print(f"[DETECTOR] Loaded XGBoost model")
            except Exception as e:
                print(f"[DETECTOR] Error loading XGBoost model: {e}")
        
        if os.path.exists(svm_path):
            try:
                with open(svm_path, 'rb') as f:
                    self.svm_model = pickle.load(f)
                svm_loaded = True
                print(f"[DETECTOR] Loaded SVM model")
            except Exception as e:
                print(f"[DETECTOR] Error loading SVM model: {e}")
        
        self.is_trained = xgb_loaded and svm_loaded
        
        if not self.is_trained:
            print(f"[DETECTOR] Warning: Models not fully loaded - is_trained={self.is_trained}")
        
        return self.is_trained


class SentimentAnalyzer:
    """
    Analyze sentiment of reviews
    """
    
    def __init__(self):
        """Initialize sentiment analyzer"""
        try:
            from textblob import TextBlob
            self.textblob = TextBlob
        except ImportError:
            print("TextBlob not installed. Install with: pip install textblob")
            self.textblob = None
    
    def analyze_sentiment(self, text):
        """
        Analyze sentiment of review text
        
        Args:
            text (str): Review text
            
        Returns:
            dict: Sentiment analysis result {label, polarity, subjectivity}
        """
        if not self.textblob:
            return {
                'label': 'unknown',
                'polarity': 0,
                'subjectivity': 0
            }
        
        blob = self.textblob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Classify sentiment
        if polarity > 0.1:
            label = 'Positive'
        elif polarity < -0.1:
            label = 'Negative'
        else:
            label = 'Neutral'
        
        return {
            'label': label,
            'polarity': round(polarity, 3),
            'subjectivity': round(subjectivity, 3)
        }
    
    def batch_analyze_sentiment(self, texts):
        """
        Analyze sentiment for multiple texts
        
        Args:
            texts (list): List of review texts
            
        Returns:
            list: List of sentiment results
        """
        results = []
        for text in texts:
            results.append(self.analyze_sentiment(text))
        
        return results
