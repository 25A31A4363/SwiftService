/**
 * Swift Service - Minimal, Centered, Light-Mode Authentication Entry Page
 * Strictly adheres to 3 application roles (Org Admin, Store Manager, Customer)
 * Centered authentication card, no promotional panel, no forgot password/recovery screen.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import { ROLE_PRESETS } from './rbac.js';
import { escapeHtml } from './ui-utils.js';

let activeAuthTab = 'signin'; // 'signin' | 'register'

export function renderAuthPage(container) {
  container.innerHTML = `
    <div class="auth-page-container">
      <div class="auth-page-body">
        <div class="auth-form-card">
          <!-- Centered Brand Header -->
          <div class="auth-card-brand">
            <div class="auth-brand-logo">
              <span class="auth-logo-icon">⚡</span>
            </div>
            <div class="auth-brand-text">
              <span class="auth-title">Swift Service</span>
              <span class="auth-tagline">Retail Feedback Intelligence Platform</span>
            </div>
          </div>

          <!-- Auth Mode Tab Switcher -->
          <div class="auth-tab-group" role="tablist">
            <button class="auth-tab-btn ${activeAuthTab === 'signin' ? 'active' : ''}" id="tab-btn-signin" role="tab" aria-selected="${activeAuthTab === 'signin'}">
              Sign In
            </button>
            <button class="auth-tab-btn ${activeAuthTab === 'register' ? 'active' : ''}" id="tab-btn-register" role="tab" aria-selected="${activeAuthTab === 'register'}">
              Create Account
            </button>
          </div>

          <div id="auth-tab-content" class="auth-tab-content">
            <!-- Rendered by tab switcher -->
          </div>
        </div>
      </div>
    </div>
  `;

  attachAuthEvents(container);
  renderActiveTabContent(container);
}

function renderActiveTabContent(container) {
  const contentEl = container.querySelector('#auth-tab-content');
  if (!contentEl) return;

  if (activeAuthTab === 'signin') {
    contentEl.innerHTML = `
      <div class="auth-form-header">
        <h2>Welcome back</h2>
        <p>Sign in to your Swift Service portal.</p>
      </div>

      <form id="form-swift-signin" class="auth-form" novalidate>
        <div class="form-group">
          <label class="form-label" for="signin-email">Email Address</label>
          <input 
            type="email" 
            id="signin-email" 
            class="form-input" 
            placeholder="name@example.com" 
            required 
            autocomplete="email" 
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="signin-password">Password</label>
          <div class="auth-password-wrapper">
            <input 
              type="password" 
              id="signin-password" 
              class="form-input" 
              placeholder="••••••••" 
              required 
              autocomplete="current-password" 
            />
            <button type="button" id="btn-toggle-signin-pwd" class="auth-pwd-toggle" title="Show or hide password" aria-label="Toggle password visibility">👁️</button>
          </div>
        </div>

        <div class="auth-options-row">
          <label class="auth-checkbox-label">
            <input type="checkbox" id="chk-remember-session" checked />
            <span>Remember session on this device</span>
          </label>
        </div>

        <div id="signin-error-box" class="auth-error-box" style="display: none;"></div>

        <button type="submit" id="btn-submit-signin" class="btn btn-primary auth-btn-submit">
          Sign In
        </button>

        <div class="auth-switch-prompt">
          <span>Don't have an account yet?</span>
          <button type="button" id="btn-prompt-to-register" class="auth-link-btn">Create an Account</button>
        </div>
      </form>

      <!-- Clean 3-Role Evaluation Sandbox (No personal names) -->
      <div class="auth-sandbox-enclave">
        <div class="auth-sandbox-label">
          <span>⚡ One-Click Evaluation</span>
          <span class="auth-sandbox-hint">Select a role to test:</span>
        </div>
        <div class="auth-persona-chips">
          ${ROLE_PRESETS.map(p => `
            <button type="button" class="auth-persona-chip" data-email="${p.email}" title="${p.desc}">
              <span class="auth-persona-chip-title">${p.title}</span>
              <span class="auth-persona-chip-role">${p.desc}</span>
            </button>
          `).join('')}
        </div>
      </div>
    `;

    attachSignInEvents(container);
  } else {
    contentEl.innerHTML = `
      <div class="auth-form-header">
        <h2>Create Account</h2>
        <p>Register as a customer to submit feedback and track resolutions.</p>
      </div>

      <form id="form-swift-register" class="auth-form" novalidate>
        <div class="form-group">
          <label class="form-label" for="reg-fullname">Full Name</label>
          <input type="text" id="reg-fullname" class="form-input" placeholder="e.g. Jane Doe" required autocomplete="name" />
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-email">Email Address</label>
          <input type="email" id="reg-email" class="form-input" placeholder="name@example.com" required autocomplete="email" />
          <span class="form-help-text">A 6-digit verification code will be sent to activate your account.</span>
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-phone">Phone Number (Optional)</label>
          <input type="tel" id="reg-phone" class="form-input" placeholder="+1-555-019-2834" autocomplete="tel" />
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-password">Password</label>
          <div class="auth-password-wrapper">
            <input type="password" id="reg-password" class="form-input" placeholder="Min. 8 characters" required autocomplete="new-password" />
            <button type="button" id="btn-toggle-reg-pwd" class="auth-pwd-toggle" title="Show or hide password" aria-label="Toggle password visibility">👁️</button>
          </div>
          <div class="pwd-strength-container" id="pwd-strength-container" style="display: none;">
            <div class="pwd-strength-bars">
              <div class="pwd-strength-segment" id="pwd-seg-1"></div>
              <div class="pwd-strength-segment" id="pwd-seg-2"></div>
              <div class="pwd-strength-segment" id="pwd-seg-3"></div>
              <div class="pwd-strength-segment" id="pwd-seg-4"></div>
            </div>
            <div class="pwd-strength-label" id="pwd-strength-label">Password strength: Weak</div>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-confirm-password">Confirm Password</label>
          <div class="auth-password-wrapper">
            <input type="password" id="reg-confirm-password" class="form-input" placeholder="Re-type password" required autocomplete="new-password" />
          </div>
          <div id="pwd-match-msg" style="display: none; font-size: 0.78rem; margin-top: 0.25rem;"></div>
        </div>

        <div id="register-error-box" class="auth-error-box" style="display: none;"></div>

        <button type="submit" id="btn-submit-register" class="btn btn-primary auth-btn-submit">
          Create Account & Verify
        </button>

        <div class="auth-switch-prompt">
          <span>Already have an account?</span>
          <button type="button" id="btn-prompt-to-signin" class="auth-link-btn">Sign In</button>
        </div>
      </form>
    `;

    attachRegisterEvents(container);
  }
}

function attachAuthEvents(container) {
  const btnSignInTab = container.querySelector('#tab-btn-signin');
  const btnRegTab = container.querySelector('#tab-btn-register');

  btnSignInTab?.addEventListener('click', () => {
    activeAuthTab = 'signin';
    btnSignInTab.classList.add('active');
    btnRegTab.classList.remove('active');
    renderActiveTabContent(container);
  });

  btnRegTab?.addEventListener('click', () => {
    activeAuthTab = 'register';
    btnRegTab.classList.add('active');
    btnSignInTab.classList.remove('active');
    renderActiveTabContent(container);
  });
}

function attachSignInEvents(container) {
  const btnTogglePwd = container.querySelector('#btn-toggle-signin-pwd');
  const pwdInput = container.querySelector('#signin-password');
  const emailInput = container.querySelector('#signin-email');
  const form = container.querySelector('#form-swift-signin');

  btnTogglePwd?.addEventListener('click', () => {
    if (!pwdInput) return;
    const isPwd = pwdInput.type === 'password';
    pwdInput.type = isPwd ? 'text' : 'password';
    btnTogglePwd.textContent = isPwd ? '🔒' : '👁️';
  });

  emailInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (!pwdInput.value) {
        pwdInput.focus();
      } else {
        form?.requestSubmit();
      }
    }
  });

  pwdInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      form?.requestSubmit();
    }
  });

  // Demo Persona Quick-Fill Chips (Clean, role-based)
  container.querySelectorAll('.auth-persona-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const email = chip.getAttribute('data-email');
      if (emailInput && pwdInput) {
        emailInput.value = email;
        pwdInput.value = 'Password123!';
        
        container.querySelectorAll('.auth-persona-chip').forEach(c => c.classList.remove('selected'));
        chip.classList.add('selected');
        
        showToast(`Selected ${chip.querySelector('.auth-persona-chip-title')?.textContent}`, 'info');
        container.querySelector('#btn-submit-signin')?.focus();
      }
    });
  });

  // Switch to Register Prompt
  container.querySelector('#btn-prompt-to-register')?.addEventListener('click', () => {
    activeAuthTab = 'register';
    container.querySelector('#tab-btn-signin')?.classList.remove('active');
    container.querySelector('#tab-btn-register')?.classList.add('active');
    renderActiveTabContent(container);
  });

  // Sign In Form Submit
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = container.querySelector('#btn-submit-signin');
    const errBox = container.querySelector('#signin-error-box');
    const email = emailInput?.value.trim();
    const password = pwdInput?.value;

    if (!email) {
      errBox.style.display = 'block';
      errBox.textContent = 'Please enter your email address.';
      emailInput?.focus();
      return;
    }

    if (!password) {
      errBox.style.display = 'block';
      errBox.textContent = 'Please enter your password.';
      pwdInput?.focus();
      return;
    }

    btnSubmit.disabled = true;
    btnSubmit.innerHTML = 'Signing in...';
    errBox.style.display = 'none';

    try {
      const res = await api.login(email, password);
      if (res.user.role === 'CUSTOMER') {
        state.setPortalMode('CUSTOMER');
      } else {
        state.setPortalMode('OPS');
      }
      state.setAuth(res.token, res.user);
      showToast(`Welcome back, ${res.user.fullName}!`, 'success');
      state.notify();
    } catch (err) {
      console.error('Sign In Error:', err);
      errBox.style.display = 'block';

      if (err.message && err.message.includes('EMAIL_UNVERIFIED')) {
        errBox.innerHTML = `
          <div style="font-weight: 700; margin-bottom: 0.35rem;">⚠️ Account Verification Pending</div>
          <div style="font-size: 0.82rem; margin-bottom: 0.65rem;">Please complete email verification to activate your account.</div>
          <button type="button" class="btn btn-secondary btn-sm" id="btn-unverified-verify-now" style="width: 100%; justify-content: center; font-size: 0.8rem;">
            ⚡ Enter Verification Code for ${escapeHtml(email)}
          </button>
        `;
        errBox.querySelector('#btn-unverified-verify-now')?.addEventListener('click', () => {
          openOtpVerificationModal(email, null, null);
        });
      } else {
        errBox.textContent = 'Authentication Failed: ' + (err.message || 'Invalid email or password');
      }

      btnSubmit.disabled = false;
      btnSubmit.innerHTML = 'Sign In';
    }
  });
}

function attachRegisterEvents(container) {
  const pwdInput = container.querySelector('#reg-password');
  const confirmInput = container.querySelector('#reg-confirm-password');
  const strengthContainer = container.querySelector('#pwd-strength-container');
  const strengthLabel = container.querySelector('#pwd-strength-label');
  const matchMsg = container.querySelector('#pwd-match-msg');

  // Password Visibility Toggle
  container.querySelector('#btn-toggle-reg-pwd')?.addEventListener('click', () => {
    if (!pwdInput) return;
    const isPwd = pwdInput.type === 'password';
    pwdInput.type = isPwd ? 'text' : 'password';
    container.querySelector('#btn-toggle-reg-pwd').textContent = isPwd ? '🔒' : '👁️';
  });

  // Switch to Sign In Prompt
  container.querySelector('#btn-prompt-to-signin')?.addEventListener('click', () => {
    activeAuthTab = 'signin';
    container.querySelector('#tab-btn-register')?.classList.remove('active');
    container.querySelector('#tab-btn-signin')?.classList.add('active');
    renderActiveTabContent(container);
  });

  // Live Password Strength Meter
  pwdInput?.addEventListener('input', () => {
    const val = pwdInput.value;
    if (!val) {
      strengthContainer.style.display = 'none';
      return;
    }
    strengthContainer.style.display = 'block';

    let score = 0;
    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;

    for (let i = 1; i <= 4; i++) {
      const seg = container.querySelector(`#pwd-seg-${i}`);
      seg.className = 'pwd-strength-segment';
      if (i <= score) {
        if (score <= 1) seg.classList.add('weak');
        else if (score <= 3) seg.classList.add('medium');
        else seg.classList.add('strong');
      }
    }

    const labels = ['Too Weak', 'Weak', 'Good', 'Strong'];
    strengthLabel.textContent = `Password strength: ${labels[score - 1] || 'Too Weak'}`;
  });

  // Live Confirm Password Matcher
  confirmInput?.addEventListener('input', () => {
    if (!confirmInput.value) {
      matchMsg.style.display = 'none';
      return;
    }
    matchMsg.style.display = 'block';
    if (confirmInput.value === pwdInput.value) {
      matchMsg.style.color = '#16a34a';
      matchMsg.textContent = '✓ Passwords match';
    } else {
      matchMsg.style.color = '#dc2626';
      matchMsg.textContent = '✗ Passwords do not match';
    }
  });

  // Register Form Submit
  const form = container.querySelector('#form-swift-register');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = container.querySelector('#btn-submit-register');
    const errBox = container.querySelector('#register-error-box');

    const fullName = container.querySelector('#reg-fullname').value.trim();
    const email = container.querySelector('#reg-email').value.trim();
    const phone = container.querySelector('#reg-phone').value.trim();
    const password = pwdInput.value;
    const confirmPassword = confirmInput.value;

    if (!fullName) {
      errBox.style.display = 'block';
      errBox.textContent = 'Please enter your full name.';
      container.querySelector('#reg-fullname').focus();
      return;
    }

    if (!email) {
      errBox.style.display = 'block';
      errBox.textContent = 'Please enter your email address.';
      container.querySelector('#reg-email').focus();
      return;
    }

    if (password !== confirmPassword) {
      errBox.style.display = 'block';
      errBox.textContent = 'Validation Error: Passwords do not match.';
      return;
    }

    if (password.length < 8) {
      errBox.style.display = 'block';
      errBox.textContent = 'Validation Error: Password must be at least 8 characters long.';
      return;
    }

    btnSubmit.disabled = true;
    btnSubmit.innerHTML = 'Creating Account...';
    errBox.style.display = 'none';

    try {
      const res = await api.registerCustomer({ fullName, email, password, phone });
      showToast('Account created! Please verify your email with the 6-digit code.', 'info');
      // Open OTP Verification Dialog
      openOtpVerificationModal(email, res.devOtpCode, res.emailDelivery);
    } catch (err) {
      console.error('Registration Error:', err);
      errBox.style.display = 'block';
      errBox.textContent = 'Registration Failed: ' + (err.message || 'Unable to register account');
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = 'Create Account & Verify';
    }
  });
}

function openOtpVerificationModal(email, devOtpCode, emailDelivery) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  const isSandbox = !emailDelivery || emailDelivery.provider === 'sandbox' || emailDelivery.status === 'SANDBOX';

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="otp-modal-backdrop">
      <div class="rw-modal" style="max-width: 460px; background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
        <div class="rw-modal-header" style="border-bottom: 1px solid #e2e8f0;">
          <div>
            <h2 style="font-size: 1.2rem; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0;">Verify Your Email</h2>
            <div style="font-size: 0.82rem; color: #64748b;">Enter the 6-digit code sent to ${escapeHtml(email)}</div>
          </div>
          <button class="rw-btn-close" id="btn-close-otp" style="color: #64748b;">✕</button>
        </div>

        <div class="rw-modal-body" style="padding: 1.5rem;">
          ${isSandbox ? `
            <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 0.85rem; margin-bottom: 1.25rem;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.35rem;">
                <span style="font-weight: 700; color: #0284c7; font-size: 0.85rem;">⚡ Verification Sandbox</span>
                <span style="font-size: 0.7rem; font-weight: 700; background: #e0f2fe; color: #0284c7; padding: 0.15rem 0.45rem; border-radius: 4px;">Code Ready</span>
              </div>
              <div style="font-size: 0.78rem; color: #475569; margin-bottom: 0.5rem;">
                Your cryptographic 6-digit verification code is:
              </div>
              <div style="display: flex; align-items: center; gap: 0.75rem;">
                <code style="font-size: 1.35rem; font-weight: 800; letter-spacing: 4px; color: #0f172a; background: #e2e8f0; padding: 0.25rem 0.65rem; border-radius: 4px;" id="sandbox-code-val">${devOtpCode || '123456'}</code>
                <button type="button" class="btn btn-secondary btn-sm" id="btn-autofill-otp" style="font-size: 0.75rem;">
                  ⚡ Auto-Fill Code
                </button>
              </div>
            </div>
          ` : `
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 0.75rem; margin-bottom: 1.25rem; font-size: 0.82rem; color: #16a34a;">
              ✓ Verification code sent via ${escapeHtml(emailDelivery?.provider || 'Email')}. Please check your inbox.
            </div>
          `}

          <form id="form-verify-otp">
            <div class="form-group" style="text-align: center; margin-bottom: 1.25rem;">
              <label class="form-label" for="input-otp-code" style="font-size: 0.85rem; margin-bottom: 0.5rem; display: block; color: #334155;">
                Enter 6-Digit Single-Use Code:
              </label>
              <input 
                type="text" 
                id="input-otp-code" 
                maxlength="6" 
                pattern="[0-9]{6}" 
                class="form-input" 
                style="font-size: 1.6rem; letter-spacing: 8px; text-align: center; width: 220px; margin: 0 auto; font-family: monospace; font-weight: 700; background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;" 
                placeholder="000000" 
                required 
                autocomplete="one-time-code" 
              />
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; font-size: 0.8rem; color: #64748b;">
              <span id="otp-timer">Code expires in 10:00</span>
              <button type="button" class="auth-link-btn" id="btn-resend-otp" style="color: #2563eb;">Resend Code</button>
            </div>

            <button type="submit" id="btn-submit-verify" class="btn btn-primary" style="width: 100%; justify-content: center; padding: 0.75rem;">
              Verify & Sign In Automatically
            </button>
          </form>
        </div>
      </div>
    </div>
  `;

  // Close Modal Handler
  const closeModal = () => {
    modalContainer.innerHTML = '';
  };
  modalContainer.querySelector('#btn-close-otp')?.addEventListener('click', closeModal);
  modalContainer.querySelector('#otp-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'otp-modal-backdrop') closeModal();
  });

  // Autofill button in sandbox
  modalContainer.querySelector('#btn-autofill-otp')?.addEventListener('click', () => {
    const code = modalContainer.querySelector('#sandbox-code-val')?.textContent || devOtpCode;
    const input = modalContainer.querySelector('#input-otp-code');
    if (input && code) {
      input.value = code.trim();
      showToast('Filled sandbox verification code', 'info');
    }
  });

  // Resend OTP
  modalContainer.querySelector('#btn-resend-otp')?.addEventListener('click', async () => {
    const btnResend = modalContainer.querySelector('#btn-resend-otp');
    btnResend.disabled = true;
    btnResend.textContent = 'Resending...';
    try {
      const res = await api.resendCustomerOtp({ email });
      showToast('Fresh verification code sent!', 'success');
      if (res.devOtpCode) {
        const codeEl = modalContainer.querySelector('#sandbox-code-val');
        if (codeEl) codeEl.textContent = res.devOtpCode;
      }
      btnResend.textContent = 'Code Sent';
    } catch (err) {
      showToast(err.message || 'Cooldown active. Please wait.', 'error');
      btnResend.disabled = false;
      btnResend.textContent = 'Resend Code';
    }
  });

  // Verify submit -> Establishes authenticated session and redirects directly to dashboard without second login!
  const form = modalContainer.querySelector('#form-verify-otp');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const otp = modalContainer.querySelector('#input-otp-code').value.trim();
    if (otp.length !== 6) {
      showToast('Please enter the full 6-digit code', 'error');
      return;
    }

    const btnSubmit = modalContainer.querySelector('#btn-submit-verify');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Verifying...';

    try {
      const res = await api.verifyCustomerOtp({ email, otp });
      // Establish session immediately
      state.setPortalMode('CUSTOMER');
      state.setAuth(res.token, res.user);
      showToast(`Welcome to Swift Service, ${res.user.fullName}!`, 'success');
      closeModal();
      state.notify();
    } catch (err) {
      console.error('OTP Verification error:', err);
      showToast(err.message || 'Invalid or expired verification code', 'error');
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Verify & Sign In Automatically';
    }
  });
}
