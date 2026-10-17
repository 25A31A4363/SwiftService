/**
 * R5 Operational Intelligence Platform - Main Application Controller
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import { NAV_ITEMS, NAV_SECTIONS, ROLE_PRESETS, canAccessView } from './rbac.js';
import {
  renderOrgHierarchyView,
  renderTeamsView,
  renderUsersView,
  renderOwnershipView,
  renderRolesView
} from './hierarchy-views.js';
import { renderFeedbackView, openSubmitFeedbackModal } from './feedback-view.js';
import { renderOutcomesView } from './outcomes-view.js';
import { renderBriefsView } from './briefs-view.js';
import { renderDemoView } from './demo-view.js';

// DOM Elements
const elApp = document.getElementById('app');
const elModalContainer = document.getElementById('modal-container');

/* -------------------------------------------------------------------------
   ENTERPRISE UI UTILITIES & ACCESSIBILITY HELPERS
-------------------------------------------------------------------------- */
export {
  escapeHtml,
  renderEmptyStateHtml,
  renderSkeletonCardsHtml,
  renderSkeletonTableHtml,
  renderErrorStateHtml
} from './ui-utils.js';

import {
  escapeHtml,
  renderEmptyStateHtml,
  renderSkeletonCardsHtml,
  renderSkeletonTableHtml,
  renderErrorStateHtml
} from './ui-utils.js';

async function init() {
  // Apply saved theme preference (default: dark)
  const savedTheme = localStorage.getItem('r5_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  state.subscribe(render);

  if (state.token) {
    try {
      // Validate session with backend source of truth
      const me = await api.getMe();
      state.user = me;
      localStorage.setItem('r5_user', JSON.stringify(me));
      await loadInitialData();
    } catch (err) {
      console.warn('Session verification failed, prompting login:', err);
      state.setAuth(null, null);
    }
  } else {
    // Unauthenticated: display secure login view (no silent fallback)
    render();
  }
}


async function loadInitialData() {
  try {
    const [orgs, regions, stores, teams, alerts, issues] = await Promise.all([
      api.getOrganizations(),
      api.getRegions(state.selectedOrgId),
      api.getStores(state.selectedOrgId, state.selectedRegionId),
      api.getTeams(state.selectedStoreId),
      api.getAlerts(state.selectedStoreId),
      api.getIssues(state.selectedStoreId)
    ]);

    state.organizations = orgs;
    state.regions = regions;
    state.stores = stores;
    state.teams = teams;
    state.activeAlertsCount = alerts.filter(a => !a.isAcknowledged).length;
    state.p1Count = issues.filter(i => i.priorityTier === 'P1_CRITICAL' && i.status !== 'CLOSED').length;

    if (!state.selectedOrgId && orgs.length > 0) state.selectedOrgId = orgs[0].id;
    if (!state.selectedRegionId && regions.length > 0) state.selectedRegionId = regions[0].id;
    if (!state.selectedStoreId && stores.length > 0) state.selectedStoreId = stores[0].id;

    state.notify();
  } catch (err) {
    console.error('Error loading initial data:', err);
  }
}

function render() {
  if (!state.token || !state.user) {
    renderLoginModal();
    return;
  }
  closeModal();

  elApp.innerHTML = `
    <!-- Mobile Backdrop -->
    <div id="sidebar-backdrop" class="sidebar-backdrop"></div>

    <!-- Sidebar Navigation -->
    <aside class="app-sidebar" id="app-sidebar" role="navigation" aria-label="Operations Navigation">
      <div class="sidebar-header">
        <div class="brand-badge">R5</div>
        <div class="brand-title-group">
          <h1>R5 Intelligence</h1>
          <div class="brand-subtitle">Retail Ops Platform</div>
        </div>
      </div>

      <nav class="sidebar-nav">
        ${NAV_SECTIONS.map(section => {
          const items = NAV_ITEMS.filter(item => item.section === section.id && canAccessView(state.user.role, item.id));
          if (items.length === 0) return '';
          return `
            <div class="nav-section-group">
              <div class="nav-section-label">${section.label}</div>
              ${items.map(item => {
                const isActive = state.currentView === item.id;
                const isHighlight = item.highlight ? 'nav-demo-highlight' : '';
                const alertBadge = (item.id === 'alerts' && state.activeAlertsCount > 0)
                  ? `<span class="nav-badge" aria-label="${state.activeAlertsCount} active alerts">${state.activeAlertsCount}</span>`
                  : (item.badgeText ? `<span class="nav-badge-pill" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);">${item.badgeText}</span>` : '');
                return `
                  <a class="nav-item ${isActive ? 'active' : ''} ${isHighlight}" data-view="${item.id}" role="button" tabindex="0" aria-current="${isActive ? 'page' : 'false'}">
                    <span class="nav-item-icon">${item.icon}</span>
                    <span>${item.label}</span>
                    ${alertBadge}
                  </a>
                `;
              }).join('')}
            </div>
          `;
        }).join('')}
      </nav>

      <div class="sidebar-footer">
        <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.5rem;">Quick Role Switcher (Demo):</div>
        <button id="btn-open-role-switcher" class="btn btn-secondary btn-sm" style="width: 100%;">
          🔄 Switch Active Role
        </button>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="app-main" role="main">
      <!-- Topbar Context Bar -->
      <header class="app-topbar" role="banner">
        <div class="topbar-context-group">
          <!-- Mobile Drawer Toggle -->
          <button class="btn-mobile-sidebar-toggle" id="btn-toggle-sidebar" aria-label="Toggle Navigation Sidebar">
            ☰
          </button>

          <!-- Org Context -->
          <div class="context-selector-box">
            <span class="context-selector-label">Org:</span>
            <select id="select-org" class="context-select" aria-label="Select Organization Context">
              ${state.organizations.map(o => `
                <option value="${o.id}" ${o.id === state.selectedOrgId ? 'selected' : ''}>${escapeHtml(o.name)}</option>
              `).join('')}
            </select>
          </div>

          <!-- Region Context -->
          <div class="context-selector-box">
            <span class="context-selector-label">Region:</span>
            <select id="select-region" class="context-select" aria-label="Select Region Context">
              ${state.regions.map(r => `
                <option value="${r.id}" ${r.id === state.selectedRegionId ? 'selected' : ''}>${escapeHtml(r.name)}</option>
              `).join('')}
            </select>
          </div>

          <!-- Store Context -->
          <div class="context-selector-box">
            <span class="context-selector-label">Store:</span>
            <select id="select-store" class="context-select" aria-label="Select Store Facility">
              ${state.stores.map(s => `
                <option value="${s.id}" ${s.id === state.selectedStoreId ? 'selected' : ''}>#${s.storeNumber} - ${escapeHtml(s.name)}</option>
              `).join('')}
            </select>
          </div>

          <!-- Fast-Track E2E Demo Button -->
          <button id="btn-topbar-demo" class="topbar-demo-btn" title="Open Complete 15-Stage Closed-Loop Retail Demo">
            <span>🚀</span> Live E2E Demo
          </button>
        </div>

        <div class="topbar-actions-group">
          <!-- Theme Toggle (Dark / Light Enterprise Mode) -->
          <button id="btn-theme-toggle" class="btn btn-secondary btn-sm" title="Toggle Light/Dark Theme" aria-label="Toggle theme mode" style="padding: 0.35rem 0.65rem; font-size: 0.95rem;">
            🌓
          </button>

          <!-- Notification Center -->
          <div class="topbar-notifications-wrapper" style="position: relative;">
            <button id="btn-notifications-toggle" class="btn btn-secondary btn-sm" title="Operations Notifications" aria-label="Notifications" style="position: relative; padding: 0.35rem 0.65rem;">
              🔔
              ${state.activeAlertsCount > 0 ? `<span class="notification-indicator-dot"></span>` : ''}
            </button>
            <div id="topbar-notifications-dropdown" class="topbar-notifications-dropdown" style="display: none; position: absolute; right: 0; top: calc(100% + 6px); width: 290px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); z-index: 1000; overflow: hidden;">
              <div style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; background: var(--bg-elevated);">
                <span style="font-weight: 700; font-size: 0.85rem; color: #fff;">Operational Alerts</span>
                <span class="badge ${state.activeAlertsCount > 0 ? 'badge-p1' : 'badge-neutral'}" style="font-size: 0.68rem;">
                  ${state.activeAlertsCount} Unacknowledged
                </span>
              </div>
              <div style="max-height: 240px; overflow-y: auto; padding: 0.5rem 0;">
                ${state.activeAlertsCount > 0 ? `
                  <div style="padding: 0.6rem 1rem; border-bottom: 1px solid var(--border-subtle); cursor: pointer;" id="btn-notif-view-alerts">
                    <div style="font-weight: 600; font-size: 0.82rem; color: #f87171;">⚠️ Active Operational Alert</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">
                      Store #${getSelectedStoreNumber()} has ${state.activeAlertsCount} active alert(s) requiring acknowledgment.
                    </div>
                  </div>
                ` : `
                  <div style="padding: 1.25rem 1rem; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
                    ✓ All clear. No unacknowledged alerts.
                  </div>
                `}
              </div>
            </div>
          </div>

          <!-- User Profile & Account Settings Button -->
          <div class="user-profile-badge" id="btn-user-profile" role="button" tabindex="0" title="Click to manage profile, email & password" style="cursor: pointer;">
            <div class="user-avatar-circle">
              ${escapeHtml(state.user.fullName.split(' ').map(n => n[0]).join('').slice(0, 2))}
            </div>
            <div class="user-info-text">
              <span class="user-name">${escapeHtml(state.user.fullName)}</span>
              <span class="user-role-chip">${escapeHtml(state.user.role.replace(/_/g, ' '))}</span>
            </div>
            <span style="font-size: 0.85rem; color: var(--text-muted); margin-left: 2px;" title="Account Settings">⚙️</span>
          </div>

          <!-- Sign Out Button -->
          <button id="btn-logout" class="btn btn-secondary btn-sm" title="Sign Out of Session">Sign Out</button>
        </div>
      </header>

      <!-- Dynamic View Workspace -->
      <section id="view-workspace" class="app-content" aria-live="polite">
        <!-- Rendered by view controllers -->
      </section>
    </main>
  `;

  attachGlobalEvents();
  renderActiveView();
}

function attachGlobalEvents() {
  // Mobile sidebar drawer toggling
  const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');

  const closeSidebarMobile = () => {
    if (sidebar) sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.remove('active');
  };

  if (btnToggleSidebar && sidebar && backdrop) {
    btnToggleSidebar.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      backdrop.classList.toggle('active');
    });
    backdrop.addEventListener('click', closeSidebarMobile);
  }

  // Fast-track demo button in topbar
  const btnTopbarDemo = document.getElementById('btn-topbar-demo');
  if (btnTopbarDemo) {
    btnTopbarDemo.addEventListener('click', () => {
      closeSidebarMobile();
      state.setView('demo');
    });
  }

  // Navigation clicks and keyboard accessibility
  document.querySelectorAll('.nav-item').forEach(el => {
    const handleNav = () => {
      const view = el.getAttribute('data-view');
      closeSidebarMobile();
      state.setView(view);
    };
    el.addEventListener('click', handleNav);
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleNav();
      }
    });
  });

  // Topbar Context Switchers
  const selOrg = document.getElementById('select-org');
  if (selOrg) {
    selOrg.addEventListener('change', async (e) => {
      state.selectedOrgId = e.target.value;
      const regions = await api.getRegions(state.selectedOrgId);
      state.regions = regions;
      if (regions.length > 0) state.selectedRegionId = regions[0].id;
      const stores = await api.getStores(state.selectedOrgId, state.selectedRegionId);
      state.stores = stores;
      if (stores.length > 0) state.selectedStoreId = stores[0].id;
      await loadInitialData();
      showToast('Context updated to organization', 'info');
    });
  }

  const selRegion = document.getElementById('select-region');
  if (selRegion) {
    selRegion.addEventListener('change', async (e) => {
      state.selectedRegionId = e.target.value;
      const stores = await api.getStores(state.selectedOrgId, state.selectedRegionId);
      state.stores = stores;
      if (stores.length > 0) state.selectedStoreId = stores[0].id;
      await loadInitialData();
      showToast('Context updated to region', 'info');
    });
  }

  const selStore = document.getElementById('select-store');
  if (selStore) {
    selStore.addEventListener('change', async (e) => {
      state.selectedStoreId = e.target.value;
      await loadInitialData();
      showToast('Facility switched to Store #' + getSelectedStoreNumber(), 'info');
    });
  }

  // Theme Toggle (Dark / Light Mode)
  const btnThemeToggle = document.getElementById('btn-theme-toggle');
  if (btnThemeToggle) {
    btnThemeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('r5_theme', newTheme);
      showToast(`Visual theme switched to ${newTheme} mode`, 'info');
    });
  }

  // Notification Center Dropdown
  const btnNotifications = document.getElementById('btn-notifications-toggle');
  const notifDropdown = document.getElementById('topbar-notifications-dropdown');
  if (btnNotifications && notifDropdown) {
    btnNotifications.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDropdown.style.display = notifDropdown.style.display === 'none' ? 'block' : 'none';
    });
    document.addEventListener('click', () => {
      if (notifDropdown) notifDropdown.style.display = 'none';
    });
    const btnViewAlerts = document.getElementById('btn-notif-view-alerts');
    if (btnViewAlerts) {
      btnViewAlerts.addEventListener('click', () => {
        notifDropdown.style.display = 'none';
        state.setView('alerts');
      });
    }
  }

  // User Profile -> Account & Security Settings Modal
  const btnUserProfile = document.getElementById('btn-user-profile');
  if (btnUserProfile) {
    const handleAccountClick = () => openAccountSettingsModal();
    btnUserProfile.addEventListener('click', handleAccountClick);
    btnUserProfile.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleAccountClick();
      }
    });
  }

  // Role switcher modal (Evaluation Sandbox)
  const btnRoleSwitch = document.getElementById('btn-open-role-switcher');
  if (btnRoleSwitch) {
    btnRoleSwitch.addEventListener('click', openRoleSwitcherModal);
  }

  // Secure Sign Out
  const btnLogout = document.getElementById('btn-logout');
  if (btnLogout) {
    btnLogout.addEventListener('click', async () => {
      try {
        await api.logout();
      } catch {}
      state.setAuth(null, null);
      showToast('Signed out of session safely.', 'info');
    });
  }
}

