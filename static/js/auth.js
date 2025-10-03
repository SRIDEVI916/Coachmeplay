const API_URL = 'http://localhost:5000/api';

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth.js loaded successfully!');
    
    // Login functionality
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        console.log('Login form found');
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Login form submitted');
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch(`${API_URL}/auth/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                console.log('Login response:', data);
                
                if (response.ok) {
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user_type', data.user_type);
                    localStorage.setItem('user_id', data.user_id);
                    localStorage.setItem('full_name', data.full_name);
                    
                    if (data.user_type === 'athlete') {
                        window.location.href = '/athlete/dashboard';
                    } else {
                        window.location.href = '/coach/dashboard';
                    }
                } else {
                    showAlert(data.error, 'error');
                }
            } catch (error) {
                console.error('Login error:', error);
                showAlert('Login failed. Please try again.', 'error');
            }
        });
    }

    // Registration functionality
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        console.log('Register form found');
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Register form submitted');
            
            const formData = {
                email: document.getElementById('email').value,
                password: document.getElementById('password').value,
                user_type: document.getElementById('user_type').value,
                full_name: document.getElementById('full_name').value,
                phone_number: document.getElementById('phone_number').value,
                date_of_birth: document.getElementById('date_of_birth').value
            };
            
            console.log('Form data:', formData);
            
            const confirmPassword = document.getElementById('confirm_password').value;
            if (formData.password !== confirmPassword) {
                showAlert('Passwords do not match', 'error');
                return;
            }
            
            if (!formData.user_type) {
                showAlert('Please select if you are an Athlete or Coach', 'error');
                return;
            }
            
            try {
                console.log('Sending registration request...');
                const response = await fetch(`${API_URL}/auth/register`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                console.log('Registration response:', data);
                
                if (response.ok) {
                    showAlert('Registration successful! Redirecting to login...', 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else {
                    showAlert(data.error || 'Registration failed', 'error');
                }
            } catch (error) {
                console.error('Registration error:', error);
                showAlert('Registration failed. Please try again.', 'error');
            }
        });
    }
    
});

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_type');
    localStorage.removeItem('user_id');
    localStorage.removeItem('full_name');
    window.location.href = '/login';
}

function showAlert(message, type) {
    const alertDiv = document.getElementById('alert');
    if (alertDiv) {
        alertDiv.className = type === 'error' ? 'alert alert-error' : 'alert alert-success';
        alertDiv.textContent = message;
        alertDiv.style.display = 'block';
        
        setTimeout(() => {
            alertDiv.style.display = 'none';
        }, 5000);
    }
}

function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
    }
    return token;
}

function getAuthHeader() {
    const token = localStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

