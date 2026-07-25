const { chromium } = require('playwright');
const fs = require('fs');

const JOB = 'texas-holdem-1000-persona';
const OUT = 'C:\\Users\\Saksham Kapoor\\Documents\\MatrAIx\\pr284-reports-v2\\texas-holdem-poker.pdf';
const TMP = 'C:\\Users\\Saksham Kapoor\\AppData\\Local\\Temp\\playwright-pdfs\\poker_enriched.pdf';
fs.mkdirSync('C:\\Users\\Saksham Kapoor\\AppData\\Local\\Temp\\playwright-pdfs', { recursive: true });
try { fs.unlinkSync(TMP); } catch(e) {}
try { fs.unlinkSync(OUT); } catch(e) {}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1400, height: 900 });
  const context = await browser.newContext({ acceptDownloads: true });

  await page.goto(`http://127.0.0.1:8765/?view=runs&harborJob=${encodeURIComponent(JOB)}`, { waitUntil: 'load', timeout: 120000 });
  console.log('Page loaded, waiting for aggregation rebuild...');
  // Wait for the "Download PDF" button to appear (signals aggregation loaded)
  await page.locator('button:has-text("Download PDF")').first().waitFor({ timeout: 120000 });
  console.log('Download PDF button visible. Proceeding...');
  await page.waitForTimeout(2000);

  // Pre-expand all sections
  console.log('Pre-expanding sections...');
  for (let r = 0; r < 6; r++) {
    await page.evaluate(() => window.scrollBy(0, 700));
    await page.waitForTimeout(500);
    const count = await page.evaluate(() => {
      let c = 0;
      document.querySelectorAll('[aria-expanded="false"]').forEach(el => {
        if (!(el instanceof HTMLElement)) return;
        const txt = (el.textContent || '').trim();
        if (txt.includes('3 issues') || txt.includes('description')) return;
        el.scrollIntoViewIfNeeded(); el.click(); c++;
      }); return c;
    });
    if (count === 0) break;
    await page.waitForTimeout(2000);
  }
  await page.addStyleTag({ content: '* { max-height: none !important; overflow: visible !important; }' });
  await page.waitForTimeout(1500);

  // Click Download PDF
  console.log('Clicking Download PDF...');
  const btn = page.locator('button:has-text("Download PDF")').first();
  if (await btn.count() === 0) { console.error('No button'); await browser.close(); return; }
  const dl = page.waitForEvent('download', { timeout: 120000 });
  await btn.click();
  const download = await dl;
  await download.saveAs(TMP);
  fs.copyFileSync(TMP, OUT);
  console.log(`PDF: ${(fs.statSync(OUT).size/1024).toFixed(0)} KB`);
  await browser.close();
})();