async function renderActiveView() {
  const ws = document.getElementById('view-workspace');
  if (!ws) return;

  switch (state.currentView) {
    case 'dashboard':
      await renderDashboardView(ws);
      break;
    case 'demo':
      await renderDemoView(ws);
      break;
    case 'feedback':
      await renderFeedbackView(ws);
      break;
    case 'issues':
      await renderIssuesView(ws);
      break;
    case 'clusters':
      await renderClustersView(ws);
      break;
    case 'alerts':
      await renderAlertsView(ws);
      break;
    case 'actions':
      await renderActionsView(ws);
      break;
    case 'outcomes':
      await renderOutcomesView(ws);
      break;
    case 'briefs':
      await renderBriefsView(ws);
      break;
    case 'audit':
      await renderAuditView(ws);
      break;
    case 'org-hierarchy':
      await renderOrgHierarchyView(ws);
      break;
    case 'teams':
      await renderTeamsView(ws);
      break;
    case 'users':
      await renderUsersView(ws);
      break;
    case 'ownership':
      await renderOwnershipView(ws);
      break;
    case 'roles':
      await renderRolesView(ws);
      break;
    case 'personal-home':
      await renderPersonalHomeView(ws);
      break;
    default:
      ws.innerHTML = `<div class="r5-card"><div class="r5-card-body">View "${state.currentView}" under construction.</div></div>`;
  }
}

/* -------------------------------------------------------------------------
   VIEW 1: COMMAND CENTER (DASHBOARD)
-------------------------------------------------------------------------- */
let dashSearchQuery = '';
let dashPriorityFilter = 'ALL';
let dashStatusFilter = 'ALL';

async function renderDashboardView(container) {
  // Skeleton Loading State
  container.innerHTML = `
    ${renderSkeletonCardsHtml(4)}
    <div style="margin-top: 1.25rem;">
      ${renderSkeletonTableHtml(4, 6)}
    </div>
  `;

  try {
    const [issues, alerts, actions] = await Promise.all([
      api.getIssues(state.selectedStoreId),
      api.getAlerts(state.selectedStoreId),
      api.getActions()
    ]);

    const activeIssues = issues.filter(i => i.status !== 'CLOSED');
    const p1Issues = issues.filter(i => i.priorityTier === 'P1_CRITICAL' && i.status !== 'CLOSED');
    const pendingActions = actions.filter(a => a.approvalStatus === 'PENDING');
    const emergingAnomalies = issues.filter(i => i.isEmergingAnomaly && i.status !== 'CLOSED');

    const filteredIssues = issues.filter(i => {
      const matchesSearch = !dashSearchQuery ||
        i.title.toLowerCase().includes(dashSearchQuery.toLowerCase()) ||
        i.description.toLowerCase().includes(dashSearchQuery.toLowerCase()) ||
        (i.assignedTeamName && i.assignedTeamName.toLowerCase().includes(dashSearchQuery.toLowerCase()));
      const matchesPriority = dashPriorityFilter === 'ALL' || i.priorityTier === dashPriorityFilter;
      const matchesStatus = dashStatusFilter === 'ALL' || i.status === dashStatusFilter;
      return matchesSearch && matchesPriority && matchesStatus;
    });

    const topCritical = p1Issues[0] || emergingAnomalies[0];

    container.innerHTML = `
      <!-- Operational Storytelling Top Banner (What Needs Attention Now?) -->
      ${topCritical ? `
        <div class="hero-crisis-card" role="alert" style="background: linear-gradient(90deg, rgba(239, 68, 68, 0.16) 0%, rgba(26, 34, 52, 0.85) 100%); border-left: 4px solid var(--p1-critical); border-radius: var(--radius-md); padding: 1.25rem 1.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1.25rem; margin-bottom: 1.25rem; box-shadow: 0 4px 20px rgba(239, 68, 68, 0.15);">
          <div style="display: flex; align-items: flex-start; gap: 1rem; max-width: 750px;">
            <span class="anomaly-pulse" style="margin-top: 2px;"><span class="pulse-dot"></span> P1 ESCALATION ACTIVE</span>
            <div>
              <div style="font-weight: 700; color: #fff; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                <span>${escapeHtml(topCritical.title)}</span>
                <span class="badge badge-p1" style="font-size: 0.68rem;">Score: ${topCritical.priorityScore}/100</span>
                <span class="badge badge-neutral" style="font-size: 0.68rem;">Store #${getSelectedStoreNumber()}</span>
              </div>
              <div style="font-size: 0.82rem; color: #cbd5e1; margin-top: 5px; line-height: 1.45;">
                <strong>Hypothesis:</strong> <span style="color: #38bdf8;">${escapeHtml(topCritical.rootCauseHypothesis || 'Technician diagnostics needed')}</span>
                &bull; Assigned: <strong>${escapeHtml(topCritical.assignedTeamName || 'Fast-Response Team')}</strong>
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 0.65rem;">
            <button class="btn btn-danger btn-sm" id="btn-hero-inspect" data-id="${topCritical.id}">
              🔍 Inspect Evidence & Triage
            </button>
            <button class="btn btn-primary btn-sm" id="btn-hero-dispatch" data-id="${topCritical.id}">
              ⚡ Rapid Dispatch
            </button>
          </div>
        </div>
      ` : `
        <div class="hero-operational-card" style="background: linear-gradient(90deg, rgba(16, 185, 129, 0.12) 0%, rgba(26, 34, 52, 0.6) 100%); border-left: 4px solid var(--accent-emerald); border-radius: var(--radius-md); padding: 1.1rem 1.35rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;">
          <div style="display: flex; align-items: center; gap: 0.85rem;">
            <span style="font-size: 1.6rem;">🛡️</span>
            <div>
              <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">Operations Steady — Zero Critical P1 Escalations</div>
              <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">
                All active incidents within target SLA window for Store #${getSelectedStoreNumber()}. Closed-loop verification active.
              </div>
            </div>
          </div>
          <button class="btn btn-secondary btn-sm" id="btn-hero-create-incident">+ Log Operational Issue</button>
        </div>
      `}

      <!-- Clickable KPI Metrics Grid (Context Filters) -->
      <div class="kpi-grid">
        <div class="kpi-card clickable" id="kpi-card-active" role="button" tabindex="0" title="Click to filter table to all active incidents" style="cursor: pointer;">
          <div class="kpi-card-header">
            <span>Active Incidents</span>
            <span>🚨</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${activeIssues.length}</span>
            <span class="kpi-trend neutral">Store #${getSelectedStoreNumber()} (Click to View)</span>
          </div>
        </div>

        <div class="kpi-card critical clickable" id="kpi-card-p1" role="button" tabindex="0" title="Click to isolate Critical P1 incidents" style="cursor: pointer;">
          <div class="kpi-card-header">
            <span>Critical P1 Incidents</span>
            <span>🔥</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${p1Issues.length}</span>
            <span class="kpi-trend" style="color: var(--p1-critical);">SLA &lt; 15m (Click to Filter)</span>
          </div>
        </div>

        <div class="kpi-card highlight clickable" id="kpi-card-approvals" role="button" tabindex="0" title="Click to navigate to Human-in-the-Loop Approvals" style="cursor: pointer;">
          <div class="kpi-card-header">
            <span>Pending Approvals</span>
            <span>⚖️</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">${pendingActions.length}</span>
            <span class="kpi-trend neutral">Human-in-the-Loop Gate &rarr;</span>
          </div>
        </div>

        <div class="kpi-card clickable" id="kpi-card-resolution" role="button" tabindex="0" title="Click to view 72h Closed-Loop Outcome Verification" style="cursor: pointer;">
          <div class="kpi-card-header">
            <span>72h Resolution Rate</span>
            <span>✅</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">100%</span>
            <span class="kpi-trend positive">↑ Closed-Loop Verified &rarr;</span>
          </div>
        </div>
      </div>

      <!-- Live Incident Resolution Core Table -->
      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>⚡</span>
            <span>Active Incident Clusters & Priority Pipeline (${filteredIssues.length})</span>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button id="btn-create-incident" class="btn btn-primary btn-sm">+ Log Operational Issue</button>
          </div>
        </div>

        <!-- Filter Toolbar -->
        <div class="r5-filter-toolbar">
          <div class="r5-filter-group">
            <input type="text" id="dash-search-input" class="form-input" style="padding: 0.35rem 0.65rem; font-size: 0.82rem; width: 200px;" placeholder="Filter by title, desc..." value="${escapeHtml(dashSearchQuery)}" aria-label="Search incidents" />
            
            <select id="dash-filter-priority" class="form-select" style="padding: 0.35rem 0.65rem; font-size: 0.82rem;" aria-label="Filter by priority tier">
              <option value="ALL" ${dashPriorityFilter === 'ALL' ? 'selected' : ''}>All Priority Tiers</option>
              <option value="P1_CRITICAL" ${dashPriorityFilter === 'P1_CRITICAL' ? 'selected' : ''}>P1 Critical</option>
              <option value="P2_HIGH" ${dashPriorityFilter === 'P2_HIGH' ? 'selected' : ''}>P2 High</option>
              <option value="P3_MEDIUM" ${dashPriorityFilter === 'P3_MEDIUM' ? 'selected' : ''}>P3 Medium</option>
              <option value="P4_LOW" ${dashPriorityFilter === 'P4_LOW' ? 'selected' : ''}>P4 Low</option>
            </select>

            <select id="dash-filter-status" class="form-select" style="padding: 0.35rem 0.65rem; font-size: 0.82rem;" aria-label="Filter by lifecycle status">
              <option value="ALL" ${dashStatusFilter === 'ALL' ? 'selected' : ''}>All Lifecycle Statuses</option>
              <option value="DETECTED" ${dashStatusFilter === 'DETECTED' ? 'selected' : ''}>Detected</option>
              <option value="TRIAGED" ${dashStatusFilter === 'TRIAGED' ? 'selected' : ''}>Triaged</option>
              <option value="DISPATCHED" ${dashStatusFilter === 'DISPATCHED' ? 'selected' : ''}>Dispatched</option>
              <option value="IN_PROGRESS" ${dashStatusFilter === 'IN_PROGRESS' ? 'selected' : ''}>In Progress</option>
              <option value="REMEDIATED" ${dashStatusFilter === 'REMEDIATED' ? 'selected' : ''}>Remediated</option>
              <option value="VERIFYING" ${dashStatusFilter === 'VERIFYING' ? 'selected' : ''}>Verifying</option>
              <option value="CLOSED" ${dashStatusFilter === 'CLOSED' ? 'selected' : ''}>Closed</option>
            </select>

            ${(dashSearchQuery || dashPriorityFilter !== 'ALL' || dashStatusFilter !== 'ALL') ? `
              <button id="btn-dash-clear-filters" class="btn btn-secondary btn-sm" style="font-size: 0.78rem;">Clear Filters</button>
            ` : ''}
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">
            Formula: <code>Priority = Clamp(∑ [W_i × S_i] - Discount, 1, 100)</code>
          </div>
        </div>

        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Priority Score</th>
                <th>Incident Details & Diagnostics</th>
                <th>Status</th>
                <th>Assigned Team & SLA</th>
                <th>Evidence Count</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${filteredIssues.length === 0 ? `
                <tr>
                  <td colspan="6">
                    ${renderEmptyStateHtml({
                      icon: '📋',
                      title: 'No matching operational incidents',
                      desc: 'No incidents match your active filters. Clear filters or log a new operational issue.',
                      actionLabel: '+ Log Operational Issue',
                      actionId: 'btn-dash-empty-log'
                    })}
                  </td>
                </tr>
              ` : ''}
              ${filteredIssues.map(item => `
                <tr>
                  <td>
                    <div class="priority-score-box">
                      <span class="score-number" style="color: ${getPriorityColor(item.priorityTier)};">${item.priorityScore}</span>
                      <div>
                        <div class="score-bar-track">
                          <div class="score-bar-fill" style="width: ${item.priorityScore}%; background-color: ${getPriorityColor(item.priorityTier)};"></div>
                        </div>
                        <span class="badge badge-${item.priorityTier.toLowerCase().replace(/_/g, '-')}" style="margin-top: 4px; font-size: 0.65rem;">
                          ${escapeHtml(item.priorityTier.replace(/_/g, ' '))}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div style="font-weight: 700; color: #fff;">${escapeHtml(item.title)}</div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">${escapeHtml(item.description.slice(0, 85))}...</div>
                    <div style="font-size: 0.75rem; color: #38bdf8; margin-top: 3px; display: flex; align-items: center; gap: 0.35rem;">
                      <span class="badge badge-hypothesis" style="font-size: 0.62rem; padding: 1px 5px;">HYPOTHESIS</span>
                      <span>${escapeHtml(item.rootCauseHypothesis || 'Pending technician investigation')}</span>
                    </div>
                    ${item.isEmergingAnomaly ? `
                      <span class="anomaly-pulse" style="margin-top: 4px;"><span class="pulse-dot"></span> Emerging Spike (+${item.anomalyVelocityZScore}z)</span>
                    ` : ''}
                  </td>
                  <td>
                    <span class="badge ${item.status === 'VERIFYING' ? 'badge-verifying' : item.status === 'CLOSED' ? 'badge-p4' : item.status === 'IN_PROGRESS' ? 'badge-p2' : 'badge-neutral'}">
                      ${item.status}
                    </span>
                  </td>
                  <td>
                    <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem;">${escapeHtml(item.assignedTeamName || 'Unassigned')}</div>
                    <div style="margin-top: 4px;">
                      ${getSlaCountdownHtml(item)}
                    </div>
                    ${item.slaDeadline ? `
                      <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;" title="${item.slaDeadline}">
                        Target: ${new Date(item.slaDeadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    ` : ''}
                  </td>
                  <td>
                    <span class="badge badge-neutral">${item.feedbackCount} Raw Reports</span>
                  </td>
                  <td>
                    <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
                      <button class="btn btn-primary btn-sm btn-open-issue-detail" data-id="${item.id}" title="Inspect Complete Operational Lifecycle & Factor Attribution">
                        🔍 Detail & DAG
                      </button>
                      <button class="btn btn-secondary btn-sm btn-view-evidence" data-id="${item.id}" title="Inspect Grounded Verbatim Citations">
                        📜 Citations
                      </button>
                      ${renderStatusActionButtons(item)}
                    </div>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Filter event handlers
    const searchInput = container.querySelector('#dash-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        dashSearchQuery = e.target.value;
        renderDashboardView(container);
      });
    }

    const prioritySelect = container.querySelector('#dash-filter-priority');
    if (prioritySelect) {
      prioritySelect.addEventListener('change', (e) => {
        dashPriorityFilter = e.target.value;
        renderDashboardView(container);
      });
    }

    const statusSelect = container.querySelector('#dash-filter-status');
    if (statusSelect) {
      statusSelect.addEventListener('change', (e) => {
        dashStatusFilter = e.target.value;
        renderDashboardView(container);
      });
    }

    const btnClearFilters = container.querySelector('#btn-dash-clear-filters');
    if (btnClearFilters) {
      btnClearFilters.addEventListener('click', () => {
        dashSearchQuery = '';
        dashPriorityFilter = 'ALL';
        dashStatusFilter = 'ALL';
        renderDashboardView(container);
      });
    }

    // Hero Banner Action triggers
    const btnHeroInspect = container.querySelector('#btn-hero-inspect');
    if (btnHeroInspect) {
      btnHeroInspect.addEventListener('click', () => openIssueDetailModal(btnHeroInspect.getAttribute('data-id')));
    }

    const btnHeroDispatch = container.querySelector('#btn-hero-dispatch');
    if (btnHeroDispatch) {
      btnHeroDispatch.addEventListener('click', async () => {
        const id = btnHeroDispatch.getAttribute('data-id');
        try {
          await api.updateIssueStatus(id, 'DISPATCHED', 'Rapid dispatch initiated from Command Center Hero Alert');
          showToast('Fast-Response technician dispatched!', 'success');
          await loadInitialData();
          await renderDashboardView(container);
        } catch (err) {
          showToast('Dispatch failed: ' + err.message, 'error');
        }
      });
    }

    const btnHeroCreateInc = container.querySelector('#btn-hero-create-incident');
    if (btnHeroCreateInc) {
      btnHeroCreateInc.addEventListener('click', openCreateIssueModal);
    }

    // Clickable KPI Metrics Grid triggers
    const kpiActive = container.querySelector('#kpi-card-active');
    if (kpiActive) {
      kpiActive.addEventListener('click', () => {
        dashStatusFilter = 'ALL';
        dashPriorityFilter = 'ALL';
        dashSearchQuery = '';
        renderDashboardView(container);
        showToast('Viewing all active store incidents', 'info');
      });
    }

    const kpiP1 = container.querySelector('#kpi-card-p1');
    if (kpiP1) {
      kpiP1.addEventListener('click', () => {
        dashPriorityFilter = 'P1_CRITICAL';
        dashStatusFilter = 'ALL';
        renderDashboardView(container);
        showToast('Filtered table to Critical P1 incidents', 'info');
      });
    }

    const kpiApprovals = container.querySelector('#kpi-card-approvals');
    if (kpiApprovals) {
      kpiApprovals.addEventListener('click', () => {
        state.setView('actions');
      });
    }

    const kpiResolution = container.querySelector('#kpi-card-resolution');
    if (kpiResolution) {
      kpiResolution.addEventListener('click', () => {
        state.setView('outcomes');
      });
    }

    // Modal and action triggers
    container.querySelectorAll('.btn-open-issue-detail').forEach(btn => {
      btn.addEventListener('click', () => openIssueDetailModal(btn.getAttribute('data-id')));
    });

    container.querySelectorAll('.btn-view-evidence').forEach(btn => {
      btn.addEventListener('click', () => openEvidenceModal(btn.getAttribute('data-id')));
    });

    const btnInspect = container.querySelector('#btn-inspect-anomaly');
    if (btnInspect) {
      btnInspect.addEventListener('click', () => openIssueDetailModal(btnInspect.getAttribute('data-id')));
    }

    const btnCreateInc = container.querySelector('#btn-create-incident');
    if (btnCreateInc) {
      btnCreateInc.addEventListener('click', openCreateIssueModal);
    }

    const btnDashEmpty = container.querySelector('#btn-dash-empty-log');
    if (btnDashEmpty) {
      btnDashEmpty.addEventListener('click', openCreateIssueModal);
    }

    container.querySelectorAll('.btn-transition-status').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        const nextStatus = btn.getAttribute('data-status');
        try {
          await api.updateIssueStatus(id, nextStatus, 'Manual transition via Operations Cockpit');
          showToast(`Issue status advanced to ${nextStatus}`, 'success');
          await loadInitialData();
          await renderDashboardView(container);
        } catch (err) {
          showToast('Status transition failed: ' + err.message, 'error');
        }
      });
    });

  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Failed to load operational dashboard',
      message: err.message,
      onRetryId: 'btn-retry-dashboard'
    });
    const retryBtn = container.querySelector('#btn-retry-dashboard');
    if (retryBtn) retryBtn.addEventListener('click', () => renderDashboardView(container));
  }
}

