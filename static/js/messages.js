let currentUserId = null;
let currentOtherUserId = null;
let messageRefreshInterval = null;

// Get current user info
async function getCurrentUser() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return null;
    }

    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();
            currentUserId = data.user.user_id;
            return data.user;
        }
        return null;
    } catch (error) {
        console.error('Error fetching current user:', error);
        return null;
    }
}

// Load conversations
async function loadConversations() {
    try {
        const response = await fetch(`${API_URL}/messages/conversations?user_id=${currentUserId}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        if (response.ok) {
            const data = await response.json();
            displayConversations(data.conversations);
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

// Display conversations
function displayConversations(conversations) {
    const container = document.getElementById('conversationsList');
    
    if (conversations.length === 0) {
        container.innerHTML = '<p class="empty-message">No conversations yet</p>';
        return;
    }

    container.innerHTML = conversations.map(conv => `
        <div class="conversation-item ${conv.unread_count > 0 ? 'unread' : ''}" 
             onclick="openChat(${conv.other_user_id}, '${conv.full_name}', '${conv.profile_picture || '/static/images/default-avatar.png'}')">
            <img src="${conv.profile_picture || '/static/images/default-avatar.png'}" alt="${conv.full_name}">
            <div class="conversation-info">
                <div class="conversation-header">
                    <h4>${conv.full_name}</h4>
                    <span class="time">${formatTime(conv.last_message_time)}</span>
                </div>
                <div class="conversation-preview">
                    <p>${conv.last_message || 'No messages yet'}</p>
                    ${conv.unread_count > 0 ? `<span class="unread-badge">${conv.unread_count}</span>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// Open chat with user
async function openChat(userId, userName, userAvatar) {
    currentOtherUserId = userId;
    
    // Update header
    document.getElementById('chatHeader').style.display = 'flex';
    document.getElementById('chatUserName').textContent = userName;
    document.getElementById('chatUserAvatar').src = userAvatar;
    document.getElementById('chatInput').style.display = 'flex';
    
    // Load messages
    await loadMessages();
    
    // Start auto-refresh
    if (messageRefreshInterval) clearInterval(messageRefreshInterval);
    messageRefreshInterval = setInterval(loadMessages, 3000);
}

// Load messages
async function loadMessages() {
    try {
        const response = await fetch(`${API_URL}/messages/messages/${currentOtherUserId}?user_id=${currentUserId}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        if (response.ok) {
            const data = await response.json();
            displayMessages(data.messages);
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// Display messages
function displayMessages(messages) {
    const container = document.getElementById('chatMessages');
    
    if (messages.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No messages yet. Start the conversation!</p></div>';
        return;
    }

    container.innerHTML = messages.map(msg => `
        <div class="message ${msg.sender_id === currentUserId ? 'sent' : 'received'}">
            <div class="message-content">
                <p>${msg.message_text}</p>
                <span class="message-time">${formatTime(msg.sent_at)}</span>
            </div>
        </div>
    `).join('');
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// Send message
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const messageText = input.value.trim();
    
    if (!messageText || !currentOtherUserId) return;
    
    try {
        const response = await fetch(`${API_URL}/messages/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                sender_id: currentUserId,
                receiver_id: currentOtherUserId,
                message_text: messageText
            })
        });

        if (response.ok) {
            input.value = '';
            await loadMessages();
            await loadConversations();
        } else {
            alert('Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Failed to send message');
    }
}

// Format timestamp
function formatTime(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + ' mins ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + ' hours ago';
    
    return date.toLocaleDateString();
}

// Search conversations
document.getElementById('searchConversations').addEventListener('input', (e) => {
    const search = e.target.value.toLowerCase();
    const conversations = document.querySelectorAll('.conversation-item');
    
    conversations.forEach(conv => {
        const name = conv.querySelector('h4').textContent.toLowerCase();
        conv.style.display = name.includes(search) ? 'flex' : 'none';
    });
});

// Send message on button click
document.getElementById('sendMessageBtn').addEventListener('click', sendMessage);

// Send message on Enter (Shift+Enter for new line)
document.getElementById('messageInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Initialize
getCurrentUser().then(() => {
    loadConversations();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (messageRefreshInterval) clearInterval(messageRefreshInterval);
});

// Show new message modal
function showNewMessageModal() {
    document.getElementById('newMessageModal').style.display = 'flex';
    loadAvailableUsers();
}

// Close modal
function closeNewMessageModal() {
    document.getElementById('newMessageModal').style.display = 'none';
    document.getElementById('newMessageText').value = '';
}

// Load available users - UPDATED VERSION
async function loadAvailableUsers() {
    const token = localStorage.getItem('token');
    
    try {
        const userResponse = await fetch(`${API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (userResponse.ok) {
            const userData = await userResponse.json();
            const userType = userData.user.role;
            
            // Get coaches if athlete, athletes if coach
            let endpoint;
            if (userType === 'athlete') {
                endpoint = `${API_URL}/athlete/all-coaches`;
            } else {
                endpoint = `${API_URL}/coach/all-athletes`;
            }
            
            const response = await fetch(endpoint, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                const users = data.coaches || data.athletes || [];
                
                const select = document.getElementById('newMessageUser');
                select.innerHTML = '<option value="">Select a user...</option>' + 
                    users.map(u => `<option value="${u.user_id}">${u.full_name}</option>`).join('');
            } else {
                console.error('Failed to load users:', response.status);
                alert('Failed to load users. Please try again.');
            }
        }
    } catch (error) {
        console.error('Error loading available users:', error);
        alert('An error occurred while loading users. Please try again.');
    }
}

// Send new message
async function sendNewMessage() {
    const userId = document.getElementById('newMessageUser').value;
    const messageText = document.getElementById('newMessageText').value.trim();
    
    if (!userId || !messageText) {
        alert('Please select a user and type a message');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/messages/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                sender_id: currentUserId,
                receiver_id: userId,
                message_text: messageText
            })
        });

        if (response.ok) {
            closeNewMessageModal();
            await loadConversations();
            // Get user info and open chat
            const select = document.getElementById('newMessageUser');
            const userName = select.options[select.selectedIndex].text;
            openChat(userId, userName, '/static/images/default-avatar.png');
        } else {
            alert('Failed to send message');
        }
    } catch (error) {
        console.error('Error sending new message:', error);
        alert('Failed to send message. Please try again.');
    }
}
