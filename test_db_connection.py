"""
Database Connection Test Script
Run this to diagnose connection issues
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_config import get_db_connection, init_database, DB_CONFIG

print("\n" + "="*60)
print("DATABASE CONNECTION DIAGNOSTIC")
print("="*60)

print("\n[1] Configuration Details:")
print(f"    Host: {DB_CONFIG['host']}")
print(f"    User: {DB_CONFIG['user']}")
print(f"    Password: {'*' * len(DB_CONFIG['password'])}")
print(f"    Database: {DB_CONFIG['database']}")

print("\n[2] Testing Connection...")
connection = get_db_connection()

if connection:
    print("    ✓ Connection successful!")
    print("    ✓ MySQL server is running")
    print("    ✓ Credentials are valid")
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"    ✓ MySQL version: {version[0]}")
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"    ✗ Error querying MySQL: {e}")
else:
    print("    ✗ Connection failed!")
    print("    Please check:")
    print("       - MySQL server is running")
    print("       - Host: localhost")
    print("       - User: root")
    print("       - Password: simplepass123")
    print("       - Database exists: fake_review_db")

print("\n[3] Initializing Database...")
result = init_database()

if result:
    print("    ✓ Database initialized successfully!")
    print("    ✓ All tables created")
else:
    print("    ✗ Database initialization failed")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60 + "\n")