function renderStatusActionButtons(issue) {
  if (issue.status === 'DETECTED') {
    return `<button class="btn btn-secondary btn-sm btn-transition-status" data-id="${issue.id}" data-status="TRIAGED">Triage</button>`;
  }
  if (issue.status === 'TRIAGED') {
    return `<button class="btn btn-primary btn-sm btn-transition-status" data-id="${issue.id}" data-status="DISPATCHED">Dispatch</button>`;
  }
  if (issue.status === 'DISPATCHED' && state.user.role === 'MAINTENANCE_TEAM') {
    return `<button class="btn btn-primary btn-sm btn-transition-status" data-id="${issue.id}" data-status="IN_PROGRESS">Accept & Work</button>`;
  }
  if (issue.status === 'IN_PROGRESS' && state.user.role === 'MAINTENANCE_TEAM') {
    return `<button class="btn btn-success btn-sm btn-transition-status" data-id="${issue.id}" data-status="REMEDIATED">Log Fix</button>`;
  }
  return '';
}

/* -------------------------------------------------------------------------
   VIEW 3: ISSUES & INCIDENTS (EXPLAINABLE PRIORITIZATION & LINEAGE DAG)
-------------------------------------------------------------------------- */
let issueSearchQuery = '';
let issuePriorityFilter = 'ALL';
let issueStatusFilter = 'ALL';

async function renderIssuesView(container) {
  container.innerHTML = renderSkeletonTableHtml(5, 6);

  try {
    const issues = await api.getIssues(state.selectedStoreId);

    const filteredIssues = issues.filter(i => {
      const matchesSearch = !issueSearchQuery ||
        i.title.toLowerCase().includes(issueSearchQuery.toLowerCase()) ||
        i.description.toLowerCase().includes(issueSearchQuery.toLowerCase()) ||
        (i.assignedTeamName && i.assignedTeamName.toLowerCase().includes(issueSearchQuery.toLowerCase()));
      const matchesPriority = issuePriorityFilter === 'ALL' || i.priorityTier === issuePriorityFilter;
      const matchesStatus = issueStatusFilter === 'ALL' || i.status === issueStatusFilter;
      return matchesSearch && matchesPriority && matchesStatus;
    });

    container.innerHTML = `
      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>⚠️</span>
            <span>Operational Incidents & Explainable Prioritization (${filteredIssues.length})</span>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button id="btn-create-incident-view" class="btn btn-primary btn-sm">+ Log Operational Issue</button>
          </div>
        </div>

        <div class="r5-card-body" style="border-bottom: 1px solid var(--border-subtle); background-color: rgba(17, 24, 39, 0.4); padding: 0.85rem 1.25rem;">
          <div style="font-size: 0.82rem; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <strong>Explainable Prioritization Formula:</strong>
              <code>Priority = Clamp(∑ [Weight_i × Signal_i] - UncertaintyDiscount, 1, 100)</code>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">
              Signals: Severity, Urgency, Operational Impact, Safety Relevance, Growth Velocity, Recurrence
            </div>
          </div>
        </div>

        <!-- Filter Toolbar -->
        <div class="r5-filter-toolbar">
          <div class="r5-filter-group">
            <input type="text" id="issue-search-input" class="form-input" style="padding: 0.35rem 0.65rem; font-size: 0.82rem; width: 220px;" placeholder="Search title, description..." value="${escapeHtml(issueSearchQuery)}" aria-label="Search incidents" />
            
            <select id="issue-filter-priority" class="form-select" style="padding: 0.35rem 0.65rem; font-size: 0.82rem;" aria-label="Filter by priority tier">
              <option value="ALL" ${issuePriorityFilter === 'ALL' ? 'selected' : ''}>All Priority Tiers</option>
              <option value="P1_CRITICAL" ${issuePriorityFilter === 'P1_CRITICAL' ? 'selected' : ''}>P1 Critical</option>
              <option value="P2_HIGH" ${issuePriorityFilter === 'P2_HIGH' ? 'selected' : ''}>P2 High</option>
              <option value="P3_MEDIUM" ${issuePriorityFilter === 'P3_MEDIUM' ? 'selected' : ''}>P3 Medium</option>
              <option value="P4_LOW" ${issuePriorityFilter === 'P4_LOW' ? 'selected' : ''}>P4 Low</option>
            </select>

            <select id="issue-filter-status" class="form-select" style="padding: 0.35rem 0.65rem; font-size: 0.82rem;" aria-label="Filter by status">
              <option value="ALL" ${issueStatusFilter === 'ALL' ? 'selected' : ''}>All Lifecycle Statuses</option>
              <option value="DETECTED" ${issueStatusFilter === 'DETECTED' ? 'selected' : ''}>Detected</option>
              <option value="TRIAGED" ${issueStatusFilter === 'TRIAGED' ? 'selected' : ''}>Triaged</option>
              <option value="DISPATCHED" ${issueStatusFilter === 'DISPATCHED' ? 'selected' : ''}>Dispatched</option>
              <option value="IN_PROGRESS" ${issueStatusFilter === 'IN_PROGRESS' ? 'selected' : ''}>In Progress</option>
              <option value="REMEDIATED" ${issueStatusFilter === 'REMEDIATED' ? 'selected' : ''}>Remediated</option>
              <option value="VERIFYING" ${issueStatusFilter === 'VERIFYING' ? 'selected' : ''}>Verifying</option>
              <option value="CLOSED" ${issueStatusFilter === 'CLOSED' ? 'selected' : ''}>Closed</option>
            </select>

            ${(issueSearchQuery || issuePriorityFilter !== 'ALL' || issueStatusFilter !== 'ALL') ? `
              <button id="btn-issue-clear-filters" class="btn btn-secondary btn-sm" style="font-size: 0.78rem;">Clear Filters</button>
            ` : ''}
          </div>
        </div>

        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Incident Details & Diagnostics</th>
                <th>Factor Contributions</th>
                <th>Assigned Team & SLA</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${filteredIssues.length === 0 ? `
                <tr>
                  <td colspan="6">
                    ${renderEmptyStateHtml({
                      icon: '⚠️',
                      title: 'No matching incidents',
                      desc: 'No operational incidents found matching your query. Clear filters or create a new issue.',
                      actionLabel: '+ Log Operational Issue',
                      actionId: 'btn-issues-empty-log'
                    })}
                  </td>
                </tr>
              ` : ''}
              ${filteredIssues.map(i => {
                const factors = i.factorBreakdown || {};
                const isTriage = i.routingStatus === 'TRIAGE_QUEUE' || !i.assignedTeamId;
                return `
                  <tr>
                    <td>
                      <div style="font-size: 1.25rem; font-weight: 800; color: ${getPriorityColor(i.priorityTier)};">${i.priorityScore}</div>
                      <span class="badge badge-${i.priorityTier.toLowerCase().replace(/_/g, '-')}">${escapeHtml(i.priorityTier.replace(/_/g, ' '))}</span>
                    </td>
                    <td>
                      <div style="font-weight: 700; color: #fff;">${escapeHtml(i.title)}</div>
                      <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px;">${escapeHtml(i.description)}</div>
                      <div style="font-size: 0.75rem; color: #38bdf8; margin-top: 4px; display: flex; align-items: center; gap: 0.35rem;">
                        <span class="badge badge-hypothesis" style="font-size: 0.62rem; padding: 1px 5px;">HYPOTHESIS</span>
                        <span>${escapeHtml(i.rootCauseHypothesis || 'Pending investigation')}</span>
                      </div>
                      ${i.prioritizationExplanation ? `
                        <div style="font-size: 0.72rem; color: #fbbf24; margin-top: 4px; font-style: italic;">
                          ⓘ ${escapeHtml(i.prioritizationExplanation)}
                        </div>
                      ` : ''}
                    </td>
                    <td>
                      <div style="font-size: 0.72rem; display: flex; flex-direction: column; gap: 2px;">
                        <div>Severity: <strong>+${factors.severity || (i.severityScore * 40).toFixed(1)} pts</strong></div>
                        <div>Urgency: <strong>+${factors.urgency || (i.urgencyScore * 35).toFixed(1)} pts</strong></div>
                        <div>Impact Scope: <strong>+${factors.operationalImpact || (i.impactScopeScore * 25).toFixed(1)} pts</strong></div>
                        ${factors.safety ? `<div style="color: #f87171;">Safety Hazard: <strong>+${factors.safety} pts</strong></div>` : ''}
                        ${factors.growth ? `<div style="color: #fbbf24;">Velocity Z-Score: <strong>+${factors.growth} pts</strong></div>` : ''}
                        <div style="color: var(--text-muted); margin-top: 2px;">Confidence: <strong>${Math.round((i.confidenceScore || 0.85) * 100)}%</strong></div>
                      </div>
                    </td>
                    <td>
                      <div style="display: flex; flex-direction: column; gap: 4px;">
                        ${isTriage ? `
                          <span class="badge badge-warning" style="align-self: flex-start;">⚠️ Human Triage Queue</span>
                        ` : `
                          <div style="font-weight: 700; color: #fff; font-size: 0.85rem;">${escapeHtml(i.assignedTeamName || 'Assigned')}</div>
                        `}
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">
                          SLA: <strong>${i.slaMinutes || 60}m</strong>
                        </div>
                        ${i.slaDeadline ? `
                          <div style="font-size: 0.7rem; color: #34d399;" title="${i.slaDeadline}">
                            Due: ${new Date(i.slaDeadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        ` : ''}
                      </div>
                    </td>
                    <td><span class="badge badge-neutral">${i.status}</span></td>
                    <td>
                      <div style="display: flex; flex-direction: column; gap: 4px;">
                        <button class="btn btn-primary btn-sm btn-open-issue-detail" data-id="${i.id}" title="Inspect full operational lifecycle and attribution">
                          🔍 Detail & DAG
                        </button>
                        <button class="btn btn-secondary btn-sm btn-manage-routing" data-id="${i.id}" title="Manage intelligent operational routing and team dispatch">
                          🔀 Route / SLA
                        </button>
                        <button class="btn btn-secondary btn-sm btn-recalc-priority" data-id="${i.id}" title="Recalculate explainable priority score">
                          ⚡ Recalculate
                        </button>
                        <button class="btn btn-secondary btn-sm btn-override-priority" data-id="${i.id}" data-score="${i.priorityScore}">
                          ✎ Override
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

    // Filter event handlers
    const searchInput = container.querySelector('#issue-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        issueSearchQuery = e.target.value;
        renderIssuesView(container);
      });
    }

    const prioritySelect = container.querySelector('#issue-filter-priority');
    if (prioritySelect) {
      prioritySelect.addEventListener('change', (e) => {
        issuePriorityFilter = e.target.value;
        renderIssuesView(container);
      });
    }

    const statusSelect = container.querySelector('#issue-filter-status');
    if (statusSelect) {
      statusSelect.addEventListener('change', (e) => {
        issueStatusFilter = e.target.value;
        renderIssuesView(container);
      });
    }

    const btnClear = container.querySelector('#btn-issue-clear-filters');
    if (btnClear) {
      btnClear.addEventListener('click', () => {
        issueSearchQuery = '';
        issuePriorityFilter = 'ALL';
        issueStatusFilter = 'ALL';
        renderIssuesView(container);
      });
    }

    container.querySelectorAll('.btn-open-issue-detail').forEach(btn => {
      btn.addEventListener('click', () => openIssueDetailModal(btn.getAttribute('data-id')));
    });

    container.querySelectorAll('.btn-manage-routing').forEach(btn => {
      btn.addEventListener('click', () => openRoutingModal(btn.getAttribute('data-id')));
    });

    container.querySelectorAll('.btn-recalc-priority').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        try {
          await api.recalculateIssuePriority(id);
          showToast('Priority recalculated and factor contributions updated.', 'success');
          await renderIssuesView(container);
        } catch (err) {
          showToast('Error recalculating priority: ' + err.message, 'error');
        }
      });
    });

    container.querySelectorAll('.btn-override-priority').forEach(btn => {
      btn.addEventListener('click', () => openOverridePriorityModal(btn.getAttribute('data-id'), btn.getAttribute('data-score')));
    });

    const btnCreate = container.querySelector('#btn-create-incident-view');
    if (btnCreate) btnCreate.addEventListener('click', openCreateIssueModal);

    const btnEmptyLog = container.querySelector('#btn-issues-empty-log');
    if (btnEmptyLog) btnEmptyLog.addEventListener('click', openCreateIssueModal);

  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Failed to load issues',
      message: err.message,
      onRetryId: 'btn-retry-issues'
    });
    const retryBtn = container.querySelector('#btn-retry-issues');
    if (retryBtn) retryBtn.addEventListener('click', () => renderIssuesView(container));
  }
}


