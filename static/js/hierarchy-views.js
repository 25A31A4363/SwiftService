/**
 * R5 Operational Intelligence Platform - Organization & Operational Context Layer Views
 * Phase 2 Implementation: Complete CRUD, Relationships, Metadata, Operating Status,
 * Team Responsibilities, Specializations, Escalation Ownership, and Lineage Tracing.
 */

import { state } from './state.js';
import { api, showToast } from './api.js';

// Modal Helpers
function openModal(contentHtml) {
  const el = document.getElementById('modal-container');
  if (el) {
    el.innerHTML = `
      <div class="modal-backdrop">
        <div class="modal-content">
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

export function renderOperatingStatusBadge(status) {
  const norm = (status || 'OPERATIONAL').toLowerCase();
  const label = (status || 'OPERATIONAL').replace(/_/g, ' ');
  return `<span class="badge status-${norm}">${label}</span>`;
}

/* =========================================================================
   VIEW 1: ORGANIZATION & STORE HIERARCHY
   ========================================================================= */
let currentHierarchyTab = 'stores'; // 'stores' | 'regions' | 'organizations'
let storeFilterStatus = '';
let storeSearchQuery = '';
let regionSearchQuery = '';
let orgSearchQuery = '';

export async function renderOrgHierarchyView(container) {
  container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">Loading organization hierarchy...</div>`;

  try {
    const [orgs, regions, stores] = await Promise.all([
      api.getOrganizations(orgSearchQuery || undefined),
      api.getRegions(state.selectedOrgId, regionSearchQuery || undefined),
      api.getStores(state.selectedOrgId, state.selectedRegionId, storeFilterStatus || undefined, storeSearchQuery || undefined)
    ]);

    container.innerHTML = `
      <!-- Synthetic Demo Data Disclaimer Banner -->
      <div class="demo-seed-banner">
        <span style="font-weight: 700; color: #f59e0b;">DEMO / SEED DATA</span> &mdash;
        The enterprise hierarchy, regions, and store facilities below represent synthetic demonstration fixtures for operational evaluation and do NOT represent real-world statistics.
      </div>

      <!-- Navigation Tabs -->
      <div class="tabs-nav">
        <button class="tab-btn ${currentHierarchyTab === 'stores' ? 'active' : ''}" data-tab="stores">🏪 Stores (${stores.length})</button>
        <button class="tab-btn ${currentHierarchyTab === 'regions' ? 'active' : ''}" data-tab="regions">🌐 Regions (${regions.length})</button>
        <button class="tab-btn ${currentHierarchyTab === 'organizations' ? 'active' : ''}" data-tab="organizations">🏢 Organizations (${orgs.length})</button>
      </div>

      <!-- Active Tab Content Area -->
      <div id="hierarchy-tab-content">
        ${currentHierarchyTab === 'stores' ? renderStoresTab(stores, regions) : ''}
        ${currentHierarchyTab === 'regions' ? renderRegionsTab(regions, orgs) : ''}
        ${currentHierarchyTab === 'organizations' ? renderOrganizationsTab(orgs) : ''}
      </div>
    `;

    // Attach Tab Switching
    container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        currentHierarchyTab = btn.getAttribute('data-tab');
        renderOrgHierarchyView(container);
      });
    });

    // Attach Store Tab Event Handlers
    if (currentHierarchyTab === 'stores') {
      attachStoresEvents(container);
    } else if (currentHierarchyTab === 'regions') {
      attachRegionsEvents(container);
    } else if (currentHierarchyTab === 'organizations') {
      attachOrganizationsEvents(container);
    }

  } catch (err) {
    container.innerHTML = `<div class="r5-card"><div class="r5-card-body">${err.message}</div></div>`;
  }
}

function renderStoresTab(stores, regions) {
  return `
    <div class="r5-card">
      <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
        <div class="r5-card-title">
          <span>🏪</span>
          <span>Retail Store Facilities & Operating Status</span>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
          <input type="text" id="store-search-input" class="form-input" style="padding: 0.4rem 0.75rem; font-size: 0.82rem; width: 180px;" placeholder="Search store name/number..." value="${storeSearchQuery}" />
          <select id="store-status-filter" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
            <option value="">All Operating Statuses</option>
            <option value="OPERATIONAL" ${storeFilterStatus === 'OPERATIONAL' ? 'selected' : ''}>Operational</option>
            <option value="MAINTENANCE_HOLD" ${storeFilterStatus === 'MAINTENANCE_HOLD' ? 'selected' : ''}>Maintenance Hold</option>
            <option value="RENOVATION" ${storeFilterStatus === 'RENOVATION' ? 'selected' : ''}>Renovation</option>
            <option value="TEMPORARILY_CLOSED" ${storeFilterStatus === 'TEMPORARILY_CLOSED' ? 'selected' : ''}>Temporarily Closed</option>
            <option value="DECOMMISSIONED" ${storeFilterStatus === 'DECOMMISSIONED' ? 'selected' : ''}>Decommissioned</option>
          </select>
          <button id="btn-create-store" class="btn btn-primary btn-sm">+ Add Store</button>
        </div>
      </div>
      <div class="r5-table-container">
        <table class="r5-table">
          <thead>
            <tr>
              <th>Store</th>
              <th>Region</th>
              <th>Format & Size</th>
              <th>Operating Status</th>
              <th>Contact & Hours</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${stores.length === 0 ? `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No retail stores found matching filters.</td></tr>` : ''}
            ${stores.map(store => {
              const meta = store.metadata || {};
              const region = regions.find(r => r.id === store.regionId);
              return `
                <tr>
                  <td>
                    <div style="font-weight: 700; color: #fff;">#${store.storeNumber} &mdash; ${store.name}</div>
                    <div class="table-id-mono" style="font-size: 0.7rem; color: var(--text-muted);">${store.id.slice(0, 8)}...</div>
                  </td>
                  <td>
                    <span class="badge badge-neutral">${region ? region.name : 'Unassigned'}</span>
                  </td>
                  <td>
                    <div style="font-weight: 600; color: var(--accent-cyan); font-size: 0.8rem;">${meta.formatTier || 'SUPERCENTER'}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${meta.squareFootage ? meta.squareFootage.toLocaleString() + ' sq ft' : '—'}</div>
                  </td>
                  <td>
                    ${renderOperatingStatusBadge(store.operatingStatus)}
                  </td>
                  <td>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">${meta.contactPhone || '—'}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">${meta.openingHours || '06:00 - 23:00'}</div>
                  </td>
                  <td style="text-align: right;">
                    <div style="display: inline-flex; gap: 0.35rem;">
                      <button class="btn btn-secondary btn-sm btn-store-status" data-id="${store.id}" title="Change Operating Status">⚡ Status</button>
                      <button class="btn btn-secondary btn-sm btn-store-meta" data-id="${store.id}" title="View/Edit Metadata">⚙️ Meta</button>
                      <button class="btn btn-secondary btn-sm btn-store-edit" data-id="${store.id}" title="Edit Store Details">Edit</button>
                      <button class="btn btn-primary btn-sm btn-store-trace" data-id="${store.id}" title="Trace Lineage">Trace</button>
                      <button class="btn btn-danger btn-sm btn-store-delete" data-id="${store.id}" title="Delete Store">✕</button>
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
}

