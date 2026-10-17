/**
 * Swift Service - Shared Enterprise UI Utilities
 * Reusable components for empty states, skeleton loaders, error states, and XSS sanitization.
 */

export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function renderEmptyStateHtml({
  icon = '📭',
  title = 'No records found',
  desc = 'There are no active records in this view.',
  actionLabel = '',
  actionId = ''
} = {}) {
  return `
    <div class="r5-empty-state" role="status" aria-live="polite">
      <div class="r5-empty-state-icon">${icon}</div>
      <div class="r5-empty-state-title">${escapeHtml(title)}</div>
      <div class="r5-empty-state-desc">${escapeHtml(desc)}</div>
      ${actionLabel && actionId ? `
        <button id="${actionId}" class="btn btn-primary btn-sm">${escapeHtml(actionLabel)}</button>
      ` : ''}
    </div>
  `;
}

export function renderSkeletonCardsHtml(count = 4) {
  return `
    <div class="kpi-grid" role="status" aria-label="Loading metrics">
      ${Array.from({ length: count }).map(() => `
        <div class="r5-skeleton-card">
          <div class="r5-skeleton r5-skeleton-line short"></div>
          <div class="r5-skeleton r5-skeleton-line medium" style="height: 28px;"></div>
          <div class="r5-skeleton r5-skeleton-line short"></div>
        </div>
      `).join('')}
    </div>
  `;
}

export function renderSkeletonTableHtml(rows = 4, cols = 5) {
  return `
    <div class="r5-card" role="status" aria-label="Loading data table">
      <div class="r5-card-header">
        <div class="r5-skeleton r5-skeleton-line medium" style="width: 240px; height: 20px;"></div>
      </div>
      <div style="padding: 1rem 1.25rem;">
        ${Array.from({ length: rows }).map(() => `
          <div class="r5-skeleton-table-row">
            ${Array.from({ length: cols }).map((_, cIdx) => `
              <div class="r5-skeleton r5-skeleton-line ${cIdx === 1 ? 'long' : 'medium'}" style="flex: 1; margin: 0;"></div>
            `).join('')}
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

export function renderErrorStateHtml({
  title = 'Operation Failed',
  message = 'An unexpected error occurred while querying telemetry.',
  onRetryId = ''
} = {}) {
  return `
    <div class="r5-error-state" role="alert">
      <span class="r5-error-state-icon">⚠️</span>
      <div style="flex: 1;">
        <div class="r5-error-state-title">${escapeHtml(title)}</div>
        <div class="r5-error-state-desc">${escapeHtml(message)}</div>
        ${onRetryId ? `
          <button id="${onRetryId}" class="btn btn-secondary btn-sm" style="margin-top: 0.75rem;">🔄 Retry Request</button>
        ` : ''}
      </div>
    </div>
  `;
}
