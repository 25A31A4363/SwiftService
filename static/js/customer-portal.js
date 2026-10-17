/**
 * Swift Service - Customer Experience Portal & Operational Triage Component
 * Complete Voice-of-Store customer complaint filing, 10-category selection,
 * multi-step guided wizard, cryptographic OTP verification, chronological tracking,
 * and authorized staff operations management.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import { escapeHtml } from './ui-utils.js';

export const COMPLAINT_CATEGORIES = [
  { id: 'Order and Delivery', icon: '📦', title: 'Order and Delivery', desc: 'Late carrier delivery, missing bags, or transit damage' },
  { id: 'Product Quality or Defect', icon: '🏷️', title: 'Product Quality or Defect', desc: 'Damaged packaging, spoiled goods, or quality defects' },
  { id: 'Returns and Refunds', icon: '🔄', title: 'Returns and Refunds', desc: 'Refund delays, receipt lookup, or return authorization' },
  { id: 'Payment and Billing', icon: '💳', title: 'Payment and Billing', desc: 'Double charge, declined card, or register discrepancy' },
  { id: 'Store Service', icon: '🏪', title: 'Store Service', desc: 'Aisle safety hazards, wet floors, or facility cleanliness' },
  { id: 'Staff Behaviour', icon: '👥', title: 'Staff Behaviour', desc: 'Customer assistance, employee conduct, or service delays' },
  { id: 'Product Availability', icon: '🛒', title: 'Product Availability', desc: 'Out-of-stock items, empty shelves, or inventory gaps' },
  { id: 'Pricing or Offers', icon: '🏷️', title: 'Pricing or Offers', desc: 'Shelf tag mismatch, coupon issues, or promotional errors' },
  { id: 'Store Facilities', icon: '🏢', title: 'Store Facilities', desc: 'Restrooms, parking, shopping carts, HVAC, or accessibility' },
  { id: 'Other', icon: '💬', title: 'Other Inquiries', desc: 'General customer inquiries and operational feedback' }
];

export async function renderCustomerPortal(container) {
  const isCustomer = state.user && state.user.role === 'CUSTOMER';
  const isLoggedIn = !!state.user;
  const isStaff = isLoggedIn && state.user.role !== 'CUSTOMER';

  let myComplaints = [];
  if (isLoggedIn) {
    try {
      myComplaints = await api.getMyComplaints();
    } catch (err) {
      console.warn('Could not load customer complaints:', err);
    }
  }

  container.innerHTML = `
    <div class="ss-portal-wrapper">
      <!-- Swift Service Deep Navy Header -->
      <header class="ss-header" role="banner">
        <div class="ss-header-inner">
          <div class="ss-brand-group">
            <div class="ss-brand-mark">
              <span class="ss-logo-icon">⚡</span>
            </div>
            <div class="ss-brand-text">
              <span class="ss-brand-name">Swift Service</span>
              <span class="ss-brand-tag">Customer Experience Portal</span>
            </div>
          </div>

          <nav class="ss-nav-links" aria-label="Customer Navigation">
            <a href="#" class="ss-nav-link active" id="nav-ss-home">Home</a>
            <a href="#" class="ss-nav-link" id="nav-ss-categories">Categories</a>
            <a href="#" class="ss-nav-link" id="nav-ss-submit">Submit Complaint</a>
            <a href="#" class="ss-nav-link" id="nav-ss-my-complaints">
              My Complaints ${myComplaints.length > 0 ? `<span class="ss-nav-counter">${myComplaints.length}</span>` : ''}
            </a>
            <a href="#" class="ss-nav-link" id="nav-ss-track">Track Status</a>
            <a href="#" class="ss-nav-link" id="nav-ss-help">Help & FAQ</a>
          </nav>

          <div class="ss-header-actions">
            ${isStaff ? `
              <button class="ss-btn-mode-switch" id="btn-switch-to-ops" title="Switch to Authorized Operations Intelligence Portal">
                ⚙️ Operations Intelligence Portal
              </button>
            ` : ''}

            ${isLoggedIn ? `
              <div class="ss-user-pill" id="btn-customer-profile" role="button" tabindex="0" title="Manage Account Profile & Security">
                <div class="ss-avatar">
                  ${escapeHtml(state.user.fullName.split(' ').map(n => n[0]).join('').slice(0, 2))}
                </div>
                <div class="ss-user-meta">
                  <span class="ss-user-name">${escapeHtml(state.user.fullName)}</span>
                  <span class="ss-user-role">${escapeHtml(state.user.role.replace(/_/g, ' '))}</span>
                </div>
              </div>
              <button class="btn btn-secondary btn-sm" id="btn-ss-logout" title="Sign Out of Session">
                Sign Out
              </button>
            ` : `
              <button class="btn btn-primary btn-sm" id="btn-ss-auth-entry">
                Sign In / Register
              </button>
            `}
          </div>
        </div>
      </header>

      <!-- Main Customer Experience Body -->
      <main class="ss-portal-main">
        <!-- Welcoming Hero Section -->
        <section class="ss-hero-section">
          <div class="ss-hero-content">
            <span class="ss-hero-badge">⚡ Voice-of-Store Resolution Platform</span>
            <h1 class="ss-hero-title">How can we help you today?</h1>
            <p class="ss-hero-subtitle">
              We are committed to exceptional retail quality. Submit a complaint, attach supporting evidence, and track real-time resolution with transparent operational milestones.
            </p>

            <!-- Quick Actions Row -->
            <div class="ss-hero-actions">
              <button class="btn btn-primary ss-hero-btn" id="btn-hero-submit-complaint">
                <span>📝</span> Submit a Complaint
              </button>
              <button class="btn btn-secondary ss-hero-btn" id="btn-hero-track-complaint">
                <span>🔍</span> Track Existing Complaint
              </button>
            </div>

            <!-- Instant Reference Tracker Bar -->
            <div class="ss-quick-tracker-card">
              <div class="ss-tracker-label">
                <strong>Track Status by Reference Number:</strong>
                <span>Instant live update on any reported complaint</span>
              </div>
              <form id="form-quick-track" class="ss-tracker-form">
                <div class="ss-tracker-input-group">
                  <span class="ss-tracker-icon">🔎</span>
                  <input 
                    type="text" 
                    id="input-quick-track-ref" 
                    class="ss-tracker-input" 
                    placeholder="e.g. REF-2026-A8K92" 
                    pattern="REF-2026-[A-Z0-9]{5}"
                    title="Reference format: REF-2026-XXXXX"
                    required
                  />
                  <button type="submit" class="btn btn-primary ss-tracker-submit-btn">
                    Track Status
                  </button>
                </div>
              </form>
            </div>
          </div>
        </section>

        <!-- 10 Complaint Category Cards Section -->
        <section class="ss-categories-section" id="section-categories">
          <div class="ss-section-header">
            <div>
              <h2 class="ss-section-title">Select a Complaint Category</h2>
              <p class="ss-section-subtitle">Click any category below to begin our guided multi-step complaint submission.</p>
            </div>
          </div>

          <div class="ss-categories-grid">
            ${COMPLAINT_CATEGORIES.map(c => `
              <div class="ss-category-card" data-category="${c.id}" role="button" tabindex="0" title="File complaint under ${c.title}">
                <div class="ss-category-icon">${c.icon}</div>
                <h3 class="ss-category-title">${c.title}</h3>
                <p class="ss-category-desc">${c.desc}</p>
                <div class="ss-category-action">
                  <span>File Complaint</span>
                  <span class="ss-arrow">→</span>
                </div>
              </div>
            `).join('')}
          </div>
        </section>

        <!-- Customer My Complaints Section (When Logged In) -->
        <section class="ss-complaints-section" id="section-my-complaints">
          <div class="ss-section-header">
            <div>
              <h2 class="ss-section-title">My Complaint History</h2>
              <p class="ss-section-subtitle">Your authoritative submitted reports and live operational resolution updates.</p>
            </div>
            <div class="ss-section-actions">
              <button class="btn btn-primary btn-sm" id="btn-new-complaint-top">
                + New Complaint
              </button>
            </div>
          </div>

          ${myComplaints.length > 0 ? `
            <!-- Filter Tabs for Customer -->
            <div class="ss-filter-tabs" role="tablist">
              <button class="ss-filter-tab active" data-filter="ALL">All Reports (${myComplaints.length})</button>
              <button class="ss-filter-tab" data-filter="OPEN">Open (${myComplaints.filter(c => c.status === 'SUBMITTED' || c.status === 'UNDER_REVIEW').length})</button>
              <button class="ss-filter-tab" data-filter="IN_PROGRESS">In Progress (${myComplaints.filter(c => c.status === 'IN_PROGRESS').length})</button>
              <button class="ss-filter-tab" data-filter="RESOLVED">Resolved (${myComplaints.filter(c => c.status === 'RESOLVED' || c.status === 'CLOSED').length})</button>
            </div>

            <div class="ss-complaints-list" id="customer-complaints-list">
              ${renderCustomerComplaintCards(myComplaints)}
            </div>
          ` : `
            <div class="ss-empty-box">
              <div class="ss-empty-icon">📋</div>
              <h3>No Complaints Submitted Yet</h3>
              <p>You have not filed any customer complaints. If you experienced any issue with a recent order, item, or store visit, our support team is here to assist.</p>
              <button class="btn btn-primary" id="btn-empty-submit">
                Submit Your First Complaint
              </button>
            </div>
          `}
        </section>

        <!-- Help & FAQ Section -->
        <section class="ss-faq-section" id="section-help">
          <div class="ss-section-header">
            <div>
              <h2 class="ss-section-title">Frequently Asked Questions</h2>
              <p class="ss-section-subtitle">Common questions regarding our resolution timeline and complaint process.</p>
            </div>
          </div>

          <div class="ss-faq-grid">
            <div class="ss-faq-item">
              <div class="ss-faq-q">⏱️ How long does resolution usually take?</div>
              <div class="ss-faq-a">Our store operations team reviews incoming complaints within 2 hours. Physical store maintenance or refrigeration investigations are typically assigned and resolved within 24 to 48 hours.</div>
            </div>
            <div class="ss-faq-item">
              <div class="ss-faq-q">🧾 Can I track a complaint without logging in?</div>
              <div class="ss-faq-a">Yes. Every complaint receives a unique reference number (e.g. REF-2026-A8K92). You can enter this code in the tracker bar above to view live chronological milestones at any time.</div>
            </div>
            <div class="ss-faq-item">
              <div class="ss-faq-q">📎 What supporting files can I attach?</div>
              <div class="ss-faq-a">You can attach PNG, JPG, or WEBP photos of product packaging, damaged cartons, store shelf tags, or digital PDF receipts up to 10 MB.</div>
            </div>
            <div class="ss-faq-item">
              <div class="ss-faq-q">🔒 Who has access to my complaint information?</div>
              <div class="ss-faq-a">Only you and authorized Swift Service operational staff assigned to your specific store location have access. Your contact details are never shared with other customers or external parties.</div>
            </div>
          </div>
        </section>
      </main>

      <!-- Swift Service Footer -->
      <footer class="ss-footer" role="contentinfo">
        <div class="ss-footer-inner">
          <div class="ss-footer-col">
            <div class="ss-footer-brand">
              <span class="ss-logo-icon">⚡</span>
              <span>Swift Service Support</span>
            </div>
            <p class="ss-footer-desc">
              AI-powered retail operational intelligence and customer feedback resolution engine across regional store fleets.
            </p>
          </div>
          <div class="ss-footer-col">
            <h4>Quick Links</h4>
            <a href="#" id="link-footer-submit">Submit a Complaint</a>
            <a href="#" id="link-footer-track">Track Existing Reference</a>
            <a href="#" id="link-footer-categories">10 Service Categories</a>
          </div>
          <div class="ss-footer-col">
            <h4>Security & Privacy</h4>
            <a href="#" id="link-footer-privacy">Customer Privacy Notice</a>
            <a href="#" id="link-footer-terms">Terms of Service</a>
            <a href="#" id="link-footer-gov">Governance & RBAC</a>
          </div>
        </div>
        <div class="ss-footer-bottom">
          <div>© 2026 Swift Service Platform. Voice-of-Store Operations Intelligence. All rights reserved.</div>
        </div>
      </footer>
    </div>
  `;

  attachCustomerPortalEvents(container, myComplaints);
}

function renderCustomerComplaintCards(complaints) {
  return complaints.map(c => {
    const statusClass = getStatusBadgeClass(c.status);
    const dateFormatted = new Date(c.createdAt).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });

    return `
      <div class="ss-complaint-card" data-ref="${escapeHtml(c.referenceNumber)}">
        <div class="ss-card-top">
          <div class="ss-ref-group">
            <span class="ss-ref-badge">${escapeHtml(c.referenceNumber)}</span>
            <span class="ss-category-pill">${escapeHtml(c.category)}</span>
          </div>
          <span class="ss-status-badge ${statusClass}">${escapeHtml(c.status.replace(/_/g, ' '))}</span>
        </div>

        <h4 class="ss-card-subject">${escapeHtml(c.subject)}</h4>
        <p class="ss-card-desc">${escapeHtml(c.description.slice(0, 140))}${c.description.length > 140 ? '...' : ''}</p>

        <div class="ss-card-meta">
          <div class="ss-meta-item">
            <span>📅 Submitted:</span>
            <strong>${dateFormatted}</strong>
          </div>
          ${c.assignedTeamName ? `
            <div class="ss-meta-item">
              <span>🛠️ Team:</span>
              <strong>${escapeHtml(c.assignedTeamName)}</strong>
            </div>
          ` : ''}
          ${c.orderNumber ? `
            <div class="ss-meta-item">
              <span>📦 Order:</span>
              <strong>${escapeHtml(c.orderNumber)}</strong>
            </div>
          ` : ''}
        </div>

        ${c.resolutionSummary ? `
          <div class="ss-card-resolution-note">
            <strong>✓ Resolution Update:</strong> ${escapeHtml(c.resolutionSummary)}
          </div>
        ` : ''}

        <div class="ss-card-footer">
          <button class="btn btn-secondary btn-sm btn-track-card" data-ref="${escapeHtml(c.referenceNumber)}">
            View Chronological Status Timeline →
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'SUBMITTED': return 'status-submitted';
    case 'UNDER_REVIEW': return 'status-review';
    case 'IN_PROGRESS': return 'status-progress';
    case 'RESOLVED': return 'status-resolved';
    case 'CLOSED': return 'status-closed';
    default: return 'status-neutral';
  }
}

function attachCustomerPortalEvents(container, myComplaints) {
  // Navigation scrolling
  container.querySelector('#nav-ss-home')?.addEventListener('click', (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  container.querySelector('#nav-ss-categories')?.addEventListener('click', (e) => {
    e.preventDefault();
    container.querySelector('#section-categories')?.scrollIntoView({ behavior: 'smooth' });
  });

  container.querySelector('#nav-ss-submit')?.addEventListener('click', (e) => {
    e.preventDefault();
    openGuidedComplaintWizard();
  });

  container.querySelector('#btn-hero-submit-complaint')?.addEventListener('click', () => {
    openGuidedComplaintWizard();
  });

  container.querySelector('#btn-new-complaint-top')?.addEventListener('click', () => {
    openGuidedComplaintWizard();
  });

  container.querySelector('#btn-empty-submit')?.addEventListener('click', () => {
    openGuidedComplaintWizard();
  });

  container.querySelector('#nav-ss-my-complaints')?.addEventListener('click', (e) => {
    e.preventDefault();
    container.querySelector('#section-my-complaints')?.scrollIntoView({ behavior: 'smooth' });
  });

  container.querySelector('#nav-ss-track')?.addEventListener('click', (e) => {
    e.preventDefault();
    container.querySelector('#input-quick-track-ref')?.focus();
  });

  container.querySelector('#btn-hero-track-complaint')?.addEventListener('click', () => {
    container.querySelector('#input-quick-track-ref')?.focus();
  });

  container.querySelector('#nav-ss-help')?.addEventListener('click', (e) => {
    e.preventDefault();
    container.querySelector('#section-help')?.scrollIntoView({ behavior: 'smooth' });
  });

  // Category Cards: Launch Multi-Step Wizard with selected category
  container.querySelectorAll('.ss-category-card').forEach(card => {
    card.addEventListener('click', () => {
      const categoryId = card.getAttribute('data-category');
      openGuidedComplaintWizard(categoryId);
    });
  });

  // Quick Tracker Form
  const trackForm = container.querySelector('#form-quick-track');
  trackForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const ref = container.querySelector('#input-quick-track-ref').value.trim().toUpperCase();
    if (!ref) return;
    openTrackingTimelineModal(ref);
  });

  // Track buttons on individual cards
  container.querySelectorAll('.btn-track-card').forEach(btn => {
    btn.addEventListener('click', () => {
      const ref = btn.getAttribute('data-ref');
      openTrackingTimelineModal(ref);
    });
  });

  // Customer Filter Tabs
  container.querySelectorAll('.ss-filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.ss-filter-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const filter = tab.getAttribute('data-filter');
      const listEl = container.querySelector('#customer-complaints-list');
      if (!listEl) return;

      let filtered = myComplaints;
      if (filter === 'OPEN') {
        filtered = myComplaints.filter(c => c.status === 'SUBMITTED' || c.status === 'UNDER_REVIEW');
      } else if (filter === 'IN_PROGRESS') {
        filtered = myComplaints.filter(c => c.status === 'IN_PROGRESS');
      } else if (filter === 'RESOLVED') {
        filtered = myComplaints.filter(c => c.status === 'RESOLVED' || c.status === 'CLOSED');
      }

      listEl.innerHTML = renderCustomerComplaintCards(filtered);

      // Re-attach card events
      listEl.querySelectorAll('.btn-track-card').forEach(b => {
        b.addEventListener('click', () => {
          openTrackingTimelineModal(b.getAttribute('data-ref'));
        });
      });
    });
  });

  // Switch to Operations Cockpit (Authorized Staff only)
  container.querySelector('#btn-switch-to-ops')?.addEventListener('click', () => {
    state.setPortalMode('OPS');
    showToast('Switching active view to Operations Intelligence Portal (Staff Mode)...', 'info');
  });

  // Auth Entry Button (if not logged in)
  container.querySelector('#btn-ss-auth-entry')?.addEventListener('click', () => {
    state.setAuth(null, null);
    state.notify();
  });

  // Logout
  container.querySelector('#btn-ss-logout')?.addEventListener('click', () => {
    state.setAuth(null, null);
    showToast('Signed out safely from Swift Service.', 'info');
    state.notify();
  });

  // Profile Modal
  container.querySelector('#btn-customer-profile')?.addEventListener('click', () => {
    openCustomerProfileModal();
  });
}

/**
 * Multi-Step Guided Complaint Submission Wizard
 * Step 1: Complaint Details
 * Step 2: Additional Info, Follow-Ups & File Attachment
 * Step 3: Review & Submit
 * Output: Authoritative Reference Code
 */