function renderRegionsTab(regions, orgs) {
  return `
    <div class="r5-card">
      <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
        <div class="r5-card-title">
          <span>🌐</span>
          <span>Operational Regions & Regional Leadership</span>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <input type="text" id="region-search-input" class="form-input" style="padding: 0.4rem 0.75rem; font-size: 0.82rem; width: 200px;" placeholder="Search region name/code..." value="${regionSearchQuery}" />
          <button id="btn-create-region" class="btn btn-primary btn-sm">+ Add Region</button>
        </div>
      </div>
      <div class="r5-table-container">
        <table class="r5-table">
          <thead>
            <tr>
              <th>Region Code</th>
              <th>Region Name</th>
              <th>Organization</th>
              <th>Regional Lead</th>
              <th>Description</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${regions.length === 0 ? `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No operational regions found.</td></tr>` : ''}
            ${regions.map(reg => {
              const org = orgs.find(o => o.id === reg.organizationId);
              return `
                <tr>
                  <td><span class="badge badge-p4" style="font-family: var(--font-family-mono);">${reg.code}</span></td>
                  <td><div style="font-weight: 700; color: #fff;">${reg.name}</div></td>
                  <td>${org ? org.name : '—'}</td>
                  <td>
                    <div style="font-weight: 600; color: var(--accent-cyan);">${reg.leadUserName || 'Regional VP (PNW)'}</div>
                  </td>
                  <td style="font-size: 0.82rem; color: var(--text-secondary); max-width: 250px;">${reg.description || '—'}</td>
                  <td style="text-align: right;">
                    <button class="btn btn-secondary btn-sm btn-region-edit" data-id="${reg.id}">Edit</button>
                    <button class="btn btn-danger btn-sm btn-region-delete" data-id="${reg.id}">✕</button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderOrganizationsTab(orgs) {
  return `
    <div class="r5-card">
      <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
        <div class="r5-card-title">
          <span>🏢</span>
          <span>Enterprise Organizations</span>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <input type="text" id="org-search-input" class="form-input" style="padding: 0.4rem 0.75rem; font-size: 0.82rem; width: 200px;" placeholder="Search organization..." value="${orgSearchQuery}" />
          <button id="btn-create-org" class="btn btn-primary btn-sm">+ Add Organization</button>
        </div>
      </div>
      <div class="r5-table-container">
        <table class="r5-table">
          <thead>
            <tr>
              <th>Org Code</th>
              <th>Organization Name</th>
              <th>Status</th>
              <th>Description</th>
              <th>Created</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${orgs.length === 0 ? `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No organizations found.</td></tr>` : ''}
            ${orgs.map(org => `
              <tr>
                <td><span class="badge badge-neutral" style="font-family: var(--font-family-mono);">${org.code}</span></td>
                <td><div style="font-weight: 700; color: #fff;">${org.name}</div></td>
                <td><span class="badge ${org.status === 'ACTIVE' ? 'status-operational' : 'status-decommissioned'}">${org.status || 'ACTIVE'}</span></td>
                <td style="font-size: 0.82rem; color: var(--text-secondary);">${org.description || '—'}</td>
                <td class="table-id-mono">${new Date(org.createdAt).toLocaleDateString()}</td>
                <td style="text-align: right;">
                  <button class="btn btn-secondary btn-sm btn-org-edit" data-id="${org.id}">Edit</button>
                  <button class="btn btn-danger btn-sm btn-org-delete" data-id="${org.id}">✕</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function attachStoresEvents(container) {
  const searchInput = container.querySelector('#store-search-input');
  if (searchInput) {
    searchInput.addEventListener('change', (e) => {
      storeSearchQuery = e.target.value.trim();
      renderOrgHierarchyView(container);
    });
  }

  const statusFilter = container.querySelector('#store-status-filter');
  if (statusFilter) {
    statusFilter.addEventListener('change', (e) => {
      storeFilterStatus = e.target.value;
      renderOrgHierarchyView(container);
    });
  }

  container.querySelector('#btn-create-store')?.addEventListener('click', () => {
    openCreateStoreModal(() => renderOrgHierarchyView(container));
  });

  container.querySelectorAll('.btn-store-status').forEach(btn => {
    btn.addEventListener('click', () => {
      openStoreStatusModal(btn.getAttribute('data-id'), () => renderOrgHierarchyView(container));
    });
  });

  container.querySelectorAll('.btn-store-meta').forEach(btn => {
    btn.addEventListener('click', () => {
      openStoreMetadataModal(btn.getAttribute('data-id'), () => renderOrgHierarchyView(container));
    });
  });

  container.querySelectorAll('.btn-store-edit').forEach(btn => {
    btn.addEventListener('click', () => {
      openEditStoreModal(btn.getAttribute('data-id'), () => renderOrgHierarchyView(container));
    });
  });

  container.querySelectorAll('.btn-store-trace').forEach(btn => {
    btn.addEventListener('click', () => {
      state.selectedStoreId = btn.getAttribute('data-id');
      state.setView('ownership');
    });
  });

  container.querySelectorAll('.btn-store-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (!confirm('Are you sure you want to delete this store? This will audit log the deletion.')) return;
      try {
        await api.deleteStore(id);
        showToast('Store successfully deleted and audited.', 'success');
        renderOrgHierarchyView(container);
      } catch (err) {}
    });
  });
}

function attachRegionsEvents(container) {
  const searchInput = container.querySelector('#region-search-input');
  if (searchInput) {
    searchInput.addEventListener('change', (e) => {
      regionSearchQuery = e.target.value.trim();
      renderOrgHierarchyView(container);
    });
  }

  container.querySelector('#btn-create-region')?.addEventListener('click', () => {
    openCreateRegionModal(() => renderOrgHierarchyView(container));
  });

  container.querySelectorAll('.btn-region-edit').forEach(btn => {
    btn.addEventListener('click', () => {
      openEditRegionModal(btn.getAttribute('data-id'), () => renderOrgHierarchyView(container));
    });
  });

  container.querySelectorAll('.btn-region-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (!confirm('Are you sure you want to delete this operational region?')) return;
      try {
        await api.deleteRegion(id);
        showToast('Region successfully deleted.', 'success');
        renderOrgHierarchyView(container);
      } catch (err) {}
    });
  });
}

function attachOrganizationsEvents(container) {
  const searchInput = container.querySelector('#org-search-input');
  if (searchInput) {
    searchInput.addEventListener('change', (e) => {
      orgSearchQuery = e.target.value.trim();
      renderOrgHierarchyView(container);
    });
  }

  container.querySelector('#btn-create-org')?.addEventListener('click', () => {
    openCreateOrgModal(() => renderOrgHierarchyView(container));
  });

  container.querySelectorAll('.btn-org-edit').forEach(btn => {
    btn.addEventListener('click', () => {
      openEditOrgModal(btn.getAttribute('data-id'), () => renderOrgHierarchyView(container));
    });
  });

  container.querySelectorAll('.btn-org-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (!confirm('Are you sure you want to delete this organization? Cascade rules apply.')) return;
      try {
        await api.deleteOrganization(id);
        showToast('Organization deleted.', 'success');
        renderOrgHierarchyView(container);
      } catch (err) {}
    });
  });
}

/* =========================================================================
   VIEW 2: OPERATIONAL TEAMS & SPECIALIZATIONS
   ========================================================================= */
let teamFilterSpec = '';
let teamSearchQuery = '';

export async function renderTeamsView(container) {
  container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">Loading operational teams...</div>`;

  try {
    const teams = await api.getTeams(state.selectedStoreId, state.selectedRegionId, teamFilterSpec || undefined, teamSearchQuery || undefined);

    container.innerHTML = `
      <!-- Synthetic Demo Data Disclaimer Banner -->
      <div class="demo-seed-banner">
        <span style="font-weight: 700; color: #f59e0b;">DEMO / SEED DATA</span> &mdash;
        Operational squads, specializations, and escalation contacts are synthetic demonstration fixtures.
      </div>

      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>👥</span>
            <span>Operational Teams, Responsibilities & Specialization</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <input type="text" id="team-search-input" class="form-input" style="padding: 0.4rem 0.75rem; font-size: 0.82rem; width: 180px;" placeholder="Search squad/code..." value="${teamSearchQuery}" />
            <select id="team-spec-filter" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
              <option value="">All Specializations</option>
              <option value="HVAC_REFRIGERATION" ${teamFilterSpec === 'HVAC_REFRIGERATION' ? 'selected' : ''}>HVAC & Refrigeration</option>
              <option value="ELECTRICAL" ${teamFilterSpec === 'ELECTRICAL' ? 'selected' : ''}>Electrical Systems</option>
              <option value="PLUMBING" ${teamFilterSpec === 'PLUMBING' ? 'selected' : ''}>Plumbing & Drainage</option>
              <option value="FOOD_SAFETY" ${teamFilterSpec === 'FOOD_SAFETY' ? 'selected' : ''}>Food Safety & Sanitation</option>
              <option value="LOSS_PREVENTION" ${teamFilterSpec === 'LOSS_PREVENTION' ? 'selected' : ''}>Loss Prevention</option>
              <option value="IT_POINT_OF_SALE" ${teamFilterSpec === 'IT_POINT_OF_SALE' ? 'selected' : ''}>Point of Sale & IT</option>
              <option value="GENERAL_MAINTENANCE" ${teamFilterSpec === 'GENERAL_MAINTENANCE' ? 'selected' : ''}>General Maintenance</option>
            </select>
            <button id="btn-create-team" class="btn btn-primary btn-sm">+ Add Operational Team</button>
          </div>
        </div>
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Team Name & Code</th>
                <th>Specialization</th>
                <th>Responsibility</th>
                <th>Scope Assignment</th>
                <th>Escalation Tier & Contact</th>
                <th>Lead & Members</th>
                <th>Status</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${teams.length === 0 ? `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No operational teams found matching filters.</td></tr>` : ''}
              ${teams.map(team => `
                <tr>
                  <td>
                    <div style="font-weight: 700; color: #fff;">${team.name}</div>
                    <div class="table-id-mono" style="font-size: 0.72rem; color: var(--text-muted);">${team.teamCode}</div>
                  </td>
                  <td>
                    <span class="badge badge-p4">${(team.specialization || 'GENERAL').replace(/_/g, ' ')}</span>
                  </td>
                  <td>
                    <span class="badge badge-neutral">${(team.responsibility || 'STORE_LEVEL').replace(/_/g, ' ')}</span>
                  </td>
                  <td>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">
                      ${team.storeName ? `Store: <strong>${team.storeName}</strong>` : team.regionName ? `Region: <strong>${team.regionName}</strong>` : 'Enterprise'}
                    </div>
                  </td>
                  <td>
                    <div style="font-weight: 600; color: var(--accent-cyan); font-size: 0.8rem;">${team.escalationTier || 'TIER_1'}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">${team.escalationContact || 'N/A'}</div>
                  </td>
                  <td>
                    <div style="font-size: 0.82rem; font-weight: 600; color: #fff;">${team.leadUserName || 'Unassigned Lead'}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">${team.memberCount || 0} active members</div>
                  </td>
                  <td>
                    <span class="badge ${team.status === 'ACTIVE' ? 'status-operational' : 'status-decommissioned'}">${team.status || 'ACTIVE'}</span>
                  </td>
                  <td style="text-align: right;">
                    <div style="display: inline-flex; gap: 0.35rem;">
                      <button class="btn btn-secondary btn-sm btn-team-members" data-id="${team.id}">👥 Members (${team.memberCount || 0})</button>
                      <button class="btn btn-secondary btn-sm btn-team-edit" data-id="${team.id}">Edit</button>
                      <button class="btn btn-danger btn-sm btn-team-delete" data-id="${team.id}">✕</button>
                    </div>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Events
    container.querySelector('#team-search-input')?.addEventListener('change', (e) => {
      teamSearchQuery = e.target.value.trim();
      renderTeamsView(container);
    });

    container.querySelector('#team-spec-filter')?.addEventListener('change', (e) => {
      teamFilterSpec = e.target.value;
      renderTeamsView(container);
    });

    container.querySelector('#btn-create-team')?.addEventListener('click', () => {
      openCreateTeamModal(() => renderTeamsView(container));
    });

    container.querySelectorAll('.btn-team-members').forEach(btn => {
      btn.addEventListener('click', () => {
        openTeamMembersModal(btn.getAttribute('data-id'), () => renderTeamsView(container));
      });
    });

    container.querySelectorAll('.btn-team-edit').forEach(btn => {
      btn.addEventListener('click', () => {
        openEditTeamModal(btn.getAttribute('data-id'), () => renderTeamsView(container));
      });
    });

    container.querySelectorAll('.btn-team-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        if (!confirm('Are you sure you want to delete this operational team?')) return;
        try {
          await api.deleteTeam(id);
          showToast('Operational team removed.', 'success');
          renderTeamsView(container);
        } catch (err) {}
      });
    });

  } catch (err) {
    container.innerHTML = `<div class="r5-card"><div class="r5-card-body">${err.message}</div></div>`;
  }
}

