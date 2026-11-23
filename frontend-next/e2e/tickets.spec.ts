import { expect, test } from '@playwright/test';
import { createTicketViaApi, loginAndWait, patchTicketStatus, USERS } from './helpers';

test.describe('ticket submission, polling and isolation', () => {
  test('student submits a query and sees the public reference', async ({ page }) => {
    await loginAndWait(page, USERS.student, '/student');

    await page.locator('#ticket-subject').fill('E2E scholarship document question');
    await page.locator('#ticket-description').fill(
      'Please confirm which scholarship documents I must upload this semester.',
    );
    await page.locator('#ticket-department').selectOption({ label: 'Registry' });
    await page.getByRole('button', { name: 'Submit query' }).click();

    const notice = page.locator('p[role="status"]');
    await expect(notice).toContainText(/TKT-[0-9A-F]{8} submitted successfully/);
    await expect(page.getByRole('cell', { name: /E2E scholarship document question/ })).toBeVisible();
  });

  test('ticket detail polls and reflects a status change', async ({ page, request }) => {
    const ticket = await createTicketViaApi(request, USERS.student, {
      subject: 'E2E live status ticket',
      description: 'The status of this ticket will change while the page is open.',
    });
    await loginAndWait(page, USERS.student, '/student');
    await page.goto(`/tickets/${ticket.id}`);

    await expect(page.getByRole('heading', { name: 'E2E live status ticket' })).toBeVisible();
    await expect(page.getByLabel('Live status updates enabled')).toBeVisible();
    await expect(page.getByText('New', { exact: true }).first()).toBeVisible();

    await patchTicketStatus(request, USERS.admin, ticket.id, 'in_progress');

    await expect(page.getByText('In progress', { exact: true }).first()).toBeVisible({
      timeout: 25_000,
    });
  });

  test('a student cannot read another student ticket by id', async ({ page, request }) => {
    const other = await createTicketViaApi(request, USERS.student2, {
      subject: 'E2E private ticket must not leak',
      description: 'Another student must never see this subject or reference.',
    });

    await loginAndWait(page, USERS.student, '/student');
    await page.goto(`/tickets/${other.id}`);

    await expect(page.getByText('Ticket unavailable')).toBeVisible();
    await expect(page.getByText('E2E private ticket must not leak')).toHaveCount(0);
    await expect(page.getByText(other.public_reference)).toHaveCount(0);
  });

  test('escalation and de-escalation appear in recorded history and staff notifications', async ({
    page,
    request,
  }) => {
    const ticket = await createTicketViaApi(request, USERS.student, {
      subject: 'E2E escalation history and notifications',
      description: 'Verifies recorded escalation history and notification centre delivery.',
    });
    const adminLogin = await request.post('http://127.0.0.1:8100/api/v1/auth/login', {
      data: { email: USERS.admin, password: 'E2ePassword123!' },
    });
    const adminBody = (await adminLogin.json()) as { access_token: string };
    const staffLookup = await request.get('http://127.0.0.1:8100/api/v1/users/assignable', {
      headers: { Authorization: `Bearer ${adminBody.access_token}` },
    });
    const assignable = (await staffLookup.json()).items as Array<{ id: number; email: string }>;
    const staffUser = assignable.find((item) => item.email === USERS.staff);
    expect(staffUser).toBeDefined();

    await request.post(`http://127.0.0.1:8100/api/v1/tickets/${ticket.id}/assign`, {
      headers: { Authorization: `Bearer ${adminBody.access_token}` },
      data: { assignee_id: staffUser!.id },
    });

    await loginAndWait(page, USERS.admin, '/admin');
    await page.goto(`/tickets/${ticket.id}`);

    const checkbox = page.getByRole('checkbox', { name: 'Escalated' });
    await expect(checkbox).toBeVisible();
    await checkbox.click();
    await expect(checkbox).toBeChecked();
    await expect(page.locator('p[role="status"]')).toContainText('Ticket escalated');

    await expect(page.getByRole('heading', { name: 'Escalations' })).toBeVisible();
    await expect(page.getByText('Escalated by E2E Admin (ADMIN)').first()).toBeVisible();

    await checkbox.click();
    await expect(checkbox).not.toBeChecked();
    await expect(page.locator('p[role="status"]')).toContainText('Escalation removed');
    await expect(page.getByText('De-escalated by E2E Admin (ADMIN)').first()).toBeVisible();

    await page.getByRole('button', { name: /Account menu/i }).click();
    await page.getByRole('menuitem', { name: /Sign out/i }).click();
    await page.waitForURL('**/login');

    await loginAndWait(page, USERS.staff, '/staff');
    await page.goto('/notifications');
    await expect(page.getByText(`Escalated ticket ${ticket.public_reference}`, { exact: true })).toBeVisible();
    await expect(page.getByText(`De-escalated ticket ${ticket.public_reference}`, { exact: true })).toBeVisible();
  });
});
