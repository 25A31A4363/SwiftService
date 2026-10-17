/**
 * RetailWave - Customer Complaint Portal & Operational Dashboard Component
 * Clean navy header, guided submission, cryptographic OTP verification,
 * live reference tracking, and authorized operational triage.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import { escapeHtml } from './ui-utils.js';

export const COMPLAINT_CATEGORIES = [
  { id: 'Orders', icon: '📦', title: 'Orders', desc: 'Wrong items, missing contents, or checkout discrepancies' },
  { id: 'Product Issues', icon: '🏷️', title: 'Product Issues', desc: 'Damaged packaging, spoiled goods, or quality defects' },
  { id: 'Returns and Refunds', icon: '🔄', title: 'Returns and Refunds', desc: 'Refund status, receipt lookup, or return authorization' },
  { id: 'Payments', icon: '💳', title: 'Payments', desc: 'Double charge, declined card, or payment discrepancies' },
  { id: 'Delivery', icon: '🚚', title: 'Delivery', desc: 'Late carrier delivery, curbside pickup delay, or missing bags' },
  { id: 'Store Service', icon: '🏪', title: 'Store Service', desc: 'Aisle safety hazards, wet floors, or store staff assistance' },
  { id: 'Other', icon: '💬', title: 'Other Inquiries', desc: 'Store facilities, accessibility, or general feedback' }
];

export async function renderCustomerPortal(container) {
  const isCustomer = state.user && state.user.role === 'CUSTOMER';
  const isLoggedIn = !!state.user;

  let myComplaints = [];
  if (isLoggedIn) {
    try {
      myComplaints = await api.getMyComplaints();
    } catch (err) {
      console.warn('Could not load user complaints:', err);
    }
  }

  container.innerHTML = `
    <div class="rw-portal-wrapper">
      <!-- RetailWave Approved Navy Header -->
      <header class="rw-header" role="banner">
        <div class="rw-header-inner">
          <div class="rw-brand-group">
            <div class="rw-brand-mark">
              <span class="rw-logo-icon">🌊</span>
            </div>
            <div class="rw-brand-text">
              <span class="rw-brand-name">RetailWave</span>
              <span class="rw-brand-tag">Customer Support & Transparency</span>
            </div>
          </div>

          <nav class="rw-nav-links" aria-label="Customer Navigation">
            <a href="#" class="rw-nav-link active" id="nav-rw-home">Home</a>
            <a href="#" class="rw-nav-link" id="nav-rw-shop" title="Browse retail catalog demo">Shop</a>
            <a href="#" class="rw-nav-link" id="nav-rw-categories">Categories</a>
            <a href="#" class="rw-nav-link" id="nav-rw-offers">Offers</a>
            <a href="#" class="rw-nav-link" id="nav-rw-track-link">Track & Support</a>
          </nav>

          <div class="rw-header-actions">
            <button class="rw-btn-mode-switch" id="btn-switch-to-ops" title="Switch to Authorized R5 Operations Cockpit">
              ⚙️ Operations Cockpit
            </button>

            ${isLoggedIn ? `
              <div class="rw-user-menu">
                <div class="rw-user-pill" id="btn-rw-user-profile" role="button" tabindex="0">
                  <span class="rw-avatar">${escapeHtml((state.user.fullName || 'User').slice(0, 2).toUpperCase())}</span>
                  <div class="rw-user-meta">
                    <span class="rw-user-name">${escapeHtml(state.user.fullName || state.user.email)}</span>
                    <span class="rw-user-role-badge">${escapeHtml(state.user.role.replace(/_/g, ' '))}</span>
                  </div>
                </div>
                <button class="rw-btn-secondary-sm" id="btn-rw-logout">Sign Out</button>
              </div>
            ` : `
              <div class="rw-auth-buttons">
                <button class="rw-btn-secondary" id="btn-rw-open-login">Sign In</button>
                <button class="rw-btn-primary" id="btn-rw-open-register">Create Account</button>
              </div>
            `}
          </div>
        </div>
      </header>

      <!-- Support Landing Hero -->
      <section class="rw-hero-section">
        <div class="rw-hero-content">
          <span class="rw-hero-pill">⚡ Powered by R5 Closed-Loop Intelligence</span>
          <h1 class="rw-hero-title">Your Feedback Matters. Real Resolutions in Real Time.</h1>
          <p class="rw-hero-desc">
            Directly connect your feedback with store managers, regional HVAC technicians, and safety teams.
            Every issue receives an authentic tracking reference and verified resolution timeline.
          </p>

          <!-- Search & Track Bar -->
          <div class="rw-track-bar-card">
            <div class="rw-track-bar-label">🔍 Track an existing complaint:</div>
            <form id="form-quick-track" class="rw-track-form">
              <input 
                type="text" 
                id="input-track-ref" 
                class="rw-track-input" 
                placeholder="Enter reference number (e.g. REF-2026-A8K92)" 
                required 
                maxlength="20"
                autocomplete="off"
              />
              <button type="submit" class="rw-btn-primary rw-track-btn" id="btn-submit-track">
                Track Status
              </button>
            </form>
          </div>
        </div>
      </section>

      <!-- Category Cards Section -->
      <section class="rw-categories-section" id="section-categories">
        <div class="rw-section-header">
          <h2>Select a Feedback Category</h2>
          <p>Choose an area below to submit a guided complaint directly to the responsible team.</p>
        </div>

        <div class="rw-category-grid">
          ${COMPLAINT_CATEGORIES.map(cat => `
            <div class="rw-category-card" data-category="${cat.id}" role="button" tabindex="0">
              <div class="rw-cat-icon-box">${cat.icon}</div>
              <h3 class="rw-cat-title">${cat.title}</h3>
              <p class="rw-cat-desc">${cat.desc}</p>
              <div class="rw-cat-action-link">
                Submit Report →
              </div>
            </div>
          `).join('')}
        </div>
      </section>

      <!-- Customer Complaints History & Live Tracking Section -->
      <section class="rw-history-section" id="section-my-complaints">
        <div class="rw-section-header-flex">
          <div>
            <h2>${isLoggedIn ? 'Your Active & Historical Complaints' : 'Recent Tracked Resolutions'}</h2>
            <p>${isLoggedIn ? 'All reports filed by your account, synced in real time with store operations.' : 'Sign in to file a new report or review your account history.'}</p>
          </div>
          <div class="rw-history-actions">
            ${isLoggedIn ? `
              <button class="rw-btn-primary" id="btn-rw-new-complaint">
                + Submit New Complaint
              </button>
            ` : `
              <button class="rw-btn-primary" id="btn-rw-register-prompt">
                Register & File Complaint
              </button>
            `}
          </div>
        </div>

        <div id="rw-complaints-cards-container" class="rw-complaints-cards-grid">
          ${myComplaints.length === 0 ? `
            <div class="rw-empty-state">
              <span class="rw-empty-icon">📋</span>
              <h3>No Complaints Filed Yet</h3>
              <p>You haven't submitted any complaints under this account. Pick a category above to submit your first report.</p>
              <button class="rw-btn-secondary" id="btn-empty-file-complaint">Submit Complaint</button>
            </div>
          ` : myComplaints.map(c => renderComplaintCardHtml(c)).join('')}
        </div>
      </section>

      <!-- RetailWave Assurance Banner -->
      <footer class="rw-portal-footer">
        <div class="rw-footer-inner">
          <div class="rw-footer-col">
            <div class="rw-footer-brand">RetailWave Support</div>
            <p>Closed-loop operational responsiveness for modern retail environments.</p>
          </div>
          <div class="rw-footer-col">
            <h4>Security & Privacy</h4>
            <p>Customer data is strictly isolated. Passwords and OTP codes are protected by cryptographic hashing.</p>
          </div>
          <div class="rw-footer-col">
            <h4>Operational SLA</h4>
            <p>P1 safety hazards trigger mandatory technician alerts within 30 minutes.</p>
          </div>
        </div>
        <div class="rw-footer-bottom">
          © 2026 RetailWave & R5 Operational Intelligence Platform. All rights reserved.
        </div>
      </footer>
    </div>
  `;

  attachCustomerPortalEvents(container);
}

function renderComplaintCardHtml(c) {
  const statusBadgeClass = `badge-status-${(c.status || 'SUBMITTED').toLowerCase().replace(/_/g, '-')}`;
  const priorityClass = `badge-priority-${(c.priority || 'MEDIUM').toLowerCase()}`;
  const createdDate = new Date(c.createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });

  return `
    <div class="rw-complaint-card" data-id="${c.id}" data-ref="${c.referenceNumber}">
      <div class="rw-card-header">
        <span class="rw-ref-chip">${escapeHtml(c.referenceNumber)}</span>
        <span class="rw-status-chip ${statusBadgeClass}">${escapeHtml(c.status.replace(/_/g, ' '))}</span>
      </div>

      <div class="rw-card-meta">
        <span class="rw-card-category">${escapeHtml(c.category)}</span>
        <span class="rw-priority-badge ${priorityClass}">● ${escapeHtml(c.priority)}</span>
      </div>

      <h4 class="rw-card-subject">${escapeHtml(c.subject)}</h4>
      <p class="rw-card-snippet">${escapeHtml(c.description.slice(0, 120))}${c.description.length > 120 ? '...' : ''}</p>

      ${c.resolutionSummary ? `
        <div class="rw-card-resolution-box">
          <span class="rw-res-icon">✅</span>
          <div>
            <strong>Resolution:</strong>
            <p>${escapeHtml(c.resolutionSummary)}</p>
          </div>
        </div>
      ` : ''}

      <div class="rw-card-footer">
        <span class="rw-card-date">📅 ${createdDate}</span>
        <button class="rw-btn-text btn-view-complaint-timeline" data-id="${c.id}" data-ref="${c.referenceNumber}">
          View Status Timeline →
        </button>
      </div>
    </div>
  `;
}

function attachCustomerPortalEvents(container) {
  // Mode switcher back to staff Operations Cockpit
  const btnSwitchOps = container.querySelector('#btn-switch-to-ops');
  if (btnSwitchOps) {
    btnSwitchOps.addEventListener('click', () => {
      // If customer is logged in, alert or switch to staff preset
      if (state.user && state.user.role === 'CUSTOMER') {
        showToast('Switching active view to R5 Operations Cockpit (Staff Mode)...', 'info');
      }
      state.currentPortalMode = 'OPS';
      state.notify();
    });
  }

  // Quick track reference form
  const formTrack = container.querySelector('#form-quick-track');
  if (formTrack) {
    formTrack.addEventListener('submit', async (e) => {
      e.preventDefault();
      const refInput = container.querySelector('#input-track-ref');
      const ref = (refInput ? refInput.value : '').trim();
      if (!ref) return;
      await openTrackingModal(ref);
    });
  }

  // Header Nav links
  const trackLink = container.querySelector('#nav-rw-track-link');
  if (trackLink) {
    trackLink.addEventListener('click', (e) => {
      e.preventDefault();
      const input = container.querySelector('#input-track-ref');
      if (input) {
        input.focus();
        input.scrollIntoView({ behavior: 'smooth' });
      }
    });
  }

  const shopLink = container.querySelector('#nav-rw-shop');
  if (shopLink) {
    shopLink.addEventListener('click', (e) => {
      e.preventDefault();
      showToast('Catalog demo: browse fresh groceries & supercenter merchandise.', 'info');
    });
  }

  // Category card clicks -> opens submission modal with preselected category
  container.querySelectorAll('.rw-category-card').forEach(card => {
    card.addEventListener('click', () => {
      const cat = card.dataset.category;
      openComplaintSubmissionModal(cat);
    });
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openComplaintSubmissionModal(card.dataset.category);
      }
    });
  });

  // Buttons for new complaint
  const btnNew = container.querySelector('#btn-rw-new-complaint') || container.querySelector('#btn-empty-file-complaint');
  if (btnNew) {
    btnNew.addEventListener('click', () => openComplaintSubmissionModal());
  }

  const btnRegisterPrompt = container.querySelector('#btn-rw-register-prompt');
  if (btnRegisterPrompt) {
    btnRegisterPrompt.addEventListener('click', () => openCustomerRegisterModal());
  }

  // Auth buttons
  const btnLogin = container.querySelector('#btn-rw-open-login');
  if (btnLogin) {
    btnLogin.addEventListener('click', () => openCustomerLoginModal());
  }

  const btnRegister = container.querySelector('#btn-rw-open-register');
  if (btnRegister) {
    btnRegister.addEventListener('click', () => openCustomerRegisterModal());
  }

  // Logout
  const btnLogout = container.querySelector('#btn-rw-logout');
  if (btnLogout) {
    btnLogout.addEventListener('click', async () => {
      try {
        await api.logout();
      } catch {}
      state.setAuth(null, null);
      showToast('Signed out successfully.', 'info');
    });
  }

  // User Profile
  const btnProfile = container.querySelector('#btn-rw-user-profile');
  if (btnProfile) {
    btnProfile.addEventListener('click', () => openCustomerProfileModal());
  }

  // View timeline buttons on cards
  container.querySelectorAll('.btn-view-complaint-timeline').forEach(btn => {
    btn.addEventListener('click', () => {
      const ref = btn.dataset.ref;
      openTrackingModal(ref);
    });
  });
}

/**
 * Open Guided Complaint Submission Modal
 */
