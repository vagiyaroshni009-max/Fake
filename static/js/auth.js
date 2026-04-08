/**
 * Authentication Module
 * Handles login, signup, and password reset forms
 */

document.addEventListener('DOMContentLoaded', function() {
    // Determine which form to handle
    if (document.getElementById('loginForm')) {
        setupLoginForm();
    }
    if (document.getElementById('signupForm')) {
        setupSignupForm();
    }
    if (document.getElementById('forgotForm')) {
        setupForgotForm();
    }
});

/**
 * Setup login form handler
 */
function setupLoginForm() {
    const form = document.getElementById('loginForm');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const formMessage = document.getElementById('formMessage');
    const submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Clear previous messages
        clearFormMessages();
        clearFieldErrors();

        // Validate inputs
        if (!emailInput.value.trim()) {
            showFieldError('emailError', 'Email is required');
            return;
        }

        if (!isValidEmail(emailInput.value)) {
            showFieldError('emailError', 'Please enter a valid email');
            return;
        }

        if (!passwordInput.value.trim()) {
            showFieldError('passwordError', 'Password is required');
            return;
        }

        // Set loading state
        setLoadingState(submitBtn, true);

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: emailInput.value.trim(),
                    password: passwordInput.value
                })
            });

            const data = await response.json();

            if (response.ok) {
                showFormMessage(formMessage, data.message, 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            } else {
                showFormMessage(formMessage, data.message, 'error');
            }
        } catch (error) {
            showFormMessage(formMessage, 'An error occurred. Please try again.', 'error');
            console.error('Login error:', error);
        } finally {
            setLoadingState(submitBtn, false);
        }
    });
}

/**
 * Setup signup form handler
 */
function setupSignupForm() {
    const form = document.getElementById('signupForm');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const formMessage = document.getElementById('formMessage');
    const submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Clear previous messages
        clearFormMessages();
        clearFieldErrors();

        // Validate inputs
        if (!validateSignupForm(emailInput, passwordInput, confirmPasswordInput)) {
            return;
        }

        // Set loading state
        setLoadingState(submitBtn, true);

        try {
            const response = await fetch('/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: emailInput.value.trim(),
                    password: passwordInput.value,
                    confirm_password: confirmPasswordInput.value
                })
            });

            const data = await response.json();

            if (response.ok) {
                showFormMessage(formMessage, data.message, 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            } else {
                showFormMessage(formMessage, data.message, 'error');
            }
        } catch (error) {
            showFormMessage(formMessage, 'An error occurred. Please try again.', 'error');
            console.error('Signup error:', error);
        } finally {
            setLoadingState(submitBtn, false);
        }
    });
}

/**
 * Setup forgot password form handler
 */
function setupForgotForm() {
    const form = document.getElementById('forgotForm');
    const emailInput = document.getElementById('email');
    const formMessage = document.getElementById('formMessage');
    const submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Clear previous messages
        clearFormMessages();
        clearFieldErrors();

        // Validate email
        if (!emailInput.value.trim()) {
            showFieldError('emailError', 'Email is required');
            return;
        }

        if (!isValidEmail(emailInput.value)) {
            showFieldError('emailError', 'Please enter a valid email');
            return;
        }

        // Set loading state
        setLoadingState(submitBtn, true);

        try {
            const response = await fetch('/forgot-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: emailInput.value.trim()
                })
            });

            const data = await response.json();

            if (response.ok) {
                showFormMessage(formMessage, data.message, 'success');
                emailInput.value = '';
            } else {
                showFormMessage(formMessage, data.message, 'error');
            }
        } catch (error) {
            showFormMessage(formMessage, 'An error occurred. Please try again.', 'error');
            console.error('Forgot password error:', error);
        } finally {
            setLoadingState(submitBtn, false);
        }
    });
}

/**
 * Validate signup form inputs
 * @param {HTMLElement} emailInput 
 * @param {HTMLElement} passwordInput 
 * @param {HTMLElement} confirmPasswordInput 
 * @returns {boolean}
 */
function validateSignupForm(emailInput, passwordInput, confirmPasswordInput) {
    let isValid = true;

    if (!emailInput.value.trim()) {
        showFieldError('emailError', 'Email is required');
        isValid = false;
    } else if (!isValidEmail(emailInput.value)) {
        showFieldError('emailError', 'Please enter a valid email');
        isValid = false;
    }

    if (!passwordInput.value.trim()) {
        showFieldError('passwordError', 'Password is required');
        isValid = false;
    } else if (passwordInput.value.length < 6) {
        showFieldError('passwordError', 'Password must be at least 6 characters');
        isValid = false;
    }

    if (!confirmPasswordInput.value.trim()) {
        showFieldError('confirmPasswordError', 'Please confirm your password');
        isValid = false;
    } else if (passwordInput.value !== confirmPasswordInput.value) {
        showFieldError('confirmPasswordError', 'Passwords do not match');
        isValid = false;
    }

    return isValid;
}

/**
 * Validate email format
 * @param {string} email 
 * @returns {boolean}
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Show field error message
 * @param {string} fieldId 
 * @param {string} message 
 */
function showFieldError(fieldId, message) {
    const errorElement = document.getElementById(fieldId);
    if (errorElement) {
        errorElement.textContent = message;
    }
}

/**
 * Clear all field error messages
 */
function clearFieldErrors() {
    const errorMessages = document.querySelectorAll('.error-message');
    errorMessages.forEach(element => {
        element.textContent = '';
    });
}

/**
 * Show form message (success or error)
 * @param {HTMLElement} element 
 * @param {string} message 
 * @param {string} type - 'success' or 'error'
 */
function showFormMessage(element, message, type) {
    if (element) {
        element.textContent = message;
        element.className = `form-message ${type}`;
        element.style.display = 'block';
    }
}

/**
 * Clear all form messages
 */
function clearFormMessages() {
    const formMessages = document.querySelectorAll('.form-message');
    formMessages.forEach(element => {
        element.textContent = '';
        element.style.display = 'none';
    });
}

/**
 * Set loading state for submit button
 * @param {HTMLElement} button 
 * @param {boolean} isLoading 
 */
function setLoadingState(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.querySelector('.btn-text').style.display = 'none';
        button.querySelector('.btn-loader').style.display = 'inline-block';
    } else {
        button.disabled = false;
        button.querySelector('.btn-text').style.display = 'inline';
        button.querySelector('.btn-loader').style.display = 'none';
    }
}
