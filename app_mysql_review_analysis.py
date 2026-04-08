"""
Flask app for product review analysis with MySQL persistence.

Requirements implemented:
1. Auto-create tables:
   - products (id, product_name, product_url)
   - reviews (id, product_id, review_text, sentiment, is_fake)
2. Save product + reviews after fetch/analyze.
3. Use mysql.connector.
4. Avoid duplicate products using product_url.
5. Integrate in Flask routes: /analyze and /search.
6. Return saved data with fake/genuine percentages.
7. Proper error handling with commit/rollback.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse, unquote

from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error

from model.scraper import ReviewScraper
from model.detector import SentimentAnalyzer

app = Flask(__name__)

# MySQL configuration from requirement
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "fake_review_db"),
    "port": int(os.getenv("DB_PORT", "3306")),
}

scraper = ReviewScraper()
sentiment_analyzer = SentimentAnalyzer()


def create_database_if_not_exists() -> None:
    """Create fake_review_db if it does not exist."""
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            port=DB_CONFIG["port"],
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
        connection.commit()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_db_connection():
    """Return a new MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)


def init_db() -> None:
    """Create required tables if they do not exist."""
    create_database_if_not_exists()

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                product_url VARCHAR(500) NOT NULL UNIQUE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL,
                review_text TEXT NOT NULL,
                sentiment VARCHAR(20) NOT NULL,
                is_fake BOOLEAN NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
            """
        )

        connection.commit()
    except Error:
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def slugify(text: str) -> str:
    """Create URL-safe slug from product name."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "-", cleaned) or "product"


def extract_name_from_url(product_url: str) -> str:
    """Infer product name from URL path if possible."""
    parsed = urlparse(product_url)
    tokens = [t for t in parsed.path.split("/") if t]
    if not tokens:
        return "Unknown Product"

    candidate = unquote(tokens[-1]).replace("-", " ").replace("_", " ").strip()
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate.title() if candidate else "Unknown Product"


def detect_fake_review(review_text: str) -> bool:
    """
    Simple rule-based fake review detection.
    Replace with your ML model if you already have one.
    """
    text = (review_text or "").strip()
    lower = text.lower()
    words = lower.split()

    suspicious_terms = {
        "guaranteed",
        "100%",
        "best ever",
        "must buy",
        "life changing",
        "unbelievable",
        "scam",
        "fake",
        "sponsored",
    }

    score = 0
    if len(words) < 4:
        score += 1
    if text.count("!") >= 3:
        score += 1
    if re.search(r"\b(\w+)(?:\s+\1){2,}\b", lower):
        score += 1
    if sum(term in lower for term in suspicious_terms) >= 2:
        score += 1

    return score >= 2


def analyze_reviews(raw_reviews: list[dict]) -> list[dict]:
    """Generate sentiment + fake flag for each review."""
    analyzed = []
    for item in raw_reviews:
        review_text = (item or {}).get("text", "").strip()
        if not review_text:
            continue

        sentiment_result = sentiment_analyzer.analyze_sentiment(review_text)
        sentiment = sentiment_result.get("label", "Neutral")
        is_fake = detect_fake_review(review_text)

        analyzed.append(
            {
                "review_text": review_text,
                "sentiment": sentiment,
                "is_fake": is_fake,
            }
        )
    return analyzed


def generate_reviews_for_name(product_name: str) -> list[dict]:
    """Fallback/demo reviews for product-name search."""
    templates = [
        f"I bought {product_name} recently and quality is good for the price.",
        f"{product_name} works as expected, delivery was on time.",
        f"Battery life of {product_name} is disappointing and support is slow.",
        f"{product_name} looks premium but performance is average.",
        f"Absolutely love {product_name}, worth buying.",
        f"{product_name} stopped working in one week. Not recommended.",
    ]
    return [{"text": line} for line in templates]


def fetch_product_details_and_reviews(
    product_url: str | None, product_name: str | None
) -> dict:
    """Fetch reviews by URL; fallback to name-based reviews."""
    if product_url:
        reviews, platform = scraper.scrape_reviews(product_url)
        if not reviews:
            reviews = scraper.create_sample_reviews()
            platform = "Sample Fallback"

        resolved_name = product_name or extract_name_from_url(product_url)
        resolved_url = product_url
        return {
            "product_name": resolved_name,
            "product_url": resolved_url,
            "platform": platform,
            "reviews": reviews,
        }

    # Name search path
    resolved_name = product_name or "Unknown Product"
    resolved_url = f"search://{slugify(resolved_name)}"
    reviews = generate_reviews_for_name(resolved_name)
    return {
        "product_name": resolved_name,
        "product_url": resolved_url,
        "platform": "Name Search",
        "reviews": reviews,
    }


