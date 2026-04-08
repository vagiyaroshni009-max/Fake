/**
 * Dashboard Module
 * Handles review analysis, display, and user interactions
 */

// Global state
let currentAnalysisResults = [];
let currentProductId = null;

document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadAnalysisHistory();
});

/**
 * Setup all event listeners for dashboard
 */
function setupEventListeners() {
    const analyzeForm = document.getElementById('analyzeForm');
    const sampleBtn = document.getElementById('sampleBtn');

    if (analyzeForm) {
        analyzeForm.addEventListener('submit', handleAnalyzeSubmit);
    }

    if (sampleBtn) {
        sampleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            analyzeReviews(null, true, 'auto');
        });
    }

    setupHistoryNavigation();
}

/**
 * Handle form submission for URL analysis
 * @param {Event} e 
 */
async function handleAnalyzeSubmit(e) {
    e.preventDefault();

    const urlInput = document.getElementById('productUrl');
    const platformSelect = document.getElementById('platformSelect');
    const url = urlInput.value.trim();
    const platform = platformSelect ? platformSelect.value : 'auto';

    // Validate URL
    if (!url) {
        showUrlError('Please enter a product URL');
        return;
    }

    if (!isValidUrl(url)) {
        showUrlError('Please enter a valid URL');
        return;
    }

    clearUrlError();
    analyzeReviews(url, false, platform);
}

/**
 * Analyze reviews from URL or use sample data
 * @param {string|null} url - Product URL or null for sample
 * @param {boolean} useSample - Use sample data
 * @param {string} platform - Selected platform
 */
async function analyzeReviews(url, useSample, platform = 'auto') {
    const loadingSection = document.getElementById('loadingSection');
    const resultsSection = document.getElementById('resultsSection');
    const historySection = document.getElementById('historySection');

    // Hide previous results
    resultsSection.style.display = 'none';
    historySection.style.display = 'none';
    resetReviewerInsights();

    // Show loading
    loadingSection.style.display = 'block';

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                use_sample: useSample,
                platform: platform
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentAnalysisResults = data.reviews;
            currentProductId = data.product_id;
            displayResults(data);
            loadReviewerInsights(data.reviews || []);
            if (data.fetch_warning) {
                showAnalysisWarning(data.fetch_warning + '. Showing fallback sample data.');
            }
            document.getElementById('productUrl').value = '';
        } else {
            showAnalysisError(data.message);
        }
    } catch (error) {
        showAnalysisError('An error occurred during analysis. Please try again.');
        console.error('Analysis error:', error);
    } finally {
        loadingSection.style.display = 'none';
    }
}

/**
 * Display analysis results
 * @param {Object} data - Analysis results from API
 */
function displayResults(data) {
    const resultsSection = document.getElementById('resultsSection');
    const reviewsList = document.getElementById('reviewsList');

    // Update statistics
    const totalReviews = data.reviews.length;
    const fakeCount = data.reviews.filter(r => r.prediction === 'Fake').length;
    const genuineCount = totalReviews - fakeCount;
    const fakePercentage = totalReviews > 0 ? ((fakeCount / totalReviews) * 100).toFixed(1) : 0;

    document.getElementById('totalReviews').textContent = totalReviews;
    document.getElementById('fakeCount').textContent = fakeCount;
    document.getElementById('genuineCount').textContent = genuineCount;
    document.getElementById('fakePercentage').textContent = fakePercentage + '%';

    // Clear previous reviews
    reviewsList.innerHTML = '';

    // Display each review
    data.reviews.forEach((review, index) => {
        const reviewCard = createReviewCard(review, index);
        reviewsList.appendChild(reviewCard);
    });

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Fetch reviewer insights from backend add-on endpoint.
 * @param {Array} reviews
 */
async function loadReviewerInsights(reviews) {
    try {
        const response = await fetch('/reviewer-insights', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ reviews: reviews })
        });

        const data = await response.json();
        if (response.ok && data.success && data.insights) {
            renderReviewerInsights(data.insights);
        } else {
            resetReviewerInsights();
            console.error('Reviewer insights error:', data.message || 'Unknown error');
        }
    } catch (error) {
        resetReviewerInsights();
        console.error('Reviewer insights request failed:', error);
    }
}

/**
 * Render reviewer insights summary, charts and lists.
 * @param {Object} insights
 */
