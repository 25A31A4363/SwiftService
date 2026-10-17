export interface ApiMetadata {
  page?: number;
  limit?: number;
  total?: number;
  totalPages?: number;
  requestId?: string;
  timestamp: string;
}

export interface ApiErrorDetail {
  field?: string;
  message: string;
  rule?: string;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: ApiErrorDetail[] | Record<string, unknown>;
  timestamp: string;
  path?: string;
  requestId?: string;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiErrorResponse;
  meta?: ApiMetadata;
}

export interface PaginationQuery {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface OperationalFilterQuery extends PaginationQuery {
  organizationId?: string;
  regionId?: string;
  storeId?: string;
  departmentId?: string;
  teamId?: string;
  status?: string;
  priorityTier?: string;
  search?: string;
}
