"""
Database configuration and connection utilities
"""
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

# Required MySQL configuration (from environment variables)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'fake_review_db'),
    'port': int(os.getenv('DB_PORT', 3306))
}


def ensure_database_exists():
    """Create database if it doesn't exist."""
    conn = None
    cursor = None
    try:
        config_no_db = {
            'host': DB_CONFIG['host'],
            'user': DB_CONFIG['user'],
            'password': DB_CONFIG['password'],
            'port': DB_CONFIG['port']
        }
        conn = mysql.connector.connect(**config_no_db)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
        conn.commit()
        print(f"[DB] Database '{DB_CONFIG['database']}' is ready")
        return True
    except Error as e:
        print(f"[DB] Error creating database: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print("Connected to DB")
            return conn
        print("[DB] Connection failed: connection object created but not connected")
        return None
    except Error as e:
        print(f"[DB] Connection failed: {e}")
        return None


def _column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (DB_CONFIG['database'], table_name, column_name)
    )
    return cursor.fetchone() is not None


def _ensure_column(cursor, table_name, column_name, definition):
    """Add column if missing."""
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_database():
    """Initialize database with required tables."""
    print("[DB INIT] Ensuring database exists...")
    ensure_database_exists()

    conn = get_db_connection()
    if not conn:
        print("[DB INIT] X Failed to connect to database")
        return False

    print("[DB INIT] Creating tables...")
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                url VARCHAR(500) NOT NULL,
                product_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Required columns: id, product_url, review_text, prediction, confidence
        # Extra columns kept for compatibility with existing project routes/logic.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INT PRIMARY KEY AUTO_INCREMENT,
                product_id INT,
                product_url TEXT,
                review_text TEXT NOT NULL,
                prediction VARCHAR(20),
                confidence FLOAT,
                reviewer_name VARCHAR(255),
                rating FLOAT,
                sentiment VARCHAR(20),
                is_duplicate BOOLEAN DEFAULT FALSE,
                is_anomaly BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
            """
        )

        # For old deployments where reviews table already exists with missing columns,
        # backfill every column used by insert_review_if_not_exists().
        _ensure_column(cursor, 'reviews', 'product_id', 'INT')
        _ensure_column(cursor, 'reviews', 'product_url', 'TEXT')
        _ensure_column(cursor, 'reviews', 'review_text', 'TEXT NOT NULL')
        _ensure_column(cursor, 'reviews', 'prediction', 'VARCHAR(20)')
        _ensure_column(cursor, 'reviews', 'confidence', 'FLOAT')
        _ensure_column(cursor, 'reviews', 'reviewer_name', 'VARCHAR(255)')
        _ensure_column(cursor, 'reviews', 'rating', 'FLOAT')
        _ensure_column(cursor, 'reviews', 'sentiment', 'VARCHAR(20)')
        _ensure_column(cursor, 'reviews', 'is_duplicate', 'BOOLEAN DEFAULT FALSE')
        _ensure_column(cursor, 'reviews', 'is_anomaly', 'BOOLEAN DEFAULT FALSE')

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INT PRIMARY KEY AUTO_INCREMENT,
                product_id INT NOT NULL,
                total_reviews INT,
                fake_count INT,
                genuine_count INT,
                fake_percentage FLOAT,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
            """
        )

        conn.commit()
        print("[DB INIT] ? Database initialized successfully - all tables created")
        return True

    except Error as e:
        conn.rollback()
        print(f"[DB INIT] X Error initializing database: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def execute_query(query, params=None):
    """Execute query and return results."""
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed")

    cursor = conn.cursor(dictionary=True)

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().upper().startswith('SELECT'):
            return cursor.fetchall()

        conn.commit()
        return cursor.rowcount

    except Error as e:
        error_code = e.errno if hasattr(e, 'errno') else None
        error_msg = str(e)
        print(f"[DB ERROR] Query failed - Code {error_code}: {error_msg}")
        conn.rollback()
        raise Exception(f"Query error ({error_code}): {error_msg}")

    finally:
        cursor.close()
        conn.close()


def execute_insert(query, params=None):
    """Execute insert query and return inserted id."""
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed")

    cursor = conn.cursor()

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        conn.commit()
        return cursor.lastrowid

    except Error as e:
        error_code = e.errno if hasattr(e, 'errno') else None
        error_msg = str(e)
        print(f"[DB ERROR] Insert failed - Code {error_code}: {error_msg}")
        conn.rollback()

        if error_code == 1062:
            raise Exception(f"Duplicate entry: {error_msg}")
        raise Exception(f"Insert error ({error_code}): {error_msg}")

    finally:
        cursor.close()
        conn.close()


def insert_review_if_not_exists(product_id, product_url, review_text, prediction, confidence,
                                reviewer_name=None, rating=None, sentiment=None,
                                is_duplicate=False, is_anomaly=False):
    """
    Insert review only if same review text for same product URL does not already exist.
    Returns True when inserted, False when duplicate.
    """
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed")

    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id FROM reviews
            WHERE product_url = %s AND review_text = %s
            LIMIT 1
            """,
            (product_url, review_text)
        )
        existing = cursor.fetchone()
        if existing:
            return False

        cursor.execute(
            """
            INSERT INTO reviews
            (product_id, product_url, review_text, prediction, confidence,
             reviewer_name, rating, sentiment, is_duplicate, is_anomaly)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (product_id, product_url, review_text, prediction, confidence,
             reviewer_name, rating, sentiment, is_duplicate, is_anomaly)
        )
        conn.commit()
        return True

    except Error as e:
        conn.rollback()
        raise Exception(f"Insert review error: {e}")

    finally:
        cursor.close()
        conn.close()
