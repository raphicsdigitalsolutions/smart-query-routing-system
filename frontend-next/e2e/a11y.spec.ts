import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { createTicketViaApi, loginAndWait, USERS } from './helpers';

async function expectNoSeriousViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const blocking = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(
    blocking.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      help: violation.help,
      nodes: violation.nodes.map((node) => ({
        target: node.target.join(' '),
        html: node.html,
        failureSummary: node.failureSummary,
      })),
    })),
  ).toEqual([]);
}

test.describe('accessibility', () => {
  test('login page has no serious axe violations', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    await expectNoSeriousViolations(page);
  });

  test('student workspace has no serious axe violations', async ({ page }) => {
    await loginAndWait(page, USERS.student, '/student');
    await expect(page.getByRole('main').getByRole('heading', { name: 'My queries' })).toBeVisible();
    await expectNoSeriousViolations(page);
  });

  test('ticket detail has no serious axe violations', async ({ page, request }) => {
    const ticket = await createTicketViaApi(request, USERS.student, {
      subject: 'E2E accessibility ticket',
      description: 'Accessibility scan target for the ticket detail screen.',
    });
    await loginAndWait(page, USERS.student, '/student');
    await page.goto(`/tickets/${ticket.id}`);
    await expect(page.getByRole('heading', { name: 'E2E accessibility ticket' })).toBeVisible();
    await expectNoSeriousViolations(page);
  });
});
