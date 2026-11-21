export const ROLES = ['student', 'staff', 'hod', 'admin'] as const;
export type Role = (typeof ROLES)[number];

export const TICKET_STATUSES = [
  'new',
  'assigned',
  'in_progress',
  'waiting_for_student',
  'resolved',
  'closed',
] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];

export const TICKET_PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;
export type TicketPriority = (typeof TICKET_PRIORITIES)[number];

export interface UserResponse {
  id: number;
  full_name: string;
  email: string;
  role: Role;
  department_id: number | null;
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: UserResponse;
}

export interface SessionResponse {
  user: UserResponse;
  csrfToken: string;
  expiresIn: number | null;
}

export interface SessionProbeResponse {
  user: UserResponse | null;
  csrfToken: string;
  expiresIn: number | null;
}

export interface HealthResponse {
  success: boolean;
  status: string;
}

export interface DepartmentResponse {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface DepartmentListResponse {
  success: boolean;
  items: DepartmentResponse[];
}

export interface DepartmentCreate {
  name: string;
  description?: string | null;
}

export interface DepartmentUpdate {
  name?: string;
  description?: string | null;
  is_active?: boolean;
}

export interface AssignableUserResponse {
  id: number;
  full_name: string;
  email: string;
  role: Role;
  department_id: number | null;
}

export interface AssignableUserListResponse {
  success: boolean;
  items: AssignableUserResponse[];
}

export const TICKET_CHANNELS = ['web', 'email', 'whatsapp'] as const;
export type TicketChannel = (typeof TICKET_CHANNELS)[number];

export interface TicketResponse {
  id: number;
  public_reference: string;
  subject: string;
  description: string;
  category: string | null;
  priority: TicketPriority;
  status: TicketStatus;
  is_escalated: boolean;
  student_id: number;
  assigned_to: number | null;
  department_id: number;
  student_name: string;
  assignee_name: string | null;
  department_name: string;
  created_at: string;
  updated_at: string;
  channel?: TicketChannel;
  auto_routed?: boolean;
}

export interface TicketListResponse {
  success: boolean;
  items: TicketResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface MessageResponse {
  id: number;
  ticket_id: number;
  sender_id: number;
  sender_name: string;
  message_body: string;
  is_internal: boolean;
  created_at: string;
}

export interface MessageListResponse {
  success: boolean;
  items: MessageResponse[];
  total: number;
}

export interface MessageCreatedResponse {
  success: boolean;
  message: MessageResponse;
}

/** Safe attachment metadata returned by the backend; storage paths are never exposed. */
export interface AttachmentResponse {
  id: number;
  message_id: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface AttachmentListResponse {
  success: boolean;
  items: AttachmentResponse[];
  total: number;
}

export interface AttachmentCreateInput {
  file: File;
  message_body?: string;
  is_internal?: boolean;
}

/** Client-side hints only; the backend validates allowed types and size authoritatively. */
export const ATTACHMENT_EXTENSIONS = ['pdf', 'txt', 'md'] as const;
export const ATTACHMENT_MAX_BYTES = 5 * 1024 * 1024;

export interface AiErrorPayload {
  code: string;
  message: string;
}

export interface AiExecutionStep {
  node: string;
  status: string;
  duration_ms: number;
  detail?: string | null;
  attempts?: number | null;
  model?: string | null;
}

export interface AiClassificationResult {
  intent: string;
  category: string;
  urgency: TicketPriority;
  language: string;
  entities: string[];
  confidence: number;
  rationale: string;
}

export interface AiDepartmentRecommendation {
  department_id: number | null;
  department_name: string | null;
  confidence: number;
  reason: string;
  source?: string;
}

export interface AiStaffRecommendation {
  staff_id: number;
  staff_name: string;
  role: string;
  confidence: number;
  reason: string;
}

export interface AiKnowledgeSource {
  source_id: string;
  title: string;
  excerpt: string;
  source_url?: string | null;
  tags?: string[];
  relevance_score: number;
}

export interface AiDraft {
  body: string;
  language: string;
  confidence: number;
  source_ids: string[];
  needs_staff_review: boolean;
}

export interface AiValidation {
  passed: boolean;
  issues: string[];
  overall_confidence: number;
  checked_at: string;
}

export interface AiAnalysisResponse {
  success: boolean;
  id: number;
  ticket_id: number;
  version: number;
  status: 'completed' | 'failed';
  is_current: boolean;
  classification: AiClassificationResult | null;
  priority_recommendation: TicketPriority | null;
  department_recommendation: AiDepartmentRecommendation | null;
  staff_recommendation: AiStaffRecommendation | null;
  knowledge_sources: AiKnowledgeSource[];
  no_evidence: boolean;
  draft: AiDraft | null;
  validation: AiValidation | null;
  confidence: number | null;
  abstention_reason: string | null;
  error: AiErrorPayload | null;
  execution_metadata: AiExecutionStep[];
  approved_message_id: number | null;
  approved_at: string | null;
  created_at: string;
}

export interface AiDraftApprovalResponse {
  success: boolean;
  analysis_id: number;
  message: MessageResponse;
  already_approved: boolean;
}

export interface StatusHistoryItem {
  id: number;
  from_status: TicketStatus | null;
  to_status: TicketStatus;
  changed_by_id: number | null;
  note: string | null;
  created_at: string;
}

export interface AssignmentHistoryItem {
  id: number;
  from_assignee_id: number | null;
  to_assignee_id: number | null;
  changed_by_id: number | null;
  created_at: string;
}

export interface TicketHistoryResponse {
  success: boolean;
  status_changes: StatusHistoryItem[];
  assignments: AssignmentHistoryItem[];
}

export interface MutationResponse {
  success: boolean;
  ticket: TicketResponse;
  message: string | null;
}

export interface TicketCreate {
  subject: string;
  description: string;
  department_id?: number | null;
  category?: string | null;
  priority?: TicketPriority;
  auto_route?: boolean;
  channel?: TicketChannel;
}

export interface TicketUpdate {
  subject?: string;
  description?: string;
  priority?: TicketPriority;
  status?: TicketStatus;
  is_escalated?: boolean;
  department_id?: number;
}

export interface MessageCreate {
  message_body: string;
  is_internal?: boolean;
}

export interface TicketFilters {
  status: TicketStatus | '';
  priority: TicketPriority | '';
  escalated: 'true' | 'false' | '';
  search: string;
}

export const EMPTY_TICKET_FILTERS: TicketFilters = {
  status: '',
  priority: '',
  escalated: '',
  search: '',
};

export const ROLE_HOME: Record<Role, string> = {
  student: '/student',
  staff: '/staff',
  hod: '/hod',
  admin: '/admin',
};

export const STATUS_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  new: ['assigned', 'in_progress', 'closed'],
  assigned: ['in_progress', 'waiting_for_student', 'resolved', 'new'],
  in_progress: ['waiting_for_student', 'resolved', 'assigned'],
  waiting_for_student: ['in_progress', 'resolved', 'closed'],
  resolved: ['closed', 'in_progress'],
  closed: [],
};

export const STAFF_ALLOWED_TRANSITIONS: TicketStatus[] = [
  'in_progress',
  'waiting_for_student',
  'resolved',
  'closed',
];

export const PRETTY_LABELS: Record<string, string> = {
  student: 'Student',
  staff: 'Staff',
  hod: 'HOD',
  admin: 'Administrator',
  new: 'New',
  assigned: 'Assigned',
  in_progress: 'In progress',
  waiting_for_student: 'Waiting for student',
  resolved: 'Resolved',
  closed: 'Closed',
  low: 'Low',
  normal: 'Normal',
  high: 'High',
  urgent: 'Urgent',
  web: 'Web',
  email: 'Email',
  whatsapp: 'WhatsApp',
};

/* -------------------------------------------------------------------------- */
/* Phase 7 — platform capabilities                                            */
/* -------------------------------------------------------------------------- */

/** Backend error code raised when a user has not configured a personal AI key. */
export const AI_MISSING_KEY_CODE = 'ai_personal_key_required';

export interface ApiKeyStatus {
  provider: string;
  configured: boolean;
  key_hint: string | null;
  is_valid: boolean | null;
  validated_at: string | null;
  last_used_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** The API may return a single status object or a provider list; both are normalised by the client. */
export interface ApiKeyListPayload {
  success?: boolean;
  items?: ApiKeyStatus[];
  providers?: ApiKeyStatus[];
  status?: ApiKeyStatus;
  provider?: string;
  configured?: boolean;
  key_hint?: string | null;
  is_valid?: boolean | null;
  validated_at?: string | null;
  last_used_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface IntegrationStatus {
  success?: boolean;
  smtp: boolean;
  whatsapp: boolean;
  google_oauth: boolean;
  intake_webhook: boolean;
}

export type KnowledgeSourceType = 'text' | 'txt' | 'md' | 'pdf';

export interface KnowledgeDocument {
  id: number;
  title: string;
  source_key: string;
  version: number;
  source_type: string;
  file_name: string | null;
  mime_type: string | null;
  checksum?: string | null;
  content_text?: string | null;
  department_id: number | null;
  uploaded_by_id: number;
  approved_by_id: number | null;
  approved_at: string | null;
  is_approved: boolean;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface KnowledgeVersion {
  id: number;
  version: number;
  title?: string;
  source_key?: string;
  source_type?: string;
  file_name?: string | null;
  is_approved?: boolean;
  is_active?: boolean;
  approved_at?: string | null;
  created_at: string;
  content_text?: string | null;
}

export interface KnowledgeListPayload {
  success?: boolean;
  items?: KnowledgeDocument[];
  documents?: KnowledgeDocument[];
  total?: number;
  skip?: number;
  limit?: number;
}

export interface KnowledgeVersionListPayload {
  success?: boolean;
  items?: KnowledgeVersion[];
  versions?: KnowledgeVersion[];
}

export interface KnowledgeCreateInput {
  title: string;
  source_type: KnowledgeSourceType;
  source_key?: string;
  content?: string;
  department_id?: number | null;
  file?: File | null;
}

export interface NotificationItem {
  id: number;
  ticket_id: number | null;
  recipient_user_id: number | null;
  recipient_address: string | null;
  channel: string;
  event_type: string;
  subject: string | null;
  body: string;
  status: string;
  attempts?: number;
  last_error?: string | null;
  provider_id?: string | null;
  sent_at?: string | null;
  read_at: string | null;
  is_internal?: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface NotificationListPayload {
  success?: boolean;
  items?: NotificationItem[];
  notifications?: NotificationItem[];
  total?: number;
  skip?: number;
  limit?: number;
}

export interface AnalyticsCountItem {
  name: string;
  value: number;
}

export interface AnalyticsMonthlyItem {
  month: string;
  created?: number;
  resolved?: number;
  value?: number;
}

/** Overview aggregates are role-scoped by the backend. Counts may be absent until data exists. */
export interface AnalyticsOverview {
  success?: boolean;
  role?: Role;
  total_tickets?: number;
  open_tickets?: number;
  resolved_tickets?: number;
  escalated_tickets?: number;
  unassigned_tickets?: number;
  avg_resolution_hours?: number | null;
  avg_first_response_hours?: number | null;
  by_status?: AnalyticsCountItem[] | Record<string, number>;
  by_priority?: AnalyticsCountItem[] | Record<string, number>;
  by_department?: AnalyticsCountItem[] | Record<string, number>;
  monthly?: AnalyticsMonthlyItem[] | Record<string, number>;
  generated_at?: string | null;
}

export type ReportFormat = 'pdf' | 'xlsx';

export interface Announcement {
  id: number;
  title: string;
  body: string;
  audience_roles_json?: Role[];
  audience_roles?: Role[];
  department_id: number | null;
  created_by_id: number;
  published_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface AnnouncementListPayload {
  success?: boolean;
  items?: Announcement[];
  announcements?: Announcement[];
  total?: number;
  skip?: number;
  limit?: number;
}

export interface AnnouncementCreate {
  title: string;
  body: string;
  audience_roles?: Role[];
  department_id?: number | null;
}

export interface AnnouncementUpdate {
  title?: string;
  body?: string;
  audience_roles?: Role[];
  is_active?: boolean;
  department_id?: number | null;
}

export interface LeaveWindow {
  id: number;
  user_id: number;
  start_at: string;
  end_at: string;
  reason: string | null;
  auto_reply: string;
  is_active: boolean;
  created_by_id?: number;
  created_at: string;
  updated_at?: string | null;
  user_name?: string | null;
}

export interface LeaveListPayload {
  success?: boolean;
  items?: LeaveWindow[];
  leaves?: LeaveWindow[];
  total?: number;
  skip?: number;
  limit?: number;
}

export interface LeaveCreate {
  start_at: string;
  end_at: string;
  reason?: string | null;
  auto_reply: string;
  is_active?: boolean;
}

export interface LeaveUpdate {
  start_at?: string;
  end_at?: string;
  reason?: string | null;
  auto_reply?: string;
  is_active?: boolean;
}

export interface AuditLogEntry {
  id: number;
  actor_id: number | null;
  actor_role: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: Record<string, unknown> | null;
  is_override: boolean;
  created_at: string;
}

export interface AuditListPayload {
  success?: boolean;
  items?: AuditLogEntry[];
  logs?: AuditLogEntry[];
  total?: number;
  skip?: number;
  limit?: number;
}

export interface EscalationRunResponse {
  success?: boolean;
  scanned: number;
  escalated: number;
}