/* =========================================================================
   VIEW 3: USER DIRECTORY & ROLES
   ========================================================================= */
let userFilterRole = '';
let userFilterStore = '';
let userSearchQuery = '';

export async function renderUsersView(container) {
  container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">Loading user directory...</div>`;

  try {
    const [users, stores] = await Promise.all([
      api.getUsers(userFilterRole || undefined, userFilterStore || undefined, userSearchQuery || undefined),
      api.getStores()
    ]);

    container.innerHTML = `
      <!-- Synthetic Demo Data Disclaimer Banner -->
      <div class="demo-seed-banner">
        <span style="font-weight: 700; color: #f59e0b;">DEMO / SEED DATA</span> &mdash;
        User profiles and credentials shown below are demonstration entities with simulated permissions.
      </div>

      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>👤</span>
            <span>Enterprise User Directory & Operational Scoping</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <input type="text" id="user-search-input" class="form-input" style="padding: 0.4rem 0.75rem; font-size: 0.82rem; width: 180px;" placeholder="Search name/email..." value="${userSearchQuery}" />
            <select id="user-role-filter" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
              <option value="">All Roles</option>
              <option value="ORGANIZATION_ADMIN" ${userFilterRole === 'ORGANIZATION_ADMIN' ? 'selected' : ''}>Org Admin</option>
              <option value="OPERATIONS_MANAGER" ${userFilterRole === 'OPERATIONS_MANAGER' ? 'selected' : ''}>Operations Manager</option>
              <option value="REGIONAL_MANAGER" ${userFilterRole === 'REGIONAL_MANAGER' ? 'selected' : ''}>Regional VP</option>
              <option value="STORE_MANAGER" ${userFilterRole === 'STORE_MANAGER' ? 'selected' : ''}>Store Manager</option>
              <option value="MAINTENANCE_TEAM" ${userFilterRole === 'MAINTENANCE_TEAM' ? 'selected' : ''}>Maintenance Tech</option>
              <option value="ANALYST" ${userFilterRole === 'ANALYST' ? 'selected' : ''}>Analyst</option>
              <option value="VIEWER" ${userFilterRole === 'VIEWER' ? 'selected' : ''}>Viewer</option>
            </select>
            <button id="btn-create-user" class="btn btn-primary btn-sm">+ Add User</button>
          </div>
        </div>
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>User / Operator</th>
                <th>Role</th>
                <th>Region & Store</th>
                <th>Assigned Squad</th>
                <th>Status</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${users.length === 0 ? `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No users found matching query.</td></tr>` : ''}
              ${users.map(u => `
                <tr>
                  <td>
                    <div style="font-weight: 700; color: #fff;">${u.fullName}</div>
                    <div style="font-size: 0.78rem; color: var(--text-secondary);">${u.email}</div>
                  </td>
                  <td>
                    <span class="badge badge-p4">${u.role.replace(/_/g, ' ')}</span>
                  </td>
                  <td>
                    <div style="font-size: 0.82rem; color: #fff;">${u.storeName ? `Store: ${u.storeName}` : 'All Stores'}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">${u.regionName || 'Enterprise'}</div>
                  </td>
                  <td>
                    <span class="badge badge-neutral">${u.teamName || 'Unassigned'}</span>
                  </td>
                  <td>
                    <span class="badge ${u.isActive ? 'status-operational' : 'status-decommissioned'}">${u.isActive ? 'ACTIVE' : 'INACTIVE'}</span>
                  </td>
                  <td style="text-align: right;">
                    <button class="btn btn-secondary btn-sm btn-user-edit" data-id="${u.id}">Edit</button>
                    <button class="btn btn-danger btn-sm btn-user-delete" data-id="${u.id}">✕</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Events
    container.querySelector('#user-search-input')?.addEventListener('change', (e) => {
      userSearchQuery = e.target.value.trim();
      renderUsersView(container);
    });

    container.querySelector('#user-role-filter')?.addEventListener('change', (e) => {
      userFilterRole = e.target.value;
      renderUsersView(container);
    });

    container.querySelector('#btn-create-user')?.addEventListener('click', () => {
      openCreateUserModal(() => renderUsersView(container));
    });

    container.querySelectorAll('.btn-user-edit').forEach(btn => {
      btn.addEventListener('click', () => {
        openEditUserModal(btn.getAttribute('data-id'), () => renderUsersView(container));
      });
    });

    container.querySelectorAll('.btn-user-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        if (!confirm('Are you sure you want to deactivate/delete this user?')) return;
        try {
          await api.deleteUser(id);
          showToast('User deactivated.', 'success');
          renderUsersView(container);
        } catch (err) {}
      });
    });

  } catch (err) {
    container.innerHTML = `<div class="r5-card"><div class="r5-card-body">${err.message}</div></div>`;
  }
}

/* =========================================================================
   VIEW 4: OPERATIONAL OWNERSHIP & LINEAGE TRACING
   ========================================================================= */
let activeTraceStoreId = null;
let activeTraceDomain = 'REFRIGERATION_HVAC';
let ownershipDomainFilter = '';
let ownershipSearchQuery = '';

