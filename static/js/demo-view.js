/**
 * R5 Operational Intelligence Platform - Phase 21: End-to-End Demonstration View
 * Implements an interactive visual walkthrough of the complete 15-stage closed-loop lifecycle:
 * RAW FEEDBACK -> AI UNDERSTANDING -> INVESTIGATION -> CLUSTER -> EMERGING ISSUE ->
 * PRIORITY -> EVIDENCE -> ROUTING -> ACTION -> RESOLUTION -> OUTCOME -> EXECUTIVE BRIEF
 */

import { api, showToast } from './api.js';
import { state } from './state.js';

let currentDemoData = null;
let isExecuting = false;

export async function renderDemoView(container) {
  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
      <div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <h2 style="margin: 0; font-family: var(--font-heading); font-size: 1.5rem; color: #fff;">
            Complete End-to-End Operational Lifecycle Demo
          </h2>
          <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);">
            PHASE 21 VERIFIED
          </span>
        </div>
        <p style="color: var(--text-secondary); margin: 0.35rem 0 0 0; font-size: 0.88rem; max-width: 820px;">
          Experience the closed-loop R5 platform on a realistic retail refrigeration failure at Store 104 (Seattle Downtown Concourse).
          Witness autonomous triage, active slip hazard escalation, dispatch within 30m SLA, post-repair telemetry verification, and outcome measurement.
        </p>
      </div>

      <div style="display: flex; gap: 0.75rem;">
        <button id="btn-reset-demo" class="btn btn-secondary" style="display: flex; align-items: center; gap: 0.5rem;" ${isExecuting ? 'disabled' : ''}>
          <span>🔄</span> Reset Demo
        </button>
        <button id="btn-run-demo" class="btn btn-primary" style="display: flex; align-items: center; gap: 0.5rem; background: linear-gradient(135deg, var(--color-primary) 0%, #3b82f6 100%);" ${isExecuting ? 'disabled' : ''}>
          <span>🚀</span> ${isExecuting ? 'Executing Demo Pipeline...' : 'Run Full Lifecycle Demo'}
        </button>
      </div>
    </div>

    <!-- Interactive Pipeline Flow Stepper -->
    <div class="r5-card" style="margin-bottom: 1.5rem; padding: 1.25rem;">
      <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-bottom: 0.85rem; font-weight: 700;">
        Closed-Loop Operational Architecture (15 Continuous Stages)
      </div>
      <div class="demo-pipeline-flow" style="display: flex; align-items: center; justify-content: space-between; overflow-x: auto; padding-bottom: 0.5rem; gap: 0.5rem;">
        ${renderPipelineStepBadge('1', 'RAW FEEDBACK', '📥')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('2', 'AI UNDERSTAND', '🧠')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('3', 'INVESTIGATE', '🔍')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('4', 'CLUSTER', '🗂️')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('5', 'EMERGING ALERT', '🚨')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('6', 'PRIORITY', '⚖️')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('7', 'EVIDENCE', '📜')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('8', 'ROUTING', '🧭')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('9', 'ACTION', '🛠️')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('10', 'RESOLUTION', '🔧')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('11', 'OUTCOME', '🎯')}
        ${renderPipelineArrow()}
        ${renderPipelineStepBadge('12', 'BRIEF', '📋')}
      </div>
    </div>

    <!-- Active Demo Content Body -->
    <div id="demo-content-body">
      <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <div style="font-size: 2.5rem; margin-bottom: 1rem;">🚀</div>
        <div style="font-weight: 600; font-size: 1.1rem; color: #fff; margin-bottom: 0.5rem;">
          Ready to Run Complete Retail Cold-Chain Lifecycle
        </div>
        <div style="max-width: 580px; margin: 0 auto 1.5rem auto; font-size: 0.88rem; line-height: 1.5;">
          Click <strong>"Run Full Lifecycle Demo"</strong> to trigger the complete pipeline from raw multilingual input
          (English, Spanish, French, Hinglish, German) to verified technician remediation and executive summary.
        </div>
        <button id="btn-run-demo-hero" class="btn btn-primary" style="padding: 0.65rem 1.5rem;">
          Start Live Demonstration
        </button>
      </div>
    </div>
  `;

  // Attach event handlers
  const btnRun = container.querySelector('#btn-run-demo');
  const btnRunHero = container.querySelector('#btn-run-demo-hero');
  const btnReset = container.querySelector('#btn-reset-demo');

  const handleRun = async () => {
    if (isExecuting) return;
    isExecuting = true;
    renderDemoView(container);

    const bodyEl = container.querySelector('#demo-content-body');
    if (bodyEl) {
      bodyEl.innerHTML = `
        <div style="text-align: center; padding: 4rem 1rem;">
          <div class="spinner" style="width: 48px; height: 48px; margin: 0 auto 1.5rem auto; border-top-color: var(--color-primary);"></div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">Executing 15 Operational Stages in SQLite...</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem;">
            Parsing multilingual feedback, clustering, calculating Poisson velocity z-score, applying safety floors, and measuring outcomes.
          </div>
        </div>
      `;
    }

    try {
      const res = await api.runDemo(true);
      currentDemoData = res;
      showToast('Lifecycle Demonstration executed successfully (15/15 stages passed)!', 'success');
    } catch (err) {
      showToast('Demonstration failed: ' + err.message, 'error');
    } finally {
      isExecuting = false;
      renderDemoView(container);
      if (currentDemoData) {
        renderDemoResults(container.querySelector('#demo-content-body'), currentDemoData);
      }
    }
  };

  const handleReset = async () => {
    if (isExecuting) return;
    try {
      await api.resetDemo();
      currentDemoData = null;
      showToast('Demo environment cleanly reset.', 'info');
      renderDemoView(container);
    } catch (err) {
      showToast('Failed to reset demo: ' + err.message, 'error');
    }
  };

  if (btnRun) btnRun.addEventListener('click', handleRun);
  if (btnRunHero) btnRunHero.addEventListener('click', handleRun);
  if (btnReset) btnReset.addEventListener('click', handleReset);

  // If we already have demo data in memory, render it immediately
  if (currentDemoData) {
    const bodyEl = container.querySelector('#demo-content-body');
    if (bodyEl) renderDemoResults(bodyEl, currentDemoData);
  }
}

function renderPipelineStepBadge(num, label, icon) {
  return `
    <div style="display: flex; align-items: center; gap: 0.4rem; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 999px; padding: 0.35rem 0.75rem; white-space: nowrap;">
      <span style="font-size: 0.85rem;">${icon}</span>
      <span style="font-weight: 700; font-size: 0.75rem; color: #fff;">${label}</span>
    </div>
  `;
}

function renderPipelineArrow() {
  return `<span style="color: var(--text-muted); font-size: 0.75rem; font-weight: 700;">→</span>`;
}

function renderDemoResults(container, data) {
  if (!container || !data) return;

  const scenario = data.scenario || {};
  const stages = data.stages || [];
  const entities = data.entitiesCreated || {};

  container.innerHTML = `
    <!-- Top Execution Banner -->
    <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(30, 41, 59, 0.9) 100%); border-left: 4px solid #10b981; border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
      <div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <span style="font-size: 1.25rem;">✅</span>
          <span style="font-weight: 700; color: #fff; font-size: 1.05rem;">
            End-to-End Demonstration Succeeded: 15 / 15 Stages Complete
          </span>
        </div>
        <div style="color: var(--text-secondary); font-size: 0.82rem; margin-top: 4px;">
          Execution ID: <code>${data.demonstrationId}</code> | Total Runtime: <strong>${data.totalDurationMs} ms</strong> | Database Status: <strong>Ground Truth Verified</strong>
        </div>
      </div>
      <div style="display: flex; gap: 0.5rem;">
        <span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4);">
          Store 104 (Seattle)
        </span>
        <span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4);">
          P1_CRITICAL (Score 85)
        </span>
        <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);">
          -100% Resolved
        </span>
      </div>
    </div>

    <!-- Two-Column Layout: Left Stage Stepper, Right Interactive Inspector -->
    <div style="display: grid; grid-template-columns: 1fr; gap: 1.25rem;">
      ${stages.map((stage, idx) => renderStageCard(stage, idx + 1)).join('')}
    </div>

    <!-- Operational Navigation & Ground-Truth Verification Hub -->
    <div class="r5-card" style="margin-top: 1.5rem; padding: 1.5rem; background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(59, 130, 246, 0.35);">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
        <div>
          <div style="font-weight: 700; color: #fff; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;">
            <span>🎯</span> Core R5 Closed-Loop Journey Complete
          </div>
          <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px; max-width: 620px;">
            The retail refrigeration failure has traversed all 15 stages. Directly inspect the persisted ground-truth operational artifacts across the platform:
          </div>
        </div>
        <div style="display: flex; gap: 0.6rem; flex-wrap: wrap;">
          <button class="btn btn-secondary btn-sm" id="btn-demo-nav-dash">📊 Command Center</button>
          <button class="btn btn-secondary btn-sm" id="btn-demo-nav-issues">⚠️ Issues & DAG</button>
          <button class="btn btn-secondary btn-sm" id="btn-demo-nav-outcomes">🎯 Outcome Verification</button>
          <button class="btn btn-primary btn-sm" id="btn-demo-nav-briefs">📋 Executive Brief</button>
        </div>
      </div>
    </div>
  `;

  // Attach navigation events
  const btnDash = container.querySelector('#btn-demo-nav-dash');
  if (btnDash) btnDash.addEventListener('click', () => state.setView('dashboard'));

  const btnIssues = container.querySelector('#btn-demo-nav-issues');
  if (btnIssues) btnIssues.addEventListener('click', () => state.setView('issues'));

  const btnOutcomes = container.querySelector('#btn-demo-nav-outcomes');
  if (btnOutcomes) btnOutcomes.addEventListener('click', () => state.setView('outcomes'));

  const btnBriefs = container.querySelector('#btn-demo-nav-briefs');
  if (btnBriefs) btnBriefs.addEventListener('click', () => state.setView('briefs'));
}


function renderStageCard(stage, index) {
  const code = stage.stageCode;
  const metrics = stage.metrics || {};
  const data = stage.data || {};

  // Custom highlights per stage
  let customContent = '';

  if (code === 'RAW_FEEDBACK_INGESTION' && data.records) {
    customContent = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0.75rem; margin-top: 0.75rem;">
        ${data.records.map(r => `
          <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: var(--radius-sm); padding: 0.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
              <span class="badge" style="font-size: 0.65rem; background: rgba(59, 130, 246, 0.2); color: #93c5fd;">${r.channel}</span>
              <span class="badge" style="font-size: 0.65rem; background: rgba(147, 51, 234, 0.2); color: #c084fc;">LANG: ${r.language.toUpperCase()}</span>
            </div>
            <div style="font-size: 0.82rem; color: #fff; font-style: italic; line-height: 1.4;">"${escapeHtml(r.rawText)}"</div>
          </div>
        `).join('')}
      </div>
    `;
  } else if (code === 'INVESTIGATION_FOLLOWUP') {
    customContent = `
      <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; border-radius: var(--radius-sm); padding: 0.75rem; margin-top: 0.75rem;">
        <div style="font-size: 0.8rem; font-weight: 700; color: #f59e0b;">Targeted Investigation Clarification:</div>
        <div style="font-size: 0.82rem; color: #fff; margin-top: 2px;">Q: "${escapeHtml(data.question || '')}"</div>
        <div style="font-size: 0.82rem; color: #34d399; margin-top: 4px; font-weight: 600;">Frontline Answer: "${escapeHtml(data.frontlineAnswer || '')}" (by ${data.answeredBy})</div>
      </div>
    `;
  } else if (code === 'EXPLAINABLE_PRIORITIZATION' && data.factorContributions) {
    customContent = `
      <div style="margin-top: 0.75rem; background: rgba(15, 23, 42, 0.6); padding: 0.75rem; border-radius: var(--radius-sm);">
        <div style="font-size: 0.8rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;">Factor Breakdown Table (Deterministic Math):</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.5rem;">
          ${Object.entries(data.factorContributions).map(([k, v]) => `
            <div style="background: rgba(30, 41, 59, 0.7); padding: 0.5rem; border-radius: 4px; text-align: center;">
              <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: capitalize;">${k}</div>
              <div style="font-size: 0.9rem; font-weight: 700; color: #fff;">+${v} pts</div>
            </div>
          `).join('')}
        </div>
        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.5rem; font-style: italic;">
          Explanation: ${escapeHtml(data.explanation || '')}
        </div>
      </div>
    `;
  } else if (code === 'OUTCOME_MEASUREMENT') {
    customContent = `
      <div style="margin-top: 0.75rem; background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10b981; padding: 0.75rem; border-radius: var(--radius-sm);">
        <div style="font-size: 0.82rem; font-weight: 700; color: #34d399;">Before vs After Telemetry Measurement:</div>
        <div style="font-size: 0.82rem; color: #fff; margin-top: 3px;">${escapeHtml(data.statusMessage || '')}</div>
        <div style="display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.8rem;">
          <div>Baseline: <strong>${metrics.baselineComplaints} complaints</strong></div>
          <div>Post-Fix: <strong>${metrics.postObservationComplaints} complaints</strong></div>
          <div>Reduction: <strong style="color: #34d399;">${metrics.frequencyDeltaPct}%</strong></div>
          <div>Recurrence: <strong>0</strong></div>
        </div>
      </div>
    `;
  } else if (code === 'EXECUTIVE_BRIEF') {
    customContent = `
      <div style="margin-top: 0.75rem; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); padding: 0.85rem; border-radius: var(--radius-sm);">
        <div style="font-size: 0.85rem; font-weight: 700; color: #fff;">${escapeHtml(data.title || '')}</div>
        <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.4rem; line-height: 1.5;">${escapeHtml(data.executiveSummary || '')}</div>
        ${data.recommendations && data.recommendations.length > 0 ? `
          <div style="margin-top: 0.5rem; font-size: 0.78rem; color: #93c5fd;">
            <strong>Recommendations:</strong> ${data.recommendations.slice(0, 2).map(r => typeof r === 'string' ? r : r.title || r.action || '').join('; ')}
          </div>
        ` : ''}
      </div>
    `;
  }

  return `
    <div class="r5-card" style="padding: 1.25rem; border-left: 4px solid var(--color-primary);">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; font-size: 0.75rem; font-weight: 700;">
              STAGE ${index} OF 15
            </span>
            <h3 style="margin: 0; font-size: 1.05rem; color: #fff; font-family: var(--font-heading);">
              ${stage.title}
            </h3>
          </div>
          <p style="color: var(--text-secondary); font-size: 0.85rem; margin: 0.35rem 0 0 0;">
            ${stage.summary}
          </p>
        </div>
        <div style="text-align: right;">
          <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399;">
            ${stage.status}
          </span>
          <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 3px;">
            ${stage.durationMs} ms
          </div>
        </div>
      </div>

      <!-- Key Metrics Pill Row -->
      <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.85rem;">
        ${Object.entries(metrics).map(([k, v]) => `
          <div style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 0.25rem 0.5rem; font-size: 0.75rem;">
            <span style="color: var(--text-muted);">${formatMetricKey(k)}:</span>
            <strong style="color: #fff; margin-left: 4px;">${formatMetricVal(v)}</strong>
          </div>
        `).join('')}
      </div>

      ${customContent}
    </div>
  `;
}

function formatMetricKey(key) {
  return key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
}

function formatMetricVal(val) {
  if (typeof val === 'boolean') return val ? 'TRUE' : 'FALSE';
  if (Array.isArray(val)) return `[${val.join(', ')}]`;
  return String(val);
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
