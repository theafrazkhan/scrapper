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
    } else if (tabName === 'schedules') {
        loadSchedules();
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
    console.log('deleteUser called:', userId, userEmail); // Debug log
    
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
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
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
            console.error('Delete user error:', error); // Debug log
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete user: ' + error.message,
                confirmButtonColor: '#ff6b35'
            });
        }
    }
}

// Make sure function is globally accessible
window.deleteUser = deleteUser;

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


// ============================================================================
// SCHEDULE MANAGEMENT
// ============================================================================

async function loadSchedules() {
    console.log('loadSchedules() called'); // Debug log
    const tbody = document.getElementById('schedulesTableBody');
    
    try {
        const response = await fetch('/api/admin/schedules');
        console.log('API response status:', response.status); // Debug log
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('API data:', data); // Debug log
        
        if (!data.success || data.schedules.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: var(--spacing-xl);">
                        <div class="empty-state">
                            <i class="fas fa-clock"></i>
                            <p>No schedules configured yet</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = data.schedules.map(s => {
            const nextRun = s.next_run ? new Date(s.next_run).toLocaleString() : 'N/A';
            const lastRun = s.last_run ? new Date(s.last_run).toLocaleString() : 'Never';
            const statusClass = s.is_enabled ? 'status-enabled' : 'status-disabled';
            const statusText = s.is_enabled ? 'Enabled' : 'Disabled';
            const toggleIcon = s.is_enabled ? 'fa-pause' : 'fa-play';
            const toggleTitle = s.is_enabled ? 'Disable' : 'Enable';
            
            return `
                <tr>
                    <td><strong>${s.name}</strong></td>
                    <td><span class="badge">${s.frequency}</span></td>
                    <td>${s.time_of_day}</td>
                    <td>${s.timezone}</td>
                    <td>${nextRun}</td>
                    <td>${lastRun}</td>
                    <td>
                        ${s.send_email ? '<i class="fas fa-check" style="color: var(--success);"></i>' : '<i class="fas fa-times" style="color: var(--gray-400);"></i>'}
                    </td>
                    <td><span class="badge ${statusClass}">${statusText}</span></td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-icon" onclick="toggleSchedule(${s.id})" title="${toggleTitle}">
                                <i class="fas ${toggleIcon}"></i>
                            </button>
                            <button class="btn-icon" onclick="editSchedule(${s.id})" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon" onclick="deleteSchedule(${s.id}, '${s.name}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Load schedules error:', error);
        const tbody = document.getElementById('schedulesTableBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: var(--spacing-xl);">
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle" style="color: var(--danger);"></i>
                        <p style="color: var(--danger);">Failed to load schedules</p>
                        <p style="font-size: 0.9em; color: var(--gray-600);">${error.message}</p>
                        <button onclick="loadSchedules()" class="btn-primary" style="margin-top: 10px;">
                            <i class="fas fa-sync"></i> Retry
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
}

async function addSchedule(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = {
        name: form.name.value,
        frequency: form.frequency.value,
        time_of_day: form.time_of_day.value,
        timezone: form.timezone.value,
        send_email: form.send_email.checked
    };
    
    try {
        const response = await fetch('/api/admin/schedules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Schedule Created',
                text: `Schedule "${formData.name}" has been created successfully`,
                confirmButtonColor: '#ff6b35'
            }).then(() => {
                form.reset();
                loadSchedules();
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to create schedule',
                confirmButtonColor: '#ff6b35'
            });
        }
    } catch (error) {
        console.error('Add schedule error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to create schedule: ' + error.message,
            confirmButtonColor: '#ff6b35'
        });
    }
}

async function toggleSchedule(scheduleId) {
    try {
        const response = await fetch(`/api/admin/schedules/${scheduleId}/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            Swal.fire({
                icon: 'success',
                title: data.message,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 2000
            });
            loadSchedules();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'Failed to toggle schedule',
                confirmButtonColor: '#ff6b35'
            });
        }
    } catch (error) {
        console.error('Toggle schedule error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to toggle schedule: ' + error.message,
            confirmButtonColor: '#ff6b35'
        });
    }
}

