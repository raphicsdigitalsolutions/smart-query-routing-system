import axios from 'axios';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const baseURL = configuredBaseUrl.replace(/\/+$/, '');

/**
 * Access tokens are held in module memory only - never in localStorage or
 * sessionStorage. They are attached as Bearer headers, so the browser never
 * sends them automatically and CSRF tokens are not required for this design.
 */
let accessToken = null;

export function setAuthToken(token) {
  accessToken = token || null;
}

export function clearAuthToken() {
  accessToken = null;
}

export function getAuthToken() {
  return accessToken;
}

/** Single Axios instance shared by the whole frontend. */
export const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: { Accept: 'application/json' },
});

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuthToken();
      // AuthContext listens and clears UI state without logging request bodies.
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export const API_BASE_URL = baseURL;

/** Turn an API error into a short, user-safe message (never echoes passwords). */
export function getApiErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const data = error?.response?.data;
  if (typeof data?.error === 'string') return data.error;
  if (typeof data?.detail === 'string') return data.detail;
  if (error?.code === 'ERR_NETWORK') return 'Backend is unreachable. Check that the API is running.';
  return fallback;
}

export async function getRootInfo() {
  const { data } = await api.get('/');
  return data;
}

export async function getHealth() {
  const { data } = await api.get('/health');
  return data;
}

export async function getApiStatus() {
  const { data } = await api.get('/api/v1/status');
  return data;
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------
export async function registerStudent(payload) {
  const { data } = await api.post('/api/v1/auth/register', payload);
  return data;
}

export async function login(payload) {
  const { data } = await api.post('/api/v1/auth/login', payload);
  setAuthToken(data.access_token);
  return data;
}

export async function getMe() {
  const { data } = await api.get('/api/v1/auth/me');
  return data;
}

// ---------------------------------------------------------------------------
// Departments
// ---------------------------------------------------------------------------
export async function listDepartments() {
  const { data } = await api.get('/api/v1/departments');
  return data;
}

export async function createDepartment(payload) {
  const { data } = await api.post('/api/v1/departments', payload);
  return data;
}

export async function updateDepartment(id, payload) {
  const { data } = await api.patch(`/api/v1/departments/${id}`, payload);
  return data;
}

export async function listAssignableUsers() {
  const { data } = await api.get('/api/v1/users/assignable');
  return data;
}

// ---------------------------------------------------------------------------
// Tickets
// ---------------------------------------------------------------------------
export async function createTicket(payload) {
  const { data } = await api.post('/api/v1/tickets', payload);
  return data;
}

export async function listTickets(params = {}) {
  // Avoid sending empty filter strings to typed FastAPI query parameters.
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  );
  const { data } = await api.get('/api/v1/tickets', { params: cleanParams });
  return data;
}

export async function getTicket(ticketId) {
  const { data } = await api.get(`/api/v1/tickets/${ticketId}`);
  return data;
}

export async function getTicketHistory(ticketId) {
  const { data } = await api.get(`/api/v1/tickets/${ticketId}/history`);
  return data;
}

export async function patchTicket(ticketId, payload) {
  const { data } = await api.patch(`/api/v1/tickets/${ticketId}`, payload);
  return data;
}

export async function assignTicket(ticketId, assigneeId) {
  const { data } = await api.post(`/api/v1/tickets/${ticketId}/assign`, {
    assignee_id: assigneeId,
  });
  return data;
}

export async function listMessages(ticketId) {
  const { data } = await api.get(`/api/v1/tickets/${ticketId}/messages`);
  return data;
}

export async function postMessage(ticketId, payload) {
  const { data } = await api.post(`/api/v1/tickets/${ticketId}/messages`, payload);
  return data;
}

export default api;
