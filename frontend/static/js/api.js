/**
 * R5 Operational Intelligence Platform - Client API Service
 */
import { state } from './state.js';
import { mockBackend } from './mock-backend.js';

const API_BASE = '/api/v1';

// Detect if running on static hosting environments (Netlify, GitHub Pages, or local file)
const isStaticHost = typeof window !== 'undefined' && (
  window.location.hostname.includes('netlify.app') ||
  window.location.hostname.includes('github.io') ||
  window.location.hostname.includes('surge.sh') ||
  window.location.protocol === 'file:'
);

let forceMockBackend = isStaticHost;

export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
  toast.innerHTML = `
    <span style="font-size: 1.1rem;">${icon}</span>
    <div style="flex: 1;">
      <div style="font-weight: 600; font-size: 0.85rem; color: #fff;">${type.toUpperCase()}</div>
      <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">${message}</div>
    </div>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 200ms ease';
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}

export async function apiRequest(endpoint, options = {}) {
  // If static hosting detected or live backend unavailable, engage mock backend directly
  if (forceMockBackend) {
    return await mockBackend.handleRequest(endpoint, options);
  }

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  const url = `${API_BASE}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers
    });

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      // Returned HTML or static fallback rewrite
      console.warn(`[R5 Platform] API endpoint ${endpoint} returned non-JSON. Falling back to autonomous client engine.`);
      forceMockBackend = true;
      return await mockBackend.handleRequest(endpoint, options);
    }

    const json = await response.json();

    if (!response.ok || !json.success) {
      if (response.status === 404) {
        console.warn(`[R5 Platform] Endpoint ${endpoint} returned 404. Falling back to autonomous client engine.`);
        return await mockBackend.handleRequest(endpoint, options);
      }

      const errMessage = json?.error?.message || `HTTP Error ${response.status}`;
      if (response.status === 401 && state.token) {
        showToast('Session expired. Please re-authenticate.', 'error');
        state.setAuth(null, null);
      } else {
        showToast(errMessage, 'error');
      }
      throw new Error(errMessage);
    }

    return json.data;
  } catch (err) {
    // If network failure or backend not responding, fallback to mock backend
    if (err.name === 'TypeError' || err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError') || err.message?.includes('JSON')) {
      console.warn(`[R5 Platform] Live backend unreachable for ${endpoint}. Falling back to autonomous client engine.`);
      forceMockBackend = true;
      return await mockBackend.handleRequest(endpoint, options);
    }

    if (!endpoint.includes('/auth/login')) {
      console.error(`API Error on ${endpoint}:`, err);
    }
    throw err;
  }
}

