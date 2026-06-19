document.addEventListener('DOMContentLoaded', () => {
    // If already logged in via token, redirect to index
    if (localStorage.getItem('user_token')) {
        window.location.href = '/index.html';
        return;
    }

    let isLoginMode = true;

    const loginForm = document.getElementById('login-form');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const togglePwBtn = document.getElementById('toggle-pw');
    
    const formTitle = document.getElementById('form-title');
    const formSubtitle = document.getElementById('form-subtitle');
    const submitBtn = document.getElementById('submit-btn');
    const toggleModeBtn = document.getElementById('toggle-mode');
    const toggleText = document.getElementById('toggle-text');
    const forgotPw = document.getElementById('forgot-pw');
    
    const errorMsg = document.getElementById('error-msg');
    const successMsg = document.getElementById('success-msg');

    // Toggle password visibility
    togglePwBtn.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        
        // Update icon based on state (simplified stroke change)
        if (type === 'text') {
            togglePwBtn.style.color = '#8b5cf6';
        } else {
            togglePwBtn.style.color = '#94a3b8';
        }
    });

    // Toggle between Login and Register modes
    toggleModeBtn.addEventListener('click', () => {
        isLoginMode = !isLoginMode;
        errorMsg.style.display = 'none';
        successMsg.style.display = 'none';
        emailInput.value = '';
        passwordInput.value = '';

        if (isLoginMode) {
            formTitle.textContent = 'Welcome back';
            formSubtitle.textContent = 'Sign in to your account';
            submitBtn.textContent = 'Sign in';
            toggleText.textContent = 'No account?';
            toggleModeBtn.textContent = 'Create one';
            forgotPw.style.display = 'block';
        } else {
            formTitle.textContent = 'Create an account';
            formSubtitle.textContent = 'Join the movie network';
            submitBtn.textContent = 'Sign up';
            toggleText.textContent = 'Already have an account?';
            toggleModeBtn.textContent = 'Sign in';
            forgotPw.style.display = 'none';
        }
    });

    // Handle form submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) {
            errorMsg.textContent = 'Please fill in all fields.';
            errorMsg.style.display = 'block';
            return;
        }
        
        errorMsg.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.7';
        
        const endpoint = isLoginMode ? '/api/login' : '/api/register';
        
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Authentication failed');
            }
            
            if (isLoginMode) {
                // Success Login
                localStorage.setItem('user_token', data.token);
                localStorage.setItem('user_email', data.email);
                window.location.href = '/index.html';
            } else {
                // Success Registration
                successMsg.textContent = 'Account created! Switching to login...';
                successMsg.style.display = 'block';
                setTimeout(() => {
                    toggleModeBtn.click(); // Switch back to login mode
                    emailInput.value = email; // Keep email filled
                }, 1500);
            }
        } catch (err) {
            errorMsg.textContent = err.message;
            errorMsg.style.display = 'block';
            successMsg.style.display = 'none';
        } finally {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
        }
    });
});
