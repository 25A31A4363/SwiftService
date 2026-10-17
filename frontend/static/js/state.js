/**
 * Swift Service - Global State Store
 */

export const state = {
  token: localStorage.getItem('r5_token') || null,
  user: JSON.parse(localStorage.getItem('r5_user') || 'null'),
  
  // Enterprise Context
  selectedOrgId: null,
  selectedRegionId: null,
  selectedStoreId: null,

  // Hierarchy Data
  organizations: [],
  regions: [],
  stores: [],
  teams: [],

  // Active View & Portal Mode
  currentView: 'dashboard', // 'dashboard' | 'feedback' | 'issues' | 'alerts' | 'actions' | 'audit' | 'personal-home' | 'customer-complaints'
  currentPortalMode: localStorage.getItem('r5_portal_mode') || 'CUSTOMER', // 'CUSTOMER' | 'OPS'

  // Counters
  activeAlertsCount: 0,
  p1Count: 0,

  listeners: [],

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  },

  notify() {
    this.listeners.forEach(fn => fn(this));
  },

  setAuth(token, user) {
    this.token = token;
    this.user = user;
    if (token) {
      localStorage.setItem('r5_token', token);
      localStorage.setItem('r5_user', JSON.stringify(user));
      if (user.storeId) this.selectedStoreId = user.storeId;
      if (user.regionId) this.selectedRegionId = user.regionId;
      if (user.organizationId) this.selectedOrgId = user.organizationId;
    } else {
      localStorage.removeItem('r5_token');
      localStorage.removeItem('r5_user');
      this.user = null;
    }
    this.notify();
  },

  setContext(orgId, regionId, storeId) {
    if (orgId !== undefined) this.selectedOrgId = orgId;
    if (regionId !== undefined) this.selectedRegionId = regionId;
    if (storeId !== undefined) this.selectedStoreId = storeId;
    this.notify();
  },

  setView(viewName) {
    this.currentView = viewName;
    this.notify();
  },

  setPortalMode(mode) {
    this.currentPortalMode = mode;
    localStorage.setItem('r5_portal_mode', mode);
    this.notify();
  }
};
