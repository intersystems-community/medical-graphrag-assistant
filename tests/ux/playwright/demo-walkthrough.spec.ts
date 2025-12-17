import { test } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Demo Walkthrough - Captures screenshots for animated GIF
 *
 * This test captures a series of screenshots demonstrating key features
 * of the Medical GraphRAG Assistant. Screenshots can be combined into
 * an animated GIF using tools like ImageMagick or gifski.
 *
 * Usage:
 *   npx playwright test demo-walkthrough.spec.ts --headed
 *
 * Then create GIF:
 *   convert -delay 200 -loop 0 screenshots/*.png demo-walkthrough.gif
 *   # or with gifski for better quality:
 *   gifski --fps 2 -o demo-walkthrough.gif screenshots/*.png
 */

const SCREENSHOT_DIR = 'screenshots';

test.describe('Demo Walkthrough', () => {
  test.beforeAll(async () => {
    // Create screenshots directory
    const dir = path.join(__dirname, SCREENSHOT_DIR);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });

  test('capture walkthrough screenshots', async ({ page }) => {
    const screenshotPath = (name: string) =>
      path.join(__dirname, SCREENSHOT_DIR, name);

    // Set viewport for consistent screenshots
    await page.setViewportSize({ width: 1280, height: 800 });

    // 1. Navigate to app
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: screenshotPath('01-home.png'), fullPage: false });

    // 2. Show sidebar with tools
    const sidebar = page.locator('[data-testid="stSidebar"]');
    await sidebar.waitFor({ state: 'visible' });
    await page.screenshot({ path: screenshotPath('02-sidebar-tools.png'), fullPage: false });

    // 3. Click "Common Symptoms" example button
    await page.click('button:has-text("Common Symptoms")');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: screenshotPath('03-query-sent.png'), fullPage: false });

    // 4. Wait for AI response
    await page.locator('.stChatMessage').nth(1).waitFor({ state: 'visible', timeout: 60000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: screenshotPath('04-ai-response.png'), fullPage: false });

    // 5. Expand "Show Execution Details"
    const detailsExpander = page.getByText('Show Execution Details', { exact: false }).first();
    await detailsExpander.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: screenshotPath('05-execution-details.png'), fullPage: false });

    // 6. Scroll to see entities section
    await page.evaluate(() => window.scrollBy(0, 300));
    await page.waitForTimeout(500);
    await page.screenshot({ path: screenshotPath('06-entities-section.png'), fullPage: false });

    // 7. Clear chat
    await page.click('button:has-text("Clear")');
    await page.waitForTimeout(1000);

    // 8. Click "Symptom Chart" for visualization (or error response if tables missing)
    await page.click('button:has-text("Symptom Chart")');
    // Wait for either Plotly chart or AI response (backend may return error if tables missing)
    await page.locator('.stChatMessage').nth(1).waitFor({ state: 'visible', timeout: 60000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: screenshotPath('07-symptom-chart.png'), fullPage: false });

    // 9. Clear and show Knowledge Graph
    await page.click('button:has-text("Clear")');
    await page.waitForTimeout(1000);

    await page.click('button:has-text("Knowledge Graph")');
    await page.locator('.stChatMessage').nth(1).waitFor({ state: 'visible', timeout: 60000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: screenshotPath('08-knowledge-graph.png'), fullPage: false });

    // 10. Final summary screenshot
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({ path: screenshotPath('09-final.png'), fullPage: false });

    console.log(`\nScreenshots saved to: ${path.join(__dirname, SCREENSHOT_DIR)}`);
    console.log('\nTo create animated GIF:');
    console.log('  convert -delay 200 -loop 0 tests/ux/playwright/screenshots/*.png demo-walkthrough.gif');
    console.log('  # or with gifski for better quality:');
    console.log('  gifski --fps 2 -o demo-walkthrough.gif tests/ux/playwright/screenshots/*.png');
  });
});
