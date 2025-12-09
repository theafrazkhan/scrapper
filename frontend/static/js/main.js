// Global State
let socket = null;
let scrapingStartTime = null;
let timerInterval = null;
let isLoggedIn = false;
let scrapingInProgress = false;
let currentUser = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Check if already logged in (from session/cookie)
    checkLoginStatus();
    
    // Set up event listeners
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Initialize Socket.IO connection
    initializeSocket();
    
    // Set up user menu after a short delay to ensure elements are loaded
    setTimeout(initializeUserMenu, 100);
}

// Initialize user menu dropdown
function initializeUserMenu() {
    const userMenuButton = document.getElementById('userMenuButton');
    const userDropdown = document.getElementById('userDropdown');
    const dropdownOverlay = document.getElementById('dropdownOverlay');
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (userMenuButton && userDropdown && dropdownOverlay) {
        // Toggle dropdown on button click
        userMenuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = userDropdown.classList.contains('active');
            
            if (isActive) {
                closeDropdown();
            } else {
                openDropdown();
            }
        });
        
        // Close dropdown when clicking overlay
        dropdownOverlay.addEventListener('click', () => {
            closeDropdown();
        });
        
        // Prevent dropdown from closing when clicking inside it
        userDropdown.addEventListener('click', (e) => {
            // Only allow links to navigate
            if (!e.target.closest('a') && !e.target.closest('.logout-btn')) {
                e.stopPropagation();
            }
        });
    }
    
    // User menu logout button
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            closeDropdown();
            logout();
        });
    }
}

function openDropdown() {
    const userMenuButton = document.getElementById('userMenuButton');
    const userDropdown = document.getElementById('userDropdown');
    const dropdownOverlay = document.getElementById('dropdownOverlay');
    
    userMenuButton.classList.add('active');
    userDropdown.classList.add('active');
    dropdownOverlay.classList.add('active');
}

function closeDropdown() {
    const userMenuButton = document.getElementById('userMenuButton');
    const userDropdown = document.getElementById('userDropdown');
    const dropdownOverlay = document.getElementById('dropdownOverlay');
    
    userMenuButton.classList.remove('active');
    userDropdown.classList.remove('active');
    dropdownOverlay.classList.remove('active');
}

// Toggle password visibility
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const toggleBtn = document.querySelector('.toggle-password i');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleBtn.classList.remove('fa-eye');
        toggleBtn.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        toggleBtn.classList.remove('fa-eye-slash');
        toggleBtn.classList.add('fa-eye');
    }
}

// Check login status
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.logged_in && data.user) {
            isLoggedIn = true;
            currentUser = data.user;
            showDashboard();
            updateUserMenu();
        }
    } catch (error) {
        console.error('Error checking login status:', error);
    }
}

// Handle login form submission
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('loginBtn');
    
    // Disable button and show loading
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Logging in...</span>';
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            isLoggedIn = true;
            currentUser = data.user; // Store user info
            showToast('Success', 'Login successful!', 'success');
            showDashboard();
            updateUserMenu();
        } else {
            showToast('Error', data.message || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Error', 'Failed to connect to server', 'error');
    } finally {
        loginBtn.disabled = false;
        loginBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i><span>Login & Start Scraping</span>';
    }
}

// Show dashboard after login
function showDashboard() {
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('dashboardSection').classList.remove('hidden');
    addLog('Ready to start scraping', 'success');
}

// Get status icon
function getStatusIcon(status) {
    const icons = {
        'completed': 'fa-check-circle',
        'failed': 'fa-times-circle',
        'running': 'fa-spinner fa-spin'
    };
    return icons[status] || 'fa-info-circle';
}

// Format date time
function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Update user menu with user info
function updateUserMenu() {
    const userMenuWrapper = document.getElementById('userMenuWrapper');
    const userEmailShort = document.getElementById('userEmailShort');
    const userEmail = document.getElementById('userEmail');
    const userRole = document.getElementById('userRole');
    const settingsLink = document.getElementById('settingsLink');
    
    if (currentUser) {
        // Get first name or first part of email
        const emailName = currentUser.email.split('@')[0];
        const shortName = emailName.length > 15 ? emailName.substring(0, 15) + '...' : emailName;
        
        userEmailShort.textContent = shortName;
        userEmail.textContent = currentUser.email;
        userRole.textContent = currentUser.role;
        
        // Add admin badge styling
        if (currentUser.role === 'admin') {
            userRole.classList.add('admin');
        }
        
        // Show menu wrapper
        userMenuWrapper.classList.remove('hidden');
        
        // Show settings link if user is admin
        if (currentUser.role === 'admin') {
            settingsLink.style.display = 'flex';
        }
    }
}