async function editSchedule(scheduleId) {
    // Get current schedule data
    const response = await fetch('/api/admin/schedules');
    const data = await response.json();
    const schedule = data.schedules.find(s => s.id === scheduleId);
    
    if (!schedule) return;
    
    const { value: formValues } = await Swal.fire({
        title: 'Edit Schedule',
        html: `
            <div style="text-align: left;">
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Name</label>
                    <input id="edit-name" class="swal2-input" value="${schedule.name}" style="width: 90%; margin: 0;">
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Frequency</label>
                    <select id="edit-frequency" class="swal2-input" style="width: 95%; margin: 0;">
                        <option value="daily" ${schedule.frequency === 'daily' ? 'selected' : ''}>Daily</option>
                        <option value="3-day" ${schedule.frequency === '3-day' ? 'selected' : ''}>Every 3 Days</option>
                        <option value="weekly" ${schedule.frequency === 'weekly' ? 'selected' : ''}>Weekly</option>
                        <option value="monthly" ${schedule.frequency === 'monthly' ? 'selected' : ''}>Monthly</option>
                    </select>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Time</label>
                    <input id="edit-time" type="time" class="swal2-input" value="${schedule.time_of_day}" style="width: 90%; margin: 0;">
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Timezone</label>
                    <select id="edit-timezone" class="swal2-input" style="width: 95%; margin: 0;">
                        <option value="UTC" ${schedule.timezone === 'UTC' ? 'selected' : ''}>UTC</option>
                        <option value="America/New_York" ${schedule.timezone === 'America/New_York' ? 'selected' : ''}>Eastern Time (ET)</option>
                        <option value="America/Chicago" ${schedule.timezone === 'America/Chicago' ? 'selected' : ''}>Central Time (CT)</option>
                        <option value="America/Denver" ${schedule.timezone === 'America/Denver' ? 'selected' : ''}>Mountain Time (MT)</option>
                        <option value="America/Los_Angeles" ${schedule.timezone === 'America/Los_Angeles' ? 'selected' : ''}>Pacific Time (PT)</option>
                        <option value="America/Toronto" ${schedule.timezone === 'America/Toronto' ? 'selected' : ''}>Toronto</option>
                        <option value="Europe/London" ${schedule.timezone === 'Europe/London' ? 'selected' : ''}>London</option>
                    </select>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center;">
                        <input id="edit-send-email" type="checkbox" ${schedule.send_email ? 'checked' : ''} style="margin-right: 8px;">
                        <span>Send email after scraping</span>
                    </label>
                </div>
            </div>
        `,
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonColor: '#ff6b35',
        confirmButtonText: 'Update',
        preConfirm: () => {
            return {
                name: document.getElementById('edit-name').value,
                frequency: document.getElementById('edit-frequency').value,
                time_of_day: document.getElementById('edit-time').value,
                timezone: document.getElementById('edit-timezone').value,
                send_email: document.getElementById('edit-send-email').checked
            };
        }
    });
    
    if (formValues) {
        try {
            const response = await fetch(`/api/admin/schedules/${scheduleId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formValues)
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Schedule Updated',
                    confirmButtonColor: '#ff6b35'
                }).then(() => {
                    loadSchedules();
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'Failed to update schedule',
                    confirmButtonColor: '#ff6b35'
                });
            }
        } catch (error) {
            console.error('Update schedule error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to update schedule: ' + error.message,
                confirmButtonColor: '#ff6b35'
            });
        }
    }
}

async function deleteSchedule(scheduleId, scheduleName) {
    console.log('deleteSchedule called:', scheduleId, scheduleName);
    
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: `Delete schedule "${scheduleName}"?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ff6b35',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete it!'
    });
    
    if (result.isConfirmed) {
        try {
            const response = await fetch(`/api/admin/schedules/${scheduleId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Deleted!',
                    text: 'Schedule has been deleted',
                    confirmButtonColor: '#ff6b35'
                }).then(() => {
                    loadSchedules();
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'Failed to delete schedule',
                    confirmButtonColor: '#ff6b35'
                });
            }
        } catch (error) {
            console.error('Delete schedule error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete schedule: ' + error.message,
                confirmButtonColor: '#ff6b35'
            });
        }
    }
}

// Make sure functions are globally accessible
window.addSchedule = addSchedule;
window.editSchedule = editSchedule;
window.deleteSchedule = deleteSchedule;
window.toggleSchedule = toggleSchedule;
window.loadSchedules = loadSchedules;

