import { expect, type APIRequestContext, type Page } from '@playwright/test';

export const E2E_PASSWORD = 'E2ePassword123!';
export const API_URL = 'http://127.0.0.1:8100/api/v1';

export const USERS = {
  student: 'e2e.student@university.edu',
  student2: 'e2e.student2@university.edu',
  staff: 'e2e.staff@university.edu',
  admin: 'e2e.admin@university.edu',
} as const;

export async function uiLogin(page: Page, email: string, password = E2E_PASSWORD) {
  await page.goto('/login');
  await page.locator('#login-email').fill(email);
  await page.locator('#login-password').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
}

export async function loginAndWait(page: Page, email: string, home: string) {
  await uiLogin(page, email);
  await page.waitForURL(`**${home}`);
  await expect(page).not.toHaveURL(/\/login/);
}

export async function apiLogin(request: APIRequestContext, email: string, password = E2E_PASSWORD) {
  const response = await request.post(`${API_URL}/auth/login`, {
    data: { email, password },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as { access_token: string; user: { id: number } };
}

export async function createTicketViaApi(
  request: APIRequestContext,
  email: string,
  payload: Partial<{ subject: string; description: string; department_id: number }> = {},
) {
  const login = await apiLogin(request, email);
  const departments = await request.get(`${API_URL}/departments`, {
    headers: { Authorization: `Bearer ${login.access_token}` },
  });
  expect(departments.ok()).toBeTruthy();
  const departmentId = payload.department_id ?? (await departments.json()).items[0].id as number;

  const response = await request.post(`${API_URL}/tickets`, {
    headers: { Authorization: `Bearer ${login.access_token}` },
    data: {
      subject: payload.subject ?? 'E2E polling ticket',
      description: payload.description ?? 'Created by the E2E suite for polling verification.',
      department_id: departmentId,
    },
  });
  expect(response.status(), await response.text()).toBe(201);
  return (await response.json()) as {
    id: number;
    public_reference: string;
    subject: string;
    status: string;
  };
}

export async function patchTicketStatus(
  request: APIRequestContext,
  adminEmail: string,
  ticketId: number,
  status: string,
) {
  const login = await apiLogin(request, adminEmail);
  const response = await request.patch(`${API_URL}/tickets/${ticketId}`, {
    headers: { Authorization: `Bearer ${login.access_token}` },
    data: { status },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}