export async function renderOwnershipView(container) {
  container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">Loading ownership & lineage graph...</div>`;

  try {
    if (!activeTraceStoreId) {
      activeTraceStoreId = state.selectedStoreId || (state.stores[0]?.id);
    }

    const [stores, mappings, trace] = await Promise.all([
      api.getStores(),
      api.getOwnershipMappings(undefined, ownershipDomainFilter || undefined, ownershipSearchQuery || undefined),
      activeTraceStoreId ? api.traceOperationalObject({ storeId: activeTraceStoreId, domain: activeTraceDomain }) : Promise.resolve(null)
    ]);

    container.innerHTML = `
      <!-- Synthetic Demo Data Disclaimer Banner -->
      <div class="demo-seed-banner">
        <span style="font-weight: 700; color: #f59e0b;">DEMO / SEED DATA</span> &mdash;
        Operational ownership routing and lineage graphs represent synthetic topology for demonstration.
      </div>

      <!-- SECTION 1: INTERACTIVE OPERATIONAL LINEAGE & TRACE EXPLORER -->
      <div class="r5-card" style="margin-bottom: 1.5rem;">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div>
            <div class="r5-card-title">
              <span>🧭</span>
              <span>Operational Lineage & Tracing Engine</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
              Trace any operational object back to its root hierarchy: Organization ➔ Region ➔ Store ➔ Team ➔ Escalation Owner.
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <select id="trace-select-store" class="form-select" style="padding: 0.45rem 0.75rem; font-size: 0.82rem;">
              ${stores.map(s => `
                <option value="${s.id}" ${s.id === activeTraceStoreId ? 'selected' : ''}>Store #${s.storeNumber} &mdash; ${s.name}</option>
              `).join('')}
            </select>
            <select id="trace-select-domain" class="form-select" style="padding: 0.45rem 0.75rem; font-size: 0.82rem;">
              <option value="REFRIGERATION_HVAC" ${activeTraceDomain === 'REFRIGERATION_HVAC' ? 'selected' : ''}>Refrigeration & HVAC</option>
              <option value="POINT_OF_SALE_IT" ${activeTraceDomain === 'POINT_OF_SALE_IT' ? 'selected' : ''}>Point of Sale & IT</option>
              <option value="FACILITIES_SAFETY" ${activeTraceDomain === 'FACILITIES_SAFETY' ? 'selected' : ''}>Facilities & Physical Safety</option>
              <option value="INVENTORY_LOGISTICS" ${activeTraceDomain === 'INVENTORY_LOGISTICS' ? 'selected' : ''}>Cold Chain Logistics</option>
              <option value="ENERGY_ELECTRICAL" ${activeTraceDomain === 'ENERGY_ELECTRICAL' ? 'selected' : ''}>Energy & Electrical Grid</option>
            </select>
            <button id="btn-run-trace" class="btn btn-primary btn-sm">Trace Lineage</button>
          </div>
        </div>

        <div class="r5-card-body">
          <div id="trace-display-container">
            ${trace ? renderTraceVisualChain(trace) : `<div style="color: var(--text-muted);">Select a store to run trace.</div>`}
          </div>
        </div>
      </div>

      <!-- SECTION 2: OPERATIONAL OWNERSHIP MAPPINGS TABLE -->
      <div class="r5-card">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div class="r5-card-title">
            <span>📋</span>
            <span>Domain Ownership Mappings (${mappings.length})</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <input type="text" id="ownership-search-input" class="form-input" style="padding: 0.4rem 0.75rem; font-size: 0.82rem; width: 160px;" placeholder="Search domain/team..." value="${ownershipSearchQuery}" />
            <select id="ownership-domain-filter" class="form-select" style="padding: 0.4rem 0.75rem; font-size: 0.82rem;">
              <option value="">All Domains</option>
              <option value="REFRIGERATION_HVAC" ${ownershipDomainFilter === 'REFRIGERATION_HVAC' ? 'selected' : ''}>Refrigeration & HVAC</option>
              <option value="POINT_OF_SALE_IT" ${ownershipDomainFilter === 'POINT_OF_SALE_IT' ? 'selected' : ''}>Point of Sale & IT</option>
              <option value="FACILITIES_SAFETY" ${ownershipDomainFilter === 'FACILITIES_SAFETY' ? 'selected' : ''}>Facilities & Safety</option>
              <option value="INVENTORY_LOGISTICS" ${ownershipDomainFilter === 'INVENTORY_LOGISTICS' ? 'selected' : ''}>Cold Chain Logistics</option>
              <option value="ENERGY_ELECTRICAL" ${ownershipDomainFilter === 'ENERGY_ELECTRICAL' ? 'selected' : ''}>Energy & Electrical</option>
            </select>
            <button id="btn-create-mapping" class="btn btn-primary btn-sm">+ Add Ownership Mapping</button>
          </div>
        </div>
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Operational Domain</th>
                <th>Store / Scope</th>
                <th>Primary Team</th>
                <th>Secondary Team</th>
                <th>Escalation Owner</th>
                <th>SLA Response</th>
                <th>Auto-Escalate</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${mappings.length === 0 ? `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No operational ownership mappings configured.</td></tr>` : ''}
              ${mappings.map(m => `
                <tr>
                  <td>
                    <span class="badge badge-p4">${m.operationalDomain.replace(/_/g, ' ')}</span>
                  </td>
                  <td>
                    <div style="font-size: 0.82rem; font-weight: 600; color: #fff;">${m.storeName || 'Enterprise Scope'}</div>
                  </td>
                  <td>
                    <div style="font-weight: 600; color: var(--accent-cyan); font-size: 0.82rem;">${m.primaryTeamName}</div>
                  </td>
                  <td>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">${m.secondaryTeamName || 'None'}</div>
                  </td>
                  <td>
                    <div style="font-size: 0.82rem; font-weight: 600; color: #fff;">${m.escalationOwnerName || 'Store Manager'}</div>
                    <div style="font-size: 0.72rem; color: var(--text-secondary);">${m.escalationOwnerEmail || 'storemanager@apex.com'}</div>
                  </td>
                  <td>
                    <span class="badge badge-p3">${m.slaResponseMinutes}m target</span>
                  </td>
                  <td>
                    <span class="badge badge-neutral">${m.autoEscalateAfterMinutes}m</span>
                  </td>
                  <td style="text-align: right;">
                    <button class="btn btn-secondary btn-sm btn-mapping-edit" data-id="${m.id}">Edit</button>
                    <button class="btn btn-danger btn-sm btn-mapping-delete" data-id="${m.id}">✕</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Trace Controls
    container.querySelector('#btn-run-trace')?.addEventListener('click', () => {
      activeTraceStoreId = container.querySelector('#trace-select-store').value;
      activeTraceDomain = container.querySelector('#trace-select-domain').value;
      renderOwnershipView(container);
    });

    // Mappings controls
    container.querySelector('#ownership-search-input')?.addEventListener('change', (e) => {
      ownershipSearchQuery = e.target.value.trim();
      renderOwnershipView(container);
    });

    container.querySelector('#ownership-domain-filter')?.addEventListener('change', (e) => {
      ownershipDomainFilter = e.target.value;
      renderOwnershipView(container);
    });

    container.querySelector('#btn-create-mapping')?.addEventListener('click', () => {
      openCreateOwnershipModal(() => renderOwnershipView(container));
    });

    container.querySelectorAll('.btn-mapping-edit').forEach(btn => {
      btn.addEventListener('click', () => {
        openEditOwnershipModal(btn.getAttribute('data-id'), () => renderOwnershipView(container));
      });
    });

    container.querySelectorAll('.btn-mapping-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        if (!confirm('Are you sure you want to delete this ownership routing mapping?')) return;
        try {
          await api.deleteOwnershipMapping(id);
          showToast('Ownership mapping removed.', 'success');
          renderOwnershipView(container);
        } catch (err) {}
      });
    });

  } catch (err) {
    container.innerHTML = `<div class="r5-card"><div class="r5-card-body">${err.message}</div></div>`;
  }
}

function renderTraceVisualChain(trace) {
  return `
    <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.85rem 1rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
      <div style="font-size: 0.82rem; color: var(--text-secondary);">
        Active Lineage Chain: <strong style="color: var(--accent-cyan);">${trace.lineagePath}</strong>
      </div>
      <span class="badge status-operational">VALIDATED TRACE</span>
    </div>

    <div class="lineage-chain">
      <!-- Node 1: Organization -->
      <div class="lineage-node node-org">
        <div class="lineage-node-type">🏢 Organization</div>
        <div class="lineage-node-title">${trace.organization?.name || 'Apex Retail Holdings'}</div>
        <div class="lineage-node-detail">
          <span>Code: <strong>${trace.organization?.code || 'APEX'}</strong></span>
          <span>Status: <strong style="color: #10b981;">${trace.organization?.status || 'ACTIVE'}</strong></span>
        </div>
      </div>

      <div class="lineage-arrow">➔</div>

      <!-- Node 2: Region -->
      <div class="lineage-node node-region">
        <div class="lineage-node-type">🌐 Region</div>
        <div class="lineage-node-title">${trace.region?.name || 'Pacific Northwest'}</div>
        <div class="lineage-node-detail">
          <span>Code: <strong>${trace.region?.code || 'PNW'}</strong></span>
          <span>Lead: <strong>${trace.region?.leadUserName || 'Regional VP'}</strong></span>
        </div>
      </div>

      <div class="lineage-arrow">➔</div>

      <!-- Node 3: Store -->
      <div class="lineage-node node-store">
        <div class="lineage-node-type">🏪 Store</div>
        <div class="lineage-node-title">#${trace.store?.storeNumber} ${trace.store?.name}</div>
        <div class="lineage-node-detail">
          <span>Status: ${renderOperatingStatusBadge(trace.store?.operatingStatus)}</span>
          <span>Tier: <strong>${trace.store?.formatTier || 'SUPERCENTER'}</strong></span>
        </div>
      </div>

      <div class="lineage-arrow">➔</div>

      <!-- Node 4: Team -->
      <div class="lineage-node node-team">
        <div class="lineage-node-type">👥 Primary Team</div>
        <div class="lineage-node-title">${trace.primaryTeam?.name || 'Store Maintenance'}</div>
        <div class="lineage-node-detail">
          <span>Spec: <strong>${(trace.primaryTeam?.specialization || 'GENERAL').replace(/_/g, ' ')}</strong></span>
          <span>Escalation: <strong>${trace.primaryTeam?.escalationTier || 'TIER_1'}</strong></span>
        </div>
      </div>

      <div class="lineage-arrow">➔</div>

      <!-- Node 5: User / Escalation Owner -->
      <div class="lineage-node node-user">
        <div class="lineage-node-type">👤 Escalation Owner</div>
        <div class="lineage-node-title">${trace.escalationOwner?.fullName || 'Store Manager'}</div>
        <div class="lineage-node-detail">
          <span>Role: <strong>${trace.escalationOwner?.role?.replace(/_/g, ' ') || 'STORE MANAGER'}</strong></span>
          <span>Contact: <strong style="color: var(--accent-cyan);">${trace.escalationOwner?.email || 'N/A'}</strong></span>
        </div>
      </div>
    </div>
  `;
}

/* =========================================================================
   VIEW 5: ROLE GOVERNANCE & PERMISSIONS MATRIX
   ========================================================================= */
