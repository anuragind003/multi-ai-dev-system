import { test, expect } from '@playwright/test';

test.describe('Application E2E Tests', () => {
  // Base URL for the frontend application (running via docker-compose in CI)
  const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  test.beforeEach(async ({ page }) => {
    // Navigate to the application's home page before each test
    await page.goto(BASE_URL);
  });

  test('should display the home page title', async ({ page }) => {
    await expect(page).toHaveTitle(/Next.js App/); // Adjust based on your actual title
    await expect(page.locator('h1')).toHaveText('Welcome to Next.js!'); // Adjust based on your actual H1
  });

  test('should be able to navigate to an about page (if exists)', async ({ page }) => {
    // Assuming there's a link to /about
    const aboutLink = page.locator('a', { hasText: 'About' });
    if (await aboutLink.isVisible()) {
      await aboutLink.click();
      await expect(page).toHaveURL(`${BASE_URL}/about`);
      await expect(page.locator('h1')).toHaveText('About Us'); // Adjust based on your actual About page H1
    } else {
      test.skip(true, 'About link not found, skipping navigation test.');
    }
  });

  test('should be able to fetch data from the backend API', async ({ page }) => {
    // This test assumes your frontend has a button or a section that fetches data from the backend.
    // Example: A button that fetches items from /api/items
    await page.goto(BASE_URL); // Ensure we are on the home page

    // Mock the backend API response for predictable testing
    await page.route(`${API_URL}/items`, async route => {
      const json = [
        { id: 1, name: 'Mock Item 1', description: 'Description 1' },
        { id: 2, name: 'Mock Item 2', description: 'Description 2' },
      ];
      await route.fulfill({ json, status: 200 });
    });

    // Assuming there's a button to load items
    const loadItemsButton = page.locator('button', { hasText: 'Load Items' });
    if (await loadItemsButton.isVisible()) {
      await loadItemsButton.click();
      await expect(page.locator('text=Mock Item 1')).toBeVisible();
      await expect(page.locator('text=Mock Item 2')).toBeVisible();
    } else {
      test.skip(true, 'Load Items button not found, skipping API fetch test.');
    }
  });

  test('should display a 404 page for non-existent routes', async ({ page }) => {
    await page.goto(`${BASE_URL}/non-existent-page`);
    await expect(page.locator('h1')).toHaveText(/404/); // Adjust based on your actual 404 page H1
    await expect(page.locator('text=This page could not be found.')).toBeVisible(); // Adjust text
  });
});