export function openGuidedComplaintWizard(initialCategory = 'Order and Delivery') {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  const stores = state.stores && state.stores.length > 0 ? state.stores : [
    { id: 'store-104', name: 'Apex Supercenter - Seattle Downtown' },
    { id: 'store-205', name: 'Apex Metro - Cambridge Galleria' }
  ];

  let currentStep = 1;
  let wizardData = {
    category: initialCategory,
    subject: '',
    description: '',
    orderNumber: '',
    storeId: stores[0]?.id || '',
    incidentDate: '',
    categoryFollowUp: '',
    contactPreference: 'Email',
    attachmentUrl: null,
    attachmentName: null
  };

  function renderWizard() {
    modalContainer.innerHTML = `
      <div class="rw-modal-backdrop" id="wizard-modal-backdrop">
        <div class="rw-modal ss-wizard-modal">
          <div class="rw-modal-header">
            <div>
              <h2 style="font-size: 1.25rem; font-weight: 700; color: #fff;">File a Customer Complaint</h2>
              <div style="font-size: 0.8rem; color: var(--text-muted);">Guided 3-Step Intake — Directly Linked to Swift Service Intelligence</div>
            </div>
            <button class="rw-btn-close" id="btn-close-wizard">✕</button>
          </div>

          <!-- 3-Step Stepper Header -->
          <div class="ss-wizard-stepper">
            <div class="ss-step-item ${currentStep === 1 ? 'active' : (currentStep > 1 ? 'completed' : '')}">
              <div class="ss-step-circle">${currentStep > 1 ? '✓' : '1'}</div>
              <div class="ss-step-label">Complaint Details</div>
            </div>
            <div class="ss-step-connector ${currentStep > 1 ? 'completed' : ''}"></div>
            <div class="ss-step-item ${currentStep === 2 ? 'active' : (currentStep > 2 ? 'completed' : '')}">
              <div class="ss-step-circle">${currentStep > 2 ? '✓' : '2'}</div>
              <div class="ss-step-label">Additional Info</div>
            </div>
            <div class="ss-step-connector ${currentStep > 2 ? 'completed' : ''}"></div>
            <div class="ss-step-item ${currentStep === 3 ? 'active' : ''}">
              <div class="ss-step-circle">3</div>
              <div class="ss-step-label">Review & Submit</div>
            </div>
          </div>

          <!-- Wizard Body -->
          <div class="rw-modal-body">
            ${currentStep === 1 ? renderStep1Html(wizardData, stores) : ''}
            ${currentStep === 2 ? renderStep2Html(wizardData) : ''}
            ${currentStep === 3 ? renderStep3Html(wizardData, stores) : ''}
          </div>

          <!-- Wizard Footer Controls -->
          <div class="rw-modal-footer ss-wizard-footer">
            ${currentStep > 1 ? `
              <button type="button" class="btn btn-secondary" id="btn-wizard-prev">
                ← Back
              </button>
            ` : `
              <button type="button" class="btn btn-secondary" id="btn-wizard-cancel">
                Cancel
              </button>
            `}

            ${currentStep < 3 ? `
              <button type="button" class="btn btn-primary" id="btn-wizard-next">
                Next: ${currentStep === 1 ? 'Additional Information →' : 'Review & Submit →'}
              </button>
            ` : `
              <button type="button" class="btn btn-primary" id="btn-wizard-submit">
                ✓ Confirm & Submit Complaint
              </button>
            `}
          </div>
        </div>
      </div>
    `;

    attachWizardStepEvents();
  }

  function renderStep1Html(data, storeList) {
    return `
      <div class="ss-step-content">
        <div class="form-row">
          <div class="form-group flex-1">
            <label class="form-label required" for="wiz-category">Complaint Category</label>
            <select id="wiz-category" class="form-input">
              ${COMPLAINT_CATEGORIES.map(c => `
                <option value="${c.id}" ${c.id === data.category ? 'selected' : ''}>${c.icon} ${c.title}</option>
              `).join('')}
            </select>
          </div>

          <div class="form-group flex-1">
            <label class="form-label" for="wiz-order-num">Order or Transaction Number <span class="form-optional">(Optional)</span></label>
            <input type="text" id="wiz-order-num" class="form-input" placeholder="e.g. ORD-84920" value="${escapeHtml(data.orderNumber)}" />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group flex-1">
            <label class="form-label" for="wiz-store">Retail Store / Branch Facility</label>
            <select id="wiz-store" class="form-input">
              ${storeList.map(s => `
                <option value="${s.id}" ${s.id === data.storeId ? 'selected' : ''}>${escapeHtml(s.name)}</option>
              `).join('')}
            </select>
          </div>

          <div class="form-group flex-1">
            <label class="form-label" for="wiz-date">Incident Date & Time <span class="form-optional">(Optional)</span></label>
            <input type="datetime-local" id="wiz-date" class="form-input" value="${escapeHtml(data.incidentDate)}" />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label required" for="wiz-subject">Subject</label>
          <input type="text" id="wiz-subject" class="form-input" placeholder="Brief summary of the issue (e.g. Broken seal on refrigerated dairy carton)" value="${escapeHtml(data.subject)}" required minlength="3" maxlength="200" />
        </div>

        <div class="form-group">
          <label class="form-label required" for="wiz-description">Detailed Description</label>
          <textarea id="wiz-description" class="form-input rw-textarea" rows="4" placeholder="Please describe exactly what occurred, including aisle, product brand, or employee interactions." required minlength="10" maxlength="5000">${escapeHtml(data.description)}</textarea>
          <div class="form-help-text">Minimum 10 characters. Avoid entering payment card CVV or sensitive IDs.</div>
        </div>
      </div>
    `;
  }

  function renderStep2Html(data) {
    const followUpQuestion = getCategoryFollowUpPrompt(data.category);

    return `
      <div class="ss-step-content">
        <!-- Category Specific Follow Up -->
        <div class="form-group">
          <label class="form-label" for="wiz-followup">${followUpQuestion}</label>
          <input type="text" id="wiz-followup" class="form-input" placeholder="Provide any extra details if known" value="${escapeHtml(data.categoryFollowUp)}" />
        </div>

        <!-- Preferred Contact Method -->
        <div class="form-group">
          <label class="form-label">Preferred Contact Channel for Updates</label>
          <div style="display: flex; gap: 1rem; margin-top: 0.35rem;">
            ${['Email', 'Phone Call', 'SMS Text'].map(m => `
              <label class="auth-checkbox-label" style="font-size: 0.85rem;">
                <input type="radio" name="contact-pref" value="${m}" ${data.contactPreference === m ? 'checked' : ''} />
                <span>${m}</span>
              </label>
            `).join('')}
          </div>
        </div>

        <!-- File Attachment Dropzone -->
        <div class="form-group">
          <label class="form-label">Attach Photos or PDF Receipts <span class="form-optional">(Optional)</span></label>
          <div class="rw-file-upload-dropzone" id="dropzone-evidence">
            <input type="file" id="file-attachment" accept="image/png,image/jpeg,image/webp,application/pdf" style="display: none;" />
            
            <div class="rw-dropzone-content" id="dropzone-content" style="${data.attachmentName ? 'display: none;' : ''}">
              <span class="rw-upload-icon">📎</span>
              <div class="rw-upload-text">
                <strong>Click to upload</strong> or drag and drop photos or PDF receipts
              </div>
              <div class="rw-upload-limits">PNG, JPG, WEBP, PDF up to 10 MB</div>
            </div>

            <div id="upload-preview" class="rw-upload-preview" style="${data.attachmentName ? 'display: flex;' : 'display: none;'}">
              <span class="rw-preview-icon">📄</span>
              <span id="preview-filename" class="rw-preview-name">${escapeHtml(data.attachmentName || '')}</span>
              <button type="button" class="rw-btn-remove-file" id="btn-remove-file">✕</button>
            </div>
          </div>
        </div>

        <div class="ss-privacy-notice-box">
          <span style="font-size: 1.1rem;">🔒</span>
          <div>
            <strong>Customer Privacy Notice:</strong> Your attachments and contact details are strictly compartmentalized and accessible only to assigned retail investigation staff.
          </div>
        </div>
      </div>
    `;
  }

  function renderStep3Html(data, storeList) {
    const storeObj = storeList.find(s => s.id === data.storeId);
    const storeName = storeObj ? storeObj.name : 'Not Specified';

    return `
      <div class="ss-step-content">
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 1.25rem;">
          <h3 style="font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 1rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem;">
            Review Your Complaint Information
          </h3>

          <div class="ss-review-grid">
            <div class="ss-review-row">
              <span class="ss-review-label">Category:</span>
              <strong class="ss-review-val">${escapeHtml(data.category)}</strong>
            </div>
            <div class="ss-review-row">
              <span class="ss-review-label">Subject:</span>
              <strong class="ss-review-val">${escapeHtml(data.subject)}</strong>
            </div>
            <div class="ss-review-row">
              <span class="ss-review-label">Store Location:</span>
              <span class="ss-review-val">${escapeHtml(storeName)}</span>
            </div>
            ${data.orderNumber ? `
              <div class="ss-review-row">
                <span class="ss-review-label">Order Ref:</span>
                <span class="ss-review-val">${escapeHtml(data.orderNumber)}</span>
              </div>
            ` : ''}
            <div class="ss-review-row" style="align-items: flex-start;">
              <span class="ss-review-label">Description:</span>
              <span class="ss-review-val" style="white-space: pre-wrap;">${escapeHtml(data.description)}</span>
            </div>
            ${data.categoryFollowUp ? `
              <div class="ss-review-row">
                <span class="ss-review-label">Additional Note:</span>
                <span class="ss-review-val">${escapeHtml(data.categoryFollowUp)}</span>
              </div>
            ` : ''}
            <div class="ss-review-row">
              <span class="ss-review-label">Evidence File:</span>
              <span class="ss-review-val">${data.attachmentName ? `📎 ${escapeHtml(data.attachmentName)}` : 'None attached'}</span>
            </div>
            <div class="ss-review-row">
              <span class="ss-review-label">Contact Update:</span>
              <span class="ss-review-val">${escapeHtml(data.contactPreference)}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function getCategoryFollowUpPrompt(category) {
    switch (category) {
      case 'Order and Delivery': return 'Was this an in-store order or home courier delivery?';
      case 'Product Quality or Defect': return 'What is the product brand name, batch code, or expiration date?';
      case 'Returns and Refunds': return 'Do you have the original store purchase receipt or return slip?';
      case 'Payment and Billing': return 'Did the self-pay register terminal print a receipt or error slip?';
      case 'Store Service': return 'Which specific aisle or department was affected?';
      case 'Staff Behaviour': return 'Which store counter or department did this occur in?';
      case 'Product Availability': return 'Which specific product brand or flavor was missing from shelves?';
      case 'Pricing or Offers': return 'What was the posted shelf price vs the scanned register price?';
      case 'Store Facilities': return 'Which facility area (restrooms, entrance, parking) requires maintenance?';
      default: return 'Any additional context for our operations investigation team:';
    }
  }

  function attachWizardStepEvents() {
    // Close & Cancel
    const closeWizard = () => { modalContainer.innerHTML = ''; };
    modalContainer.querySelector('#btn-close-wizard')?.addEventListener('click', closeWizard);
    modalContainer.querySelector('#btn-wizard-cancel')?.addEventListener('click', closeWizard);
    modalContainer.querySelector('#wizard-modal-backdrop')?.addEventListener('click', (e) => {
      if (e.target.id === 'wizard-modal-backdrop') closeWizard();
    });

    // Step 1 -> Step 2
    modalContainer.querySelector('#btn-wizard-next')?.addEventListener('click', () => {
      if (currentStep === 1) {
        const cat = modalContainer.querySelector('#wiz-category').value;
        const subj = modalContainer.querySelector('#wiz-subject').value.trim();
        const desc = modalContainer.querySelector('#wiz-description').value.trim();
        const orderNum = modalContainer.querySelector('#wiz-order-num').value.trim();
        const storeId = modalContainer.querySelector('#wiz-store').value;
        const incDate = modalContainer.querySelector('#wiz-date').value;

        if (!subj || subj.length < 3) {
          showToast('Please provide a subject (minimum 3 characters)', 'error');
          return;
        }
        if (!desc || desc.length < 10) {
          showToast('Please provide a detailed description (minimum 10 characters)', 'error');
          return;
        }

        wizardData.category = cat;
        wizardData.subject = subj;
        wizardData.description = desc;
        wizardData.orderNumber = orderNum;
        wizardData.storeId = storeId;
        wizardData.incidentDate = incDate;

        currentStep = 2;
        renderWizard();
      } else if (currentStep === 2) {
        const followup = modalContainer.querySelector('#wiz-followup')?.value.trim() || '';
        const prefEl = modalContainer.querySelector('input[name="contact-pref"]:checked');
        wizardData.categoryFollowUp = followup;
        if (prefEl) wizardData.contactPreference = prefEl.value;

        currentStep = 3;
        renderWizard();
      }
    });

    // Step Back
    modalContainer.querySelector('#btn-wizard-prev')?.addEventListener('click', () => {
      if (currentStep > 1) {
        currentStep--;
        renderWizard();
      }
    });

    // File Upload handling in Step 2
    if (currentStep === 2) {
      const dropzone = modalContainer.querySelector('#dropzone-evidence');
      const fileInput = modalContainer.querySelector('#file-attachment');
      const contentEl = modalContainer.querySelector('#dropzone-content');
      const previewEl = modalContainer.querySelector('#upload-preview');
      const filenameEl = modalContainer.querySelector('#preview-filename');
      const removeBtn = modalContainer.querySelector('#btn-remove-file');

      dropzone?.addEventListener('click', () => fileInput?.click());
      removeBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        wizardData.attachmentUrl = null;
        wizardData.attachmentName = null;
        if (fileInput) fileInput.value = '';
        if (previewEl) previewEl.style.display = 'none';
        if (contentEl) contentEl.style.display = 'block';
      });

      fileInput?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (file.size > 10 * 1024 * 1024) {
          showToast('File size exceeds the 10 MB limit', 'error');
          return;
        }

        showToast('Uploading file attachment...', 'info');
        try {
          const res = await api.uploadComplaintFile(file);
          wizardData.attachmentUrl = res.url;
          wizardData.attachmentName = res.name;
          if (filenameEl) filenameEl.textContent = res.name;
          if (contentEl) contentEl.style.display = 'none';
          if (previewEl) previewEl.style.display = 'flex';
          showToast('Evidence file attached successfully', 'success');
        } catch (err) {
          showToast(err.message || 'Error uploading file', 'error');
        }
      });
    }

    // Submit Final in Step 3
    modalContainer.querySelector('#btn-wizard-submit')?.addEventListener('click', async () => {
      const btnSubmit = modalContainer.querySelector('#btn-wizard-submit');
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = 'Submitting Complaint to Backend...';

      try {
        const payload = {
          category: wizardData.category,
          subject: wizardData.subject,
          description: wizardData.categoryFollowUp 
            ? `${wizardData.description}\n\n[Additional Context]: ${wizardData.categoryFollowUp}`
            : wizardData.description,
          orderNumber: wizardData.orderNumber || null,
          storeId: wizardData.storeId || null,
          attachmentUrl: wizardData.attachmentUrl,
          attachmentName: wizardData.attachmentName
        };

        const complaint = await api.submitComplaint(payload);
        showToast('Complaint logged successfully in Swift Service!', 'success');
        renderConfirmationScreen(complaint);
      } catch (err) {
        console.error('Complaint submission error:', err);
        showToast(err.message || 'Error submitting complaint', 'error');
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = '✓ Confirm & Submit Complaint';
      }
    });
  }

  function renderConfirmationScreen(complaint) {
    modalContainer.innerHTML = `
      <div class="rw-modal-backdrop">
        <div class="rw-modal" style="max-width: 520px; text-align: center;">
          <div class="rw-modal-body" style="padding: 2.5rem 1.5rem;">
            <div style="width: 64px; height: 64px; border-radius: 50%; background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 2rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem;">
              ✓
            </div>

            <h2 style="font-size: 1.4rem; font-weight: 800; color: #fff; margin-bottom: 0.5rem;">
              Complaint Submitted Successfully
            </h2>
            <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 1.5rem;">
              Your report has been logged directly into the authoritative Swift Service operational triage system.
            </p>

            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
              <div style="font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.35rem;">
                Official Reference Number
              </div>
              <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem;">
                <code style="font-size: 1.45rem; font-weight: 800; letter-spacing: 2px; color: #38bdf8; font-family: monospace;" id="conf-ref-num">
                  ${escapeHtml(complaint.referenceNumber)}
                </code>
                <button type="button" class="btn btn-secondary btn-sm" id="btn-copy-ref" title="Copy Reference to Clipboard">
                  📋 Copy
                </button>
              </div>
              <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.5rem;">
                Submitted at: ${new Date(complaint.createdAt).toLocaleString()}
              </div>
            </div>

            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <button class="btn btn-primary" id="btn-track-now" style="width: 100%; justify-content: center; padding: 0.75rem;">
                🔍 Track This Complaint Now
              </button>
              <button class="btn btn-secondary" id="btn-done-confirmation" style="width: 100%; justify-content: center;">
                Return to Customer Portal
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#btn-copy-ref')?.addEventListener('click', () => {
      navigator.clipboard.writeText(complaint.referenceNumber);
      showToast('Reference number copied to clipboard', 'info');
    });

    modalContainer.querySelector('#btn-track-now')?.addEventListener('click', () => {
      modalContainer.innerHTML = '';
      openTrackingTimelineModal(complaint.referenceNumber);
    });

    modalContainer.querySelector('#btn-done-confirmation')?.addEventListener('click', () => {
      modalContainer.innerHTML = '';
      // Refresh customer portal
      const appEl = document.getElementById('app');
      if (appEl) renderCustomerPortal(appEl);
    });
  }

  renderWizard();
}