// Logout
async function logout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        isLoggedIn = false;
        scrapingInProgress = false;
        currentUser = null;
        
        document.getElementById('dashboardSection').classList.add('hidden');
        document.getElementById('loginSection').classList.remove('hidden');
        document.getElementById('userMenuWrapper').classList.add('hidden');
        
        // Reset form
        document.getElementById('loginForm').reset();
        
        // Reset stats
        resetStats();
        
        showToast('Success', 'Logged out successfully', 'success');
    } catch (error) {
        console.error('Logout error:', error);
        showToast('Error', 'Failed to logout', 'error');
    }
}

// Initialize Socket.IO connection
function initializeSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Socket connected');
        updateStatus('Ready', 'ready');
    });
    
    socket.on('disconnect', () => {
        console.log('Socket disconnected');
        updateStatus('Disconnected', 'disconnected');
    });
    
    socket.on('scraping_progress', (data) => {
        handleScrapingProgress(data);
    });
    
    socket.on('scraping_complete', (data) => {
        handleScrapingComplete(data);
    });
    
    socket.on('scraping_error', (data) => {
        handleScrapingError(data);
    });
    
    socket.on('scraping_stopped', (data) => {
        handleScrapingStopped(data);
    });
}

// Start scraping
async function startScraping() {
    if (!isLoggedIn) {
        showToast('Error', 'Please login first', 'error');
        return;
    }
    
    if (scrapingInProgress) {
        showToast('Warning', 'Scraping already in progress', 'warning');
        return;
    }
    
    scrapingInProgress = true;
    scrapingStartTime = Date.now();
    
    // UI Updates
    document.getElementById('startBtn').classList.add('hidden');
    document.getElementById('stopBtn').classList.remove('hidden');
    document.getElementById('downloadBtn').classList.add('hidden');
    updateStatus('Processing', 'processing');
    
    // Initialize progress bar with loading state
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    progressBar.classList.add('loading');
    progressBar.style.width = '100%';
    progressText.textContent = 'Starting...';
    
    // Start timer
    timerInterval = setInterval(updateTimer, 1000);
    
    addLog('Starting scraping process...', 'info');
    
    try {
        const response = await fetch('/api/start_scraping', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to start scraping');
        }
        
        addLog('Scraping started successfully', 'success');
    } catch (error) {
        console.error('Start scraping error:', error);
        showToast('Error', error.message, 'error');
        stopScraping();
    }
}

// Stop scraping
async function stopScraping() {
    try {
        const response = await fetch('/api/stop_scraping', { method: 'POST' });
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to stop scraping');
        }
        
        addLog('Stopping scraping...', 'warning');
        // The actual UI update will be handled by the WebSocket event
    } catch (error) {
        console.error('Stop scraping error:', error);
        // Still update UI even if API call failed
        scrapingInProgress = false;
        clearInterval(timerInterval);
        
        document.getElementById('stopBtn').classList.add('hidden');
        document.getElementById('startBtn').classList.remove('hidden');
        updateStatus('Ready', 'ready');
        
        showToast('Warning', 'Stop request sent but may have failed', 'warning');
    }
}

// Handle scraping progress updates
function handleScrapingProgress(data) {
    console.log('Progress update received:', data); // Debug logging
    
    // Update stats
    if (data.total_products !== undefined) {
        document.getElementById('totalProducts').textContent = data.total_products;
    }
    
    if (data.downloaded !== undefined) {
        document.getElementById('downloadedProducts').textContent = data.downloaded;
    }
    
    if (data.speed !== undefined) {
        document.getElementById('speed').textContent = data.speed.toFixed(2);
    }
    
    // Update progress bar
    if (data.progress !== undefined) {
        console.log('Updating progress bar to:', data.progress + '%'); // Debug logging
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        if (data.progress === 0 || data.progress < 1) {
            // Show loading/indeterminate animation when progress is 0%
            progressBar.classList.add('loading');
            progressBar.style.width = '100%';
            progressText.textContent = 'Initializing...';
        } else {
            // Show actual progress
            progressBar.classList.remove('loading');
            progressBar.style.width = data.progress + '%';
            progressText.textContent = Math.round(data.progress) + '%';
        }
    }
    
    // Add log message
    if (data.message) {
        addLog(data.message, data.type || 'info');
    }
}

