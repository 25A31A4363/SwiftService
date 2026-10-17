/**
 * R5 Operational Intelligence Platform - RBAC & Role Presets
 */

export const ROLE_PRESETS = [
  {
    role: 'ORGANIZATION_ADMIN',
    email: 'orgadmin@apex.com',
    title: 'Org Admin',
    desc: 'Unrestricted enterprise control & config'
  },
  {
    role: 'OPERATIONS_MANAGER',
    email: 'opsmanager@apex.com',
    title: 'Operations Manager',
    desc: 'Cross-store operational triage & routing'
  },
  {
    role: 'REGIONAL_MANAGER',
    email: 'regmanager@apex.com',
    title: 'Regional VP (PNW)',
    desc: 'Regional stores oversight & escalation'
  },
  {
    role: 'STORE_MANAGER',
    email: 'storemanager@apex.com',
    title: 'Store Lead (Store 104)',
    desc: 'Store dispatch, human approvals & overrides'
  },
  {
    role: 'MAINTENANCE_TEAM',
    email: 'maintenance@apex.com',
    title: 'Senior HVAC Tech',
    desc: 'Work order execution & repair resolution'
  },
  {
    role: 'ANALYST',
    email: 'analyst@apex.com',
    title: 'Operations Analyst',
    desc: 'Incident analytics & feedback auditing'
  },
  {
    role: 'VIEWER',
    email: 'viewer@apex.com',
    title: 'Store Auditor',
    desc: 'Read-only visibility across metrics'
  },
  {
    role: 'CUSTOMER',
    email: 'customer@retailwave.com',
    title: 'Sarah Jenkins (Customer)',
    desc: 'Swift Service customer portal, complaint filing & tracking'
  }
];

export const NAV_SECTIONS = [
  { id: 'core', label: 'Core Operational Intelligence' },
  { id: 'intervention', label: 'Intervention & Verification' },
  { id: 'platform', label: 'Enterprise Platform' }
];

export const NAV_ITEMS = [
  // 1. Core Operational Journey (R5)
  {
    id: 'dashboard',
    section: 'core',
    label: 'Command Center',
    icon: '📊',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'customer-complaints',
    section: 'core',
    label: 'Customer Complaints',
    icon: '💬',
    highlight: true,
    badgeText: 'PORTAL',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'demo',
    section: 'core',
    label: 'E2E Lifecycle Demo',
    icon: '🚀',
    highlight: true,
    badgeText: '15 STAGES',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'feedback',
    section: 'core',
    label: 'Feedback Ingestion',
    icon: '📥',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'issues',
    section: 'core',
    label: 'Issues & Incidents',
    icon: '⚠️',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'clusters',
    section: 'core',
    label: 'Semantic Clusters',
    icon: '🗂️',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },

  // 2. Intervention & Verification
  {
    id: 'alerts',
    section: 'intervention',
    label: 'Emerging Alerts',
    icon: '🔔',
    minRole: 'MAINTENANCE_TEAM',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'actions',
    section: 'intervention',
    label: 'Actions & Approvals',
    icon: '🛠️',
    minRole: 'MAINTENANCE_TEAM',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'outcomes',
    section: 'intervention',
    label: 'Outcome Intelligence',
    icon: '🎯',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'briefs',
    section: 'intervention',
    label: 'Executive Briefs',
    icon: '📋',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },

  // 3. Enterprise Administration
  {
    id: 'org-hierarchy',
    section: 'platform',
    label: 'Org & Stores',
    icon: '🏢',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'teams',
    section: 'platform',
    label: 'Teams & Skills',
    icon: '👥',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'users',
    section: 'platform',
    label: 'User Directory',
    icon: '👤',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'ownership',
    section: 'platform',
    label: 'Ownership & Trace',
    icon: '🧭',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'roles',
    section: 'platform',
    label: 'Role Permissions',
    icon: '🛡️',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  },
  {
    id: 'audit',
    section: 'platform',
    label: 'Audit & Governance',
    icon: '📜',
    minRole: 'ANALYST',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'ANALYST']
  },
  {
    id: 'personal-home',
    section: 'platform',
    label: 'Personal / Home (Ext)',
    icon: '🏠',
    minRole: 'VIEWER',
    allowedRoles: ['ORGANIZATION_ADMIN', 'OPERATIONS_MANAGER', 'REGIONAL_MANAGER', 'STORE_MANAGER', 'MAINTENANCE_TEAM', 'ANALYST', 'VIEWER']
  }
];


export function canAccessView(userRole, viewId) {
  const item = NAV_ITEMS.find(n => n.id === viewId);
  if (!item) return false;
  return item.allowedRoles.includes(userRole);
}