export async function renderRolesView(container) {
  container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">Loading role permissions matrix...</div>`;

  try {
    const [roles, matrixData] = await Promise.all([
      api.getRoles(),
      api.getPermissionsMatrix()
    ]);

    container.innerHTML = `
      <!-- Synthetic Demo Data Disclaimer Banner -->
      <div class="demo-seed-banner">
        <span style="font-weight: 700; color: #f59e0b;">DEMO / SEED DATA</span> &mdash;
        Role configurations and permissions below govern platform authorization policies.
      </div>

      <!-- SECTION 1: ROLES OVERVIEW CARDS -->
      <div class="r5-card" style="margin-bottom: 1.5rem;">
        <div class="r5-card-header" style="flex-wrap: wrap; gap: 0.75rem;">
          <div>
            <div class="r5-card-title">
              <span>🛡️</span>
              <span>System & Operational Roles (${roles.length})</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
              Built-in immutable system roles and dynamically provisioned custom roles.
            </div>
          </div>
          <button id="btn-create-role" class="btn btn-primary btn-sm">+ Create Custom Role</button>
        </div>

        <div class="r5-card-body" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem;">
          ${roles.map(r => `
            <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; display: flex; flex-direction: column; justify-content: space-between;">
              <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                  <span style="font-weight: 700; color: #fff; font-size: 0.9rem;">${r.name.replace(/_/g, ' ')}</span>
                  <span class="badge ${r.isSystem ? 'badge-p4' : 'badge-neutral'}">${r.isSystem ? 'SYSTEM' : 'CUSTOM'}</span>
                </div>
                <div style="font-size: 0.78rem; color: var(--text-secondary); min-height: 38px;">
                  ${r.description || 'Enterprise role definition.'}
                </div>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem; border-top: 1px solid var(--border-subtle); padding-top: 0.5rem; font-size: 0.72rem; color: var(--text-muted);">
                <span>${r.userCount || 0} assigned users</span>
                ${!r.isSystem ? `<button class="btn btn-danger btn-sm btn-delete-role" data-id="${r.id}" style="padding: 2px 6px; font-size: 0.7rem;">Delete</button>` : '<span style="opacity: 0.5;">Protected</span>'}
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- SECTION 2: PERMISSIONS MATRIX GRID -->
      <div class="r5-card">
        <div class="r5-card-header">
          <div class="r5-card-title">
            <span>📊</span>
            <span>Comprehensive Role Permissions Matrix</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--accent-cyan);">
            Your Active Role: <strong>${state.user?.role?.replace(/_/g, ' ')}</strong>
          </div>
        </div>
        <div class="r5-table-container">
          <table class="matrix-table">
            <thead>
              <tr>
                <th style="min-width: 240px; text-align: left;">Operational Permission / Capability</th>
                ${matrixData.roles.map(r => `
                  <th style="${state.user?.role === r ? 'background-color: rgba(6, 182, 212, 0.15); color: #fff;' : ''}">
                    ${r.replace(/_/g, ' ')}
                  </th>
                `).join('')}
              </tr>
            </thead>
            <tbody>
              ${Object.entries(matrixData.categories).map(([category, perms]) => `
                <tr>
                  <td colspan="${matrixData.roles.length + 1}" class="matrix-cat-header">
                    ${category.toUpperCase()} PERMISSIONS
                  </td>
                </tr>
                ${perms.map(p => `
                  <tr>
                    <td>
                      <div style="font-weight: 600; color: #fff; font-size: 0.8rem;">${p.label}</div>
                      <div style="font-size: 0.7rem; color: var(--text-muted);">${p.description}</div>
                    </td>
                    ${matrixData.roles.map(r => {
                      const granted = p.roles.includes(r);
                      const isUserRole = state.user?.role === r;
                      return `
                        <td style="${isUserRole ? 'background-color: rgba(6, 182, 212, 0.05);' : ''}">
                          ${granted ? '<span class="matrix-check">✓</span>' : '<span class="matrix-dash">&mdash;</span>'}
                        </td>
                      `;
                    }).join('')}
                  </tr>
                `).join('')}
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    container.querySelector('#btn-create-role')?.addEventListener('click', () => {
      openCreateRoleModal(() => renderRolesView(container));
    });

    container.querySelectorAll('.btn-delete-role').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        if (!confirm('Are you sure you want to delete this custom role?')) return;
        try {
          await api.deleteRole(id);
          showToast('Custom role deleted.', 'success');
          renderRolesView(container);
        } catch (err) {}
      });
    });

  } catch (err) {
    container.innerHTML = `<div class="r5-card"><div class="r5-card-body">${err.message}</div></div>`;
  }
}

/* =========================================================================
   MODALS & DIALOG CONTROLLERS
   ========================================================================= */

// Store Modals
async function openCreateStoreModal(onSuccess) {
  try {
    const regions = await api.getRegions(state.selectedOrgId);
    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Add Retail Store Facility</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-create-store">
        <div class="modal-body">
          <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Store Number</label>
              <input type="text" id="cs-number" class="form-input" required placeholder="e.g. 106" />
            </div>
            <div class="form-group">
              <label class="form-label">Store Name</label>
              <input type="text" id="cs-name" class="form-input" required placeholder="e.g. Westside Hypercenter" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Region Assignment</label>
            <select id="cs-region" class="form-select" required>
              ${regions.map(r => `<option value="${r.id}">${r.name} (${r.code})</option>`).join('')}
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Initial Operating Status</label>
              <select id="cs-status" class="form-select">
                <option value="OPERATIONAL">Operational</option>
                <option value="MAINTENANCE_HOLD">Maintenance Hold</option>
                <option value="RENOVATION">Renovation</option>
                <option value="TEMPORARILY_CLOSED">Temporarily Closed</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Format Tier</label>
              <select id="cs-format" class="form-select">
                <option value="SUPERCENTER">Supercenter</option>
                <option value="HYPERMARKET">Hypermarket</option>
                <option value="EXPRESS">Express</option>
                <option value="FLAGSHIP">Flagship</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Square Footage</label>
              <input type="number" id="cs-sqft" class="form-input" value="125000" />
            </div>
            <div class="form-group">
              <label class="form-label">Contact Phone</label>
              <input type="text" id="cs-phone" class="form-input" placeholder="+1-555-0199" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Operating Hours</label>
            <input type="text" id="cs-hours" class="form-input" value="06:00 - 23:00" />
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Create Store Facility</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-create-store').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.createStore({
          storeNumber: document.getElementById('cs-number').value.trim(),
          name: document.getElementById('cs-name').value.trim(),
          organizationId: state.selectedOrgId,
          regionId: document.getElementById('cs-region').value,
          operatingStatus: document.getElementById('cs-status').value,
          metadata: {
            formatTier: document.getElementById('cs-format').value,
            squareFootage: parseInt(document.getElementById('cs-sqft').value) || 0,
            contactPhone: document.getElementById('cs-phone').value.trim(),
            openingHours: document.getElementById('cs-hours').value.trim()
          }
        });
        showToast('Retail store facility registered and audited.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load regions: ' + err.message, 'error');
  }
}

async function openEditStoreModal(storeId, onSuccess) {
  try {
    const [store, regions] = await Promise.all([
      api.getStore(storeId),
      api.getRegions(state.selectedOrgId)
    ]);
    const meta = store.metadata || {};

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Edit Store Details &mdash; #${store.storeNumber}</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-edit-store">
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Store Name</label>
            <input type="text" id="es-name" class="form-input" required value="${store.name}" />
          </div>
          <div class="form-group">
            <label class="form-label">Region Assignment</label>
            <select id="es-region" class="form-select" required>
              ${regions.map(r => `<option value="${r.id}" ${r.id === store.regionId ? 'selected' : ''}>${r.name} (${r.code})</option>`).join('')}
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Format Tier</label>
              <select id="es-format" class="form-select">
                <option value="SUPERCENTER" ${meta.formatTier === 'SUPERCENTER' ? 'selected' : ''}>Supercenter</option>
                <option value="HYPERMARKET" ${meta.formatTier === 'HYPERMARKET' ? 'selected' : ''}>Hypermarket</option>
                <option value="EXPRESS" ${meta.formatTier === 'EXPRESS' ? 'selected' : ''}>Express</option>
                <option value="FLAGSHIP" ${meta.formatTier === 'FLAGSHIP' ? 'selected' : ''}>Flagship</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Square Footage</label>
              <input type="number" id="es-sqft" class="form-input" value="${meta.squareFootage || 0}" />
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Contact Phone</label>
              <input type="text" id="es-phone" class="form-input" value="${meta.contactPhone || ''}" />
            </div>
            <div class="form-group">
              <label class="form-label">Opening Hours</label>
              <input type="text" id="es-hours" class="form-input" value="${meta.openingHours || '06:00 - 23:00'}" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-edit-store').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.updateStore(storeId, {
          name: document.getElementById('es-name').value.trim(),
          regionId: document.getElementById('es-region').value,
          metadata: {
            ...meta,
            formatTier: document.getElementById('es-format').value,
            squareFootage: parseInt(document.getElementById('es-sqft').value) || 0,
            contactPhone: document.getElementById('es-phone').value.trim(),
            openingHours: document.getElementById('es-hours').value.trim()
          }
        });
        showToast('Store updated successfully.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load store: ' + err.message, 'error');
  }
}

async function openStoreStatusModal(storeId, onSuccess) {
  try {
    const store = await api.getStore(storeId);
    openModal(`
      <div class="modal-header">
        <div>
          <h3 style="font-size: 1.1rem; font-weight: 700;">Update Store Operating Status</h3>
          <div style="font-size: 0.8rem; color: var(--text-muted);">#${store.storeNumber} &mdash; ${store.name}</div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-update-store-status">
        <div class="modal-body">
          <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.75rem 1rem; margin-bottom: 0.75rem;">
            <div style="font-size: 0.78rem; color: var(--text-secondary);">Current Status:</div>
            <div style="margin-top: 4px;">${renderOperatingStatusBadge(store.operatingStatus)}</div>
          </div>
          <div class="form-group">
            <label class="form-label">New Operating Status</label>
            <select id="ss-new-status" class="form-select" required>
              <option value="OPERATIONAL" ${store.operatingStatus === 'OPERATIONAL' ? 'selected' : ''}>Operational (Normal Operations)</option>
              <option value="MAINTENANCE_HOLD" ${store.operatingStatus === 'MAINTENANCE_HOLD' ? 'selected' : ''}>Maintenance Hold (Critical System Outage)</option>
              <option value="RENOVATION" ${store.operatingStatus === 'RENOVATION' ? 'selected' : ''}>Renovation (Capital Works)</option>
              <option value="TEMPORARILY_CLOSED" ${store.operatingStatus === 'TEMPORARILY_CLOSED' ? 'selected' : ''}>Temporarily Closed (Severe Weather/Emergency)</option>
              <option value="DECOMMISSIONED" ${store.operatingStatus === 'DECOMMISSIONED' ? 'selected' : ''}>Decommissioned (Permanently Shut Down)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Mandatory Operational Justification</label>
            <textarea id="ss-justification" class="form-textarea" required minlength="5" placeholder="Document reason for status change (logged to immutable audit trail)..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Apply Status Change</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-update-store-status').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.updateStoreStatus(
          storeId,
          document.getElementById('ss-new-status').value,
          document.getElementById('ss-justification').value.trim()
        );
        showToast('Store operating status updated and audited.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load store: ' + err.message, 'error');
  }
}