/**
 * Complaint Details & Chronological Timeline Stepper Modal
 */
export async function openTrackingTimelineModal(referenceNumber) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="track-modal-backdrop">
      <div class="rw-modal ss-tracking-modal">
        <div class="rw-modal-header">
          <div>
            <h2 style="font-size: 1.25rem; font-weight: 700; color: #fff;">Complaint Status & Timeline</h2>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Tracking: ${escapeHtml(referenceNumber)}</div>
          </div>
          <button class="rw-btn-close" id="btn-close-track">✕</button>
        </div>
        <div class="rw-modal-body" id="track-modal-content">
          <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
            <div class="spinner" style="margin: 0 auto 1rem;"></div>
            Loading chronological status milestones...
          </div>
        </div>
      </div>
    </div>
  `;

  const closeTrackModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-track')?.addEventListener('click', closeTrackModal);
  modalContainer.querySelector('#track-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'track-modal-backdrop') closeTrackModal();
  });

  try {
    const complaint = await api.trackComplaint(referenceNumber);
    renderTrackingContent(modalContainer.querySelector('#track-modal-content'), complaint);
  } catch (err) {
    const contentEl = modalContainer.querySelector('#track-modal-content');
    if (contentEl) {
      contentEl.innerHTML = `
        <div class="ss-empty-box">
          <div class="ss-empty-icon">⚠️</div>
          <h3>Complaint Reference Not Found</h3>
          <p>We could not find any active complaint with reference <code>${escapeHtml(referenceNumber)}</code>.</p>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">
            Please check the reference number and try again. Format: <strong>REF-2026-XXXXX</strong>.
          </div>
        </div>
      `;
    }
  }
}

function renderTrackingContent(container, c) {
  const statusSteps = [
    { key: 'SUBMITTED', label: 'Submitted', desc: 'Complaint logged into Swift Service customer portal' },
    { key: 'UNDER_REVIEW', label: 'Under Review', desc: 'Assigned to store lead & triaged against operational baseline' },
    { key: 'IN_PROGRESS', label: 'In Progress', desc: 'Operational team dispatched for remediation or inspection' },
    { key: 'RESOLVED', label: 'Resolved', desc: 'Corrective action verified and customer summary published' },
    { key: 'CLOSED', label: 'Closed', desc: 'Incident closed and audited' }
  ];

  const statusOrder = ['SUBMITTED', 'UNDER_REVIEW', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];
  const currentIdx = statusOrder.indexOf(c.status);

  container.innerHTML = `
    <!-- Top Details Banner -->
    <div class="ss-track-summary-card">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <span class="ss-ref-badge" style="font-size: 0.95rem;">${escapeHtml(c.referenceNumber)}</span>
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-top: 0.35rem;">${escapeHtml(c.subject)}</h3>
        </div>
        <span class="ss-status-badge ${getStatusBadgeClass(c.status)}" style="font-size: 0.85rem; padding: 0.35rem 0.75rem;">
          ${escapeHtml(c.status.replace(/_/g, ' '))}
        </span>
      </div>

      <div class="ss-track-meta-row">
        <div><strong>Category:</strong> ${escapeHtml(c.category)}</div>
        ${c.storeName ? `<div><strong>Store:</strong> ${escapeHtml(c.storeName)}</div>` : ''}
        ${c.orderNumber ? `<div><strong>Order Ref:</strong> ${escapeHtml(c.orderNumber)}</div>` : ''}
        ${c.assignedTeamName ? `<div><strong>Responsible Team:</strong> ${escapeHtml(c.assignedTeamName)}</div>` : ''}
      </div>

      <div style="margin-top: 0.75rem; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5; background: rgba(0,0,0,0.25); padding: 0.75rem; border-radius: 6px;">
        <strong>Reported Issue:</strong> ${escapeHtml(c.description)}
      </div>

      ${c.attachmentName ? `
        <div style="margin-top: 0.75rem; font-size: 0.82rem; color: #38bdf8;">
          📎 Attached Evidence: <strong>${escapeHtml(c.attachmentName)}</strong>
        </div>
      ` : ''}
    </div>

    <!-- Official Resolution Box (When Available) -->
    ${c.resolutionSummary ? `
      <div class="ss-resolution-banner">
        <div style="font-weight: 700; color: #34d399; font-size: 0.92rem; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.4rem;">
          <span>✅</span> Official Swift Service Resolution Summary
        </div>
        <div style="font-size: 0.88rem; color: #e2e8f0; line-height: 1.5;">
          ${escapeHtml(c.resolutionSummary)}
        </div>
      </div>
    ` : ''}

    <!-- Chronological Stepper Progression -->
    <div style="margin-top: 2rem;">
      <h4 style="font-size: 0.95rem; font-weight: 700; color: #fff; margin-bottom: 1.25rem;">
        Chronological Operational Timeline
      </h4>

      <div class="ss-timeline-stepper">
        ${statusSteps.map((step, idx) => {
          const isDone = currentIdx >= idx;
          const isCurrent = currentIdx === idx;
          const stepClass = isDone ? 'completed' : '';
          const currentClass = isCurrent ? 'current' : '';

          // Look up matching milestone in timeline array
          const milestone = (c.timeline || []).find(t => t.status === step.key);

          return `
            <div class="ss-timeline-step ${stepClass} ${currentClass}">
              <div class="ss-timeline-node">
                <span class="ss-node-icon">${isDone ? '✓' : (idx + 1)}</span>
              </div>
              <div class="ss-timeline-details">
                <div class="ss-timeline-title-row">
                  <span class="ss-timeline-step-label">${step.label}</span>
                  ${milestone ? `
                    <span class="ss-timeline-time">${new Date(milestone.timestamp).toLocaleString()}</span>
                  ` : ''}
                </div>
                <div class="ss-timeline-step-desc">
                  ${milestone && milestone.note ? escapeHtml(milestone.note) : step.desc}
                </div>
                ${milestone && milestone.actor ? `
                  <div class="ss-timeline-actor">Logged by: ${escapeHtml(milestone.actor)}</div>
                ` : ''}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

/**
 * Customer Profile & Password Update Modal
 */
function openCustomerProfileModal() {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer || !state.user) return;

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="profile-modal-backdrop">
      <div class="rw-modal" style="max-width: 500px;">
        <div class="rw-modal-header">
          <div>
            <h2 style="font-size: 1.15rem; font-weight: 700; color: #fff;">Account Settings & Security</h2>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(state.user.email)}</div>
          </div>
          <button class="rw-btn-close" id="btn-close-profile">✕</button>
        </div>

        <div class="rw-modal-body">
          <form id="form-update-profile" style="display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.5rem;">
            <h4 style="font-size: 0.9rem; font-weight: 700; color: var(--accent-cyan);">Personal Information</h4>
            <div class="form-group">
              <label class="form-label" for="prof-fullname">Full Name</label>
              <input type="text" id="prof-fullname" class="form-input" value="${escapeHtml(state.user.fullName)}" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="prof-phone">Phone Number</label>
              <input type="tel" id="prof-phone" class="form-input" value="${escapeHtml(state.user.phone || '')}" placeholder="+1-555-019-2834" />
            </div>
            <button type="submit" class="btn btn-primary" id="btn-save-profile">
              Save Profile Changes
            </button>
          </form>

          <form id="form-change-password" style="display: flex; flex-direction: column; gap: 1rem; border-top: 1px solid var(--border-subtle); padding-top: 1.25rem;">
            <h4 style="font-size: 0.9rem; font-weight: 700; color: #f87171;">Update Password</h4>
            <div class="form-group">
              <label class="form-label" for="pwd-current">Current Password</label>
              <input type="password" id="pwd-current" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="pwd-new">New Password (Min 8 chars)</label>
              <input type="password" id="pwd-new" class="form-input" minlength="8" required />
            </div>
            <button type="submit" class="btn btn-secondary" id="btn-save-pwd">
              Update Password
            </button>
          </form>
        </div>
      </div>
    </div>
  `;

  const closeProfile = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-profile')?.addEventListener('click', closeProfile);
  modalContainer.querySelector('#profile-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'profile-modal-backdrop') closeProfile();
  });

  // Save Profile Info
  modalContainer.querySelector('#form-update-profile')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fullName = modalContainer.querySelector('#prof-fullname').value.trim();
    const phone = modalContainer.querySelector('#prof-phone').value.trim();
    const btn = modalContainer.querySelector('#btn-save-profile');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
      const res = await api.updateProfile({ fullName, phone });
      state.user = res;
      localStorage.setItem('r5_user', JSON.stringify(res));
      showToast('Profile updated successfully!', 'success');
      closeProfile();
      const appEl = document.getElementById('app');
      if (appEl) renderCustomerPortal(appEl);
    } catch (err) {
      showToast(err.message || 'Error updating profile', 'error');
      btn.disabled = false;
      btn.textContent = 'Save Profile Changes';
    }
  });

  // Change Password
  modalContainer.querySelector('#form-change-password')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const currentPassword = modalContainer.querySelector('#pwd-current').value;
    const newPassword = modalContainer.querySelector('#pwd-new').value;
    const btn = modalContainer.querySelector('#btn-save-pwd');
    btn.disabled = true;
    btn.textContent = 'Updating...';

    try {
      await api.changePassword(currentPassword, newPassword);
      showToast('Password updated successfully! Please sign in again with your new password.', 'success');
      state.setAuth(null, null);
      closeProfile();
      state.notify();
    } catch (err) {
      showToast(err.message || 'Error updating password', 'error');
      btn.disabled = false;
      btn.textContent = 'Update Password';
    }
  });
}

