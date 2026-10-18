/**
 * Swift Service - Organization Admin Portal Controller
 * Executive fleet governance, real KPI aggregation, store CRUD,
 * Store Manager provisioning, complaint triage, and operational audits.
 * Strictly light-mode, premium responsive design.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';
import { escapeHtml } from './ui-utils.js';
import { COMPLAINT_CATEGORIES } from './customer-portal.js';

let adminComplaintSearch = '';
let adminComplaintCategory = 'ALL';
let adminComplaintStatus = 'ALL';

export async function renderOrgAdminDashboard(container) {
  container.innerHTML = `
    <div style="padding: 2.5rem 1rem; text-align: center; color: var(--text-muted);">
      <div class="spinner" style="margin: 0 auto 1rem;"></div>
      Loading Organization Admin fleet intelligence and complaint records...
    </div>
  `;

  try {
    const [complaintsRes, stores, users, issues, alerts, auditLogs, teams, regions] = await Promise.all([
      api.listComplaints({ limit: 100 }),
      api.getStores(),
      api.getUsers(),
      api.getIssues(),
      api.getAlerts(),
      api.getAuditLogs().catch(() => []),
      api.getTeams(),
      api.getRegions(state.selectedOrgId).catch(() => [])
    ]);

    const complaints = complaintsRes.items || complaintsRes || [];
    const activeStores = stores.filter(s => s.operatingStatus !== 'DECOMMISSIONED');
    const storeManagers = users.filter(u => u.role === 'STORE_MANAGER' && u.isActive);

    const totalComplaints = complaints.length;
    const openComplaints = complaints.filter(c => c.status === 'SUBMITTED' || c.status === 'UNDER_REVIEW').length;
    const inProgressComplaints = complaints.filter(c => c.status === 'IN_PROGRESS').length;
    const resolvedComplaints = complaints.filter(c => c.status === 'RESOLVED' || c.status === 'CLOSED').length;
    const highPriorityComplaints = complaints.filter(c => c.priority === 'CRITICAL' || c.priority === 'HIGH').length;
    const emergingIssuesCount = issues.filter(i => i.isEmergingAnomaly || (i.status !== 'CLOSED' && i.status !== 'REMEDIATED')).length;

    container.innerHTML = `
      <div class="admin-portal-wrapper">
        <!-- Organization Header & Fleet Context -->
        <div class="view-header" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem;">
              <span class="badge" style="background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; font-weight: 700;">
                🏢 Organization Admin Portal
              </span>
              <span class="badge badge-neutral">Apex Retail International</span>
            </div>
            <h1 class="view-title" style="color: #0f172a; font-size: 1.6rem; font-weight: 800; margin: 0 0 0.35rem 0;">
              Executive Operations & Customer Intelligence
            </h1>
            <p class="view-subtitle" style="color: #64748b; font-size: 0.9rem; margin: 0;">
              Fleet oversight, complaint resolution tracking, store facility governance, and Store Manager assignments.
            </p>
          </div>
          <div class="view-header-actions" style="display: flex; gap: 0.65rem; flex-wrap: wrap; align-items: center;">
            <button class="btn btn-primary" id="btn-admin-add-store" style="font-weight: 600;">
              + Add Retail Store
            </button>
            <button class="btn btn-secondary" id="btn-admin-provision-mgr" style="font-weight: 600;">
              + Provision Store Manager
            </button>
            <button class="btn btn-secondary" id="btn-admin-preview-customer" title="Switch view to Customer Experience Portal">
              🛍️ Customer Portal
            </button>
          </div>
        </div>

        <!-- 8 Key Operational Metrics Grid (Calculated from Real Database Records) -->
        <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">Total Complaint Volume</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #0f172a; margin: 0.25rem 0;">${totalComplaints}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Verified customer reports</div>
          </div>

          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">Open & Under Review</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #d97706; margin: 0.25rem 0;">${openComplaints}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Initial intake and triage</div>
          </div>

          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">In Progress (Remediation)</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #2563eb; margin: 0.25rem 0;">${inProgressComplaints}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Assigned to field staff</div>
          </div>

          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">Verified Resolved</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #16a34a; margin: 0.25rem 0;">${resolvedComplaints}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Resolution note published</div>
          </div>

          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">High / Critical Priority</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #dc2626; margin: 0.25rem 0;">${highPriorityComplaints}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Urgent refrigeration/safety</div>
          </div>

          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">Emerging Operational Issues</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #7c3aed; margin: 0.25rem 0;">${emergingIssuesCount}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Voice-of-Store anomalies</div>
          </div>

          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">Active Fleet Stores</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #0f172a; margin: 0.25rem 0;">${activeStores.length}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Retail branch locations</div>
          </div>

          <div class="stat-card" style="background: #ffffff; border: 1px solid #e2e8f0; padding: 1.15rem; border-radius: 8px;">
            <div class="stat-label" style="color: #64748b; font-size: 0.78rem; text-transform: uppercase; font-weight: 600;">Active Store Managers</div>
            <div class="stat-value" style="font-size: 1.8rem; font-weight: 800; color: #0284c7; margin: 0.25rem 0;">${storeManagers.length}</div>
            <div class="stat-subtext" style="color: #64748b; font-size: 0.75rem;">Provisioned leadership</div>
          </div>
        </div>

        <!-- Section 1: Store Performance & Issue Distribution -->
        <div class="r5-card" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
          <div class="r5-card-header" style="border-bottom: 1px solid #e2e8f0; padding: 1.15rem 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
            <div>
              <div style="font-weight: 700; font-size: 1.1rem; color: #0f172a; display: flex; align-items: center; gap: 0.4rem;">
                <span>🏪</span> Store Performance & Fleet Governance
              </div>
              <div style="font-size: 0.8rem; color: #64748b; margin-top: 2px;">
                Operational status, assigned Store Managers, and active complaint distribution across stores.
              </div>
            </div>
            <button class="btn btn-secondary btn-sm" id="btn-admin-manage-all-stores">
              Manage Fleet in Org View →
            </button>
          </div>

          <div class="r5-card-body" style="padding: 0; overflow-x: auto;">
            <table class="r5-table" style="width: 100%; border-collapse: collapse;">
              <thead>
                <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Store Facility</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Region</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Operating Status</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Assigned Store Manager</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Open Complaints</th>
                  <th style="padding: 0.75rem 1rem; text-align: right; font-size: 0.78rem; color: #475569;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${stores.map(s => {
                  const sComplaints = complaints.filter(c => c.storeId === s.id && c.status !== 'RESOLVED' && c.status !== 'CLOSED');
                  const assignedManager = users.find(u => u.role === 'STORE_MANAGER' && u.storeId === s.id);
                  const isDecom = s.operatingStatus === 'DECOMMISSIONED';

                  return `
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                      <td style="padding: 0.85rem 1rem;">
                        <strong style="color: #0f172a; font-size: 0.9rem;">#${s.storeNumber} &mdash; ${escapeHtml(s.name)}</strong>
                        <div style="font-size: 0.75rem; color: #64748b;">Format: ${escapeHtml(s.metadata?.formatTier || 'SUPERCENTER')}</div>
                      </td>
                      <td style="padding: 0.85rem 1rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Pacific Northwest</span>
                      </td>
                      <td style="padding: 0.85rem 1rem;">
                        <span class="badge ${isDecom ? 'badge-p4' : 'badge-neutral'}" style="font-size: 0.75rem; font-weight: 600;">
                          ${escapeHtml((s.operatingStatus || 'OPERATIONAL').replace(/_/g, ' '))}
                        </span>
                      </td>
                      <td style="padding: 0.85rem 1rem;">
                        ${assignedManager ? `
                          <div style="font-weight: 600; color: #0f172a; font-size: 0.85rem;">👤 ${escapeHtml(assignedManager.fullName)}</div>
                          <div style="font-size: 0.72rem; color: #64748b;">${escapeHtml(assignedManager.email)}</div>
                        ` : `
                          <span style="color: #d97706; font-size: 0.8rem; font-weight: 600;">⚠️ Unassigned</span>
                        `}
                      </td>
                      <td style="padding: 0.85rem 1rem;">
                        <span class="badge ${sComplaints.length > 0 ? 'badge-p2' : 'badge-neutral'}" style="font-size: 0.8rem;">
                          ${sComplaints.length} active
                        </span>
                      </td>
                      <td style="padding: 0.85rem 1rem; text-align: right;">
                        <div style="display: inline-flex; gap: 0.35rem;">
                          <button class="btn btn-secondary btn-sm btn-assign-mgr-store" data-id="${s.id}" data-name="${escapeHtml(s.name)}">
                            Assign Manager
                          </button>
                          <button class="btn btn-secondary btn-sm btn-toggle-store-status" data-id="${s.id}" data-status="${s.operatingStatus || 'OPERATIONAL'}">
                            ${isDecom ? 'Reactivate' : 'Deactivate'}
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

        <!-- Section 2: Authoritative Complaint Management Table -->
        <div class="r5-card" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
          <div class="r5-card-header" style="border-bottom: 1px solid #e2e8f0; padding: 1.15rem 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
              <div style="font-weight: 700; font-size: 1.1rem; color: #0f172a; display: flex; align-items: center; gap: 0.4rem;">
                <span>💬</span> Customer Complaint Management Stream (${complaints.length})
              </div>
              <div style="font-size: 0.8rem; color: #64748b; margin-top: 2px;">
                Comprehensive intake triage, root-cause investigation, and operational status transitions.
              </div>
            </div>

            <div style="display: flex; gap: 0.65rem; align-items: center; flex-wrap: wrap;">
              <input 
                type="text" 
                id="admin-filter-complaints-search" 
                class="form-input" 
                style="width: 200px; font-size: 0.82rem;" 
                placeholder="Search reference, subject..." 
                value="${escapeHtml(adminComplaintSearch)}" 
              />

              <select id="admin-filter-complaints-category" class="form-input" style="width: 170px; font-size: 0.82rem;">
                <option value="ALL" ${adminComplaintCategory === 'ALL' ? 'selected' : ''}>All Categories</option>
                ${COMPLAINT_CATEGORIES.map(c => `
                  <option value="${c.id}" ${adminComplaintCategory === c.id ? 'selected' : ''}>${c.title}</option>
                `).join('')}
              </select>

              <select id="admin-filter-complaints-status" class="form-input" style="width: 140px; font-size: 0.82rem;">
                <option value="ALL" ${adminComplaintStatus === 'ALL' ? 'selected' : ''}>All Statuses</option>
                <option value="SUBMITTED" ${adminComplaintStatus === 'SUBMITTED' ? 'selected' : ''}>Submitted</option>
                <option value="UNDER_REVIEW" ${adminComplaintStatus === 'UNDER_REVIEW' ? 'selected' : ''}>Under Review</option>
                <option value="IN_PROGRESS" ${adminComplaintStatus === 'IN_PROGRESS' ? 'selected' : ''}>In Progress</option>
                <option value="RESOLVED" ${adminComplaintStatus === 'RESOLVED' ? 'selected' : ''}>Resolved</option>
                <option value="CLOSED" ${adminComplaintStatus === 'CLOSED' ? 'selected' : ''}>Closed</option>
              </select>
            </div>
          </div>

          <div class="r5-card-body" style="padding: 0; overflow-x: auto;">
            <table class="r5-table" style="width: 100%; border-collapse: collapse;" id="table-admin-complaints">
              <thead>
                <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Reference</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Customer</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Category</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Subject</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Store Facility</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Status</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Priority</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Assigned Owner</th>
                  <th style="padding: 0.75rem 1rem; text-align: left; font-size: 0.78rem; color: #475569;">Submitted</th>
                  <th style="padding: 0.75rem 1rem; text-align: right; font-size: 0.78rem; color: #475569;">Actions</th>
                </tr>
              </thead>
              <tbody id="tbody-admin-complaints">
                ${renderAdminComplaintRows(complaints)}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Section 3: Recent Activity & Governance Audit Trail -->
        <div class="r5-card" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
          <div class="r5-card-header" style="border-bottom: 1px solid #e2e8f0; padding: 1.15rem 1.5rem;">
            <div style="font-weight: 700; font-size: 1.05rem; color: #0f172a; display: flex; align-items: center; gap: 0.4rem;">
              <span>📜</span> Recent Operational Activity & Governance Audit Trail
            </div>
          </div>
          <div class="r5-card-body" style="padding: 1.25rem 1.5rem;">
            <div class="audit-stream" style="display: flex; flex-direction: column; gap: 0.85rem;">
              ${auditLogs && auditLogs.length > 0 ? auditLogs.slice(0, 5).map(log => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 0.75rem; border-bottom: 1px solid #f1f5f9;">
                  <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.2rem;">⚡</span>
                    <div>
                      <div style="font-weight: 600; font-size: 0.85rem; color: #0f172a;">${escapeHtml(log.action || 'OPERATIONAL_UPDATE')} &mdash; ${escapeHtml(log.entityType || 'SYSTEM')} (${escapeHtml(log.entityId || '')})</div>
                      <div style="font-size: 0.75rem; color: #64748b;">Actor: <strong>${escapeHtml(log.performedBy || 'System')}</strong></div>
                    </div>
                  </div>
                  <div style="font-size: 0.75rem; color: #64748b;">
                    ${new Date(log.timestamp || Date.now()).toLocaleTimeString()}
                  </div>
                </div>
              `).join('') : `
                <div style="text-align: center; color: #64748b; padding: 1rem; font-size: 0.85rem;">
                  ✓ Audit logging active. No high-severity governance events recorded today.
                </div>
              `}
            </div>
          </div>
        </div>

        <!-- Complaint Investigation Drawer Placeholder -->
        <div id="admin-complaint-investigation-drawer" class="rw-drawer" style="display: none;"></div>
      </div>
    `;

    attachAdminDashboardEvents(container, complaints, stores, users, teams, regions);

  } catch (err) {
    console.error('Error rendering Organization Admin dashboard:', err);
    container.innerHTML = `
      <div class="r5-card">
        <div class="r5-card-body" style="padding: 2rem; text-align: center; color: #dc2626;">
          <h3>Error Loading Organization Admin Dashboard</h3>
          <p>${escapeHtml(err.message || 'Unable to connect to backend services')}</p>
          <button class="btn btn-secondary btn-sm" onclick="location.reload()">Retry Connection</button>
        </div>
      </div>
    `;
  }
}

function renderAdminComplaintRows(complaints) {
  let filtered = complaints;
  const q = adminComplaintSearch.toLowerCase();
  if (q) {
    filtered = filtered.filter(c => 
      c.referenceNumber.toLowerCase().includes(q) ||
      c.subject.toLowerCase().includes(q) ||
      c.customerName.toLowerCase().includes(q) ||
      c.category.toLowerCase().includes(q)
    );
  }
  if (adminComplaintCategory !== 'ALL') {
    filtered = filtered.filter(c => c.category === adminComplaintCategory);
  }
  if (adminComplaintStatus !== 'ALL') {
    filtered = filtered.filter(c => c.status === adminComplaintStatus);
  }

  if (filtered.length === 0) {
    return `
      <tr>
        <td colspan="10" style="text-align: center; padding: 2.5rem; color: #64748b;">
          No customer complaints match the active filter criteria.
        </td>
      </tr>
    `;
  }

  return filtered.map(c => `
    <tr style="border-bottom: 1px solid #f1f5f9;">
      <td style="padding: 0.85rem 1rem;"><span class="ss-ref-badge">${escapeHtml(c.referenceNumber)}</span></td>
      <td style="padding: 0.85rem 1rem;"><strong>${escapeHtml(c.customerName)}</strong></td>
      <td style="padding: 0.85rem 1rem;"><span class="ss-category-pill">${escapeHtml(c.category)}</span></td>
      <td style="padding: 0.85rem 1rem; max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(c.subject)}">
        ${escapeHtml(c.subject)}
      </td>
      <td style="padding: 0.85rem 1rem;">${escapeHtml(c.storeName || 'N/A')}</td>
      <td style="padding: 0.85rem 1rem;">
        <span class="ss-status-badge status-${(c.status || '').toLowerCase().replace(/_/g, '-')}">
          ${escapeHtml((c.status || '').replace(/_/g, ' '))}
        </span>
      </td>
      <td style="padding: 0.85rem 1rem;">
        <span class="badge ${c.priority === 'CRITICAL' ? 'badge-p1' : (c.priority === 'HIGH' ? 'badge-p2' : 'badge-p3')}">
          ${escapeHtml(c.priority || 'MEDIUM')}
        </span>
      </td>
      <td style="padding: 0.85rem 1rem; font-size: 0.82rem; color: #334155;">
        ${escapeHtml(c.assignedToName || c.assignedTeamName || 'Unassigned')}
      </td>
      <td style="padding: 0.85rem 1rem; font-size: 0.8rem; color: #64748b;">
        ${new Date(c.createdAt).toLocaleDateString()}
      </td>
      <td style="padding: 0.85rem 1rem; text-align: right;">
        <button class="btn btn-secondary btn-sm btn-admin-investigate" data-id="${c.id}">
          🔍 Investigate & Update
        </button>
      </td>
    </tr>
  `).join('');
}

function attachAdminDashboardEvents(container, complaints, stores, users, teams, regions) {
  // Quick Actions
  container.querySelector('#btn-admin-add-store')?.addEventListener('click', () => {
    openAdminCreateStoreModal(regions, () => renderOrgAdminDashboard(container));
  });

  container.querySelector('#btn-admin-provision-mgr')?.addEventListener('click', () => {
    openAdminProvisionManagerModal(stores, () => renderOrgAdminDashboard(container));
  });

  container.querySelector('#btn-admin-preview-customer')?.addEventListener('click', () => {
    state.setPortalMode('CUSTOMER');
    showToast('Switched to Customer Experience Portal View', 'info');
  });

  container.querySelector('#btn-admin-manage-all-stores')?.addEventListener('click', () => {
    state.setView('org-hierarchy');
  });

  // Complaint Filters
  const searchInput = container.querySelector('#admin-filter-complaints-search');
  const catSelect = container.querySelector('#admin-filter-complaints-category');
  const statusSelect = container.querySelector('#admin-filter-complaints-status');
  const tbody = container.querySelector('#tbody-admin-complaints');

  const updateTable = () => {
    adminComplaintSearch = searchInput?.value || '';
    adminComplaintCategory = catSelect?.value || 'ALL';
    adminComplaintStatus = statusSelect?.value || 'ALL';
    if (tbody) {
      tbody.innerHTML = renderAdminComplaintRows(complaints);
      attachInvestigateButtons();
    }
  };

  searchInput?.addEventListener('input', updateTable);
  catSelect?.addEventListener('change', updateTable);
  statusSelect?.addEventListener('change', updateTable);

  const attachInvestigateButtons = () => {
    container.querySelectorAll('.btn-admin-investigate').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const c = complaints.find(x => x.id === id);
        if (c) openAdminInvestigationDrawer(container, c, teams, users, () => renderOrgAdminDashboard(container));
      });
    });
  };
  attachInvestigateButtons();

  // Store Management Actions
  container.querySelectorAll('.btn-assign-mgr-store').forEach(btn => {
    btn.addEventListener('click', () => {
      const storeId = btn.getAttribute('data-id');
      const storeName = btn.getAttribute('data-name');
      openAdminAssignStoreManagerModal(storeId, storeName, users, () => renderOrgAdminDashboard(container));
    });
  });

  container.querySelectorAll('.btn-toggle-store-status').forEach(btn => {
    btn.addEventListener('click', async () => {
      const storeId = btn.getAttribute('data-id');
      const currentStatus = btn.getAttribute('data-status');
      const newStatus = currentStatus === 'DECOMMISSIONED' ? 'OPERATIONAL' : 'DECOMMISSIONED';

      if (!confirm(`Are you sure you want to ${newStatus === 'DECOMMISSIONED' ? 'deactivate' : 'reactivate'} Store #${storeId}?`)) return;

      try {
        await api.updateStoreStatus(storeId, newStatus, 'Status modified via Organization Admin portal.');
        showToast(`Store operating status updated to ${newStatus}`, 'success');
        renderOrgAdminDashboard(container);
      } catch (err) {
        showToast(err.message || 'Error updating store status', 'error');
      }
    });
  });
}

/**
 * Admin Investigation Drawer
 */