async function openStoreMetadataModal(storeId, onSuccess) {
  try {
    const store = await api.getStore(storeId);
    const meta = store.metadata || {};

    openModal(`
      <div class="modal-header">
        <div>
          <h3 style="font-size: 1.1rem; font-weight: 700;">Store Facility Metadata</h3>
          <div style="font-size: 0.8rem; color: var(--text-muted);">#${store.storeNumber} &mdash; ${store.name}</div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-store-metadata">
        <div class="modal-body">
          <div style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
            Extensible attributes, specifications, and operational parameters:
          </div>
          <div class="form-group">
            <label class="form-label">Metadata (JSON format)</label>
            <textarea id="sm-json" class="form-textarea" style="font-family: var(--font-family-mono); font-size: 0.82rem; min-height: 160px;" required>${JSON.stringify(meta, null, 2)}</textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Update Metadata</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-store-metadata').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const parsed = JSON.parse(document.getElementById('sm-json').value);
        await api.updateStore(storeId, { metadata: parsed });
        showToast('Metadata updated and logged to audit trail.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {
        showToast('Invalid JSON: ' + err.message, 'error');
      }
    });
  } catch (err) {
    showToast('Failed to load metadata: ' + err.message, 'error');
  }
}

// Region Modals
async function openCreateRegionModal(onSuccess) {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Add Operational Region</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-create-region">
      <div class="modal-body">
        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Region Code</label>
            <input type="text" id="cr-code" class="form-input" required placeholder="e.g. PNW" />
          </div>
          <div class="form-group">
            <label class="form-label">Region Name</label>
            <input type="text" id="cr-name" class="form-input" required placeholder="e.g. Pacific Northwest Division" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Description / Operating Scope</label>
          <textarea id="cr-desc" class="form-textarea" placeholder="Covers WA, OR, ID retail territories..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Region</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('form-create-region').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.createRegion({
        code: document.getElementById('cr-code').value.trim().toUpperCase(),
        name: document.getElementById('cr-name').value.trim(),
        organizationId: state.selectedOrgId,
        description: document.getElementById('cr-desc').value.trim()
      });
      showToast('Operational region created.', 'success');
      closeModal();
      if (onSuccess) onSuccess();
    } catch (err) {}
  });
}

async function openEditRegionModal(regionId, onSuccess) {
  try {
    const regions = await api.getRegions(state.selectedOrgId);
    const reg = regions.find(r => r.id === regionId);
    if (!reg) return;

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Edit Region &mdash; ${reg.code}</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-edit-region">
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Region Name</label>
            <input type="text" id="er-name" class="form-input" required value="${reg.name}" />
          </div>
          <div class="form-group">
            <label class="form-label">Description</label>
            <textarea id="er-desc" class="form-textarea">${reg.description || ''}</textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-edit-region').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.updateRegion(regionId, {
          name: document.getElementById('er-name').value.trim(),
          description: document.getElementById('er-desc').value.trim()
        });
        showToast('Region updated.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {}
}

// Organization Modals
async function openCreateOrgModal(onSuccess) {
  openModal(`
    <div class="modal-header">
      <h3 style="font-size: 1.1rem; font-weight: 700;">Add Enterprise Organization</h3>
      <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
    </div>
    <form id="form-create-org">
      <div class="modal-body">
        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Org Code</label>
            <input type="text" id="co-code" class="form-input" required placeholder="e.g. APEX" />
          </div>
          <div class="form-group">
            <label class="form-label">Organization Name</label>
            <input type="text" id="co-name" class="form-input" required placeholder="e.g. Apex Retail Holdings" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Description</label>
          <textarea id="co-desc" class="form-textarea" placeholder="Enterprise retail parent entity..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Organization</button>
      </div>
    </form>
  `);

  document.getElementById('btn-close-modal').addEventListener('click', closeModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

  document.getElementById('form-create-org').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.createOrganization({
        code: document.getElementById('co-code').value.trim().toUpperCase(),
        name: document.getElementById('co-name').value.trim(),
        description: document.getElementById('co-desc').value.trim(),
        status: 'ACTIVE'
      });
      showToast('Organization registered.', 'success');
      closeModal();
      if (onSuccess) onSuccess();
    } catch (err) {}
  });
}

async function openEditOrgModal(orgId, onSuccess) {
  try {
    const orgs = await api.getOrganizations();
    const org = orgs.find(o => o.id === orgId);
    if (!org) return;

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Edit Organization &mdash; ${org.code}</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-edit-org">
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Organization Name</label>
            <input type="text" id="eo-name" class="form-input" required value="${org.name}" />
          </div>
          <div class="form-group">
            <label class="form-label">Status</label>
            <select id="eo-status" class="form-select">
              <option value="ACTIVE" ${org.status === 'ACTIVE' ? 'selected' : ''}>Active</option>
              <option value="INACTIVE" ${org.status === 'INACTIVE' ? 'selected' : ''}>Inactive</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Description</label>
            <textarea id="eo-desc" class="form-textarea">${org.description || ''}</textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-edit-org').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.updateOrganization(orgId, {
          name: document.getElementById('eo-name').value.trim(),
          description: document.getElementById('eo-desc').value.trim(),
          status: document.getElementById('eo-status').value
        });
        showToast('Organization updated.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {}
}

// Team & Members Modals
async function openCreateTeamModal(onSuccess) {
  try {
    const [regions, stores, users] = await Promise.all([
      api.getRegions(state.selectedOrgId),
      api.getStores(),
      api.getUsers()
    ]);

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Add Operational Squad / Team</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-create-team">
        <div class="modal-body">
          <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Team Code</label>
              <input type="text" id="ct-code" class="form-input" required placeholder="e.g. S104-ELEC" />
            </div>
            <div class="form-group">
              <label class="form-label">Team Name</label>
              <input type="text" id="ct-name" class="form-input" required placeholder="e.g. Store 104 Electrical Squad" />
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Specialization</label>
              <select id="ct-spec" class="form-select" required>
                <option value="HVAC_REFRIGERATION">HVAC & Refrigeration</option>
                <option value="ELECTRICAL">Electrical Systems</option>
                <option value="PLUMBING">Plumbing & Drainage</option>
                <option value="FOOD_SAFETY">Food Safety & Sanitation</option>
                <option value="LOSS_PREVENTION">Loss Prevention</option>
                <option value="IT_POINT_OF_SALE">Point of Sale & IT</option>
                <option value="GENERAL_MAINTENANCE">General Maintenance</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Responsibility Level</label>
              <select id="ct-resp" class="form-select" required>
                <option value="STORE_LEVEL">Store-Level Dedicated</option>
                <option value="REGIONAL_DISPATCH">Regional Roving Dispatch</option>
                <option value="CENTRAL_FACILITIES">Central Facilities & Tier-3</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Region</label>
              <select id="ct-region" class="form-select">
                <option value="">(None / All Regions)</option>
                ${regions.map(r => `<option value="${r.id}">${r.name}</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Store Scope</label>
              <select id="ct-store" class="form-select">
                <option value="">(Region-wide / Multiple)</option>
                ${stores.map(s => `<option value="${s.id}">#${s.storeNumber} ${s.name}</option>`).join('')}
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Escalation Tier</label>
              <select id="ct-tier" class="form-select">
                <option value="TIER_1">Tier 1 (First Response)</option>
                <option value="TIER_2">Tier 2 (Specialist Squad)</option>
                <option value="TIER_3">Tier 3 (Master / Vendor)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Escalation Contact</label>
              <input type="text" id="ct-contact" class="form-input" placeholder="e.g. dispatch@apex.com" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Team Lead</label>
            <select id="ct-lead" class="form-select">
              <option value="">(Unassigned)</option>
              ${users.map(u => `<option value="${u.id}">${u.fullName} (${u.role})</option>`).join('')}
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Create Operational Team</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-create-team').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.createTeam({
          teamCode: document.getElementById('ct-code').value.trim().toUpperCase(),
          name: document.getElementById('ct-name').value.trim(),
          specialization: document.getElementById('ct-spec').value,
          responsibility: document.getElementById('ct-resp').value,
          regionId: document.getElementById('ct-region').value || null,
          storeId: document.getElementById('ct-store').value || null,
          escalationTier: document.getElementById('ct-tier').value,
          escalationContact: document.getElementById('ct-contact').value.trim(),
          leadUserId: document.getElementById('ct-lead').value || null,
          status: 'ACTIVE'
        });
        showToast('Operational team created.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load team form data: ' + err.message, 'error');
  }
}