/* -------------------------------------------------------------------------
   VIEW 3B: SEMANTIC ISSUE CLUSTERING (PHASE 6)
-------------------------------------------------------------------------- */
async function renderClustersView(container) {
  container.innerHTML = renderSkeletonTableHtml(4, 5);

  try {
    const clusters = await api.getClusters(state.selectedStoreId);

    container.innerHTML = `
      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>🗂️</span>
            <span>Cross-Source Semantic Issue Clusters (${clusters.length})</span>
          </div>
          <button class="btn btn-primary btn-sm" id="btn-discover-clusters">
            ⚡ Run Semantic Clustering Job
          </button>
        </div>
        <div class="r5-card-body" style="border-bottom: 1px solid var(--border-subtle); background-color: rgba(17, 24, 39, 0.4); padding: 0.85rem 1.25rem;">
          <div style="font-size: 0.85rem; color: var(--text-secondary);">
            Synthesizes fragmented customer complaints, frontline observations, and maintenance work orders into single grounded issue clusters using deterministic text similarity & embedding models.
          </div>
        </div>
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Cluster Title & Category</th>
                <th>Quality & Confidence</th>
                <th>Sources & Volume</th>
                <th>Grounded Empirical Summary</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${clusters.length === 0 ? `
                <tr>
                  <td colspan="5">
                    ${renderEmptyStateHtml({
                      icon: '🗂️',
                      title: 'No active semantic clusters found',
                      desc: 'No synthesized clusters for Store #' + getSelectedStoreNumber() + '. Run the clustering job to group raw multilingual feedback.',
                      actionLabel: '⚡ Run Semantic Clustering Job',
                      actionId: 'btn-empty-discover-clusters'
                    })}
                  </td>
                </tr>
              ` : ''}
              ${clusters.map(c => `
                <tr>
                  <td>
                    <div style="font-weight: 700; color: #fff;">${escapeHtml(c.title)}</div>
                    <div style="display: flex; gap: 0.4rem; margin-top: 3px;">
                      <span class="badge badge-neutral" style="font-size: 0.7rem;">${escapeHtml(c.category.replace(/_/g, ' '))}</span>
                      <span class="badge ${c.status === 'ACTIVE' ? 'badge-p4' : 'badge-neutral'}" style="font-size: 0.7rem;">${c.status}</span>
                    </div>
                  </td>
                  <td>
                    <div style="font-size: 0.8rem; font-weight: 700; color: #34d399;">
                      ${Math.round(c.qualityScore * 100)}% Quality
                    </div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">
                      Confidence: ${Math.round(c.confidenceScore * 100)}%
                    </div>
                  </td>
                  <td>
                    <div style="font-weight: 700; color: #fff;">${c.feedbackCount} Member Report(s)</div>
                    <div style="display: flex; gap: 3px; flex-wrap: wrap; margin-top: 3px;">
                      ${(c.sources || []).map(s => `<span class="badge badge-neutral" style="font-size: 0.65rem;">${escapeHtml(s.replace(/_/g, ' '))}</span>`).join('')}
                    </div>
                  </td>
                  <td>
                    <div style="font-size: 0.78rem; color: var(--text-secondary); max-width: 450px;">
                      ${escapeHtml(c.summary)}
                    </div>
                  </td>
                  <td>
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                      <button class="btn btn-secondary btn-sm btn-inspect-cluster" data-id="${c.id}">
                        🔍 Members (${c.feedbackCount})
                      </button>
                    </div>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    const handleClusterRun = async () => {
      try {
        showToast('Running cross-source semantic clustering job...', 'info');
        const res = await api.discoverClusters({ storeId: state.selectedStoreId, timeWindowHours: 72 });
        showToast(`Clustering complete: synthesized ${res.length} cluster(s).`, 'success');
        await renderClustersView(container);
      } catch (err) {
        showToast('Clustering failed: ' + err.message, 'error');
      }
    };

    const btnDiscover = document.getElementById('btn-discover-clusters');
    if (btnDiscover) btnDiscover.addEventListener('click', handleClusterRun);

    const btnEmptyDiscover = document.getElementById('btn-empty-discover-clusters');
    if (btnEmptyDiscover) btnEmptyDiscover.addEventListener('click', handleClusterRun);

    container.querySelectorAll('.btn-inspect-cluster').forEach(btn => {
      btn.addEventListener('click', () => openClusterDetailModal(btn.getAttribute('data-id'), () => renderClustersView(container)));
    });
  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Failed to load semantic clusters',
      message: err.message,
      onRetryId: 'btn-retry-clusters'
    });
    const retryBtn = container.querySelector('#btn-retry-clusters');
    if (retryBtn) retryBtn.addEventListener('click', () => renderClustersView(container));
  }
}

/* -------------------------------------------------------------------------
   VIEW 4: ALERTS (PHASE 7 EMERGING ISSUE DETECTION & LIFECYCLE)
-------------------------------------------------------------------------- */
async function renderAlertsView(container) {
  container.innerHTML = renderSkeletonTableHtml(4, 6);

  try {
    const alerts = await api.getAlerts(state.selectedStoreId);

    container.innerHTML = `
      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>🔔</span>
            <span>Emerging Issue Detection & Operational Velocity Alerts (${alerts.length})</span>
          </div>
          <button class="btn btn-primary btn-sm" id="btn-run-detection">
            ⚡ Run Emerging Issue Detection
          </button>
        </div>
        <div class="r5-card-body" style="border-bottom: 1px solid var(--border-subtle); background-color: rgba(17, 24, 39, 0.4); padding: 0.85rem 1.25rem;">
          <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.45;">
            Deterministic anomaly analytics comparing recent 24h frequency against 14-day historical store Poisson baselines (&lambda;).
            Distinguishes active statistical velocity spikes (<span class="badge badge-p1" style="font-size: 0.65rem;">ANOMALY &ge; +2.0z</span>) from uncalibrated data (<span class="badge badge-p2" style="font-size: 0.65rem;">INSUFFICIENT_BASELINE</span>).
          </div>
        </div>
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Alert & Baseline Status</th>
                <th>Severity & Urgency</th>
                <th>Evidence & Velocity</th>
                <th>Deterministic Explanation</th>
                <th>Lifecycle Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${alerts.length === 0 ? `
                <tr>
                  <td colspan="6">
                    ${renderEmptyStateHtml({
                      icon: '🔔',
                      title: 'No operational alerts active',
                      desc: 'All monitored categories are within Poisson baseline bounds for Store #' + getSelectedStoreNumber() + '.',
                      actionLabel: '⚡ Run Emerging Issue Detection',
                      actionId: 'btn-empty-run-detection'
                    })}
                  </td>
                </tr>
              ` : ''}
              ${alerts.map(a => {
                const isAnomaly = a.baselineStatus === 'ANOMALY';
                const isInsufficient = a.baselineStatus === 'INSUFFICIENT_BASELINE';
                return `
                  <tr>
                    <td>
                      <div style="font-weight: 700; color: #fff;">${escapeHtml(a.what || a.message)}</div>
                      <div style="display: flex; gap: 0.35rem; margin-top: 4px;">
                        ${isAnomaly ? `<span class="badge badge-p1">📈 Anomaly (+${a.velocityZscore}z)</span>` : ''}
                        ${isInsufficient ? `<span class="badge badge-p2">⚠️ Insufficient Baseline</span>` : ''}
                        <span class="badge badge-neutral">${escapeHtml(a.alertType)}</span>
                      </div>
                    </td>
                    <td>
                      <div><span class="badge badge-${a.severity === 'CRITICAL' ? 'p1' : 'p2'}">${a.severity}</span></div>
                      <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">Urgency: <strong>${a.urgency || 'MEDIUM'}</strong></div>
                    </td>
                    <td>
                      <div style="font-weight: 600; color: #fff;">${a.observationCount || 1} observation(s)</div>
                      <div style="font-size: 0.72rem; color: var(--accent-cyan); margin-top: 2px;">
                        Growth: +${Math.round((a.growthRate || 0) * 100)}%
                      </div>
                    </td>
                    <td>
                      <div style="font-size: 0.78rem; color: var(--text-secondary); max-width: 350px;">
                        ${escapeHtml(a.whyGenerated || a.message)}
                      </div>
                    </td>
                    <td>
                      <span class="badge ${a.status === 'NEW' ? 'badge-p1' : a.status === 'ACKNOWLEDGED' ? 'badge-p4' : 'badge-neutral'}">
                        ${a.status || (a.isAcknowledged ? 'ACKNOWLEDGED' : 'NEW')}
                      </span>
                    </td>
                    <td>
                      <div style="display: flex; flex-direction: column; gap: 4px;">
                        <button class="btn btn-secondary btn-sm btn-inspect-alert-evidence" data-id="${a.id}">
                          📜 Citations
                        </button>
                        ${a.status === 'NEW' || !a.isAcknowledged ? `
                          <button class="btn btn-primary btn-sm btn-ack-alert" data-id="${a.id}">Acknowledge</button>
                        ` : ''}
                        ${a.status !== 'DISMISSED' && a.status !== 'RESOLVED' ? `
                          <button class="btn btn-secondary btn-sm btn-dismiss-alert" data-id="${a.id}">Dismiss</button>
                        ` : ''}
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

    const handleRunDetection = async () => {
      try {
        showToast('Running deterministic emerging issue detection...', 'info');
        const res = await api.detectEmergingIssues({ storeId: state.selectedStoreId });
        showToast(`Detection complete: ${res.length} alert(s) generated.`, 'success');
        await renderAlertsView(container);
      } catch (err) {
        showToast('Detection error: ' + err.message, 'error');
      }
    };

    const btnRun = document.getElementById('btn-run-detection');
    if (btnRun) btnRun.addEventListener('click', handleRunDetection);

    const btnEmptyRun = document.getElementById('btn-empty-run-detection');
    if (btnEmptyRun) btnEmptyRun.addEventListener('click', handleRunDetection);

    container.querySelectorAll('.btn-inspect-alert-evidence').forEach(btn => {
      btn.addEventListener('click', () => openAlertEvidenceModal(btn.getAttribute('data-id')));
    });

    container.querySelectorAll('.btn-ack-alert').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        try {
          await api.acknowledgeAlert(id);
          showToast('Alert acknowledged.', 'success');
          await loadInitialData();
          await renderAlertsView(container);
        } catch (err) {
          showToast('Ack error: ' + err.message, 'error');
        }
      });
    });

    container.querySelectorAll('.btn-dismiss-alert').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        const reason = prompt('Please enter justification for dismissing this alert:');
        if (!reason) return;
        try {
          await api.dismissAlert(id, reason);
          showToast('Alert dismissed.', 'info');
          await loadInitialData();
          await renderAlertsView(container);
        } catch (err) {
          showToast('Dismiss error: ' + err.message, 'error');
        }
      });
    });
  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Failed to load operational alerts',
      message: err.message,
      onRetryId: 'btn-retry-alerts'
    });
    const retryBtn = container.querySelector('#btn-retry-alerts');
    if (retryBtn) retryBtn.addEventListener('click', () => renderAlertsView(container));
  }
}

/* -------------------------------------------------------------------------
   VIEW 5: ACTIONS & APPROVALS
-------------------------------------------------------------------------- */
async function renderActionsView(container) {
  container.innerHTML = renderSkeletonTableHtml(4, 5);

  try {
    const actions = await api.getActions();

    container.innerHTML = `
      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>🛠️</span>
            <span>Action Plans, Work Orders & Human Approval Gate (${actions.length})</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">
            Human-in-the-Loop Governance Guardrail Active
          </div>
        </div>
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Recommended Action</th>
                <th>Target Team</th>
                <th>SLA Countdown & Due Time</th>
                <th>Approval Status</th>
                <th>Governance Controls</th>
              </tr>
            </thead>
            <tbody>
              ${actions.length === 0 ? `
                <tr>
                  <td colspan="5">
                    ${renderEmptyStateHtml({
                      icon: '🛠️',
                      title: 'No pending actions or work orders',
                      desc: 'All operational dispatches are currently fulfilled for Store #' + getSelectedStoreNumber() + '.',
                      actionLabel: '',
                      actionId: ''
                    })}
                  </td>
                </tr>
              ` : ''}
              ${actions.map(act => {
                const now = new Date();
                const deadline = new Date(act.slaDeadline);
                const diffMin = Math.round((deadline - now) / 60000);
                const isOverdue = diffMin < 0;
                const countdownText = isOverdue
                  ? `<span style="color: var(--p1-critical); font-weight: 700;">Overdue by ${Math.abs(diffMin)}m</span>`
                  : `<span style="color: #34d399; font-weight: 600;">Due in ${diffMin}m</span>`;

                return `
                  <tr>
                    <td>
                      <div style="font-weight: 600; color: #fff;">${escapeHtml(act.recommendedAction)}</div>
                      ${act.overrideReason ? `
                        <div style="font-size: 0.75rem; color: var(--p2-high); margin-top: 3px;">
                          <em>Override Reason: "${escapeHtml(act.overrideReason)}"</em>
                        </div>
                      ` : ''}
                    </td>
                    <td><span style="font-weight: 600; color: var(--accent-cyan);">${escapeHtml(act.targetTeamName || act.targetTeamId)}</span></td>
                    <td>
                      <div>${countdownText}</div>
                      <div class="table-id-mono" style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">
                        Target: ${deadline.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>
                    <td>
                      <span class="badge ${act.approvalStatus === 'APPROVED' ? 'badge-p4' : act.approvalStatus === 'OVERRIDDEN' ? 'badge-p2' : 'badge-p1'}">
                        ${act.approvalStatus}
                      </span>
                    </td>
                    <td>
                      <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                        ${act.approvalStatus === 'PENDING' ? `
                          <button class="btn btn-success btn-sm btn-approve-action" data-id="${act.id}">Approve Work Order</button>
                        ` : ''}
                        <button class="btn btn-secondary btn-sm btn-override-routing" data-id="${act.id}">Override Route</button>
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

    container.querySelectorAll('.btn-approve-action').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        try {
          await api.approveAction(id, 'APPROVED', 'Approved by authorized manager in Cockpit');
          showToast('Work order approved and dispatched to operational team.', 'success');
          await loadInitialData();
          await renderActionsView(container);
        } catch (err) {
          showToast('Approval failed: ' + err.message, 'error');
        }
      });
    });

    container.querySelectorAll('.btn-override-routing').forEach(btn => {
      btn.addEventListener('click', () => openOverrideRoutingModal(btn.getAttribute('data-id')));
    });

  } catch (err) {
    container.innerHTML = renderErrorStateHtml({
      title: 'Failed to load action plans',
      message: err.message,
      onRetryId: 'btn-retry-actions'
    });
    const retryBtn = container.querySelector('#btn-retry-actions');
    if (retryBtn) retryBtn.addEventListener('click', () => renderActionsView(container));
  }
}

