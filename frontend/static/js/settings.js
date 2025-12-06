// Settings Page JavaScript

// Tab switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
    
    // Load data based on tab
    if (tabName === 'email-config') {
        loadEmailConfig();
    } else if (tabName === 'lululemon-creds') {
        loadLululemonCredentials();
    }
}

// Modal functions
function openAddUserModal() {
    document.getElementById('add-user-modal').classList.add('active');
}

function openAddRecipientModal() {
    document.getElementById('add-recipient-modal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// User Management
async function addUser(event) {
    event.preventDefault();
    
    const email = document.getElementById('new-user-email').value;
    const password = document.getElementById('new-user-password').value;
    const role = document.getElementById('new-user-role').value;
    
    try {
        const response = await fetch('/api/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password, role })
        });
        
        const data = await response.json();
        
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Success!',
                text: 'User added successfully',
                confirmButtonColor: '#ff6b35'
            }).then(() => {
                location.reload();
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to add user',
                confirmButtonColor: '#ff6b35'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to add user',
            confirmButtonColor: '#ff6b35'
        });
    }
    
    closeModal('add-user-modal');
}

async function deleteUser(userId, userEmail) {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: `Delete user ${userEmail}?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ff6b35',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete it!'
    });
    
    if (result.isConfirmed) {
        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Deleted!',
                    text: 'User has been deleted',
                    confirmButtonColor: '#ff6b35'
                }).then(() => {
                    location.reload();
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'Failed to delete user',
                    confirmButtonColor: '#ff6b35'
                });
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete user',
                confirmButtonColor: '#ff6b35'
            });
        }
    }
}

// Email Recipient Management
async function addRecipient(event) {
    event.preventDefault();
    
    const email = document.getElementById('new-recipient-email').value;
    
    try {
        const response = await fetch('/api/admin/recipients', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Success!',
                text: 'Recipient added successfully',
                confirmButtonColor: '#ff6b35'
            }).then(() => {
                location.reload();
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to add recipient',
                confirmButtonColor: '#ff6b35'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to add recipient',
            confirmButtonColor: '#ff6b35'
        });
    }
    
    closeModal('add-recipient-modal');
}

async function toggleRecipient(recipientId, currentStatus) {
    try {
        const response = await fetch(`/api/admin/recipients/${recipientId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: !currentStatus })
        });
        
        const data = await response.json();
        
        if (data.success) {
            location.reload();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to toggle recipient',
                confirmButtonColor: '#ff6b35'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to toggle recipient',
            confirmButtonColor: '#ff6b35'
        });
    }
}

async function deleteRecipient(recipientId, recipientEmail) {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: `Delete recipient ${recipientEmail}?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ff6b35',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete it!'
    });
    
    if (result.isConfirmed) {
        try {
            const response = await fetch(`/api/admin/recipients/${recipientId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Deleted!',
                    text: 'Recipient has been deleted',
                    confirmButtonColor: '#ff6b35'
                }).then(() => {
                    location.reload();
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'Failed to delete recipient',
                    confirmButtonColor: '#ff6b35'
                });
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete recipient',
                confirmButtonColor: '#ff6b35'
            });
        }
    }
}

// Test Email
async function sendTestEmail() {
    const email = document.getElementById('test-email').value;
    
    if (!email) {
        Swal.fire({
            icon: 'warning',
            title: 'Email Required',
            text: 'Please enter an email address',
            confirmButtonColor: '#ff6b35'
        });
        return;
    }
    
    Swal.fire({
        title: 'Sending...',
        text: 'Please wait',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    try {
        const response = await fetch('/api/email/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Test Email Sent!',
                text: `Check ${email} for the test email`,
                confirmButtonColor: '#ff6b35'
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Failed',
                text: data.error || 'Failed to send test email',
                confirmButtonColor: '#ff6b35'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to send test email',
            confirmButtonColor: '#ff6b35'
        });
    }
}

// Load Email Configuration
async function loadEmailConfig() {
    try {
        const response = await fetch('/api/email/config');
        const data = await response.json();
        
        if (data.success) {
            const config = data.config;
            // Update display view
            document.getElementById('display-provider').textContent = config.provider || 'Resend';
            document.getElementById('display-api-key').textContent = '••••••••••••••••';
            document.getElementById('display-from-email').textContent = config.from_email || 'Not set';
            document.getElementById('display-from-name').textContent = config.from_name || 'Not set';
            document.getElementById('display-domain').textContent = config.domain || 'Not set';
        }
    } catch (error) {
        console.error('Failed to load email config:', error);
    }
}

// Open Edit Email Configuration Modal
async function openEditEmailConfigModal() {
    try {
        const response = await fetch('/api/admin/email-config');
        const data = await response.json();
        
        if (data.success) {
            const config = data.config;
            document.getElementById('email-api-key').value = config.api_key || '';
            document.getElementById('email-from-email').value = config.from_email || '';
            document.getElementById('email-from-name').value = config.from_name || '';
            document.getElementById('email-domain').value = config.domain || '';
        }
    } catch (error) {
        console.error('Failed to load email config:', error);
    }
    
    document.getElementById('edit-email-config-modal').classList.add('active');
}

// Update Email Configuration
async function updateEmailConfiguration(event) {
    event.preventDefault();
    
    const apiKey = document.getElementById('email-api-key').value;
    const fromEmail = document.getElementById('email-from-email').value;
    const fromName = document.getElementById('email-from-name').value;
    const domain = document.getElementById('email-domain').value;
    
    Swal.fire({
        title: 'Saving...',
        text: 'Updating email configuration',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    try {
        const response = await fetch('/api/admin/email-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key: apiKey,
                from_email: fromEmail,
                from_name: fromName,
                domain: domain
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Success!',
                text: 'Email configuration updated successfully',
                confirmButtonColor: '#ff6b35'
            });
            
            closeModal('edit-email-config-modal');
            loadEmailConfig();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to update email configuration',
                confirmButtonColor: '#ff6b35'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to update email configuration',
            confirmButtonColor: '#ff6b35'
        });
    }
}