async function openEditTeamModal(teamId, onSuccess) {
  try {
    const [team, regions, stores, users] = await Promise.all([
      api.getTeam(teamId),
      api.getRegions(state.selectedOrgId),
      api.getStores(),
      api.getUsers()
    ]);

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Edit Team &mdash; ${team.name}</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-edit-team">
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Team Name</label>
            <input type="text" id="et-name" class="form-input" required value="${team.name}" />
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Specialization</label>
              <select id="et-spec" class="form-select" required>
                <option value="HVAC_REFRIGERATION" ${team.specialization === 'HVAC_REFRIGERATION' ? 'selected' : ''}>HVAC & Refrigeration</option>
                <option value="ELECTRICAL" ${team.specialization === 'ELECTRICAL' ? 'selected' : ''}>Electrical Systems</option>
                <option value="PLUMBING" ${team.specialization === 'PLUMBING' ? 'selected' : ''}>Plumbing & Drainage</option>
                <option value="FOOD_SAFETY" ${team.specialization === 'FOOD_SAFETY' ? 'selected' : ''}>Food Safety & Sanitation</option>
                <option value="LOSS_PREVENTION" ${team.specialization === 'LOSS_PREVENTION' ? 'selected' : ''}>Loss Prevention</option>
                <option value="IT_POINT_OF_SALE" ${team.specialization === 'IT_POINT_OF_SALE' ? 'selected' : ''}>Point of Sale & IT</option>
                <option value="GENERAL_MAINTENANCE" ${team.specialization === 'GENERAL_MAINTENANCE' ? 'selected' : ''}>General Maintenance</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Responsibility Level</label>
              <select id="et-resp" class="form-select" required>
                <option value="STORE_LEVEL" ${team.responsibility === 'STORE_LEVEL' ? 'selected' : ''}>Store-Level Dedicated</option>
                <option value="REGIONAL_DISPATCH" ${team.responsibility === 'REGIONAL_DISPATCH' ? 'selected' : ''}>Regional Roving Dispatch</option>
                <option value="CENTRAL_FACILITIES" ${team.responsibility === 'CENTRAL_FACILITIES' ? 'selected' : ''}>Central Facilities & Tier-3</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Escalation Tier</label>
              <select id="et-tier" class="form-select">
                <option value="TIER_1" ${team.escalationTier === 'TIER_1' ? 'selected' : ''}>Tier 1 (First Response)</option>
                <option value="TIER_2" ${team.escalationTier === 'TIER_2' ? 'selected' : ''}>Tier 2 (Specialist Squad)</option>
                <option value="TIER_3" ${team.escalationTier === 'TIER_3' ? 'selected' : ''}>Tier 3 (Master / Vendor)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Escalation Contact</label>
              <input type="text" id="et-contact" class="form-input" value="${team.escalationContact || ''}" />
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Team Lead</label>
              <select id="et-lead" class="form-select">
                <option value="">(Unassigned)</option>
                ${users.map(u => `<option value="${u.id}" ${u.id === team.leadUserId ? 'selected' : ''}>${u.fullName} (${u.role})</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Status</label>
              <select id="et-status" class="form-select">
                <option value="ACTIVE" ${team.status === 'ACTIVE' ? 'selected' : ''}>Active</option>
                <option value="INACTIVE" ${team.status === 'INACTIVE' ? 'selected' : ''}>Inactive</option>
              </select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-edit-team').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.updateTeam(teamId, {
          name: document.getElementById('et-name').value.trim(),
          specialization: document.getElementById('et-spec').value,
          responsibility: document.getElementById('et-resp').value,
          escalationTier: document.getElementById('et-tier').value,
          escalationContact: document.getElementById('et-contact').value.trim(),
          leadUserId: document.getElementById('et-lead').value || null,
          status: document.getElementById('et-status').value
        });
        showToast('Team updated.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load team: ' + err.message, 'error');
  }
}

async function openTeamMembersModal(teamId, onSuccess) {
  try {
    const [team, members, users] = await Promise.all([
      api.getTeam(teamId),
      api.getTeamMembers(teamId),
      api.getUsers()
    ]);

    const memberUserIds = new Set(members.map(m => m.userId));
    const availableUsers = users.filter(u => !memberUserIds.has(u.id));

    openModal(`
      <div class="modal-header">
        <div>
          <h3 style="font-size: 1.1rem; font-weight: 700;">Squad Roster &mdash; ${team.name}</h3>
          <div style="font-size: 0.8rem; color: var(--text-muted);">${members.length} Active Operational Members</div>
        </div>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <div class="modal-body">
        <!-- Add Member Form -->
        <form id="form-add-member" style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
          <div style="font-weight: 700; color: #fff; font-size: 0.85rem; margin-bottom: 0.5rem;">Add Member to Squad</div>
          <div style="display: grid; grid-template-columns: 2fr 1fr auto; gap: 0.5rem; align-items: flex-end;">
            <div class="form-group">
              <label class="form-label">Select User</label>
              <select id="am-user" class="form-select" required>
                ${availableUsers.length === 0 ? '<option value="">(All enterprise users assigned)</option>' : ''}
                ${availableUsers.map(u => `<option value="${u.id}">${u.fullName} (${u.role})</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Squad Role</label>
              <select id="am-role" class="form-select" required>
                <option value="SPECIALIST">Specialist</option>
                <option value="TECHNICIAN">Technician</option>
                <option value="DISPATCHER">Dispatcher</option>
                <option value="ANALYST">Analyst</option>
                <option value="LEAD">Squad Lead</option>
              </select>
            </div>
            <button type="submit" class="btn btn-primary" ${availableUsers.length === 0 ? 'disabled' : ''}>+ Add</button>
          </div>
        </form>

        <!-- Current Members Table -->
        <div class="r5-table-container">
          <table class="r5-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Squad Role</th>
                <th>Assigned</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${members.length === 0 ? `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No members currently assigned to this squad.</td></tr>` : ''}
              ${members.map(m => `
                <tr>
                  <td>
                    <div style="font-weight: 600; color: #fff;">${m.userName}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">${m.userEmail}</div>
                  </td>
                  <td>
                    <span class="badge badge-p4">${m.teamRole}</span>
                  </td>
                  <td class="table-id-mono" style="font-size: 0.75rem;">
                    ${new Date(m.assignedAt).toLocaleDateString()}
                  </td>
                  <td style="text-align: right;">
                    <button class="btn btn-danger btn-sm btn-remove-member" data-id="${m.userId}">Remove</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="btn-close-members">Close</button>
      </div>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-members').addEventListener('click', closeModal);

    document.getElementById('form-add-member').addEventListener('submit', async (e) => {
      e.preventDefault();
      const userId = document.getElementById('am-user').value;
      const teamRole = document.getElementById('am-role').value;
      if (!userId) return;
      try {
        await api.addTeamMember(teamId, { userId, teamRole });
        showToast('Member assigned to operational team.', 'success');
        openTeamMembersModal(teamId, onSuccess);
        if (onSuccess) onSuccess();
      } catch (err) {}
    });

    document.querySelectorAll('.btn-remove-member').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = btn.getAttribute('data-id');
        try {
          await api.removeTeamMember(teamId, userId);
          showToast('Member unassigned.', 'info');
          openTeamMembersModal(teamId, onSuccess);
          if (onSuccess) onSuccess();
        } catch (err) {}
      });
    });

  } catch (err) {
    showToast('Failed to load squad members: ' + err.message, 'error');
  }
}

// User Modals
async function openCreateUserModal(onSuccess) {
  try {
    const [regions, stores, teams] = await Promise.all([
      api.getRegions(state.selectedOrgId),
      api.getStores(),
      api.getTeams()
    ]);

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Add Enterprise User</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-create-user">
        <div class="modal-body">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Full Name</label>
              <input type="text" id="cu-name" class="form-input" required placeholder="e.g. Jordan Miller" />
            </div>
            <div class="form-group">
              <label class="form-label">Email Address</label>
              <input type="email" id="cu-email" class="form-input" required placeholder="jordan@apex.com" />
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Temporary Password</label>
              <input type="password" id="cu-pass" class="form-input" required value="Password123!" />
            </div>
            <div class="form-group">
              <label class="form-label">System Role</label>
              <select id="cu-role" class="form-select" required>
                <option value="ORGANIZATION_ADMIN">Organization Admin</option>
                <option value="OPERATIONS_MANAGER">Operations Manager</option>
                <option value="REGIONAL_MANAGER">Regional VP</option>
                <option value="STORE_MANAGER">Store Manager</option>
                <option value="MAINTENANCE_TEAM">Maintenance Team Tech</option>
                <option value="ANALYST">Operations Analyst</option>
                <option value="VIEWER">Auditor / Viewer</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Region Assignment</label>
              <select id="cu-region" class="form-select">
                <option value="">(None / Enterprise)</option>
                ${regions.map(r => `<option value="${r.id}">${r.name}</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Store Assignment</label>
              <select id="cu-store" class="form-select">
                <option value="">(None / Cross-store)</option>
                ${stores.map(s => `<option value="${s.id}">#${s.storeNumber} ${s.name}</option>`).join('')}
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Primary Operational Squad</label>
            <select id="cu-team" class="form-select">
              <option value="">(None)</option>
              ${teams.map(t => `<option value="${t.id}">${t.name} (${t.specialization})</option>`).join('')}
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Create User Profile</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-create-user').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.createUser({
          fullName: document.getElementById('cu-name').value.trim(),
          email: document.getElementById('cu-email').value.trim(),
          password: document.getElementById('cu-pass').value,
          role: document.getElementById('cu-role').value,
          organizationId: state.selectedOrgId,
          regionId: document.getElementById('cu-region').value || null,
          storeId: document.getElementById('cu-store').value || null,
          teamId: document.getElementById('cu-team').value || null
        });
        showToast('User created and scoped.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load user form options: ' + err.message, 'error');
  }
}