export function openComplaintSubmissionModal(initialCategory = 'Orders') {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  const stores = state.stores && state.stores.length > 0 ? state.stores : [
    { id: 'store-104', name: 'Apex Supercenter - Seattle Downtown' },
    { id: 'store-205', name: 'Apex Metro - Cambridge Galleria' }
  ];

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-submission-modal" role="dialog" aria-modal="true" aria-labelledby="modal-submit-title">
        <div class="modal-header">
          <div>
            <h2 id="modal-submit-title">Submit a Customer Complaint</h2>
            <p class="modal-subtitle">Your report is logged directly into the R5 operational management network.</p>
          </div>
          <button class="modal-close-btn" id="btn-close-submit-modal" aria-label="Close dialog">✕</button>
        </div>

        <form id="form-submit-complaint" class="rw-form-body">
          <div class="form-row">
            <div class="form-group flex-1">
              <label for="complaint-category" class="form-label required">Feedback Category</label>
              <select id="complaint-category" class="form-control" required>
                ${COMPLAINT_CATEGORIES.map(c => `
                  <option value="${c.id}" ${c.id === initialCategory ? 'selected' : ''}>${c.icon} ${c.title}</option>
                `).join('')}
              </select>
            </div>

            <div class="form-group flex-1">
              <label for="complaint-order-num" class="form-label">Order Number <span class="form-optional">(Optional)</span></label>
              <input type="text" id="complaint-order-num" class="form-control" placeholder="e.g. ORD-84920" maxlength="30" />
            </div>
          </div>

          <div class="form-group">
            <label for="complaint-store" class="form-label">Retail Store Location</label>
            <select id="complaint-store" class="form-control">
              ${stores.map(s => `
                <option value="${s.id}">${escapeHtml(s.name)}</option>
              `).join('')}
            </select>
          </div>

          <div class="form-group">
            <label for="complaint-subject" class="form-label required">Subject</label>
            <input 
              type="text" 
              id="complaint-subject" 
              class="form-control" 
              placeholder="Brief summary of the issue (e.g. Leaking milk carton in dairy aisle)" 
              required 
              minlength="3" 
              maxlength="200" 
            />
          </div>

          <div class="form-group">
            <label for="complaint-description" class="form-label required">Detailed Description</label>
            <textarea 
              id="complaint-description" 
              class="form-control rw-textarea" 
              rows="4" 
              placeholder="Please provide details such as aisle location, product name, or staff interaction to help us resolve the issue swiftly."
              required
              minlength="10"
              maxlength="5000"
            ></textarea>
            <div class="form-help-text">Minimum 10 characters. Avoid entering payment card CVV or sensitive personal IDs.</div>
          </div>

          <!-- Supporting Evidence File Upload -->
          <div class="form-group">
            <label class="form-label">Supporting Evidence / Photos <span class="form-optional">(Optional)</span></label>
            <div class="rw-file-upload-dropzone" id="dropzone-evidence">
              <input type="file" id="file-attachment" accept="image/png,image/jpeg,image/webp,application/pdf" style="display: none;" />
              <div class="rw-dropzone-content" id="dropzone-content">
                <span class="rw-upload-icon">📎</span>
                <div class="rw-upload-text">
                  <strong>Click to upload</strong> or drag and drop photos or PDF receipts
                </div>
                <div class="rw-upload-limits">PNG, JPG, WEBP, PDF up to 10 MB</div>
              </div>
              <div id="upload-preview" class="rw-upload-preview" style="display: none;">
                <span class="rw-preview-icon">📄</span>
                <span id="preview-filename" class="rw-preview-name"></span>
                <button type="button" class="rw-btn-remove-file" id="btn-remove-file">✕</button>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" id="btn-cancel-submit">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-confirm-submit">
              Submit Complaint
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  let uploadedFileUrl = null;
  let uploadedFileName = null;

  // Close handlers
  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-submit-modal').addEventListener('click', closeModal);
  modalContainer.querySelector('#btn-cancel-submit').addEventListener('click', closeModal);
  modalContainer.querySelector('#modal-backdrop').addEventListener('click', (e) => {
    if (e.target.id === 'modal-backdrop') closeModal();
  });

  // File Upload interactions
  const fileInput = modalContainer.querySelector('#file-attachment');
  const dropzone = modalContainer.querySelector('#dropzone-evidence');
  const dropzoneContent = modalContainer.querySelector('#dropzone-content');
  const uploadPreview = modalContainer.querySelector('#upload-preview');
  const previewFilename = modalContainer.querySelector('#preview-filename');
  const btnRemoveFile = modalContainer.querySelector('#btn-remove-file');

  dropzone.addEventListener('click', (e) => {
    if (e.target !== btnRemoveFile) fileInput.click();
  });

  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      showToast('File size exceeds 10 MB limit', 'error');
      return;
    }

    try {
      dropzoneContent.style.display = 'none';
      uploadPreview.style.display = 'flex';
      previewFilename.textContent = `Uploading ${file.name}...`;

      const uploadRes = await api.uploadComplaintAttachment(file);
      uploadedFileUrl = uploadRes.url;
      uploadedFileName = uploadRes.filename || file.name;

      previewFilename.textContent = `${uploadedFileName} (Ready)`;
      showToast('Evidence attachment uploaded successfully', 'success');
    } catch (err) {
      console.error('Upload error:', err);
      showToast(err.message || 'File upload failed', 'error');
      dropzoneContent.style.display = 'block';
      uploadPreview.style.display = 'none';
      uploadedFileUrl = null;
      uploadedFileName = null;
    }
  });

  btnRemoveFile.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.value = '';
    uploadedFileUrl = null;
    uploadedFileName = null;
    dropzoneContent.style.display = 'block';
    uploadPreview.style.display = 'none';
  });

  // Form submit
  const form = modalContainer.querySelector('#form-submit-complaint');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!state.user) {
      showToast('Please sign in or create an account to submit your complaint.', 'info');
      closeModal();
      openCustomerRegisterModal();
      return;
    }

    const payload = {
      category: modalContainer.querySelector('#complaint-category').value,
      orderNumber: modalContainer.querySelector('#complaint-order-num').value.trim() || undefined,
      storeId: modalContainer.querySelector('#complaint-store').value || undefined,
      subject: modalContainer.querySelector('#complaint-subject').value.trim(),
      description: modalContainer.querySelector('#complaint-description').value.trim(),
      attachmentUrl: uploadedFileUrl || undefined,
      attachmentName: uploadedFileName || undefined
    };

    const submitBtn = modalContainer.querySelector('#btn-confirm-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    try {
      const res = await api.submitComplaint(payload);
      showToast(`Complaint submitted! Reference: ${res.referenceNumber}`, 'success');
      closeModal();
      openSubmissionConfirmationModal(res);
      // Trigger re-render to update customer dashboard
      state.notify();
    } catch (err) {
      console.error('Complaint submission error:', err);
      showToast(err.message || 'Failed to submit complaint. Please check your connection.', 'error');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Complaint';
    }
  });
}

