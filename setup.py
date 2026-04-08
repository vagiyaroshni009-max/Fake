"""
Setup Script for Fake Review Detector
Run this script to automatically set up the application
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60)

def print_step(text):
    """Print step message"""
    print(f"\n→ {text}")

def print_success(text):
    """Print success message"""
    print(f"  ✓ {text}")

def print_error(text):
    """Print error message"""
    print(f"  ✗ {text}")

def check_python_version():
    """Check if Python version is 3.8+"""
    print_step("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python 3.8+ required. Found {version.major}.{version.minor}")
        return False

def create_virtual_environment():
    """Create virtual environment"""
    print_step("Creating virtual environment...")
    if os.path.exists('.venv'):
        print_success("Virtual environment already exists")
        return True
    
    try:
        subprocess.run([sys.executable, '-m', 'venv', '.venv'], check=True)
        print_success("Virtual environment created")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        return False

def install_dependencies():
    """Install required packages"""
    print_step("Installing dependencies...")
    
    # Determine pip executable
    if os.name == 'nt':  # Windows
        pip_exec = '.\.venv\Scripts\pip'
    else:  # Mac/Linux
        pip_exec = './.venv/bin/pip'
    
    try:
        subprocess.run([pip_exec, 'install', '-r', 'requirements.txt'], check=True)
        print_success("All dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False

def create_env_file():
    """Create .env file from template"""
    print_step("Configuring environment...")
    
    if os.path.exists('.env'):
        print_success(".env file already exists")
        return True
    
    if os.path.exists('.env.template'):
        try:
            with open('.env.template', 'r') as template:
                with open('.env', 'w') as env_file:
                    env_file.write(template.read())
            print_success(".env file created from template")
            return True
        except Exception as e:
            print_error(f"Failed to create .env: {e}")
            return False
    else:
        print_error(".env.template not found")
        return False

def create_directories():
    """Create necessary directories"""
    print_step("Creating required directories...")
    
    directories = [
        'model/trained_models',
        'static/images',
        'logs'
    ]
    
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print_success(f"Directory created: {dir_path}")
    
    return True

def download_nltk_data():
    """Download required NLTK data"""
    print_step("Downloading NLP data...")
    
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        print_success("Downloaded 'punkt'")
        
        nltk.download('stopwords', quiet=True)
        print_success("Downloaded 'stopwords'")
        
        nltk.download('wordnet', quiet=True)
        print_success("Downloaded 'wordnet'")
        
        return True
    except Exception as e:
        print_error(f"Failed to download NLTK data: {e}")
        return False

def check_mysql():
    """Check MySQL connection"""
    print_step("Checking MySQL connection...")
    
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host='localhost',
            user='root'
        )
        conn.close()
        print_success("MySQL connection successful")
        return True
    except Exception as e:
        print_error(f"MySQL connection failed: {e}")
        print("  Please ensure MySQL is running and credentials are correct")
        return False

def initialize_database():
    """Initialize database"""
    print_step("Initializing database...")
    
    try:
        from database.db_config import init_database
        if init_database():
            print_success("Database initialized")
            return True
        else:
            print_error("Failed to initialize database")
            return False
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return False

def create_sample_models():
    """Train sample models"""
    print_step("Creating sample ML models...")
    
    try:
        from train_models import create_sample_training_data, train_models
        import numpy as np
        
        texts, labels = create_sample_training_data()
        train_models(texts, np.array(labels))
        print_success("Sample models created")
        return True
    except Exception as e:
        print_error(f"Failed to create models: {e}")
        return False

def main():
    """Run setup"""
    print_header("FAKE REVIEW DETECTOR - SETUP")
    
    steps = [
        ("Python Version", check_python_version),
        ("Virtual Environment", create_virtual_environment),
        ("Dependencies", install_dependencies),
        ("Environment Config", create_env_file),
        ("Directories", create_directories),
        ("NLP Data", download_nltk_data),
        ("MySQL Check", check_mysql),
        ("Database", initialize_database),
        ("ML Models", create_sample_models),
    ]
    
    completed = 0
    failed = []
    
    for step_name, step_func in steps:
        try:
            if step_func():
                completed += 1
            else:
                failed.append(step_name)
        except Exception as e:
            print_error(f"{step_name} failed: {e}")
            failed.append(step_name)
    
    print_header("SETUP SUMMARY")
    print(f"\nCompleted: {completed}/{len(steps)}")
    
    if failed:
        print(f"\nFailed steps: {', '.join(failed)}")
        print("\nPlease fix these issues and run setup again.")
    else:
        print("\n✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Update .env file with your MySQL credentials")
        print("2. Run: python app.py")
        print("3. Open: http://localhost:5000")
    
    return 0 if not failed else 1

if __name__ == '__main__':
    sys.exit(main())
