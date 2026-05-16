const { test, expect } = require('@playwright/test');

test('Check dashboard-2049 UI', async ({ page }) => {
    await page.goto('http://localhost:8000/LYRN_v6/dashboard-2049.html');
    await expect(page.locator('#hud-background')).toBeVisible();
});