/**
 * Complaint Confirmation Modal with Copy Reference Button
 */
function openSubmissionConfirmationModal(complaint) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-confirm-modal" role="dialog" aria-modal="true">
        <div class="rw-confirm-icon-box">✓</div>
        <h2>Complaint Submitted Successfully</h2>
        <p class="rw-confirm-subtitle">Your report is logged and queued for store operations investigation.</p>

        <div class="rw-ref-box">
          <div class="rw-ref-label">Your Tracking Reference Number:</div>
          <div class="rw-ref-display" id="ref-copy-text">${escapeHtml(complaint.referenceNumber)}</div>
          <button class="rw-btn-copy" id="btn-copy-ref">📋 Copy Reference</button>
        </div>

        <div class="rw-confirm-details">
          <div class="rw-confirm-row">
            <span>Category:</span>
            <strong>${escapeHtml(complaint.category)}</strong>
          </div>
          <div class="rw-confirm-row">
            <span>Initial Priority:</span>
            <strong>● ${escapeHtml(complaint.priority)}</strong>
          </div>
          <div class="rw-confirm-row">
            <span>Facility:</span>
            <strong>${escapeHtml(complaint.storeName || 'Local Supercenter')}</strong>
          </div>
        </div>

        <div class="modal-footer" style="justify-content: center; margin-top: 1.5rem;">
          <button class="btn btn-secondary" id="btn-confirm-dismiss">Close</button>
          <button class="btn btn-primary" id="btn-confirm-track-now">Track Status Timeline →</button>
        </div>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-confirm-dismiss').addEventListener('click', closeModal);
  modalContainer.querySelector('#btn-confirm-track-now').addEventListener('click', () => {
    closeModal();
    openTrackingModal(complaint.referenceNumber);
  });

  const btnCopy = modalContainer.querySelector('#btn-copy-ref');
  btnCopy.addEventListener('click', () => {
    navigator.clipboard.writeText(complaint.referenceNumber).then(() => {
      btnCopy.textContent = '✓ Copied!';
      setTimeout(() => { btnCopy.textContent = '📋 Copy Reference'; }, 2000);
    });
  });
}

