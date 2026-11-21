import { apiAuthFetch, apiFetch, notifyUnauthorized } from './client';
import { ApiError, parseApiError } from './errors';
import type {
  AiAnalysisResponse,
  AiDraftApprovalResponse,
  AnalyticsOverview,
  Announcement,
  AttachmentCreateInput,
  AttachmentListResponse,
  AttachmentResponse,
  AnnouncementCreate,
  AnnouncementListPayload,
  AnnouncementUpdate,
  ApiKeyListPayload,
  ApiKeyStatus,
  AssignableUserListResponse,
  AuditListPayload,
  AuditLogEntry,
  DepartmentCreate,
  DepartmentListResponse,
  DepartmentResponse,
  DepartmentUpdate,
  EscalationRunResponse,
  HealthResponse,
  IntegrationStatus,
  KnowledgeCreateInput,
  KnowledgeDocument,
  KnowledgeListPayload,
  KnowledgeVersion,
  KnowledgeVersionListPayload,
  LeaveCreate,
  LeaveListPayload,
  LeaveUpdate,
  LeaveWindow,
  MessageCreate,
  MessageCreatedResponse,
  MessageListResponse,
  MutationResponse,
  NotificationItem,
  NotificationListPayload,
  ReportFormat,
  SessionProbeResponse,
  SessionResponse,
  TicketCreate,
  TicketHistoryResponse,
  TicketListResponse,
  TicketResponse,
  TicketUpdate,
  UserResponse,
} from './types';

export type TicketQuery = Record<string, string | number | boolean | null | undefined>;

function buildQuery(params: TicketQuery = {}): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === '' || value === null || value === undefined) return;
    search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

/** Browsers disagree on the MIME type of .md files; send the type the backend expects. */
const ATTACHMENT_MIME: Record<string, string> = {
  pdf: 'application/pdf',
  txt: 'text/plain',
  md: 'text/markdown',
};

function asArray<T>(...values: Array<T[] | undefined | null>): T[] {
  for (const value of values) {
    if (Array.isArray(value)) return value;
  }
  return [];
}

function normalizeApiKeys(payload: ApiKeyListPayload): ApiKeyStatus[] {
  if (payload && typeof payload === 'object' && 'provider' in payload && typeof payload.provider === 'string') {
    const status: ApiKeyStatus = {
      provider: payload.provider,
      configured: Boolean(payload.configured),
      key_hint: payload.key_hint ?? null,
      is_valid: payload.is_valid ?? null,
      validated_at: payload.validated_at ?? null,
      last_used_at: payload.last_used_at ?? null,
      created_at: payload.created_at ?? null,
      updated_at: payload.updated_at ?? null,
    };
    return [status];
  }
  return asArray(payload?.items, payload?.providers).length > 0
    ? asArray(payload?.items, payload?.providers)
    : payload?.status
      ? [payload.status]
      : [];
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/health', { cache: 'no-store', signal });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw parseApiError(response.status, payload);
  return payload as HealthResponse;
}

