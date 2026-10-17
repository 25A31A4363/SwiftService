import { RoleName } from './domain';

export type Permission =
  // Organization & Structure
  | 'org:read'
  | 'org:manage'
  | 'region:read'
  | 'region:manage'
  | 'store:read'
  | 'store:manage'
  | 'team:read'
  | 'team:manage'
  | 'user:read'
  | 'user:manage'
  
  // Operational Feedback & Issues
  | 'feedback:read'
  | 'feedback:submit'
  | 'feedback:export'
  
  // Issues & Incidents
  | 'issue:read'
  | 'issue:triage'
  | 'issue:assign'
  | 'issue:override'
  | 'issue:close'
  
  // Alerts
  | 'alert:read'
  | 'alert:acknowledge'
  
  // Actions & Approvals
  | 'action:read'
  | 'action:approve'
  | 'action:reject'
  | 'action:override'
  | 'action:execute'
  
  // Resolutions & Outcomes
  | 'resolution:read'
  | 'resolution:create'
  | 'resolution:verify'
  
  // Audits & Analytics
  | 'audit:read'
  | 'analytics:read'
  | 'analytics:export';

export const ROLE_PERMISSIONS: Record<RoleName, readonly Permission[]> = {
  ORGANIZATION_ADMIN: [
    'org:read', 'org:manage',
    'region:read', 'region:manage',
    'store:read', 'store:manage',
    'team:read', 'team:manage',
    'user:read', 'user:manage',
    'feedback:read', 'feedback:submit', 'feedback:export',
    'issue:read', 'issue:triage', 'issue:assign', 'issue:override', 'issue:close',
    'alert:read', 'alert:acknowledge',
    'action:read', 'action:approve', 'action:reject', 'action:override', 'action:execute',
    'resolution:read', 'resolution:create', 'resolution:verify',
    'audit:read', 'analytics:read', 'analytics:export'
  ],
  OPERATIONS_MANAGER: [
    'org:read',
    'region:read', 'region:manage',
    'store:read', 'store:manage',
    'team:read', 'team:manage',
    'user:read',
    'feedback:read', 'feedback:submit', 'feedback:export',
    'issue:read', 'issue:triage', 'issue:assign', 'issue:override', 'issue:close',
    'alert:read', 'alert:acknowledge',
    'action:read', 'action:approve', 'action:reject', 'action:override', 'action:execute',
    'resolution:read', 'resolution:create', 'resolution:verify',
    'audit:read', 'analytics:read', 'analytics:export'
  ],
  REGIONAL_MANAGER: [
    'org:read',
    'region:read',
    'store:read',
    'team:read',
    'user:read',
    'feedback:read', 'feedback:submit', 'feedback:export',
    'issue:read', 'issue:triage', 'issue:assign', 'issue:override', 'issue:close',
    'alert:read', 'alert:acknowledge',
    'action:read', 'action:approve', 'action:reject', 'action:override',
    'resolution:read', 'resolution:verify',
    'audit:read', 'analytics:read', 'analytics:export'
  ],
  STORE_MANAGER: [
    'org:read',
    'region:read',
    'store:read',
    'team:read',
    'feedback:read', 'feedback:submit',
    'issue:read', 'issue:triage', 'issue:assign', 'issue:override',
    'alert:read', 'alert:acknowledge',
    'action:read', 'action:approve', 'action:reject', 'action:override', 'action:execute',
    'resolution:read', 'resolution:create', 'resolution:verify',
    'audit:read', 'analytics:read'
  ],
  MAINTENANCE_TEAM: [
    'store:read',
    'team:read',
    'feedback:read', 'feedback:submit',
    'issue:read',
    'alert:read', 'alert:acknowledge',
    'action:read', 'action:execute',
    'resolution:read', 'resolution:create'
  ],
  ANALYST: [
    'org:read',
    'region:read',
    'store:read',
    'team:read',
    'feedback:read', 'feedback:export',
    'issue:read',
    'alert:read',
    'action:read',
    'resolution:read',
    'audit:read', 'analytics:read', 'analytics:export'
  ],
  VIEWER: [
    'org:read',
    'region:read',
    'store:read',
    'feedback:read',
    'issue:read',
    'alert:read',
    'action:read',
    'resolution:read',
    'analytics:read'
  ]
};

export function hasPermission(role: RoleName, permission: Permission): boolean {
  const permissions = ROLE_PERMISSIONS[role];
  return Boolean(permissions && permissions.includes(permission));
}

export function canAccessStore(user: { role: RoleName; storeId?: string | null; regionId?: string | null }, targetStore: { id: string; regionId: string }): boolean {
  if (user.role === 'ORGANIZATION_ADMIN' || user.role === 'OPERATIONS_MANAGER' || user.role === 'ANALYST' || user.role === 'VIEWER') {
    return true;
  }
  if (user.role === 'REGIONAL_MANAGER') {
    return user.regionId === targetStore.regionId;
  }
  if (user.role === 'STORE_MANAGER' || user.role === 'MAINTENANCE_TEAM') {
    return user.storeId === targetStore.id;
  }
  return false;
}
