"""
NLTK Resource Verification Script
Tests and verifies that all NLTK resources are properly installed and accessible
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\n" + "="*60)
print("NLTK RESOURCE VERIFICATION TEST")
print("="*60)

# Test 1: Import NLTK
print("\n[TEST 1] Checking NLTK import...")
try:
    import nltk
    print(f"✓ NLTK version {nltk.__version__} imported successfully")
except ImportError as e:
    print(f"✗ Failed to import NLTK: {e}")
    sys.exit(1)

# Test 2: Check NLTK data directory
print("\n[TEST 2] Checking NLTK data directory...")
try:
    nltk_data_path = nltk.data.path
    print(f"✓ NLTK data paths: {nltk_data_path}")
except Exception as e:
    print(f"⚠ Error checking NLTK path: {e}")

# Test 3: Test punkt tokenizer
print("\n[TEST 3] Testing 'punkt' tokenizer...")
try:
    nltk.data.find('tokenizers/punkt')
    print("✓ 'punkt' resource found")
except LookupError:
    print("✗ 'punkt' resource NOT found")
    print("  Attempting to download...")
    try:
        nltk.download('punkt', quiet=False)
        print("✓ 'punkt' downloaded successfully")
    except Exception as e:
        print(f"✗ Failed to download 'punkt': {e}")

# Test 4: Test stopwords
print("\n[TEST 4] Testing 'stopwords'...")
try:
    nltk.data.find('corpora/stopwords')
    print("✓ 'stopwords' resource found")
except LookupError:
    print("✗ 'stopwords' resource NOT found")
    print("  Attempting to download...")
    try:
        nltk.download('stopwords', quiet=False)
        print("✓ 'stopwords' downloaded successfully")
    except Exception as e:
        print(f"✗ Failed to download 'stopwords': {e}")

# Test 5: Test wordnet
print("\n[TEST 5] Testing 'wordnet'...")
try:
    nltk.data.find('corpora/wordnet')
    print("✓ 'wordnet' resource found")
except LookupError:
    print("✗ 'wordnet' resource NOT found")
    print("  Attempting to download...")
    try:
        nltk.download('wordnet', quiet=False)
        print("✓ 'wordnet' downloaded successfully")
    except Exception as e:
        print(f"✗ Failed to download 'wordnet': {e}")

# Test 6: Functional test - Tokenization
print("\n[TEST 6] Functional test - Tokenization...")
try:
    from nltk.tokenize import word_tokenize
    test_text = "This is a test sentence for tokenization."
    tokens = word_tokenize(test_text)
    print(f"✓ Tokenization successful: {tokens}")
except Exception as e:
    print(f"✗ Tokenization failed: {e}")

# Test 7: Functional test - Stopwords
print("\n[TEST 7] Functional test - Stopwords loading...")
try:
    from nltk.corpus import stopwords
    stop_words = stopwords.words('english')
    print(f"✓ Stopwords loaded: {len(stop_words)} words")
    print(f"  Sample: {stop_words[:10]}")
except Exception as e:
    print(f"✗ Stopwords loading failed: {e}")

# Test 8: Functional test - Lemmatization
print("\n[TEST 8] Functional test - Lemmatization...")
try:
    from nltk.stem import WordNetLemmatizer
    lemmatizer = WordNetLemmatizer()
    word = "running"
    lemma = lemmatizer.lemmatize(word, pos='v')
    print(f"✓ Lemmatization successful: '{word}' → '{lemma}'")
except Exception as e:
    print(f"✗ Lemmatization failed: {e}")

# Test 9: Test NLTK init module
print("\n[TEST 9] Testing custom NLTK initialization module...")
try:
    from model.nltk_init import ensure_nltk_resources, verify_nltk_ready
    print("✓ NLTK init module imported successfully")
    
    print("  Running ensure_nltk_resources()...")
    result = ensure_nltk_resources()
    
    print("  Running verify_nltk_ready()...")
    ready = verify_nltk_ready()
    
    if ready:
        print("✓ All NLTK initialization checks passed!")
    else:
        print("⚠ Some NLTK checks had warnings")
except ImportError as e:
    print(f"✗ Could not import NLTK init module: {e}")
except Exception as e:
    print(f"✗ NLTK init module test failed: {e}")

# Test 10: Test preprocessor
print("\n[TEST 10] Testing ReviewPreprocessor with text...")
try:
    from model.preprocessor import ReviewPreprocessor
    preprocessor = ReviewPreprocessor()
    
    test_review = "This product is absolutely amazing! I love it so much."
    processed = preprocessor.preprocess(test_review)
    
    print(f"✓ Preprocessing successful!")
    print(f"  Original: {test_review}")
    print(f"  Processed: {processed}")
except Exception as e:
    print(f"✗ Preprocessing test failed: {e}")

print("\n" + "="*60)
print("VERIFICATION COMPLETE")
print("="*60 + "\n")

print("If all tests passed with ✓, your NLTK setup is correct!")
print("If you see ✗ or ⚠, read the messages above for resolution steps.")