function renderReviewerInsights(insights) {
    const section = document.getElementById('reviewerInsightsSection');
    if (!section) {
        return;
    }

    document.getElementById('insightTotalReviews').textContent = insights.total_reviews || 0;
    document.getElementById('insightTotalReviewers').textContent = insights.total_reviewers || 0;
    document.getElementById('insightPositiveCount').textContent = insights.positive_reviews_count || 0;
    document.getElementById('insightNegativeCount').textContent = insights.negative_reviews_count || 0;
    document.getElementById('insightGenuineCount').textContent = insights.genuine_count || 0;
    document.getElementById('insightFakeCount').textContent = insights.fake_count || 0;

    const hasVerified = Object.prototype.hasOwnProperty.call(insights, 'verified_purchase_count');
    document.getElementById('insightVerifiedPurchases').textContent = hasVerified
        ? insights.verified_purchase_count
        : 'N/A';

    renderTopPositiveReviewers(insights.top_positive_reviewers || []);
    renderSuspiciousReviewers(insights.suspicious_reviewers || []);
    drawGenuineFakePieChart(insights.genuine_count || 0, insights.fake_count || 0);
    drawPositiveNegativeBarChart(insights.positive_reviews_count || 0, insights.negative_reviews_count || 0);

    section.style.display = 'block';
}

/**
 * Hide and clear reviewer insights section.
 */
function resetReviewerInsights() {
    const section = document.getElementById('reviewerInsightsSection');
    if (!section) {
        return;
    }

    section.style.display = 'none';
    clearCanvas('genuineFakePieChart');
    clearCanvas('positiveNegativeBarChart');

    const topList = document.getElementById('topPositiveReviewersList');
    const suspiciousList = document.getElementById('suspiciousReviewersList');
    if (topList) {
        topList.innerHTML = '';
    }
    if (suspiciousList) {
        suspiciousList.innerHTML = '';
    }
}

/**
 * Render top positive reviewers list.
 * @param {Array} reviewers
 */
function renderTopPositiveReviewers(reviewers) {
    const list = document.getElementById('topPositiveReviewersList');
    if (!list) {
        return;
    }

    if (!reviewers.length) {
        list.innerHTML = '<li class="empty-state">No repeat positive reviewers found.</li>';
        return;
    }

    list.innerHTML = reviewers.map(item => {
        const username = escapeHtml(String(item.username || 'Anonymous'));
        const count = Number(item.count || 0);
        return `<li><strong>${username}</strong> - ${count} positive reviews</li>`;
    }).join('');
}

/**
 * Render suspicious reviewers list.
 * @param {Array} reviewers
 */
function renderSuspiciousReviewers(reviewers) {
    const list = document.getElementById('suspiciousReviewersList');
    if (!list) {
        return;
    }

    if (!reviewers.length) {
        list.innerHTML = '<li class="empty-state">No suspicious reviewers flagged.</li>';
        return;
    }

    list.innerHTML = reviewers.map(item => {
        const username = escapeHtml(String(item.username || 'Anonymous'));
        const reason = escapeHtml(String(item.reason || 'No reason provided'));
        return `<li><strong>${username}</strong> - ${reason}</li>`;
    }).join('');
}

/**
 * Draw a pie chart for genuine vs fake counts.
 * @param {number} genuineCount
 * @param {number} fakeCount
 */
function drawGenuineFakePieChart(genuineCount, fakeCount) {
    const canvas = document.getElementById('genuineFakePieChart');
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const total = genuineCount + fakeCount;

    ctx.clearRect(0, 0, width, height);

    if (total <= 0) {
        drawNoDataText(ctx, width, height);
        return;
    }

    const centerX = Math.round(width * 0.35);
    const centerY = Math.round(height * 0.5);
    const radius = Math.min(width, height) * 0.3;

    const genuineColor = getCssVarValue('--success-color', '#22c55e');
    const fakeColor = getCssVarValue('--danger-color', '#ef4444');

    const genuineAngle = (genuineCount / total) * Math.PI * 2;
    let startAngle = -Math.PI / 2;

    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, startAngle + genuineAngle);
    ctx.closePath();
    ctx.fillStyle = genuineColor;
    ctx.fill();

    startAngle += genuineAngle;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, -Math.PI / 2 + Math.PI * 2);
    ctx.closePath();
    ctx.fillStyle = fakeColor;
    ctx.fill();

    drawChartLegend(ctx, [
        { label: `Genuine (${genuineCount})`, color: genuineColor },
        { label: `Fake (${fakeCount})`, color: fakeColor }
    ], width * 0.62, height * 0.4);
}

/**
 * Draw a bar chart for positive vs negative counts.
 * @param {number} positiveCount
 * @param {number} negativeCount
 */
