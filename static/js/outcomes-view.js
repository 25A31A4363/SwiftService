/**
 * R5 Operational Intelligence Platform - Phase 12: Post-Intervention Outcome Measurement View
 * R5 CORE OBJECTIVE: Measure whether corrective action actually changed the operational problem.
 * Deterministic comparison: BEFORE intervention vs AFTER intervention.
 * Guards against fabricated improvements: shows "outcome cannot yet be determined." when data is insufficient.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import {
  escapeHtml,
  renderEmptyStateHtml,
  renderSkeletonCardsHtml,
  renderErrorStateHtml
} from './ui-utils.js';

let currentFilter = 'ALL';
let searchQuery = '';

export async function renderOutcomesView(container) {
  container.innerHTML = `
    <div style="margin-bottom: 1.5rem;">
      ${renderSkeletonCardsHtml(4)}
    </div>
  `;

  try {
    const summary = await api.getOutcomesDashboard(state.selectedStoreId);
    renderDashboardContent(container, summary);
  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Outcome Measurement Service Unavailable',
      message: err.message || 'Unable to audit post-intervention operational telemetry.',
      onRetryId: 'btn-retry-outcomes'
    });
    container.querySelector('#btn-retry-outcomes')?.addEventListener('click', () => {
      renderOutcomesView(container);
    });
  }
}

function renderDashboardContent(container, data) {
  const outcomes = data.outcomes || [];
  
  // Filter outcomes
  const filtered = outcomes.filter(o => {
    const matchesStatus = (currentFilter === 'ALL') || (o.outcomeStatus === currentFilter);
    const matchesSearch = !searchQuery || 
      o.issueTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.storeName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (o.statusMessage && o.statusMessage.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  container.innerHTML = `
    <!-- Header -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
      <div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <h2 style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0;">Outcome Intelligence</h2>
          <span class="badge-r5 badge-purple">Phase 12: Closed-Loop Measurement</span>
        </div>
        <p style="color: var(--text-secondary); margin: 0.35rem 0 0 0; font-size: 0.9rem; max-width: 760px;">
          R5 Core Objective: Measure whether corrective action actually changed the operational problem by deterministically comparing 
          <strong>BEFORE intervention</strong> vs <strong>AFTER intervention</strong>.
        </p>
      </div>
      <div style="display: flex; gap: 0.5rem; align-items: center;">
        <button id="btn-reevaluate-all" class="r5-btn r5-btn-secondary" style="display: flex; align-items: center; gap: 0.4rem;">
          <span>🔄</span> Re-Audit Operational Signals
        </button>
      </div>
    </div>

    <!-- Operational Guardrail Callout Banner -->
    <div class="outcome-guardrail-banner">
      <div style="display: flex; align-items: flex-start; gap: 0.85rem;">
        <span style="font-size: 1.35rem; line-height: 1;">🛡️</span>
        <div>
          <strong style="color: var(--text-primary); font-size: 0.92rem;">Guarded Against Fabricated Improvements:</strong>
          <div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.2rem; line-height: 1.45;">
            Operational reality is measured strictly on empirical complaint volume, arrival frequency, severity delta, and recurrence. 
            If insufficient observation time or baseline sample exists, the system deterministically outputs: 
            <span class="outcome-quote">"outcome cannot yet be determined."</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Top KPI Cards -->
    <div class="outcome-kpi-grid">
      <div class="r5-card outcome-kpi-card">
        <div class="outcome-kpi-label">Decisive Improvement Rate</div>
        <div class="outcome-kpi-val text-success">${data.improvedRatePct}%</div>
        <div class="outcome-kpi-sub">${data.improvedCount} of ${data.improvedCount + data.noChangeCount + data.worsenedCount} evaluated issues improved</div>
      </div>
      <div class="r5-card outcome-kpi-card">
        <div class="outcome-kpi-label">Total Measured Incidents</div>
        <div class="outcome-kpi-val" style="color: var(--text-primary);">${data.totalResolvedIssues}</div>
        <div class="outcome-kpi-sub">Across active retail store network</div>
      </div>
      <div class="r5-card outcome-kpi-card">
        <div class="outcome-kpi-label">SLA Compliance Rate</div>
        <div class="outcome-kpi-val" style="color: var(--info);">${data.slaComplianceRatePct}%</div>
        <div class="outcome-kpi-sub">Avg resolution: ${data.avgResolutionTimeHours} hrs</div>
      </div>
      <div class="r5-card outcome-kpi-card">
        <div class="outcome-kpi-label">Outcome State Distribution</div>
        <div style="display: flex; gap: 0.4rem; margin-top: 0.5rem; flex-wrap: wrap;">
          <span class="outcome-badge-pill pill-improved" title="Improved">${data.improvedCount} Improved</span>
          <span class="outcome-badge-pill pill-nochange" title="No Change">${data.noChangeCount} Unchanged</span>
          <span class="outcome-badge-pill pill-worsened" title="Worsened">${data.worsenedCount} Worsened</span>
          <span class="outcome-badge-pill pill-inconclusive" title="Inconclusive">${data.inconclusiveCount} Inconclusive</span>
        </div>
      </div>
    </div>

    <!-- Filter & Search Bar -->
    <div class="r5-card" style="margin-bottom: 1.5rem;">
      <div class="r5-card-body" style="padding: 0.85rem 1.25rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
        <div style="display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap;">
          <span style="font-size: 0.85rem; color: var(--text-muted); margin-right: 0.3rem;">Filter Status:</span>
          ${['ALL', 'Improved', 'No significant change', 'Worsened', 'Inconclusive'].map(status => `
            <button class="outcome-filter-btn ${currentFilter === status ? 'active' : ''}" data-filter="${status}">
              ${status === 'ALL' ? 'All Outcomes' : status}
            </button>
          `).join('')}
        </div>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <input 
            type="text" 
            id="outcome-search-input" 
            class="r5-input" 
            style="width: 240px; padding: 0.35rem 0.65rem; font-size: 0.85rem;" 
            placeholder="Search issue title or store..." 
            value="${searchQuery}"
          />
        </div>
      </div>
    </div>

    <!-- Outcome Records List -->
    <div class="outcome-records-container">
      ${filtered.length === 0 ? `
        <div style="margin-top: 1rem;">
          ${renderEmptyStateHtml({
            icon: '⚖️',
            title: 'No outcome records match your filter',
            desc: 'No post-intervention evaluations match the selected status or search query. Adjust the filter pills or search terms.',
            actionLabel: 'Reset Outcome Filter',
            actionId: 'btn-reset-outcomes-filter'
          })}
        </div>
      ` : filtered.map(item => renderOutcomeCard(item)).join('')}
    </div>
  `;

  // Attach Event Handlers
  container.querySelector('#btn-reset-outcomes-filter')?.addEventListener('click', () => {
    currentFilter = 'ALL';
    searchQuery = '';
    renderOutcomesView(container);
  });

  container.querySelectorAll('.outcome-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      currentFilter = btn.dataset.filter;
      renderOutcomesView(container);
    });
  });

  const searchInput = container.querySelector('#outcome-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value;
      renderDashboardContent(container, data);
    });
  }

  const btnReevaluateAll = container.querySelector('#btn-reevaluate-all');
  if (btnReevaluateAll) {
    btnReevaluateAll.addEventListener('click', async () => {
      btnReevaluateAll.disabled = true;
      btnReevaluateAll.innerHTML = `<span>⏳</span> Re-Auditing...`;
      try {
        for (const o of outcomes) {
          await api.evaluateIssueOutcome(o.issueId, { forceReevaluate: true });
        }
        showToast('Successfully re-audited operational outcomes with latest telemetry', 'success');
        await renderOutcomesView(container);
      } catch (err) {
        showToast('Error re-auditing outcomes: ' + err.message, 'error');
        btnReevaluateAll.disabled = false;
        btnReevaluateAll.innerHTML = `<span>🔄</span> Re-Audit Operational Signals`;
      }
    });
  }

  // Attach Card Inspect Handlers
  container.querySelectorAll('.btn-inspect-evidence').forEach(btn => {
    btn.addEventListener('click', () => {
      const outcomeId = btn.dataset.outcomeId;
      const outcome = outcomes.find(o => o.id === outcomeId);
      if (outcome) {
        openEvidenceModal(outcome);
      }
    });
  });

  container.querySelectorAll('.btn-simulate-window').forEach(btn => {
    btn.addEventListener('click', () => {
      const issueId = btn.dataset.issueId;
      openSimulationModal(issueId, container);
    });
  });
}

function renderOutcomeCard(o) {
  const b = o.baseline;
  const obs = o.observationWindow;
  const c = o.comparison;
  const iv = o.intervention;

  let statusClass = 'pill-inconclusive';
  let statusIcon = '🟣';
  if (o.outcomeStatus === 'Improved') {
    statusClass = 'pill-improved';
    statusIcon = '🟢';
  } else if (o.outcomeStatus === 'No significant change') {
    statusClass = 'pill-nochange';
    statusIcon = '🟡';
  } else if (o.outcomeStatus === 'Worsened') {
    statusClass = 'pill-worsened';
    statusIcon = '🔴';
  }

  const confidencePct = Math.round(o.confidence * 100);
  const freqChangeSign = c.frequencyChangePct > 0 ? `+${c.frequencyChangePct}` : `${c.frequencyChangePct}`;
  const freqColor = c.frequencyChangePct < 0 ? 'var(--success)' : (c.frequencyChangePct > 0 ? 'var(--danger)' : 'var(--text-muted)');

  return `
    <div class="r5-card outcome-card" id="card-${o.id}">
      <!-- Card Header -->
      <div class="outcome-card-header">
        <div style="flex: 1;">
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <span class="outcome-store-tag">${o.storeName}</span>
            <span class="outcome-id-tag">ID: ${o.issueId}</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Resolved: ${formatDateTime(iv.timestamp)}</span>
          </div>
          <h3 class="outcome-issue-title">${escapeHtml(o.issueTitle)}</h3>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.35rem;">
          <span class="outcome-badge-pill ${statusClass}" style="font-size: 0.88rem; padding: 0.3rem 0.75rem;">
            ${statusIcon} ${o.outcomeStatus}
          </span>
          <div style="font-size: 0.78rem; color: var(--text-muted);">
            Confidence: <strong style="color: var(--text-primary);">${confidencePct}%</strong>
          </div>
        </div>
      </div>

      <!-- Status Verdict Message Banner -->
      <div class="outcome-verdict-banner ${statusClass}-bg">
        <span style="font-weight: 600;">Operational Verdict:</span> 
        <span style="font-style: ${o.outcomeStatus === 'Inconclusive' ? 'italic' : 'normal'};">
          ${escapeHtml(o.statusMessage || 'Outcome evaluated.')}
        </span>
      </div>

      <!-- Comparative Telemetry Grid (BEFORE vs AFTER) -->
      <div class="outcome-comparison-grid">
        <!-- Column 1: BEFORE Intervention -->
        <div class="outcome-col">
          <div class="outcome-col-header text-muted">
            <span>⏮️ BEFORE Intervention</span>
            <span class="outcome-chip">${b.windowHours}h Baseline</span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Complaint Volume:</span>
            <span class="metric-val"><strong>${b.complaintVolume}</strong> complaints</span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Arrival Frequency:</span>
            <span class="metric-val"><strong>${b.issueFrequencyPerDay}</strong> / day</span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Mean Severity:</span>
            <span class="metric-val"><strong>${b.avgSeverity.toFixed(2)}</strong></span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Affected Locations:</span>
            <span class="metric-val"><strong>${b.affectedLocationsCount}</strong> depts</span>
          </div>
        </div>

        <!-- Column 2: INTERVENTION Execution -->
        <div class="outcome-col" style="background: rgba(255, 255, 255, 0.015);">
          <div class="outcome-col-header text-muted">
            <span>⚙️ Intervention Details</span>
            <span class="outcome-chip ${c.slaCompliance ? 'text-success' : 'text-danger'}">
              ${c.slaCompliance ? '✓ SLA Compliant' : '⚠ SLA Breached'}
            </span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Resolution Time:</span>
            <span class="metric-val"><strong>${c.resolutionTimeMinutes || 45}</strong> mins</span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Technician:</span>
            <span class="metric-val">${escapeHtml(iv.resolvedByName || 'Staff Technician')}</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.4rem; line-height: 1.35; background: var(--bg-surface-raised); padding: 0.45rem; border-radius: 4px; border-left: 2px solid var(--accent);">
            ${escapeHtml(iv.technicianNotes || iv.actionDescription || 'Corrective action executed.')}
          </div>
        </div>

        <!-- Column 3: AFTER Intervention (Observation Window) -->
        <div class="outcome-col">
          <div class="outcome-col-header text-muted">
            <span>⏭️ AFTER Intervention</span>
            <span class="outcome-chip ${obs.isWindowSufficient ? 'text-success' : 'text-warning'}">
              ${obs.windowHours}h (${obs.isWindowSufficient ? 'Sufficient' : 'Waiting'})
            </span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Post Complaints:</span>
            <span class="metric-val"><strong>${obs.complaintVolume}</strong> complaints</span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Post Arrival Rate:</span>
            <span class="metric-val"><strong>${obs.issueFrequencyPerDay}</strong> / day</span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Recurrence Count:</span>
            <span class="metric-val" style="color: ${c.recurrenceCount > 0 ? 'var(--danger)' : 'var(--success)'};">
              <strong>${c.recurrenceCount}</strong> events
            </span>
          </div>
          <div class="outcome-metric-row">
            <span class="metric-label">Frequency Shift:</span>
            <span class="metric-val" style="color: ${freqColor}; font-weight: 700;">
              ${freqChangeSign}%
            </span>
          </div>
        </div>
      </div>

      <!-- Card Footer Actions -->
      <div class="outcome-card-footer">
        <div style="display: flex; align-items: center; gap: 0.75rem; flex: 1;">
          <div style="width: 120px; background: rgba(255, 255, 255, 0.08); border-radius: 10px; height: 6px; overflow: hidden;">
            <div style="width: ${confidencePct}%; background: ${confidencePct > 80 ? 'var(--success)' : (confidencePct > 50 ? 'var(--warning)' : 'var(--text-muted)')}; height: 100%;"></div>
          </div>
          <span style="font-size: 0.78rem; color: var(--text-muted);">Audit Confidence: ${confidencePct}%</span>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button class="r5-btn r5-btn-secondary btn-simulate-window" data-issue-id="${o.issueId}" style="font-size: 0.8rem; padding: 0.3rem 0.6rem;">
            <span>⏱️</span> Simulate Window
          </button>
          <button class="r5-btn r5-btn-primary btn-inspect-evidence" data-outcome-id="${o.id}" style="font-size: 0.8rem; padding: 0.3rem 0.75rem;">
            <span>🔍</span> Inspect Evidence Citations
          </button>
        </div>
      </div>
    </div>
  `;
}

function openEvidenceModal(outcome) {
  const container = document.getElementById('modal-container');
  if (!container) return;

  const evList = outcome.evidence || [];
  const b = outcome.baseline;
  const c = outcome.comparison;

  container.innerHTML = `
    <div class="r5-modal-backdrop" id="evidence-modal-backdrop">
      <div class="r5-modal" style="max-width: 760px; max-height: 85vh; overflow-y: auto;">
        <div class="r5-modal-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem;">
          <div>
            <h3 style="margin: 0; font-size: 1.2rem; color: var(--text-primary);">Deterministic Evidence & Lineage</h3>
            <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.2rem;">
              Issue: ${escapeHtml(outcome.issueTitle)} (${outcome.issueId})
            </div>
          </div>
          <button class="r5-btn r5-btn-secondary" id="btn-close-evidence-modal" style="padding: 0.25rem 0.5rem;">✕</button>
        </div>

        <div class="r5-modal-body" style="padding: 1.25rem 0;">
          <!-- Verdict Summary -->
          <div style="background: var(--bg-surface-raised); border-radius: 6px; padding: 0.85rem 1rem; margin-bottom: 1.25rem; border-left: 3px solid var(--accent);">
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.92rem; margin-bottom: 0.3rem;">
              Outcome Status: <span class="badge-r5">${outcome.outcomeStatus}</span> (Confidence: ${(outcome.confidence * 100).toFixed(0)}%)
            </div>
            <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4;">
              ${escapeHtml(outcome.statusMessage || '')}
            </div>
          </div>

          <!-- Deterministic Metrics Proof Table -->
          <h4 style="font-size: 0.92rem; margin: 0 0 0.6rem 0; color: var(--text-primary);">Mathematical Delta Audit</h4>
          <table class="r5-table" style="font-size: 0.82rem; width: 100%; margin-bottom: 1.5rem;">
            <thead>
              <tr style="background: rgba(255, 255, 255, 0.02);">
                <th style="padding: 0.4rem 0.6rem;">Operational Metric</th>
                <th style="padding: 0.4rem 0.6rem;">Baseline (BEFORE)</th>
                <th style="padding: 0.4rem 0.6rem;">Post-Obs (AFTER)</th>
                <th style="padding: 0.4rem 0.6rem;">Absolute Delta</th>
                <th style="padding: 0.4rem 0.6rem;">Shift %</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="padding: 0.4rem 0.6rem; font-weight: 500;">Arrival Frequency</td>
                <td style="padding: 0.4rem 0.6rem;">${b.issueFrequencyPerDay} / day</td>
                <td style="padding: 0.4rem 0.6rem;">${outcome.observationWindow.issueFrequencyPerDay} / day</td>
                <td style="padding: 0.4rem 0.6rem;">${c.frequencyDeltaPerDay} / day</td>
                <td style="padding: 0.4rem 0.6rem; font-weight: 700;">${c.frequencyChangePct}%</td>
              </tr>
              <tr>
                <td style="padding: 0.4rem 0.6rem; font-weight: 500;">Complaint Volume</td>
                <td style="padding: 0.4rem 0.6rem;">${b.complaintVolume} complaints</td>
                <td style="padding: 0.4rem 0.6rem;">${outcome.observationWindow.complaintVolume} complaints</td>
                <td style="padding: 0.4rem 0.6rem;">${c.complaintVolumeDelta}</td>
                <td style="padding: 0.4rem 0.6rem;">${c.volumeChangePct}%</td>
              </tr>
              <tr>
                <td style="padding: 0.4rem 0.6rem; font-weight: 500;">Mean Severity Score</td>
                <td style="padding: 0.4rem 0.6rem;">${b.avgSeverity.toFixed(2)}</td>
                <td style="padding: 0.4rem 0.6rem;">${outcome.observationWindow.avgSeverity.toFixed(2)}</td>
                <td style="padding: 0.4rem 0.6rem;">${c.severityDelta.toFixed(2)}</td>
                <td style="padding: 0.4rem 0.6rem;">—</td>
              </tr>
              <tr>
                <td style="padding: 0.4rem 0.6rem; font-weight: 500;">Recurrence Count</td>
                <td style="padding: 0.4rem 0.6rem;">0 (Baseline)</td>
                <td style="padding: 0.4rem 0.6rem;">${c.recurrenceCount} events</td>
                <td style="padding: 0.4rem 0.6rem;">+${c.recurrenceCount}</td>
                <td style="padding: 0.4rem 0.6rem;">—</td>
              </tr>
            </tbody>
          </table>

          <!-- Chronological Citations Stream -->
          <h4 style="font-size: 0.92rem; margin: 0 0 0.6rem 0; color: var(--text-primary);">Verifiable Evidence Citations</h4>
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            ${evList.map((item, idx) => `
              <div class="evidence-timeline-item">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                  <span class="evidence-stage-tag stage-${item.stage.toLowerCase()}">${item.stage}</span>
                  <span style="font-size: 0.75rem; color: var(--text-muted);">${formatDateTime(item.timestamp)}</span>
                </div>
                <div style="font-weight: 600; color: var(--text-primary); font-size: 0.88rem;">${escapeHtml(item.title)}</div>
                <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.2rem; line-height: 1.4;">${escapeHtml(item.claim)}</div>
                ${item.verbatimQuote ? `
                  <div class="evidence-verbatim-quote">
                    "${escapeHtml(item.verbatimQuote)}"
                  </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        </div>

        <div class="r5-modal-footer" style="display: flex; justify-content: flex-end; border-top: 1px solid var(--border-color); padding-top: 0.75rem;">
          <button class="r5-btn r5-btn-primary" id="btn-modal-done">Close Evidence Inspection</button>
        </div>
      </div>
    </div>
  `;

  const closeModal = () => { container.innerHTML = ''; };
  document.getElementById('btn-close-evidence-modal')?.addEventListener('click', closeModal);
  document.getElementById('btn-modal-done')?.addEventListener('click', closeModal);
  document.getElementById('evidence-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'evidence-modal-backdrop') closeModal();
  });
}

function openSimulationModal(issueId, mainContainer) {
  const container = document.getElementById('modal-container');
  if (!container) return;

  container.innerHTML = `
    <div class="r5-modal-backdrop" id="sim-modal-backdrop">
      <div class="r5-modal" style="max-width: 500px;">
        <div class="r5-modal-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem;">
          <h3 style="margin: 0; font-size: 1.15rem; color: var(--text-primary);">Simulate Observation Window</h3>
          <button class="r5-btn r5-btn-secondary" id="btn-close-sim" style="padding: 0.25rem 0.5rem;">✕</button>
        </div>
        <div class="r5-modal-body" style="padding: 1rem 0;">
          <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0;">
            Adjust the simulated post-intervention observation window to test how deterministic evidence evaluates outcomes as time elapses:
          </p>
          <div style="margin-bottom: 1rem;">
            <label style="display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.35rem;">Observation Window Duration (Hours):</label>
            <select id="sim-hours-select" class="r5-input" style="width: 100%;">
              <option value="0.5">0.5 Hours (30 mins — Inconclusive check)</option>
              <option value="6.0">6 Hours (Immature window check)</option>
              <option value="12.0">12 Hours (Minimum threshold)</option>
              <option value="24.0" selected>24 Hours (Full standard observation)</option>
              <option value="48.0">48 Hours (Extended observation)</option>
              <option value="72.0">72 Hours (Long-term stability audit)</option>
            </select>
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); line-height: 1.4; background: var(--bg-surface-raised); padding: 0.5rem; border-radius: 4px;">
            Note: If observation window is &lt; 12.0 hours, the system prevents fabricated assurance and outputs: <em>"outcome cannot yet be determined."</em>
          </div>
        </div>
        <div class="r5-modal-footer" style="display: flex; justify-content: flex-end; gap: 0.5rem; border-top: 1px solid var(--border-color); padding-top: 0.75rem;">
          <button class="r5-btn r5-btn-secondary" id="btn-cancel-sim">Cancel</button>
          <button class="r5-btn r5-btn-primary" id="btn-run-sim">Run Deterministic Evaluation</button>
        </div>
      </div>
    </div>
  `;

  const closeModal = () => { container.innerHTML = ''; };
  document.getElementById('btn-close-sim')?.addEventListener('click', closeModal);
  document.getElementById('btn-cancel-sim')?.addEventListener('click', closeModal);
  document.getElementById('sim-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'sim-modal-backdrop') closeModal();
  });

  document.getElementById('btn-run-sim')?.addEventListener('click', async () => {
    const hours = parseFloat(document.getElementById('sim-hours-select').value);
    closeModal();
    try {
      showToast(`Evaluating outcome with ${hours}h observation window...`, 'info');
      await api.evaluateIssueOutcome(issueId, { observationHours: hours, forceReevaluate: true });
      showToast(`Outcome evaluated successfully!`, 'success');
      await renderOutcomesView(mainContainer);
    } catch (err) {
      showToast('Simulation failed: ' + err.message, 'error');
    }
  });
}

function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return isoString;
  }
}