/**
 * Authorized Operational View: Customer Complaints Management
 * Embedded within Swift Service Operations Intelligence Portal
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
        <h1 class="view-title">Swift Service — Customer Complaints & Feedback Triage</h1>
        <p class="view-subtitle">Authoritative customer portal intake, root-cause team assignment, and verified SLA resolution.</p>
      </div>
      <div class="view-header-actions">
        <button class="btn btn-secondary" id="btn-preview-customer-portal">
          🛍️ Switch to Customer Portal
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
        <div class="stat-value" style="color: var(--p1-critical);" id="kpi-critical">${critical}</div>
        <div class="stat-subtext">Refrigeration, hazard, or safety</div>
      </div>
    </div>

    <!-- Complaints Management Panel -->
    <div class="r5-card">
      <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
        <div style="font-weight: 700; font-size: 1.05rem;">
          Customer Complaints Stream (${complaints.length})
        </div>
        <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;">
          <input type="text" id="filter-complaints-search" class="form-input" style="width: 220px; font-size: 0.85rem;" placeholder="Search reference, subject..." />
          <select id="filter-complaints-status" class="form-input" style="width: 140px; font-size: 0.85rem;">
            <option value="ALL">All Statuses</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>
      </div>

      <div class="r5-card-body" style="padding: 0; overflow-x: auto;">
        <table class="r5-table" id="table-staff-complaints">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Customer</th>
              <th>Category</th>
              <th>Subject</th>
              <th>Facility / Store</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Assigned Team</th>
              <th>Submitted</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="tbody-staff-complaints">
            ${renderStaffComplaintTableRows(complaints)}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Side Drawer for Investigation & Status Updates -->
    <div id="complaint-investigation-drawer" class="rw-drawer" style="display: none;">
      <!-- Populated dynamically -->
    </div>
  `;

  attachStaffComplaintsEvents(container, complaints, teams);
}

function renderStaffComplaintTableRows(complaints) {
  if (complaints.length === 0) {
    return `<tr><td colspan="10" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">No complaints match the selected filter criteria.</td></tr>`;
  }

  return complaints.map(c => `
    <tr>
      <td><span class="ss-ref-badge">${escapeHtml(c.referenceNumber)}</span></td>
      <td><strong>${escapeHtml(c.customerName)}</strong></td>
      <td><span class="ss-category-pill">${escapeHtml(c.category)}</span></td>
      <td style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(c.subject)}">
        ${escapeHtml(c.subject)}
      </td>
      <td>${escapeHtml(c.storeName || 'N/A')}</td>
      <td><span class="ss-status-badge ${getStatusBadgeClass(c.status)}">${escapeHtml(c.status.replace(/_/g, ' '))}</span></td>
      <td><span class="badge ${c.priority === 'CRITICAL' ? 'badge-p1' : (c.priority === 'HIGH' ? 'badge-p2' : 'badge-p3')}">${escapeHtml(c.priority)}</span></td>
      <td>${escapeHtml(c.assignedTeamName || 'Unassigned')}</td>
      <td>${new Date(c.createdAt).toLocaleDateString()}</td>
      <td>
        <button class="btn btn-secondary btn-sm btn-investigate-complaint" data-id="${c.id}">
          Investigate & Update
        </button>
      </td>
    </tr>
  `).join('');
}

function attachStaffComplaintsEvents(container, complaints, teams) {
  // Preview / Switch to customer portal
  container.querySelector('#btn-preview-customer-portal')?.addEventListener('click', () => {
    state.setPortalMode('CUSTOMER');
    showToast('Switched to Swift Service Customer Portal View', 'info');
  });

  // Search & Filter
  const searchInput = container.querySelector('#filter-complaints-search');
  const statusSelect = container.querySelector('#filter-complaints-status');
  const tbody = container.querySelector('#tbody-staff-complaints');

  const applyFilters = () => {
    const q = (searchInput?.value || '').toLowerCase();
    const st = statusSelect?.value || 'ALL';

    const filtered = complaints.filter(c => {
      const matchSearch = !q || 
        c.referenceNumber.toLowerCase().includes(q) ||
        c.subject.toLowerCase().includes(q) ||
        c.customerName.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q);
      const matchStatus = st === 'ALL' || c.status === st;
      return matchSearch && matchStatus;
    });

    if (tbody) tbody.innerHTML = renderStaffComplaintTableRows(filtered);

    // Reattach investigate buttons
    tbody?.querySelectorAll('.btn-investigate-complaint').forEach(b => {
      b.addEventListener('click', () => {
        const id = b.getAttribute('data-id');
        const c = complaints.find(item => item.id === id);
        if (c) openInvestigationDrawer(container, c, teams);
      });
    });
  };

  searchInput?.addEventListener('input', applyFilters);
  statusSelect?.addEventListener('change', applyFilters);

  // Attach investigate buttons initially
  tbody?.querySelectorAll('.btn-investigate-complaint').forEach(b => {
    b.addEventListener('click', () => {
      const id = b.getAttribute('data-id');
      const c = complaints.find(item => item.id === id);
      if (c) openInvestigationDrawer(container, c, teams);
    });
  });
}

function openInvestigationDrawer(container, c, teams) {
  const drawer = container.querySelector('#complaint-investigation-drawer');
  if (!drawer) return;

  drawer.style.display = 'block';
  drawer.innerHTML = `
    <div class="rw-drawer-backdrop" id="drawer-backdrop"></div>
    <div class="rw-drawer-panel">
      <div class="rw-drawer-header">
        <div>
          <span class="ss-ref-badge" style="font-size: 0.95rem;">${escapeHtml(c.referenceNumber)}</span>
          <h2 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-top: 0.25rem;">${escapeHtml(c.subject)}</h2>
        </div>
        <button class="rw-btn-close" id="btn-close-drawer">✕</button>
      </div>

      <div class="rw-drawer-body">
        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;">
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.25rem;">Original Customer Report</div>
          <div style="font-size: 0.88rem; color: #fff; line-height: 1.5; white-space: pre-wrap;">${escapeHtml(c.description)}</div>
          
          <div style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); display: flex; gap: 1rem; flex-wrap: wrap;">
            <span>👤 ${escapeHtml(c.customerName)}</span>
            <span>✉️ ${escapeHtml(c.customerEmail || 'Confidential')}</span>
            <span>🏢 ${escapeHtml(c.storeName || 'N/A')}</span>
          </div>

          ${c.attachmentName ? `
            <div style="margin-top: 0.75rem; font-size: 0.82rem; color: #38bdf8;">
              📎 Customer Attached Evidence: <strong>${escapeHtml(c.attachmentName)}</strong>
            </div>
          ` : ''}
        </div>

        <form id="form-investigate-update">
          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label" for="update-status">Operational Status Transition</label>
            <select id="update-status" class="form-input">
              <option value="SUBMITTED" ${c.status === 'SUBMITTED' ? 'selected' : ''}>SUBMITTED — In queue</option>
              <option value="UNDER_REVIEW" ${c.status === 'UNDER_REVIEW' ? 'selected' : ''}>UNDER_REVIEW — Reviewing evidence</option>
              <option value="IN_PROGRESS" ${c.status === 'IN_PROGRESS' ? 'selected' : ''}>IN_PROGRESS — Field team active</option>
              <option value="RESOLVED" ${c.status === 'RESOLVED' ? 'selected' : ''}>RESOLVED — Remediation complete</option>
              <option value="CLOSED" ${c.status === 'CLOSED' ? 'selected' : ''}>CLOSED — Audited & archived</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label" for="update-team">Assign Responsible Operational Team</label>
            <select id="update-team" class="form-input">
              <option value="">-- Leave Unassigned --</option>
              ${teams.map(t => `
                <option value="${t.id}" ${t.id === c.assignedTeamId ? 'selected' : ''}>${escapeHtml(t.name)}</option>
              `).join('')}
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label" for="update-internal-notes">Internal Investigation Notes (Private to Staff)</label>
            <textarea id="update-internal-notes" class="form-input rw-textarea" rows="3" placeholder="Record internal technician work orders, equipment tags, or cross-store coordination...">${escapeHtml(c.investigationNotes || '')}</textarea>
            <div class="form-help-text">Internal notes are strictly restricted from public customer tracking views.</div>
          </div>

          <div class="form-group" style="margin-bottom: 1.5rem;">
            <label class="form-label" for="update-resolution-summary">Customer-Facing Resolution Note (Published to Customer)</label>
            <textarea id="update-resolution-summary" class="form-input rw-textarea" rows="3" placeholder="Explain the resolution or corrective action taken to the customer...">${escapeHtml(c.resolutionSummary || '')}</textarea>
            <div class="form-help-text">This explanation appears directly in the customer's chronological status timeline.</div>
          </div>

          <div style="display: flex; gap: 0.75rem;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-drawer" style="flex: 1;">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-save-investigation" style="flex: 2;">
              Save Operational Updates
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeDrawer = () => { drawer.style.display = 'none'; };
  drawer.querySelector('#btn-close-drawer')?.addEventListener('click', closeDrawer);
  drawer.querySelector('#btn-cancel-drawer')?.addEventListener('click', closeDrawer);
  drawer.querySelector('#drawer-backdrop')?.addEventListener('click', closeDrawer);

  drawer.querySelector('#form-investigate-update')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = drawer.querySelector('#btn-save-investigation');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Saving Changes...';

    const status = drawer.querySelector('#update-status').value;
    const assignedTeamId = drawer.querySelector('#update-team').value || null;
    const investigationNotes = drawer.querySelector('#update-internal-notes').value.trim() || null;
    const resolutionSummary = drawer.querySelector('#update-resolution-summary').value.trim() || null;

    try {
      await api.updateComplaintStatus(c.id, {
        status,
        assignedTeamId,
        investigationNotes,
        resolutionSummary
      });

      showToast('Operational status and investigation notes saved!', 'success');
      closeDrawer();
      const ws = document.getElementById('view-workspace');
      if (ws) renderCustomerComplaintsView(ws);
    } catch (err) {
      showToast(err.message || 'Error updating complaint', 'error');
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Save Operational Updates';
    }
  });
}
