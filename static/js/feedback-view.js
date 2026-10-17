/**
 * R5 Operational Intelligence Platform - Feedback Ingestion View Controller
 * Phase 3 Implementation: Multichannel Feed, 3-Stage Lifecycle Inspector,
 * Pluggable Ingestion Form, and Bulk Import (JSON & CSV).
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import {
  escapeHtml,
  renderEmptyStateHtml,
  renderSkeletonCardsHtml,
  renderSkeletonTableHtml,
  renderErrorStateHtml
} from './ui-utils.js';

// Modal Helpers
function openModal(contentHtml) {
  const el = document.getElementById('modal-container');
  if (el) {
    el.innerHTML = `
      <div class="modal-backdrop">
        <div class="modal-content" style="max-width: 720px;">
          ${contentHtml}
        </div>
      </div>
    `;
  }
}

function closeModal() {
  const el = document.getElementById('modal-container');
  if (el) el.innerHTML = '';
}

let activeChannelFilter = '';
let activeStatusFilter = '';
let activeSubmitterFilter = '';
let activeLanguageFilter = '';
let feedbackSearchQuery = '';

export async function renderFeedbackView(container) {
  container.innerHTML = `
    <div style="margin-bottom: 1.25rem;">
      ${renderSkeletonCardsHtml(5)}
    </div>
    ${renderSkeletonTableHtml(6, 8)}
  `;

  try {
    const feedbackList = await api.getFeedback({
      storeId: state.selectedStoreId || undefined,
      channelType: activeChannelFilter || undefined,
      processingStatus: activeStatusFilter || undefined,
      submitterType: activeSubmitterFilter || undefined,
      languageCode: activeLanguageFilter || undefined,
      q: feedbackSearchQuery || undefined,
      limit: 100
    });

    const items = Array.isArray(feedbackList) ? feedbackList : (feedbackList?.items || []);

    // Summary Statistics
    const totalCount = items.length;
    const analyzedCount = items.filter(f => f.processingStatus === 'analyzed' || f.processingStatus === 'reviewed').length;
    const duplicateCount = items.filter(f => f.isDuplicate).length;
    const piiCount = items.filter(f => f.hasPii).length;
    const reviewedCount = items.filter(f => f.processingStatus === 'reviewed').length;

    container.innerHTML = `
      <!-- Synthetic Demo Data Disclaimer Banner -->
      <div class="demo-seed-banner">
        <span style="font-weight: 700; color: #f59e0b;">DEMO / SEED DATA</span> &mdash;
        Multichannel feedback stream captures raw operational human inputs across customer, employee, and maintenance channels for evaluation.
      </div>

      <!-- Top KPI Stats Row -->
      <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 1.25rem;">
        <div class="kpi-card">
          <div class="kpi-card-header">
            <span>Total Ingested</span>
            <span>📥</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${totalCount}</span>
            <span class="kpi-trend neutral">Raw Inputs</span>
          </div>
        </div>

        <div class="kpi-card highlight">
          <div class="kpi-card-header">
            <span>AI Analyzed</span>
            <span>⚡</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${analyzedCount}</span>
            <span class="kpi-trend positive">3-Stage Ready</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-card-header">
            <span>Flagged Duplicates</span>
            <span>🛡️</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${duplicateCount}</span>
            <span class="kpi-trend neutral">SHA-256 Deduplicated</span>
          </div>
        </div>

        <div class="kpi-card critical">
          <div class="kpi-card-header">
            <span>PII Scrubbed</span>
            <span>🔒</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${piiCount}</span>
            <span class="kpi-trend" style="color: var(--p1-critical);">Restricted Privacy</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-card-header">
            <span>Manager Reviewed</span>
            <span>✅</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${reviewedCount}</span>
            <span class="kpi-trend positive">Triaged</span>
          </div>
        </div>
      </div>

      <!-- Main Ingestion Console Card -->
      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>📥</span>
            <span>Multichannel Frontline Human Feedback Stream (${totalCount})</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <button id="btn-open-multilingual-inspector" class="btn btn-secondary btn-sm" style="border: 1px solid var(--accent-cyan); color: #38bdf8;">
              🌐 Multilingual AI Inspector & Benchmark
            </button>
            <button id="btn-open-single-ingest" class="btn btn-primary btn-sm">+ Ingest Feedback</button>
            <button id="btn-open-bulk-ingest" class="btn btn-secondary btn-sm">📁 Bulk CSV / JSON</button>
          </div>
        </div>

        <!-- Filter Toolbar -->
        <div style="padding: 0.85rem 1.25rem; background-color: rgba(17, 24, 39, 0.4); border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
          <input type="text" id="fb-search-input" class="form-input" style="padding: 0.4rem 0.75rem; font-size: 0.82rem; width: 170px;" placeholder="Search text..." value="${feedbackSearchQuery}" />
          
          <select id="fb-filter-channel" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
            <option value="">All Channels</option>
            <option value="MANUAL_ENTRY" ${activeChannelFilter === 'MANUAL_ENTRY' ? 'selected' : ''}>Manual Entry</option>
            <option value="CUSTOMER_COMPLAINT" ${activeChannelFilter === 'CUSTOMER_COMPLAINT' ? 'selected' : ''}>Customer Complaint</option>
            <option value="EMPLOYEE_FEEDBACK" ${activeChannelFilter === 'EMPLOYEE_FEEDBACK' ? 'selected' : ''}>Employee Feedback</option>
            <option value="MAINTENANCE_REPORT" ${activeChannelFilter === 'MAINTENANCE_REPORT' ? 'selected' : ''}>Maintenance Report</option>
            <option value="SURVEY_RESPONSE" ${activeChannelFilter === 'SURVEY_RESPONSE' ? 'selected' : ''}>Survey Response</option>
            <option value="OPERATIONAL_NOTE" ${activeChannelFilter === 'OPERATIONAL_NOTE' ? 'selected' : ''}>Operational Note</option>
            <option value="BULK_IMPORT" ${activeChannelFilter === 'BULK_IMPORT' ? 'selected' : ''}>Bulk Import</option>
            <option value="QR_KIOSK" ${activeChannelFilter === 'QR_KIOSK' ? 'selected' : ''}>QR Kiosk</option>
          </select>

          <select id="fb-filter-status" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
            <option value="">All Processing States</option>
            <option value="received" ${activeStatusFilter === 'received' ? 'selected' : ''}>Received</option>
            <option value="validating" ${activeStatusFilter === 'validating' ? 'selected' : ''}>Validating</option>
            <option value="processing" ${activeStatusFilter === 'processing' ? 'selected' : ''}>Processing</option>
            <option value="analyzed" ${activeStatusFilter === 'analyzed' ? 'selected' : ''}>Analyzed</option>
            <option value="reviewed" ${activeStatusFilter === 'reviewed' ? 'selected' : ''}>Reviewed</option>
            <option value="failed" ${activeStatusFilter === 'failed' ? 'selected' : ''}>Failed</option>
          </select>

          <select id="fb-filter-submitter" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
            <option value="">All Submitters</option>
            <option value="CUSTOMER" ${activeSubmitterFilter === 'CUSTOMER' ? 'selected' : ''}>Customer</option>
            <option value="EMPLOYEE" ${activeSubmitterFilter === 'EMPLOYEE' ? 'selected' : ''}>Employee</option>
            <option value="MAINTENANCE_TECH" ${activeSubmitterFilter === 'MAINTENANCE_TECH' ? 'selected' : ''}>Technician</option>
            <option value="STORE_ASSOCIATE" ${activeSubmitterFilter === 'STORE_ASSOCIATE' ? 'selected' : ''}>Associate</option>
            <option value="STORE_MANAGER" ${activeSubmitterFilter === 'STORE_MANAGER' ? 'selected' : ''}>Store Manager</option>
          </select>

          <select id="fb-filter-lang" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
            <option value="">All Languages</option>
            <option value="en" ${activeLanguageFilter === 'en' ? 'selected' : ''}>English (en)</option>
            <option value="es" ${activeLanguageFilter === 'es' ? 'selected' : ''}>Spanish (es)</option>
            <option value="fr" ${activeLanguageFilter === 'fr' ? 'selected' : ''}>French (fr)</option>
            <option value="de" ${activeLanguageFilter === 'de' ? 'selected' : ''}>German (de)</option>
            <option value="hi" ${activeLanguageFilter === 'hi' ? 'selected' : ''}>Hindi (hi)</option>
            <option value="ta" ${activeLanguageFilter === 'ta' ? 'selected' : ''}>Tamil (ta)</option>
            <option value="te" ${activeLanguageFilter === 'te' ? 'selected' : ''}>Telugu (te)</option>
            <option value="hi-Latn" ${activeLanguageFilter === 'hi-Latn' ? 'selected' : ''}>Hinglish (hi-Latn)</option>
            <option value="ta-Latn" ${activeLanguageFilter === 'ta-Latn' ? 'selected' : ''}>Tanglish (ta-Latn)</option>
          </select>

          ${(activeChannelFilter || activeStatusFilter || activeSubmitterFilter || activeLanguageFilter || feedbackSearchQuery) ? `
            <button id="btn-clear-filters" class="btn btn-secondary btn-sm" style="font-size: 0.78rem;">Clear Filters</button>
          ` : ''}
        </div>

        <!-- Table Stream -->
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Time & Origin</th>
                <th>Channel & Submitter</th>
                <th>Detected Language</th>
                <th>Original Text (Preserved)</th>
                <th>Normalized Interpretation</th>
                <th>Extracted Issue</th>
                <th>Confidence & State</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${items.length === 0 ? `
                <tr>
                  <td colspan="8" style="padding: 1.5rem;">
                    ${renderEmptyStateHtml({
                      icon: '📥',
                      title: 'No feedback records found',
                      desc: 'No operational inputs match the selected channel, status, submitter role, or search query.',
                      actionLabel: 'Reset All Filters',
                      actionId: 'btn-empty-clear-filters'
                    })}
                  </td>
                </tr>
              ` : ''}
              ${items.map(fb => {
                const intentLabel = ai.detectedIntent ? ai.detectedIntent.replace(/_/g, ' ') : 'GENERAL';
                const procStatusClass = `badge-${fb.processingStatus || 'analyzed'}`;
                const langInfo = fb.detectedLanguageInfo || ai.detectedLanguage || { code: fb.languageCode || 'en', name: fb.languageCode || 'English' };
                const extracted = fb.extractedIssue || ai.extractedIssue || {};
                const cat = extracted.category || (ai.issueCategory ? ai.issueCategory.value : intentLabel);
                const itype = extracted.issueType || (ai.issueType ? ai.issueType.value : '');
                const isSafety = extracted.isSafetyHazard || (ai.safetyRelevance && ai.safetyRelevance.value !== 'NON_HAZARD');
                const confVal = Math.round(((fb.multilingualConfidence || ai.confidence || ai.overallConfidence || 0.85)) * 100);
                const confColor = confVal >= 85 ? '#34d399' : confVal >= 70 ? '#fbbf24' : '#f87171';

                return `
                  <tr>
                    <td>
                      <div class="table-id-mono" style="font-size: 0.75rem; color: #fff;">${new Date(fb.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                      <div style="font-size: 0.72rem; color: var(--text-muted);">${new Date(fb.createdAt).toLocaleDateString()}</div>
                      <div style="font-size: 0.7rem; color: var(--accent-cyan); margin-top: 2px;">${fb.storeName ? '#' + fb.storeName : 'Store #104'}</div>
                    </td>
                    <td>
                      <span class="badge badge-neutral" style="font-size: 0.7rem;">${(fb.channelType || fb.sourceType || 'MANUAL').replace(/_/g, ' ')}</span>
                      <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 3px;">
                        By: <strong>${(fb.submitterType || 'CUSTOMER').replace(/_/g, ' ')}</strong>
                      </div>
                    </td>
                    <td>
                      <div style="display: flex; flex-direction: column; gap: 2px;">
                        <span class="badge badge-neutral" style="font-family: var(--font-family-mono); font-weight: 700; font-size: 0.72rem; align-self: flex-start;">
                          ${(langInfo.code || fb.languageCode || 'en').toUpperCase()}
                        </span>
                        <div style="font-size: 0.72rem; color: #fff; font-weight: 500;">
                          ${langInfo.name || (fb.languageCode === 'hi' ? 'Hindi' : 'English')}
                        </div>
                        ${langInfo.isTransliterated ? `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; font-size: 0.65rem; align-self: flex-start;">Transliterated</span>` : ''}
                        ${langInfo.isCodeMixed ? `<span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-size: 0.65rem; align-self: flex-start;">Code-Mixed</span>` : ''}
                      </div>
                    </td>
                    <td style="max-width: 250px;">
                      <div style="color: #fff; font-weight: 500; font-size: 0.85rem; line-height: 1.35; word-break: break-word;">
                        "${fb.rawText}"
                      </div>
                      <div style="font-size: 0.65rem; color: #818cf8; margin-top: 3px; font-weight: 600;">
                        IMMUTABLE VERBATIM INPUT
                      </div>
                    </td>
                    <td style="max-width: 250px;">
                      <div style="font-size: 0.82rem; color: #a5f3fc; line-height: 1.3; background: rgba(6, 182, 212, 0.08); padding: 5px 8px; border-radius: 4px; border-left: 2px solid #22d3ee; word-break: break-word;">
                        "${fb.normalizedInterpretation || fb.normalizedText || fb.rawText}"
                      </div>
                      ${fb.spellingCorrections && Object.keys(fb.spellingCorrections).length > 0 ? `
                        <div style="font-size: 0.68rem; color: #fbbf24; margin-top: 3px;">
                          Typos: ${Object.entries(fb.spellingCorrections).map(([k, v]) => `<code>${k}→${v}</code>`).join(', ')}
                        </div>
                      ` : ''}
                    </td>
                    <td>
                      <div style="display: flex; flex-direction: column; gap: 3px;">
                        <span class="badge badge-p4" style="font-size: 0.7rem; align-self: flex-start;">
                          ${(cat || 'GENERAL').replace(/_/g, ' ')}
                        </span>
                        ${itype && itype !== 'unknown' ? `
                          <div style="font-size: 0.72rem; color: #fff; font-weight: 600;">
                            ${itype.replace(/_/g, ' ')}
                          </div>
                        ` : ''}
                        ${isSafety ? `
                          <span class="badge badge-p1" style="font-size: 0.65rem; align-self: flex-start; margin-top: 2px;">
                            ⚠️ SAFETY HAZARD
                          </span>
                        ` : ''}
                      </div>
                    </td>
                    <td>
                      <div>
                        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.72rem; margin-bottom: 2px;">
                          <span style="color: var(--text-muted);">Confidence</span>
                          <strong style="color: ${confColor}; font-family: var(--font-family-mono);">${confVal}%</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.1); height: 4px; border-radius: 2px; overflow: hidden; width: 75px;">
                          <div style="background: ${confColor}; height: 100%; width: ${confVal}%;"></div>
                        </div>
                        <div style="margin-top: 5px;">
                          <span class="badge ${procStatusClass}" style="text-transform: uppercase; font-size: 0.68rem; font-weight: 700;">
                            ${fb.processingStatus || 'analyzed'}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td style="text-align: right;">
                      <div style="display: inline-flex; gap: 0.35rem;">
                        <button class="btn btn-secondary btn-sm btn-inspect-lifecycle" data-id="${fb.id}" title="Inspect 5-Stage Multilingual Intelligence Lifecycle">
                          🔍 Inspect
                        </button>
                        <button class="btn btn-primary btn-sm btn-review-feedback" data-id="${fb.id}" data-status="${fb.processingStatus || 'analyzed'}" data-life="${fb.status || 'NEW'}">
                          Review
                        </button>
                      </div>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Attach Event Handlers
    container.querySelector('#fb-search-input')?.addEventListener('change', (e) => {
      feedbackSearchQuery = e.target.value.trim();
      renderFeedbackView(container);
    });

    container.querySelector('#fb-filter-channel')?.addEventListener('change', (e) => {
      activeChannelFilter = e.target.value;
      renderFeedbackView(container);
    });

    container.querySelector('#fb-filter-status')?.addEventListener('change', (e) => {
      activeStatusFilter = e.target.value;
      renderFeedbackView(container);
    });

    container.querySelector('#fb-filter-submitter')?.addEventListener('change', (e) => {
      activeSubmitterFilter = e.target.value;
      renderFeedbackView(container);
    });

    container.querySelector('#fb-filter-lang')?.addEventListener('change', (e) => {
      activeLanguageFilter = e.target.value;
      renderFeedbackView(container);
    });

    const resetFilters = () => {
      activeChannelFilter = '';
      activeStatusFilter = '';
      activeSubmitterFilter = '';
      activeLanguageFilter = '';
      feedbackSearchQuery = '';
      renderFeedbackView(container);
    };

    container.querySelector('#btn-clear-filters')?.addEventListener('click', resetFilters);
    container.querySelector('#btn-empty-clear-filters')?.addEventListener('click', resetFilters);

    container.querySelector('#btn-open-multilingual-inspector')?.addEventListener('click', () => {
      openMultilingualInspectorModal(() => renderFeedbackView(container));
    });

    container.querySelector('#btn-open-single-ingest')?.addEventListener('click', () => {
      openSubmitFeedbackModal(() => renderFeedbackView(container));
    });

    container.querySelector('#btn-open-bulk-ingest')?.addEventListener('click', () => {
      openBulkImportModal(() => renderFeedbackView(container));
    });

    container.querySelectorAll('.btn-inspect-lifecycle').forEach(btn => {
      btn.addEventListener('click', () => {
        openFeedbackLifecycleModal(btn.getAttribute('data-id'), () => renderFeedbackView(container));
      });
    });

    container.querySelectorAll('.btn-review-feedback').forEach(btn => {
      btn.addEventListener('click', () => {
        openReviewFeedbackModal(
          btn.getAttribute('data-id'),
          btn.getAttribute('data-status'),
          btn.getAttribute('data-life'),
          () => renderFeedbackView(container)
        );
      });
    });

  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Feedback Ingestion Stream Unavailable',
      message: err.message || 'Unable to connect to operational feedback service.',
      onRetryId: 'btn-retry-feedback'
    });
    container.querySelector('#btn-retry-feedback')?.addEventListener('click', () => {
      renderFeedbackView(container);
    });
  }
}

/* =========================================================================
   MODAL 1: SINGLE MULTICHANNEL INGESTION FORM
   ========================================================================= */
