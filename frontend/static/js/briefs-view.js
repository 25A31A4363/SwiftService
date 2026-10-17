/**
 * R5 Operational Intelligence Platform - Phase 14: AI Operational Intelligence Briefs View
 * Generates concise evidence-grounded intelligence summaries for management.
 * All numerical claims strictly originate from deterministic SQL analytics.
 * Recommendations grounded in observed evidence with explicit epistemic tagging.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import {
  escapeHtml,
  renderEmptyStateHtml,
  renderSkeletonCardsHtml,
  renderErrorStateHtml
} from './ui-utils.js';

let activeBrief = null;
let currentEpistemicFilter = 'ALL';
let currentTimeframe = 'DAILY';
let briefHistoryList = [];

export async function renderBriefsView(container) {
  container.innerHTML = `
    <div style="margin-bottom: 1.5rem;">
      ${renderSkeletonCardsHtml(5)}
    </div>
  `;

  try {
    const [latestBrief, history] = await Promise.all([
      api.getLatestBrief(state.selectedStoreId, currentTimeframe),
      api.listBriefs(state.selectedStoreId, 10)
    ]);
    activeBrief = latestBrief;
    briefHistoryList = history || [];
    renderBriefContent(container);
  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Operational Intelligence Brief Unavailable',
      message: err.message || 'Unable to synthesize deterministic operational intelligence.',
      onRetryId: 'btn-retry-briefs'
    });
    container.querySelector('#btn-retry-briefs')?.addEventListener('click', () => {
      renderBriefsView(container);
    });
  }
}

function renderBriefContent(container) {
  if (!activeBrief) {
    container.innerHTML = `
      <div style="margin-top: 2rem;">
        ${renderEmptyStateHtml({
          icon: '📋',
          title: 'No Operational Briefs Found',
          desc: 'Generate your first evidence-grounded intelligence summary for executive leadership based on deterministic operational telemetry.',
          actionLabel: 'Generate Operational Brief',
          actionId: 'btn-generate-initial'
        })}
      </div>
    `;
    const btn = document.getElementById('btn-generate-initial');
    if (btn) btn.addEventListener('click', () => openGenerateBriefModal(container));
    return;
  }

  const b = activeBrief;
  const metrics = b.deterministicMetrics || {};
  const claims = b.labeledClaims || [];

  // Filter claims based on active epistemic pill
  const filteredClaims = claims.filter(c => {
    if (currentEpistemicFilter === 'ALL') return true;
    return c.type === currentEpistemicFilter;
  });

  const countObs = claims.filter(c => c.type === 'OBSERVATION').length;
  const countHyp = claims.filter(c => c.type === 'HYPOTHESIS').length;
  const countRec = claims.filter(c => c.type === 'RECOMMENDATION').length;
  const countUnk = claims.filter(c => c.type === 'UNKNOWN').length;

  container.innerHTML = `
    <!-- Top Action & Filter Header -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 1rem;">
      <div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <h2 style="font-size: 1.4rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.02em;">
            📋 Operational Intelligence Briefs
          </h2>
          <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-primary); border: 1px solid rgba(59, 130, 246, 0.3);">
            Phase 14 Grounded Core
          </span>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
          Deterministic executive briefings with strict epistemic labeling • Zero hallucinated statistics
        </div>
      </div>

      <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
        <!-- Timeframe Selector -->
        <div class="r5-tab-group" style="padding: 2px;">
          <button class="r5-tab-btn ${currentTimeframe === 'DAILY' ? 'active' : ''}" data-tf="DAILY">Daily (24h)</button>
          <button class="r5-tab-btn ${currentTimeframe === 'WEEKLY' ? 'active' : ''}" data-tf="WEEKLY">Weekly (7d)</button>
          <button class="r5-tab-btn ${currentTimeframe === 'CUSTOM' ? 'active' : ''}" data-tf="CUSTOM">Custom</button>
        </div>

        <!-- History Selector -->
        ${briefHistoryList.length > 1 ? `
          <select id="select-brief-history" class="form-control" style="font-size: 0.85rem; max-width: 200px;">
            ${briefHistoryList.map(item => `
              <option value="${item.id}" ${item.id === b.id ? 'selected' : ''}>
                ${item.timeframeType} • ${item.createdAt.slice(5, 16).replace('T', ' ')}
              </option>
            `).join('')}
          </select>
        ` : ''}

        <button id="btn-open-generate" class="btn btn-primary" style="display: flex; align-items: center; gap: 0.4rem;">
          <span>⚡</span>
          <span>Generate Brief</span>
        </button>

        <button id="btn-print-brief" class="btn btn-secondary" title="Print Brief for Operations Meeting">
          <span>🖨️</span>
        </button>
      </div>
    </div>

    <!-- Executive Summary Banner -->
    <div class="r5-card brief-exec-banner" style="background: linear-gradient(135deg, rgba(26, 34, 52, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(59, 130, 246, 0.3); box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4); margin-bottom: 1.5rem; position: relative; overflow: hidden;">
      <div style="position: absolute; top: -40px; right: -40px; width: 140px; height: 140px; background: radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%); border-radius: 50%; pointer-events: none;"></div>
      <div class="r5-card-body" style="padding: 1.5rem 1.75rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
              <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--p4-low); font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.3);">
                DETERMINISTIC INTELLIGENCE VERIFIED
              </span>
              <span style="font-size: 0.8rem; color: var(--text-muted);">
                Window: <strong>${b.startDate.slice(0, 10)}</strong> to <strong>${b.endDate.slice(0, 10)}</strong>
              </span>
            </div>
            <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); margin: 0;">
              ${b.title}
            </h3>
          </div>
          <div style="text-align: right; font-size: 0.8rem; color: var(--text-muted);">
            <div>Generated: <strong>${b.createdAt.slice(0, 16).replace('T', ' ')} UTC</strong></div>
            <div>Scope: <strong>${b.storeName || 'Enterprise'}</strong></div>
          </div>
        </div>

        <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.6; margin: 0 0 1.25rem 0; font-weight: 400; max-width: 1100px;">
          ${b.executiveSummary}
        </p>

        <!-- KPI Strip -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.08);">
          <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Feedback Volume</div>
            <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin-top: 2px;">
              ${metrics.total_feedback || 0}
              <span style="font-size: 0.75rem; font-weight: 600; color: ${(metrics.feedback_delta || 0) >= 0 ? 'var(--p2-high)' : 'var(--p4-low)'};">
                (${(metrics.feedback_delta || 0) >= 0 ? '+' : ''}${metrics.feedback_delta || 0})
              </span>
            </div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">New / Resolved Issues</div>
            <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin-top: 2px;">
              <span style="color: var(--p2-high);">${metrics.new_issues_count || 0}</span>
              <span style="color: var(--text-muted); font-size: 0.9rem;">/</span>
              <span style="color: var(--p4-low);">${metrics.resolved_issues_count || 0}</span>
            </div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">SLA Compliance</div>
            <div style="font-size: 1.25rem; font-weight: 800; color: ${(metrics.sla_compliance_rate_pct || 100) >= 90 ? 'var(--p4-low)' : 'var(--p1-critical)'}; margin-top: 2px;">
              ${(metrics.sla_compliance_rate_pct !== undefined ? metrics.sla_compliance_rate_pct : 100.0).toFixed(1)}%
            </div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Active Backlog</div>
            <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin-top: 2px;">
              ${metrics.active_backlog_count || 0}
              ${(metrics.p1_critical_count || 0) > 0 ? `
                <span class="badge" style="background: var(--p1-critical-bg); color: var(--p1-critical); font-size: 0.7rem; margin-left: 4px;">
                  ${metrics.p1_critical_count} P1
                </span>
              ` : ''}
            </div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Interventions Evaluated</div>
            <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin-top: 2px;">
              ${metrics.evaluated_outcomes_count || 0}
              <span style="font-size: 0.75rem; font-weight: 600; color: var(--p4-low);">
                (${metrics.improved_outcomes_count || 0} improved)
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Epistemic Claim Filter Toolbar -->
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 0.75rem; background: var(--bg-surface); padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
      <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text-secondary); font-weight: 600;">
        <span>Epistemic Grounding Filter:</span>
      </div>
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
        <button class="epistemic-filter-pill ${currentEpistemicFilter === 'ALL' ? 'active' : ''}" data-type="ALL">
          All Claims (${claims.length})
        </button>
        <button class="epistemic-filter-pill pill-observation ${currentEpistemicFilter === 'OBSERVATION' ? 'active' : ''}" data-type="OBSERVATION">
          🟢 Observation (${countObs})
        </button>
        <button class="epistemic-filter-pill pill-hypothesis ${currentEpistemicFilter === 'HYPOTHESIS' ? 'active' : ''}" data-type="HYPOTHESIS">
          🟣 Hypothesis (${countHyp})
        </button>
        <button class="epistemic-filter-pill pill-recommendation ${currentEpistemicFilter === 'RECOMMENDATION' ? 'active' : ''}" data-type="RECOMMENDATION">
          🔵 Recommendation (${countRec})
        </button>
        <button class="epistemic-filter-pill pill-unknown ${currentEpistemicFilter === 'UNKNOWN' ? 'active' : ''}" data-type="UNKNOWN">
          🟡 Unknown (${countUnk})
        </button>
      </div>
    </div>

    <!-- Active Filter Notice if filtered -->
    ${currentEpistemicFilter !== 'ALL' ? `
      <div class="r5-card" style="margin-bottom: 1.5rem; background: rgba(30, 41, 59, 0.4); border-left: 4px solid var(--accent-primary);">
        <div class="r5-card-body" style="padding: 0.75rem 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 0.85rem; color: var(--text-primary);">
              Displaying ${filteredClaims.length} statements labeled strictly as <strong>${currentEpistemicFilter}</strong> across all brief sections.
            </div>
            <button id="btn-reset-filter" class="btn btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">Reset Filter</button>
          </div>
          <div style="display: flex; flex-direction: column; gap: 0.4rem; margin-top: 0.75rem;">
            ${filteredClaims.map(c => `
              <div style="background: rgba(15, 23, 42, 0.6); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;">
                <div style="font-size: 0.85rem; color: #f8fafc;">${c.statement}</div>
                <div style="display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;">
                  <span class="badge" style="font-size: 0.7rem; font-family: var(--font-family-mono); background: rgba(255, 255, 255, 0.05); color: var(--text-muted);">${c.groundingSource}</span>
                  <span class="badge" style="font-size: 0.7rem; color: var(--accent-cyan); font-weight: 700;">${Math.round(c.confidence * 100)}% conf</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    ` : ''}

    <!-- 10 Mandatory Intelligence Sections Grid -->
    <div style="display: flex; flex-direction: column; gap: 1.5rem;">

      <!-- SECTION 1: What Changed -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">📊</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              1. What Changed (Telemetry Deltas & Shifts)
            </h4>
          </div>
          <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--p4-low);">OBSERVATION</span>
        </div>
        <div class="r5-card-body">
          <p style="color: var(--text-primary); font-size: 0.9rem; line-height: 1.5; margin-bottom: 1rem;">
            ${b.whatChanged.summaryText || 'Telemetry analysis complete.'}
          </p>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 1rem;">
            <div style="background: rgba(15, 23, 42, 0.5); padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-size: 0.75rem; color: var(--text-muted);">Feedback Delta</div>
              <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">
                ${b.whatChanged.feedbackVolumeDelta >= 0 ? '+' : ''}${b.whatChanged.feedbackVolumeDelta} 
                <span style="font-size: 0.8rem; font-weight: 500; color: var(--text-secondary);">(${b.whatChanged.feedbackVolumeChangePct >= 0 ? '+' : ''}${b.whatChanged.feedbackVolumeChangePct}%)</span>
              </div>
            </div>

            <div style="background: rgba(15, 23, 42, 0.5); padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-size: 0.75rem; color: var(--text-muted);">SLA Shift</div>
              <div style="font-size: 1.1rem; font-weight: 700; color: ${b.whatChanged.slaShiftPct >= 0 ? 'var(--p4-low)' : 'var(--p1-critical)'};">
                ${b.whatChanged.slaShiftPct >= 0 ? '+' : ''}${b.whatChanged.slaShiftPct}%
              </div>
            </div>

            <div style="background: rgba(15, 23, 42, 0.5); padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-size: 0.75rem; color: var(--text-muted);">Sentiment Shift</div>
              <div style="font-size: 1.1rem; font-weight: 700; color: ${b.whatChanged.sentimentShift >= 0 ? 'var(--p4-low)' : 'var(--p1-critical)'};">
                ${b.whatChanged.sentimentShift >= 0 ? '+' : ''}${b.whatChanged.sentimentShift}
              </div>
            </div>
          </div>

          ${(b.whatChanged.operatingStatusChanges && b.whatChanged.operatingStatusChanges.length > 0) ? `
            <div style="margin-top: 0.75rem; border-top: 1px solid var(--border-subtle); padding-top: 0.75rem;">
              <div style="font-size: 0.8rem; font-weight: 600; color: var(--p2-high); margin-bottom: 0.4rem;">
                ⚠️ Physical Store Operating Status Alterations:
              </div>
              ${b.whatChanged.operatingStatusChanges.map(sc => `
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
                  • <strong>${sc.storeName}</strong>: <span class="badge" style="background: var(--p2-high-bg); color: var(--p2-high); font-size: 0.7rem;">${sc.operatingStatus}</span> - ${sc.notice}
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>
      </div>

      <!-- SECTION 2: Emerging Issues -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">⚡</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              2. Emerging Issues (Velocity Anomalies & Early Bursts)
            </h4>
          </div>
          <span class="badge" style="background: rgba(249, 115, 22, 0.15); color: var(--p2-high);">STATISTICAL ANOMALY</span>
        </div>
        <div class="r5-card-body">
          ${(!b.emergingIssues || b.emergingIssues.length === 0) ? `
            <div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic;">
              No statistical velocity anomalies (z-score > 1.8) detected in this window. Operating within baseline variation.
            </div>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 0.6rem;">
              ${b.emergingIssues.map(ei => `
                <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                  <div style="flex: 1; min-width: 250px;">
                    <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary);">${ei.title}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
                      ${ei.whyGenerated}
                    </div>
                  </div>
                  <div style="display: flex; align-items: center; gap: 0.6rem;">
                    <span class="badge" style="background: rgba(249, 115, 22, 0.15); color: var(--p2-high); font-weight: 700;">
                      z-score ${ei.velocityZscore.toFixed(2)}
                    </span>
                    <span class="badge" style="background: rgba(255, 255, 255, 0.05); color: var(--text-secondary);">
                      ${ei.observationCount} observations
                    </span>
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>
      </div>

      <!-- SECTION 3: Highest-Priority Issues -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">🚨</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              3. Highest-Priority Issues (Multi-Factor Scoring)
            </h4>
          </div>
          <span class="badge" style="background: rgba(239, 68, 68, 0.15); color: var(--p1-critical);">EXPLAINABLE RANKING</span>
        </div>
        <div class="r5-card-body">
          ${(!b.highestPriorityIssues || b.highestPriorityIssues.length === 0) ? `
            <div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic;">No active P1/P2 issues.</div>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${b.highestPriorityIssues.map(pi => `
                <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid ${pi.priorityTier === 'P1_CRITICAL' ? 'rgba(239, 68, 68, 0.3)' : 'var(--border-subtle)'};">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.35rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                      <span class="badge priority-${pi.priorityTier.toLowerCase()}">${pi.priorityTier}</span>
                      <strong style="color: var(--text-primary); font-size: 0.95rem;">${pi.title}</strong>
                      ${pi.isSafetyHazard ? `
                        <span class="badge" style="background: var(--p1-critical-bg); color: var(--p1-critical); border: 1px solid var(--p1-critical-border);">
                          ⚠️ SAFETY HAZARD
                        </span>
                      ` : ''}
                    </div>
                    <div style="font-family: var(--font-family-mono); font-size: 0.8rem; color: var(--accent-cyan); font-weight: 700;">
                      Score ${pi.priorityScore}
                    </div>
                  </div>
                  <div style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 0.4rem;">
                    ${pi.explainableSummary}
                  </div>
                  <div style="display: flex; gap: 1rem; font-size: 0.78rem; color: var(--text-muted);">
                    <div>Assigned: <strong style="color: var(--text-primary);">${pi.assignedTeamName || 'Unassigned'}</strong></div>
                    <div>Status: <strong style="color: var(--text-primary);">${pi.status}</strong></div>
                    ${pi.slaDeadline ? `<div>SLA: <strong style="color: var(--text-primary);">${pi.slaDeadline.slice(11, 16)} UTC</strong></div>` : ''}
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>
      </div>

      <!-- SECTION 4: Affected Locations -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">📍</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              4. Affected Locations (Facility & Zone Concentration)
            </h4>
          </div>
          <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--p4-low);">OBSERVATION</span>
        </div>
        <div class="r5-card-body">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 0.75rem;">
            ${(b.affectedLocations || []).map(al => `
              <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: 700; color: var(--text-primary); font-size: 0.9rem;">${al.storeName}</div>
                  <div style="font-size: 0.8rem; color: var(--text-muted);">${al.departmentName || 'Facility-Wide Zone'}</div>
                </div>
                <div style="text-align: right;">
                  <span class="badge" style="background: ${al.riskLevel === 'HIGH' ? 'var(--p1-critical-bg)' : al.riskLevel === 'MEDIUM' ? 'var(--p2-high-bg)' : 'var(--p4-low-bg)'}; color: ${al.riskLevel === 'HIGH' ? 'var(--p1-critical)' : al.riskLevel === 'MEDIUM' ? 'var(--p2-high)' : 'var(--p4-low)'};">
                    ${al.riskLevel} RISK
                  </span>
                  <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 3px;">
                    ${al.incidentCount} issues • ${al.feedbackCount} feedback
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- SECTION 5: Evidence -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">🔎</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              5. Concrete Evidence (Verbatim Frontline & Customer Citations)
            </h4>
          </div>
          <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--p4-low);">UNALTERED EVIDENCE</span>
        </div>
        <div class="r5-card-body">
          <div style="display: flex; flex-direction: column; gap: 0.6rem;">
            ${(b.evidence || []).map(ev => `
              <div style="background: rgba(15, 23, 42, 0.4); padding: 0.6rem 0.8rem; border-left: 3px solid var(--accent-primary); border-radius: var(--radius-sm); font-size: 0.85rem;">
                <div style="color: #f1f5f9; font-style: italic; margin-bottom: 0.25rem;">
                  "${ev.verbatimQuote}"
                </div>
                <div style="display: flex; gap: 0.75rem; font-size: 0.75rem; color: var(--text-muted);">
                  <span>Channel: <strong>${ev.channelType}</strong></span>
                  <span>Store: <strong>${ev.storeName}</strong></span>
                  <span>Time: <strong>${ev.timestamp.slice(11, 16)} UTC</strong></span>
                  ${ev.sentimentScore !== null ? `<span>Sentiment: <strong style="color: ${ev.sentimentScore < 0 ? 'var(--p1-critical)' : 'var(--p4-low)'};">${ev.sentimentScore}</strong></span>` : ''}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- SECTION 6: Possible Explanations / Hypotheses -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">💡</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              6. Possible Explanations & Root-Cause Hypotheses
            </h4>
          </div>
          <span class="badge" style="background: rgba(139, 92, 246, 0.15); color: var(--accent-purple);">HYPOTHESIS</span>
        </div>
        <div class="r5-card-body">
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            ${(b.hypotheses || []).map(h => `
              <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
                  <strong style="color: #e2e8f0; font-size: 0.92rem;">${h.hypothesis}</strong>
                  <span class="badge" style="background: rgba(139, 92, 246, 0.2); color: var(--accent-purple); font-weight: 700;">
                    ${Math.round(h.confidence * 100)}% Confidence
                  </span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.35rem;">
                  <strong>Supporting Observations:</strong>
                </div>
                <ul style="margin: 0 0 0.5rem 1.25rem; padding: 0; font-size: 0.82rem; color: var(--text-secondary);">
                  ${h.supportingObservations.map(so => `<li>${so}</li>`).join('')}
                </ul>
                ${h.uncertainties && h.uncertainties.length > 0 ? `
                  <div style="font-size: 0.75rem; color: var(--p3-medium); background: rgba(234, 179, 8, 0.08); padding: 0.35rem 0.6rem; border-radius: var(--radius-sm);">
                    ⚠️ <strong>Uncertainties:</strong> ${h.uncertainties.join('; ')}
                  </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- SECTION 7: Recommended Actions -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">🎯</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              7. Recommended Actions (Evidence-Grounded Directives)
            </h4>
          </div>
          <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-primary);">RECOMMENDATION</span>
        </div>
        <div class="r5-card-body">
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            ${(b.recommendedActions || []).map(ra => `
              <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
                <div style="flex: 1; min-width: 280px;">
                  <div style="font-weight: 700; color: var(--text-primary); font-size: 0.95rem;">
                    ${ra.recommendation}
                  </div>
                  <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 2px;">
                    ${ra.groundedRationale}
                  </div>
                  <div style="display: flex; gap: 0.75rem; font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
                    <span>Assigned Team: <strong style="color: var(--text-primary);">${ra.targetTeamName}</strong></span>
                    <span>Urgency: <strong style="color: var(--accent-primary);">${ra.urgencyTier}</strong></span>
                  </div>
                </div>
                <div>
                  ${ra.requiresApproval ? `
                    <span class="badge" style="background: var(--p2-high-bg); color: var(--p2-high); border: 1px solid var(--p2-high-border);">
                      HUMAN APPROVAL REQUIRED
                    </span>
                  ` : `
                    <span class="badge" style="background: var(--p4-low-bg); color: var(--p4-low); border: 1px solid var(--p4-low-border);">
                      DIRECT DISPATCH
                    </span>
                  `}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- SECTION 8: Uncertainty -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">❓</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              8. Uncertainty (Explicit Operational Unknowns & Data Gaps)
            </h4>
          </div>
          <span class="badge" style="background: rgba(234, 179, 8, 0.15); color: var(--p3-medium);">UNKNOWN</span>
        </div>
        <div class="r5-card-body">
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            ${(b.uncertainties || []).map(u => `
              <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border-left: 3px solid var(--p3-medium);">
                <div style="font-weight: 700; color: #fef08a; font-size: 0.9rem; margin-bottom: 0.25rem;">
                  [UNKNOWN] ${u.area}
                </div>
                <div style="font-size: 0.85rem; color: #e2e8f0; margin-bottom: 0.4rem;">
                  ${u.description}
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.5rem; font-size: 0.78rem; background: rgba(0, 0, 0, 0.2); padding: 0.5rem; border-radius: var(--radius-sm);">
                  <div><strong style="color: var(--p1-critical);">Risk of Inaction:</strong> ${u.riskOfInaction}</div>
                  <div><strong style="color: var(--accent-cyan);">Missing Information:</strong> ${u.missingInformation}</div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- SECTION 9: Unresolved Issues -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">⏳</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              9. Unresolved Issues Backlog
            </h4>
          </div>
          <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--p4-low);">OBSERVATION</span>
        </div>
        <div class="r5-card-body">
          <div class="r5-table-container">
            <table class="r5-table">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Backlog Age</th>
                  <th>Assigned Team</th>
                  <th>SLA State</th>
                </tr>
              </thead>
              <tbody>
                ${(b.unresolvedIssues || []).map(ui => `
                  <tr>
                    <td><span class="badge priority-${ui.priorityTier.toLowerCase()}">${ui.priorityTier}</span></td>
                    <td><strong>${ui.title}</strong></td>
                    <td>${ui.status}</td>
                    <td>${ui.ageHours} hrs</td>
                    <td>${ui.assignedTeamName || 'Unassigned'}</td>
                    <td>
                      <span class="badge" style="background: ${ui.slaStatus === 'BREACHED' ? 'var(--p1-critical-bg)' : ui.slaStatus === 'AT_RISK' ? 'var(--p2-high-bg)' : 'var(--p4-low-bg)'}; color: ${ui.slaStatus === 'BREACHED' ? 'var(--p1-critical)' : ui.slaStatus === 'AT_RISK' ? 'var(--p2-high)' : 'var(--p4-low)'};">
                        ${ui.slaStatus}
                      </span>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- SECTION 10: Outcome of Previous Interventions -->
      <div class="r5-card">
        <div class="r5-card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">📈</span>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              10. Outcome of Previous Interventions (Phase 12 Integration)
            </h4>
          </div>
          <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-primary);">VERIFIED OUTCOMES</span>
        </div>
        <div class="r5-card-body">
          ${(!b.interventionOutcomes || b.interventionOutcomes.length === 0) ? `
            <div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic;">
              No post-intervention measurements recorded yet.
            </div>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${b.interventionOutcomes.map(io => `
                <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
                  <div style="flex: 1; min-width: 260px;">
                    <div style="font-weight: 700; color: var(--text-primary); font-size: 0.95rem;">
                      ${io.issueTitle}
                    </div>
                    <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 2px;">
                      ${io.statusMessage}
                    </div>
                  </div>
                  <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span class="badge" style="background: ${io.outcomeStatus === 'Improved' ? 'rgba(16, 185, 129, 0.15)' : io.outcomeStatus === 'Inconclusive' ? 'rgba(234, 179, 8, 0.15)' : io.outcomeStatus === 'Worsened' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(148, 163, 184, 0.15)'}; color: ${io.outcomeStatus === 'Improved' ? 'var(--p4-low)' : io.outcomeStatus === 'Inconclusive' ? 'var(--p3-medium)' : io.outcomeStatus === 'Worsened' ? 'var(--p1-critical)' : 'var(--text-secondary)'}; font-weight: 700;">
                      ${io.outcomeStatus.toUpperCase()}
                    </span>
                    <span style="font-size: 0.8rem; font-family: var(--font-family-mono); color: var(--accent-cyan);">
                      ${io.frequencyChangePct >= 0 ? '+' : ''}${io.frequencyChangePct}% freq
                    </span>
                    <span class="badge" style="background: rgba(255, 255, 255, 0.05); color: var(--text-muted); font-size: 0.75rem;">
                      ${Math.round(io.confidence * 100)}% conf
                    </span>
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>
      </div>

    </div>
  `;

  // Attach Event Listeners
  attachBriefEventListeners(container);
}

function attachBriefEventListeners(container) {
  // Timeframe selector
  container.querySelectorAll('.r5-tab-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const tf = e.target.getAttribute('data-tf');
      if (tf === currentTimeframe) return;
      currentTimeframe = tf;
      await renderBriefsView(container);
    });
  });

  // Epistemic filter pills
  container.querySelectorAll('.epistemic-filter-pill').forEach(pill => {
    pill.addEventListener('click', (e) => {
      const type = e.target.getAttribute('data-type');
      currentEpistemicFilter = type;
      renderBriefContent(container);
    });
  });

  // Reset filter button
  const btnReset = document.getElementById('btn-reset-filter');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      currentEpistemicFilter = 'ALL';
      renderBriefContent(container);
    });
  }

  // History selector
  const selHistory = document.getElementById('select-brief-history');
  if (selHistory) {
    selHistory.addEventListener('change', async (e) => {
      const briefId = e.target.value;
      try {
        activeBrief = await api.getBriefById(briefId);
        renderBriefContent(container);
      } catch (err) {
        showToast('Failed to load historical brief: ' + err.message, 'error');
      }
    });
  }

  // Generate brief button
  const btnGen = document.getElementById('btn-open-generate');
  if (btnGen) {
    btnGen.addEventListener('click', () => openGenerateBriefModal(container));
  }

  // Print button
  const btnPrint = document.getElementById('btn-print-brief');
  if (btnPrint) {
    btnPrint.addEventListener('click', () => {
      window.print();
    });
  }
}

function openGenerateBriefModal(container) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="r5-modal-backdrop" id="modal-backdrop">
      <div class="r5-modal" style="max-width: 520px;">
        <div class="r5-modal-header" style="display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; font-size: 1.15rem; color: var(--text-primary); font-weight: 700;">
            Generate Intelligence Brief
          </h3>
          <button id="btn-close-brief-modal" class="btn btn-secondary" style="padding: 0.2rem 0.5rem;">✕</button>
        </div>

        <form id="form-generate-brief">
          <div class="r5-modal-body" style="display: flex; flex-direction: column; gap: 1rem;">
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0;">
              Runs deterministic SQL analytics to produce a 10-section grounded operational summary.
            </p>

            <div class="form-group">
              <label class="form-label">Reporting Timeframe</label>
              <select id="modal-timeframe-type" class="form-control">
                <option value="DAILY" selected>DAILY (Past 24 Hours)</option>
                <option value="WEEKLY">WEEKLY (Past 7 Days)</option>
                <option value="CUSTOM">CUSTOM Time Window</option>
              </select>
            </div>

            <div id="modal-custom-dates" style="display: none; flex-direction: column; gap: 0.75rem;">
              <div class="form-group">
                <label class="form-label">Start Date & Time (UTC)</label>
                <input type="datetime-local" id="modal-start-date" class="form-control" />
              </div>
              <div class="form-group">
                <label class="form-label">End Date & Time (UTC)</label>
                <input type="datetime-local" id="modal-end-date" class="form-control" />
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Operational Scope</label>
              <select id="modal-store-id" class="form-control">
                <option value="">All Stores (Enterprise Network-Wide)</option>
                ${(state.stores || []).map(st => `
                  <option value="${st.id}" ${st.id === state.selectedStoreId ? 'selected' : ''}>
                    ${st.name} (#${st.storeNumber})
                  </option>
                `).join('')}
              </select>
            </div>
          </div>

          <div class="r5-modal-footer" style="display: flex; justify-content: flex-end; gap: 0.75rem;">
            <button type="button" id="btn-cancel-brief-modal" class="btn btn-secondary">Cancel</button>
            <button type="submit" id="btn-submit-generate" class="btn btn-primary">
              Generate Intelligence Brief
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const tfSelect = document.getElementById('modal-timeframe-type');
  const customDatesDiv = document.getElementById('modal-custom-dates');
  tfSelect.addEventListener('change', (e) => {
    if (e.target.value === 'CUSTOM') {
      customDatesDiv.style.display = 'flex';
    } else {
      customDatesDiv.style.display = 'none';
    }
  });

  const closeBtn = document.getElementById('btn-close-brief-modal');
  const cancelBtn = document.getElementById('btn-cancel-brief-modal');
  const closeModal = () => { modalContainer.innerHTML = ''; };
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  const form = document.getElementById('form-generate-brief');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById('btn-submit-generate');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analyzing Database...';

    const tf = tfSelect.value;
    const storeIdVal = document.getElementById('modal-store-id').value || null;

    let startDateVal = null;
    let endDateVal = null;
    if (tf === 'CUSTOM') {
      const s = document.getElementById('modal-start-date').value;
      const ed = document.getElementById('modal-end-date').value;
      if (s) startDateVal = new Date(s).toISOString();
      if (ed) endDateVal = new Date(ed).toISOString();
    }

    try {
      const generated = await api.generateBrief({
        timeframeType: tf,
        storeId: storeIdVal,
        startDate: startDateVal,
        endDate: endDateVal
      });

      closeModal();
      activeBrief = generated;
      currentTimeframe = tf;
      showToast('Operational Intelligence Brief generated successfully!', 'success');
      await renderBriefsView(container);
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Generate Intelligence Brief';
      showToast('Generation failed: ' + err.message, 'error');
    }
  });
}