def save_product_and_reviews(
    product_name: str, product_url: str, analyzed_reviews: list[dict]
) -> dict:
    """
    Save product + all analyzed reviews in one transaction.
    If product_url already exists, reuse product_id and refresh reviews.
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1) Duplicate product check by product_url
        cursor.execute(
            "SELECT id, product_name, product_url FROM products WHERE product_url = %s",
            (product_url,),
        )
        existing_product = cursor.fetchone()

        if existing_product:
            product_id = existing_product["id"]
            product_name = existing_product["product_name"] or product_name

            # Optional refresh behavior: replace previous reviews for same product.
            cursor.execute("DELETE FROM reviews WHERE product_id = %s", (product_id,))
            is_new_product = False
        else:
            # 2) Insert product and get product_id
            cursor.execute(
                "INSERT INTO products (product_name, product_url) VALUES (%s, %s)",
                (product_name, product_url),
            )
            product_id = cursor.lastrowid
            is_new_product = True

        # 3) Insert all reviews with product_id
        review_rows = [
            (
                product_id,
                review["review_text"],
                review["sentiment"],
                int(review["is_fake"]),
            )
            for review in analyzed_reviews
        ]
        if review_rows:
            cursor.executemany(
                """
                INSERT INTO reviews (product_id, review_text, sentiment, is_fake)
                VALUES (%s, %s, %s, %s)
                """,
                review_rows,
            )

        # 4) Commit transaction
        connection.commit()

        # Read saved rows for response
        cursor.execute(
            """
            SELECT id, product_id, review_text, sentiment, is_fake
            FROM reviews
            WHERE product_id = %s
            ORDER BY id ASC
            """,
            (product_id,),
        )
        saved_reviews = cursor.fetchall()

        return {
            "product_id": product_id,
            "product_name": product_name,
            "product_url": product_url,
            "is_new_product": is_new_product,
            "saved_reviews": saved_reviews,
        }

    except Error as db_error:
        if connection:
            connection.rollback()
        raise db_error
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def calculate_percentages(saved_reviews: list[dict]) -> dict:
    """Compute fake/genuine counts and percentages."""
    total = len(saved_reviews)
    fake_count = sum(1 for review in saved_reviews if bool(review["is_fake"]))
    genuine_count = total - fake_count

    fake_percentage = round((fake_count / total) * 100, 2) if total else 0.0
    genuine_percentage = round((genuine_count / total) * 100, 2) if total else 0.0

    return {
        "total_reviews": total,
        "fake_count": fake_count,
        "genuine_count": genuine_count,
        "fake_percentage": fake_percentage,
        "genuine_percentage": genuine_percentage,
    }


@app.route("/", methods=["GET"])
def health():
    return jsonify(
        {
            "success": True,
            "message": "Use POST /analyze or POST /search with product_url or product_name",
        }
    )


@app.route("/analyze", methods=["POST"])
@app.route("/search", methods=["POST"])
def analyze_or_search():
    """
    Analyze route:
    Accepts JSON body:
    {
      "product_url": "https://...",
      "product_name": "Optional product name"
    }
    """
    try:
        payload = request.get_json(silent=True) or request.form.to_dict() or {}

        product_url = (payload.get("product_url") or payload.get("url") or "").strip()
        product_name = (payload.get("product_name") or payload.get("name") or "").strip()

        if not product_url and not product_name:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Provide either product_url or product_name",
                    }
                ),
                400,
            )

        if product_url and not ReviewScraper.validate_url(product_url):
            return jsonify({"success": False, "message": "Invalid product_url"}), 400

        fetched = fetch_product_details_and_reviews(
            product_url=product_url or None,
            product_name=product_name or None,
        )

        analyzed_reviews = analyze_reviews(fetched["reviews"])
        if not analyzed_reviews:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "No reviews fetched for this product",
                    }
                ),
                404,
            )

        saved = save_product_and_reviews(
            product_name=fetched["product_name"],
            product_url=fetched["product_url"],
            analyzed_reviews=analyzed_reviews,
        )

        summary = calculate_percentages(saved["saved_reviews"])

        return (
            jsonify(
                {
                    "success": True,
                    "platform": fetched["platform"],
                    "product": {
                        "id": saved["product_id"],
                        "product_name": saved["product_name"],
                        "product_url": saved["product_url"],
                        "is_new_product": saved["is_new_product"],
                    },
                    "saved_reviews": saved["saved_reviews"],
                    "summary": summary,
                }
            ),
            200,
        )

    except Error as db_error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"MySQL error: {str(db_error)}",
                }
            ),
            500,
        )
    except Exception as ex:
        return jsonify({"success": False, "message": f"Server error: {str(ex)}"}), 500


if __name__ == "__main__":
    try:
        init_db()
        port = int(os.getenv("PORT", "5000"))
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as startup_error:
        print(f"Startup failed: {startup_error}")