export const api = {
  // Auth
  login: (email, password) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  getMe: () => apiRequest('/auth/me'),
  updateProfile: (payload) => apiRequest('/auth/me', { method: 'PUT', body: JSON.stringify(payload) }),
  changePassword: (payload) => apiRequest('/auth/change-password', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => apiRequest('/auth/logout', { method: 'POST' }),

  // Hierarchy - Organizations
  getOrganizations: (q, status) => {
    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (status) params.append('status', status);
    return apiRequest(`/organizations${params.toString() ? `?${params.toString()}` : ''}`);
  },
  createOrganization: (payload) => apiRequest('/organizations', { method: 'POST', body: JSON.stringify(payload) }),
  updateOrganization: (id, payload) => apiRequest(`/organizations/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteOrganization: (id) => apiRequest(`/organizations/${id}`, { method: 'DELETE' }),

  // Hierarchy - Regions
  getRegions: (orgId, q) => {
    const params = new URLSearchParams();
    if (orgId) params.append('organizationId', orgId);
    if (q) params.append('q', q);
    return apiRequest(`/regions${params.toString() ? `?${params.toString()}` : ''}`);
  },
  createRegion: (payload) => apiRequest('/regions', { method: 'POST', body: JSON.stringify(payload) }),
  updateRegion: (id, payload) => apiRequest(`/regions/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteRegion: (id) => apiRequest(`/regions/${id}`, { method: 'DELETE' }),

  // Hierarchy - Stores
  getStores: (orgId, regId, status, q) => {
    const params = new URLSearchParams();
    if (orgId) params.append('organizationId', orgId);
    if (regId) params.append('regionId', regId);
    if (status) params.append('operatingStatus', status);
    if (q) params.append('q', q);
    return apiRequest(`/stores?${params.toString()}`);
  },
  getStore: (id) => apiRequest(`/stores/${id}`),
  createStore: (payload) => apiRequest('/stores', { method: 'POST', body: JSON.stringify(payload) }),
  updateStore: (id, payload) => apiRequest(`/stores/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  updateStoreStatus: (id, operatingStatus, justification) => apiRequest(`/stores/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ operatingStatus, justification })
  }),
  deleteStore: (id) => apiRequest(`/stores/${id}`, { method: 'DELETE' }),

  getDepartments: (storeId) => apiRequest(`/departments?storeId=${storeId}`),
  getAssets: (storeId) => apiRequest(`/assets?storeId=${storeId}`),

  // Operational Teams & Members
  getTeams: (storeId, regionId, specialization, q) => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (regionId) params.append('regionId', regionId);
    if (specialization) params.append('specialization', specialization);
    if (q) params.append('q', q);
    return apiRequest(`/teams${params.toString() ? `?${params.toString()}` : ''}`);
  },
  getTeam: (id) => apiRequest(`/teams/${id}`),
  createTeam: (payload) => apiRequest('/teams', { method: 'POST', body: JSON.stringify(payload) }),
  updateTeam: (id, payload) => apiRequest(`/teams/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteTeam: (id) => apiRequest(`/teams/${id}`, { method: 'DELETE' }),
  getTeamMembers: (teamId) => apiRequest(`/teams/${teamId}/members`),
  addTeamMember: (teamId, payload) => apiRequest(`/teams/${teamId}/members`, { method: 'POST', body: JSON.stringify(payload) }),
  removeTeamMember: (teamId, userId) => apiRequest(`/teams/${teamId}/members/${userId}`, { method: 'DELETE' }),

  // User Management
  getUsers: (role, storeId, q) => {
    const params = new URLSearchParams();
    if (role) params.append('role', role);
    if (storeId) params.append('storeId', storeId);
    if (q) params.append('q', q);
    return apiRequest(`/users${params.toString() ? `?${params.toString()}` : ''}`);
  },
  getUser: (id) => apiRequest(`/users/${id}`),
  createUser: (payload) => apiRequest('/users', { method: 'POST', body: JSON.stringify(payload) }),
  updateUser: (id, payload) => apiRequest(`/users/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteUser: (id) => apiRequest(`/users/${id}`, { method: 'DELETE' }),

  // Roles & Permissions Matrix
  getRoles: () => apiRequest('/roles'),
  getPermissionsMatrix: () => apiRequest('/roles/permissions-matrix'),
  createRole: (payload) => apiRequest('/roles', { method: 'POST', body: JSON.stringify(payload) }),
  updateRolePermissions: (roleId, permissions) => apiRequest(`/roles/${roleId}/permissions`, {
    method: 'PUT',
    body: JSON.stringify({ permissions })
  }),
  deleteRole: (roleId) => apiRequest(`/roles/${roleId}`, { method: 'DELETE' }),

  // Operational Ownership Mappings
  getOwnershipMappings: (storeId, domain, q) => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (domain) params.append('domain', domain);
    if (q) params.append('q', q);
    return apiRequest(`/ownership-mappings${params.toString() ? `?${params.toString()}` : ''}`);
  },
  createOwnershipMapping: (payload) => apiRequest('/ownership-mappings', { method: 'POST', body: JSON.stringify(payload) }),
  updateOwnershipMapping: (id, payload) => apiRequest(`/ownership-mappings/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteOwnershipMapping: (id) => apiRequest(`/ownership-mappings/${id}`, { method: 'DELETE' }),

  // Hierarchy Lineage & Operational Tracing
  traceOperationalObject: (paramsObj = {}) => {
    const params = new URLSearchParams();
    if (paramsObj.storeId) params.append('storeId', paramsObj.storeId);
    if (paramsObj.domain) params.append('domain', paramsObj.domain);
    if (paramsObj.entityType) params.append('entityType', paramsObj.entityType);
    if (paramsObj.entityId) params.append('entityId', paramsObj.entityId);
    return apiRequest(`/hierarchy/trace${params.toString() ? `?${params.toString()}` : ''}`);
  },

  // Feedback (Phase 3 Multichannel Ingestion)
  getFeedback: (filterParams = {}) => {
    const params = new URLSearchParams();
    if (typeof filterParams === 'string') {
      params.append('storeId', filterParams);
    } else if (filterParams) {
      if (filterParams.storeId) params.append('storeId', filterParams.storeId);
      if (filterParams.regionId) params.append('regionId', filterParams.regionId);
      if (filterParams.departmentId) params.append('departmentId', filterParams.departmentId);
      if (filterParams.channelType) params.append('channelType', filterParams.channelType);
      if (filterParams.processingStatus) params.append('processingStatus', filterParams.processingStatus);
      if (filterParams.submitterType) params.append('submitterType', filterParams.submitterType);
      if (filterParams.languageCode) params.append('languageCode', filterParams.languageCode);
      if (filterParams.q) params.append('q', filterParams.q);
      if (filterParams.page) params.append('page', filterParams.page);
      if (filterParams.limit) params.append('limit', filterParams.limit);
    }
    return apiRequest(`/feedback${params.toString() ? `?${params.toString()}` : ''}`);
  },
  getFeedbackById: (id) => apiRequest(`/feedback/${id}`),
  submitFeedback: (payload) => apiRequest('/feedback', { method: 'POST', body: JSON.stringify(payload) }),
  submitBulkFeedbackJson: (payload) => apiRequest('/feedback/bulk', { method: 'POST', body: JSON.stringify(payload) }),
  submitBulkFeedbackCsv: (csvText, storeId) => apiRequest(`/feedback/bulk/csv${storeId ? `?storeId=${storeId}` : ''}`, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: csvText
  }),
  updateFeedbackStatus: (id, payload) => apiRequest(`/feedback/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }),
  getFeedbackUnderstanding: (id) => apiRequest(`/feedback/${id}/understanding`),
  reviewFeedbackWithOverrides: (id, payload) => apiRequest(`/feedback/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  reanalyzeFeedback: (id) => apiRequest(`/feedback/${id}/analyze`, {
    method: 'POST'
  }),
  submitFollowUp: (payload) => apiRequest('/feedback/follow-up', { method: 'POST', body: JSON.stringify(payload) }),

  // Issues
  getIssues: (storeId, status, priorityTier) => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (status) params.append('status', status);
    if (priorityTier) params.append('priorityTier', priorityTier);
    return apiRequest(`/issues?${params.toString()}`);
  },
  getIssue: (id) => apiRequest(`/issues/${id}`),
  getIssueEvidence: (id) => apiRequest(`/issues/${id}/evidence`),
  createIssue: (payload) => apiRequest('/issues', { method: 'POST', body: JSON.stringify(payload) }),
  updateIssueStatus: (id, status, justification) => apiRequest(`/issues/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, justification })
  }),
  overridePriority: (id, newPriorityScore, justification) => apiRequest(`/issues/${id}/override-priority`, {
    method: 'POST',
    body: JSON.stringify({ newPriorityScore, justification })
  }),

  // Alerts (Phase 7 Enhanced)
  getAlerts: (storeId, status) => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (status) params.append('status', status);
    return apiRequest(`/alerts${params.toString() ? `?${params.toString()}` : ''}`);
  },
  getAlertById: (id) => apiRequest(`/alerts/${id}`),
  detectEmergingIssues: (payload = {}) => apiRequest('/alerts/detect', { method: 'POST', body: JSON.stringify(payload) }),
  acknowledgeAlert: (id) => apiRequest(`/alerts/${id}/acknowledge`, { method: 'POST' }),
  escalateAlert: (id, targetTeamId, notes) => apiRequest(`/alerts/${id}/escalate`, {
    method: 'POST',
    body: JSON.stringify({ targetTeamId, notes })
  }),
  dismissAlert: (id, reason) => apiRequest(`/alerts/${id}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),
  getAlertEvidence: (id) => apiRequest(`/alerts/${id}/evidence`),

  // Dynamic Investigation (Phase 5)
  getFeedbackInvestigation: (feedbackId) => apiRequest(`/investigation/feedback/${feedbackId}`),
  answerInvestigationQuestion: (questionId, answer) => apiRequest(`/investigation/questions/${questionId}/answer`, {
    method: 'POST',
    body: JSON.stringify({ answer })
  }),
  addCustomInvestigationQuestion: (feedbackId, questionText, reason, options) => apiRequest(`/investigation/feedback/${feedbackId}/custom-question`, {
    method: 'POST',
    body: JSON.stringify({ questionText, reason, options })
  }),
  dismissInvestigationQuestion: (questionId, reason) => apiRequest(`/investigation/questions/${questionId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),
  enrichAndReanalyzeFeedback: (feedbackId) => apiRequest(`/investigation/feedback/${feedbackId}/enrich-reanalyze`, {
    method: 'POST'
  }),

  // Semantic Clustering (Phase 6)
  getClusters: (storeId, status = 'ACTIVE') => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (status) params.append('status', status);
    return apiRequest(`/clusters${params.toString() ? `?${params.toString()}` : ''}`);
  },
  getCluster: (id) => apiRequest(`/clusters/${id}`),
  discoverClusters: (payload = {}) => apiRequest('/clusters/discover', { method: 'POST', body: JSON.stringify(payload) }),
  mergeClusters: (primaryClusterId, secondaryClusterId, mergedTitle, justification) => apiRequest('/clusters/merge', {
    method: 'POST',
    body: JSON.stringify({ primaryClusterId, secondaryClusterId, mergedTitle, justification })
  }),
  splitCluster: (clusterId, feedbackItemIdsToEject, newClusterTitle, justification) => apiRequest(`/clusters/${clusterId}/split`, {
    method: 'POST',
    body: JSON.stringify({ feedbackItemIdsToEject, newClusterTitle, justification })
  }),
  updateCluster: (clusterId, payload) => apiRequest(`/clusters/${clusterId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }),

  // Prioritization & Explainability (Phase 8)
  recalculateIssuePriority: (issueId) => apiRequest(`/issues/${issueId}/recalculate-priority`, { method: 'POST' }),

  // Lineage Graph & Citations (Phase 9)
  getIssueLineage: (issueId) => apiRequest(`/lineage/issue/${issueId}`),

  // Intelligent Operational Routing (Phase 10)
  routeIssue: (issueId) => apiRequest(`/routing/issues/${issueId}/route`, { method: 'POST' }),
  reassignIssue: (issueId, payload) => apiRequest(`/routing/issues/${issueId}/reassign`, {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  escalateIssue: (issueId, payload) => apiRequest(`/routing/issues/${issueId}/escalate`, {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getIssueRoutingHistory: (issueId) => apiRequest(`/routing/issues/${issueId}/history`),
  getTriageQueue: (storeId) => apiRequest(`/routing/triage-queue${storeId ? `?storeId=${storeId}` : ''}`),
  simulateRouting: (payload) => apiRequest('/routing/simulate', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  // Actions
  getActions: (issueId) => apiRequest(`/actions${issueId ? `?issueId=${issueId}` : ''}`),
  approveAction: (id, decision, justification) => apiRequest(`/actions/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ decision, justification })
  }),
  overrideRouting: (id, newTargetTeamId, overrideReason) => apiRequest(`/actions/${id}/override`, {
    method: 'POST',
    body: JSON.stringify({ newTargetTeamId, overrideReason })
  }),

  // Resolutions
  getResolutions: (issueId) => apiRequest(`/resolutions/issue/${issueId}`),
  createResolution: (payload) => apiRequest('/resolutions', { method: 'POST', body: JSON.stringify(payload) }),

  // Audit Logs
  getAuditLogs: (entityType, entityId) => {
    const params = new URLSearchParams();
    if (entityType) params.append('entityType', entityType);
    if (entityId) params.append('entityId', entityId);
    return apiRequest(`/audit-logs?${params.toString()}`);
  },

  // Personal / Home Mode (Segregated)
  getHomeAppliances: () => apiRequest('/personal-home/appliances'),
  registerHomeAppliance: (payload) => apiRequest('/personal-home/appliances', { method: 'POST', body: JSON.stringify(payload) }),
  getHomeTickets: () => apiRequest('/personal-home/tickets'),
  createHomeTicket: (payload) => apiRequest('/personal-home/tickets', { method: 'POST', body: JSON.stringify(payload) }),

  // Phase 12: Post-Intervention Outcome Measurement
  getOutcomesDashboard: (storeId) => apiRequest(`/outcomes/dashboard${storeId ? `?storeId=${storeId}` : ''}`),
  getOutcomes: (storeId, outcomeStatus) => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (outcomeStatus) params.append('outcomeStatus', outcomeStatus);
    const qs = params.toString();
    return apiRequest(`/outcomes${qs ? `?${qs}` : ''}`);
  },
  getIssueOutcome: (issueId) => apiRequest(`/outcomes/issues/${issueId}`),
  evaluateIssueOutcome: (issueId, payload) => apiRequest(`/outcomes/issues/${issueId}/evaluate`, {
    method: 'POST',
    body: JSON.stringify(payload || {})
  }),
  captureBaselineSnapshot: (issueId) => apiRequest(`/outcomes/issues/${issueId}/baseline`, {
    method: 'POST'
  }),

  // Phase 14: AI Operational Intelligence Briefs
  getLatestBrief: (storeId, timeframeType) => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (timeframeType) params.append('timeframeType', timeframeType);
    const qs = params.toString();
    return apiRequest(`/briefs/latest${qs ? `?${qs}` : ''}`);
  },
  getBriefById: (briefId) => apiRequest(`/briefs/${briefId}`),
  listBriefs: (storeId, limit = 50) => {
    const params = new URLSearchParams();
    if (storeId) params.append('storeId', storeId);
    if (limit) params.append('limit', limit);
    const qs = params.toString();
    return apiRequest(`/briefs${qs ? `?${qs}` : ''}`);
  },
  generateBrief: (payload) => apiRequest('/briefs/generate', {
    method: 'POST',
    body: JSON.stringify(payload || {})
  }),

  // Phase 15: Multilingual Operational Intelligence Hardening
  parseMultilingualText: (text, languageHint) => apiRequest('/multilingual/parse', {
    method: 'POST',
    body: JSON.stringify({ text, languageHint })
  }),
  getMultilingualBenchmark: () => apiRequest('/multilingual/benchmark'),
  getMultilingualTestCases: () => apiRequest('/multilingual/test-cases'),

  // Phase 21: Complete End-to-End Demonstration
  getDemoScenario: () => apiRequest('/demo/scenario'),
  runDemo: (autoAdvance = true) => apiRequest('/demo/run', {
    method: 'POST',
    body: JSON.stringify({ autoAdvance })
  }),
  getDemoStatus: () => apiRequest('/demo/status'),
  resetDemo: () => apiRequest('/demo/reset', {
    method: 'POST'
  }),

  // Customer Authentication & Email Verification
  registerCustomer: (payload) => apiRequest('/auth/customer/register', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  verifyCustomerOtp: (payload) => apiRequest('/auth/customer/verify-otp', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  resendCustomerOtp: (payload) => apiRequest('/auth/customer/resend-otp', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  // Customer Complaints & Public Tracking
  submitComplaint: (payload) => apiRequest('/complaints', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getMyComplaints: () => apiRequest('/complaints/my'),
  trackComplaint: (referenceNumber) => apiRequest(`/complaints/track/${encodeURIComponent(referenceNumber)}`),
  getComplaintById: (id) => apiRequest(`/complaints/${id}`),
  listComplaints: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/complaints${qs ? `?${qs}` : ''}`);
  },
  updateComplaintStatus: (id, payload) => apiRequest(`/complaints/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }),
  uploadComplaintAttachment: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    if (forceMockBackend) {
      return await mockBackend.handleRequest('/complaints/upload', { method: 'POST', body: formData });
    }
    const headers = {};
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const res = await fetch(`${API_BASE}/complaints/upload`, {
      method: 'POST',
      headers,
      body: formData
    });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error(json.error?.message || 'File upload failed');
    return json.data;
  }
};

