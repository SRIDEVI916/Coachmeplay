// Use API_URL from auth.js (already defined)


// Load notifications when page loads
document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (token) {
        loadNotificationCount();
        setupNotificationDropdown();
    }
});

// Load unread notification count
async function loadNotificationCount() {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch(`${API_URL}/notifications/unread-count`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const badge = document.getElementById('notificationBadge');
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading notification count:', error);
    }
}

// Setup notification dropdown
function setupNotificationDropdown() {
    const bell = document.getElementById('notificationBell');
    const dropdown = document.getElementById('notificationDropdown');
    
    if (bell && dropdown) {
        bell.addEventListener('click', async function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
            
            if (dropdown.classList.contains('show')) {
                await loadNotifications();
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function() {
            dropdown.classList.remove('show');
        });
    }
}

// Load all notifications
async function loadNotifications() {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch(`${API_URL}/notifications/`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayNotifications(data.notifications);
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

// Display notifications in dropdown
function displayNotifications(notifications) {
    const container = document.getElementById('notificationList');
    
    if (notifications.length === 0) {
        container.innerHTML = '<div class="notification-item empty">No notifications</div>';
        return;
    }
    
    container.innerHTML = notifications.map(notif => `
        <div class="notification-item ${notif.is_read ? 'read' : 'unread'}" 
             onclick="markAsRead(${notif.notification_id})">
            <div class="notification-title">${notif.title}</div>
            <div class="notification-message">${notif.message}</div>
            <div class="notification-time">${formatTime(notif.created_at)}</div>
        </div>
    `).join('');
}

// Mark notification as read
async function markAsRead(notificationId) {
    const token = localStorage.getItem('token');
    
    try {
        await fetch(`${API_URL}/notifications/${notificationId}/read`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        loadNotificationCount();
        loadNotifications();
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

// Format timestamp
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes} min ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    return `${days} day${days > 1 ? 's' : ''} ago`;
}

// Mark all as read
async function markAllAsRead() {
    const token = localStorage.getItem('token');
    
    try {
        await fetch(`${API_URL}/notifications/mark-all-read`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        loadNotificationCount();
        loadNotifications();
    } catch (error) {
        console.error('Error marking all as read:', error);
    }
}