function openAdminInvestigationDrawer(container, c, teams, users, onSuccess) {
  const drawer = container.querySelector('#admin-complaint-investigation-drawer');
  if (!drawer) return;

  const storeManagers = users.filter(u => u.role === 'STORE_MANAGER' && u.isActive);

  drawer.style.display = 'block';
  drawer.innerHTML = `
    <div class="rw-drawer-backdrop" id="admin-drawer-backdrop"></div>
    <div class="rw-drawer-panel" style="background: #ffffff; color: #0f172a; border-left: 1px solid #e2e8f0; box-shadow: -10px 0 25px -5px rgba(0,0,0,0.1); width: 480px; max-width: 90vw;">
      <div class="rw-drawer-header" style="border-bottom: 1px solid #e2e8f0; padding: 1.25rem 1.5rem; display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <span class="ss-ref-badge" style="font-size: 0.95rem;">${escapeHtml(c.referenceNumber)}</span>
          <h2 style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-top: 0.25rem;">${escapeHtml(c.subject)}</h2>
        </div>
        <button class="rw-btn-close" id="btn-close-admin-drawer" style="color: #64748b;">✕</button>
      </div>

      <div class="rw-drawer-body" style="padding: 1.5rem; overflow-y: auto;">
        <!-- Original Customer Report -->
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;">
          <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; margin-bottom: 0.25rem; font-weight: 600;">Original Customer Report</div>
          <div style="font-size: 0.88rem; color: #0f172a; line-height: 1.5; white-space: pre-wrap;">${escapeHtml(c.description)}</div>
          
          <div style="margin-top: 0.75rem; font-size: 0.8rem; color: #475569; display: flex; gap: 1rem; flex-wrap: wrap;">
            <span>👤 ${escapeHtml(c.customerName)}</span>
            <span>✉️ ${escapeHtml(c.customerEmail || 'Confidential')}</span>
            <span>🏢 ${escapeHtml(c.storeName || 'N/A')}</span>
          </div>

          ${c.attachmentName ? `
            <div style="margin-top: 0.75rem; font-size: 0.82rem; color: #2563eb;">
              📎 Customer Attached Evidence: <strong>${escapeHtml(c.attachmentName)}</strong>
            </div>
          ` : ''}
        </div>

        <form id="form-admin-investigate-update">
          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label" for="admin-update-status" style="font-size: 0.85rem; font-weight: 600;">Operational Status Transition</label>
            <select id="admin-update-status" class="form-input">
              <option value="SUBMITTED" ${c.status === 'SUBMITTED' ? 'selected' : ''}>SUBMITTED — In queue</option>
              <option value="UNDER_REVIEW" ${c.status === 'UNDER_REVIEW' ? 'selected' : ''}>UNDER_REVIEW — Reviewing evidence</option>
              <option value="IN_PROGRESS" ${c.status === 'IN_PROGRESS' ? 'selected' : ''}>IN_PROGRESS — Field team active</option>
              <option value="RESOLVED" ${c.status === 'RESOLVED' ? 'selected' : ''}>RESOLVED — Remediation complete</option>
              <option value="CLOSED" ${c.status === 'CLOSED' ? 'selected' : ''}>CLOSED — Audited & archived</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label" for="admin-update-mgr" style="font-size: 0.85rem; font-weight: 600;">Assign Responsible Store Manager</label>
            <select id="admin-update-mgr" class="form-input">
              <option value="">-- Leave Unassigned --</option>
              ${storeManagers.map(m => `
                <option value="${m.id}" ${m.id === c.assignedToUserId ? 'selected' : ''}>${escapeHtml(m.fullName)} (${escapeHtml(m.email)})</option>
              `).join('')}
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label" for="admin-update-team" style="font-size: 0.85rem; font-weight: 600;">Assign Specialized Response Team</label>
            <select id="admin-update-team" class="form-input">
              <option value="">-- Leave Unassigned --</option>
              ${teams.map(t => `
                <option value="${t.id}" ${t.id === c.assignedTeamId ? 'selected' : ''}>${escapeHtml(t.name)}</option>
              `).join('')}
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label" for="admin-internal-notes" style="font-size: 0.85rem; font-weight: 600;">Internal Staff Notes (Restricted)</label>
            <textarea id="admin-internal-notes" class="form-input rw-textarea" rows="3" placeholder="Enter internal investigation findings or technician dispatch notes...">${escapeHtml(c.investigationNotes || '')}</textarea>
            <div class="form-help-text">Internal notes are strictly restricted from customer tracking views.</div>
          </div>

          <div class="form-group" style="margin-bottom: 1.5rem;">
            <label class="form-label" for="admin-resolution-summary" style="font-size: 0.85rem; font-weight: 600;">Customer-Facing Resolution Note (Published)</label>
            <textarea id="admin-resolution-summary" class="form-input rw-textarea" rows="3" placeholder="Explain the verified resolution or corrective action published to the customer...">${escapeHtml(c.resolutionSummary || '')}</textarea>
            <div class="form-help-text">This note is published directly to the customer's chronological status timeline.</div>
          </div>

          <div style="display: flex; gap: 0.75rem;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-admin-drawer" style="flex: 1;">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-save-admin-investigation" style="flex: 2;">
              Save Operational Updates
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeDrawer = () => { drawer.style.display = 'none'; };
  drawer.querySelector('#btn-close-admin-drawer')?.addEventListener('click', closeDrawer);
  drawer.querySelector('#btn-cancel-admin-drawer')?.addEventListener('click', closeDrawer);
  drawer.querySelector('#admin-drawer-backdrop')?.addEventListener('click', closeDrawer);

  drawer.querySelector('#form-admin-investigate-update')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = drawer.querySelector('#btn-save-admin-investigation');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Saving...';

    const status = drawer.querySelector('#admin-update-status').value;
    const assignedTeamId = drawer.querySelector('#admin-update-team').value || null;
    const assignedToUserId = drawer.querySelector('#admin-update-mgr').value || null;
    const investigationNotes = drawer.querySelector('#admin-internal-notes').value.trim() || null;
    const resolutionSummary = drawer.querySelector('#admin-resolution-summary').value.trim() || null;

    try {
      await api.updateComplaintStatus(c.id, {
        status,
        assignedTeamId,
        assignedToUserId,
        investigationNotes,
        resolutionSummary
      });

      showToast('Operational updates saved and persisted to database.', 'success');
      closeDrawer();
      if (onSuccess) onSuccess();
    } catch (err) {
      showToast(err.message || 'Error updating complaint', 'error');
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Save Operational Updates';
    }
  });
}

/**
 * Modal: Add Retail Store Facility
 */
function openAdminCreateStoreModal(regions, onSuccess) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="create-store-backdrop">
      <div class="rw-modal" style="max-width: 520px; background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
        <div class="rw-modal-header" style="border-bottom: 1px solid #e2e8f0; padding: 1.25rem 1.5rem;">
          <div>
            <h2 style="font-size: 1.2rem; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0;">Add Retail Store Facility</h2>
            <div style="font-size: 0.8rem; color: #64748b;">Register a new store into the Apex Retail enterprise hierarchy</div>
          </div>
          <button class="rw-btn-close" id="btn-close-store-modal" style="color: #64748b;">✕</button>
        </div>

        <form id="form-admin-create-store" style="padding: 1.5rem;">
          <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 0.75rem; margin-bottom: 1rem;">
            <div class="form-group">
              <label class="form-label required">Store Number</label>
              <input type="number" id="as-number" class="form-input" required placeholder="e.g. 108" min="100" max="999" />
            </div>
            <div class="form-group">
              <label class="form-label required">Store Facility Name</label>
              <input type="text" id="as-name" class="form-input" required placeholder="e.g. Apex Hypercenter - Portland" />
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem;">
            <div class="form-group">
              <label class="form-label required">Operating Status</label>
              <select id="as-status" class="form-input">
                <option value="OPERATIONAL">OPERATIONAL</option>
                <option value="MAINTENANCE_HOLD">MAINTENANCE_HOLD</option>
                <option value="RENOVATION">RENOVATION</option>
                <option value="TEMPORARILY_CLOSED">TEMPORARILY_CLOSED</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label required">Format Tier</label>
              <select id="as-format" class="form-input">
                <option value="SUPERCENTER">Supercenter</option>
                <option value="HYPERMARKET">Hypermarket</option>
                <option value="EXPRESS">Express</option>
                <option value="FLAGSHIP">Flagship</option>
              </select>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1.5rem;">
            <div class="form-group">
              <label class="form-label">Contact Phone</label>
              <input type="tel" id="as-phone" class="form-input" placeholder="+1-555-018-9922" />
            </div>
            <div class="form-group">
              <label class="form-label">Operating Hours</label>
              <input type="text" id="as-hours" class="form-input" value="06:00 - 23:00" />
            </div>
          </div>

          <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-store-modal">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-create-store">
              Create Store Facility
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-store-modal')?.addEventListener('click', closeModal);
  modalContainer.querySelector('#btn-cancel-store-modal')?.addEventListener('click', closeModal);
  modalContainer.querySelector('#create-store-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'create-store-backdrop') closeModal();
  });

  modalContainer.querySelector('#form-admin-create-store')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = modalContainer.querySelector('#btn-submit-create-store');
    btn.disabled = true;
    btn.textContent = 'Creating Store...';

    const storeNumber = modalContainer.querySelector('#as-number').value.trim();
    const name = modalContainer.querySelector('#as-name').value.trim();
    const operatingStatus = modalContainer.querySelector('#as-status').value;
    const formatTier = modalContainer.querySelector('#as-format').value;
    const contactPhone = modalContainer.querySelector('#as-phone').value.trim();
    const openingHours = modalContainer.querySelector('#as-hours').value.trim();

    try {
      await api.createStore({
        storeNumber,
        name,
        operatingStatus,
        organizationId: state.selectedOrgId || 'org-apex-01',
        regionId: 'reg-pnw-01',
        metadata: {
          formatTier,
          contactPhone,
          openingHours,
          squareFootage: 120000
        }
      });

      showToast(`Store #${storeNumber} (${name}) registered successfully!`, 'success');
      closeModal();
      if (onSuccess) onSuccess();
    } catch (err) {
      showToast(err.message || 'Error creating store', 'error');
      btn.disabled = false;
      btn.textContent = 'Create Store Facility';
    }
  });
}

