import { expect, test } from '@playwright/test';
import { USERS, loginAndWait, uiLogin } from './helpers';

test.describe('authentication and access control', () => {
  test('student signs in and lands on the student workspace', async ({ page }) => {
    await loginAndWait(page, USERS.student, '/student');

    await expect(page.getByRole('main').getByRole('heading', { name: 'My queries' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Submit a new query' })).toBeVisible();
  });

  test('invalid credentials show a safe generic error', async ({ page }) => {
    await uiLogin(page, USERS.student, 'wrong-password');

    const alert = page.locator('p[role="alert"]');
    await expect(alert).toContainText('Invalid email or password');
    await expect(page).toHaveURL(/\/login/);
  });

  test('unauthenticated visitor is redirected to login', async ({ page }) => {
    await page.goto('/student');
    await page.waitForURL('**/login');
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  });

  test('student cannot open admin-only screens', async ({ page }) => {
    await loginAndWait(page, USERS.student, '/student');
    await page.goto('/admin');

    await expect(page.getByRole('heading', { name: 'Access restricted' })).toBeVisible();
    await expect(page.getByText('Backend authorization remains the final authority.')).toBeVisible();
  });

  test('admin signs in and lands on the admin console', async ({ page }) => {
    await loginAndWait(page, USERS.admin, '/admin');
    await expect(page).not.toHaveURL(/\/login/);
  });
});