export function openSubmitFeedbackModal(onSuccess) {
  openModal(`
    <div class="modal-header">
      <div>
        <h3 style="font-size: 1.15rem; font-weight: 700;">Ingest Multichannel Operational Feedback</h3>
        <div style="font-size: 0.8rem; color: var(--text-muted);">Transform raw frontline input into structured operational telemetry</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-submit-feedback">
      <div class="modal-body">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Ingestion Channel</label>
            <select id="fb-in-channel" class="form-select" required>
              <option value="MANUAL_ENTRY">Manual Entry (Frontline)</option>
              <option value="CUSTOMER_COMPLAINT">Customer Complaint (Guest Desk)</option>
              <option value="EMPLOYEE_FEEDBACK">Employee Feedback (Floor Staff)</option>
              <option value="MAINTENANCE_REPORT">Maintenance Report (Technician)</option>
              <option value="SURVEY_RESPONSE">Survey Response (NPS / CSAT)</option>
              <option value="OPERATIONAL_NOTE">Operational Note (Shift Log)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Submitter Role</label>
            <select id="fb-in-submitter" class="form-select" required>
              <option value="CUSTOMER">Customer</option>
              <option value="EMPLOYEE">Store Employee</option>
              <option value="MAINTENANCE_TECH">Maintenance Technician</option>
              <option value="STORE_ASSOCIATE">Store Associate</option>
              <option value="STORE_MANAGER">Store Manager</option>
              <option value="ANONYMOUS">Anonymous</option>
              <option value="VENDOR">Vendor / Contractor</option>
            </select>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Language Mode</label>
            <select id="fb-in-lang" class="form-select">
              <option value="auto">Auto-Detect Language</option>
              <option value="en">English (en)</option>
              <option value="es">Spanish (es)</option>
              <option value="fr">French (fr)</option>
              <option value="de">German (de)</option>
              <option value="hi">Hindi (hi)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Privacy Classification</label>
            <select id="fb-in-privacy" class="form-select">
              <option value="INTERNAL">Internal</option>
              <option value="CONFIDENTIAL">Confidential</option>
              <option value="PUBLIC">Public</option>
              <option value="RESTRICTED_PII">Restricted PII</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <label class="form-label">Verbatim Raw Human Feedback Text (Never Mutated)</label>
            <div style="display: flex; gap: 0.35rem;">
              <button type="button" class="btn btn-secondary btn-sm btn-quick-sample" data-text="El estante de leche en el pasillo 4 se siente tibio y hay agua estancada goteando en el piso." style="font-size: 0.68rem; padding: 2px 6px;">Sample (ES)</button>
              <button type="button" class="btn btn-secondary btn-sm btn-quick-sample" data-text="Le congelateur du rayon bio fait un bruit inhabituel et fuit sur le sol." style="font-size: 0.68rem; padding: 2px 6px;">Sample (FR)</button>
              <button type="button" class="btn btn-secondary btn-sm btn-quick-sample" data-text="Scanner on self checkout lane 3 keeps freezing on barcode scan." style="font-size: 0.68rem; padding: 2px 6px;">Sample (POS)</button>
            </div>
          </div>
          <textarea id="fb-in-text" class="form-textarea" required minlength="3" style="min-height: 100px;" placeholder="Enter verbatim customer, employee, or technician feedback..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Execute Ingestion Pipeline</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.querySelectorAll('.btn-quick-sample').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('fb-in-text').value = btn.getAttribute('data-text');
    });
  });

  document.getElementById('form-submit-feedback').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const payload = {
        storeId: state.selectedStoreId,
        channelType: document.getElementById('fb-in-channel').value,
        submitterType: document.getElementById('fb-in-submitter').value,
        languageCode: document.getElementById('fb-in-lang').value,
        privacyClassification: document.getElementById('fb-in-privacy').value,
        rawText: document.getElementById('fb-in-text').value.trim()
      };
      const res = await api.submitFeedback(payload);
      showToast(`Feedback ingested as ${res.channelType} (${res.processingStatus}).`, 'success');
      closeModal();
      if (onSuccess) onSuccess();
    } catch (err) {}
  });
}

/* =========================================================================
   MODAL 2: BULK CSV & JSON INGESTION MODAL
   ========================================================================= */
let bulkActiveTab = 'json'; // 'json' | 'csv'

export function openBulkImportModal(onSuccess) {
  const jsonSample = JSON.stringify([
    {
      "channelType": "CUSTOMER_COMPLAINT",
      "submitterType": "CUSTOMER",
      "languageCode": "en",
      "rawText": "Milk jugs in cooler 4B feel warm and thermometer shows 48 degrees F."
    },
    {
      "channelType": "MAINTENANCE_REPORT",
      "submitterType": "MAINTENANCE_TECH",
      "languageCode": "en",
      "rawText": "Routine walk: Condenser drain line partially clogged with condensation overflow."
    },
    {
      "channelType": "EMPLOYEE_FEEDBACK",
      "submitterType": "STORE_ASSOCIATE",
      "languageCode": "es",
      "rawText": "Charco grande de agua resbaladizo en pasillo 4 cerca de los lacteos."
    }
  ], null, 2);

  const csvSample = `rawText,channelType,submitterType,languageCode
Milk jugs in cooler 4B feel warm and thermometer shows 48 degrees F,CUSTOMER_COMPLAINT,CUSTOMER,en
Routine walk: Condenser drain line partially clogged with condensation overflow,MAINTENANCE_REPORT,MAINTENANCE_TECH,en
Charco grande de agua resbaladizo en pasillo 4 cerca de los lacteos,EMPLOYEE_FEEDBACK,STORE_ASSOCIATE,es`;

  openModal(`
    <div class="modal-header">
      <div>
        <h3 style="font-size: 1.15rem; font-weight: 700;">Bulk Operational Feedback Import</h3>
        <div style="font-size: 0.8rem; color: var(--text-muted);">Batch ingestion supporting JSON arrays and CSV payloads</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <div class="modal-body">
      <!-- Format Tabs -->
      <div class="tabs-nav" style="margin-bottom: 0.85rem;">
        <button class="tab-btn ${bulkActiveTab === 'json' ? 'active' : ''}" id="tab-bulk-json">JSON Array Format</button>
        <button class="tab-btn ${bulkActiveTab === 'csv' ? 'active' : ''}" id="tab-bulk-csv">CSV Text Format</button>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
        <label class="form-label" style="margin: 0;">Payload Content</label>
        <button type="button" class="btn btn-secondary btn-sm" id="btn-load-sample" style="font-size: 0.72rem; padding: 2px 8px;">
          📋 Load Sample Batch
        </button>
      </div>

      <textarea id="bulk-content-input" class="form-textarea" style="font-family: var(--font-family-mono); font-size: 0.82rem; min-height: 180px;" required>${bulkActiveTab === 'json' ? jsonSample : csvSample}</textarea>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
      <button type="button" class="btn btn-primary" id="btn-execute-bulk">Import Batch</button>
    </div>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('tab-bulk-json').addEventListener('click', () => {
    bulkActiveTab = 'json';
    openBulkImportModal(onSuccess);
  });

  document.getElementById('tab-bulk-csv').addEventListener('click', () => {
    bulkActiveTab = 'csv';
    openBulkImportModal(onSuccess);
  });

  document.getElementById('btn-load-sample').addEventListener('click', () => {
    document.getElementById('bulk-content-input').value = bulkActiveTab === 'json' ? jsonSample : csvSample;
  });

  document.getElementById('btn-execute-bulk').addEventListener('click', async () => {
    const content = document.getElementById('bulk-content-input').value.trim();
    if (!content) return;

    try {
      let res;
      if (bulkActiveTab === 'json') {
        const parsed = JSON.parse(content);
        const items = Array.isArray(parsed) ? parsed : (parsed.items || []);
        // Inject active store if not provided
        items.forEach(i => {
          if (!i.storeId) i.storeId = state.selectedStoreId;
        });
        res = await api.submitBulkFeedbackJson({ items });
      } else {
        res = await api.submitBulkFeedbackCsv(content, state.selectedStoreId);
      }

      showToast(`Bulk Import complete: ${res.succeeded} ingested, ${res.duplicatesDetected} duplicates, ${res.failed} errors.`, res.failed > 0 ? 'info' : 'success');
      closeModal();
      if (onSuccess) onSuccess();
    } catch (err) {
      showToast('Bulk import error: ' + err.message, 'error');
    }
  });
}

/* =========================================================================
   MODAL 3: PHASE 4 OPERATIONAL INTELLIGENCE & GROUNDED LIFECYCLE INSPECTOR
   ========================================================================= */
export async function openFeedbackLifecycleModal(feedbackId, onSuccess) {
  try {
    const decomp = await api.getFeedbackUnderstanding(feedbackId);
    const fb = await api.getFeedbackById(feedbackId);
    const sys = decomp.systemFacts || {};
    const ai = decomp.aiDerivedFacts || {};
    const humanOv = decomp.humanOverrides || {};
    const eff = decomp.effectiveInterpretation || {};
    const effFields = eff.effectiveFields || {};

    const overallConf = (ai.overallConfidence !== undefined ? (ai.overallConfidence * 100).toFixed(0) : '0');
    const confClass = overallConf >= 80 ? 'confidence-bar-high' : overallConf >= 50 ? 'confidence-bar-med' : 'confidence-bar-low';

    // Helper to render an individual grounded field card
    const renderFieldCard = (key, label) => {
      const f = effFields[key] || { value: 'unknown', confidence: 0, evidence: null, uncertainty: true, uncertaintyReason: 'Not extracted' };
      const val = f.value || 'unknown';
      const isUnknown = val === 'unknown';
      const confPct = Math.round((f.confidence || 0) * 100);
      const confBarClass = confPct >= 80 ? 'confidence-bar-high' : confPct >= 50 ? 'confidence-bar-med' : 'confidence-bar-low';

      return `
        <div class="field-card" style="${f.isOverridden ? 'border-color: rgba(245, 158, 11, 0.4); background-color: rgba(245, 158, 11, 0.05);' : ''}">
          <div>
            <div class="field-card-header">
              <span class="field-card-label">${label}</span>
              <div style="display: flex; align-items: center; gap: 0.35rem;">
                ${f.isOverridden ? `<span class="override-pill" title="Original AI: ${f.originalAiValue} (${Math.round(f.originalAiConfidence * 100)}%)">✎ Human Override</span>` : ''}
                <span style="font-size: 0.72rem; font-family: var(--font-family-mono); font-weight: 700; color: ${isUnknown ? 'var(--text-muted)' : 'var(--text-primary)'};">
                  ${confPct}%
                </span>
              </div>
            </div>

            <div class="field-card-value" style="color: ${isUnknown ? 'var(--text-muted)' : (f.isOverridden ? '#fbbf24' : '#fff')};">
              ${val.toString().replace(/_/g, ' ')}
            </div>

            ${f.evidence ? `
              <div class="field-card-evidence" title="Source text coordinates [${f.evidence.start}:${f.evidence.end}]">
                <span>❝</span>
                <span>${f.evidence.text}</span>
                <span style="opacity: 0.6; font-size: 0.65rem; font-family: var(--font-family-mono); margin-left: auto;">[${f.evidence.start}:${f.evidence.end}]</span>
              </div>
            ` : ''}

            ${f.uncertainty ? `
              <div class="field-card-uncertainty">
                ⚠️ ${f.uncertaintyReason || 'Uncertain or data missing from feedback text'}
              </div>
            ` : ''}

            ${f.isOverridden && f.overrideReason ? `
              <div style="font-size: 0.72rem; color: #fbbf24; margin-top: 0.35rem; font-style: italic;">
                Reason: "${f.overrideReason}"
              </div>
            ` : ''}
          </div>

          <div class="confidence-bar-wrap">
            <div class="confidence-bar-fill ${confBarClass}" style="width: ${confPct}%;"></div>
          </div>
        </div>
      `;
    };

    openModal(`
      <div class="modal-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <h3 style="font-size: 1.15rem; font-weight: 700;">Grounded Operational Feedback Inspector</h3>
            <span class="badge badge-${fb.processingStatus || 'analyzed'}">${(fb.processingStatus || 'analyzed').toUpperCase()}</span>
            ${humanOv.reviewedAt ? `<span class="override-pill">✓ Human Reviewed by ${humanOv.reviewedBy || 'Manager'}</span>` : ''}
          </div>
          <div style="display: flex; align-items: center; gap: 1rem; margin-top: 3px; font-size: 0.75rem; color: var(--text-muted);">
            <span>ID: <code class="table-id-mono">${fb.id}</code></span>
            <span>Origin Store: <strong>#${sys.storeName || '104'}</strong></span>
            <span>Overall Grounded Confidence: <strong style="color: #34d399;">${overallConf}%</strong></span>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>

      <div class="modal-body" style="max-height: 75vh; overflow-y: auto;">
        <div class="lifecycle-grid">

          <!-- STAGE 1: VERBATIM RAW INPUT -->
          <div class="lifecycle-panel tier-raw">
            <div class="lifecycle-panel-title">
              <span style="font-weight: 700; color: #818cf8; font-size: 0.85rem;">STAGE 1: VERBATIM RAW INPUT (NEVER OVERWRITTEN)</span>
              <span class="lifecycle-badge" style="background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3);">
                IMMUTABLE AUDIT RECORD
              </span>
            </div>
            <div class="lifecycle-raw-text">
              "${fb.rawText}"
            </div>
            <div class="lifecycle-meta-tags">
              <span>Channel: <strong>${(sys.channelType || 'MANUAL_ENTRY').replace(/_/g, ' ')}</strong></span>
              <span>Submitter: <strong>${(sys.submitterType || 'CUSTOMER').replace(/_/g, ' ')}</strong></span>
              <span>Submitted At: <strong>${new Date(sys.submittedAt || fb.createdAt).toLocaleString()}</strong></span>
              <span>Content Hash: <code class="table-id-mono" style="font-size: 0.7rem;">${(sys.contentHash || 'N/A').slice(0, 16)}...</code></span>
              <span>Duplicate Signal: <strong>${sys.isDuplicate ? '⚠️ Duplicate of ' + sys.duplicateOfId : '✓ Unique Signal'}</strong></span>
            </div>
          </div>

          <!-- STAGE 2: NORMALIZED CANONICAL REPRESENTATION -->
          <div class="lifecycle-panel tier-norm">
            <div class="lifecycle-panel-title">
              <span style="font-weight: 700; color: #22d3ee; font-size: 0.85rem;">STAGE 2: NORMALIZED & CANONICAL REPRESENTATION</span>
              <span class="lifecycle-badge" style="background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.3);">
                PII SCRUBBED & TOKENIZED
              </span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-secondary); background-color: rgba(0, 0, 0, 0.2); padding: 0.75rem; border-radius: var(--radius-sm);">
              ${fb.normalizedText || fb.rawText}
            </div>
            <div class="lifecycle-meta-tags" style="margin-top: 0.5rem;">
              <span>Detected Language: <strong>${(ai.language ? ai.language.code : fb.languageCode).toUpperCase()}</strong> (${ai.language ? Math.round(ai.language.confidence * 100) : 100}% conf)</span>
              <span>PII Assessment: <strong>${fb.hasPii ? '🔒 PII Scrubbed' : '✓ Clean'}</strong></span>
              <span>Privacy Level: <strong>${sys.privacyClassification}</strong></span>
            </div>
          </div>

          <!-- STAGE 3: GROUNDED AI-DERIVED FACTS -->
          <div class="lifecycle-panel tier-ai">
            <div class="lifecycle-panel-title">
              <span style="font-weight: 700; color: #34d399; font-size: 0.85rem;">STAGE 3: GROUNDED AI OPERATIONAL EXTRACTION</span>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                ${ai.overallUncertainty ? `<span class="field-card-uncertainty" style="margin: 0; padding: 2px 8px; font-weight: 700;">⚠️ Has Uncertain Fields</span>` : `<span class="lifecycle-badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);">High Confidence</span>`}
                <button type="button" class="btn btn-secondary btn-sm" id="btn-reanalyze-ai" style="font-size: 0.72rem; padding: 2px 8px;">
                  ⚡ Re-Analyze
                </button>
              </div>
            </div>

            ${ai.uncertaintySummary && ai.uncertaintySummary.length > 0 ? `
              <div style="background: rgba(251, 191, 36, 0.08); border: 1px solid rgba(251, 191, 36, 0.25); border-radius: var(--radius-sm); padding: 0.65rem; margin-bottom: 0.75rem; font-size: 0.78rem; color: #fbbf24;">
                <strong>AI Uncertainty Summary:</strong>
                <ul style="margin: 4px 0 0 1.25rem; padding: 0;">
                  ${ai.uncertaintySummary.map(u => `<li>${u}</li>`).join('')}
                </ul>
              </div>
            ` : ''}

            <!-- 14 Structured Field Cards Grid -->
            <div class="field-grid">
              ${renderFieldCard('issueCategory', 'Issue Category')}
              ${renderFieldCard('issueType', 'Issue Type')}
              ${renderFieldCard('location', 'Store Location')}
              ${renderFieldCard('affectedEntity', 'Affected Entity')}
              ${renderFieldCard('severity', 'Severity Level')}
              ${renderFieldCard('urgency', 'Operational Urgency')}
              ${renderFieldCard('operationalImpact', 'Operational Impact')}
              ${renderFieldCard('customerImpact', 'Customer Impact')}
              ${renderFieldCard('safetyRelevance', 'Safety Relevance')}
              ${renderFieldCard('intent', 'Operational Intent')}
              ${renderFieldCard('temporalInformation', 'Temporal Reference')}
            </div>

            <!-- Sentiment & Entity Mentions -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 0.75rem;">
              <div style="background-color: rgba(0, 0, 0, 0.2); padding: 0.65rem; border-radius: var(--radius-sm); font-size: 0.8rem;">
                <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">GROUNDED SENTIMENT</div>
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 3px;">
                  <strong style="color: ${fb.sentimentScore < 0 ? 'var(--p1-critical)' : '#10b981'}; font-size: 0.95rem;">
                    ${ai.sentiment ? ai.sentiment.label : 'NEUTRAL'} (${fb.sentimentScore})
                  </strong>
                  ${ai.sentiment && ai.sentiment.evidence ? `<span style="font-size: 0.72rem; color: #38bdf8; font-style: italic;">❝${ai.sentiment.evidence.text}❞</span>` : ''}
                </div>
              </div>
              <div style="background-color: rgba(0, 0, 0, 0.2); padding: 0.65rem; border-radius: var(--radius-sm); font-size: 0.8rem;">
                <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">OBSERVED SYMPTOMS</div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 3px;">
                  ${ai.symptoms && ai.symptoms.length > 0 ? ai.symptoms.map(s => `<span class="badge badge-neutral" style="font-size: 0.7rem;">${s.text}</span>`).join('') : '<span style="color: var(--text-muted); font-size: 0.75rem;">None extracted</span>'}
                </div>
              </div>
            </div>
          </div>

          <!-- STAGE 4: DYNAMIC INVESTIGATION & TARGETED FOLLOW-UP (PHASE 5) -->
          <div class="lifecycle-panel" style="border-left: 4px solid #38bdf8; background-color: rgba(56, 189, 248, 0.04);">
            <div class="lifecycle-panel-title">
              <span style="font-weight: 700; color: #38bdf8; font-size: 0.85rem;">STAGE 4: DYNAMIC INVESTIGATION & TARGETED FOLLOW-UP</span>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="lifecycle-badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);">
                  ${fb.investigationStatus || 'IN_PROGRESS'}
                </span>
                <button type="button" class="btn btn-secondary btn-sm" id="btn-reanalyze-enriched" style="font-size: 0.72rem; padding: 2px 8px;">
                  ⚡ Enrich & Re-Analyze
                </button>
              </div>
            </div>

            <div id="investigation-content-area" style="font-size: 0.82rem;">
              <div style="color: var(--text-muted); font-size: 0.78rem;">Loading clarification context & targeted questions...</div>
            </div>
          </div>

          <!-- STAGE 5: HUMAN REVIEW & OVERRIDE CONSOLE -->
          <div class="lifecycle-panel tier-corrections">
            <div class="lifecycle-panel-title">
              <span style="font-weight: 700; color: #fbbf24; font-size: 0.85rem;">STAGE 5: HUMAN REVIEW & CORRECTION CONSOLE</span>
              <span class="lifecycle-badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3);">
                ${humanOv.reviewedAt ? 'REVIEWED' : 'AWAITING OPERATOR REVIEW'}
              </span>
            </div>

            ${humanOv.reviewNotes ? `
              <div style="background-color: rgba(0, 0, 0, 0.2); padding: 0.65rem; border-radius: var(--radius-sm); margin-bottom: 0.75rem; font-size: 0.82rem;">
                <span style="color: var(--text-muted);">Operator Review Notes (${humanOv.reviewedBy || 'Manager'} at ${new Date(humanOv.reviewedAt).toLocaleString()}):</span>
                <div style="color: #fff; font-weight: 500; margin-top: 2px;">"${humanOv.reviewNotes}"</div>
              </div>
            ` : ''}

            <!-- Override Submission Form -->
            <form id="form-human-override" style="background-color: rgba(0, 0, 0, 0.2); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid rgba(255, 255, 255, 0.05);">
              <div style="font-size: 0.8rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;">
                Submit Human Correction / Override (Leaves AI Facts Untouched)
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.65rem; margin-bottom: 0.65rem;">
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.75rem;">Target Field to Correct</label>
                  <select id="ov-field-select" class="form-select" style="font-size: 0.82rem;">
                    <option value="severity">Severity Level</option>
                    <option value="location">Store Location</option>
                    <option value="issueCategory">Issue Category</option>
                    <option value="issueType">Issue Type</option>
                    <option value="affectedEntity">Affected Entity</option>
                    <option value="urgency">Operational Urgency</option>
                    <option value="safetyRelevance">Safety Relevance</option>
                  </select>
                </div>
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.75rem;">Corrected Human Value</label>
                  <input type="text" id="ov-value-input" class="form-input" style="font-size: 0.82rem;" placeholder="e.g. CRITICAL or Aisle 4B" required />
                </div>
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.75rem;">Correction Reason / Justification</label>
                  <input type="text" id="ov-reason-input" class="form-input" style="font-size: 0.82rem;" placeholder="e.g. Verified active puddle in person" required />
                </div>
              </div>

              <div class="form-group" style="margin-bottom: 0.65rem;">
                <label class="form-label" style="font-size: 0.75rem;">General Review Notes</label>
                <textarea id="ov-general-notes" class="form-textarea" style="font-size: 0.82rem; min-height: 50px;" placeholder="Document overall floor verification, follow-up actions taken, or maintenance ticket references...">${humanOv.reviewNotes || ''}</textarea>
              </div>

              <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
                <button type="submit" class="btn btn-primary btn-sm" id="btn-save-override">
                  ✓ Save Correction & Mark Reviewed
                </button>
              </div>
            </form>
          </div>

        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="btn-close-lifecycle">Close Inspector</button>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-lifecycle').addEventListener('click', closeModal);

    // Re-analyze trigger
    document.getElementById('btn-reanalyze-ai').addEventListener('click', async () => {
      try {
        await api.reanalyzeFeedback(feedbackId);
        showToast('AI Understanding re-analyzed with fresh groundings.', 'success');
        openFeedbackLifecycleModal(feedbackId, onSuccess);
        if (onSuccess) onSuccess();
      } catch (err) {
        showToast('Re-analysis error: ' + err.message, 'error');
      }
    });

    const btnReanalyzeEnriched = document.getElementById('btn-reanalyze-enriched');
    if (btnReanalyzeEnriched) {
      btnReanalyzeEnriched.addEventListener('click', async () => {
        try {
          await api.enrichAndReanalyzeFeedback(feedbackId);
          showToast('Enrichment and AI re-analysis complete.', 'success');
          openFeedbackLifecycleModal(feedbackId, onSuccess);
          if (onSuccess) onSuccess();
        } catch (err) {
          showToast('Re-analysis error: ' + err.message, 'error');
        }
      });
    }

    // Fetch and render dynamic investigation
    try {
      const inv = await api.getFeedbackInvestigation(feedbackId);
      const invArea = document.getElementById('investigation-content-area');
      if (invArea) {
        const isSufficient = inv.investigationStatus === 'SUFFICIENT' || inv.questions.length === 0;
        let html = '';
        if (inv.missingFields && inv.missingFields.length > 0) {
          html += `
            <div style="display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.65rem;">
              <span style="color: var(--text-muted); font-size: 0.72rem; font-weight: 700;">MISSING CONTEXT DETECTED:</span>
              ${inv.missingFields.map(f => `<span class="badge badge-p2" style="font-size: 0.68rem;">${f}</span>`).join('')}
            </div>
          `;
        }

        if (inv.hasEnrichedText && inv.enrichedText) {
          html += `
            <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: var(--radius-sm); padding: 0.5rem; margin-bottom: 0.65rem; font-size: 0.78rem;">
              <strong style="color: #38bdf8;">Enriched Context Representation:</strong>
              <div style="color: var(--text-secondary); margin-top: 2px;">${inv.enrichedText}</div>
            </div>
          `;
        }

        if (isSufficient) {
          html += `
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; color: #34d399; font-size: 0.8rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>✓</span>
              <span><strong>Operational Context Sufficient:</strong> All critical attributes grounded. Dynamic follow-up concluded.</span>
            </div>
          `;
        } else {
          html += `
            <div style="display: flex; flex-direction: column; gap: 0.6rem;">
              ${inv.questions.map(q => `
                <div class="field-card" style="border-left: 3px solid ${q.status === 'ANSWERED' ? '#34d399' : '#38bdf8'};">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 700; color: #fff; font-size: 0.82rem;">${q.questionText}</span>
                    <span class="badge ${q.status === 'ANSWERED' ? 'badge-p4' : 'badge-neutral'}" style="font-size: 0.68rem;">${q.status}</span>
                  </div>
                  <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">
                    <em>Reason: ${q.reason}</em>
                  </div>
                  ${q.status === 'ANSWERED' ? `
                    <div style="color: #34d399; font-size: 0.8rem; margin-top: 4px; font-weight: 600;">
                      Answer: "${q.answer}"
                    </div>
                  ` : `
                    <div style="display: flex; gap: 0.4rem; margin-top: 6px;">
                      <input type="text" class="form-input input-inv-answer" data-id="${q.id}" placeholder="Provide answer or clarification..." style="font-size: 0.78rem; padding: 4px 8px;" />
                      <button type="button" class="btn btn-primary btn-sm btn-submit-inv-answer" data-id="${q.id}" style="font-size: 0.75rem;">Submit</button>
                      <button type="button" class="btn btn-secondary btn-sm btn-dismiss-inv-question" data-id="${q.id}" style="font-size: 0.75rem;">Dismiss</button>
                    </div>
                  `}
                </div>
              `).join('')}
            </div>
          `;
        }

        invArea.innerHTML = html;

        invArea.querySelectorAll('.btn-submit-inv-answer').forEach(btn => {
          btn.addEventListener('click', async () => {
            const qId = btn.getAttribute('data-id');
            const input = invArea.querySelector(`.input-inv-answer[data-id="${qId}"]`);
            const ans = input ? input.value.trim() : '';
            if (!ans) return;
            try {
              await api.answerInvestigationQuestion(qId, ans);
              showToast('Clarification recorded and feedback re-analyzed.', 'success');
              openFeedbackLifecycleModal(feedbackId, onSuccess);
              if (onSuccess) onSuccess();
            } catch (err) {
              showToast('Error recording answer: ' + err.message, 'error');
            }
          });
        });

        invArea.querySelectorAll('.btn-dismiss-inv-question').forEach(btn => {
          btn.addEventListener('click', async () => {
            const qId = btn.getAttribute('data-id');
            try {
              await api.dismissInvestigationQuestion(qId, 'Dismissed by operator');
              showToast('Question dismissed.', 'info');
              openFeedbackLifecycleModal(feedbackId, onSuccess);
            } catch (err) {
              showToast('Dismiss error: ' + err.message, 'error');
            }
          });
        });
      }
    } catch (err) {
      console.warn('Failed to load investigation summary:', err);
    }

    // Form submission
    document.getElementById('form-human-override').addEventListener('submit', async (e) => {
      e.preventDefault();
      const field = document.getElementById('ov-field-select').value;
      const value = document.getElementById('ov-value-input').value.trim();
      const reason = document.getElementById('ov-reason-input').value.trim();
      const reviewNotes = document.getElementById('ov-general-notes').value.trim();

      try {
        await api.reviewFeedbackWithOverrides(feedbackId, {
          processingStatus: 'reviewed',
          status: 'IN_REVIEW',
          reviewNotes: reviewNotes || reason,
          overrides: {
            [field]: {
              value: value,
              reason: reason
            }
          }
        });

        showToast(`Field '${field}' corrected and saved to human overrides.`, 'success');
        openFeedbackLifecycleModal(feedbackId, onSuccess);
        if (onSuccess) onSuccess();
      } catch (err) {
        showToast('Failed to save correction: ' + err.message, 'error');
      }
    });

  } catch (err) {
    showToast('Failed to load feedback understanding: ' + err.message, 'error');
  }
}

/* =========================================================================
   MODAL 4: MANAGER REVIEW & PROCESSING STATUS ADVANCEMENT
   ========================================================================= */
export function openReviewFeedbackModal(feedbackId, currentProcStatus, currentLifeStatus, onSuccess) {
  // Delegate to full 4-stage Operational Intelligence Inspector for rich human review
  openFeedbackLifecycleModal(feedbackId, onSuccess);
}

/* =========================================================================
   MODAL 5: PHASE 15 MULTILINGUAL OPERATIONAL INTELLIGENCE HARDENING & BENCHMARK
   ========================================================================= */
let multilingualActiveTab = 'tester';

export async function openMultilingualInspectorModal(onSuccess) {
  openModal(`
    <div class="modal-header">
      <div>
        <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
          <h3 style="font-size: 1.15rem; font-weight: 700;">🌐 Multilingual Operational Intelligence Inspector</h3>
          <span class="badge" style="background: rgba(14, 165, 233, 0.2); color: #38bdf8; font-weight: 700;">PHASE 15 HARDENING</span>
        </div>
        <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">
          5-Stage Telemetry: Original Text → Language Detection → Normalization → Semantic Understanding → Structured Extraction (Evidence Preserved)
        </div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>

    <div class="modal-body" style="max-height: 75vh; overflow-y: auto;">
      <!-- Tab Navigation -->
      <div style="display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1rem; padding-bottom: 0.5rem;">
        <button id="tab-ml-tester" class="btn btn-sm ${multilingualActiveTab === 'tester' ? 'btn-primary' : 'btn-secondary'}" style="font-size: 0.8rem;">
          🔬 Live 5-Stage Pipeline Tester
        </button>
        <button id="tab-ml-benchmark" class="btn btn-sm ${multilingualActiveTab === 'benchmark' ? 'btn-primary' : 'btn-secondary'}" style="font-size: 0.8rem;">
          📊 Grounded Evaluation Benchmark
        </button>
      </div>

      <div id="ml-modal-tab-content">
        ${multilingualActiveTab === 'tester' ? renderMultilingualTesterHtml() : '<div style="color: var(--text-muted); padding: 1.5rem; text-align: center;">Loading benchmark evaluation data...</div>'}
      </div>
    </div>
  `);

  document.getElementById('btn-close-modal')?.addEventListener('click', closeModal);

  document.getElementById('tab-ml-tester')?.addEventListener('click', () => {
    multilingualActiveTab = 'tester';
    openMultilingualInspectorModal(onSuccess);
  });

  document.getElementById('tab-ml-benchmark')?.addEventListener('click', () => {
    multilingualActiveTab = 'benchmark';
    openMultilingualInspectorModal(onSuccess);
  });

  if (multilingualActiveTab === 'tester') {
    wireMultilingualTesterHandlers(onSuccess);
  } else {
    loadAndRenderBenchmarkTab();
  }
}

function renderMultilingualTesterHtml() {
  return `
    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <!-- Sample Buttons Row -->
      <div>
        <label class="form-label" style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted);">
          Load Noisy / Multilingual Sample Inputs:
        </label>
        <div style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.25rem;">
          <button type="button" class="btn btn-secondary btn-sm btn-load-ml-sample" data-sample="डेयरी सेक्शन में दूध का फ्रिज बहुत ज्यादा लीक कर रहा है, फर्श पर फिसलन है।" style="font-size: 0.72rem;">
            🥛 Hindi Devanagari (Dairy Leak)
          </button>
          <button type="button" class="btn btn-secondary btn-sm btn-load-ml-sample" data-sample="dairy section cooler se pani leak ho raha hai farsh geela hai girne ka darr hai" style="font-size: 0.72rem;">
            🇮🇳 Hinglish (Dairy Leak Slip)
          </button>
          <button type="button" class="btn btn-secondary btn-sm btn-load-ml-sample" data-sample="பால் பிரிவு கூலர் தண்ணீர் லீக் ஆகிறது தரை வழுக்குகிறது" style="font-size: 0.72rem;">
            🌾 Tamil Script (Dairy Leak)
          </button>
          <button type="button" class="btn btn-secondary btn-sm btn-load-ml-sample" data-sample="dairy fridge la thanni leak aaguthu floor romba slippery ah irukku" style="font-size: 0.72rem;">
            🌴 Tanglish (Chiller Leak)
          </button>
          <button type="button" class="btn btn-secondary btn-sm btn-load-ml-sample" data-sample="dairy section frij and chiler is leeking wtr, floor slipery dangrous temprature high" style="font-size: 0.72rem;">
            ⚠️ Phonetic Typos (frij/chiler)
          </button>
          <button type="button" class="btn btn-secondary btn-sm btn-load-ml-sample" data-sample="सब्जी विभाग में ऑर्गेनिक पालक और गाजर बिल्कुल खत्म हैं, शेल्फ खाली हैं।" style="font-size: 0.72rem;">
            🥬 Hindi (Produce Empty)
          </button>
        </div>
      </div>

      <!-- Live Input -->
      <div>
        <label class="form-label">Frontline Feedback Text (Multilingual / Noisy / Transliterated)</label>
        <textarea id="ml-test-input" class="form-textarea" style="min-height: 80px; font-size: 0.9rem;" placeholder="Type or paste feedback in English, Hindi, Tamil, Telugu, Hinglish, Tanglish, or with typos..."></textarea>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
        <button type="button" class="btn btn-primary" id="btn-run-ml-pipeline">⚡ Run 5-Stage Pipeline</button>
      </div>

      <!-- Results Display Container -->
      <div id="ml-pipeline-results" style="display: none; border-top: 1px solid var(--border-subtle); padding-top: 1rem;">
      </div>
    </div>
  `;
}

function wireMultilingualTesterHandlers(onSuccess) {
  const container = document.getElementById('modal-container');
  if (!container) return;

  container.querySelectorAll('.btn-load-ml-sample').forEach(btn => {
    btn.addEventListener('click', () => {
      const sampleText = btn.getAttribute('data-sample');
      const input = document.getElementById('ml-test-input');
      if (input) {
        input.value = sampleText;
      }
    });
  });

  document.getElementById('btn-run-ml-pipeline')?.addEventListener('click', async () => {
    const text = document.getElementById('ml-test-input')?.value.trim();
    if (!text) {
      showToast('Please enter or select feedback text.', 'error');
      return;
    }

    const resultsArea = document.getElementById('ml-pipeline-results');
    if (resultsArea) {
      resultsArea.style.display = 'block';
      resultsArea.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem;">Executing 5-Stage Multilingual Intelligence Pipeline...</div>`;
    }

    try {
      const res = await api.parseMultilingualText(text);
      if (resultsArea) {
        renderMultilingualPipelineOutput(resultsArea, res);
      }
    } catch (err) {
      if (resultsArea) {
        resultsArea.innerHTML = `<div style="color: var(--p1-critical); font-size: 0.85rem;">Analysis failed: ${err.message}</div>`;
      }
    }
  });
}

