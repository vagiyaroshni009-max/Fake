"""
NLTK Resource Initialization and Management
Handles downloading and verification of all required NLTK resources
"""
import nltk
import os
from pathlib import Path

# NLTK resources required for preprocessing
# Note: NLTK 3.8+ may use 'punkt_tab' instead of 'punkt'
REQUIRED_RESOURCES = {
    'tokenizers': ['punkt', 'punkt_tab'],  # Try both old and new format
    'corpora': ['stopwords', 'wordnet', 'averaged_perceptron_tagger'],  # Added POS tagger for better lemmatization
}

def ensure_nltk_resources():
    """
    Ensure all required NLTK resources are downloaded and available.
    This function will:
    1. Check if resources exist
    2. Download missing resources
    3. Provide detailed error reporting
    """
    print("[NLTK_INIT] Starting NLTK resource initialization...")
    
    missing_resources = []
    
    # Check and download tokenizers
    for resource in REQUIRED_RESOURCES.get('tokenizers', []):
        try:
            nltk.data.find(f'tokenizers/{resource}')
            print(f"[NLTK_INIT] ✓ Resource 'tokenizers/{resource}' found")
        except LookupError:
            print(f"[NLTK_INIT] ⚠ Resource 'tokenizers/{resource}' not found, downloading...")
            missing_resources.append((resource, 'tokenizers'))
            try:
                nltk.download(resource, quiet=True)
                # Verify download
                try:
                    nltk.data.find(f'tokenizers/{resource}')
                    print(f"[NLTK_INIT] ✓ Downloaded and verified '{resource}'")
                except:
                    print(f"[NLTK_INIT] ⚠ Download completed but verification failed for '{resource}'")
            except Exception as e:
                print(f"[NLTK_INIT] ✗ Failed to download '{resource}': {e}")
    
    # Check and download corpora
    for resource in REQUIRED_RESOURCES.get('corpora', []):
        try:
            nltk.data.find(f'corpora/{resource}')
            print(f"[NLTK_INIT] ✓ Resource 'corpora/{resource}' found")
        except LookupError:
            print(f"[NLTK_INIT] ⚠ Resource 'corpora/{resource}' not found, downloading...")
            missing_resources.append((resource, 'corpora'))
            try:
                nltk.download(resource, quiet=True)
                # Verify download
                try:
                    nltk.data.find(f'corpora/{resource}')
                    print(f"[NLTK_INIT] ✓ Downloaded and verified '{resource}'")
                except:
                    # Some resources like averaged_perceptron_tagger might have different names
                    print(f"[NLTK_INIT] ⚠ Download completed but verification failed for '{resource}' (may be non-critical)")
            except Exception as e:
                print(f"[NLTK_INIT] ✗ Failed to download '{resource}': {e}")
    
    print("[NLTK_INIT] ✓ NLTK resource initialization completed!")
    return True

def verify_nltk_ready():
    """
    Quick verification that NLTK is ready to use.
    Returns True if all resources are available, False otherwise.
    This function now handles both punkt and punkt_tab.
    """
    try:
        # Test tokenization - Try punkt_tab first (newer NLTK), then punkt (older)
        from nltk.tokenize import word_tokenize
        test_text = "This is a test sentence."
        
        try:
            tokens = word_tokenize(test_text)
            print("[NLTK_INIT] ✓ Tokenization test passed")
        except LookupError as e:
            if 'punkt_tab' in str(e):
                print("[NLTK_INIT] ⚠ punkt_tab not found, attempting to download...")
                nltk.download('punkt_tab', quiet=True)
                tokens = word_tokenize(test_text)
                print("[NLTK_INIT] ✓ Tokenization works with punkt_tab")
            elif 'punkt' in str(e):
                print("[NLTK_INIT] ⚠ punkt not found, attempting to download...")
                nltk.download('punkt', quiet=True)
                tokens = word_tokenize(test_text)
                print("[NLTK_INIT] ✓ Tokenization works with punkt")
            else:
                raise
        
        # Test stopwords
        from nltk.corpus import stopwords
        stop_words = stopwords.words('english')
        print(f"[NLTK_INIT] ✓ Stopwords loaded ({len(stop_words)} words)")
        
        # Test lemmatization
        from nltk.stem import WordNetLemmatizer
        lemmatizer = WordNetLemmatizer()
        lemma = lemmatizer.lemmatize("running", pos='v')
        print("[NLTK_INIT] ✓ Lemmatization test passed")
        
        print("[NLTK_INIT] ✓ NLTK verification successful - all components working")
        return True
        
    except Exception as e:
        print(f"[NLTK_INIT] ✗ NLTK verification failed: {e}")
        print("[NLTK_INIT] Attempting automatic recovery...")
        
        # Try comprehensive download
        try:
            print("[NLTK_INIT] Downloading all required resources...")
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            print("[NLTK_INIT] ✓ Recovery download successful")
            return True
        except Exception as recovery_error:
            print(f"[NLTK_INIT] ✗ Recovery failed: {recovery_error}")
            print("[NLTK_INIT] WARNING: Application may be unstable during preprocessing")
            return False

# Initialize NLTK resources when this module is imported
try:
    ensure_nltk_resources()
    verify_nltk_ready()
except Exception as e:
    print(f"[NLTK_INIT] ✗ Unexpected error during initialization: {e}")
    print("[NLTK_INIT] WARNING: Application may be unstable")