function drawPositiveNegativeBarChart(positiveCount, negativeCount) {
    const canvas = document.getElementById('positiveNegativeBarChart');
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const maxValue = Math.max(positiveCount, negativeCount, 1);

    ctx.clearRect(0, 0, width, height);

    const leftPadding = 45;
    const bottomPadding = 35;
    const topPadding = 18;
    const chartWidth = width - leftPadding - 24;
    const chartHeight = height - topPadding - bottomPadding;
    const barWidth = Math.min(70, chartWidth / 3);
    const gap = Math.min(60, chartWidth / 4);
    const firstBarX = leftPadding + 25;
    const secondBarX = firstBarX + barWidth + gap;
    const baseY = topPadding + chartHeight;

    const positiveColor = getCssVarValue('--success-color', '#22c55e');
    const negativeColor = getCssVarValue('--danger-color', '#ef4444');
    const axisColor = '#94a3b8';

    ctx.strokeStyle = axisColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(leftPadding, topPadding);
    ctx.lineTo(leftPadding, baseY);
    ctx.lineTo(width - 16, baseY);
    ctx.stroke();

    const positiveBarHeight = (positiveCount / maxValue) * chartHeight;
    const negativeBarHeight = (negativeCount / maxValue) * chartHeight;

    ctx.fillStyle = positiveColor;
    ctx.fillRect(firstBarX, baseY - positiveBarHeight, barWidth, positiveBarHeight);
    ctx.fillStyle = negativeColor;
    ctx.fillRect(secondBarX, baseY - negativeBarHeight, barWidth, negativeBarHeight);

    ctx.fillStyle = '#111827';
    ctx.font = '12px Segoe UI, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(String(positiveCount), firstBarX + barWidth / 2, baseY - positiveBarHeight - 6);
    ctx.fillText(String(negativeCount), secondBarX + barWidth / 2, baseY - negativeBarHeight - 6);
    ctx.fillText('Positive', firstBarX + barWidth / 2, baseY + 16);
    ctx.fillText('Negative', secondBarX + barWidth / 2, baseY + 16);
}

/**
 * Draw chart legend blocks.
 * @param {CanvasRenderingContext2D} ctx
 * @param {Array} entries
 * @param {number} startX
 * @param {number} startY
 */
function drawChartLegend(ctx, entries, startX, startY) {
    ctx.font = '12px Segoe UI, sans-serif';
    ctx.textAlign = 'left';

    entries.forEach((entry, index) => {
        const y = startY + (index * 22);
        ctx.fillStyle = entry.color;
        ctx.fillRect(startX, y, 12, 12);
        ctx.fillStyle = '#111827';
        ctx.fillText(entry.label, startX + 18, y + 10);
    });
}

/**
 * Draw no-data text in chart area.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} width
 * @param {number} height
 */
function drawNoDataText(ctx, width, height) {
    ctx.fillStyle = '#6b7280';
    ctx.font = '13px Segoe UI, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No data available', width / 2, height / 2);
}

/**
 * Clear a chart canvas.
 * @param {string} canvasId
 */
function clearCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        return;
    }
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/**
 * Get CSS variable value from document root.
 * @param {string} variableName
 * @param {string} fallback
 * @returns {string}
 */
function getCssVarValue(variableName, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
    return value || fallback;
}

/**
 * Create a review card element
 * @param {Object} review 
 * @param {number} index 
 * @returns {HTMLElement}
 */
function createReviewCard(review, index) {
    const card = document.createElement('div');
    card.className = `review-card ${review.prediction === 'Genuine' ? 'genuine' : 'fake'}`;

    const sentimentIcon = getSentimentIcon(review.sentiment);
    const duplicateIndicator = review.is_duplicate ? '<span> • Duplicate</span>' : '';
    const anomalyIndicator = review.is_anomaly ? '<span> • Anomaly</span>' : '';

    card.innerHTML = `
        <div class="review-header">
            <div class="review-title">Review #${index + 1}</div>
            <span class="review-badge ${review.prediction === 'Genuine' ? 'badge-genuine' : 'badge-fake'}">
                ${review.prediction}
            </span>
        </div>

        <div class="review-text">
            "${review.text}"
        </div>

        <div class="review-meta">
            <div class="meta-item">
                <span class="meta-label">By:</span>
                <span>${escapeHtml(review.reviewer)}</span>
            </div>
            ${review.rating ? `
                <div class="meta-item">
                    <span class="meta-label">Rating:</span>
                    <span>${review.rating}/5.0 ⭐</span>
                </div>
            ` : ''}
        </div>

        <div class="review-stats">
            <div class="stat-item">
                <div class="stat-item-label">Confidence</div>
                <div class="stat-item-value">${review.confidence}%</div>
            </div>
            <div class="stat-item">
                <div class="stat-item-label">Sentiment</div>
                <div class="stat-item-value">${sentimentIcon} ${review.sentiment}</div>
            </div>
            ${review.is_duplicate ? `
                <div class="stat-item">
                    <div class="stat-item-label">⚠️ Duplicate</div>
                </div>
            ` : ''}
            ${review.is_anomaly ? `
                <div class="stat-item">
                    <div class="stat-item-label">⚠️ Anomaly</div>
                </div>
            ` : ''}
        </div>
    `;

    return card;
}

/**
 * Get sentiment icon
 * @param {string} sentiment 
 * @returns {string}
 */