/**
 * Modal: Provision Store Manager
 */
function openAdminProvisionManagerModal(stores, onSuccess) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="provision-mgr-backdrop">
      <div class="rw-modal" style="max-width: 500px; background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
        <div class="rw-modal-header" style="border-bottom: 1px solid #e2e8f0; padding: 1.25rem 1.5rem;">
          <div>
            <h2 style="font-size: 1.2rem; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0;">+ Provision Store Manager</h2>
            <div style="font-size: 0.8rem; color: #64748b;">Create an authorized Store Manager account and scope their facility</div>
          </div>
          <button class="rw-btn-close" id="btn-close-mgr-modal" style="color: #64748b;">✕</button>
        </div>

        <form id="form-admin-provision-mgr" style="padding: 1.5rem;">
          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label required">Manager Full Name</label>
            <input type="text" id="pm-name" class="form-input" required placeholder="e.g. Rachel Sterling" />
          </div>

          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label required">Corporate Email Address</label>
            <input type="email" id="pm-email" class="form-input" required placeholder="rachel.sterling@apex.com" />
          </div>

          <div class="form-group" style="margin-bottom: 1rem;">
            <label class="form-label required">Initial Password (Min 8 characters)</label>
            <input type="password" id="pm-password" class="form-input" required value="Password123!" minlength="8" />
          </div>

          <div class="form-group" style="margin-bottom: 1.5rem;">
            <label class="form-label required">Assign to Retail Store</label>
            <select id="pm-store" class="form-input" required>
              ${stores.map(s => `
                <option value="${s.id}">#${s.storeNumber} &mdash; ${escapeHtml(s.name)}</option>
              `).join('')}
            </select>
          </div>

          <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-mgr-modal">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-provision-mgr">
              Provision Manager
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-mgr-modal')?.addEventListener('click', closeModal);
  modalContainer.querySelector('#btn-cancel-mgr-modal')?.addEventListener('click', closeModal);
  modalContainer.querySelector('#provision-mgr-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'provision-mgr-backdrop') closeModal();
  });

  modalContainer.querySelector('#form-admin-provision-mgr')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = modalContainer.querySelector('#btn-submit-provision-mgr');
    btn.disabled = true;
    btn.textContent = 'Provisioning...';

    const fullName = modalContainer.querySelector('#pm-name').value.trim();
    const email = modalContainer.querySelector('#pm-email').value.trim();
    const password = modalContainer.querySelector('#pm-password').value;
    const storeId = modalContainer.querySelector('#pm-store').value;

    try {
      await api.createUser({
        fullName,
        email,
        password,
        role: 'STORE_MANAGER',
        storeId,
        organizationId: state.selectedOrgId || 'org-apex-01',
        regionId: 'reg-pnw-01'
      });

      showToast(`Store Manager ${fullName} provisioned successfully!`, 'success');
      closeModal();
      if (onSuccess) onSuccess();
    } catch (err) {
      showToast(err.message || 'Error provisioning manager', 'error');
      btn.disabled = false;
      btn.textContent = 'Provision Manager';
    }
  });
}