/**
 * Public or Authenticated Tracking Modal with Chronological Timeline Stepper
 */
export async function openTrackingModal(referenceNumber) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-tracking-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <h2>Tracking Reference: <span style="color: var(--color-primary);">${escapeHtml(referenceNumber)}</span></h2>
            <p class="modal-subtitle">Live resolution progress from Retail Operations Cockpit</p>
          </div>
          <button class="modal-close-btn" id="btn-close-track-modal">✕</button>
        </div>

        <div id="tracking-modal-content" class="rw-tracking-loading">
          <div class="spinner"></div>
          <p>Looking up complaint status and evidence lineage...</p>
        </div>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-track-modal').addEventListener('click', closeModal);
  modalContainer.querySelector('#modal-backdrop').addEventListener('click', (e) => {
    if (e.target.id === 'modal-backdrop') closeModal();
  });

  const contentEl = modalContainer.querySelector('#tracking-modal-content');

  try {
    const data = await api.trackComplaint(referenceNumber);

    const steps = [
      { key: 'SUBMITTED', label: 'Submitted', desc: 'Complaint logged into R5 customer portal' },
      { key: 'UNDER_REVIEW', label: 'Under Review', desc: 'Assigned to store lead & specialized team' },
      { key: 'IN_PROGRESS', label: 'In Progress', desc: 'Field technician or staff investigating' },
      { key: 'RESOLVED', label: 'Resolved', desc: 'Remediation completed and verified' }
    ];

    const currentStatus = data.status || 'SUBMITTED';
    const statusOrder = ['SUBMITTED', 'UNDER_REVIEW', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];
    const currentIndex = statusOrder.indexOf(currentStatus);

    contentEl.className = 'rw-tracking-body';
    contentEl.innerHTML = `
      <!-- Stepper Header -->
      <div class="rw-stepper-container">
        ${steps.map((step, idx) => {
          const isDone = currentIndex >= idx;
          const isCurrent = currentStatus === step.key;
          const stateClass = isDone ? 'step-done' : '';
          const currentClass = isCurrent ? 'step-active' : '';
          return `
            <div class="rw-step-item ${stateClass} ${currentClass}">
              <div class="rw-step-circle">${isDone ? '✓' : idx + 1}</div>
              <div class="rw-step-label">${step.label}</div>
              <div class="rw-step-sub">${step.desc}</div>
            </div>
          `;
        }).join('')}
      </div>

      <!-- Complaint Details -->
      <div class="rw-track-card-section">
        <div class="rw-track-header-row">
          <div>
            <span class="rw-card-category">${escapeHtml(data.category)}</span>
            <h3 style="margin: 0.4rem 0 0.2rem 0; font-size: 1.15rem; color: #fff;">${escapeHtml(data.subject)}</h3>
          </div>
          <div style="text-align: right;">
            <span class="badge-status-${currentStatus.toLowerCase()} rw-status-chip">
              ${escapeHtml(currentStatus.replace(/_/g, ' '))}
            </span>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">
              Assigned: <strong>${escapeHtml(data.assignedTeamName || 'Triage Queue')}</strong>
            </div>
          </div>
        </div>

        <div class="rw-track-description-box">
          <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 4px;">Customer Feedback:</div>
          <p style="margin: 0; font-size: 0.9rem; line-height: 1.5; color: var(--text-secondary);">
            ${escapeHtml(data.description)}
          </p>
        </div>

        ${data.attachmentName ? `
          <div class="rw-track-attachment-pill">
            <span>📎 Attached Evidence:</span>
            <strong>${escapeHtml(data.attachmentName)}</strong>
          </div>
        ` : ''}

        ${data.resolutionSummary ? `
          <div class="rw-official-resolution-card">
            <div class="rw-res-heading">
              <span>✅</span> Official RetailWave Resolution Summary
            </div>
            <p class="rw-res-text">${escapeHtml(data.resolutionSummary)}</p>
          </div>
        ` : ''}
      </div>

      <!-- Chronological Timeline Stepper -->
      <div class="rw-timeline-section">
        <h4 style="font-size: 0.95rem; margin-bottom: 0.75rem; color: #fff;">Chronological Audit Timeline</h4>
        <div class="rw-timeline-list">
          ${(data.timeline || []).map((entry, idx) => {
            const timeFormatted = new Date(entry.timestamp).toLocaleString(undefined, {
              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            return `
              <div class="rw-timeline-node">
                <div class="rw-node-dot"></div>
                <div class="rw-node-content">
                  <div class="rw-node-header">
                    <span class="rw-node-status">${escapeHtml(entry.status.replace(/_/g, ' '))}</span>
                    <span class="rw-node-time">${timeFormatted}</span>
                  </div>
                  <div class="rw-node-actor">Actor: <strong>${escapeHtml(entry.actor || 'System')}</strong></div>
                  ${entry.note ? `<div class="rw-node-note">${escapeHtml(entry.note)}</div>` : ''}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <div class="modal-footer" style="margin-top: 1rem;">
        <button class="btn btn-secondary" id="btn-close-track-bottom">Close</button>
      </div>
    `;

    modalContainer.querySelector('#btn-close-track-bottom').addEventListener('click', closeModal);
  } catch (err) {
    contentEl.className = 'rw-tracking-body';
    contentEl.innerHTML = `
      <div class="rw-error-box">
        <span style="font-size: 2rem;">❌</span>
        <h3>Complaint Reference Not Found</h3>
        <p>${escapeHtml(err.message || 'We could not locate this reference number. Please check the spelling.')}</p>
        <button class="btn btn-secondary" id="btn-error-close" style="margin-top: 1rem;">Close</button>
      </div>
    `;
    modalContainer.querySelector('#btn-error-close').addEventListener('click', closeModal);
  }
}

/**
 * Customer Registration Modal with Cryptographic 6-Digit Email OTP
 */
export function openCustomerRegisterModal() {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-auth-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <h2>Create RetailWave Customer Account</h2>
            <p class="modal-subtitle">Secure access to track complaints and service requests.</p>
          </div>
          <button class="modal-close-btn" id="btn-close-reg-modal">✕</button>
        </div>

        <form id="form-customer-register" class="rw-form-body">
          <div class="form-group">
            <label for="reg-name" class="form-label required">Full Name</label>
            <input type="text" id="reg-name" class="form-control" placeholder="e.g. Sarah Jenkins" required minlength="2" />
          </div>

          <div class="form-group">
            <label for="reg-email" class="form-label required">Email Address</label>
            <input type="email" id="reg-email" class="form-control" placeholder="e.g. customer@retailwave.com" required />
            <div class="form-help-text">A 6-digit single-use verification code will be dispatched to this address.</div>
          </div>

          <div class="form-row">
            <div class="form-group flex-1">
              <label for="reg-password" class="form-label required">Password</label>
              <input type="password" id="reg-password" class="form-control" placeholder="Min. 8 characters" required minlength="8" />
            </div>

            <div class="form-group flex-1">
              <label for="reg-phone" class="form-label">Phone <span class="form-optional">(Optional)</span></label>
              <input type="tel" id="reg-phone" class="form-control" placeholder="+1-555-019-2834" />
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-text" id="btn-switch-to-login">Already have an account? Sign In</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-reg">Create Account & Send Code</button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-reg-modal').addEventListener('click', closeModal);
  modalContainer.querySelector('#modal-backdrop').addEventListener('click', (e) => {
    if (e.target.id === 'modal-backdrop') closeModal();
  });
  modalContainer.querySelector('#btn-switch-to-login').addEventListener('click', () => {
    closeModal();
    openCustomerLoginModal();
  });

  const form = modalContainer.querySelector('#form-customer-register');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const fullName = modalContainer.querySelector('#reg-name').value.trim();
    const email = modalContainer.querySelector('#reg-email').value.trim();
    const password = modalContainer.querySelector('#reg-password').value;
    const phone = modalContainer.querySelector('#reg-phone').value.trim() || undefined;

    const btnSubmit = modalContainer.querySelector('#btn-submit-reg');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Sending Verification Code...';

    try {
      const res = await api.registerCustomer({ fullName, email, password, phone });
      showToast('Verification code dispatched to your email.', 'info');
      closeModal();
      openOtpVerificationModal(email, res.devOtpCode);
    } catch (err) {
      console.error('Registration error:', err);
      showToast(err.message || 'Failed to create account', 'error');
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Create Account & Send Code';
    }
  });
}

/**
 * 6-Digit Email OTP Verification Modal
 */
export function openOtpVerificationModal(email, devOtpCode = null) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-otp-modal" role="dialog" aria-modal="true">
        <div class="modal-header" style="text-align: center;">
          <div style="width: 100%;">
            <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">📬</div>
            <h2>Verify Your Email Address</h2>
            <p class="modal-subtitle">We sent a 6-digit verification code to <strong>${escapeHtml(email)}</strong></p>
          </div>
        </div>

        ${devOtpCode ? `
          <div class="rw-dev-sandbox-notice">
            <span class="rw-dev-badge">Sandbox Evaluation</span>
            <div>Developer evaluation code: <strong>${escapeHtml(devOtpCode)}</strong></div>
            <button type="button" class="rw-btn-text-xs" id="btn-autofill-otp">Auto-fill Code</button>
          </div>
        ` : ''}

        <form id="form-verify-otp" class="rw-form-body">
          <div class="form-group" style="text-align: center;">
            <label for="input-otp-code" class="form-label required">Enter 6-Digit Code</label>
            <input 
              type="text" 
              id="input-otp-code" 
              class="rw-otp-input" 
              maxlength="6" 
              placeholder="000000" 
              required 
              autocomplete="one-time-code"
              pattern="[0-9]{6}"
            />
            <div class="rw-otp-timer" id="otp-timer">Expires in 10:00</div>
          </div>

          <div class="modal-footer" style="flex-direction: column; gap: 0.75rem;">
            <button type="submit" class="btn btn-primary" id="btn-submit-verify" style="width: 100%;">
              Verify & Complete Sign In
            </button>
            <button type="button" class="btn btn-secondary btn-sm" id="btn-resend-otp" style="width: 100%;">
              Resend Code
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };

  // Auto-fill button if in sandbox
  const btnAutofill = modalContainer.querySelector('#btn-autofill-otp');
  if (btnAutofill && devOtpCode) {
    btnAutofill.addEventListener('click', () => {
      const input = modalContainer.querySelector('#input-otp-code');
      if (input) input.value = devOtpCode;
    });
  }

  // Resend OTP
  const btnResend = modalContainer.querySelector('#btn-resend-otp');
  if (btnResend) {
    btnResend.addEventListener('click', async () => {
      btnResend.disabled = true;
      btnResend.textContent = 'Resending...';
      try {
        const res = await api.resendCustomerOtp({ email });
        showToast('Fresh verification code sent to your inbox.', 'info');
        btnResend.textContent = 'Code Sent';
        if (res.devOtpCode) {
          const notice = modalContainer.querySelector('.rw-dev-sandbox-notice strong');
          if (notice) notice.textContent = res.devOtpCode;
        }
        setTimeout(() => {
          btnResend.disabled = false;
          btnResend.textContent = 'Resend Code';
        }, 60000);
      } catch (err) {
        showToast(err.message || 'Could not resend code', 'error');
        btnResend.disabled = false;
        btnResend.textContent = 'Resend Code';
      }
    });
  }

  // Verify submit
  const form = modalContainer.querySelector('#form-verify-otp');
  form.addEventListener('submit', async (e) => {
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
      state.setAuth(res.token, res.user);
      showToast('Email verified successfully! Welcome to RetailWave.', 'success');
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

/**
 * Customer Sign In Modal
 */
export function openCustomerLoginModal() {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-auth-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <h2>Sign In to RetailWave</h2>
            <p class="modal-subtitle">Access your submitted complaints and store resolutions.</p>
          </div>
          <button class="modal-close-btn" id="btn-close-login-modal">✕</button>
        </div>

        <form id="form-customer-login" class="rw-form-body">
          <div class="form-group">
            <label for="login-email" class="form-label required">Email Address</label>
            <input type="email" id="login-email" class="form-control" placeholder="customer@retailwave.com" required />
          </div>

          <div class="form-group">
            <label for="login-password" class="form-label required">Password</label>
            <input type="password" id="login-password" class="form-control" placeholder="Password123!" required />
          </div>

          <div class="rw-login-hint">
            <strong>Demo Customer Account:</strong> customer@retailwave.com / Password123!
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-text" id="btn-switch-to-reg">Don't have an account? Register</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-login">Sign In</button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-login-modal').addEventListener('click', closeModal);
  modalContainer.querySelector('#modal-backdrop').addEventListener('click', (e) => {
    if (e.target.id === 'modal-backdrop') closeModal();
  });
  modalContainer.querySelector('#btn-switch-to-reg').addEventListener('click', () => {
    closeModal();
    openCustomerRegisterModal();
  });

  const form = modalContainer.querySelector('#form-customer-login');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = modalContainer.querySelector('#login-email').value.trim();
    const password = modalContainer.querySelector('#login-password').value;

    const btnSubmit = modalContainer.querySelector('#btn-submit-login');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Authenticating...';

    try {
      const res = await api.login(email, password);
      state.setAuth(res.token, res.user);
      showToast(`Welcome back, ${res.user.fullName || res.user.email}!`, 'success');
      closeModal();
      state.notify();
    } catch (err) {
      console.error('Login error:', err);
      if (err.message && err.message.includes('EMAIL_UNVERIFIED')) {
        showToast('Your email is not verified yet. Please enter the verification code.', 'info');
        closeModal();
        openOtpVerificationModal(email);
        return;
      }
      showToast(err.message || 'Invalid email or password', 'error');
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Sign In';
    }
  });
}

/**
 * Customer Profile & Permitted Account Updates Modal
 */
export function openCustomerProfileModal() {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer || !state.user) return;

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-profile-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <h2>Manage Customer Profile</h2>
            <p class="modal-subtitle">Update your personal contact details or password securely.</p>
          </div>
          <button class="modal-close-btn" id="btn-close-prof-modal">✕</button>
        </div>

        <form id="form-update-profile" class="rw-form-body">
          <div class="form-group">
            <label for="prof-fullname" class="form-label required">Full Name</label>
            <input type="text" id="prof-fullname" class="form-control" value="${escapeHtml(state.user.fullName || '')}" required minlength="2" />
          </div>

          <div class="form-group">
            <label for="prof-email" class="form-label required">Email Address</label>
            <input type="email" id="prof-email" class="form-control" value="${escapeHtml(state.user.email || '')}" required />
            <div class="form-help-text">Changing your email address will require single-use OTP re-verification.</div>
          </div>

          <div class="form-group">
            <label for="prof-phone" class="form-label">Phone Number</label>
            <input type="tel" id="prof-phone" class="form-control" value="${escapeHtml(state.user.phone || '')}" placeholder="+1-555-019-2834" />
          </div>

          <div class="modal-footer" style="padding: 0; margin-top: 1rem;">
            <button type="submit" class="btn btn-primary" id="btn-save-profile">Save Contact Changes</button>
          </div>
        </form>

        <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;" />

        <!-- Password Change Section -->
        <form id="form-update-password" class="rw-form-body">
          <h4 style="margin: 0 0 0.5rem 0; color: #fff;">Change Password</h4>
          <div class="form-group">
            <label for="pwd-current" class="form-label required">Current Password</label>
            <input type="password" id="pwd-current" class="form-control" required />
          </div>

          <div class="form-row">
            <div class="form-group flex-1">
              <label for="pwd-new" class="form-label required">New Password</label>
              <input type="password" id="pwd-new" class="form-control" required minlength="8" />
            </div>
            <div class="form-group flex-1">
              <label for="pwd-confirm" class="form-label required">Confirm New Password</label>
              <input type="password" id="pwd-confirm" class="form-control" required minlength="8" />
            </div>
          </div>

          <div class="modal-footer" style="padding: 0; margin-top: 1rem;">
            <button type="submit" class="btn btn-secondary" id="btn-save-password">Update Password</button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-prof-modal').addEventListener('click', closeModal);
  modalContainer.querySelector('#modal-backdrop').addEventListener('click', (e) => {
    if (e.target.id === 'modal-backdrop') closeModal();
  });

  // Profile save
  const formProfile = modalContainer.querySelector('#form-update-profile');
  formProfile.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fullName = modalContainer.querySelector('#prof-fullname').value.trim();
    const email = modalContainer.querySelector('#prof-email').value.trim();
    const phone = modalContainer.querySelector('#prof-phone').value.trim();

    try {
      const updated = await api.updateProfile({ fullName, email, phone });
      state.user = updated;
      localStorage.setItem('r5_user', JSON.stringify(updated));
      showToast('Profile information updated in authoritative database.', 'success');
      closeModal();
      state.notify();
    } catch (err) {
      showToast(err.message || 'Failed to update profile', 'error');
    }
  });

  // Password save
  const formPwd = modalContainer.querySelector('#form-update-password');
  formPwd.addEventListener('submit', async (e) => {
    e.preventDefault();
    const currentPassword = modalContainer.querySelector('#pwd-current').value;
    const newPassword = modalContainer.querySelector('#pwd-new').value;
    const confirm = modalContainer.querySelector('#pwd-confirm').value;

    if (newPassword !== confirm) {
      showToast('New passwords do not match', 'error');
      return;
    }

    try {
      await api.changePassword({ currentPassword, newPassword });
      showToast('Password updated successfully.', 'success');
      closeModal();
    } catch (err) {
      showToast(err.message || 'Failed to change password', 'error');
    }
  });
}

/**
 * Operations Cockpit - Customer Complaints Management View
 * For Store Managers, Operations Managers, Regional VPs, and Analysts.
 */
export async function renderCustomerComplaintsView(container) {
  let complaints = [];
  let teams = [];
  try {
    const [cRes, tRes] = await Promise.all([
      api.listComplaints({ limit: 100 }),
      api.getTeams()
    ]);
    complaints = cRes.items || [];
    teams = tRes || [];
  } catch (err) {
    console.error('Error fetching staff complaints:', err);
  }

  const totalComplaints = complaints.length;
  const underInvestigation = complaints.filter(c => c.status === 'IN_PROGRESS' || c.status === 'UNDER_REVIEW').length;
  const resolved = complaints.filter(c => c.status === 'RESOLVED' || c.status === 'CLOSED').length;
  const critical = complaints.filter(c => c.priority === 'CRITICAL' || c.priority === 'HIGH').length;

  container.innerHTML = `
    <div class="view-header">
      <div>
        <h1 class="view-title">Customer Complaints & Ingested Feedback</h1>
        <p class="view-subtitle">Unified triage for customer portal reports, evidence lineage, and SLA resolution.</p>
      </div>
      <div class="view-header-actions">
        <button class="btn btn-secondary" id="btn-preview-customer-portal">
          🛍️ Open Customer Portal View
        </button>
      </div>
    </div>

    <!-- Operations Metrics KPI Row -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Incoming Reports</div>
        <div class="stat-value" id="kpi-total-complaints">${totalComplaints}</div>
        <div class="stat-subtext">Authoritative customer submissions</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Active Investigations</div>
        <div class="stat-value" style="color: var(--color-warning);" id="kpi-investigating">${underInvestigation}</div>
        <div class="stat-subtext">Under review or technician dispatch</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Verified Resolved</div>
        <div class="stat-value" style="color: var(--color-success);" id="kpi-resolved">${resolved}</div>
        <div class="stat-subtext">Resolution summary published</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">High / Critical Priority</div>
        <div class="stat-value" style="color: var(--color-error);" id="kpi-critical">${critical}</div>
        <div class="stat-subtext">Immediate safety / facility threats</div>
      </div>
    </div>

    <!-- Staff Filter Controls -->
    <div class="filter-bar" style="margin-top: 1.5rem;">
      <div class="search-box flex-1">
        <input type="text" id="staff-complaint-search" class="search-input" placeholder="Search by reference #, customer name, keyword, or store..." />
      </div>

      <div class="filter-group">
        <select id="staff-filter-status" class="filter-select">
          <option value="ALL">All Statuses</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="RESOLVED">Resolved</option>
          <option value="CLOSED">Closed</option>
        </select>

        <select id="staff-filter-category" class="filter-select">
          <option value="ALL">All Categories</option>
          ${COMPLAINT_CATEGORIES.map(cat => `<option value="${cat.id}">${cat.id}</option>`).join('')}
        </select>
      </div>
    </div>

    <!-- Staff Complaints Table -->
    <div class="table-container" style="margin-top: 1rem;">
      <table class="data-table" id="table-staff-complaints">
        <thead>
          <tr>
            <th>Reference</th>
            <th>Customer</th>
            <th>Category</th>
            <th>Facility Store</th>
            <th>Subject</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Assigned Team</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="tbody-staff-complaints">
          ${renderStaffComplaintsRows(complaints)}
        </tbody>
      </table>
    </div>
  `;

  // Attach staff view events
  const btnPreview = container.querySelector('#btn-preview-customer-portal');
  if (btnPreview) {
    btnPreview.addEventListener('click', () => {
      state.currentPortalMode = 'CUSTOMER';
      state.notify();
    });
  }

  const searchInput = container.querySelector('#staff-complaint-search');
  const selStatus = container.querySelector('#staff-filter-status');
  const selCat = container.querySelector('#staff-filter-category');
  const tbody = container.querySelector('#tbody-staff-complaints');

  const filterStaffList = () => {
    const q = (searchInput ? searchInput.value : '').toLowerCase().trim();
    const st = selStatus ? selStatus.value : 'ALL';
    const cat = selCat ? selCat.value : 'ALL';

    let filtered = complaints;
    if (st !== 'ALL') filtered = filtered.filter(c => c.status === st);
    if (cat !== 'ALL') filtered = filtered.filter(c => c.category === cat);
    if (q) {
      filtered = filtered.filter(c => 
        c.referenceNumber.toLowerCase().includes(q) ||
        c.customerName.toLowerCase().includes(q) ||
        c.subject.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q)
      );
    }
    tbody.innerHTML = renderStaffComplaintsRows(filtered);
    attachInvestigateButtons(container, complaints, teams);
  };

  if (searchInput) searchInput.addEventListener('input', filterStaffList);
  if (selStatus) selStatus.addEventListener('change', filterStaffList);
  if (selCat) selCat.addEventListener('change', filterStaffList);

  attachInvestigateButtons(container, complaints, teams);
}

function renderStaffComplaintsRows(complaints) {
  if (complaints.length === 0) {
    return `<tr><td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">No complaints match the selected filters.</td></tr>`;
  }

  return complaints.map(c => `
    <tr>
      <td>
        <span class="rw-ref-chip">${escapeHtml(c.referenceNumber)}</span>
      </td>
      <td>
        <strong>${escapeHtml(c.customerName)}</strong>
        <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(c.customerEmail)}</div>
      </td>
      <td>${escapeHtml(c.category)}</td>
      <td>${escapeHtml(c.storeName || 'Flagship')}</td>
      <td>
        <div style="font-weight: 500; color: #fff; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
          ${escapeHtml(c.subject)}
        </div>
      </td>
      <td>
        <span class="badge-priority-${(c.priority || 'MEDIUM').toLowerCase()}">● ${escapeHtml(c.priority)}</span>
      </td>
      <td>
        <span class="badge-status-${(c.status || 'SUBMITTED').toLowerCase().replace(/_/g, '-')}">
          ${escapeHtml(c.status.replace(/_/g, ' '))}
        </span>
      </td>
      <td>
        <span style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(c.assignedTeamName || 'Unassigned')}</span>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm btn-staff-investigate" data-id="${c.id}">
          Investigate & Update
        </button>
      </td>
    </tr>
  `).join('');
}

