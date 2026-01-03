// Small client helper for API interactions
(function(){
    const BASE_API_URL = (typeof API_URL !== 'undefined') ? API_URL : 'http://localhost:5000/api';
    
    // Cache for feedback details
    const feedbackCache = new Map();
    // Debounce cache for functions
    const debounceTimers = new Map();

    // Debounce helper
    function debounce(func, wait = 300) {
        return function (...args) {
            const key = func.toString() + JSON.stringify(args);
            if (debounceTimers.has(key)) {
                clearTimeout(debounceTimers.get(key));
            }
            return new Promise((resolve) => {
                debounceTimers.set(key, setTimeout(async () => {
                    debounceTimers.delete(key);
                    resolve(await func.apply(this, args));
                }, wait));
            });
        };
    }

    async function getCurrentUser() {
        const token = localStorage.getItem('token');
        if (!token) throw new Error('No token');
        const res = await fetch(`${BASE_API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Not authenticated');
        const data = await res.json();
        return data.user;
    }

    function getAuthHeader() {
        const token = localStorage.getItem('token');
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }

    function getCoachIdFromUser(user) {
        return (user && (user.coach_id || user.coachId)) ? (user.coach_id || user.coachId) : (user ? user.user_id : null);
    }

    async function getFeedbackDetailRaw(feedbackId) {
        const res = await fetch(`${BASE_API_URL}/feedback/${feedbackId}`, {
            headers: getAuthHeader()
        });
        if (!res.ok) {
            throw new Error('Failed to load feedback details');
        }
        const data = await res.json();
        feedbackCache.set(feedbackId, {
            data,
            timestamp: Date.now()
        });
        return data;
    }

    // Cached and debounced version of getFeedbackDetail
    const getFeedbackDetail = debounce(async (feedbackId) => {
        // Check cache (valid for 5 minutes)
        const cached = feedbackCache.get(feedbackId);
        if (cached && (Date.now() - cached.timestamp < 5 * 60 * 1000)) {
            return cached.data;
        }
        return await getFeedbackDetailRaw(feedbackId);
    }, 300);

    // Helper to clear feedback cache (useful after updates)
    function clearFeedbackCache(feedbackId = null) {
        if (feedbackId === null) {
            feedbackCache.clear();
        } else {
            feedbackCache.delete(feedbackId);
        }
    }

    window.API_HELPER = {
        API_URL: BASE_API_URL,
        getCurrentUser,
        getAuthHeader,
        getCoachIdFromUser,
        getFeedbackDetail,
        clearFeedbackCache
    };
})();