/**
 * Modal: Assign Store Manager to Store
 */
function openAdminAssignStoreManagerModal(storeId, storeName, users, onSuccess) {
  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) return;

  const storeManagers = users.filter(u => u.role === 'STORE_MANAGER');

  modalContainer.innerHTML = `
    <div class="rw-modal-backdrop" id="assign-mgr-backdrop">
      <div class="rw-modal" style="max-width: 460px; background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
        <div class="rw-modal-header" style="border-bottom: 1px solid #e2e8f0; padding: 1.25rem 1.5rem;">
          <div>
            <h2 style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0;">Assign Store Manager</h2>
            <div style="font-size: 0.8rem; color: #64748b;">Facility: ${escapeHtml(storeName)}</div>
          </div>
          <button class="rw-btn-close" id="btn-close-assign-modal" style="color: #64748b;">✕</button>
        </div>

        <form id="form-admin-assign-mgr" style="padding: 1.5rem;">
          <div class="form-group" style="margin-bottom: 1.5rem;">
            <label class="form-label required">Select Store Manager</label>
            <select id="am-mgr-select" class="form-input" required>
              <option value="">-- Choose Manager --</option>
              ${storeManagers.map(m => `
                <option value="${m.id}">${escapeHtml(m.fullName)} (${escapeHtml(m.email)})</option>
              `).join('')}
            </select>
          </div>

          <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-assign-modal">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-assign-mgr">
              Assign to Facility
            </button>
          </div>
        </form>
      </div>
    </div>
  `;

  const closeModal = () => { modalContainer.innerHTML = ''; };
  modalContainer.querySelector('#btn-close-assign-modal')?.addEventListener('click', closeModal);
  modalContainer.querySelector('#btn-cancel-assign-modal')?.addEventListener('click', closeModal);
  modalContainer.querySelector('#assign-mgr-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'assign-mgr-backdrop') closeModal();
  });

  modalContainer.querySelector('#form-admin-assign-mgr')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const mgrId = modalContainer.querySelector('#am-mgr-select').value;
    if (!mgrId) return;

    const btn = modalContainer.querySelector('#btn-submit-assign-mgr');
    btn.disabled = true;
    btn.textContent = 'Saving Assignment...';

    try {
      await api.updateUser(mgrId, { storeId });
      showToast('Store Manager assigned to facility successfully!', 'success');
      closeModal();
      if (onSuccess) onSuccess();
    } catch (err) {
      showToast(err.message || 'Error assigning manager', 'error');
      btn.disabled = false;
      btn.textContent = 'Assign to Facility';
    }
  });
}