export const authApi = {
  login: (email: string, password: string) =>
    apiAuthFetch<SessionResponse>('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (payload: { full_name: string; email: string; password: string }) =>
    apiAuthFetch<SessionResponse>('/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  me: () => apiAuthFetch<SessionProbeResponse>('/session'),
  logout: () => apiAuthFetch<{ success: true }>('/logout', { method: 'POST' }),
  google: (credential: string) =>
    apiAuthFetch<SessionResponse>('/google', {
      method: 'POST',
      body: JSON.stringify({ credential }),
    }),
};

export const departmentsApi = {
  list: (signal?: AbortSignal) => apiFetch<DepartmentListResponse>('/departments', { signal }),
  create: (payload: DepartmentCreate) =>
    apiFetch<DepartmentResponse>('/departments', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  update: (id: number, payload: DepartmentUpdate) =>
    apiFetch<DepartmentResponse>(`/departments/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
};

export const usersApi = {
  listAssignable: (signal?: AbortSignal) => apiFetch<AssignableUserListResponse>('/users/assignable', { signal }),
};

export const ticketsApi = {
  create: (payload: TicketCreate) =>
    apiFetch<TicketResponse>('/tickets', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  list: (params: TicketQuery = {}, signal?: AbortSignal) =>
    apiFetch<TicketListResponse>(`/tickets${buildQuery(params)}`, { signal }),
  get: (ticketId: number | string, signal?: AbortSignal) => apiFetch<TicketResponse>(`/tickets/${ticketId}`, { signal }),
  history: (ticketId: number | string, signal?: AbortSignal) =>
    apiFetch<TicketHistoryResponse>(`/tickets/${ticketId}/history`, { signal }),
  update: (ticketId: number | string, payload: TicketUpdate) =>
    apiFetch<MutationResponse>(`/tickets/${ticketId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  assign: (ticketId: number | string, assigneeId: number | null) =>
    apiFetch<MutationResponse>(`/tickets/${ticketId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ assignee_id: assigneeId }),
    }),
  listMessages: (ticketId: number | string, signal?: AbortSignal) =>
    apiFetch<MessageListResponse>(`/tickets/${ticketId}/messages`, { signal }),
  postMessage: (ticketId: number | string, payload: MessageCreate) =>
    apiFetch<MessageCreatedResponse>(`/tickets/${ticketId}/messages`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listAttachments: (ticketId: number | string, signal?: AbortSignal) =>
    apiFetch<AttachmentListResponse>(`/tickets/${ticketId}/attachments`, { signal }),
  uploadAttachment: (ticketId: number | string, input: AttachmentCreateInput) => {
    const body = new FormData();
    const extension = input.file.name.split('.').pop()?.toLowerCase() ?? '';
    const mimeType = ATTACHMENT_MIME[extension];
    body.set('file', mimeType ? new File([input.file], input.file.name, { type: mimeType }) : input.file);
    if (input.message_body?.trim()) body.set('message_body', input.message_body.trim());
    body.set('is_internal', String(Boolean(input.is_internal)));
    return apiFetch<AttachmentResponse>(`/tickets/${ticketId}/attachments`, {
      method: 'POST',
      body,
    });
  },
};

export const aiApi = {
  analyze: (ticketId: number | string, signal?: AbortSignal) =>
    apiFetch<AiAnalysisResponse>(`/ai/tickets/${ticketId}/analyze`, {
      method: 'POST',
      signal,
    }),
  getAnalysis: (ticketId: number | string, signal?: AbortSignal) =>
    apiFetch<AiAnalysisResponse>(`/ai/tickets/${ticketId}/analysis`, { signal }),
  regenerateDraft: (ticketId: number | string, signal?: AbortSignal) =>
    apiFetch<AiAnalysisResponse>(`/ai/tickets/${ticketId}/draft`, {
      method: 'POST',
      signal,
    }),
  approveDraft: (ticketId: number | string) =>
    apiFetch<AiDraftApprovalResponse>(`/ai/tickets/${ticketId}/approve-draft`, {
      method: 'POST',
    }),
};

/* -------------------------------------------------------------------------- */
/* Phase 7 — settings, knowledge, analytics and workspace capabilities         */
/* -------------------------------------------------------------------------- */

export const apiKeysApi = {
  list: async (signal?: AbortSignal): Promise<ApiKeyStatus[]> => {
    const payload = await apiFetch<ApiKeyListPayload>('/settings/api-keys', { signal });
    return normalizeApiKeys(payload);
  },
  save: (apiKey: string) =>
    apiFetch<ApiKeyStatus>('/settings/api-keys', {
      method: 'PUT',
      body: JSON.stringify({ api_key: apiKey }),
    }),
  validate: () =>
    apiFetch<ApiKeyStatus>('/settings/api-keys/validate', {
      method: 'POST',
    }),
  remove: () =>
    apiFetch<{ success?: boolean }>('/settings/api-keys', {
      method: 'DELETE',
    }),
};

export const integrationsApi = {
  status: (signal?: AbortSignal) =>
    apiFetch<IntegrationStatus>('/integrations/status', { signal }),
};

export interface KnowledgeListResult {
  items: KnowledgeDocument[];
  total: number;
}

export const knowledgeApi = {
  list: async (params: TicketQuery = {}, signal?: AbortSignal): Promise<KnowledgeListResult> => {
    const payload = await apiFetch<KnowledgeListPayload>(`/knowledge${buildQuery(params)}`, { signal });
    const items = asArray(payload?.items, payload?.documents);
    return { items, total: payload?.total ?? items.length };
  },
  get: (id: number, signal?: AbortSignal) =>
    apiFetch<KnowledgeDocument>(`/knowledge/${id}`, { signal }),
  create: (input: KnowledgeCreateInput) => {
    const body = new FormData();
    body.set('title', input.title.trim());
    body.set('source_type', input.source_type);
    if (input.source_key?.trim()) body.set('source_key', input.source_key.trim());
    if (input.content?.trim()) body.set('content', input.content.trim());
    if (input.department_id && input.department_id > 0) {
      body.set('department_id', String(input.department_id));
    }
    if (input.file) body.set('file', input.file);
    return apiFetch<KnowledgeDocument>('/knowledge', { method: 'POST', body });
  },
  update: (id: number, payload: { is_approved?: boolean; is_active?: boolean }) =>
    apiFetch<KnowledgeDocument>(`/knowledge/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  remove: (id: number) =>
    apiFetch<{ success?: boolean }>(`/knowledge/${id}`, { method: 'DELETE' }),
  versions: async (id: number, signal?: AbortSignal): Promise<KnowledgeVersion[]> => {
    const payload = await apiFetch<KnowledgeVersionListPayload>(`/knowledge/${id}/versions`, { signal });
    return asArray(payload?.items, payload?.versions);
  },
};

export interface NotificationListResult {
  items: NotificationItem[];
  total: number;
}

export const notificationsApi = {
  list: async (params: TicketQuery = {}, signal?: AbortSignal): Promise<NotificationListResult> => {
    const payload = await apiFetch<NotificationListPayload>(`/notifications${buildQuery(params)}`, { signal });
    const items = asArray(payload?.items, payload?.notifications);
    return { items, total: payload?.total ?? items.length };
  },
  markRead: (id: number) =>
    apiFetch<{ success?: boolean; notification?: NotificationItem }>(`/notifications/${id}/read`, {
      method: 'POST',
    }),
};

export const analyticsApi = {
  overview: (signal?: AbortSignal) =>
    apiFetch<AnalyticsOverview>('/analytics/overview', { signal }),
};

/** Fetch a report through the BFF. GET keeps the request CSRF-safe and cookie-authenticated. */
export async function downloadReport(format: ReportFormat): Promise<Blob> {
  const response = await fetch(`/api/reports/${format}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = parseApiError(response.status, payload);
    if (response.status === 401) notifyUnauthorized();
    throw error;
  }
  return response.blob();
}

export const announcementsApi = {
  list: async (params: TicketQuery = {}, signal?: AbortSignal): Promise<Announcement[]> => {
    const payload = await apiFetch<AnnouncementListPayload>(`/announcements${buildQuery(params)}`, { signal });
    return asArray(payload?.items, payload?.announcements);
  },
  create: (input: AnnouncementCreate) =>
    apiFetch<Announcement>('/announcements', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  update: (id: number, payload: AnnouncementUpdate) =>
    apiFetch<Announcement>(`/announcements/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  remove: (id: number) =>
    apiFetch<{ success?: boolean }>(`/announcements/${id}`, { method: 'DELETE' }),
};

export const leaveApi = {
  list: async (params: TicketQuery = {}, signal?: AbortSignal): Promise<LeaveWindow[]> => {
    const payload = await apiFetch<LeaveListPayload>(`/leave${buildQuery(params)}`, { signal });
    return asArray(payload?.items, payload?.leaves);
  },
  create: (input: LeaveCreate) =>
    apiFetch<LeaveWindow>('/leave', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  update: (id: number, payload: LeaveUpdate) =>
    apiFetch<LeaveWindow>(`/leave/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  remove: (id: number) =>
    apiFetch<{ success?: boolean }>(`/leave/${id}`, { method: 'DELETE' }),
};

export interface AuditListResult {
  items: AuditLogEntry[];
  total: number;
}

export const auditApi = {
  list: async (params: TicketQuery = {}, signal?: AbortSignal): Promise<AuditListResult> => {
    const payload = await apiFetch<AuditListPayload>(`/audit${buildQuery(params)}`, { signal });
    const items = asArray(payload?.items, payload?.logs);
    return { items, total: payload?.total ?? items.length };
  },
};

export const escalationApi = {
  run: () =>
    apiFetch<EscalationRunResponse>('/tickets/escalation/run', { method: 'POST' }),
};

export type { UserResponse, ApiError };
