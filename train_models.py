"""
Model Training Script
Train XGBoost and SVM models on sample/real fake review data
"""

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification
from model.detector import FakeReviewDetector
from model.preprocessor import ReviewPreprocessor
import sys

def create_sample_training_data():
    """
    Create sample training data for model training
    In production, this would be replaced with real labeled data
    
    Returns:
        tuple: (texts, labels)
    """
    # Genuine reviews
    genuine_reviews = [
        "Excellent product! Exceeded my expectations. Highly recommend.",
        "Great quality and fast shipping. Very satisfied with purchase.",
        "Best product I've bought. Worth every penny. Will buy again.",
        "Amazing quality! Perfect for the price. Highly satisfied.",
        "Love it! Works better than expected. Great customer service too.",
        "Fantastic product! Better than competing brands. Recommended.",
        "Arrived quickly and in perfect condition. Very happy!",
        "This is exactly what I needed. Great product, fair price.",
        "Outstanding quality and serviceability. Definitely buying again.",
        "Perfect purchase! Matches description perfectly. Highly recommend.",
    ]
    
    # Fake reviews (suspicious patterns)
    fake_reviews = [
        "Amazing! Best product ever! You must buy this now!!! Everyone loves it!!!",
        "5 stars! Incredible! Fantastic! Awesome! Perfect! Must have!",
        "Wow amazing this is the best thing ever purchased this immediately",
        "Outstanding product highly recommend to everyone must buy urgently",
        "Absolutely perfect cannot believe the quality unbelievable amazing incredible",
        "Best best best best best best best product ever created anywhere",
        "Fantastic fantastic fantastic fantastic fantastic fantastic fantastic product",
        "This product changed my life forever absolutely incredible fantastic",
        "5 stars amazing great wonderful fantastic incredible awesome product",
        "Seriously best product I have ever seen in my entire life amazing",
    ]
    
    # Combine and create labels
    texts = genuine_reviews + fake_reviews
    labels = [0] * len(genuine_reviews) + [1] * len(fake_reviews)
    
    return texts, labels

def prepare_features(texts, preprocessor=None):
    """
    Preprocess texts and extract features
    
    Args:
        texts (list): List of review texts
        preprocessor (ReviewPreprocessor): Preprocessor instance
        
    Returns:
        array: Feature matrix
    """
    if not preprocessor:
        preprocessor = ReviewPreprocessor()
    
    # Preprocess texts
    processed_texts = [preprocessor.preprocess(text) for text in texts]
    
    # Extract TF-IDF features
    features = preprocessor.extract_features(processed_texts)
    
    return features.toarray(), preprocessor

def train_models(texts, labels):
    """
    Train both XGBoost and SVM models
    
    Args:
        texts (list): Review texts
        labels (array): Binary labels (0=Genuine, 1=Fake)
        
    Returns:
        dict: Training results and metrics
    """
    print("=" * 60)
    print("FAKE REVIEW DETECTION MODEL TRAINING")
    print("=" * 60)
    
    # Step 1: Preprocess and extract features
    print("\n[1/4] Preprocessing texts and extracting features...")
    features, preprocessor = prepare_features(texts)
    print(f"     ✓ Extracted {features.shape[1]} features from {len(texts)} reviews")
    
    # Step 2: Split data
    print("\n[2/4] Splitting data into training and validation sets...")
    X_train, X_val, y_train, y_val = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )
    print(f"     ✓ Training set: {len(X_train)} samples")
    print(f"     ✓ Validation set: {len(X_val)} samples")
    
    # Step 3: Initialize detector and train models
    print("\n[3/4] Training machine learning models...")
    detector = FakeReviewDetector()
    
    # Train XGBoost
    print("     Training XGBoost classifier...")
    xgb_metrics = detector.train_xgboost(X_train, y_train, X_val, y_val)
    print(f"     ✓ XGBoost Accuracy: {xgb_metrics['accuracy']:.4f}")
    print(f"     ✓ XGBoost Precision: {xgb_metrics['precision']:.4f}")
    print(f"     ✓ XGBoost Recall: {xgb_metrics['recall']:.4f}")
    print(f"     ✓ XGBoost F1-Score: {xgb_metrics['f1']:.4f}")
    
    # Train SVM
    print("     Training SVM classifier...")
    svm_metrics = detector.train_svm(X_train, y_train)
    print(f"     ✓ SVM Accuracy: {svm_metrics['accuracy']:.4f}")
    print(f"     ✓ SVM Precision: {svm_metrics['precision']:.4f}")
    print(f"     ✓ SVM Recall: {svm_metrics['recall']:.4f}")
    print(f"     ✓ SVM F1-Score: {svm_metrics['f1']:.4f}")
    
    # Step 4: Save models
    print("\n[4/4] Saving trained models...")
    detector.save_models()
    print("     ✓ Models saved successfully")
    print(f"     ✓ Location: model/trained_models/")
    
    # Save vectorizer
    import pickle
    import os
    vectorizer_path = os.path.join(detector.model_dir, 'tfidf_vectorizer.pkl')
    with open(vectorizer_path, 'wb') as f:
        pickle.dump(preprocessor.vectorizer, f)
    print(f"     ✓ TF-IDF Vectorizer saved to {vectorizer_path}")
    
    # Test ensemble prediction
    print("\n" + "=" * 60)
    print("TESTING ENSEMBLE PREDICTIONS")
    print("=" * 60)
    
    sample_predictions, proba, confidence = detector.predict_ensemble(X_val[:5])
    
    for i in range(min(5, len(X_val))):
        prediction = "Fake" if sample_predictions[i] == 1 else "Genuine"
        confidence_pct = confidence[i] * 100
        print(f"\nSample {i+1}:")
        print(f"  Prediction: {prediction}")
        print(f"  Confidence: {confidence_pct:.2f}%")
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    return {
        'xgb_metrics': xgb_metrics,
        'svm_metrics': svm_metrics,
        'detector': detector,
        'preprocessor': preprocessor
    }

def main():
    """Main training function"""
    try:
        # Create sample data
        print("\nCreating sample training data...")
        texts, labels = create_sample_training_data()
        print(f"✓ Created {len(texts)} sample reviews")
        print(f"  - Genuine: {labels.count(0)}")
        print(f"  - Fake: {labels.count(1)}")
        
        # Train models
        results = train_models(texts, np.array(labels))
        
        print("\n✓ All models trained and saved!")
        print("✓ Ready to use in Flask application")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
