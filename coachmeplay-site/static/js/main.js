// static/js/main.js
// Global Variables
let currentUser = null;
let cartItems = [];
let currentRating = 0;

// DOM Content Loaded Event
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    loadUserData();
    setupEventListeners();
});

// Initialize Application
function initializeApp() {
    console.log('CoachMePlay Application Initialized');
    // In a Flask app, user data comes from the session, not localStorage for sensitive info.
    // We'll rely on Flask templates to pass user data or check login status.
    // Simulate loading cart items if needed for client-side features.
    const cartData = localStorage.getItem('coachMePlayCart');
    if (cartData) {
        try {
            cartItems = JSON.parse(cartData);
            updateCartUI();
        } catch (e) {
            console.error("Error parsing cart data from localStorage:", e);
            cartItems = []; // Reset on error
        }
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Smooth scrolling for anchor links (if any)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// --- Placeholder functions for Venue Dashboard Actions ---
window.CoachMePlay = {
    // --- Existing or Simulated Functions ---
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Auto remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    },

    setRating: function(rating) {
        currentRating = rating;
        const stars = document.querySelectorAll('.rating-star');
        stars.forEach((star, index) => {
            if (index < rating) {
                star.style.color = '#FFD700';
                star.classList.add('active');
            } else {
                star.style.color = '#ddd';
                star.classList.remove('active');
            }
        });
    },

    bookCoach: function(coachName) {
        this.showNotification(`Session booked with ${coachName}!`, 'success');
        // Simulate redirect
        setTimeout(() => {
            window.location.href = 'athlete-dashboard.html?section=bookings';
        }, 2000);
    },

    // --- NEW Functions for Dashboard Interactions ---
    viewBookingDetails: function(identifier) {
        this.showNotification(`Viewing details for: ${identifier} (Simulated)`, 'info');
        console.log(`View Booking Details requested for: ${identifier}`);
        // In a full app, this might open a modal or navigate to a details page
    },

    sendBookingMessage: function(identifier) {
        this.showNotification(`Sending message for: ${identifier} (Simulated)`, 'info');
        console.log(`Send Message requested for: ${identifier}`);
        // In a full app, this would open a message form/modal
    },

    confirmBooking: function(identifier) {
        this.showNotification(`Booking confirmed: ${identifier}`, 'success');
        console.log(`Confirm Booking requested for: ${identifier}`);
        // In a full app, update UI and backend
    },

    cancelBooking: function(identifier) {
        if (confirm(`Are you sure you want to cancel '${identifier}'?`)) {
            this.showNotification(`Booking cancelled: ${identifier}`, 'warning');
            console.log(`Cancel Booking requested for: ${identifier}`);
            // In a full app, update UI and backend
        }
    },

    viewAthletePlan: function(athleteName) {
        this.showNotification(`Viewing plan for athlete: ${athleteName} (Simulated)`, 'info');
        console.log(`View Plan requested for: ${athleteName}`);
    },

    messageAthlete: function(athleteName) {
        this.showNotification(`Messaging athlete: ${athleteName} (Simulated)`, 'info');
        console.log(`Message Athlete requested for: ${athleteName}`);
    },

    // --- Marketplace & Cart Functions ---
    addToCart: function(productName, price, productId) {
        // Simple simulation using localStorage
        let cart = JSON.parse(localStorage.getItem('coachMePlayCart')) || [];
        const existingItemIndex = cart.findIndex(item => item.id == productId);

        if (existingItemIndex > -1) {
            cart[existingItemIndex].quantity += 1;
            this.showNotification(`Quantity increased for ${productName}.`, 'info');
        } else {
            const newItem = {
                id: productId || Date.now(), // Use provided ID or generate one
                name: productName,
                price: price || 0,
                quantity: 1
            };
            cart.push(newItem);
            this.showNotification(`${productName} added to cart!`, 'success');
        }
        localStorage.setItem('coachMePlayCart', JSON.stringify(cart));

        // Update UI cart count if elements exist
        this.updateCartCountUI();
    },

    removeFromCart: function(productId) {
        let cart = JSON.parse(localStorage.getItem('coachMePlayCart')) || [];
        cart = cart.filter(item => item.id != productId); // Use != to handle string/number comparison
        localStorage.setItem('coachMePlayCart', JSON.stringify(cart));
        this.showNotification('Item removed from cart.', 'info');

        // Update UI cart count
        this.updateCartCountUI();

        // If on the cart page, remove the item's DOM element
        const itemElement = document.querySelector(`.cart-item-card[data-product-id="${productId}"]`);
        if (itemElement) {
            itemElement.style.transition = 'opacity 0.3s';
            itemElement.style.opacity = '0';
            setTimeout(() => {
                itemElement.remove();
                // Re-calculate totals if order summary exists
                if (window.updateCartTotals) {
                    window.updateCartTotals(); // Call the function defined in cart.html
                } else {
                    console.warn('cart.html specific updateCartTotals function not found.');
                }
            }, 300);
        }
    },

    updateCartCountUI: function() {
        const cart = JSON.parse(localStorage.getItem('coachMePlayCart')) || [];
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);

        // Update elements with class 'cart-count'
        const cartCountElements = document.querySelectorAll('.cart-count');
        cartCountElements.forEach(el => {
            el.textContent = totalItems;
        });

        // Update specific cart link in navbar if it exists
        // Note: This requires the navbar link to have an ID or be identifiable
        // Example: <a href="{{ url_for('cart') }}" id="navbar-cart-link">🛒 Cart (<span class="cart-count">0</span>)</a>
        // const navbarCartLink = document.getElementById('navbar-cart-link');
        // if (navbarCartLink) {
        //     navbarCartLink.innerHTML = `🛒 Cart (<span class="cart-count">${totalItems}</span>)`;
        // }
    },

    quickFeedback: function(type) {
        const messages = {
            excellent: 'Thank you for the excellent feedback! We\'re thrilled you had a great experience!',
            good: 'Thanks for the positive feedback! We\'ll keep working to maintain this quality.',
            okay: 'Thank you for your feedback. We\'ll work on improving your experience.',
            poor: 'We\'re sorry to hear about your experience. We\'ll address these issues immediately.'
        };

        this.showNotification(messages[type] || 'Thank you for your feedback!', 'success');

        // Save feedback to localStorage
        const feedback = {
            type: type,
            date: new Date().toISOString(),
            userId: currentUser?.id
        };

        const allFeedback = JSON.parse(localStorage.getItem('coachMePlayFeedback')) || [];
        allFeedback.push(feedback);
        localStorage.setItem('coachMePlayFeedback', JSON.stringify(allFeedback));
    }
};

// Utility Functions (can be expanded)
function updateCartUI() {
    // Example: Update a cart icon count if it exists on the page
    const cartCountElements = document.querySelectorAll('.cart-count');
    const cartCount = cartItems.reduce((total, item) => total + item.quantity, 0);
    cartCountElements.forEach(el => {
        el.textContent = cartCount;
    });
}

function loadUserData() {
    // In this Flask setup, user data is managed server-side.
    // This function can be used for client-side features that need user context.
    // For example, checking if certain elements should be shown based on a global JS variable
    // set by the Flask template (e.g., <script>var jsUserRole = "{{ session.role }}";</script>)
    console.log("Loading user data (client-side simulation)...");
}

// Ensure global access
window.CoachMePlay = window.CoachMePlay || {};

document.addEventListener('DOMContentLoaded', function() {
    // Initialize cart count on page load
    if (window.CoachMePlay) {
        window.CoachMePlay.updateCartCountUI();
    }
});
