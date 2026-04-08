"""
Web scraping utilities for extracting reviews from e-commerce platforms
"""
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse
import warnings

warnings.filterwarnings('ignore')

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class ReviewScraper:
    """
    Scrape reviews from various e-commerce platforms
    """
    SUPPORTED_PLATFORMS = {'amazon', 'flipkart', 'shopsy', 'meesho', 'myntra'}
    
    BLOCKED_PATTERNS = (
        'captcha',
        'access denied',
        'temporarily blocked',
        'verify you are human',
        'robot check',
        'request blocked',
        'security check'
    )
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    def __init__(self):
        """Initialize scraper"""
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    @staticmethod
    def validate_url(url):
        """
        Validate if URL is valid
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if valid URL
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def get_platform(url):
        """
        Detect e-commerce platform from URL
        
        Args:
            url (str): Product URL
            
        Returns:
            str: Platform name
        """
        url_lower = url.lower()
        
        if 'amazon' in url_lower:
            return 'amazon'
        elif 'flipkart' in url_lower:
            return 'flipkart'
        elif 'shopsy' in url_lower:
            return 'shopsy'
        elif 'meesho' in url_lower:
            return 'meesho'
        elif 'myntra' in url_lower:
            return 'myntra'
        elif 'ebay' in url_lower:
            return 'ebay'
        elif 'aliexpress' in url_lower:
            return 'aliexpress'
        elif 'etsy' in url_lower:
            return 'etsy'
        else:
            return 'generic'
    
    @staticmethod
    def is_valid_review(text):
        """
        Validate if extracted text is a real review
        
        Args:
            text (str): Text to validate
            
        Returns:
            bool: True if text appears to be a real review
        """
        if not text:
            return False
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Check minimum length (at least 3 words for very short reviews with strong opinions)
        word_count = len(text.split())
        if word_count < 3:
            print(f"[SCRAPER VALIDATION] Rejected: Too short ({word_count} words)")
            return False
        
        # Ignore system-generated/non-review text patterns
        non_review_patterns = [
            r'^(order|shipped|arrived|delivered|delivered to)',
            r'^(package|item|product) (arrived|delivered|shipped)',
            r'^(tracking|delivery|shipment)',
            r'^(amazon|seller|returns?|refund|replacement)',
            r'^(not?|yes|no|ok)$',  # Single word responses
            r'^(thanks?|thank you|appreciate)',
            r'^(note for seller|message|comment)',
            r'^(location|region|city|address)',
            r'(order.*placed|order.*confirmed|cancelled)',
            r'(expected.*delivery|will arrive)',
            r'(this is a gift|gift wrap)',
            r'(waiting for|pending|in transit)',
        ]
        
        text_lower = text.lower()
        for pattern in non_review_patterns:
            if re.search(pattern, text_lower):
                print(f"[SCRAPER VALIDATION] Rejected: Matches non-review pattern")
                return False
        
        # Check if text contains typical review language
        opinion_words = [
            'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing',
            'quality', 'price', 'value', 'recommend', 'satisfied', 'happy',
            'disappointed', 'like', 'love', 'hate', 'waste', 'money', 'worth',
            'product', 'item', 'delivery', 'service', 'experience', 'purchase',
            'disappointed', 'awesome', 'horrible', 'perfect', 'scam', 'investment'
        ]
        
        has_opinion = any(word in text_lower for word in opinion_words)
        
        # Must either have opinion words or be reasonably long
        if not has_opinion and word_count < 10:
            print(f"[SCRAPER VALIDATION] Rejected: No opinion words ({word_count} words)")
            return False
        
        # Check for excessive repetition (fake indicator but also spam)
        # Only reject if VERY repetitive
        words = text.split()
        unique_ratio = len(set(words)) / len(words) if words else 0
        if unique_ratio < 0.4:  # Less than 40% unique words
            print(f"[SCRAPER VALIDATION] Rejected: Excessive repetition (unique ratio: {unique_ratio:.2f})")
            return False
        
        return True

    @staticmethod
    def _contains_blocked_content(html_text):
        """Check if a page appears blocked by anti-bot protection."""
        if not html_text:
            return False

        lowered = html_text.lower()
        return any(pattern in lowered for pattern in ReviewScraper.BLOCKED_PATTERNS)

    @staticmethod
    def _extract_rating_value(raw_rating, default=3.0):
        """
        Parse numeric rating from text (supports values like "4.5", "4 out of 5", "90/100").
        """
        if raw_rating is None:
            return default

        if isinstance(raw_rating, (int, float)):
            value = float(raw_rating)
        else:
            text = str(raw_rating).strip()
            if not text:
                return default

            out_of_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/)\s*(\d+\.?\d*)', text, re.I)
            if out_of_match:
                numerator = float(out_of_match.group(1))
                denominator = float(out_of_match.group(2))
                if denominator > 0:
                    value = (numerator / denominator) * 5
                else:
                    value = numerator
            else:
                num_match = re.search(r'(\d+\.?\d*)', text)
                if not num_match:
                    return default
                value = float(num_match.group(1))

        # Normalize to 5-star scale where possible.
        if value > 5 and value <= 10:
            value = value / 2
        elif value > 10 and value <= 100:
            value = value / 20

        # Clamp to valid range.
        value = max(0.0, min(5.0, value))
        return round(value, 1)

    @staticmethod
    def _set_query_param(url, key, value):
        """Set/replace a query parameter in a URL."""
        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        params[key] = str(value)
        updated_query = urlencode(params, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            updated_query,
            parsed.fragment
        ))

    def _build_paginated_urls(self, product_url, platform_name, max_pages=3):
        """
        Build candidate pagination URLs for platforms where reviews are split over pages.
        """
        urls = [product_url]
        if max_pages <= 1:
            return urls

        seen = {product_url}

        for page in range(2, max_pages + 1):
            page_candidates = []

            # Common pagination keys across Indian e-commerce pages.
            page_candidates.append(self._set_query_param(product_url, 'page', page))
            page_candidates.append(self._set_query_param(product_url, 'pageno', page))
            page_candidates.append(self._set_query_param(product_url, 'pageNumber', page))

            # Myntra commonly uses p for pagination.
            if platform_name == 'myntra':
                page_candidates.append(self._set_query_param(product_url, 'p', page))

            for candidate in page_candidates:
                if candidate not in seen:
                    seen.add(candidate)
                    urls.append(candidate)

        return urls

    def _fetch_html_requests(self, url):
        """
        Fetch HTML using requests with robust error handling.
        """
        response = self.session.get(url, timeout=15)
        if response.status_code in (403, 429, 503):
            raise RuntimeError(f"Request blocked with status {response.status_code}")

        response.raise_for_status()
        html = response.text

        if self._contains_blocked_content(html):
            raise RuntimeError("Request appears blocked by anti-bot checks")

        return html

    def _fetch_html_selenium(self, url):
        """
        Fetch rendered HTML for dynamic pages.
        """
        if not SELENIUM_AVAILABLE:
            print("[SCRAPER] Selenium not installed; skipping dynamic fetch fallback.")
            return None

        driver = None
        try:
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'user-agent={self.HEADERS["User-Agent"]}')

            driver = webdriver.Chrome(options=options)
            driver.get(url)

            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            # Scroll to trigger lazy loading / "load more" render logic.
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.2)

            return driver.page_source
        except Exception as e:
            print(f"[SCRAPER] Selenium fetch failed: {e}")
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _extract_reviews_from_soup(self, soup, source, review_selectors, limit=30):
        """
        Extract and normalize reviews from soup using CSS selector candidates.
        """
        reviews = []
        seen_reviews = set()
        containers = []

        for selector in review_selectors:
            selected = soup.select(selector)
            if selected:
                containers.extend(selected)

        if not containers:
            return reviews

        for container in containers:
            try:
                review_text = container.get_text(" ", strip=True)
                review_text = ' '.join(review_text.split())

                # Remove common tail content.
                review_text = re.sub(r'\b(read more|view more|show more)\b', '', review_text, flags=re.I).strip()

                if len(review_text) < 10:
                    continue

                normalized_text = review_text.lower()
                if normalized_text in seen_reviews:
                    continue

                if not self.is_valid_review(review_text):
                    continue

                # Try rating from nearby context.
                rating_value = None
                context_nodes = [container]
                parent = container
                for _ in range(2):
                    if parent and parent.parent:
                        parent = parent.parent
                        context_nodes.append(parent)

                for node in context_nodes:
                    rating_elem = node.select_one('[class*="rating"], [class*="star"], [aria-label*="star"], [title*="star"]')
                    if rating_elem:
                        rating_text = rating_elem.get('aria-label') or rating_elem.get('title') or rating_elem.get_text(" ", strip=True)
                        rating_value = self._extract_rating_value(rating_text, default=None)
                        if rating_value is not None:
                            break

                if rating_value is None:
                    rating_value = self._extract_rating_value(None, default=3.0)

                review_obj = {
                    'text': review_text[:500],
                    'review_text': review_text[:500],
                    'rating': rating_value,
                    'reviewer': 'Anonymous',
                    'platform': source.title(),
                    'source': source.lower()
                }

                reviews.append(review_obj)
                seen_reviews.add(normalized_text)

                if len(reviews) >= limit:
                    break
            except Exception:
                continue

        return reviews

    def _find_next_page_url(self, soup, current_url):
        """
        Find a likely next-page URL from pagination controls.
        """
        next_link = soup.select_one('a[rel="next"], a[aria-label*="Next"], a[class*="next"], li.next a')
        if not next_link:
            next_link = soup.find('a', string=re.compile(r'^\s*next\s*$', re.I))

        if not next_link:
            return None

        href = next_link.get('href')
        if not href:
            return None

        return urljoin(current_url, href)

    def _standardize_reviews(self, reviews, default_source):
        """
        Ensure every review has both legacy and requested keys.
        """
        standardized = []
        for item in reviews or []:
            if not isinstance(item, dict):
                continue

            text = str(item.get('text') or item.get('review_text') or '').strip()
            if not text:
                continue

            rating = self._extract_rating_value(item.get('rating'), default=3.0)
            source = str(item.get('source') or default_source).lower()
            platform_name = item.get('platform') or source.title()
            reviewer = item.get('reviewer') or 'Anonymous'

            standardized.append({
                'text': text[:500],
                'review_text': text[:500],
                'rating': rating,
                'reviewer': reviewer,
                'platform': platform_name,
                'source': source
            })

        return standardized
    
    def scrape_amazon(self, url):
        """
        Scrape reviews from Amazon product page using proper selectors
        
        Args:
            url (str): Amazon product URL
            
        Returns:
            list: List of review dictionaries
        """
        reviews = []
        print(f"[SCRAPER] Attempting to scrape Amazon: {url[:60]}...")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # PRIMARY SELECTOR: Amazon's main review body container
            # Using data-hook="review-body" attribute
            print(f"[SCRAPER] Searching for review containers with data-hook='review-body'...")
            review_bodies = soup.find_all('span', {'data-hook': 'review-body'})
            print(f"[SCRAPER] Found {len(review_bodies)} review body containers")
            
            if not review_bodies:
                # Fallback selectors
                print(f"[SCRAPER] Fallback: Searching with alternative selectors...")
                alt_selectors = [
                    soup.find_all('div', {'class': re.compile(r'a-row.*review-content')}),
                    soup.find_all('div', {'id': re.compile(r'customer-reviews')}),
                    soup.find_all('span', {'class': 'a-size-base review-text'}),
                ]
                
                for alt_result in alt_selectors:
                    if alt_result:
                        print(f"[SCRAPER] Found {len(alt_result)} containers with fallback selector")
                        review_bodies = alt_result
                        break
            
            print(f"[SCRAPER] Processing {len(review_bodies)} review containers...")
            
            seen_reviews = set()  # Track duplicates
            for idx, review_elem in enumerate(review_bodies[:25], 1):  # Limit to first 25
                try:
                    # Extract review text
                    review_text = review_elem.get_text(strip=True)
                    
                    if not review_text or len(review_text) < 10:
                        continue
                    
                    # Check for duplicates
                    if review_text in seen_reviews:
                        print(f"[SCRAPER] Review #{idx}: Duplicate, skipping")
                        continue
                    
                    # Validate review text
                    if not self.is_valid_review(review_text):
                        print(f"[SCRAPER] Review #{idx}: Validation failed")
                        continue
                    
                    seen_reviews.add(review_text)
                    
                    # Try to find parent container for rating and reviewer info
                    parent = review_elem.find_parent('div', {'class': re.compile(r'review.*')})
                    if not parent:
                        parent = review_elem.find_parent('div')
                    
                    # Extract rating
                    rating = None
                    if parent:
                        rating_elem = parent.find('i', {'class': re.compile(r'a-icon-star')})
                        if rating_elem:
                            try:
                                rating_text = rating_elem.get_text(strip=True)
                                rating = float(rating_text.split()[0])
                            except:
                                pass
                    
                    # Extract reviewer name
                    reviewer_name = 'Anonymous'
                    if parent:
                        reviewer = parent.find('span', {'class': re.compile(r'a-profile-name')})
                        if reviewer:
                            reviewer_name = reviewer.get_text(strip=True)
                    
                    review_obj = {
                        'text': review_text[:500],  # Limit text length
                        'rating': rating if rating else 3.0,
                        'reviewer': reviewer_name,
                        'platform': 'Amazon'
                    }
                    
                    reviews.append(review_obj)
                    print(f"[SCRAPER] Review #{idx} (✓ Valid): {review_text[:70]}...")
                    
                except Exception as e:
                    print(f"[SCRAPER] Review #{idx}: Parse error - {str(e)[:50]}")
                    continue
            
            print(f"\n[SCRAPER] ✓ Successfully extracted {len(reviews)} valid reviews from Amazon")
        
        except Exception as e:
            print(f"[SCRAPER] ✗ Error scraping Amazon: {e}")
            return []
        
        return reviews
    
    def scrape_flipkart(self, url):
        """
        Scrape reviews from Flipkart product page using proper selectors
        
        Args:
            url (str): Flipkart product URL
            
        Returns:
            list: List of review dictionaries
        """
        reviews = []
        print(f"[SCRAPER] Attempting to scrape Flipkart: {url[:60]}...")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # PRIMARY SELECTOR: Flipkart's review text container
            # Using class "t-ZTKy" for review content
            print(f"[SCRAPER] Searching for review containers with class 't-ZTKy'...")
            review_containers = soup.find_all('div', {'class': 't-ZTKy'})
            print(f"[SCRAPER] Found {len(review_containers)} review containers with class 't-ZTKy'")
            
            if not review_containers:
                # Fallback: Try alternative Flipkart selectors
                print(f"[SCRAPER] Fallback: Searching with alternative Flipkart selectors...")
                alt_selectors = [
                    soup.find_all('div', {'class': re.compile(r'review-content|reviewContent')}),
                    soup.find_all('div', {'class': re.compile(r'_1PZc_')}),  # Another Flipkart review class
                    soup.find_all('p', {'class': re.compile(r'review')}),
                ]
                
                for alt_result in alt_selectors:
                    if alt_result:
                        print(f"[SCRAPER] Found {len(alt_result)} containers with fallback selector")
                        review_containers = alt_result
                        break
            
            print(f"[SCRAPER] Processing {len(review_containers)} review containers...")
            
            seen_reviews = set()
            for idx, review_elem in enumerate(review_containers[:25], 1):  # Limit to first 25
                try:
                    # Extract review text
                    review_text = review_elem.get_text(strip=True)
                    
                    if not review_text or len(review_text) < 10:
                        continue
                    
                    # Check for duplicates
                    if review_text in seen_reviews:
                        print(f"[SCRAPER] Review #{idx}: Duplicate, skipping")
                        continue
                    
                    # Validate review text
                    if not self.is_valid_review(review_text):
                        print(f"[SCRAPER] Review #{idx}: Validation failed")
                        continue
                    
                    seen_reviews.add(review_text)
                    
                    # Find parent container for rating and reviewer info
                    parent = review_elem.find_parent('div', {'class': re.compile(r'review')})
                    if not parent:
                        parent = review_elem.find_parent('div')
                    
                    # Extract rating
                    rating = None
                    if parent:
                        # Flipkart rating - look for star icons or rating text
                        rating_elem = parent.find(class_=re.compile(r'star|rating|_1t2oC', re.I))
                        if rating_elem:
                            try:
                                rating_text = rating_elem.get_text(strip=True)
                                # Extract first number
                                match = re.search(r'(\d+\.?\d*)', rating_text)
                                if match:
                                    rating = float(match.group(1))
                            except:
                                pass
                    
                    # Extract reviewer name
                    reviewer_name = 'Anonymous'
                    if parent:
                        reviewer = parent.find(class_=re.compile(r'reviewer|user|author', re.I))
                        if reviewer:
                            reviewer_name = reviewer.get_text(strip=True)
                    
                    review_obj = {
                        'text': review_text[:500],  # Limit text length
                        'rating': rating if rating else 3.0,
                        'reviewer': reviewer_name,
                        'platform': 'Flipkart'
                    }
                    
                    reviews.append(review_obj)
                    print(f"[SCRAPER] Review #{idx} (✓ Valid): {review_text[:70]}...")
                    
                except Exception as e:
                    print(f"[SCRAPER] Review #{idx}: Parse error - {str(e)[:50]}")
                    continue
            
            print(f"\n[SCRAPER] ✓ Successfully extracted {len(reviews)} valid reviews from Flipkart")
        
        except Exception as e:
            print(f"[SCRAPER] ✗ Error scraping Flipkart: {e}")
            return []
        
        return reviews

    def _fetch_paginated_reviews(self, product_url, source, review_selectors, max_pages=3, max_reviews=60):
        """
        Shared pagination-aware fetcher used by Shopsy/Meesho/Myntra scrapers.
        """
        if not self.validate_url(product_url):
            raise ValueError("Invalid URL format")

        all_reviews = []
        seen = set()
        visited_urls = set()
        candidate_urls = self._build_paginated_urls(product_url, source, max_pages=max_pages)

        index = 0
        while index < len(candidate_urls) and len(visited_urls) < max_pages and len(all_reviews) < max_reviews:
            page_url = candidate_urls[index]
            index += 1

            if page_url in visited_urls:
                continue
            visited_urls.add(page_url)

            try:
                html = self._fetch_html_requests(page_url)
            except Exception as e:
                print(f"[SCRAPER] {source.title()} page fetch failed for {page_url}: {e}")
                continue

            soup = BeautifulSoup(html, 'html.parser')
            page_reviews = self._extract_reviews_from_soup(
                soup=soup,
                source=source,
                review_selectors=review_selectors,
                limit=max_reviews
            )

            for review in page_reviews:
                normalized = review.get('text', '').lower()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                all_reviews.append(review)
                if len(all_reviews) >= max_reviews:
                    break

            next_page = self._find_next_page_url(soup, page_url)
            if next_page and next_page not in visited_urls and next_page not in candidate_urls:
                candidate_urls.append(next_page)

        # Dynamic-content fallback when static requests returned no reviews.
        if not all_reviews:
            print(f"[SCRAPER] No static reviews found for {source.title()}, trying Selenium fallback...")
            rendered_html = self._fetch_html_selenium(product_url)
            if rendered_html:
                rendered_soup = BeautifulSoup(rendered_html, 'html.parser')
                dynamic_reviews = self._extract_reviews_from_soup(
                    soup=rendered_soup,
                    source=source,
                    review_selectors=review_selectors,
                    limit=max_reviews
                )
                for review in dynamic_reviews:
                    normalized = review.get('text', '').lower()
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    all_reviews.append(review)
                    if len(all_reviews) >= max_reviews:
                        break

        standardized = self._standardize_reviews(all_reviews, default_source=source)
        if not standardized:
            print(f"[SCRAPER] Unable to fetch reviews from {source.title()}")

        return standardized

    def fetch_shopsy_reviews(self, product_url):
        """
        Fetch reviews from Shopsy product pages.
        Required output keys: review_text, rating, source.
        """
        selectors = [
            'div[class*=\"review\"] p',
            'div[class*=\"review\"] span',
            'div[data-testid*=\"review\"]',
            'li[class*=\"review\"]',
            'section[class*=\"review\"] div[class*=\"content\"]'
        ]
        try:
            return self._fetch_paginated_reviews(
                product_url=product_url,
                source='shopsy',
                review_selectors=selectors,
                max_pages=4,
                max_reviews=60
            )
        except Exception as e:
            print(f"[SCRAPER] Error fetching Shopsy reviews: {e}")
            return []

    def fetch_meesho_reviews(self, product_url):
        """
        Fetch reviews from Meesho product pages.
        Required output keys: review_text, rating, source.
        """
        selectors = [
            'div[class*=\"review\"] p',
            'div[class*=\"review\"] span',
            'div[class*=\"ReviewCard\"]',
            'div[class*=\"review-card\"]',
            'div[data-testid*=\"review\"]'
        ]
        try:
            return self._fetch_paginated_reviews(
                product_url=product_url,
                source='meesho',
                review_selectors=selectors,
                max_pages=4,
                max_reviews=60
            )
        except Exception as e:
            print(f"[SCRAPER] Error fetching Meesho reviews: {e}")
            return []

    def fetch_myntra_reviews(self, product_url):
        """
        Fetch reviews from Myntra product pages.
        Required output keys: review_text, rating, source.
        """
        selectors = [
            'div[class*=\"user-review\"]',
            'div[class*=\"review\"] p',
            'div[class*=\"review-text\"]',
            'li[class*=\"review\"]',
            'div[data-test*=\"review\"]'
        ]
        try:
            return self._fetch_paginated_reviews(
                product_url=product_url,
                source='myntra',
                review_selectors=selectors,
                max_pages=4,
                max_reviews=60
            )
        except Exception as e:
            print(f"[SCRAPER] Error fetching Myntra reviews: {e}")
            return []

    def fetch_all_reviews(self, product_url, platform):
        """
        Unified review fetcher for all supported platforms.

        Args:
            product_url (str): Product URL.
            platform (str): One of amazon/flipkart/shopsy/meesho/myntra or "auto".

        Returns:
            tuple: (reviews, resolved_platform)
        """
        if not self.validate_url(product_url):
            raise ValueError("Invalid URL format")

        requested_platform = (platform or '').strip().lower()
        if requested_platform in ('', 'auto'):
            requested_platform = self.get_platform(product_url)

        if requested_platform == 'amazon':
            reviews = self.scrape_amazon(product_url)
        elif requested_platform == 'flipkart':
            reviews = self.scrape_flipkart(product_url)
        elif requested_platform == 'shopsy':
            reviews = self.fetch_shopsy_reviews(product_url)
        elif requested_platform == 'meesho':
            reviews = self.fetch_meesho_reviews(product_url)
        elif requested_platform == 'myntra':
            reviews = self.fetch_myntra_reviews(product_url)
        else:
            # Keep generic behavior for unsupported/legacy URLs.
            reviews = self.scrape_generic(product_url)
            requested_platform = 'generic'

        standardized = self._standardize_reviews(reviews, default_source=requested_platform)
        return standardized, requested_platform
    
    def scrape_generic(self, url):
        """
        Generic review scraping for any website with improved validation
        
        Args:
            url (str): Website URL
            
        Returns:
            list: List of review dictionaries
        """
        reviews = []
        print(f"[SCRAPER] Attempting generic scrape: {url[:60]}...")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Collection of strategies to find review containers, in priority order
            print(f"[SCRAPER] Trying multiple strategies to locate reviews...")
            strategy_results = []
            
            # Strategy 1: Look for elements with 'review' in class/id
            print(f"[SCRAPER] Strategy 1: Looking for 'review' in class/id...")
            review_elements = soup.find_all(class_=re.compile('review', re.I))
            if review_elements:
                strategy_results.append(('review class pattern', review_elements[:20]))
                print(f"[SCRAPER] Strategy 1 found {len(review_elements)} elements")
            
            # Strategy 2: Look for 'comment' or 'feedback'
            if not strategy_results:
                print(f"[SCRAPER] Strategy 2: Looking for 'comment' or 'feedback'...")
                comment_elements = soup.find_all(class_=re.compile('comment|feedback', re.I))
                if comment_elements:
                    strategy_results.append(('comment/feedback class pattern', comment_elements[:20]))
                    print(f"[SCRAPER] Strategy 2 found {len(comment_elements)} elements")
            
            # Strategy 3: Look for 'rating' or 'star'
            if not strategy_results:
                print(f"[SCRAPER] Strategy 3: Looking for 'rating' or 'star'...")
                rating_elements = soup.find_all(class_=re.compile('rating|star', re.I))
                if rating_elements:
                    strategy_results.append(('rating/star class pattern', rating_elements[:20]))
                    print(f"[SCRAPER] Strategy 3 found {len(rating_elements)} elements")
            
            # Strategy 4: Look for article tags (common for reviews)
            if not strategy_results:
                print(f"[SCRAPER] Strategy 4: Looking for article tags...")
                articles = soup.find_all('article')
                if articles:
                    strategy_results.append(('article tags', articles[:20]))
                    print(f"[SCRAPER] Strategy 4 found {len(articles)} elements")
            
            # Strategy 5: Look for divs with substantial text content
            if not strategy_results:
                print(f"[SCRAPER] Strategy 5: Looking for divs with substantial text...")
                large_divs = [
                    d for d in soup.find_all('div') 
                    if 100 < len(d.get_text(strip=True)) < 2000
                ][:20]
                if large_divs:
                    strategy_results.append(('large text divs', large_divs))
                    print(f"[SCRAPER] Strategy 5 found {len(large_divs)} elements")
            
            if not strategy_results:
                print(f"[SCRAPER] ✗ No review containers found using any strategy")
                return []
            
            strategy_name, review_containers = strategy_results[0]
            print(f"[SCRAPER] Using strategy: {strategy_name} with {len(review_containers)} containers\n")
            
            # Extract reviews with validation
            seen_reviews = set()
            for idx, container in enumerate(review_containers, 1):
                try:
                    # Try to extract meaningful text from container
                    review_text = None
                    
                    # Priority 1: Look for paragraph tags
                    p_elem = container.find('p')
                    if p_elem:
                        review_text = p_elem.get_text(strip=True)
                    
                    # Priority 2: Look for span tags
                    if not review_text:
                        span_elem = container.find('span', class_=re.compile('text|content|body', re.I))
                        if span_elem:
                            review_text = span_elem.get_text(strip=True)
                    
                    # Priority 3: Look for div with specific classes
                    if not review_text:
                        div_elem = container.find('div', class_=re.compile('text|content|body|review', re.I))
                        if div_elem:
                            review_text = div_elem.get_text(strip=True)
                    
                    # Priority 4: Use container's direct text (as last resort)
                    if not review_text:
                        review_text = container.get_text(strip=True)
                    
                    # Clean and validate text
                    if not review_text:
                        print(f"[SCRAPER] Review #{idx}: No text found")
                        continue
                    
                    # Remove extra whitespace
                    review_text = ' '.join(review_text.split())
                    
                    # Check length constraints (valid review should be 20-2000 chars)
                    if len(review_text) < 20 or len(review_text) > 2000:
                        print(f"[SCRAPER] Review #{idx}: Invalid length ({len(review_text)} chars)")
                        continue
                    
                    # Check for duplicates
                    if review_text in seen_reviews:
                        print(f"[SCRAPER] Review #{idx}: Duplicate, skipping")
                        continue
                    
                    # Validate review content
                    if not self.is_valid_review(review_text):
                        print(f"[SCRAPER] Review #{idx}: Content validation failed")
                        continue
                    
                    seen_reviews.add(review_text)
                    
                    # Try to extract rating if available
                    rating = None
                    rating_elem = container.find(class_=re.compile('rating|star|score', re.I))
                    if rating_elem:
                        try:
                            rating_text = rating_elem.get_text(strip=True)
                            match = re.search(r'(\d+\.?\d*)', rating_text)
                            if match:
                                rating = float(match.group(1))
                                if rating > 10:  # Likely percentage, convert to 5-star
                                    rating = rating / 20
                        except:
                            pass
                    
                    review_obj = {
                        'text': review_text[:500],  # Limit to 500 chars
                        'rating': rating if rating else 3.0,
                        'reviewer': 'Anonymous',
                        'platform': 'Generic'
                    }
                    
                    reviews.append(review_obj)
                    print(f"[SCRAPER] Review #{idx} (✓ Valid): {review_text[:70]}...")
                    
                    # Stop after finding enough reviews
                    if len(reviews) >= 10:
                        break
                    
                except Exception as e:
                    print(f"[SCRAPER] Review #{idx}: Processing error - {str(e)[:50]}")
                    continue
            
            print(f"\n[SCRAPER] ✓ Successfully extracted {len(reviews)} valid reviews from generic site")
        
        except Exception as e:
            print(f"[SCRAPER] ✗ Error scraping website: {e}")
            return []
        
        return reviews
    
    def scrape_reviews(self, url):
        """
        Scrape reviews from given URL
        
        Args:
            url (str): Product/website URL
            
        Returns:
            tuple: (reviews_list, platform)
        """
        print(f"\n[SCRAPER] Starting review scraping...")
        print(f"[SCRAPER] URL: {url}")
        
        if not self.validate_url(url):
            print(f"[SCRAPER] Invalid URL format")
            return [], 'invalid'
        
        platform = self.get_platform(url)
        print(f"[SCRAPER] Detected platform: {platform}")
        
        try:
            reviews, resolved_platform = self.fetch_all_reviews(url, platform)
            
            if reviews:
                print(f"[SCRAPER] Successfully scraped {len(reviews)} reviews")
                if len(reviews) > 0:
                    print(f"[SCRAPER] Sample review: {reviews[0]['text'][:80]}...")
            else:
                print(f"[SCRAPER] No reviews found - will use fallback sample data")
            
            time.sleep(1)  # Be respectful to servers
            return reviews, resolved_platform
        
        except Exception as e:
            print(f"[SCRAPER] Exception during scraping: {e}")
            print(f"[SCRAPER] Will use fallback sample data")
            return [], platform
    
    def create_sample_reviews(self):
        """
        Create sample reviews for testing/demo purposes
        
        Returns:
            list: List of sample review dictionaries
        """
        sample_reviews = [
            {
                'text': 'Amazing product! Very satisfied with quality and delivery.',
                'rating': 5.0,
                'reviewer': 'John Doe',
                'platform': 'Sample'
            },
            {
                'text': 'Best purchase ever made! Highly recommended for everyone.',
                'rating': 5.0,
                'reviewer': 'Jane Smith',
                'platform': 'Sample'
            },
            {
                'text': 'Product arrived on time and works perfectly. Great value!',
                'rating': 4.0,
                'reviewer': 'Mike Johnson',
                'platform': 'Sample'
            },
            {
                'text': 'Not as described. Terrible quality. Waste of money.',
                'rating': 1.0,
                'reviewer': 'Sarah Williams',
                'platform': 'Sample'
            },
            {
                'text': 'Good product but took long to deliver. Average customer service.',
                'rating': 3.0,
                'reviewer': 'David Brown',
                'platform': 'Sample'
            },
            {
                'text': 'Excellent! Exceeded expectations. Will buy again soon.',
                'rating': 5.0,
                'reviewer': 'Emma Davis',
                'platform': 'Sample'
            },
            {
                'text': 'Worst product ever! Complete scam. Avoid at all costs.',
                'rating': 1.0,
                'reviewer': 'Robert Miller',
                'platform': 'Sample'
            },
            {
                'text': 'Decent product for the price. Works as expected.',
                'rating': 3.5,
                'reviewer': 'Lisa Anderson',
                'platform': 'Sample'
            },
        ]
        
        return sample_reviews


def fetch_shopsy_reviews(product_url):
    """Module-level wrapper for Shopsy reviews."""
    return ReviewScraper().fetch_shopsy_reviews(product_url)


def fetch_meesho_reviews(product_url):
    """Module-level wrapper for Meesho reviews."""
    return ReviewScraper().fetch_meesho_reviews(product_url)


def fetch_myntra_reviews(product_url):
    """Module-level wrapper for Myntra reviews."""
    return ReviewScraper().fetch_myntra_reviews(product_url)


def fetch_all_reviews(product_url, platform):
    """Module-level wrapper for unified platform fetch."""
    reviews, _ = ReviewScraper().fetch_all_reviews(product_url, platform)
    return reviews