// Handle scraping completion
function handleScrapingComplete(data) {
    scrapingInProgress = false;
    clearInterval(timerInterval);
    
    // UI Updates
    document.getElementById('stopBtn').classList.add('hidden');
    document.getElementById('startBtn').classList.remove('hidden');
    document.getElementById('downloadBtn').classList.remove('hidden');
    updateStatus('Complete', 'ready');
    
    // Update final stats
    document.getElementById('totalProducts').textContent = data.total_products || 0;
    document.getElementById('downloadedProducts').textContent = data.downloaded || 0;
    
    // Set progress to 100% and remove loading state
    const progressBar = document.getElementById('progressBar');
    progressBar.classList.remove('loading');
    progressBar.style.width = '100%';
    document.getElementById('progressText').textContent = '100%';
    
    addLog('Scraping completed successfully! ✓', 'success');
    showToast('Success', `Scraping complete! ${data.downloaded} products extracted.`, 'success');
    
    // Trigger confetti animation
    launchConfetti();
}

// Handle scraping errors
function handleScrapingError(data) {
    scrapingInProgress = false;
    clearInterval(timerInterval);
    
    document.getElementById('stopBtn').classList.add('hidden');
    document.getElementById('startBtn').classList.remove('hidden');
    updateStatus('Error', 'disconnected');
    
    // Remove loading state from progress bar
    document.getElementById('progressBar').classList.remove('loading');
    
    addLog('Error: ' + data.message, 'error');
    showToast('Error', data.message, 'error');
}

// Handle scraping stopped by user
function handleScrapingStopped(data) {
    scrapingInProgress = false;
    clearInterval(timerInterval);
    
    document.getElementById('stopBtn').classList.add('hidden');
    document.getElementById('startBtn').classList.remove('hidden');
    updateStatus('Stopped', 'ready');
    
    // Remove loading state from progress bar
    document.getElementById('progressBar').classList.remove('loading');
    
    addLog('⚠️ Scraping stopped by user', 'warning');
    showToast('Info', data.message || 'Scraping has been stopped', 'info');
}

// Download Excel file
async function downloadExcel() {
    try {
        addLog('Preparing Excel file for download...', 'info');
        
        const response = await fetch('/api/download_excel');
        
        if (!response.ok) {
            throw new Error('Failed to download Excel file');
        }
        
        // Get filename from headers
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'lululemon_products.xlsx';
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        addLog('Excel file downloaded successfully', 'success');
        showToast('Success', 'Excel file downloaded!', 'success');
    } catch (error) {
        console.error('Download error:', error);
        showToast('Error', 'Failed to download Excel file', 'error');
    }
}

// Update status indicator
function updateStatus(text, state) {
    const statusText = document.querySelector('.status-text');
    const statusDot = document.querySelector('.status-dot');
    
    statusText.textContent = text;
    
    statusDot.classList.remove('disconnected', 'processing');
    
    if (state === 'disconnected') {
        statusDot.classList.add('disconnected');
    } else if (state === 'processing') {
        statusDot.classList.add('processing');
    }
}

