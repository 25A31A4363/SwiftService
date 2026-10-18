/**
 * Swift Service - Dedicated Authentication Entry Page
 * Provides secure Sign In and Create Account experiences before granting access to protected routes.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import { ROLE_PRESETS } from './rbac.js';
import { escapeHtml } from './ui-utils.js';

let activeAuthTab = 'signin'; // 'signin' | 'register'

export function renderAuthPage(container) {
  container.innerHTML = `
    <div class="auth-page-container">
      <!-- Top Brand Navigation Bar -->
      <header class="auth-page-header">
        <div class="auth-brand-group">
          <div class="auth-brand-logo">
            <span class="auth-logo-icon">⚡</span>
          </div>
          <div class="auth-brand-text">
            <span class="auth-title">Swift Service</span>
            <span class="auth-tagline">Retail Feedback Intelligence & Operations</span>
          </div>
        </div>
        <div class="auth-header-badges">
          <span class="auth-env-badge">🔒 Enterprise Secure</span>
        </div>
      </header>

      <!-- Main Split Hero & Auth Card Section -->
      <div class="auth-page-body">
        <!-- Left Product Value Section -->
        <div class="auth-hero-banner">
          <div class="auth-hero-badge">Voice-of-Store Intelligence</div>
          <h1 class="auth-hero-heading">
            AI-Powered Operational Clarity Across Your Entire Retail Fleet
          </h1>
          <p class="auth-hero-desc">
            Swift Service connects frontline customer feedback, store incident detection, and multi-facility operational triage into a single closed-loop resolution platform.
          </p>

          <!-- Live Retail Fleet Operational Showcase Card -->
          <div class="auth-retail-showcase-card">
            <div class="auth-showcase-header">
              <div class="auth-showcase-title">
                <span class="auth-live-dot"></span>
                <span>Store Fleet Operational Signal — Store #104</span>
              </div>
              <span class="auth-showcase-badge">LIVE MONITORING</span>
            </div>
            <div class="auth-showcase-body">
              <div class="auth-signal-row">
                <div class="auth-signal-icon">❄️</div>
                <div class="auth-signal-meta">
                  <div class="auth-signal-label">Refrigeration Failure Anomaly</div>
                  <div class="auth-signal-detail">Dairy Aisle Walk-in Cooler • Temperature drift +4.2°C</div>
                </div>
                <div class="auth-signal-priority p1-tag">P1 CRITICAL</div>
              </div>
              <div class="auth-signal-row">
                <div class="auth-signal-icon">🛒</div>
                <div class="auth-signal-meta">
                  <div class="auth-signal-label">Checkout POS Latency Spike</div>
                  <div class="auth-signal-detail">Lane 3 & 4 Terminal freezes • 12 customer reports</div>
                </div>
                <div class="auth-signal-priority p2-tag">P2 HIGH</div>
              </div>
              <div class="auth-showcase-kpis">
                <div class="auth-kpi-item">
                  <span class="auth-kpi-val">18 min</span>
                  <span class="auth-kpi-lbl">Avg SLA Resolution</span>
                </div>
                <div class="auth-kpi-item">
                  <span class="auth-kpi-val">99.4%</span>
                  <span class="auth-kpi-lbl">Verified Outcomes</span>
                </div>
                <div class="auth-kpi-item">
                  <span class="auth-kpi-val">42 Stores</span>
                  <span class="auth-kpi-lbl">PNW Fleet Active</span>
                </div>
              </div>
            </div>
          </div>

          <div class="auth-feature-list">
            <div class="auth-feature-item">
              <span class="auth-feature-icon">🛡️</span>
              <div>
                <strong>Customer Complaint Portal</strong>
                <p>Guided submission, evidence attachments, and real-time status tracking.</p>
              </div>
            </div>
            <div class="auth-feature-item">
              <span class="auth-feature-icon">🧠</span>
              <div>
                <strong>Automated Incident Clustering</strong>
                <p>Early anomaly detection across refrigeration, checkout lanes, and stock.</p>
              </div>
            </div>
            <div class="auth-feature-item">
              <span class="auth-feature-icon">⚡</span>
              <div>
                <strong>Intelligent Dispatch & SLAs</strong>
                <p>Root-cause prioritization, SLA countdowns, and verified outcomes.</p>
              </div>
            </div>
          </div>

          <div class="auth-testimonial-card">
            <div class="auth-stars">★★★★★</div>
            <p class="auth-quote">"Swift Service reduced refrigeration failure escalation times from 6 hours to 18 minutes across 42 store locations."</p>
            <div class="auth-author">— Regional Operations Director, PNW Supercenters</div>
          </div>
        </div>

        <!-- Right Authentication Box -->
        <div class="auth-form-card">
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

      <!-- Auth Page Footer -->
      <footer class="auth-page-footer">
        <div>© 2026 Swift Service Platform. Authoritative Retail Intelligence. All rights reserved.</div>
        <div class="auth-footer-links">
          <a href="#" id="link-privacy-policy">Privacy Notice</a>
          <span>•</span>
          <a href="#" id="link-terms-service">Terms of Service</a>
          <span>•</span>
          <a href="#" id="link-security-docs">Security & Compliance</a>
        </div>
      </footer>
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
        <h2>Welcome Back</h2>
        <p>Sign in to access your Swift Service portal.</p>
      </div>

      <form id="form-swift-signin" class="auth-form" novalidate>
        <div class="form-group">
          <label class="form-label" for="signin-email">Email Address</label>
          <input type="email" id="signin-email" class="form-input" placeholder="e.g. name@organization.com or customer@retailwave.com" required autocomplete="email" />
        </div>

        <div class="form-group">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <label class="form-label" for="signin-password" style="margin-bottom: 0;">Password</label>
            <a href="#" id="link-forgot-password" class="auth-link-text">Forgot Password?</a>
          </div>
          <div class="auth-password-wrapper">
            <input type="password" id="signin-password" class="form-input" placeholder="••••••••" required autocomplete="current-password" />
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
          Sign In to Swift Service
        </button>

        <div class="auth-switch-prompt">
          <span>Don't have an account yet?</span>
          <button type="button" id="btn-prompt-to-register" class="auth-link-btn">Create an Account</button>
        </div>
      </form>

      <!-- Quick Demo Persona Sandbox Selector (positioned conveniently below primary form) -->
      <div class="auth-sandbox-enclave">
        <div class="auth-sandbox-label">
          <span>⚡ One-Click Evaluation Personas</span>
          <span class="auth-sandbox-hint">Click any role to auto-fill & test:</span>
        </div>
        <div class="auth-persona-chips">
          ${ROLE_PRESETS.map(p => `
            <button type="button" class="auth-persona-chip" data-email="${p.email}" title="${p.desc}">
              <span class="auth-persona-chip-title">${p.title}</span>
              <span class="auth-persona-chip-role">${p.role.replace(/_/g, ' ')}</span>
            </button>
          `).join('')}
        </div>
      </div>
    `;

    attachSignInEvents(container);
  } else {
    contentEl.innerHTML = `
      <div class="auth-form-header">
        <h2>Create Swift Service Account</h2>
        <p>Register as a verified customer to submit complaints and track resolutions.</p>
      </div>

      <form id="form-swift-register" class="auth-form">
        <div class="form-group">
          <label class="form-label" for="reg-fullname">Full Name</label>
          <input type="text" id="reg-fullname" class="form-input" placeholder="e.g. Jane Doe" required />
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-email">Email Address</label>
          <input type="email" id="reg-email" class="form-input" placeholder="name@example.com" required autocomplete="email" />
          <span class="form-help-text">A single-use 6-digit cryptographic verification code will be sent to this email.</span>
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-phone">Phone Number (Optional)</label>
          <input type="tel" id="reg-phone" class="form-input" placeholder="+1-555-019-2834" />
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-password">Password</label>
          <div class="auth-password-wrapper">
            <input type="password" id="reg-password" class="form-input" placeholder="Min. 8 characters" required autocomplete="new-password" />
            <button type="button" id="btn-toggle-reg-pwd" class="auth-pwd-toggle" title="Show or hide password">👁️</button>
          </div>
          <!-- Real-Time Password Strength Meter -->
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
          <div id="pwd-match-msg" style="display: none; font-size: 0.75rem; margin-top: 0.25rem;"></div>
        </div>

        <div class="auth-options-row">
          <label class="auth-checkbox-label">
            <input type="checkbox" id="chk-terms-agree" required />
            <span>I agree to the <a href="#" class="auth-link-text">Terms of Service</a> and acknowledge the <a href="#" class="auth-link-text">Privacy Notice</a>.</span>
          </label>
        </div>

        <div id="register-error-box" class="auth-error-box" style="display: none;"></div>

        <button type="submit" id="btn-submit-register" class="btn btn-primary auth-btn-submit">
          Create Account & Verify Email
        </button>

        <div class="auth-switch-prompt">
          <span>Already have a verified account?</span>
          <button type="button" id="btn-prompt-to-signin" class="auth-link-btn">Sign In Instead</button>
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

  // Footer Modal Links
  container.querySelector('#link-privacy-policy')?.addEventListener('click', (e) => {
    e.preventDefault();
    openLegalModal('Privacy Notice', `
      <p>Swift Service respects your personal privacy. Customer complaints, contact numbers, and internal operational records are strictly compartmentalized using server-side role-based access control.</p>
      <p>We do not sell, license, or expose customer identifiers to unauthorized third-party trackers or ad networks.</p>
    `);
  });

  container.querySelector('#link-terms-service')?.addEventListener('click', (e) => {
    e.preventDefault();
    openLegalModal('Terms of Service', `
      <p>By accessing Swift Service, you agree to submit authentic, factual operational feedback and retail complaints. Abuse, spamming, or fraudulent reporting will result in account revocation.</p>
    `);
  });

  container.querySelector('#link-security-docs')?.addEventListener('click', (e) => {
    e.preventDefault();
    openLegalModal('Security & Governance', `
      <p>Swift Service employs single-use cryptographic email OTP codes (10-minute expiry, max 5 attempts), salted PBKDF2/Argon2 password hashing, HTTP-safe session tokens, and strict customer isolation rules.</p>
    `);
  });
}

function attachSignInEvents(container) {
  // Password Visibility Toggle
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

  // Enter Key Handler for seamless keyboard submission
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

  // Demo Persona Quick-Fill Chips
  container.querySelectorAll('.auth-persona-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const email = chip.getAttribute('data-email');
      if (emailInput && pwdInput) {
        emailInput.value = email;
        pwdInput.value = 'Password123!';
        
        container.querySelectorAll('.auth-persona-chip').forEach(c => c.classList.remove('selected'));
        chip.classList.add('selected');
        
        showToast(`Filled credentials for ${email}`, 'info');
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

  // Forgot Password Action
  container.querySelector('#link-forgot-password')?.addEventListener('click', (e) => {
    e.preventDefault();
    openLegalModal('Password Recovery', `
      <p>To reset your password, contact your Swift Service corporate administrator, or if you are a customer, enter your registered email during account verification to receive a secure reset link.</p>
      <div style="margin-top: 1rem; font-size: 0.85rem; color: var(--text-secondary);">
        Demo Accounts: Default credential for evaluation accounts is <code>Password123!</code>.
      </div>
    `);
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
    btnSubmit.innerHTML = 'Authenticating...';
    errBox.style.display = 'none';

    try {
      const res = await api.login(email, password);
      // Route based on role
      if (res.user.role === 'CUSTOMER') {
        state.setPortalMode('CUSTOMER');
      } else {
        state.setPortalMode('OPS');
      }
      state.setAuth(res.token, res.user);
      showToast(`Welcome to Swift Service, ${res.user.fullName}!`, 'success');
      state.notify();
    } catch (err) {
      console.error('Sign In Error:', err);
      errBox.style.display = 'block';

      if (err.message && err.message.includes('EMAIL_UNVERIFIED')) {
        errBox.innerHTML = `
          <div style="font-weight: 700; margin-bottom: 0.35rem;">⚠️ Account Verification Pending</div>
          <div style="font-size: 0.82rem; margin-bottom: 0.65rem;">Please complete email OTP verification to activate your account.</div>
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
      btnSubmit.innerHTML = 'Sign In to Swift Service';
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
      matchMsg.style.color = '#34d399';
      matchMsg.textContent = '✓ Passwords match';
    } else {
      matchMsg.style.color = '#f87171';
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
    btnSubmit.innerHTML = 'Creating Account & Dispatching OTP...';
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
      btnSubmit.innerHTML = 'Create Account & Verify Email';
    }
  });
}

function openOtpVerificationModal(email, devOtpCode, emailDelivery) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  const isSandbox = !emailDelivery || emailDelivery.provider === 'sandbox';

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="otp-modal-backdrop">
      <div class="rw-modal" style="max-width: 480px;">
        <div class="rw-modal-header">
          <div>
            <h2 style="font-size: 1.2rem; font-weight: 700; color: #fff;">Verify Your Email</h2>
            <div style="font-size: 0.82rem; color: var(--text-muted);">Enter the 6-digit code sent to ${escapeHtml(email)}</div>
          </div>
          <button class="rw-btn-close" id="btn-close-otp">✕</button>
        </div>

        <div class="rw-modal-body">
          ${isSandbox ? `
            <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 0.85rem; margin-bottom: 1.25rem;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.35rem;">
                <span style="font-weight: 700; color: #38bdf8; font-size: 0.85rem;">⚡ Developer Evaluation Sandbox</span>
                <span class="rw-badge rw-badge-blue" style="font-size: 0.7rem;">Code Ready</span>
              </div>
              <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
                SMTP credentials not configured. Your cryptographic 6-digit verification code is:
              </div>
              <div style="display: flex; align-items: center; gap: 0.75rem;">
                <code style="font-size: 1.25rem; font-weight: 800; letter-spacing: 4px; color: #fff; background: rgba(0,0,0,0.4); padding: 0.25rem 0.65rem; border-radius: 4px;" id="sandbox-code-val">${devOtpCode || '123456'}</code>
                <button type="button" class="btn btn-secondary btn-sm" id="btn-autofill-otp" style="font-size: 0.75rem;">
                  ⚡ Click to Auto-Fill Code
                </button>
              </div>
            </div>
          ` : `
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 0.75rem; margin-bottom: 1.25rem; font-size: 0.82rem; color: #34d399;">
              ✓ Verification code sent via ${escapeHtml(emailDelivery.provider)}. Please check your inbox.
            </div>
          `}

          <form id="form-verify-otp">
            <div class="form-group" style="text-align: center; margin-bottom: 1.25rem;">
              <label class="form-label" for="input-otp-code" style="font-size: 0.85rem; margin-bottom: 0.5rem; display: block;">
                Enter 6-Digit Single-Use Code:
              </label>
              <input type="text" id="input-otp-code" maxlength="6" pattern="[0-9]{6}" class="form-input" style="font-size: 1.6rem; letter-spacing: 8px; text-align: center; width: 220px; margin: 0 auto; font-family: monospace; font-weight: 700;" placeholder="000000" required autocomplete="one-time-code" />
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; font-size: 0.8rem; color: var(--text-muted);">
              <span id="otp-timer">Code expires in 10:00</span>
              <button type="button" class="auth-link-btn" id="btn-resend-otp">Resend Code</button>
            </div>

            <button type="submit" id="btn-submit-verify" class="btn btn-primary" style="width: 100%; justify-content: center; padding: 0.75rem;">
              Verify & Complete Sign In
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

  // Verify submit
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
      state.setPortalMode('CUSTOMER');
      state.setAuth(res.token, res.user);
      showToast('Email verified successfully! Welcome to Swift Service.', 'success');
      closeModal();
      state.notify();
    } catch (err) {
      console.error('OTP Verification error:', err);
      showToast(err.message || 'Invalid or expired verification code', 'error');
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Verify & Complete Sign In';
    }
  });
}

function openLegalModal(title, contentHtml) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="legal-modal-backdrop">
      <div class="rw-modal" style="max-width: 540px;">
        <div class="rw-modal-header">
          <h2 style="font-size: 1.15rem; font-weight: 700; color: #fff;">${escapeHtml(title)}</h2>
          <button class="rw-btn-close" id="btn-close-legal">✕</button>
        </div>
        <div class="rw-modal-body" style="line-height: 1.6; font-size: 0.9rem; color: var(--text-secondary);">
          ${contentHtml}
        </div>
        <div class="rw-modal-footer" style="padding-top: 1rem; border-top: 1px solid var(--border-subtle); text-align: right;">
          <button class="btn btn-secondary btn-sm" id="btn-dismiss-legal">Close</button>
        </div>
      </div>
    </div>
  `;

  const closeLegal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-legal')?.addEventListener('click', closeLegal);
  modalContainer.querySelector('#btn-dismiss-legal')?.addEventListener('click', closeLegal);
}