// Toggle API Key Visibility
function toggleApiKeyVisibility() {
    const apiKeyInput = document.getElementById('email-api-key');
    const toggleIcon = document.getElementById('api-key-toggle-icon');
    
    if (apiKeyInput.type === 'password') {
        apiKeyInput.type = 'text';
        toggleIcon.classList.remove('fa-eye');
        toggleIcon.classList.add('fa-eye-slash');
    } else {
        apiKeyInput.type = 'password';
        toggleIcon.classList.remove('fa-eye-slash');
        toggleIcon.classList.add('fa-eye');
    }
}

// Legacy code - keeping for compatibility
async function loadEmailConfigLegacy() {
    try {
        const response = await fetch('/api/email/config');
        const data = await response.json();
        
        if (data.success) {
            const config = data.config;
            const statusElement = document.getElementById('config-status');
            statusElement.textContent = config.api_configured ? 'Configured' : 'Not Configured';
            statusElement.className = config.api_configured ? 'status-badge status-active' : 'status-badge status-inactive';
        }
    } catch (error) {
        console.error('Failed to load email config:', error);
    }
}

// ============================================================================
// LULULEMON CREDENTIALS MANAGEMENT
// ============================================================================

async function loadLululemonCredentials() {
    try {
        const response = await fetch('/api/admin/lululemon-credentials');
        const data = await response.json();
        
        if (data.success && data.credentials) {
            const creds = data.credentials;
            
            // Update display view
            document.getElementById('display-username').textContent = creds.username || 'Not set';
            document.getElementById('display-password').textContent = creds.password ? '••••••••' : 'Not set';
            
            // Store in modal form (hidden until opened)
            document.getElementById('lulu-username').value = creds.username || '';
            document.getElementById('lulu-password').value = creds.password || '';
        } else {
            document.getElementById('display-username').textContent = 'Not set';
            document.getElementById('display-password').textContent = 'Not set';
        }
    } catch (error) {
        console.error('Failed to load Lululemon credentials:', error);
        document.getElementById('display-username').textContent = 'Error loading';
        document.getElementById('display-password').textContent = 'Error loading';
    }
}

function openEditCredentialsModal() {
    // Reload credentials into form
    loadLululemonCredentials();
    // Open modal
    document.getElementById('edit-credentials-modal').classList.add('active');
}

async function updateLululemonCredentials(event) {
    event.preventDefault();
    
    const username = document.getElementById('lulu-username').value;
    const password = document.getElementById('lulu-password').value;
    
    if (!username || !password) {
        Swal.fire({
            icon: 'error',
            title: 'Missing Information',
            text: 'Please enter both username and password'
        });
        return;
    }
    
    // Show loading
    Swal.fire({
        title: 'Saving Credentials...',
        text: 'Please wait',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    try {
        const response = await fetch('/api/admin/lululemon-credentials', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Close modal
            closeModal('edit-credentials-modal');
            
            Swal.fire({
                icon: 'success',
                title: 'Success!',
                text: 'Credentials saved successfully',
                showConfirmButton: false,
                timer: 2000
            });
            
            // Reload credentials display
            loadLululemonCredentials();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Failed',
                text: data.error || 'Failed to save credentials'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to save credentials: ' + error.message
        });
    }
}

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('lulu-password');
    const icon = document.getElementById('password-toggle-icon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        passwordInput.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

// Logout
async function logout() {
    const response = await fetch('/api/logout', {method: 'POST'});
    if (response.ok) window.location.href = '/login';
}

// Load email config on page load
if (window.location.hash === '#email-config') {
    loadEmailConfig();
}

// Load Lululemon credentials on page load
if (window.location.hash === '#lululemon-creds') {
    loadLululemonCredentials();
}
