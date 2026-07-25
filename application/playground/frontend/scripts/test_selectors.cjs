const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8765/?view=runs&harborJob=texas-holdem-1000-persona', { waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);
  
  // Expand sections
  const expanders = page.locator('button[aria-expanded="false"]');
  const count = await expanders.count();
  console.log(`Found ${count} collapsible expanders`);
  for (let i = 0; i < count; i++) {
    try { 
      await expanders.nth(i).click(); 
      await page.waitForTimeout(300); 
    } catch(e) {}
  }
  await page.waitForTimeout(3000);

  const svgs = await page.locator('svg').count();
  const canvas = await page.locator('canvas').count();
  const flexCharts = await page.locator('div[class*="chart"], div[class*="Chart"], .recharts-responsive-container').count();
  const bars = await page.locator('rect, path, circle').count();
  
  console.log('SVGs found:', svgs);
  console.log('Canvases found:', canvas);
  console.log('Chart container class matches:', flexCharts);
  console.log('SVG shape nodes (bars/points):', bars);

  await browser.close();
})();