function renderMultilingualPipelineOutput(container, data) {
  const lang = data.detectedLanguage || {};
  const extracted = data.extractedIssue || {};
  const confPct = Math.round((data.confidence || 0.85) * 100);
  const confColor = confPct >= 85 ? '#34d399' : confPct >= 70 ? '#fbbf24' : '#f87171';

  container.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <div style="font-size: 0.82rem; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase; letter-spacing: 0.05em;">
        ✓ 5-Stage Pipeline Telemetry Results
      </div>

      <!-- The 5 Explicitly Required Display Fields -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0.75rem;">
        
        <!-- Field 1: Original Text (Preserved Verbatim) -->
        <div class="field-card" style="border-left: 3px solid #818cf8; background: rgba(99, 102, 241, 0.05);">
          <div class="field-card-header">
            <span class="field-card-label" style="color: #818cf8;">1. ORIGINAL TEXT (PRESERVED)</span>
            <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #818cf8; font-size: 0.65rem;">IMMUTABLE</span>
          </div>
          <div style="font-size: 0.9rem; color: #fff; font-weight: 500; margin-top: 0.4rem; line-height: 1.4;">
            "${data.rawText}"
          </div>
          <div style="font-size: 0.68rem; color: var(--text-muted); margin-top: 0.35rem;">
            Never overwritten or destroyed. Persisted in immutable telemetry tier.
          </div>
        </div>

        <!-- Field 2: Detected Language -->
        <div class="field-card" style="border-left: 3px solid #38bdf8; background: rgba(56, 189, 248, 0.05);">
          <div class="field-card-header">
            <span class="field-card-label" style="color: #38bdf8;">2. DETECTED LANGUAGE</span>
            <span style="font-family: var(--font-family-mono); font-weight: 700; color: #38bdf8; font-size: 0.75rem;">${(lang.code || 'en').toUpperCase()}</span>
          </div>
          <div style="font-size: 0.95rem; color: #fff; font-weight: 600; margin-top: 0.4rem;">
            ${lang.name || 'English'}
          </div>
          <div style="display: flex; gap: 0.35rem; margin-top: 0.4rem; flex-wrap: wrap;">
            <span class="badge badge-neutral" style="font-size: 0.65rem;">Script: ${lang.script || 'Latin'}</span>
            ${lang.isTransliterated ? `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; font-size: 0.65rem;">Transliterated</span>` : ''}
            ${lang.isCodeMixed ? `<span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-size: 0.65rem;">Code-Mixed</span>` : ''}
          </div>
          ${lang.evidence && lang.evidence.length > 0 ? `
            <div style="font-size: 0.68rem; color: var(--text-muted); margin-top: 0.35rem;">
              Tokens: <em>${lang.evidence.join(', ')}</em>
            </div>
          ` : ''}
        </div>

        <!-- Field 3: Normalized Interpretation -->
        <div class="field-card" style="border-left: 3px solid #22d3ee; background: rgba(6, 182, 212, 0.05); grid-column: span 2;">
          <div class="field-card-header">
            <span class="field-card-label" style="color: #22d3ee;">3. NORMALIZED INTERPRETATION</span>
            <span class="badge" style="background: rgba(6, 182, 212, 0.2); color: #22d3ee; font-size: 0.65rem;">CANONICAL ENGLISH</span>
          </div>
          <div style="font-size: 0.92rem; color: #a5f3fc; font-weight: 500; margin-top: 0.4rem; line-height: 1.4;">
            "${data.normalizedInterpretation}"
          </div>
          ${data.spellingCorrections && Object.keys(data.spellingCorrections).length > 0 ? `
            <div style="font-size: 0.72rem; color: #fbbf24; margin-top: 0.4rem;">
              <strong>Spelling Typo Corrections:</strong>
              ${Object.entries(data.spellingCorrections).map(([from, to]) => `<span style="margin-left: 0.4rem; background: rgba(245, 158, 11, 0.15); padding: 2px 6px; border-radius: 3px;"><code>${from}</code> → <code>${to}</code></span>`).join('')}
            </div>
          ` : ''}
        </div>

        <!-- Field 4: Extracted Issue -->
        <div class="field-card" style="border-left: 3px solid #a855f7; background: rgba(168, 85, 247, 0.05);">
          <div class="field-card-header">
            <span class="field-card-label" style="color: #a855f7;">4. EXTRACTED ISSUE</span>
            ${extracted.isSafetyHazard ? `<span class="badge badge-p1" style="font-size: 0.65rem;">⚠️ SAFETY HAZARD</span>` : `<span class="badge badge-p4" style="font-size: 0.65rem;">OPERATIONAL</span>`}
          </div>
          <div style="margin-top: 0.4rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #fff;">${extracted.category || 'FACILITIES_MAINTENANCE'}</div>
            <div style="font-size: 0.75rem; color: #d8b4fe; margin-top: 2px;">Type: <strong>${extracted.issueType || 'GENERAL_MAINTENANCE'}</strong></div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">
              Severity: <strong>${extracted.severity}</strong> &bull; Urgency: <strong>${extracted.urgency}</strong>
            </div>
            <div style="font-size: 0.75rem; color: #fff; margin-top: 4px; font-style: italic;">
              ${extracted.summary || ''}
            </div>
          </div>
        </div>

        <!-- Field 5: Calibrated Confidence -->
        <div class="field-card" style="border-left: 3px solid #34d399; background: rgba(52, 211, 153, 0.05);">
          <div class="field-card-header">
            <span class="field-card-label" style="color: #34d399;">5. CALIBRATED CONFIDENCE</span>
            <span style="font-family: var(--font-family-mono); font-weight: 700; color: ${confColor}; font-size: 1rem;">
              ${confPct}%
            </span>
          </div>
          <div style="margin-top: 0.5rem;">
            <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px; overflow: hidden;">
              <div style="background: ${confColor}; height: 100%; width: ${confPct}%;"></div>
            </div>
            <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.5rem; line-height: 1.35;">
              Calibrated empirical score combining script detection reliability and domain keyword alignment.
            </div>
          </div>
        </div>

      </div>
    </div>
  `;
}

async function loadAndRenderBenchmarkTab() {
  const tabContent = document.getElementById('ml-modal-tab-content');
  if (!tabContent) return;

  try {
    const data = await api.getMultilingualBenchmark();
    const results = data.testCaseResults || [];

    tabContent.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 1.25rem;">
        
        <!-- Grounded Mandate Banner -->
        <div style="background: rgba(14, 165, 233, 0.08); border: 1px solid rgba(14, 165, 233, 0.3); border-radius: var(--radius-sm); padding: 0.75rem 1rem;">
          <div style="font-size: 0.82rem; font-weight: 700; color: #38bdf8;">
            EMPIRICAL EVALUATION SUITE
          </div>
          <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 2px;">
            Strict adherence to platform mandate: <em>"Do not claim language accuracy without evaluation data."</em> All metrics are dynamically computed against curated multi-lingual frontline test cases.
          </div>
        </div>

        <!-- Benchmark KPI Stats Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.65rem;">
          <div class="kpi-card">
            <div class="kpi-card-header"><span style="font-size: 0.75rem;">Total Cases</span><span>📋</span></div>
            <div class="kpi-value-row"><span class="kpi-value" style="font-size: 1.4rem;">${data.totalTestCases}</span></div>
          </div>

          <div class="kpi-card highlight">
            <div class="kpi-card-header"><span style="font-size: 0.75rem;">Detection Accuracy</span><span>🌐</span></div>
            <div class="kpi-value-row"><span class="kpi-value" style="font-size: 1.4rem; color: #38bdf8;">${data.detectionAccuracyPct}%</span></div>
          </div>

          <div class="kpi-card">
            <div class="kpi-card-header"><span style="font-size: 0.75rem;">Category Accuracy</span><span>🏷️</span></div>
            <div class="kpi-value-row"><span class="kpi-value" style="font-size: 1.4rem; color: #34d399;">${data.categoryAccuracyPct}%</span></div>
          </div>

          <div class="kpi-card">
            <div class="kpi-card-header"><span style="font-size: 0.75rem;">Issue Type Acc.</span><span>⚙️</span></div>
            <div class="kpi-value-row"><span class="kpi-value" style="font-size: 1.4rem; color: #a78bfa;">${data.issueTypeAccuracyPct}%</span></div>
          </div>

          <div class="kpi-card">
            <div class="kpi-card-header"><span style="font-size: 0.75rem;">Cross-Lingual Clustering</span><span>🔗</span></div>
            <div class="kpi-value-row"><span class="kpi-value" style="font-size: 1.4rem; color: #fbbf24;">${data.crossLingualClusteringPrecisionPct}%</span></div>
          </div>
        </div>

        <!-- Languages Covered Badges -->
        <div>
          <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">
            Languages & Variants Covered (${data.languagesCovered.length}):
          </div>
          <div style="display: flex; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.35rem;">
            ${data.languagesCovered.map(l => `<span class="badge badge-neutral" style="font-family: var(--font-family-mono); font-size: 0.72rem; font-weight: 700;">${l}</span>`).join('')}
          </div>
        </div>

        <!-- Evaluation Results Table -->
        <div class="r5-table-container" style="max-height: 340px; overflow-y: auto;">
          <table class="r5-table" style="font-size: 0.75rem;">
            <thead>
              <tr>
                <th>Test Case</th>
                <th>Raw Text</th>
                <th>Detected vs Expected Lang</th>
                <th>Detected Category</th>
                <th>Normalized Interpretation</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              ${results.map(r => `
                <tr>
                  <td><code class="table-id-mono" style="font-size: 0.68rem;">${r.id}</code></td>
                  <td style="max-width: 200px; color: #fff; word-break: break-word;">"${r.text}"</td>
                  <td>
                    <div style="display: flex; align-items: center; gap: 0.25rem;">
                      <span class="badge" style="background: ${r.langMatch ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}; color: ${r.langMatch ? '#34d399' : '#f87171'}; font-weight: 700; font-size: 0.68rem;">
                        ${r.detectedLanguage}
                      </span>
                      ${!r.langMatch ? `<span style="font-size: 0.65rem; color: var(--text-muted);">(exp: ${r.expectedLanguage})</span>` : ''}
                    </div>
                  </td>
                  <td>
                    <div style="display: flex; align-items: center; gap: 0.25rem;">
                      <span class="badge" style="background: ${r.catMatch ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}; color: ${r.catMatch ? '#34d399' : '#f87171'}; font-size: 0.68rem;">
                        ${r.detectedCategory}
                      </span>
                    </div>
                  </td>
                  <td style="max-width: 220px; color: #a5f3fc; word-break: break-word;">"${r.normalizedInterpretation}"</td>
                  <td><strong style="color: #34d399; font-family: var(--font-family-mono);">${Math.round(r.confidence * 100)}%</strong></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

      </div>
    `;
  } catch (err) {
    tabContent.innerHTML = `<div style="color: var(--p1-critical); padding: 1.5rem;">Failed to load benchmark: ${err.message}</div>`;
  }
}


