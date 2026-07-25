const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  
  console.log("Navigating to Playground UI...");
  await page.goto('http://localhost:8765/?mode=playground&pgTask=chatbot&view=runs');
  await page.waitForTimeout(3000);
  
  console.log("Locating the d6556853 batch run...");
  const btn = page.locator('button[title*="d6556853"]').first();
  await btn.click();
  await page.waitForTimeout(4000);
  
  console.log("Waiting for report to render...");
  await page.waitForTimeout(2000);
  
  console.log("Clicking Download PDF...");
  const downloadPromise = page.waitForEvent('download', { timeout: 30000 });
  
  await page.locator('button:has-text("Download PDF")').click();
  
  const download = await downloadPromise;
  const savePath = path.join('C:', 'Users', 'Saksham Kapoor', 'Documents', 'MatrAIx', 'pg-meal-planning-frontend-report-v2.pdf');
  await download.saveAs(savePath);
  console.log('PDF export successful! Saved to:', savePath);
  
  await browser.close();
})();