function attachInvestigateButtons(container, complaints, teams) {
  container.querySelectorAll('.btn-staff-investigate').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.id;
      const complaint = complaints.find(c => c.id === id);
      if (complaint) openStaffInvestigationDrawer(complaint, teams);
    });
  });
}

/**
 * Operations Investigation & Resolution Drawer Modal
 */
function openStaffInvestigationDrawer(complaint, teams) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  const validStatuses = ['SUBMITTED', 'UNDER_REVIEW', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];

  modalContainer.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal-window rw-investigate-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <h2>Investigate Complaint: <span style="color: var(--color-primary);">${escapeHtml(complaint.referenceNumber)}</span></h2>
            <p class="modal-subtitle">Authorized Operations Incident Remediation & Customer Response</p>
          </div>
          <button class="modal-close-btn" id="btn-close-inv-modal">✕</button>
        </div>

        <form id="form-investigate-complaint" class="rw-form-body">
          <div class="rw-inv-customer-bar">
            <div>
              <strong>Customer:</strong> ${escapeHtml(complaint.customerName)} (${escapeHtml(complaint.customerEmail)})
            </div>
            <div>
              <strong>Facility:</strong> ${escapeHtml(complaint.storeName || 'Store 104')} | 
              <strong>Category:</strong> ${escapeHtml(complaint.category)}
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Customer's Original Verbatim Submission</label>
            <div class="rw-inv-quote-box">
              <strong style="color: #fff;">${escapeHtml(complaint.subject)}</strong>
              <p style="margin: 0.35rem 0 0 0; color: var(--text-secondary); line-height: 1.5;">${escapeHtml(complaint.description)}</p>
            </div>
          </div>

          ${complaint.attachmentName ? `
            <div class="form-group">
              <label class="form-label">Customer Attachment Evidence</label>
              <div class="rw-track-attachment-pill">
                <span>📎 ${escapeHtml(complaint.attachmentName)}</span>
                <a href="${escapeHtml(complaint.attachmentUrl || '#')}" target="_blank" style="color: var(--color-primary); margin-left: auto;">View File ↗</a>
              </div>
            </div>
          ` : ''}

          <div class="form-row">
            <div class="form-group flex-1">
              <label for="inv-status" class="form-label required">Update Status</label>
              <select id="inv-status" class="form-control" required>
                ${validStatuses.map(st => `
                  <option value="${st}" ${st === complaint.status ? 'selected' : ''}>${st.replace(/_/g, ' ')}</option>
                `).join('')}
              </select>
            </div>

            <div class="form-group flex-1">
              <label for="inv-team" class="form-label">Assign Operational Team</label>
              <select id="inv-team" class="form-control">
                <option value="">-- No Team Assigned --</option>
                ${teams.map(t => `
                  <option value="${t.id}" ${t.id === complaint.assignedTeamId ? 'selected' : ''}>${escapeHtml(t.name)}</option>
                `).join('')}
              </select>
            </div>
          </div>

          <div class="form-group">
            <label for="inv-internal-notes" class="form-label">
              Internal Investigation Notes <span class="form-optional">(Confidential - Never Exposed to Customer)</span>
            </label>
            <textarea 
              id="inv-internal-notes" 
              class="form-control rw-textarea" 
              rows="3" 
              placeholder="Record diagnostic findings, asset tag inspected, technician observations, or parts required."
            >${escapeHtml(complaint.investigationNotes || '')}</textarea>
          </div>

          <div class="form-group">
            <label for="inv-resolution-summary" class="form-label">
              Official Resolution Summary <span class="form-optional">(Customer-Facing — Published to Customer Timeline)</span>
            </label>
            <textarea 
              id="inv-resolution-summary" 
              class="form-control rw-textarea" 
              rows="3" 
              placeholder="Provide a clear, respectful summary of the resolution, refund issued, or corrective repair performed."
            >${escapeHtml(complaint.resolutionSummary || '')}</textarea>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" id="btn-cancel-inv">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-save-inv">
              Save Updates & Append Timeline
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-inv-modal').addEventListener('click', closeModal);
  modalContainer.querySelector('#btn-cancel-inv').addEventListener('click', closeModal);

  const form = modalContainer.querySelector('#form-investigate-complaint');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const status = modalContainer.querySelector('#inv-status').value;
    const assignedTeamId = modalContainer.querySelector('#inv-team').value || undefined;
    const investigationNotes = modalContainer.querySelector('#inv-internal-notes').value.trim() || undefined;
    const resolutionSummary = modalContainer.querySelector('#inv-resolution-summary').value.trim() || undefined;

    const btnSave = modalContainer.querySelector('#btn-save-inv');
    btnSave.disabled = true;
    btnSave.textContent = 'Saving...';

    try {
      await api.updateComplaintStatus(complaint.id, {
        status,
        assignedTeamId,
        investigationNotes,
        resolutionSummary
      });

      showToast(`Complaint ${complaint.referenceNumber} status updated to ${status}.`, 'success');
      closeModal();
      // Re-render complaints view in R5 cockpit
      const ws = document.getElementById('view-workspace');
      if (ws) renderCustomerComplaintsView(ws);
    } catch (err) {
      console.error('Update status error:', err);
      showToast(err.message || 'Failed to update complaint status', 'error');
      btnSave.disabled = false;
      btnSave.textContent = 'Save Updates & Append Timeline';
    }
  });
}
