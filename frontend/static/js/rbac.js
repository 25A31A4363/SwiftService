/**
 * R5 Operational Intelligence Platform - RBAC & Role Presets
 */

export const ROLE_PRESETS = [
  {
    role: 'ORGANIZATION_ADMIN',
    email: 'orgadmin@apex.com',
    title: 'Organization Admin',
    desc: 'Enterprise-wide operations, store management & complaint triage'
  },
  {
    role: 'STORE_MANAGER',
    email: 'storemanager@apex.com',
    title: 'Store Manager',
    desc: 'Store operations, complaint triage & staff resolution actions'
  },
  {
    role: 'CUSTOMER',
    email: 'customer@retailwave.com',
    title: 'Customer',
    desc: 'Submit complaints, track status & view resolution timeline'
  }
];

export const NAV_SECTIONS = [
  { id: 'core', label: 'Core Operational Intelligence' },
  { id: 'intervention', label: 'Intervention & Verification' },
  { id: 'platform', label: 'Enterprise Platform' }
];

export const NAV_ITEMS = [
  // 1. Core Operational Journey
  {
    id: 'dashboard',
    section: 'core',
    label: 'Command Center',
    icon: '📊',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'customer-complaints',
    section: 'core',
    label: 'Customer Complaints',
    icon: '💬',
    highlight: true,
    badgeText: 'TRIAGE',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'demo',
    section: 'core',
    label: 'E2E Lifecycle Demo',
    icon: '🚀',
    highlight: true,
    badgeText: '15 STAGES',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'feedback',
    section: 'core',
    label: 'Feedback Ingestion',
    icon: '📥',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'issues',
    section: 'core',
    label: 'Issues & Incidents',
    icon: '⚠️',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'clusters',
    section: 'core',
    label: 'Semantic Clusters',
    icon: '🗂️',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },

  // 2. Intervention & Verification
  {
    id: 'alerts',
    section: 'intervention',
    label: 'Emerging Alerts',
    icon: '🔔',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'actions',
    section: 'intervention',
    label: 'Actions & Approvals',
    icon: '🛠️',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'outcomes',
    section: 'intervention',
    label: 'Outcome Intelligence',
    icon: '🎯',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'briefs',
    section: 'intervention',
    label: 'Executive Briefs',
    icon: '📋',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },

  // 3. Enterprise Administration
  {
    id: 'org-hierarchy',
    section: 'platform',
    label: 'Org & Stores',
    icon: '🏢',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'teams',
    section: 'platform',
    label: 'Teams & Skills',
    icon: '👥',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  },
  {
    id: 'users',
    section: 'platform',
    label: 'User Directory',
    icon: '👤',
    allowedRoles: ['ORGANIZATION_ADMIN']
  },
  {
    id: 'ownership',
    section: 'platform',
    label: 'Ownership & Trace',
    icon: '🧭',
    allowedRoles: ['ORGANIZATION_ADMIN']
  },
  {
    id: 'roles',
    section: 'platform',
    label: 'Role Permissions',
    icon: '🛡️',
    allowedRoles: ['ORGANIZATION_ADMIN']
  },
  {
    id: 'audit',
    section: 'platform',
    label: 'Audit & Governance',
    icon: '📜',
    allowedRoles: ['ORGANIZATION_ADMIN']
  },
  {
    id: 'personal-home',
    section: 'platform',
    label: 'Personal / Home',
    icon: '🏠',
    allowedRoles: ['ORGANIZATION_ADMIN', 'STORE_MANAGER']
  }
];


export function canAccessView(userRole, viewId) {
  const item = NAV_ITEMS.find(n => n.id === viewId);
  if (!item) return false;
  return item.allowedRoles.includes(userRole);
}