function getSentimentIcon(sentiment) {
    const icons = {
        'Positive': '😊',
        'Negative': '😞',
        'Neutral': '😐'
    };
    return icons[sentiment] || sentiment;
}

/**
 * Load analysis history
 */
async function loadAnalysisHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        if (data.success && data.history.length > 0) {
            displayHistory(data.history);
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

/**
 * Display analysis history
 * @param {Array} history 
 */
function displayHistory(history) {
    const historyList = document.getElementById('historyList');

    if (historyList) {
        historyList.innerHTML = '';

        history.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';

            const date = new Date(item.analysis_date).toLocaleDateString();
            const fakePercent = item.fake_percentage ? item.fake_percentage.toFixed(1) : 0;

            historyItem.innerHTML = `
                <div class="history-info">
                    <h3>${truncateText(item.url || 'Sample Product', 50)}</h3>
                    <p>Analyzed on: ${date}</p>
                </div>
                <div class="history-stats">
                    <p><strong>${item.total_reviews}</strong> reviews</p>
                    <p><strong>${fakePercent}%</strong> fake</p>
                    <button class="btn btn-primary" onclick="viewProductDetails(${item.product_id})">
                        View Details
                    </button>
                </div>
            `;

            historyList.appendChild(historyItem);
        });

        const historySection = document.getElementById('historySection');
        if (historySection) {
            historySection.style.display = 'block';
        }
    }
}

/**
 * Setup history navigation
 */
function setupHistoryNavigation() {
    const historyLink = document.querySelector('.nav-link[href="#history"]');

    if (historyLink) {
        historyLink.addEventListener('click', function(e) {
            e.preventDefault();
            const historySection = document.getElementById('historySection');
            const resultsSection = document.getElementById('resultsSection');

            resultsSection.style.display = 'none';
            historySection.style.display = 'block';
            historySection.scrollIntoView({ behavior: 'smooth' });
            loadAnalysisHistory();
        });
    }
}

/**
 * View product details
 * @param {number} productId 
 */
async function viewProductDetails(productId) {
    try {
        const response = await fetch(`/api/product/${productId}`);
        const data = await response.json();

        if (data.success) {
            displayProductModal(data.product, data.reviews, data.summary);
        } else {
            showAnalysisError(data.message);
        }
    } catch (error) {
        showAnalysisError('Error loading product details');
        console.error('Error:', error);
    }
}

/**
 * Display product details in modal
 * @param {Object} product 
 * @param {Array} reviews 
 * @param {Object} summary 
 */
function displayProductModal(product, reviews, summary) {
    const modal = document.getElementById('reviewModal');
    const modalBody = document.getElementById('modalBody');

    const fakePercent = summary ? summary.fake_percentage.toFixed(1) : 0;

    modalBody.innerHTML = `
        <h2>Product Analysis Details</h2>
        <p><strong>URL:</strong> ${product.url}</p>
        <p><strong>Analyzed:</strong> ${new Date(product.created_at).toLocaleString()}</p>

        <h3>Summary</h3>
        <p>Total Reviews: ${reviews.length}</p>
        <p>Fake Reviews: ${summary ? summary.fake_count : 0} (${fakePercent}%)</p>
        <p>Genuine Reviews: ${summary ? summary.genuine_count : 0}</p>

        <h3>Reviews</h3>
        <div id="modalReviews"></div>
    `;

    const modalReviews = document.getElementById('modalReviews');
    reviews.forEach((review, index) => {
        const card = createReviewCard(review, index);
        modalReviews.appendChild(card);
    });

    modal.style.display = 'block';

    // Close button
    document.querySelector('.close').onclick = function() {
        modal.style.display = 'none';
    }

    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
}

/**
 * Validate URL format
 * @param {string} url 
 * @returns {boolean}
 */
function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch (error) {
        return false;
    }
}

/**
 * Show URL validation error
 * @param {string} message 
 */
function showUrlError(message) {
    const errorElement = document.getElementById('urlError');
    if (errorElement) {
        errorElement.textContent = message;
    }
}

/**
 * Clear URL validation error
 */
function clearUrlError() {
    const errorElement = document.getElementById('urlError');
    if (errorElement) {
        errorElement.textContent = '';
    }
}

/**
 * Show analysis error message
 * @param {string} message 
 */
function showAnalysisError(message) {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'none';

    alert(message);
}

/**
 * Show non-blocking warning message
 * @param {string} message 
 */
function showAnalysisWarning(message) {
    alert(message);
}

/**
 * Escape HTML entities to prevent XSS
 * @param {string} text 
 * @returns {string}
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Truncate text to specified length
 * @param {string} text 
 * @param {number} length 
 * @returns {string}
 */
function truncateText(text, length) {
    if (text.length > length) {
        return text.substring(0, length) + '...';
    }
    return text;
}