/* -------------------------------------------------------------------------
   VIEW 6: AUDIT & GOVERNANCE
-------------------------------------------------------------------------- */
async function renderAuditView(container) {
  try {
    const logs = await api.getAuditLogs();

    container.innerHTML = `
      <div class="r5-card">
        <div class="r5-card-header">
          <div class="r5-card-title">
            <span>📜</span>
            <span>Immutable Audit Trail & Governance Log</span>
          </div>
        </div>
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User / Actor</th>
                <th>Entity Type</th>
                <th>Action Performed</th>
                <th>Justification / Reason</th>
              </tr>
            </thead>
            <tbody>
              ${logs.map(log => `
                <tr>
                  <td class="table-id-mono">${new Date(log.createdAt).toLocaleString()}</td>
                  <td>
                    <div style="font-weight: 600; color: #fff;">${log.userEmail || 'System / Automated'}</div>
                  </td>
                  <td><span class="badge badge-neutral">${log.entityType}</span></td>
                  <td><span class="badge badge-neutral" style="font-family: var(--font-family-mono); font-size: 0.7rem;">${log.action}</span></td>
                  <td>${log.justification || '<span style="color: var(--text-muted); font-size: 0.75rem;">N/A</span>'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="r5-card"><div class="r5-card-body">${err.message}</div></div>`;
  }
}

/* -------------------------------------------------------------------------
   VIEW 7: PERSONAL / HOME MODE (FUTURE EXTENSIBILITY SCOPE)
-------------------------------------------------------------------------- */
async function renderPersonalHomeView(container) {
  try {
    const [appliances, tickets] = await Promise.all([
      api.getHomeAppliances(),
      api.getHomeTickets()
    ]);

    container.innerHTML = `
      <div style="background: rgba(139, 92, 246, 0.1); border: 1px dashed var(--accent-purple); border-radius: var(--radius-md); padding: 1rem 1.25rem; margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem; font-weight: 700; color: #c4b5fd;">
          <span>ℹ️</span> Secondary Future Scope — Segregated Personal/Home Mode Demonstration
        </div>
        <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px;">
          This isolated domain models personal appliances (TV, Refrigerator, AC, Washer) and manufacturer service routing without contaminating the enterprise retail operations model.
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
        <!-- Appliances Registered -->
        <div class="r5-card">
          <div class="r5-card-header">
            <div class="r5-card-title">
              <span>📺</span>
              <span>Registered Household Appliances</span>
            </div>
            <button id="btn-add-appliance" class="btn btn-primary btn-sm">+ Register Appliance</button>
          </div>
          <div class="r5-card-body" style="display: flex; flex-direction: column; gap: 1rem;">
            ${appliances.length === 0 ? `<div style="color: var(--text-muted);">No appliances registered yet.</div>` : ''}
            ${appliances.map(app => `
              <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: 700; color: #fff;">${app.brand} (${app.applianceType})</span>
                  <span class="badge badge-neutral">${app.modelNumber || 'Standard Model'}</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">
                  Serial: <code class="table-id-mono">${app.serialNumber || 'N/A'}</code>
                </div>
                <div style="font-size: 0.8rem; color: var(--p4-low); margin-top: 0.25rem;">
                  Active Warranty Until: ${app.warrantyUntil || 'Standard 1-Year'}
                </div>
                <button class="btn btn-secondary btn-sm btn-file-service-ticket" data-id="${app.id}" style="margin-top: 0.75rem;">
                  Request Service
                </button>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Service Tickets -->
        <div class="r5-card">
          <div class="r5-card-header">
            <div class="r5-card-title">
              <span>📑</span>
              <span>Personal Service Tickets</span>
            </div>
          </div>
          <div class="r5-card-body" style="display: flex; flex-direction: column; gap: 0.75rem;">
            ${tickets.length === 0 ? `<div style="color: var(--text-muted);">No open service tickets.</div>` : ''}
            ${tickets.map(t => `
              <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: 600; color: #fff;">${t.classifiedCategory}</span>
                  <span class="badge badge-p4">${t.status}</span>
                </div>
                <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.4rem;">"${t.complaintDescription}"</div>
                <div style="font-size: 0.75rem; color: var(--accent-cyan); margin-top: 0.5rem;">
                  Routed Channel: <strong>${t.routedServiceChannel}</strong>
                </div>
                <div class="table-id-mono" style="font-size: 0.7rem; margin-top: 0.25rem;">Ref: ${t.externalReferenceId}</div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    container.querySelector('#btn-add-appliance').addEventListener('click', openRegisterApplianceModal);
    container.querySelectorAll('.btn-file-service-ticket').forEach(btn => {
      btn.addEventListener('click', () => openFileServiceTicketModal(btn.getAttribute('data-id')));
    });

  } catch (err) {
    container.innerHTML = `<div class="r5-card"><div class="r5-card-body">${err.message}</div></div>`;
  }
}

/* -------------------------------------------------------------------------
   MODALS & DIALOG CONTROLLERS
-------------------------------------------------------------------------- */
function openModal(contentHtml) {
  elModalContainer.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal-content">
        ${contentHtml}
      </div>
    </div>
  `;
}

function closeModal() {
  elModalContainer.innerHTML = '';
}

export function openEvidenceDrawer(evidenceData) {
  let drawerContainer = document.getElementById('drawer-container');
  if (!drawerContainer) {
    drawerContainer = document.createElement('div');
    drawerContainer.id = 'drawer-container';
    document.body.appendChild(drawerContainer);
  }

  drawerContainer.innerHTML = `
    <div class="r5-drawer-backdrop" id="drawer-backdrop">
      <div class="r5-drawer">
        <div class="r5-drawer-header">
          <div class="r5-drawer-title">
            <span>📜</span>
            <span>${escapeHtml(evidenceData.title || 'Evidence & Grounded Lineage')}</span>
          </div>
          <button class="btn btn-secondary btn-sm" id="btn-close-drawer" aria-label="Close Evidence Drawer">✕</button>
        </div>
        <div class="r5-drawer-body">
          ${evidenceData.bodyHtml || ''}
        </div>
      </div>
    </div>
  `;

  const closeDrawer = () => {
    drawerContainer.innerHTML = '';
  };

  document.getElementById('btn-close-drawer')?.addEventListener('click', closeDrawer);
  document.getElementById('drawer-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'drawer-backdrop') closeDrawer();
  });
}

async function openAccountSettingsModal() {
  if (!state.user) return;

  let currentUser = state.user;
  try {
    currentUser = await api.getMe();
    state.user = currentUser;
    localStorage.setItem('r5_user', JSON.stringify(currentUser));
  } catch (err) {
    console.warn('Could not refresh authoritative user profile:', err);
  }

  openModal(`
    <div class="modal-header">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <span style="font-size: 1.25rem;">⚙️</span>
        <div>
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff;">Account & Security Settings</h3>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Manage your profile identity, login email, and security credentials</div>
        </div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal" aria-label="Close Settings">✕</button>
    </div>

    <div class="modal-body" style="padding: 1.25rem;">
      <!-- Tab Navigation -->
      <div class="account-settings-tabs" style="display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1.25rem; padding-bottom: 0.5rem;">
        <button class="account-settings-tab active" id="tab-btn-profile" type="button" style="padding: 0.5rem 1rem; border-radius: var(--radius-sm); border: none; font-size: 0.85rem; font-weight: 600; cursor: pointer; background: var(--accent-indigo); color: #fff;">
          👤 Profile Details
        </button>
        <button class="account-settings-tab" id="tab-btn-security" type="button" style="padding: 0.5rem 1rem; border-radius: var(--radius-sm); border: none; font-size: 0.85rem; font-weight: 600; cursor: pointer; background: var(--bg-surface); color: var(--text-secondary);">
          🔒 Password & Credentials
        </button>
      </div>

      <!-- Tab Content: Profile Details -->
      <div id="tab-content-profile" class="account-settings-panel">
        <div style="display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1.25rem; padding: 0.75rem 1rem; background: var(--bg-surface); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div class="user-avatar-circle" style="width: 44px; height: 44px; font-size: 1.1rem;">
            ${escapeHtml(currentUser.fullName.split(' ').map(n => n[0]).join('').slice(0, 2))}
          </div>
          <div>
            <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">${escapeHtml(currentUser.fullName)}</div>
            <div style="font-size: 0.78rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.4rem; margin-top: 2px;">
              <span class="badge badge-neutral" style="font-size: 0.65rem;">${escapeHtml(currentUser.role.replace(/_/g, ' '))}</span>
              <span>• Store #${getSelectedStoreNumber()}</span>
            </div>
          </div>
        </div>

        <form id="form-update-profile" style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="form-group">
            <label class="form-label" for="profile-name">Full Name</label>
            <input type="text" id="profile-name" class="form-input" required value="${escapeHtml(currentUser.fullName)}" />
          </div>

          <div class="form-group">
            <label class="form-label" for="profile-email">
              Corporate Email Address <span style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 500;">(Authoritative Login Identifier)</span>
            </label>
            <input type="email" id="profile-email" class="form-input" required value="${escapeHtml(currentUser.email)}" autocomplete="email" />
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
              Updating this email changes your sign-in address. Changes are validated and persisted to the SQLite database.
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Operational Role</label>
            <input type="text" class="form-input" value="${escapeHtml(currentUser.role)}" disabled style="opacity: 0.7; cursor: not-allowed;" />
            <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 3px;">
              Privileged role escalation requires Organization Administrator authorization.
            </div>
          </div>

          <div id="profile-status-msg" style="display: none; padding: 0.6rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.82rem;"></div>

          <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.5rem;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-profile">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-profile">Save Profile Changes</button>
          </div>
        </form>
      </div>

      <!-- Tab Content: Password & Security -->
      <div id="tab-content-security" class="account-settings-panel" style="display: none;">
        <form id="form-update-password" style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="form-group">
            <label class="form-label" for="pwd-current">Current Password</label>
            <div style="position: relative;">
              <input type="password" id="pwd-current" class="form-input" required autocomplete="current-password" placeholder="Verify identity with current password" />
              <button type="button" class="btn-pwd-toggle" data-target="pwd-current" style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.85rem;" title="Toggle Password Visibility">👁️</button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="pwd-new">New Password</label>
            <div style="position: relative;">
              <input type="password" id="pwd-new" class="form-input" required minlength="8" autocomplete="new-password" placeholder="Minimum 8 characters" />
              <button type="button" class="btn-pwd-toggle" data-target="pwd-new" style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.85rem;" title="Toggle Password Visibility">👁️</button>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
              Must be at least 8 characters. Password will be securely hashed with bcrypt.
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="pwd-confirm">Confirm New Password</label>
            <div style="position: relative;">
              <input type="password" id="pwd-confirm" class="form-input" required minlength="8" autocomplete="new-password" placeholder="Re-type new password" />
              <button type="button" class="btn-pwd-toggle" data-target="pwd-confirm" style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.85rem;" title="Toggle Password Visibility">👁️</button>
            </div>
          </div>

          <div id="pwd-status-msg" style="display: none; padding: 0.6rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.82rem;"></div>

          <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.5rem;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-pwd">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-pwd">Update Password</button>
          </div>
        </form>
      </div>
    </div>
  `);

  // Tab switching
  const tabBtnProfile = document.getElementById('tab-btn-profile');
  const tabBtnSecurity = document.getElementById('tab-btn-security');
  const panelProfile = document.getElementById('tab-content-profile');
  const panelSecurity = document.getElementById('tab-content-security');

  tabBtnProfile.addEventListener('click', () => {
    tabBtnProfile.style.background = 'var(--accent-indigo)';
    tabBtnProfile.style.color = '#fff';
    tabBtnSecurity.style.background = 'var(--bg-surface)';
    tabBtnSecurity.style.color = 'var(--text-secondary)';
    panelProfile.style.display = 'block';
    panelSecurity.style.display = 'none';
  });

  tabBtnSecurity.addEventListener('click', () => {
    tabBtnSecurity.style.background = 'var(--accent-indigo)';
    tabBtnSecurity.style.color = '#fff';
    tabBtnProfile.style.background = 'var(--bg-surface)';
    tabBtnProfile.style.color = 'var(--text-secondary)';
    panelSecurity.style.display = 'block';
    panelProfile.style.display = 'none';
  });

  // Password visibility toggles
  document.querySelectorAll('.btn-pwd-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
      }
    });
  });

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-profile')?.addEventListener('click', closeModal);
  document.getElementById('btn-cancel-pwd')?.addEventListener('click', closeModal);

  // Profile update form handler
  const formProfile = document.getElementById('form-update-profile');
  formProfile.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById('btn-submit-profile');
    const msgBox = document.getElementById('profile-status-msg');
    const newName = document.getElementById('profile-name').value.trim();
    const newEmail = document.getElementById('profile-email').value.trim();

    btnSubmit.disabled = true;
    btnSubmit.innerText = 'Saving to Database...';
    msgBox.style.display = 'none';

    try {
      const updatedUser = await api.updateProfile({ fullName: newName, email: newEmail });
      // Re-fetch me to verify persistence from the live backend
      const verifiedMe = await api.getMe();
      state.user = verifiedMe || updatedUser;
      localStorage.setItem('r5_user', JSON.stringify(state.user));
      
      showToast(`Account updated successfully! Login email is now ${state.user.email}`, 'success');
      state.notify();
      closeModal();
    } catch (err) {
      msgBox.style.display = 'block';
      msgBox.style.background = 'rgba(239, 68, 68, 0.15)';
      msgBox.style.border = '1px solid var(--p1-critical)';
      msgBox.style.color = '#fca5a5';
      msgBox.innerText = 'Error: ' + err.message;
      btnSubmit.disabled = false;
      btnSubmit.innerText = 'Save Profile Changes';
    }
  });

  // Password update form handler
  const formPwd = document.getElementById('form-update-password');
  formPwd.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById('btn-submit-pwd');
    const msgBox = document.getElementById('pwd-status-msg');
    const currentPassword = document.getElementById('pwd-current').value;
    const newPassword = document.getElementById('pwd-new').value;
    const confirmPassword = document.getElementById('pwd-confirm').value;

    if (newPassword !== confirmPassword) {
      msgBox.style.display = 'block';
      msgBox.style.background = 'rgba(239, 68, 68, 0.15)';
      msgBox.style.border = '1px solid var(--p1-critical)';
      msgBox.style.color = '#fca5a5';
      msgBox.innerText = 'New password and confirmation password do not match.';
      return;
    }

    if (newPassword.length < 8) {
      msgBox.style.display = 'block';
      msgBox.style.background = 'rgba(239, 68, 68, 0.15)';
      msgBox.style.border = '1px solid var(--p1-critical)';
      msgBox.style.color = '#fca5a5';
      msgBox.innerText = 'Password must be at least 8 characters long.';
      return;
    }

    btnSubmit.disabled = true;
    btnSubmit.innerText = 'Updating Password...';
    msgBox.style.display = 'none';

    try {
      await api.changePassword({ currentPassword, newPassword });
      showToast('Password updated securely in database.', 'success');
      closeModal();
    } catch (err) {
      msgBox.style.display = 'block';
      msgBox.style.background = 'rgba(239, 68, 68, 0.15)';
      msgBox.style.border = '1px solid var(--p1-critical)';
      msgBox.style.color = '#fca5a5';
      msgBox.innerText = 'Password Update Failed: ' + err.message;
      btnSubmit.disabled = false;
      btnSubmit.innerText = 'Update Password';
    }
  });
}

function renderLoginModal() {
  openModal(`
    <div class="modal-header">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div class="brand-badge" style="width: 32px; height: 32px; font-size: 1rem;">R5</div>
        <div>
          <h2 style="font-size: 1.15rem; font-weight: 700; color: #fff;">Sign In — R5 Intelligence</h2>
          <div style="font-size: 0.78rem; color: var(--text-muted);">Retail Operations Intelligence & Incident Management Platform</div>
        </div>
      </div>
    </div>
    <div class="modal-body">
      <!-- Demo Persona Sandbox Quick-Fill -->
      <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.75rem 1rem; margin-bottom: 1rem;">
        <div style="font-size: 0.8rem; font-weight: 600; color: var(--accent-cyan); margin-bottom: 0.35rem;">
          ⚡ Quick-Fill Demo Personas (Evaluation Sandbox)
        </div>
        <div class="role-preset-grid" style="margin-top: 0.5rem;">
          ${ROLE_PRESETS.map(p => `
            <div class="role-preset-btn" data-email="${p.email}" title="Click to fill credentials for ${p.title}">
              <div class="role-preset-title">${p.title}</div>
              <div class="role-preset-desc">${p.desc}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <form id="form-login" style="display: flex; flex-direction: column; gap: 1rem;">
        <div class="form-group">
          <label class="form-label" for="login-email">Corporate Email Address</label>
          <input type="email" id="login-email" class="form-input" required autocomplete="email" placeholder="name@organization.com" />
        </div>
        <div class="form-group">
          <label class="form-label" for="login-password">Password</label>
          <div style="position: relative;">
            <input type="password" id="login-password" class="form-input" required autocomplete="current-password" placeholder="••••••••" />
            <button type="button" id="btn-login-pwd-toggle" style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.85rem;" title="Toggle Password Visibility">👁️</button>
          </div>
        </div>
        <div id="login-error-msg" style="display: none; padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); font-size: 0.82rem; background: rgba(239, 68, 68, 0.15); border: 1px solid var(--p1-critical); color: #fca5a5;"></div>
        <button type="submit" id="btn-submit-login" class="btn btn-primary" style="width: 100%; justify-content: center; padding: 0.65rem;">
          Sign In to Cockpit
        </button>
      </form>
    </div>
  `);

  document.getElementById('btn-login-pwd-toggle')?.addEventListener('click', () => {
    const pwdInput = document.getElementById('login-password');
    if (pwdInput) {
      pwdInput.type = pwdInput.type === 'password' ? 'text' : 'password';
    }
  });

  document.querySelectorAll('.role-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const email = btn.getAttribute('data-email');
      const emailInput = document.getElementById('login-email');
      const pwdInput = document.getElementById('login-password');
      if (emailInput && pwdInput) {
        emailInput.value = email;
        pwdInput.value = 'Password123!';
        showToast(`Filled credentials for ${email}`, 'info');
      }
    });
  });

  document.getElementById('form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById('btn-submit-login');
    const errorMsg = document.getElementById('login-error-msg');
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    btnSubmit.disabled = true;
    btnSubmit.innerText = 'Authenticating...';
    errorMsg.style.display = 'none';

    try {
      const res = await api.login(email, password);
      state.setAuth(res.token, res.user);
      await loadInitialData();
      showToast(`Welcome back, ${res.user.fullName}!`, 'success');
      closeModal();
    } catch (err) {
      errorMsg.style.display = 'block';
      errorMsg.innerText = 'Authentication Failed: ' + (err.message || 'Invalid email or password');
      btnSubmit.disabled = false;
      btnSubmit.innerText = 'Sign In to Cockpit';
    }
  });
}