// Update elapsed timer
function updateTimer() {
    if (!scrapingStartTime) return;
    
    const elapsed = Math.floor((Date.now() - scrapingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    
    document.getElementById('elapsedTime').textContent = 
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// Add log entry
function addLog(message, type = 'info') {
    const logContainer = document.getElementById('activityLog');
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    
    const time = new Date().toLocaleTimeString();
    
    logEntry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-message ${type}">${message}</span>
    `;
    
    // Remove placeholder if exists
    const placeholder = logContainer.querySelector('.log-entry:first-child');
    if (placeholder && placeholder.textContent.includes('Waiting to start')) {
        logContainer.removeChild(placeholder);
    }
    
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Clear activity log
function clearLog() {
    const logContainer = document.getElementById('activityLog');
    logContainer.innerHTML = `
        <div class="log-entry">
            <span class="log-time">--:--:--</span>
            <span class="log-message">Log cleared</span>
        </div>
    `;
}

// Reset stats
function resetStats() {
    document.getElementById('totalProducts').textContent = '0';
    document.getElementById('downloadedProducts').textContent = '0';
    document.getElementById('elapsedTime').textContent = '00:00';
    document.getElementById('speed').textContent = '0';
    
    // Reset progress bar and remove loading state
    const progressBar = document.getElementById('progressBar');
    progressBar.classList.remove('loading');
    progressBar.style.width = '0%';
    document.getElementById('progressText').textContent = '0%';
    
    clearLog();
}

// Show toast notification
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${iconMap[type] || iconMap.info}"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="closeToast(this)">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            closeToast(toast.querySelector('.toast-close'));
        }
    }, 5000);
}

// Close toast
function closeToast(button) {
    const toast = button.closest('.toast');
    toast.style.animation = 'toastOut 0.3s ease-out';
    
    setTimeout(() => {
        if (toast.parentElement) {
            toast.parentElement.removeChild(toast);
        }
    }, 300);
}

// Confetti animation
function launchConfetti() {
    const duration = 3 * 1000;
    const animationEnd = Date.now() + duration;
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };

    function randomInRange(min, max) {
        return Math.random() * (max - min) + min;
    }

    const interval = setInterval(function() {
        const timeLeft = animationEnd - Date.now();

        if (timeLeft <= 0) {
            return clearInterval(interval);
        }

        const particleCount = 50 * (timeLeft / duration);
        
        // Create confetti particles manually
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.style.position = 'fixed';
            particle.style.width = '10px';
            particle.style.height = '10px';
            particle.style.backgroundColor = `hsl(${Math.random() * 360}, 100%, 50%)`;
            particle.style.left = Math.random() * window.innerWidth + 'px';
            particle.style.top = '-10px';
            particle.style.zIndex = '999';
            particle.style.borderRadius = '50%';
            particle.style.pointerEvents = 'none';
            
            document.body.appendChild(particle);
            
            const animation = particle.animate([
                { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
                { transform: `translateY(${window.innerHeight}px) rotate(${Math.random() * 720}deg)`, opacity: 0 }
            ], {
                duration: 2000 + Math.random() * 1000,
                easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
            });
            
            animation.onfinish = () => particle.remove();
        }
    }, 250);
}

// Add CSS for toast out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes toastOut {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);


// ============================================
// Forgot Password Functions
// ============================================

function openForgotPasswordModal() {
    const modal = document.getElementById('forgotPasswordModal');
    document.getElementById('resetStep1').classList.remove('hidden');
    document.getElementById('resetStep2').classList.add('hidden');
    document.getElementById('resetEmail').value = '';
    document.getElementById('resetToken').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    modal.classList.remove('hidden');
}

function closeForgotPasswordModal() {
    const modal = document.getElementById('forgotPasswordModal');
    modal.classList.add('hidden');
}

async function requestResetToken(event) {
    event.preventDefault();
    
    const email = document.getElementById('resetEmail').value;
    const submitBtn = event.target.querySelector('button[type="submit"]');
    
    // Disable button and show loading
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Sending...</span>';
    
    try {
        const response = await fetch('/api/forgot-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Check if OTP was actually sent (admin account) or just generic response
            if (data.email_masked) {
                // Admin account - OTP sent to email
                document.getElementById('resetStep1').classList.add('hidden');
                document.getElementById('resetStep2').classList.remove('hidden');
                document.getElementById('resetEmail').setAttribute('data-email', email);
                
                // Update success message to show email was sent
                const successAlert = document.querySelector('#resetStep2 .alert-success p');
                if (successAlert) {
                    successAlert.textContent = `A 6-digit OTP has been sent to ${data.email_masked}. Please check your email and enter it below.`;
                }
                
                showToast('OTP sent to your email! Check your inbox.', 'success');
            } else {
                // Generic response (non-admin or non-existent email)
                showToast(data.message, 'info');
                // Close modal after 3 seconds
                setTimeout(() => {
                    closeForgotPasswordModal();
                }, 3000);
            }
        } else {
            showToast(data.message || 'Failed to send OTP', 'error');
        }
    } catch (error) {
        console.error('Error requesting reset token:', error);
        showToast('Network error. Please try again.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> <span>Request Reset Token</span>';
    }
}

async function resetPassword(event) {
    event.preventDefault();
    
    const email = document.getElementById('resetEmail').getAttribute('data-email');
    const otp = document.getElementById('resetToken').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // Validate OTP format (6 digits)
    if (!/^\d{6}$/.test(otp)) {
        showToast('OTP must be exactly 6 digits', 'error');
        return;
    }
    
    // Validate passwords match
    if (newPassword !== confirmPassword) {
        showToast('Passwords do not match!', 'error');
        return;
    }
    
    // Validate password length
    if (newPassword.length < 6) {
        showToast('Password must be at least 6 characters long', 'error');
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Resetting...</span>';
    
    try {
        const response = await fetch('/api/reset-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                email,
                otp,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast('Password reset successfully! You can now login.', 'success');
            closeForgotPasswordModal();
            
            // Pre-fill email in login form
            document.getElementById('email').value = email;
        } else {
            showToast(data.message || 'Invalid or expired OTP', 'error');
        }
    } catch (error) {
        console.error('Error resetting password:', error);
        showToast('Network error. Please try again.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check"></i> <span>Reset Password</span>';
    }
}

function copyToken() {
    const token = document.getElementById('resetTokenDisplay').textContent;
    navigator.clipboard.writeText(token).then(() => {
        showToast('Token copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy token', 'error');
    });
}

function toggleNewPassword() {
    const passwordInput = document.getElementById('newPassword');
    const toggleBtn = passwordInput.nextElementSibling;
    const icon = toggleBtn.querySelector('i');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Add event listener for forgot password link
document.addEventListener('DOMContentLoaded', () => {
    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            openForgotPasswordModal();
        });
    }
});