async function openEditUserModal(userId, onSuccess) {
  try {
    const [user, regions, stores, teams] = await Promise.all([
      api.getUser(userId),
      api.getRegions(state.selectedOrgId),
      api.getStores(),
      api.getTeams()
    ]);

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Edit User Profile &mdash; ${user.fullName}</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-edit-user">
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Full Name</label>
            <input type="text" id="eu-name" class="form-input" required value="${user.fullName}" />
          </div>
          <div class="form-group">
            <label class="form-label">System Role</label>
            <select id="eu-role" class="form-select" required>
              <option value="ORGANIZATION_ADMIN" ${user.role === 'ORGANIZATION_ADMIN' ? 'selected' : ''}>Organization Admin</option>
              <option value="OPERATIONS_MANAGER" ${user.role === 'OPERATIONS_MANAGER' ? 'selected' : ''}>Operations Manager</option>
              <option value="REGIONAL_MANAGER" ${user.role === 'REGIONAL_MANAGER' ? 'selected' : ''}>Regional VP</option>
              <option value="STORE_MANAGER" ${user.role === 'STORE_MANAGER' ? 'selected' : ''}>Store Manager</option>
              <option value="MAINTENANCE_TEAM" ${user.role === 'MAINTENANCE_TEAM' ? 'selected' : ''}>Maintenance Team Tech</option>
              <option value="ANALYST" ${user.role === 'ANALYST' ? 'selected' : ''}>Operations Analyst</option>
              <option value="VIEWER" ${user.role === 'VIEWER' ? 'selected' : ''}>Auditor / Viewer</option>
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Region Assignment</label>
              <select id="eu-region" class="form-select">
                <option value="">(None / Enterprise)</option>
                ${regions.map(r => `<option value="${r.id}" ${r.id === user.regionId ? 'selected' : ''}>${r.name}</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Store Assignment</label>
              <select id="eu-store" class="form-select">
                <option value="">(None / Cross-store)</option>
                ${stores.map(s => `<option value="${s.id}" ${s.id === user.storeId ? 'selected' : ''}>#${s.storeNumber} ${s.name}</option>`).join('')}
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Primary Operational Squad</label>
            <select id="eu-team" class="form-select">
              <option value="">(None)</option>
              ${teams.map(t => `<option value="${t.id}" ${t.id === user.teamId ? 'selected' : ''}>${t.name}</option>`).join('')}
            </select>
          </div>
          <div class="form-group" style="flex-direction: row; align-items: center; gap: 0.5rem; margin-top: 0.5rem;">
            <input type="checkbox" id="eu-active" ${user.isActive ? 'checked' : ''} />
            <label for="eu-active" class="form-label" style="cursor: pointer; margin: 0;">Account Active & Enabled</label>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Profile Changes</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-edit-user').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.updateUser(userId, {
          fullName: document.getElementById('eu-name').value.trim(),
          role: document.getElementById('eu-role').value,
          regionId: document.getElementById('eu-region').value || null,
          storeId: document.getElementById('eu-store').value || null,
          teamId: document.getElementById('eu-team').value || null,
          isActive: document.getElementById('eu-active').checked
        });
        showToast('User profile updated.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load user: ' + err.message, 'error');
  }
}

// Ownership Mapping Modals
async function openCreateOwnershipModal(onSuccess) {
  try {
    const [stores, teams, users] = await Promise.all([
      api.getStores(),
      api.getTeams(),
      api.getUsers()
    ]);

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Add Operational Ownership Mapping</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-create-mapping">
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Operational Domain</label>
            <select id="cm-domain" class="form-select" required>
              <option value="REFRIGERATION_HVAC">Refrigeration & HVAC</option>
              <option value="POINT_OF_SALE_IT">Point of Sale & IT Infrastructure</option>
              <option value="FACILITIES_SAFETY">Facilities & Physical Safety</option>
              <option value="INVENTORY_LOGISTICS">Cold Chain Logistics & Inventory</option>
              <option value="ENERGY_ELECTRICAL">Energy & Electrical Grid</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Store Scope</label>
            <select id="cm-store" class="form-select">
              <option value="">(Enterprise / Multi-Store Scope)</option>
              ${stores.map(s => `<option value="${s.id}">#${s.storeNumber} ${s.name}</option>`).join('')}
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Primary Assigned Squad</label>
              <select id="cm-primary" class="form-select" required>
                ${teams.map(t => `<option value="${t.id}">${t.name} (${t.specialization})</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Secondary / Fallback Squad</label>
              <select id="cm-secondary" class="form-select">
                <option value="">(None)</option>
                ${teams.map(t => `<option value="${t.id}">${t.name}</option>`).join('')}
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Escalation Owner (User)</label>
            <select id="cm-owner" class="form-select" required>
              ${users.map(u => `<option value="${u.id}">${u.fullName} (${u.role})</option>`).join('')}
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">SLA Target Response (Minutes)</label>
              <input type="number" id="cm-sla" class="form-input" required value="15" />
            </div>
            <div class="form-group">
              <label class="form-label">Auto-Escalation Window (Minutes)</label>
              <input type="number" id="cm-auto" class="form-input" required value="30" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Ownership Mapping</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-create-mapping').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.createOwnershipMapping({
          operationalDomain: document.getElementById('cm-domain').value,
          storeId: document.getElementById('cm-store').value || null,
          primaryTeamId: document.getElementById('cm-primary').value,
          secondaryTeamId: document.getElementById('cm-secondary').value || null,
          escalationOwnerUserId: document.getElementById('cm-owner').value,
          slaResponseMinutes: parseInt(document.getElementById('cm-sla').value) || 15,
          autoEscalateAfterMinutes: parseInt(document.getElementById('cm-auto').value) || 30
        });
        showToast('Operational ownership routing configured.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load ownership form options: ' + err.message, 'error');
  }
}

async function openEditOwnershipModal(mappingId, onSuccess) {
  try {
    const [mappings, teams, users] = await Promise.all([
      api.getOwnershipMappings(),
      api.getTeams(),
      api.getUsers()
    ]);
    const m = mappings.find(item => item.id === mappingId);
    if (!m) return;

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Edit Ownership Mapping</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-edit-mapping">
        <div class="modal-body">
          <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.75rem 1rem; margin-bottom: 0.75rem;">
            <div style="font-size: 0.78rem; color: var(--text-secondary);">Domain Scope:</div>
            <div style="font-weight: 700; color: #fff;">${m.operationalDomain.replace(/_/g, ' ')} (${m.storeName || 'Enterprise'})</div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">Primary Squad</label>
              <select id="em-primary" class="form-select" required>
                ${teams.map(t => `<option value="${t.id}" ${t.id === m.primaryTeamId ? 'selected' : ''}>${t.name}</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Secondary Squad</label>
              <select id="em-secondary" class="form-select">
                <option value="">(None)</option>
                ${teams.map(t => `<option value="${t.id}" ${t.id === m.secondaryTeamId ? 'selected' : ''}>${t.name}</option>`).join('')}
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Escalation Owner (User)</label>
            <select id="em-owner" class="form-select" required>
              ${users.map(u => `<option value="${u.id}" ${u.id === m.escalationOwnerUserId ? 'selected' : ''}>${u.fullName} (${u.role})</option>`).join('')}
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div class="form-group">
              <label class="form-label">SLA Target Response (Minutes)</label>
              <input type="number" id="em-sla" class="form-input" required value="${m.slaResponseMinutes}" />
            </div>
            <div class="form-group">
              <label class="form-label">Auto-Escalation Window (Minutes)</label>
              <input type="number" id="em-auto" class="form-input" required value="${m.autoEscalateAfterMinutes}" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Update Mapping</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-edit-mapping').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.updateOwnershipMapping(mappingId, {
          primaryTeamId: document.getElementById('em-primary').value,
          secondaryTeamId: document.getElementById('em-secondary').value || null,
          escalationOwnerUserId: document.getElementById('em-owner').value,
          slaResponseMinutes: parseInt(document.getElementById('em-sla').value) || 15,
          autoEscalateAfterMinutes: parseInt(document.getElementById('em-auto').value) || 30
        });
        showToast('Ownership mapping updated.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load mapping: ' + err.message, 'error');
  }
}

// Custom Role Modal
async function openCreateRoleModal(onSuccess) {
  try {
    const matrix = await api.getPermissionsMatrix();
    const allPerms = [];
    Object.values(matrix.categories).forEach(catPerms => {
      catPerms.forEach(p => allPerms.push(p));
    });

    openModal(`
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; font-weight: 700;">Create Custom Operational Role</h3>
        <button class="btn btn-secondary btn-sm" id="btn-close-modal">✕</button>
      </div>
      <form id="form-create-role">
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Role Identifier Name</label>
            <input type="text" id="cr-name" class="form-input" required placeholder="e.g. STORE_SAFETY_LEAD" />
          </div>
          <div class="form-group">
            <label class="form-label">Role Description</label>
            <textarea id="cr-desc" class="form-textarea" placeholder="Supervises fire, hazard, and temperature health compliance..."></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">Granted Permissions</label>
            <div style="max-height: 220px; overflow-y: auto; background-color: var(--bg-secondary); border: 1px solid var(--border-medium); border-radius: var(--radius-md); padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;">
              ${allPerms.map(p => `
                <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; cursor: pointer;">
                  <input type="checkbox" class="cb-perm" value="${p.permissionKey}" />
                  <span><strong>${p.label}</strong> &mdash; <span style="color: var(--text-muted);">${p.description}</span></span>
                </label>
              `).join('')}
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" id="btn-cancel-modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Create Role</button>
        </div>
      </form>
    `);

    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

    document.getElementById('form-create-role').addEventListener('submit', async (e) => {
      e.preventDefault();
      const perms = Array.from(document.querySelectorAll('.cb-perm:checked')).map(cb => cb.value);
      try {
        await api.createRole({
          name: document.getElementById('cr-name').value.trim().toUpperCase(),
          description: document.getElementById('cr-desc').value.trim(),
          permissions: perms
        });
        showToast('Custom role created.', 'success');
        closeModal();
        if (onSuccess) onSuccess();
      } catch (err) {}
    });
  } catch (err) {
    showToast('Failed to load permissions: ' + err.message, 'error');
  }
}