function openRoleSwitcherModal() {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Switch Active Role (RBAC Simulation)</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <div class="modal-body">
      <div style="font-size: 0.85rem; color: var(--text-secondary);">
        Simulate how the dashboard, access boundaries, and governance controls adapt dynamically to different operational personas:
      </div>
      <div class="role-preset-grid" style="grid-template-columns: 1fr;">
        ${ROLE_PRESETS.map(p => `
          <div class="role-preset-btn ${state.user && state.user.role === p.role ? 'active' : ''}" data-email="${p.email}">
            <div style="display: flex; justify-content: space-between; width: 100%;">
              <span class="role-preset-title">${p.title} (${p.role})</span>
              ${state.user && state.user.role === p.role ? '<span class="badge badge-p4">Active</span>' : ''}
            </div>
            <div class="role-preset-desc">${p.desc}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.querySelectorAll('.role-preset-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const email = btn.getAttribute('data-email');
      try {
        const res = await api.login(email, 'Password123!');
        state.setAuth(res.token, res.user);
        await loadInitialData();
        showToast(`Switched active persona to ${res.user.fullName} (${res.user.role})`, 'success');
        closeModal();
      } catch (err) {
        showToast('Role switch failed: ' + err.message, 'error');
      }
    });
  });
}

/* -------------------------------------------------------------------------
   MODAL: ENTERPRISE OPERATIONAL ISSUE DETAIL & TRIAGE (PHASE 22)
-------------------------------------------------------------------------- */
async function openIssueDetailModal(issueId) {
  try {
    const [issue, evidenceList, history] = await Promise.all([
      api.getIssue(issueId),
      api.getIssueEvidence(issueId),
      api.getIssueRoutingHistory(issueId)
    ]);

    const factors = issue.factorBreakdown || {};
    const stages = ['DETECTED', 'TRIAGED', 'DISPATCHED', 'IN_PROGRESS', 'REMEDIATED', 'VERIFYING', 'CLOSED'];
    const currentStageIndex = stages.indexOf(issue.status);

    openModal(`
      <div class="modal-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.65rem;">
            <h3 style="font-size: 1.2rem; font-weight: 700; color: #fff;">${escapeHtml(issue.title)}</h3>
            <span class="badge badge-${issue.priorityTier.toLowerCase().replace(/_/g, '-')}">
              ${escapeHtml(issue.priorityTier.replace(/_/g, ' '))} (${issue.priorityScore}/100)
            </span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 3px;">
            Incident ID: <code class="table-id-mono">${issue.id}</code> | Store #${getSelectedStoreNumber()} | Status: <strong>${issue.status}</strong>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal" aria-label="Close Issue Detail Modal">✕</button>
      </div>

      <div class="modal-body" style="max-height: 78vh; overflow-y: auto;">
        <!-- 7-Stage Operational Lifecycle Stepper -->
        <div class="r5-lifecycle-stepper" role="region" aria-label="Incident Lifecycle Progress">
          ${stages.map((st, idx) => {
            const isCompleted = idx < currentStageIndex;
            const isActive = idx === currentStageIndex;
            const cls = isActive ? 'active' : isCompleted ? 'completed' : '';
            return `
              <div class="r5-step-item ${cls}">
                <div class="r5-step-number">${isCompleted ? '✓' : idx + 1}</div>
                <span>${st.replace(/_/g, ' ')}</span>
              </div>
              ${idx < stages.length - 1 ? `<span style="color: var(--border-medium); font-size: 0.75rem;">→</span>` : ''}
            `;
          }).join('')}
        </div>

        <!-- Strict Zero-Hallucination & Epistemological Guardrail -->
        <div style="background: rgba(56, 189, 248, 0.08); border-left: 3px solid #38bdf8; border-radius: var(--radius-sm); padding: 0.75rem 1rem; font-size: 0.82rem; color: #e2e8f0;">
          <div style="display: flex; align-items: center; gap: 0.5rem; font-weight: 700; color: #38bdf8;">
            <span>🛡️</span> Epistemological Lineage Classification
          </div>
          <div style="margin-top: 3px; font-size: 0.78rem; color: var(--text-secondary); line-height: 1.45;">
            Customer complaints and frontline sensor data are verified <span class="badge badge-fact" style="font-size: 0.65rem;">FACT</span>.
            Root-cause diagnoses are strictly classified as <span class="badge badge-hypothesis" style="font-size: 0.65rem;">HYPOTHESIS</span> requiring field verification by assigned technician before sign-off.
          </div>
        </div>

        <!-- 1. Explainable Prioritization Math -->
        <div class="r5-card" style="padding: 1rem; background: var(--bg-secondary); border-color: var(--border-subtle);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
            <div style="font-size: 0.88rem; font-weight: 700; color: #fff;">
              ⚖️ Deterministic Priority Breakdown: <span style="color: ${getPriorityColor(issue.priorityTier)}; font-size: 1.1rem;">${issue.priorityScore} pts</span>
            </div>
            <code style="font-size: 0.72rem; color: var(--text-muted); background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">
              Clamp(∑ [W_i × S_i] - Discount, 1, 100)
            </code>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.5rem; margin-bottom: 0.75rem;">
            <div style="background: var(--bg-surface); padding: 0.5rem; border-radius: 4px; text-align: center;">
              <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Severity</div>
              <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">+${factors.severity || (issue.severityScore * 40).toFixed(1)}</div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.5rem; border-radius: 4px; text-align: center;">
              <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Urgency</div>
              <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">+${factors.urgency || (issue.urgencyScore * 35).toFixed(1)}</div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.5rem; border-radius: 4px; text-align: center;">
              <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Scope</div>
              <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">+${factors.operationalImpact || (issue.impactScopeScore * 25).toFixed(1)}</div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.5rem; border-radius: 4px; text-align: center;">
              <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Safety Hazard</div>
              <div style="font-weight: 700; color: ${factors.safety ? '#f87171' : 'var(--text-muted)'}; font-size: 0.95rem;">
                +${factors.safety || (issue.isSafetyHazard ? 30 : 0)}
              </div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.5rem; border-radius: 4px; text-align: center;">
              <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Velocity Spike</div>
              <div style="font-weight: 700; color: ${issue.isEmergingAnomaly ? '#fbbf24' : 'var(--text-muted)'}; font-size: 0.95rem;">
                +${factors.growth || (issue.isEmergingAnomaly ? 20 : 0)}
              </div>
            </div>
          </div>

          <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45;">
            <strong>Deterministic Explanation:</strong> ${escapeHtml(issue.prioritizationExplanation || 'Multi-factor deterministic priority synthesized across severity, urgency, and operational velocity signals.')}
          </div>
        </div>

        <!-- 2. Root Cause Diagnostics -->
        <div style="background: rgba(17, 24, 39, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="font-size: 0.88rem; font-weight: 700; color: #fff;">
              🔍 Root-Cause Diagnostic Hypothesis:
            </div>
            <span class="badge badge-hypothesis">HYPOTHESIS</span>
          </div>
          <div style="font-size: 0.85rem; color: #38bdf8; margin-top: 0.4rem; font-weight: 500; line-height: 1.45;">
            ${escapeHtml(issue.rootCauseHypothesis || 'Pending technician physical inspection and electrical telemetry audit.')}
          </div>
          <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.5rem;">
            <strong>Incident Description:</strong> ${escapeHtml(issue.description)}
          </div>
        </div>

        <!-- 3. Grounded Customer & Frontline Evidence Citations -->
        <div style="background: rgba(17, 24, 39, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
            <div style="font-size: 0.88rem; font-weight: 700; color: #fff;">
              📜 Grounded Citations (${evidenceList.length}):
            </div>
            <span class="badge badge-fact">EMPIRICAL FACTS</span>
          </div>
          ${evidenceList.length === 0 ? `
            <div style="color: var(--text-muted); font-size: 0.82rem;">No raw customer citations linked to this cluster.</div>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              ${evidenceList.map(ev => `
                <div class="evidence-quote-box" style="margin: 0; padding: 0.75rem; border-left-color: var(--epistemic-fact);">
                  <div style="color: #fff; font-weight: 500; font-size: 0.85rem;">"${escapeHtml(ev.verbatimQuote)}"</div>
                  <div class="evidence-meta" style="margin-top: 0.35rem;">
                    <span>Source: <strong>${escapeHtml(ev.sourceMetadata.source || 'Frontline')}</strong></span>
                    <span>Lang: <strong>${escapeHtml((ev.sourceMetadata.language || 'en').toUpperCase())}</strong></span>
                    <span>Confidence: <strong>${Math.round((ev.confidenceScore || 0.85) * 100)}%</strong></span>
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>

        <!-- 4. Operational Routing & SLA Status -->
        <div style="background: rgba(17, 24, 39, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
          <div style="font-size: 0.88rem; font-weight: 700; color: #fff; margin-bottom: 0.65rem;">
            🧭 Operational Routing & SLA Dispatch:
          </div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; font-size: 0.82rem;">
            <div>
              <span style="color: var(--text-muted);">Assigned Team:</span>
              <div style="font-weight: 700; color: #fff; font-size: 0.92rem; margin-top: 2px;">
                ${escapeHtml(issue.assignedTeamName || 'Human Triage Queue')}
              </div>
            </div>
            <div>
              <span style="color: var(--text-muted);">SLA Window:</span>
              <div style="font-weight: 700; color: #34d399; font-size: 0.92rem; margin-top: 2px;">
                ${issue.slaMinutes || 60} minutes
              </div>
            </div>
            <div>
              <span style="color: var(--text-muted);">Target Due Time:</span>
              <div style="font-weight: 700; color: #fff; font-size: 0.88rem; margin-top: 2px;">
                ${issue.slaDeadline ? new Date(issue.slaDeadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Immediate'}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer" style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
          <button class="btn btn-secondary btn-sm" id="btn-modal-open-lineage" data-id="${issue.id}">
            🧭 View Lineage DAG
          </button>
          <button class="btn btn-secondary btn-sm" id="btn-modal-open-routing" data-id="${issue.id}">
            🔀 Route / SLA
          </button>
          <button class="btn btn-secondary btn-sm" id="btn-modal-override" data-id="${issue.id}" data-score="${issue.priorityScore}">
            ✎ Override Score
          </button>
        </div>
        <div style="display: flex; gap: 0.4rem;">
          ${renderModalStatusAdvanceButton(issue)}
          <button class="btn btn-secondary btn-sm" id="btn-close-modal-footer">Close</button>
        </div>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-modal-footer').addEventListener('click', closeModal);

    document.getElementById('btn-modal-open-lineage').addEventListener('click', () => {
      openLineageGraphModal(issueId);
    });

    document.getElementById('btn-modal-open-routing').addEventListener('click', () => {
      openRoutingModal(issueId);
    });

    document.getElementById('btn-modal-override').addEventListener('click', () => {
      openOverridePriorityModal(issueId, issue.priorityScore);
    });

    const btnAdvance = document.getElementById('btn-modal-advance-status');
    if (btnAdvance) {
      btnAdvance.addEventListener('click', async () => {
        const nextStatus = btnAdvance.getAttribute('data-next');
        try {
          await api.updateIssueStatus(issueId, nextStatus, 'Status progression via Issue Detail Cockpit');
          showToast(`Issue advanced to ${nextStatus}`, 'success');
          await loadInitialData();
          openIssueDetailModal(issueId);
        } catch (err) {
          showToast('Failed to update status: ' + err.message, 'error');
        }
      });
    }

  } catch (err) {
    showToast('Failed to load issue detail: ' + err.message, 'error');
  }
}

function renderModalStatusAdvanceButton(issue) {
  if (issue.status === 'DETECTED') {
    return `<button class="btn btn-primary btn-sm" id="btn-modal-advance-status" data-next="TRIAGED">Advance to TRIAGED</button>`;
  }
  if (issue.status === 'TRIAGED') {
    return `<button class="btn btn-primary btn-sm" id="btn-modal-advance-status" data-next="DISPATCHED">Dispatch to Team</button>`;
  }
  if (issue.status === 'DISPATCHED') {
    return `<button class="btn btn-primary btn-sm" id="btn-modal-advance-status" data-next="IN_PROGRESS">Accept & Work</button>`;
  }
  if (issue.status === 'IN_PROGRESS') {
    return `<button class="btn btn-success btn-sm" id="btn-modal-advance-status" data-next="REMEDIATED">Log Physical Fix</button>`;
  }
  if (issue.status === 'REMEDIATED') {
    return `<button class="btn btn-primary btn-sm" id="btn-modal-advance-status" data-next="VERIFYING">Initiate Verification</button>`;
  }
  if (issue.status === 'VERIFYING') {
    return `<button class="btn btn-success btn-sm" id="btn-modal-advance-status" data-next="CLOSED">Verify & Close Issue</button>`;
  }
  return '';
}

async function openEvidenceModal(issueId) {
  try {
    const [issue, evidenceList] = await Promise.all([
      api.getIssue(issueId),
      api.getIssueEvidence(issueId)
    ]);

    openModal(`
      <div class="modal-header">
        <div>
          <h3 style="font-size: 1.1rem; font-weight: 700;">Evidence Graph & Citations</h3>
          <div style="font-size: 0.8rem; color: var(--text-muted);">${issue.title}</div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <div class="modal-body">
        <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
          <div style="font-weight: 700; color: #fff; font-size: 0.9rem;">Diagnostic Root-Cause Hypothesis:</div>
          <div style="font-size: 0.85rem; color: var(--accent-cyan); margin-top: 4px;">
            ${issue.rootCauseHypothesis || 'No hypothesis synthesized yet.'}
          </div>
        </div>

        <div style="font-weight: 700; color: #fff; font-size: 0.9rem;">Verbatim Grounded Citations (${evidenceList.length}):</div>
        ${evidenceList.length === 0 ? `<div style="color: var(--text-muted); font-size: 0.85rem;">No citations linked to this cluster.</div>` : ''}
        ${evidenceList.map(ev => `
          <div class="evidence-quote-box">
            <div style="color: #fff; font-weight: 500;">"${ev.verbatimQuote}"</div>
            <div class="evidence-meta">
              <span>Source: <strong>${ev.sourceMetadata.source || 'Frontline'}</strong></span>
              <span>Lang: <strong>${(ev.sourceMetadata.language || 'en').toUpperCase()}</strong></span>
              <span>Confidence: <strong>${(ev.confidenceScore * 100).toFixed(0)}%</strong></span>
            </div>
          </div>
        `).join('')}
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary btn-sm" id="btn-close-modal-footer">Close</button>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-modal-footer').addEventListener('click', closeModal);
  } catch (err) {
    showToast('Failed to load evidence: ' + err.message, 'error');
  }
}

function openCreateIssueModal() {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Log Operational Issue / Incident</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-create-issue">
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Incident Title</label>
          <input type="text" id="issue-title" class="form-input" required placeholder="e.g. Broken Glass in Frozen Aisle 2" />
        </div>
        <div class="form-group">
          <label class="form-label">Description & Symptoms</label>
          <textarea id="issue-desc" class="form-textarea" required placeholder="Describe observed physical breakdown or customer complaints..."></textarea>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Severity (0-1)</label>
            <input type="number" step="0.05" min="0" max="1" id="issue-severity" class="form-input" value="0.75" />
          </div>
          <div class="form-group">
            <label class="form-label">Urgency (0-1)</label>
            <input type="number" step="0.05" min="0" max="1" id="issue-urgency" class="form-input" value="0.80" />
          </div>
          <div class="form-group">
            <label class="form-label">Impact Scope (0-1)</label>
            <input type="number" step="0.05" min="0" max="1" id="issue-scope" class="form-input" value="0.60" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Assign Operational Team</label>
          <select id="issue-team" class="form-select">
            ${state.teams.map(t => `<option value="${t.id}">${t.name} (${t.teamType})</option>`).join('')}
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Incident</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('form-create-issue').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.createIssue({
        storeId: state.selectedStoreId,
        title: document.getElementById('issue-title').value,
        description: document.getElementById('issue-desc').value,
        severityScore: parseFloat(document.getElementById('issue-severity').value),
        urgencyScore: parseFloat(document.getElementById('issue-urgency').value),
        impactScopeScore: parseFloat(document.getElementById('issue-scope').value),
        assignedTeamId: document.getElementById('issue-team').value
      });
      showToast('Operational issue logged and priority calculated.', 'success');
      closeModal();
      await loadInitialData();
    } catch {}
  });
}

function openOverridePriorityModal(issueId, currentScore) {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Override Incident Priority Score</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-override-priority">
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Current Priority Score: <strong>${currentScore} / 100</strong></label>
          <input type="number" min="1" max="100" id="override-score" class="form-input" value="${currentScore}" required />
        </div>
        <div class="form-group">
          <label class="form-label">Mandatory Manager Justification</label>
          <textarea id="override-justification" class="form-textarea" required minlength="5" placeholder="Reason for adjusting AI/system priority score (logged to immutable audit trail)..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Submit Override</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('form-override-priority').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.overridePriority(
        issueId,
        parseInt(document.getElementById('override-score').value, 10),
        document.getElementById('override-justification').value
      );
      showToast('Priority score overridden and recorded in audit log.', 'success');
      closeModal();
      await loadInitialData();
    } catch {}
  });
}

function openOverrideRoutingModal(actionId) {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Override Work Order Routing</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-override-routing">
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Reassign to Operational Team</label>
          <select id="new-target-team" class="form-select">
            ${state.teams.map(t => `<option value="${t.id}">${t.name} (${t.teamType})</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Mandatory Override Reason</label>
          <textarea id="routing-override-reason" class="form-textarea" required minlength="5" placeholder="Explain why the automated routing is being redirected (recorded to audit log)..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Routing Override</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('form-override-routing').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.overrideRouting(
        actionId,
        document.getElementById('new-target-team').value,
        document.getElementById('routing-override-reason').value
      );
      showToast('Routing overridden and team reassigned.', 'success');
      closeModal();
      await loadInitialData();
    } catch {}
  });
}


function openRegisterApplianceModal() {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Register Home Appliance (Extensibility)</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-register-appliance">
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Appliance Type</label>
          <select id="app-type" class="form-select">
            <option value="REFRIGERATOR">Refrigerator</option>
            <option value="TV">Television</option>
            <option value="AC">Air Conditioner</option>
            <option value="WASHING_MACHINE">Washing Machine</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Brand / Manufacturer</label>
          <input type="text" id="app-brand" class="form-input" required placeholder="e.g. LG, Samsung, Whirlpool" />
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Model Number</label>
            <input type="text" id="app-model" class="form-input" placeholder="e.g. LRFCS2503S" />
          </div>
          <div class="form-group">
            <label class="form-label">Serial Number</label>
            <input type="text" id="app-serial" class="form-input" placeholder="e.g. SN-991203" />
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Appliance</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('form-register-appliance').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.registerHomeAppliance({
        applianceType: document.getElementById('app-type').value,
        brand: document.getElementById('app-brand').value,
        modelNumber: document.getElementById('app-model').value,
        serialNumber: document.getElementById('app-serial').value
      });
      showToast('Appliance registered into personal vault.', 'success');
      closeModal();
      await renderActiveView();
    } catch {}
  });
}

