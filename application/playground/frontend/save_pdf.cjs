const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.error('PAGE ERROR:', err));
  
  console.log("Navigating to localhost Playground...");
  await page.goto('http://localhost:5173/');
  await page.waitForTimeout(3000);
  
  console.log("Clicking Runs tab...");
  await page.click('button[title="Runs"]');
  await page.waitForTimeout(3000);
  
  console.log("Searching for meal planning run...");
  const searchInput = page.locator('input[aria-label="Search runs"]');
  if (await searchInput.isVisible()) {
    await searchInput.fill("meal-planning");
    await page.waitForTimeout(1000);
  }
  
  console.log("Clicking meal planning job card...");
  const jobCard = page.locator('button[title*="meal-planning"]').first();
  await jobCard.click();
  await page.waitForTimeout(3000);
  
  console.log("Locating Download PDF button...");
  const pdfBtn = page.locator('button:has-text("Download PDF")').first();
  if (await pdfBtn.isVisible()) {
    console.log("Found Download PDF button! Setting up download listener...");
    const downloadPromise = page.waitForEvent('download', { timeout: 35000 });
    await pdfBtn.click();
    
    const download = await downloadPromise;
    const savePath = path.join('C:', 'Users', 'Saksham Kapoor', 'Documents', 'MatrAIx', 'pg-meal-planning-frontend-report.pdf');
    await download.saveAs(savePath);
    console.log('SUCCESS! PDF exported and saved to:', savePath);
  } else {
    console.error("Download PDF button not visible on page!");
    await page.screenshot({ path: path.join(__dirname, 'debug_pdf_error.png') });
  }
  
  await browser.close();
})();