function openFileServiceTicketModal(applianceId) {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Request Appliance Service</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-file-ticket">
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Describe Problem / Defect</label>
          <textarea id="ticket-desc" class="form-textarea" required placeholder="Describe symptoms (e.g. compressor not cooling, noise)..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Submit to Service Channel</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('form-file-ticket').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.createHomeTicket({
        applianceId,
        complaintDescription: document.getElementById('ticket-desc').value
      });
      showToast('Warranty service ticket filed to authorized channel.', 'success');
      closeModal();
      await renderActiveView();
    } catch {}
  });
}

/* -------------------------------------------------------------------------
   MODAL: SEMANTIC CLUSTER INSPECTOR & SPLIT/MERGE (PHASE 6)
-------------------------------------------------------------------------- */
async function openClusterDetailModal(clusterId, onSuccess) {
  try {
    const c = await api.getCluster(clusterId);

    openModal(`
      <div class="modal-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700;">Semantic Cluster Inspector</h3>
            <span class="badge ${c.status === 'ACTIVE' ? 'badge-p4' : 'badge-neutral'}">${c.status}</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
            Cluster ID: <code class="table-id-mono">${c.id}</code> | Category: <strong>${c.category.replace(/_/g, ' ')}</strong>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <div class="modal-body" style="max-height: 75vh; overflow-y: auto;">
        <!-- Grounded Quality Banner -->
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 700; color: #fff; font-size: 0.95rem;">${c.title}</span>
            <span style="color: #34d399; font-weight: 700; font-size: 0.9rem;">${Math.round(c.qualityScore * 100)}% Cluster Quality</span>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem; line-height: 1.4;">
            ${c.summary}
          </div>
          <div style="display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">
            <span>Primary Entity: <strong>${c.primaryEntity || 'Unspecified'}</strong></span>
            <span>Location: <strong>${c.primaryLocation || 'Store-wide'}</strong></span>
            <span>Source Diversity: <strong>${c.sourceDiversityCount} channel(s)</strong></span>
          </div>
        </div>

        <!-- Grounded Member Evidence -->
        <div style="font-weight: 700; color: #fff; font-size: 0.9rem; margin-bottom: 0.5rem;">
          Member Feedback Citations (${(c.members || []).length}):
        </div>
        <div style="display: flex; flex-direction: column; gap: 0.6rem;">
          ${(c.members || []).map(m => `
            <div class="evidence-quote-box" style="margin: 0; padding: 0.75rem;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="color: #fff; font-weight: 500; font-size: 0.85rem;">"${m.rawText}"</div>
                <span class="badge ${m.correlationType === 'SAME_ISSUE' ? 'badge-p4' : 'badge-neutral'}" style="font-size: 0.68rem; margin-left: 0.5rem; white-space: nowrap;">
                  ${m.correlationType.replace(/_/g, ' ')} (${Math.round(m.similarityScore * 100)}%)
                </span>
              </div>
              <div class="evidence-meta" style="margin-top: 0.4rem;">
                <span>Channel: <strong>${m.channelType}</strong></span>
                <span>Submitter: <strong>${m.submitterType}</strong></span>
                <span>Submitted: <strong>${new Date(m.submittedAt).toLocaleString()}</strong></span>
              </div>
            </div>
          `).join('')}
        </div>

        <!-- Human Split / Eject Console -->
        <form id="form-split-cluster" style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.85rem; margin-top: 1rem;">
          <div style="font-weight: 700; color: #fbbf24; font-size: 0.82rem; margin-bottom: 0.4rem;">
            ✂️ Human Split: Eject Irrelevant Feedback
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">
            Select feedback items that represent a distinct operational breakdown to segregate them into a new cluster:
          </div>
          <div style="display: flex; flex-direction: column; gap: 0.35rem; max-height: 120px; overflow-y: auto; margin-bottom: 0.65rem;">
            ${(c.members || []).map(m => `
              <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.78rem; color: var(--text-secondary); cursor: pointer;">
                <input type="checkbox" name="eject-item" value="${m.feedbackItemId}" />
                <span>"${m.rawText.slice(0, 75)}..." (${m.channelType})</span>
              </label>
            `).join('')}
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <input type="text" id="split-new-title" class="form-input" style="font-size: 0.78rem; padding: 4px 8px;" placeholder="Title for newly segregated cluster..." />
            <button type="submit" class="btn btn-secondary btn-sm" style="white-space: nowrap;">Execute Split</button>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="btn-close-modal-footer">Close Inspector</button>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-modal-footer').addEventListener('click', closeModal);

    document.getElementById('form-split-cluster').addEventListener('submit', async (e) => {
      e.preventDefault();
      const checkboxes = document.querySelectorAll('input[name="eject-item"]:checked');
      const ejectIds = Array.from(checkboxes).map(cb => cb.value);
      if (ejectIds.length === 0) {
        showToast('Select at least one report to eject.', 'info');
        return;
      }
      const newTitle = document.getElementById('split-new-title').value.trim() || undefined;
      try {
        await api.splitCluster(clusterId, ejectIds, newTitle, 'Human-initiated segregation via inspector');
        showToast(`Segregated ${ejectIds.length} report(s) into new cluster.`, 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {
        showToast('Split failed: ' + err.message, 'error');
      }
    });

  } catch (err) {
    showToast('Failed to load cluster: ' + err.message, 'error');
  }
}

/* -------------------------------------------------------------------------
   MODAL: FULL EVIDENCE & OPERATIONAL LINEAGE DAG (PHASE 9)
-------------------------------------------------------------------------- */
async function openLineageGraphModal(issueId) {
  try {
    const res = await api.getIssueLineage(issueId);
    const data = res.data || res;
    const nodes = data.nodes || [];
    const edges = data.edges || [];

    openModal(`
      <div class="modal-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700;">Traceable Operational Lineage DAG</h3>
            <span class="badge badge-p4">Lineage Model Verified</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
            Feedback ➔ AI Extraction ➔ Investigation Q&A ➔ Cluster ➔ Incident ➔ Alert ➔ Action ➔ Outcome
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <div class="modal-body" style="max-height: 75vh; overflow-y: auto;">
        <!-- Epistemological Counter Bar -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.65rem; margin-bottom: 1rem;">
          <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; text-align: center;">
            <div style="font-size: 1.25rem; font-weight: 800; color: #34d399;">${data.factsCount || 0}</div>
            <div style="font-size: 0.72rem; color: #34d399; font-weight: 700;">FACTS (EMPIRICAL)</div>
          </div>
          <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; text-align: center;">
            <div style="font-size: 1.25rem; font-weight: 800; color: #38bdf8;">${data.hypothesesCount || 0}</div>
            <div style="font-size: 0.72rem; color: #38bdf8; font-weight: 700;">DIAGNOSTIC HYPOTHESES</div>
          </div>
          <div style="background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; text-align: center;">
            <div style="font-size: 1.25rem; font-weight: 800; color: #c084fc;">${data.recommendationsCount || 0}</div>
            <div style="font-size: 0.72rem; color: #c084fc; font-weight: 700;">RECOMMENDATIONS</div>
          </div>
          <div style="background: rgba(148, 163, 184, 0.1); border: 1px solid rgba(148, 163, 184, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; text-align: center;">
            <div style="font-size: 1.25rem; font-weight: 800; color: #94a3b8;">${data.unknownsCount || 0}</div>
            <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 700;">UNKNOWNS / UNCONFIRMED</div>
          </div>
        </div>

        <!-- Strict Zero-Hallucination Warning -->
        <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: var(--radius-sm); padding: 0.65rem; margin-bottom: 1rem; font-size: 0.78rem; color: #fbbf24;">
          <strong>Epistemological Guardrail:</strong> Diagnoses and root-causes are strictly classified as <code>[HYPOTHESIS]</code> requiring field verification until a technician signs off on the resolution.
        </div>

        <!-- Lineage DAG Nodes Flow -->
        <div style="font-weight: 700; color: #fff; font-size: 0.9rem; margin-bottom: 0.65rem;">
          Lineage Chain & Graph Elements (${nodes.length} Nodes, ${edges.length} Directed Relationships):
        </div>
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${nodes.map(n => {
            const badgeColor = n.claimType === 'FACT' ? 'background: rgba(16, 185, 129, 0.2); color: #34d399;'
              : n.claimType === 'HYPOTHESIS' ? 'background: rgba(56, 189, 248, 0.2); color: #38bdf8;'
              : n.claimType === 'RECOMMENDATION' ? 'background: rgba(168, 85, 247, 0.2); color: #c084fc;'
              : 'background: rgba(148, 163, 184, 0.2); color: #94a3b8;';

            return `
              <div class="field-card" style="margin: 0; padding: 0.85rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 0.72rem; font-family: var(--font-family-mono); color: var(--text-muted);">${n.type}</span>
                    <strong style="color: #fff; font-size: 0.88rem;">${n.label}</strong>
                  </div>
                  <span class="badge" style="${badgeColor} font-size: 0.68rem; font-weight: 700;">
                    ${n.claimType} (${Math.round((n.confidence || 1) * 100)}%)
                  </span>
                </div>
                <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.4rem;">
                  ${Object.entries(n.details || {}).map(([k, v]) => `
                    <span style="margin-right: 0.75rem;">${k}: <strong style="color: #fff;">${typeof v === 'object' ? JSON.stringify(v) : v}</strong></span>
                  `).join('')}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="btn-close-modal-footer">Close Lineage</button>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-modal-footer').addEventListener('click', closeModal);

  } catch (err) {
    showToast('Failed to load lineage DAG: ' + err.message, 'error');
  }
}

/* -------------------------------------------------------------------------
   MODAL: DETAILED ALERT CITATIONS & EVIDENCE BREAKDOWN (PHASE 7 & 9)
-------------------------------------------------------------------------- */
async function openAlertEvidenceModal(alertId) {
  try {
    const res = await api.getAlertEvidence(alertId);
    const a = res.data || res;

    openModal(`
      <div class="modal-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700;">Emerging Alert Evidence & Baseline Audit</h3>
            <span class="badge ${a.baselineStatus === 'ANOMALY' ? 'badge-p1' : a.baselineStatus === 'INSUFFICIENT_BASELINE' ? 'badge-p2' : 'badge-neutral'}">
              ${a.baselineStatus}
            </span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
            Alert ID: <code class="table-id-mono">${a.alertId}</code> | Store: <strong>${a.whereZone}</strong>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <div class="modal-body" style="max-height: 75vh; overflow-y: auto;">
        <!-- Deterministic Claims Table -->
        <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
          <div style="font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;">
            Deterministic Baseline Analytics:
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; font-size: 0.82rem;">
            <div>
              <span style="color: var(--text-muted);">Recent Frequency (24h):</span>
              <div style="font-weight: 700; color: #fff; font-size: 1rem;">${a.observationCount} observation(s)</div>
            </div>
            <div>
              <span style="color: var(--text-muted);">Velocity Z-Score:</span>
              <div style="font-weight: 700; color: ${a.velocityZscore >= 2.0 ? 'var(--p1-critical)' : '#38bdf8'}; font-size: 1rem;">
                +${a.velocityZscore}z above baseline
              </div>
            </div>
            <div>
              <span style="color: var(--text-muted);">Growth vs Expectation:</span>
              <div style="font-weight: 700; color: ${a.growthRate > 0 ? '#34d399' : '#fff'}; font-size: 1rem;">
                +${Math.round(a.growthRate * 100)}%
              </div>
            </div>
          </div>
          <div style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4;">
            <strong>Generation Rationale:</strong> ${a.whyGenerated}
          </div>
        </div>

        <!-- Uncertainties Callout -->
        ${(a.uncertainties && a.uncertainties.length > 0) ? `
          <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: var(--radius-sm); padding: 0.75rem; margin-bottom: 1rem; font-size: 0.8rem; color: #fbbf24;">
            <strong>Operational Uncertainties:</strong>
            <ul style="margin: 4px 0 0 1.25rem; padding: 0;">
              ${a.uncertainties.map(u => `<li>${u}</li>`).join('')}
            </ul>
          </div>
        ` : ''}

        <!-- Sources Summary -->
        <div style="font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 0.4rem;">
          Cross-Source Channel Confirmation:
        </div>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
          ${(a.sources || []).map(s => `<span class="badge badge-neutral">${s.replace(/_/g, ' ')}</span>`).join('')}
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="btn-close-modal-footer">Close Evidence</button>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-modal-footer').addEventListener('click', closeModal);

  } catch (err) {
    showToast('Failed to load alert evidence: ' + err.message, 'error');
  }
}

function getPriorityColor(tier) {
  if (tier === 'P1_CRITICAL') return 'var(--p1-critical)';
  if (tier === 'P2_HIGH') return 'var(--p2-high)';
  if (tier === 'P3_MEDIUM') return 'var(--p3-medium)';
  return 'var(--p4-low)';
}

function getSlaCountdownHtml(item) {
  if (item.status === 'CLOSED') {
    return `<span class="sla-countdown-pill sla-resolved">✓ Closed</span>`;
  }
  if (!item.slaDeadline) {
    return `<span class="sla-countdown-pill sla-normal">SLA: ${item.slaMinutes || 60}m</span>`;
  }
  const remainingMs = new Date(item.slaDeadline).getTime() - Date.now();
  const remainingMins = Math.round(remainingMs / 60000);
  if (remainingMins < 0) {
    return `<span class="sla-countdown-pill sla-breached">⚠️ SLA Breached (${Math.abs(remainingMins)}m ago)</span>`;
  }
  if (remainingMins <= 30) {
    return `<span class="sla-countdown-pill sla-warning">⏳ ${remainingMins}m remaining</span>`;
  }
  return `<span class="sla-countdown-pill sla-normal">⏱️ ${remainingMins}m remaining</span>`;
}

async function openRoutingModal(issueId) {
  try {
    const issue = await api.getIssue(issueId);
    const history = await api.getIssueRoutingHistory(issueId);
    const teams = await api.getTeams(state.selectedStoreId) || [];
    const latest = history[0] || null;

    openModal(`
      <div class="modal-header">
        <div>
          <div class="modal-title">🔀 Intelligent Operational Routing</div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
            Incident: <strong>${escapeHtml(issue.title)}</strong> | Store: <strong>${issue.storeId}</strong>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <div class="modal-body" style="max-height: 75vh; overflow-y: auto;">
        ${latest && latest.isAmbiguous ? `
          <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: var(--radius-sm); padding: 0.75rem; margin-bottom: 1rem; font-size: 0.82rem; color: #fbbf24;">
            <strong>⚠️ Routed to Central Human Triage Queue:</strong>
            <div style="margin-top: 4px;">${escapeHtml(latest.reason)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
              System avoided automated guesswork due to low classification confidence (${Math.round(latest.confidence * 100)}%).
            </div>
          </div>
        ` : ''}

        <!-- Current Routing Details Card -->
        <div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1.25rem;">
          <div style="font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 0.6rem;">
            Current Operational Assignment:
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; font-size: 0.82rem;">
            <div>
              <span style="color: var(--text-muted);">Assigned Team:</span>
              <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">
                ${latest && latest.selectedTeamName ? escapeHtml(latest.selectedTeamName) : (issue.assignedTeamName || 'Unassigned')}
              </div>
            </div>
            <div>
              <span style="color: var(--text-muted);">Routing Strategy:</span>
              <div style="font-weight: 700; color: #38bdf8;">
                ${latest ? escapeHtml(latest.routingStrategy) : 'SYSTEM_DEFAULT'}
              </div>
            </div>
            <div>
              <span style="color: var(--text-muted);">SLA Window:</span>
              <div style="font-weight: 700; color: #34d399; font-size: 0.95rem;">
                ${issue.slaMinutes || 60} minutes
              </div>
            </div>
          </div>
          ${latest ? `
            <div style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4;">
              <strong>Determination Rationale:</strong> ${escapeHtml(latest.reason)}
            </div>
          ` : ''}
        </div>

        <!-- Action Dispatch Controls -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.25rem;">
          <!-- Manual Reassign (Human Override) -->
          <div style="background: rgba(17, 24, 39, 0.5); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem;">
            <div style="font-weight: 700; font-size: 0.85rem; color: #fff; margin-bottom: 0.5rem;">
              👤 Manual Reassignment (Human Override)
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <select id="reassign-team-select" class="r5-input" style="font-size: 0.8rem; padding: 0.35rem 0.5rem;">
                <option value="">-- Select Target Operational Team --</option>
                ${teams.map(t => `<option value="${t.id}">${escapeHtml(t.name)} (${t.specialization || t.teamType})</option>`).join('')}
              </select>
              <input type="text" id="reassign-reason-input" class="r5-input" placeholder="Justification for override..." style="font-size: 0.8rem; padding: 0.35rem 0.5rem;" />
              <button class="btn btn-secondary btn-sm" id="btn-submit-reassign" style="align-self: flex-start;">
                Save Reassignment
              </button>
            </div>
          </div>

          <!-- Escalate Issue -->
          <div style="background: rgba(17, 24, 39, 0.5); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem;">
            <div style="font-weight: 700; font-size: 0.85rem; color: #fff; margin-bottom: 0.5rem;">
              🚨 Operational Escalation
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted);">
                Accelerates SLA deadline by 50% and escalates to secondary tier.
              </div>
              <input type="text" id="escalate-reason-input" class="r5-input" placeholder="Escalation notes & severity rationale..." style="font-size: 0.8rem; padding: 0.35rem 0.5rem;" />
              <button class="btn btn-warning btn-sm" id="btn-submit-escalate" style="align-self: flex-start;">
                Escalate Incident
              </button>
            </div>
          </div>
        </div>

        <!-- Routing Lineage History -->
        <div style="font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;">
          Chronological Routing History:
        </div>
        ${history.length === 0 ? `
          <div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No historical routing decisions logged yet.</div>
        ` : `
          <div class="r5-table-container">
            <table class="r5-table" style="font-size: 0.78rem;">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Team & Tier</th>
                  <th>Strategy</th>
                  <th>Confidence</th>
                  <th>Reason & Provenance</th>
                </tr>
              </thead>
              <tbody>
                ${history.map(h => `
                  <tr>
                    <td style="color: var(--text-muted);">${new Date(h.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</td>
                    <td>
                      <strong>${h.selectedTeamName || 'Human Triage Queue'}</strong>
                      ${h.isHumanOverride ? `<span class="badge badge-warning" style="margin-left: 4px;">Override</span>` : ''}
                    </td>
                    <td><code>${h.routingStrategy}</code></td>
                    <td>${Math.round(h.confidence * 100)}%</td>
                    <td style="color: var(--text-secondary); max-width: 250px;">${escapeHtml(h.reason)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
      <div class="modal-footer" style="display: flex; justify-content: space-between;">
        <button class="btn btn-secondary btn-sm" id="btn-trigger-autoroute">
          ⚡ Re-evaluate Auto-Routing
        </button>
        <button class="btn btn-secondary" id="btn-close-modal-footer">Close</button>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-modal-footer').addEventListener('click', closeModal);

    document.getElementById('btn-trigger-autoroute').addEventListener('click', async () => {
      try {
        await api.routeIssue(issueId);
        showToast('Automatic routing re-evaluated and recorded.', 'success');
        closeModal();
        const main = document.getElementById('main-content');
        if (main) renderIssuesView(main);
      } catch (err) {
        showToast('Error auto-routing issue: ' + err.message, 'error');
      }
    });

    document.getElementById('btn-submit-reassign').addEventListener('click', async () => {
      const teamId = document.getElementById('reassign-team-select').value;
      const reason = document.getElementById('reassign-reason-input').value.trim();
      if (!teamId) {
        showToast('Please select a target operational team.', 'warning');
        return;
      }
      if (!reason || reason.length < 3) {
        showToast('Please provide a justification for manual reassignment.', 'warning');
        return;
      }
      try {
        await api.reassignIssue(issueId, { targetTeamId: teamId, reassignmentReason: reason });
        showToast('Issue reassigned successfully (Human override recorded).', 'success');
        closeModal();
        const main = document.getElementById('main-content');
        if (main) renderIssuesView(main);
      } catch (err) {
        showToast('Error reassigning issue: ' + err.message, 'error');
      }
    });

    document.getElementById('btn-submit-escalate').addEventListener('click', async () => {
      const reason = document.getElementById('escalate-reason-input').value.trim();
      if (!reason || reason.length < 3) {
        showToast('Please provide escalation notes.', 'warning');
        return;
      }
      try {
        await api.escalateIssue(issueId, { escalationReason: reason });
        showToast('Issue escalated and SLA accelerated.', 'success');
        closeModal();
        const main = document.getElementById('main-content');
        if (main) renderIssuesView(main);
      } catch (err) {
        showToast('Error escalating issue: ' + err.message, 'error');
      }
    });

  } catch (err) {
    showToast('Failed to load routing details: ' + err.message, 'error');
  }
}

function getSelectedStoreNumber() {
  const store = state.stores.find(s => s.id === state.selectedStoreId);
  return store ? store.storeNumber : '104';
}

// Start
document.addEventListener('DOMContentLoaded', init);
